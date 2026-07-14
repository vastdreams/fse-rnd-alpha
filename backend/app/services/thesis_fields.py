"""
PATH: backend/app/services/thesis_fields.py
PURPOSE: Pure maths for the thesis fields sealed into every metric vector:
  rd_composite / rd_elig (paper RD spine proxy), survivable (hard floors),
  payoff_skew (band asymmetry) and the weave z-scores used by the R4 rank.

CONTRACT: contracts/thesis-gates.json is the single source of thresholds and
weights. Nothing here is fitted to history; every UNKNOWN stays UNKNOWN and
fails closed at the BUY gates.

All functions are pure f(input) -> output so the universe build, the backfill
script and tests share one implementation.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any, Optional

from app.contracts.paths import contracts_dir
from app.services.rank_service.engine import robust_z

THESIS_CONTRACT_FILE = "thesis-gates.json"


@lru_cache(maxsize=1)
def load_thesis_contract() -> dict:
    """Load the sealed thesis-gates contract; fail loudly if absent."""
    path = contracts_dir() / THESIS_CONTRACT_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Sealed thesis contract missing: {path}")
    data = json.loads(path.read_text())
    if data.get("id") != "THESIS_GATES_V1":
        raise ValueError(f"Unexpected thesis contract id in {path}")
    return data


def _f(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def rd_composite_scores(
    rows: list[dict[str, Optional[float]]], contract: Optional[dict] = None
) -> list[Optional[float]]:
    """Cross-sectional RD composite: mean of robust z over the contract components.

    ``rows`` holds per-ticker raw values keyed by component name. Fewer than
    ``min_known_components`` known -> None (UNKNOWN, never imputed).
    """
    c = (contract or load_thesis_contract())["rd_composite"]
    components: list[str] = c["components"]
    min_known: int = int(c["min_known_components"])
    zs = {comp: robust_z([_f(r.get(comp)) for r in rows]) for comp in components}
    out: list[Optional[float]] = []
    for i in range(len(rows)):
        parts = [zs[comp][i] for comp in components if zs[comp][i] is not None]
        out.append(round(sum(parts) / len(parts), 6) if len(parts) >= min_known else None)
    return out


def rd_eligibility(
    composites: list[Optional[float]], contract: Optional[dict] = None
) -> list[Optional[bool]]:
    """Top-quintile membership on the composite. UNKNOWN composite -> UNKNOWN."""
    c = (contract or load_thesis_contract())["rd_composite"]
    q = float(c["eligibility_quantile"])
    known = sorted(v for v in composites if v is not None)
    if not known:
        return [None] * len(composites)
    # Inclusive quantile cut: the first member of the top (1-q) tail. With
    # n known values the top quintile starts at index ceil(q*n) (0-based).
    cut_idx = min(len(known) - 1, math.ceil(q * len(known)))
    cutoff = known[cut_idx]
    return [None if v is None else bool(v >= cutoff) for v in composites]


def survivability(
    row: dict[str, Optional[float]], contract: Optional[dict] = None
) -> Optional[bool]:
    """Hard floors from the sealed contract. Any required UNKNOWN -> UNKNOWN.

    Floors: (fcfm_sbc > 0 OR rule40 >= floor) AND runway >= floor (UNKNOWN
    tolerated only when FCF is positive) AND dilution <= ceiling AND
    (retention >= floor, UNKNOWN tolerated per contract).
    """
    c = (contract or load_thesis_contract())["survivability"]
    fcfm = _f(row.get("fcfm_sbc"))
    rule40 = _f(row.get("rule40"))
    runway = _f(row.get("runway_yrs"))
    dilution = _f(row.get("dilution_ann"))
    retention = _f(row.get("retention"))

    # Cash engine: need at least one known signal to say anything.
    if fcfm is None and rule40 is None:
        return None
    cash_ok = (fcfm is not None and fcfm > 0) or (
        rule40 is not None and rule40 >= float(c["rule40_floor"])
    )
    if not cash_ok:
        return False

    fcf_positive = fcfm is not None and fcfm > 0
    if runway is None:
        if not (fcf_positive and bool(c["runway_unknown_allowed_if_fcf_positive"])):
            return None
    elif runway < float(c["runway_years_floor"]):
        return False

    if dilution is None:
        return None
    if dilution > float(c["dilution_ann_ceiling"]):
        return False

    if retention is None:
        if not bool(c["retention_unknown_allowed"]):
            return None
    elif retention < float(c["retention_floor"]):
        return False

    return True


def payoff_skew(
    price: Optional[float],
    fair_px_lo: Optional[float],
    fair_px_hi: Optional[float],
) -> tuple[Optional[float], Optional[str]]:
    """Band asymmetry ``(hi - P) / (P - lo)``.

    Returns ``(ratio, label)``. Price at/below the low lens -> ``(None,
    "below_band")`` (downside-to-band <= 0: favourable but undefined). Any
    missing input or degenerate/inverted band -> ``(None, None)`` = UNKNOWN.
    """
    p, lo, hi = _f(price), _f(fair_px_lo), _f(fair_px_hi)
    if p is None or lo is None or hi is None or p <= 0 or hi <= lo:
        return None, None
    if p <= lo:
        return None, "below_band"
    if p >= hi:
        return 0.0, None
    return round((hi - p) / (p - lo), 4), None


def weave_z_scores(
    rows: list[dict[str, Optional[float]]],
    rd_composites: list[Optional[float]],
    contract: Optional[dict] = None,
) -> list[dict[str, Optional[float]]]:
    """Per-family weave z-scores for the R4 rank (ordinal only, no return claim).

    ``rows`` carry raw values for quality/valuation/momentum inputs;
    ``rd_composites`` is the already cross-sectional RD family score.
    """
    n = len(rows)
    quality_inputs = ["roic", "gm", "fcfm_sbc", "rule40"]
    q_zs = {k: robust_z([_f(r.get(k)) for r in rows]) for k in quality_inputs}
    v_z = robust_z([_f(r.get("mos_live")) for r in rows])
    mom_series = {
        "ret_3m": robust_z([_f(r.get("ret_3m")) for r in rows]),
        "ret_12m": robust_z([_f(r.get("ret_12m")) for r in rows]),
        # Drawdown is stored negative (price/peak − 1), so the raw value already
        # ranks correctly: shallower drawdown (closer to 0) scores higher.
        "dd": robust_z([_f(r.get("drawdown_from_peak")) for r in rows]),
    }
    out: list[dict[str, Optional[float]]] = []
    for i in range(n):
        q_parts = [q_zs[k][i] for k in quality_inputs if q_zs[k][i] is not None]
        m_parts = [s[i] for s in mom_series.values() if s[i] is not None]
        out.append(
            {
                "z_rd": rd_composites[i],
                "z_quality": round(sum(q_parts) / len(q_parts), 6) if q_parts else None,
                "z_valuation": v_z[i],
                "z_momentum": round(sum(m_parts) / len(m_parts), 6) if m_parts else None,
            }
        )
    return out


def weave_composite(z: dict[str, Optional[float]], contract: Optional[dict] = None) -> tuple[float, bool]:
    """Weighted weave score. Missing family contributes 0 and flags partial data."""
    w = (contract or load_thesis_contract())["weave_weights"]
    total = 0.0
    partial = False
    for family in ("z_rd", "z_quality", "z_valuation", "z_momentum"):
        v = z.get(family)
        if v is None:
            partial = True
            continue
        total += float(w[family]) * float(v)
    return round(total, 6), partial


def compute_thesis_fields(
    raw_rows: list[dict[str, Optional[float]]], contract: Optional[dict] = None
) -> list[dict[str, Any]]:
    """One-shot cross-sectional computation for a whole sealed universe.

    Each input row needs raw values for: rd_int, rd_capital, rd_prod, rd_mom,
    roic, gm, fcfm_sbc, rule40, runway_yrs, dilution_ann, retention, mos_live,
    ret_3m, ret_12m, drawdown_from_peak, price, fair_px_lo, fair_px_hi.
    Returns one dict per row: rd_composite, rd_elig, survivable, payoff_skew,
    payoff_skew_label, weave (z dict).
    """
    c = contract or load_thesis_contract()
    composites = rd_composite_scores(raw_rows, c)
    eligs = rd_eligibility(composites, c)
    weave = weave_z_scores(raw_rows, composites, c)
    out: list[dict[str, Any]] = []
    for row, comp, elig, z in zip(raw_rows, composites, eligs, weave):
        skew, skew_label = payoff_skew(
            row.get("price"), row.get("fair_px_lo"), row.get("fair_px_hi")
        )
        out.append(
            {
                "rd_composite": comp,
                "rd_elig": elig,
                "survivable": survivability(row, c),
                "payoff_skew": skew,
                "payoff_skew_label": skew_label,
                "weave": z,
            }
        )
    return out
