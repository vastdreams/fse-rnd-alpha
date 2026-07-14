"""Tests for the SIMULATED BUY robustness study (sim_proxy_v1).

Key invariants: PIT (no future bar can influence a gate), fail-closed on
missing data, and simulated rows never leak into the sealed ledger API.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from app.services.buy_simulation import (
    evaluate_gates,
    forward_return_pit,
    max_drawdown,
    newey_west_tstat,
    parse_bars,
    rebalance_dates,
    summarise_study,
    tape_event_pit,
)

ROOT = Path(__file__).resolve().parents[2]


def bars_from(start: date, closes: list[float]) -> list[dict]:
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "close": c, "volume": 1000}
        for i, c in enumerate(closes)
    ]


def test_parse_bars_drops_malformed_and_sorts():
    raw = [
        {"date": "2025-01-02", "close": 10.0},
        {"date": "2025-01-01", "close": 9.0},
        {"date": "bad", "close": 1.0},
        {"date": "2025-01-03", "close": -5.0},
        {"date": "2025-01-04"},
    ]
    parsed = parse_bars(raw)
    assert [d.isoformat() for d, _ in parsed] == ["2025-01-01", "2025-01-02"]


def test_tape_event_requires_min_bars_fail_closed():
    parsed = parse_bars(bars_from(date(2025, 1, 1), [100.0] * 39))
    assert tape_event_pit(parsed, date(2025, 3, 1)) is None


def test_tape_event_detects_pit_drawdown():
    closes = [100.0] * 30 + [70.0] * 30  # -30% drawdown
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    assert tape_event_pit(parsed, date(2025, 3, 15)) is True


def test_tape_event_ignores_future_crash():
    # Flat through as_of; crash only AFTER as_of — poisoned future bar.
    closes = [100.0] * 60 + [50.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    as_of = date(2025, 1, 1) + timedelta(days=59)  # last flat bar
    assert tape_event_pit(parsed, as_of) is False


def test_evaluate_gates_buy_happy_path():
    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    res = evaluate_gates(
        parsed=parsed,
        as_of=date(2025, 3, 15),
        mos=0.2,
        fair_px_med=90.0,
        grade="A",
        kill_active=False,
    )
    assert res["decision"] == "buy"
    assert res["gates"] == {"G1": True, "G2": True, "G3": True, "G4": True}


def test_evaluate_gates_missing_inputs_excluded_not_passed():
    res = evaluate_gates(
        parsed=[], as_of=date(2025, 3, 15), mos=None, fair_px_med=None, grade=None, kill_active=None
    )
    assert res["decision"] == "excluded"
    assert set(res["missing"]) == {"mos", "gap_inputs", "tape_bars", "vector_quality"}


def test_evaluate_gates_negative_gap_blocks():
    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    res = evaluate_gates(
        parsed=parsed,
        as_of=date(2025, 3, 15),
        mos=0.2,
        fair_px_med=60.0,  # below the 70 close → no gap
        grade="A",
        kill_active=False,
    )
    assert res["decision"] == "no_buy"
    assert res["gates"]["G2"] is False


def test_evaluate_gates_kill_or_grade_blocks():
    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    common = dict(parsed=parsed, as_of=date(2025, 3, 15), mos=0.2, fair_px_med=90.0)
    assert evaluate_gates(**common, grade="C", kill_active=False)["gates"]["G4"] is False
    assert evaluate_gates(**common, grade="A", kill_active=True)["gates"]["G4"] is False


def _v2_common(parsed):
    return dict(
        parsed=parsed,
        as_of=date(2025, 3, 15),
        mos=0.2,
        fair_px_med=90.0,
        grade="A",
        kill_active=False,
    )


def test_evaluate_gates_v2_buy_happy_path():
    from app.services.buy_simulation import evaluate_gates_v2

    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    res = evaluate_gates_v2(
        **_v2_common(parsed), rd_elig=True, survivable=True, payoff_skew=3.5
    )
    assert res["decision"] == "buy"
    assert res["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": True, "G5": True, "G6": True, "G7": True,
    }


def test_evaluate_gates_v2_thesis_gates_block():
    from app.services.buy_simulation import evaluate_gates_v2

    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    common = _v2_common(parsed)
    assert evaluate_gates_v2(**common, rd_elig=False, survivable=True, payoff_skew=3.5)["gates"]["G5"] is False
    assert evaluate_gates_v2(**common, rd_elig=True, survivable=False, payoff_skew=3.5)["gates"]["G6"] is False
    low_skew = evaluate_gates_v2(**common, rd_elig=True, survivable=True, payoff_skew=1.2)
    assert low_skew["gates"]["G7"] is False and low_skew["decision"] == "no_buy"
    # Below band passes G7 without a numeric skew.
    below = evaluate_gates_v2(
        **common, rd_elig=True, survivable=True, payoff_skew=None, payoff_skew_label="below_band"
    )
    assert below["gates"]["G7"] is True and below["decision"] == "buy"


def test_evaluate_gates_v2_missing_thesis_inputs_excluded():
    from app.services.buy_simulation import evaluate_gates_v2

    closes = [100.0] * 30 + [70.0] * 30
    parsed = parse_bars(bars_from(date(2025, 1, 1), closes))
    res = evaluate_gates_v2(
        **_v2_common(parsed), rd_elig=None, survivable=None, payoff_skew=None
    )
    assert res["decision"] == "excluded"
    assert set(res["missing"]) == {"rd_elig", "survivable", "payoff_skew"}


def test_v2_gates_contract_is_registered_and_frozen_shape():
    import json as _json

    from app.services.buy_simulation import PAYOFF_SKEW_MIN, STUDY_ID_V2

    contract = _json.loads((ROOT / "contracts" / "simulated-buy-gates-v2.json").read_text())
    assert contract["study_id"] == STUDY_ID_V2
    gate_ids = [g["id"] for g in contract["gates"]]
    assert gate_ids == ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    assert all(g.get("disclosure") for g in contract["gates"])
    assert contract["disclosures"]
    # Skew floor stays in lock-step with the thesis contract.
    thesis = _json.loads((ROOT / "contracts" / "thesis-gates.json").read_text())
    assert PAYOFF_SKEW_MIN == thesis["payoff_skew"]["min_ratio"]


def test_rebalance_dates_skips_warmup():
    days = [date(2025, 1, 2), date(2025, 1, 15), date(2025, 2, 3), date(2025, 3, 3), date(2025, 4, 1)]
    assert rebalance_dates(days, warmup_months=2) == [date(2025, 3, 3), date(2025, 4, 1)]


def test_forward_return_pit_never_enters_on_as_of_close():
    parsed = parse_bars(bars_from(date(2025, 1, 1), [100.0, 110.0, 121.0]))
    r = forward_return_pit(parsed, as_of=date(2025, 1, 1), sessions=1)
    # Entry at 110 (first close AFTER as_of), exit 121.
    assert r == pytest.approx(0.1, abs=1e-6)


def test_newey_west_needs_min_obs():
    assert newey_west_tstat([0.01] * 5) is None


def test_newey_west_zero_variance_is_none():
    assert newey_west_tstat([0.01] * 12) is None


def test_newey_west_positive_mean_tstat():
    series = [0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.0, 0.02, 0.01, -0.01, 0.03, 0.02]
    res = newey_west_tstat(series)
    assert res is not None
    assert res["n"] == 12
    assert res["mean"] == pytest.approx(sum(series) / 12, abs=1e-6)
    assert res["t_stat"] > 0


def test_max_drawdown():
    assert max_drawdown([0.1, -0.5, 0.2]) == pytest.approx(-0.5, abs=1e-6)
    assert max_drawdown([]) is None


def test_summarise_study_small_synthetic():
    bench = parse_bars(bars_from(date(2025, 1, 1), [100.0 + i * 0.1 for i in range(200)]))
    per_date = [
        {
            "as_of": date(2025, 2, 1),
            "members": ["AAA"],
            "returns": {21: {"AAA": 0.05}, 63: {"AAA": None}, 126: {"AAA": None}},
        }
    ]
    out = summarise_study(per_date=per_date, benchmark_parsed=bench)
    h21 = out["horizons"]["21s"]
    assert h21["n_rebalances"] == 1
    assert h21["mean_book_return"] == pytest.approx(0.05, abs=1e-6)
    assert h21["hit_rate"] == 1.0
    assert out["horizons"]["63s"]["mean_book_return"] is None


def test_gates_contract_is_registered_and_frozen_shape():
    import json

    contract = json.loads((ROOT / "contracts" / "simulated-buy-gates.json").read_text())
    assert contract["study_id"] == "sim_proxy_v1"
    assert [g["id"] for g in contract["gates"]] == ["G1", "G2", "G3", "G4"]
    assert contract["disclosures"], "disclosures must never be empty"
    registry = json.loads((ROOT / "contracts" / "formula-registry.json").read_text())
    assert any(f["id"] == "F_SIM_BUY_GATES" for f in registry["formulas"])


def test_sealed_api_never_serves_simulated_rows():
    """Source-contract guard: the book endpoint and the seal path are kind-aware."""
    src = (ROOT / "backend" / "app" / "api" / "routes" / "universe_company.py").read_text()
    assert src.count("kind='sealed'") >= 2, (
        "buy-performance-book SELECT and dup-check must filter kind='sealed'"
    )
    assert "note, kind)" in src and "'sealed')" in src, (
        "seal INSERT must explicitly write kind='sealed'"
    )
    seal_src = (ROOT / "scripts" / "seal_buy_set.py").read_text()
    assert "'sealed'" in seal_src
