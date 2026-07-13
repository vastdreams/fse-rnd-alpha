"""
PATH: backend/tests/test_rank_row_invariants.py
PURPOSE: First-principles audit for ranked rows — catch math/logic breaks in CI.
"""

from app.services.rank_row_invariants import (
    audit_rank_row,
    compute_live_vs_target_pct,
    fair_band_zone,
)

# Production-shaped KSPI snapshot used as a golden fixture.
KSPI = {
    "ticker": "KSPI",
    "price_live": 89.67,
    "fair_px_lo": 207.5951403270201,
    "fair_px_med": 249.77850114953984,
    "fair_px_hi": 291.9618619720595,
    "mos_live": 1.7855302905045147,
    "vs_median_pct": 1.7855302905045147,
    "revenue_usd": 9112728620,
    "score": 9.877425,
    "contributions": {"rd_prod": 4.5, "mos_live": 4.5, "roic": 0.4939},
}


def test_compute_live_vs_target_pct():
    assert compute_live_vs_target_pct(100, 150) == 0.5
    assert compute_live_vs_target_pct(200, 100) == -0.5
    assert compute_live_vs_target_pct(0, 100) is None
    assert compute_live_vs_target_pct(None, 100) is None


def test_fair_band_zone():
    assert fair_band_zone(90, 200, 290) == "below"
    assert fair_band_zone(240, 200, 290) == "inside"
    assert fair_band_zone(300, 200, 290) == "above"


def test_audit_passes_consistent_row():
    assert audit_rank_row(KSPI) == []


def test_audit_catches_vs_median_mismatch():
    bad = {**KSPI, "vs_median_pct": 0.5}
    codes = {v["code"] for v in audit_rank_row(bad)}
    assert "VS_MEDIAN_MISMATCH" in codes


def test_audit_catches_unordered_band():
    bad = {**KSPI, "fair_px_lo": 300, "fair_px_med": 250, "fair_px_hi": 200}
    codes = {v["code"] for v in audit_rank_row(bad)}
    assert "FAIR_BAND_ORDER" in codes


def test_audit_catches_mos_sign_contradiction():
    bad = {
        **KSPI,
        "price_live": 400,
        "fair_px_med": 250,
        "fair_px_lo": 200,
        "fair_px_hi": 290,
        "vs_median_pct": (250 - 400) / 400,
        "mos_live": 0.5,
    }
    codes = {v["code"] for v in audit_rank_row(bad)}
    assert "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET" in codes


def test_audit_catches_score_without_drivers():
    bad = {**KSPI, "contributions": {}}
    codes = {v["code"] for v in audit_rank_row(bad)}
    assert "SCORE_WITHOUT_DRIVERS" in codes
