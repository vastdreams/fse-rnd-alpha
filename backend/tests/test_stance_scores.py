"""
PATH: backend/tests/test_stance_scores.py
PURPOSE: Golden-pin stance sub-score curves (gap #10).
"""

from app.services.stance_scores import (
    aggregate_stance_score,
    clip10,
    score_fcfm,
    score_roic,
    score_rule40,
    score_valuation_from_gap,
)


def test_clip10():
    assert clip10(-1) == 0.0
    assert clip10(11) == 10.0
    # Python round uses banker's rounding: 5.555 → 5.55
    assert clip10(5.555) == 5.55
    assert clip10(5.556) == 5.56


def test_valuation_curve_golden():
    assert score_valuation_from_gap(0.0) == 5.0
    assert score_valuation_from_gap(0.5) == 8.5
    assert score_valuation_from_gap(1.0) == 10.0
    assert score_valuation_from_gap(-0.5) == 1.5


def test_fcfm_rule40_roic_curves():
    assert score_fcfm(0.0) == 3.0
    assert score_fcfm(0.15) == 9.0
    assert score_fcfm(0.25) == 10.0
    assert score_rule40(0.4) == 6.0
    assert abs(score_rule40(0.67) - 10.0) < 0.1
    assert score_roic(0.2) == 4.4
    assert score_roic(0.5) == 8.0


def test_aggregate_coverage_penalty():
    # Two equal weights, one missing → coverage 0.5
    agg = aggregate_stance_score([(1.0, 8.0), (1.0, None)])
    assert agg == round(8.0 * 10.0 * 0.5, 1) == 40.0
    assert aggregate_stance_score([(1.0, None)]) is None
    full = aggregate_stance_score([(0.3, 8.0), (0.7, 6.0)])
    assert full == round(((0.3 * 8 + 0.7 * 6) / 1.0) * 10.0 * 1.0, 1)
