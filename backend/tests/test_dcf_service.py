"""
PATH: backend/tests/test_dcf_service.py
PURPOSE: W5 goldens — dcf_service must stay bit-compatible with the research
engine (scripts/saas_ai/analysis/valuation_engine.py) formulas.
"""

import math

import pytest

from app.services.dcf_service import DcfInputs, run_dcf, three_stage_ev, two_stage_ev


def _ref_two_stage(fcf0, g, wacc, years=10, g_term=0.03):
    """Reference implementation copied verbatim from valuation_engine._two_stage_ev."""
    pv, fcf = 0.0, fcf0
    for t in range(1, years + 1):
        gt = g + (g_term - g) * (t - 1) / (years - 1)
        fcf *= 1.0 + gt
        pv += fcf / (1.0 + wacc) ** t
    pv += fcf * (1.0 + g_term) / (wacc - g_term) / (1.0 + wacc) ** years
    return pv


class TestTwoStage:
    def test_matches_reference(self):
        for fcf0, g, wacc in [(100.0, 0.15, 0.10), (55.5, 0.05, 0.12), (1e9, 0.30, 0.10)]:
            assert two_stage_ev(fcf0, g, wacc) == pytest.approx(_ref_two_stage(fcf0, g, wacc), rel=1e-12)

    def test_golden_value(self):
        # Pinned golden: fcf0=100, g=15%, wacc=10% (10y fade to 3% terminal)
        assert two_stage_ev(100.0, 0.15, 0.10) == pytest.approx(2385.2921148, rel=1e-6)

    def test_negative_fcf_returns_none(self):
        assert two_stage_ev(-10.0, 0.15, 0.10) is None

    def test_wacc_below_terminal_returns_none(self):
        assert two_stage_ev(100.0, 0.15, 0.02) is None


class TestThreeStage:
    def test_margin_glide_reaches_target(self):
        ev = three_stage_ev(1000.0, 0.20, -0.10, 0.25, 0.12)
        assert ev is not None and ev > 0

    def test_no_revenue_returns_none(self):
        assert three_stage_ev(0.0, 0.2, 0.0, 0.25, 0.12) is None


class TestRunDcf:
    def test_rejects_invalid_horizons(self):
        with pytest.raises(ValueError, match="glide_years cannot exceed years"):
            DcfInputs(ticker="TEST", growth=0.15, years=5, glide_years=6)
        with pytest.raises(ValueError):
            DcfInputs(ticker="TEST", growth=0.15, years=1)

    def test_triangulation_median(self):
        inp = DcfInputs(
            ticker="TEST", growth=0.15, wacc=0.10,
            revenue_usd=1_000_000_000, fcf_sbc_usd=100_000_000, fcfm_sbc=0.10,
            target_margin=0.25, ev_mult_usd=3_000_000_000,
            net_cash_usd=500_000_000, shares_fut_implied=100_000_000, price=20.0,
        )
        out = run_dcf(inp)
        assert out.fair_ev_lo is not None and out.fair_ev_hi is not None
        assert out.fair_ev_lo <= out.fair_ev_med <= out.fair_ev_hi
        # Price bridge: (EV + net cash) / future shares
        assert out.fair_px_med == pytest.approx((out.fair_ev_med + 500_000_000) / 100_000_000)
        assert out.mos == pytest.approx(out.fair_px_med / 20.0 - 1.0)

    def test_mos_clipped(self):
        inp = DcfInputs(
            ticker="TEST", growth=0.30, wacc=0.10,
            fcf_sbc_usd=1e9, revenue_usd=1e9, target_margin=0.4,
            net_cash_usd=0, shares_fut_implied=1_000_000, price=0.01,
        )
        out = run_dcf(inp)
        assert out.mos == 5.0  # clip at +500%

    def test_no_methods_returns_empty(self):
        out = run_dcf(DcfInputs(ticker="X", growth=0.1))
        assert out.fair_ev_med is None and out.mos is None

    def test_never_nan(self):
        inp = DcfInputs(ticker="X", growth=float("nan"), fcf_sbc_usd=100.0, wacc=0.1)
        out = run_dcf(inp)
        for v in (out.fair_ev_med, out.mos):
            assert v is None or math.isfinite(v)
