"""Tests for the thesis-field maths (contracts/thesis-gates.json)."""

from __future__ import annotations

import pytest

from app.services.thesis_fields import (
    compute_thesis_fields,
    load_thesis_contract,
    payoff_skew,
    rd_composite_scores,
    rd_eligibility,
    survivability,
    weave_composite,
    weave_z_scores,
)


def _row(**kw):
    base = {
        "rd_int": None,
        "rd_capital": None,
        "rd_prod": None,
        "rd_mom": None,
        "roic": None,
        "gm": None,
        "fcfm_sbc": None,
        "rule40": None,
        "runway_yrs": None,
        "dilution_ann": None,
        "retention": None,
        "mos_live": None,
        "ret_3m": None,
        "ret_12m": None,
        "drawdown_from_peak": None,
        "price": None,
        "fair_px_lo": None,
        "fair_px_hi": None,
    }
    base.update(kw)
    return base


def test_contract_loads_and_is_sealed_shape():
    c = load_thesis_contract()
    assert c["id"] == "THESIS_GATES_V1"
    assert c["rd_composite"]["eligibility_quantile"] == 0.8
    assert abs(sum(c["weave_weights"][k] for k in ("z_rd", "z_quality", "z_valuation", "z_momentum")) - 1.0) < 1e-9


def test_rd_composite_requires_min_known_components():
    rows = [
        _row(rd_int=0.5, rd_capital=2.0, rd_prod=1.0, rd_mom=0.1),
        _row(rd_int=0.1),  # only 1 of 4 known -> UNKNOWN
        _row(rd_int=0.3, rd_prod=0.5),
        _row(rd_int=0.2, rd_capital=1.0, rd_prod=0.6, rd_mom=0.0),
        _row(rd_int=0.05, rd_capital=0.5, rd_prod=0.2, rd_mom=-0.1),
    ]
    scores = rd_composite_scores(rows)
    assert scores[1] is None
    assert scores[0] is not None and scores[4] is not None
    assert scores[0] > scores[4]  # higher R&D everywhere -> higher composite


def test_rd_eligibility_top_quintile_and_unknown_propagates():
    composites = [1.0, 0.5, 0.2, 0.0, -0.5, -1.0, -1.5, -2.0, 0.8, None]
    elig = rd_eligibility(composites)
    assert elig[-1] is None  # UNKNOWN stays UNKNOWN
    # 9 known values, q=0.8 -> cut index ceil(0.8*9)=8 -> only the max is eligible
    assert elig[0] is True
    assert sum(1 for e in elig[:-1] if e) == 1


def test_survivability_floors_pass_fail_unknown():
    # Pass: FCF positive, runway unknown tolerated, dilution/retention fine
    assert survivability(_row(fcfm_sbc=0.05, dilution_ann=0.03, retention=0.95)) is True
    # Fail: cash engine broken
    assert survivability(_row(fcfm_sbc=-0.10, rule40=20.0, dilution_ann=0.03, runway_yrs=3.0)) is False
    # Fail: dilution above ceiling
    assert survivability(_row(fcfm_sbc=0.05, dilution_ann=0.15, retention=0.95)) is False
    # Fail: retention below floor
    assert survivability(_row(fcfm_sbc=0.05, dilution_ann=0.03, retention=0.70)) is False
    # UNKNOWN: cash engine entirely unknown
    assert survivability(_row(dilution_ann=0.03)) is None
    # UNKNOWN: pre-FCF with unknown runway (tolerance only applies when FCF>0)
    assert survivability(_row(fcfm_sbc=-0.02, rule40=45.0, dilution_ann=0.03)) is None
    # UNKNOWN: dilution unknown blocks a survivability verdict
    assert survivability(_row(fcfm_sbc=0.05, retention=0.95)) is None
    # Fail: runway below floor even with rule40 pass
    assert survivability(_row(fcfm_sbc=-0.02, rule40=50.0, runway_yrs=1.0, dilution_ann=0.02)) is False


def test_payoff_skew_ratio_below_band_and_degenerate():
    ratio, label = payoff_skew(price=10.0, fair_px_lo=8.0, fair_px_hi=18.0)
    assert ratio == pytest.approx(4.0)
    assert label is None
    # Below band: favourable but undefined
    ratio, label = payoff_skew(price=7.0, fair_px_lo=8.0, fair_px_hi=18.0)
    assert ratio is None and label == "below_band"
    # Above band: zero upside
    ratio, label = payoff_skew(price=20.0, fair_px_lo=8.0, fair_px_hi=18.0)
    assert ratio == 0.0 and label is None
    # Degenerate / inverted band -> UNKNOWN
    assert payoff_skew(price=10.0, fair_px_lo=12.0, fair_px_hi=12.0) == (None, None)
    # Missing inputs -> UNKNOWN
    assert payoff_skew(price=None, fair_px_lo=8.0, fair_px_hi=18.0) == (None, None)


def test_weave_missing_family_contributes_zero_and_flags_partial():
    score, partial = weave_composite({"z_rd": 1.0, "z_quality": None, "z_valuation": 0.5, "z_momentum": 0.0})
    c = load_thesis_contract()["weave_weights"]
    assert partial is True
    assert score == pytest.approx(c["z_rd"] * 1.0 + c["z_valuation"] * 0.5)


def test_weave_momentum_inverts_drawdown():
    rows = [
        _row(ret_3m=0.1, ret_12m=0.2, drawdown_from_peak=-0.05),  # shallow drawdown
        _row(ret_3m=0.1, ret_12m=0.2, drawdown_from_peak=-0.60),  # deep drawdown
        _row(ret_3m=0.1, ret_12m=0.2, drawdown_from_peak=-0.30),
    ]
    z = weave_z_scores(rows, [None, None, None])
    assert z[0]["z_momentum"] > z[1]["z_momentum"]


def test_compute_thesis_fields_end_to_end_unknowns_fail_closed():
    rows = [
        _row(
            rd_int=0.5, rd_capital=2.0, rd_prod=1.0, rd_mom=0.1,
            fcfm_sbc=0.05, dilution_ann=0.03, retention=0.95,
            price=10.0, fair_px_lo=8.0, fair_px_hi=18.0, mos_live=0.4,
        ),
        _row(),  # everything unknown
        _row(rd_int=0.05, rd_capital=0.1, rd_prod=0.1, rd_mom=0.0, fcfm_sbc=-0.2),
    ]
    out = compute_thesis_fields(rows)
    assert out[1]["rd_composite"] is None
    assert out[1]["rd_elig"] is None
    assert out[1]["survivable"] is None
    assert out[1]["payoff_skew"] is None
    assert out[0]["survivable"] is True
    assert out[0]["payoff_skew"] == pytest.approx(4.0)
    assert out[2]["survivable"] is False
