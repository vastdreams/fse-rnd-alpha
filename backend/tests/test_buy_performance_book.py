"""PATH: backend/tests/test_buy_performance_book.py — PIT BUY forward maths."""

from datetime import date, timedelta

from app.services.buy_performance_book import (
    empty_book_payload,
    equal_weight_book_return,
    forward_return,
    hit_rate,
    summarise_snapshot,
)


def _bars(start: date, n: int, p0: float = 100.0, step: float = 1.0):
    out = []
    px = p0
    for i in range(n):
        out.append({"date": (start + timedelta(days=i)).isoformat(), "close": px, "volume": 1})
        px += step
    return out


def test_forward_return_and_book_stats():
    as_of = date(2026, 1, 1)
    bars = _bars(as_of, 40, p0=100.0, step=1.0)
    r = forward_return(bars, as_of=as_of, sessions=21)
    # Entry is the first close strictly AFTER as_of (101.0), never the as_of
    # close itself — seals happen intraday, so that close is look-ahead.
    assert r is not None and abs(r - (122.0 / 101.0 - 1.0)) < 1e-6
    assert equal_weight_book_return([0.1, 0.2, None]) == 0.15
    assert hit_rate([0.1, -0.2, None]) == 0.5


def test_forward_return_never_enters_on_as_of_close():
    as_of = date(2026, 1, 1)
    bars = _bars(as_of, 5)
    # Only bars up to and including as_of → no PIT-valid entry.
    assert forward_return(bars[:1], as_of=as_of, sessions=1) is None


def test_empty_payload_is_honest():
    p = empty_book_payload(universe_version="uv_x")
    assert p["status"] == "empty"
    assert "HML_RD" in p["note"]
    assert p["summary"] is None


def test_summarise_snapshot_reports_missing():
    as_of = date(2026, 1, 1)
    summary = summarise_snapshot(
        as_of=as_of,
        universe_version="uv_x",
        members=[{"ticker": "AAA"}, {"ticker": "BBB"}],
        bars_by_ticker={"AAA": _bars(as_of, 30)},
    )
    assert summary["horizon_unit"] == "trading_sessions"
    h21 = summary["horizons"]["21s"]
    assert h21["n_observed"] == 1
    assert h21["n_missing"] == 1
