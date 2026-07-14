"""
PATH: backend/app/services/thesis_object.py
PURPOSE: Assemble the per-name thesis object — the single surface an investor
reads before selecting a name into a book. Every section is sealed data or
arithmetic on sealed data; nothing here invents a probability or a forecast.

Sections: disagreement (price vs sealed band), cause (tape event), repayment
engine (RD spine + frozen premium series), survivability floors, payoff skew,
p* break-even (display only), resolution (dated catalyst), size (validated
bound — zero today).
"""

from __future__ import annotations

from typing import Any, Optional

from app.services.factor_sizing import sizing_payload
from app.services.reprice_break_even import p_star_payload
from app.services.thesis_fields import load_thesis_contract


def _mv_value(vec: Any, name: str) -> Optional[float]:
    m = getattr(vec, name, None)
    return getattr(m, "value", None) if m is not None else None


def _floor_rows(vec: Any, contract: dict) -> list[dict[str, Any]]:
    s = contract["survivability"]
    return [
        {
            "field": "fcfm_sbc",
            "label": "SBC-adjusted FCF margin",
            "value": _mv_value(vec, "fcfm_sbc"),
            "threshold": "> 0 (or Rule-of-40 pass)",
        },
        {
            "field": "rule40",
            "label": "Rule of 40",
            "value": _mv_value(vec, "rule40"),
            "threshold": f">= {s['rule40_floor']:g} (alternative cash engine)",
        },
        {
            "field": "runway_yrs",
            "label": "Cash runway",
            "value": _mv_value(vec, "runway_yrs"),
            "threshold": f">= {s['runway_years_floor']:g}y (UNKNOWN tolerated only when FCF > 0)",
        },
        {
            "field": "dilution_ann",
            "label": "Annualised dilution",
            "value": _mv_value(vec, "dilution_ann"),
            "threshold": f"<= {s['dilution_ann_ceiling']:g}",
        },
        {
            "field": "retention",
            "label": "Net revenue retention",
            "value": _mv_value(vec, "retention"),
            "threshold": f">= {s['retention_floor']:g} (UNKNOWN tolerated, flagged)",
        },
    ]


def build_thesis_object(
    *,
    vec: Any,
    valuation_range: Optional[dict],
    tape_event: Optional[dict],
    dated_anchors: list[dict],
    bull_dcf: Optional[dict],
    n_sealed_months: int = 0,
) -> dict[str, Any]:
    """Pure assembly — every input is already sealed or derived arithmetic."""
    contract = load_thesis_contract()
    vr = valuation_range or {}
    price_live = vr.get("price_live")
    mos_live = _mv_value(vec, "mos_live")
    skew = _mv_value(vec, "payoff_skew")
    skew_label = getattr(vec, "payoff_skew_label", None)
    rd_elig = getattr(vec, "rd_elig", None)
    survivable = getattr(vec, "survivable", None)

    bull_med = (bull_dcf or {}).get("fair_px_med")
    p_star = p_star_payload(
        price_live,
        vr.get("fair_px_med"),
        bull_med,
        scenario_source=(bull_dcf or {}).get("source"),
    )
    if bull_dcf is None:
        p_star["reading"] = "No repricing leg run — record a bull-scenario DCF to see the market-implied probability."

    size = sizing_payload(sigma_book_sq=None, n_sealed_months=n_sealed_months)

    return {
        "engine_version": "thesis_v1",
        "disagreement": {
            "price_live": price_live,
            "price_stale": vr.get("price_stale"),
            "fair_px_lo": vr.get("fair_px_lo"),
            "fair_px_med": vr.get("fair_px_med"),
            "fair_px_hi": vr.get("fair_px_hi"),
            "mos_live_sealed": mos_live,
            "gap_to_median": vr.get("gap_to_median"),
            "note": "The band is a sealed model output; the gap is arithmetic against the live tape.",
        },
        "cause": {
            "tape_event": tape_event,
            "note": (
                "Measured peak→trough drawdown — the dislocation the thesis buys into."
                if tape_event
                else "No material tape event detected — without a measured dislocation there is no repricing cause."
            ),
        },
        "repayment_engine": {
            "rd_composite": _mv_value(vec, "rd_composite"),
            "rd_elig": rd_elig,
            "premium_series": size["series"],
            "note": (
                "Top-quintile RD composite = membership in the validated paper cohort (proxy). "
                "Cross-sectional evidence — never a per-name expected return."
            ),
        },
        "survivability": {
            "survivable": survivable,
            "floors": _floor_rows(vec, contract),
        },
        "skew": {
            "payoff_skew": skew,
            "payoff_skew_label": skew_label,
            "min_ratio": contract["payoff_skew"]["min_ratio"],
        },
        "p_star": p_star,
        "resolution": {
            "dated_anchors": dated_anchors,
            "note": (
                "Dated, cited events inside the tape-event window."
                if dated_anchors
                else "No dated catalyst anchor — F4 stays UNKNOWN and BUY is blocked."
            ),
        },
        "size": size,
    }
