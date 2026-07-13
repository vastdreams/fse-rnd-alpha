"""
PATH: backend/tests/test_sell_ceiling.py
PURPOSE: BE sell-ceiling parity with FE (F_SELL_CEILING).
"""

from app.services.sell_ceiling import compute_sell_ceiling


def test_below_median_sells_at_target():
    s = compute_sell_ceiling(
        fair_px_lo=80, fair_px_med=100, fair_px_hi=130, price_live=70
    )
    assert s["formula_id"] == "F_SELL_CEILING"
    assert s["zone"] == "to_target"
    assert s["sell_ceil"] == 100
    assert s["lens"] == "median"
    assert abs(s["upside_to_ceil"] - (100 / 70 - 1)) < 1e-12
    assert s["horizon_years"] == 2  # upside ≈ 0.428 → 2y bucket


def test_in_upper_band_trims_at_high():
    s = compute_sell_ceiling(
        fair_px_lo=80, fair_px_med=100, fair_px_hi=130, price_live=110
    )
    assert s["zone"] == "in_upper_band"
    assert s["sell_ceil"] == 130
    assert s["lens"] == "high"


def test_past_ceiling():
    s = compute_sell_ceiling(
        fair_px_lo=80, fair_px_med=100, fair_px_hi=130, price_live=140
    )
    assert s["zone"] == "past_ceiling"
    assert s["sell_ceil"] == 130
    assert s["horizon_years"] is None
    assert s["remaining_ann"] is None
