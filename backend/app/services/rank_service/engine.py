"""
PATH: backend/app/services/rank_service/engine.py
PURPOSE: Rank the ENTIRE universe for a recipe (R1–R9). W2a core.

Ship rules enforced here (kill criteria in the redesign plan):
- No fixed-N shortlist object: output length = survivors of hard filters.
- Missing (None) metric values NEVER rank — a name missing a required axis is
  excluded from that recipe (R6 rule generalized), not silently imputed.
- PIT: rows whose available_date is after the panel as_of are treated as
  missing (no look-ahead).
- Completeness / freshness / kill are carried on every output row but only
  hard-filter when the recipe says so — completeness ≠ attractiveness.
- reviewer_passed is never set here (FinalReview only).

Statistics follow the paper conventions: median/MAD robust z winsorised at
±3 (scripts/saas_ai/analysis/util.py) — re-implemented here dependency-free
so the backend doesn't import the research scripts tree.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from app.contracts.research import (
    MetricValue,
    MetricVector,
    RankedRow,
    RankRecipe,
    RecipeId,
)

WINSOR_LIMIT = 3.0
_MAD_SIGMA = 1.4826


# =============================================================================
# Robust statistics (paper Eq. z-score conventions)
# =============================================================================

def robust_z(values: list[Optional[float]]) -> list[Optional[float]]:
    """Median/MAD robust z, winsorised at ±3. None stays None (never imputed)."""
    known = [v for v in values if v is not None and math.isfinite(v)]
    if len(known) < 2:
        return [0.0 if v is not None else None for v in values]
    med = statistics.median(known)
    mad = statistics.median([abs(v - med) for v in known])
    scale = _MAD_SIGMA * mad
    if scale == 0:
        mean = statistics.fmean(known)
        std = statistics.pstdev(known)
        if std == 0:
            return [0.0 if v is not None else None for v in values]
        return [
            max(-WINSOR_LIMIT, min(WINSOR_LIMIT, (v - mean) / std)) if v is not None else None
            for v in values
        ]
    return [
        max(-WINSOR_LIMIT, min(WINSOR_LIMIT, (v - med) / scale)) if v is not None else None
        for v in values
    ]


def _rank_pct(values: list[Optional[float]], higher_better: bool = True) -> list[Optional[float]]:
    """Percentile rank in [0,1]; None excluded and stays None."""
    known = sorted(
        (v for v in values if v is not None and math.isfinite(v)), reverse=not higher_better
    )
    n = len(known)
    if n == 0:
        return [None] * len(values)
    out: list[Optional[float]] = []
    for v in values:
        if v is None or not math.isfinite(v):
            out.append(None)
        else:
            # average position of equal values, scaled to (0,1]
            idx = [i for i, k in enumerate(known) if k == v]
            pos = (idx[0] + idx[-1]) / 2 + 1
            out.append(1 - (pos - 1) / n if n > 1 else 1.0)
    return out


# =============================================================================
# PIT-aware metric access
# =============================================================================

def pit_value(metric: MetricValue, as_of: Optional[date]) -> Optional[float]:
    """Value only if knowable at `as_of` (no look-ahead). None = Unknown."""
    if metric.value is None:
        return None
    if as_of is not None and metric.available_date is not None and metric.available_date > as_of:
        return None
    return metric.value


# =============================================================================
# Recipe machinery
# =============================================================================

@dataclass
class RankRequest:
    recipe: RankRecipe
    universe_version: str
    as_of: Optional[date] = None
    extra_hard_filters: list[str] = field(default_factory=list)


@dataclass
class _AxisSpec:
    """How one axis feeds a recipe score."""

    name: str
    getter: Callable[[MetricVector, Optional[date]], Optional[float]]
    weight: float = 1.0
    higher_better: bool = True
    required: bool = True  # missing → excluded from this recipe


def _mv(attr: str) -> Callable[[MetricVector, Optional[date]], Optional[float]]:
    def get(v: MetricVector, as_of: Optional[date]) -> Optional[float]:
        return pit_value(getattr(v, attr), as_of)

    return get


def _int_attr(attr: str) -> Callable[[MetricVector, Optional[date]], Optional[float]]:
    def get(v: MetricVector, as_of: Optional[date]) -> Optional[float]:
        raw = getattr(v, attr)
        return float(raw) if raw is not None else None

    return get


def _not_killed(v: MetricVector) -> bool:
    # Missing kill state is Unknown, not proof of safety. Fail closed.
    return v.kill_active is False


def _not_carved(v: MetricVector) -> bool:
    return v.carve_out is not True


# Axis specs per preset. R9 is built at runtime from the recipe's axes list.
_PRESET_AXES: dict[str, list[_AxisSpec]] = {
    "R1": [
        _AxisSpec("roic", _mv("roic")),
        _AxisSpec("gm", _mv("gm")),
        _AxisSpec("mos_live", _mv("mos_live")),
    ],
    "R2": [
        _AxisSpec("mos_live", _mv("mos_live"), weight=2.0),
        _AxisSpec("rd_prod", _mv("rd_prod")),
    ],
    "R3": [
        _AxisSpec("rd_prod", _mv("rd_prod"), weight=1.5),
        _AxisSpec("fcfm_sbc", _mv("fcfm_sbc")),
        _AxisSpec("roic", _mv("roic")),
        _AxisSpec("mos_live", _mv("mos_live"), weight=1.5),
    ],
    "R4": [
        _AxisSpec("rd_int", _mv("rd_int")),
        _AxisSpec("rd_mom", _mv("rd_mom")),
        _AxisSpec("rd_capital", _mv("rd_capital")),
        _AxisSpec("roic", _mv("roic"), weight=0.5),
    ],
    "R5": [
        _AxisSpec("offering_quality_z", _mv("offering_quality_z"), weight=2.0),
        _AxisSpec("retention", _mv("retention")),
        _AxisSpec("rule40", _mv("rule40")),
        _AxisSpec("concentration", _mv("concentration"), higher_better=False),
    ],
    "R6": [
        _AxisSpec("retention", _mv("retention")),
        _AxisSpec("mos_live", _mv("mos_live")),
    ],
    "R7": [
        _AxisSpec("roic", _mv("roic")),
        _AxisSpec("gm", _mv("gm")),
        _AxisSpec("fcfm_sbc", _mv("fcfm_sbc")),
        _AxisSpec("mos_live", _mv("mos_live")),
        _AxisSpec("ret_12m", _mv("ret_12m")),
    ],
    "R8": [
        _AxisSpec("runway_yrs", _mv("runway_yrs")),
        _AxisSpec("dilution_ann", _mv("dilution_ann"), higher_better=False),
        _AxisSpec("gm", _mv("gm")),
        _AxisSpec("rev_cagr", _mv("rev_cagr")),
    ],
}

# Hard filters per preset (beyond the universal ones below)
_PRESET_FILTERS: dict[str, Callable[[MetricVector], bool]] = {
    "R1": lambda v: _not_killed(v) and _not_carved(v),
    "R2": lambda v: _not_killed(v) and v.table20_pass_count == 12,
    "R3": lambda v: _not_killed(v) and _not_carved(v),
    "R4": lambda v: _not_killed(v),
    "R5": lambda v: _not_killed(v),
    "R6": lambda v: _not_killed(v),  # retention requirement handled by required axis
    "R7": lambda v: _not_killed(v),
    "R8": lambda v: _not_killed(v) and v.route == "pre_fcf",  # segregated route — never mixed with FCF+ ranks
}

# Recipes whose universe must be FCF-side only (pre-FCF handled by R8)
_FCF_SIDE = {"R1", "R2", "R3", "R5", "R6", "R7"}


class RankEngine:
    """Rank the full universe of MetricVectors under one recipe."""

    def rank(self, vectors: list[MetricVector], request: RankRequest) -> list[RankedRow]:
        recipe = request.recipe
        rid: RecipeId = recipe.recipe_id
        as_of = request.as_of

        axes = self._axes_for(recipe)
        gate = _PRESET_FILTERS.get(rid, _not_killed)

        # 1. Hard filters (survivors, variable N — never a fixed shortlist)
        survivors = [
            v
            for v in vectors
            if v.universe_version == request.universe_version
            and gate(v)
            and (rid not in _FCF_SIDE or v.route != "pre_fcf")
        ]

        # 2. Required-axis exclusion: missing values never rank
        rows: list[MetricVector] = []
        for v in survivors:
            values = {a.name: a.getter(v, as_of) for a in axes}
            if any(values[a.name] is None for a in axes if a.required):
                continue
            rows.append(v)

        if not rows:
            return []

        # 3. Cross-sectional robust z per axis (sign-adjusted), weighted sum
        axis_scores: dict[str, list[Optional[float]]] = {}
        for a in axes:
            raw = [a.getter(v, as_of) for v in rows]
            zs = robust_z(raw)
            axis_scores[a.name] = [
                (z if z is None else (z if a.higher_better else -z)) for z in zs
            ]

        scored: list[tuple[MetricVector, float, dict[str, float]]] = []
        for i, v in enumerate(rows):
            contributions: dict[str, float] = {}
            total = 0.0
            for a in axes:
                z = axis_scores[a.name][i]
                contrib = (z or 0.0) * a.weight
                contributions[a.name] = round(contrib, 6)
                total += contrib
            scored.append((v, total, contributions))

        scored.sort(key=lambda t: t[1], reverse=True)

        return [
            RankedRow(
                ticker=v.ticker,
                recipe_id=rid,
                universe_version=request.universe_version,
                rank=i + 1,
                score=round(score, 6),
                contributions=contribs,
                completeness_grade=v.completeness.grade,
                freshness_ok=not v.completeness.stale,
                kill_active=v.kill_active,
                reviewer_passed=None,  # only FinalReview may ever set this
            )
            for i, (v, score, contribs) in enumerate(scored)
        ]

    def exclusions(
        self, vectors: list[MetricVector], request: RankRequest
    ) -> list[dict]:
        """Why each non-ranked name was excluded — so 'all companies' views can
        show the FULL universe with honest reasons instead of silently hiding names."""
        recipe = request.recipe
        rid = recipe.recipe_id
        axes = self._axes_for(recipe)
        gate = _PRESET_FILTERS.get(rid, _not_killed)
        out: list[dict] = []
        for v in vectors:
            if v.universe_version != request.universe_version:
                continue
            reasons: list[str] = []
            if not gate(v):
                if v.kill_active is True:
                    reasons.append("kill criterion active")
                elif v.kill_active is None:
                    reasons.append("kill state unknown (fail-closed)")
                if rid in ("R1", "R3") and v.carve_out is True:
                    reasons.append("payments/float carve-out")
                if rid == "R2" and v.table20_pass_count != 12:
                    reasons.append(f"Table-20 gates {v.table20_pass_count if v.table20_pass_count is not None else '?'}/12")
                if rid == "R8" and v.route != "pre_fcf":
                    reasons.append("not on pre-FCF route")
                if not reasons:
                    reasons.append("hard filter")
            if rid in _FCF_SIDE and v.route == "pre_fcf":
                reasons.append("pre-FCF route (ranked separately under R8)")
            missing = [
                a.name for a in axes if a.required and a.getter(v, request.as_of) is None
            ]
            if missing:
                reasons.append(f"missing: {', '.join(missing)}")
            if reasons:
                out.append(
                    {
                        "ticker": v.ticker,
                        "reasons": reasons,
                        "completeness_grade": v.completeness.grade,
                        "route": v.route,
                        "kill_active": v.kill_active,
                    }
                )
        return out

    def _axes_for(self, recipe: RankRecipe) -> list[_AxisSpec]:
        if recipe.recipe_id != "R9":
            return _PRESET_AXES[recipe.recipe_id]
        # R9 custom builder: axes list from the saved recipe, equal weights,
        # metric fields resolved dynamically; unknown fields raise loudly.
        specs: list[_AxisSpec] = []
        for axis in recipe.axes:
            if not hasattr(MetricVector, "model_fields") or axis not in MetricVector.model_fields:
                raise ValueError(f"R9 axis '{axis}' is not a MetricVector field")
            ann = MetricVector.model_fields[axis].annotation
            getter = _mv(axis) if ann is MetricValue else _int_attr(axis)
            specs.append(_AxisSpec(axis, getter))
        return specs
