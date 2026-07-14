"""Tests for the cleared-BUY construction sizing proxy."""

from app.services.sizing_proxy import load_sizing_proxy, proxy_weights, raw_score, waterfill_weights


def test_contract_loads():
    c = load_sizing_proxy()
    assert c["id"] == "SIZING_PROXY_V1"
    assert c["per_name_cap_pct"] == 15.0
    assert abs(sum(v["weight"] for v in c["inputs"].values()) - 1.0) < 1e-9


def test_below_band_beats_zero_skew():
    below = raw_score(
        weave_score=1.0,
        stance_score=80,
        mos_live=0.5,
        payoff_skew=None,
        payoff_skew_label="below_band",
    )
    zero = raw_score(
        weave_score=1.0,
        stance_score=80,
        mos_live=0.5,
        payoff_skew=0.0,
        payoff_skew_label=None,
    )
    assert below > zero


def test_non_buy_excluded_and_weights_cap():
    rows = [
        {
            "ticker": "AAA",
            "stance": "BUY",
            "weave_score": 1.5,
            "score": 85,
            "mos_live": 1.0,
            "payoff_skew_label": "below_band",
        },
        {
            "ticker": "BBB",
            "stance": "BUY",
            "weave_score": 0.5,
            "score": 70,
            "mos_live": 0.2,
            "payoff_skew": 4.0,
        },
        {
            "ticker": "CCC",
            "stance": "HOLD",
            "weave_score": 9.0,
            "score": 99,
            "mos_live": 2.0,
            "payoff_skew_label": "below_band",
        },
    ]
    # Pad with weaker BUYs so the book can fill to 100% under the 15% cap.
    for i in range(6):
        rows.append(
            {
                "ticker": f"W{i}",
                "stance": "BUY",
                "weave_score": 0.05,
                "score": 66,
                "mos_live": 0.05,
                "payoff_skew": 3.0,
            }
        )
    out = proxy_weights(rows)
    tickers = {h["ticker"] for h in out["holdings"]}
    assert "CCC" not in tickers
    assert "AAA" in tickers and "BBB" in tickers
    assert abs(out["weights_sum_pct"] - 100.0) < 0.05
    assert all(h["weight_pct"] <= 15.0 + 1e-9 for h in out["holdings"])
    by = {h["ticker"]: h["weight_pct"] for h in out["holdings"]}
    assert by["AAA"] > by["BBB"]


def test_waterfill_respects_cap_with_many_names():
    # 10 equal raw scores → each would want 10%, under the 15% cap → all 10%.
    w = waterfill_weights([1.0] * 10, cap_pct=15.0, target_sum_pct=100.0)
    assert abs(sum(w) - 100.0) < 0.05
    assert all(abs(x - 10.0) < 0.05 for x in w)

    # 4 equal → each 25% uncapped, but cap 15 → each 15, sum 60.
    w2 = waterfill_weights([1.0] * 4, cap_pct=15.0, target_sum_pct=100.0)
    assert all(abs(x - 15.0) < 0.05 for x in w2)
    assert abs(sum(w2) - 60.0) < 0.05


def test_zero_bound_no_longer_blocks_buy_weights():
    from datetime import datetime

    from app.api.routes.books import evaluate_breaches
    from app.contracts.research import BookConstraint, BookHolding

    now = datetime(2026, 7, 14)
    holdings = [
        BookHolding(ticker="AAA", weight_pct=15.0, added_at=now),
        BookHolding(ticker="BBB", weight_pct=15.0, added_at=now),
    ]
    flags = {
        "AAA": {"stance": "BUY", "kill_active": False, "completeness_grade": "A"},
        "BBB": {"stance": "BUY", "kill_active": False, "completeness_grade": "A"},
    }
    # Default contract bound is 0 → construction proxy path → no breach.
    breaches = evaluate_breaches(
        holdings, [BookConstraint(kind="max_factor_sizing")], flags
    )
    assert not [b for b in breaches if b["kind"] == "max_factor_sizing"]

    # Explicit positive limit still enforces.
    breaches2 = evaluate_breaches(
        holdings, [BookConstraint(kind="max_factor_sizing", limit=10.0)], flags
    )
    assert [b for b in breaches2 if b["kind"] == "max_factor_sizing"]
