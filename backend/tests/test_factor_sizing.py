"""Tests for the validated-evidence sizing bound and falsification status."""

from __future__ import annotations

import pytest

from app.services.factor_sizing import (
    f_max,
    falsification_status,
    load_factor_premium,
    mu_claim_pct,
    sizing_payload,
)


def test_frozen_headline_numbers_give_zero_bound():
    """λ=3.73, SE=3.38 → 3.73 − 1.96·3.38 < 0 → μ_claim = 0 → f_max = 0."""
    c = load_factor_premium()
    assert c["sizing_series"] == "annual_hml_premium"
    assert mu_claim_pct(c) == 0.0
    assert f_max(sigma_book_sq=0.02, n_sealed_months=48, contract=c) == 0.0


def test_positive_bound_with_synthetic_significant_series():
    synthetic = {
        "sizing_series": "annual_hml_premium",
        "series": {
            "annual_hml_premium": {
                "mean_pct_per_year": 6.0,
                "nw_std_error": 2.0,
                "t_statistic": 3.0,
            }
        },
    }
    # mu = 6 − 1.96·2 = 2.08%/yr = 0.0208
    assert mu_claim_pct(synthetic) == pytest.approx(2.08)
    bound = f_max(sigma_book_sq=0.04, n_sealed_months=24, contract=synthetic)
    assert bound == pytest.approx(0.25 * 0.0208 / 0.04)


def test_unknown_variance_or_short_ledger_never_unlocks_size():
    synthetic = {
        "sizing_series": "s",
        "series": {"s": {"mean_pct_per_year": 6.0, "nw_std_error": 2.0}},
    }
    assert f_max(None, 48, synthetic) == 0.0
    assert f_max(0.04, 6, synthetic) == 0.0
    assert f_max(0.0, 48, synthetic) == 0.0


def test_sizing_payload_says_no_edge_plainly():
    p = sizing_payload(sigma_book_sq=None, n_sealed_months=0)
    assert p["f_max_fraction"] == 0.0
    assert "No validated edge, no size" in p["verdict"]
    assert p["why_zero"]
    # Both frozen series present, with roles
    assert "annual_hml_premium" in p["series"]
    assert "rd_factor_premium" in p["series"]
    assert p["series"]["rd_factor_premium"]["role"].startswith("SUPPORTING")


def test_falsification_rules_registered_and_not_yet_evaluable():
    rules = falsification_status(n_sealed_months=1)
    ids = {r["id"] for r in rules}
    assert ids == {"R1_FACTOR_DECAY", "R2_LEDGER_FAILURE", "R3_CALIBRATION"}
    for r in rules:
        assert r["status"] == "armed_not_yet_evaluable"
        assert r["consequence"]


def test_falsification_rules_evaluate_when_inputs_exist():
    rules = falsification_status(
        n_sealed_months=40, ledger_excess_t=-0.5, rolling_factor_t=1.4
    )
    by_id = {r["id"]: r for r in rules}
    assert by_id["R1_FACTOR_DECAY"]["status"] == "armed_passing"
    assert by_id["R2_LEDGER_FAILURE"]["status"] == "breached"


def test_books_max_factor_sizing_breach():
    from app.api.routes.books import evaluate_breaches
    from app.contracts.research import BookConstraint, BookHolding

    from datetime import datetime

    now = datetime(2026, 7, 14)
    holdings = [
        BookHolding(ticker="AAA", weight_pct=10.0, added_at=now),
        BookHolding(ticker="BBB", weight_pct=5.0, added_at=now),
    ]
    flags = {
        "AAA": {"stance": "BUY", "kill_active": False, "completeness_grade": "A"},
        "BBB": {"stance": "HOLD", "kill_active": False, "completeness_grade": "A"},
    }
    # Zero validated bound no longer blocks construction weights.
    breaches_zero = evaluate_breaches(
        holdings, [BookConstraint(kind="max_factor_sizing")], flags
    )
    assert not [b for b in breaches_zero if b["kind"] == "max_factor_sizing"]

    # Positive explicit limit still walls off overweight BUY books.
    breaches = evaluate_breaches(
        holdings, [BookConstraint(kind="max_factor_sizing", limit=5.0)], flags
    )
    sizing = [b for b in breaches if b["kind"] == "max_factor_sizing"]
    assert len(sizing) == 1 and sizing[0]["ticker"] == "AAA"
    assert "validated bound" in sizing[0]["detail"]

    holdings[0].override_reason = "manual sizing accepted"
    breaches2 = evaluate_breaches(
        holdings, [BookConstraint(kind="max_factor_sizing", limit=5.0)], flags
    )
    assert not [b for b in breaches2 if b["kind"] == "max_factor_sizing"]
