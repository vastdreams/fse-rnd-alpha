"""
PATH: backend/app/services/factor_sizing.py
PURPOSE: The validated-evidence sizing bound and the falsification-rule status.

Only the frozen paper premium (contracts/factor-premium.json) is allowed to
size capital: f_max = 0.25 · max(0, λ − 1.96·SE_NW) / σ²_book. With today's
frozen headline numbers the bound is ZERO and every payload says so plainly —
"no validated edge, no size" — instead of inventing a positive bound.

Falsification rules live in contracts/falsification-rules.json; this module
only reports their status (armed / not-yet-evaluable / breached). Nothing
retires silently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

from app.contracts.paths import contracts_dir

FACTOR_PREMIUM_FILE = "factor-premium.json"
FALSIFICATION_FILE = "falsification-rules.json"

KELLY_FRACTION = 0.25
CI_MULTIPLIER = 1.96
MIN_SEALED_MONTHS_FOR_SIGMA = 12


@lru_cache(maxsize=1)
def load_factor_premium() -> dict:
    path = contracts_dir() / FACTOR_PREMIUM_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Sealed factor premium contract missing: {path}")
    data = json.loads(path.read_text())
    if data.get("id") != "FACTOR_PREMIUM_V1":
        raise ValueError(f"Unexpected factor premium contract id in {path}")
    return data


@lru_cache(maxsize=1)
def load_falsification_rules() -> dict:
    path = contracts_dir() / FALSIFICATION_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Sealed falsification contract missing: {path}")
    return json.loads(path.read_text())


def mu_claim_pct(contract: Optional[dict] = None) -> float:
    """Conservative claimed edge in %/yr: max(0, λ − 1.96·SE) of the sizing series."""
    c = contract or load_factor_premium()
    series = c["series"][c["sizing_series"]]
    mean = float(series["mean_pct_per_year"])
    se = float(series["nw_std_error"])
    return max(0.0, mean - CI_MULTIPLIER * se)


def f_max(
    sigma_book_sq: Optional[float],
    n_sealed_months: int,
    contract: Optional[dict] = None,
) -> float:
    """Fractional-Kelly bound on total BUY-book weight (as a fraction of capital).

    σ²_book comes from realized sealed-ledger monthly returns; without at
    least MIN_SEALED_MONTHS_FOR_SIGMA months it is UNKNOWN and the bound is 0
    (fail-closed: an unknown variance never unlocks size).
    """
    mu = mu_claim_pct(contract) / 100.0
    if mu <= 0.0:
        return 0.0
    if (
        sigma_book_sq is None
        or sigma_book_sq <= 0.0
        or n_sealed_months < MIN_SEALED_MONTHS_FOR_SIGMA
    ):
        return 0.0
    return KELLY_FRACTION * mu / sigma_book_sq


def sizing_payload(
    sigma_book_sq: Optional[float] = None,
    n_sealed_months: int = 0,
) -> dict[str, Any]:
    """Full sizing-wall payload: bound, both frozen series, and the plain-language why."""
    c = load_factor_premium()
    mu = mu_claim_pct(c)
    bound = f_max(sigma_book_sq, n_sealed_months, c)
    headline = c["series"][c["sizing_series"]]
    reasons: list[str] = []
    if mu <= 0.0:
        reasons.append(
            f"Headline premium {headline['mean_pct_per_year']:.2f}%/yr with NW SE "
            f"{headline['nw_std_error']:.2f} (t={headline['t_statistic']:.2f}) — the "
            f"95% CI includes zero, so the claimed edge is zero."
        )
    if n_sealed_months < MIN_SEALED_MONTHS_FOR_SIGMA:
        reasons.append(
            f"Sealed BUY ledger has {n_sealed_months} monthly snapshots; "
            f"{MIN_SEALED_MONTHS_FOR_SIGMA} required before realized book variance is usable."
        )
    return {
        "engine": "factor_sizing_v1",
        "mu_claim_pct_per_year": round(mu, 4),
        "f_max_fraction": round(bound, 6),
        "sigma_book_sq": sigma_book_sq,
        "n_sealed_months": n_sealed_months,
        "kelly_fraction": KELLY_FRACTION,
        "formula": "f_max = 0.25 · max(0, λ − 1.96·SE_NW) / σ²_book",
        "series": c["series"],
        "sizing_series": c["sizing_series"],
        "disclosures": c["disclosures"],
        "verdict": (
            "No validated edge, no size — capital sizing is on you until the evidence earns it."
            if bound <= 0.0
            else f"Validated bound: at most {bound*100:.1f}% of capital across BUY-clearance names."
        ),
        "why_zero": reasons or None,
    }


def falsification_status(
    n_sealed_months: int = 0,
    ledger_excess_t: Optional[float] = None,
    rolling_factor_t: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Status of each pre-registered rule. Reporting only — action is human."""
    rules = load_falsification_rules()["rules"]
    out: list[dict[str, Any]] = []
    for r in rules:
        rid = r["id"]
        status = "armed_not_yet_evaluable"
        evidence = None
        if rid == "R1_FACTOR_DECAY":
            if rolling_factor_t is not None:
                status = "breached" if rolling_factor_t < 1.0 else "armed_passing"
                evidence = f"rolling 5y NW t = {rolling_factor_t:.2f}"
            else:
                evidence = "rolling factor t-stat series not yet wired into the product"
        elif rid == "R2_LEDGER_FAILURE":
            if n_sealed_months >= 36 and ledger_excess_t is not None:
                status = "breached" if ledger_excess_t < 0.0 else "armed_passing"
                evidence = f"n={n_sealed_months} months, excess t = {ledger_excess_t:.2f}"
            else:
                evidence = f"sealed ledger has {n_sealed_months}/36 required months"
        elif rid == "R3_CALIBRATION":
            evidence = "MoS-bucket gap-closure calibration requires ≥ 12 sealed months of outcomes"
        out.append(
            {
                "id": rid,
                "label": r["label"],
                "rule": r["rule"],
                "consequence": r["consequence"],
                "status": status,
                "evidence": evidence,
            }
        )
    return out
