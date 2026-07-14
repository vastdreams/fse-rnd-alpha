"""
PATH: backend/tests/test_close_call_service.py
PURPOSE: Fail-closed stance rules — unknown catalyst / kill / weak MoS never BUY.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.contracts.research import MetricValue, MetricVector, ResearchCompleteness
from app.services.close_call_service import build_close_call_waterfall


def _mv(v: float | None) -> MetricValue:
    if v is None:
        return MetricValue()
    d = date(2026, 3, 31)
    return MetricValue(value=v, as_of_date=d, available_date=d)


def _vec(**kwargs) -> MetricVector:
    base = dict(
        ticker="TEST",
        universe_version="uv_test",
        computed_at=datetime(2026, 7, 12),
        mos_live=_mv(0.5),
        fcfm_sbc=_mv(0.12),
        rule40=_mv(0.25),
        roic=_mv(0.2),
        rev_cagr=_mv(0.05),
        kill_active=False,
        table20_pass_count=8,
        completeness=ResearchCompleteness(
            grade="B",
            filing_fetched=True,
            claims_n=5,
            dcf_reproducible=True,
            overlay_fill_rate=0.7,
            competitor_map_filled=True,
            stale=False,
        ),
    )
    base.update(kwargs)
    return MetricVector(**base)


def _bars_spike_crash() -> list[dict]:
    """Synthetic tape: grind, peak ~2025-10-20, crash through Nov — aligns EGAN anchors."""
    bars = []
    d = date(2024, 7, 1)
    end = date(2026, 7, 1)
    px = 7.0
    while d <= end:
        if d >= date(2025, 10, 1) and d <= date(2025, 10, 25):
            # ramp to peak
            px = 8.0 + (d - date(2025, 10, 1)).days * 0.3
            if d >= date(2025, 10, 18):
                px = 15.5
        elif d > date(2025, 10, 25):
            # crash toward 6.5
            days = (d - date(2025, 10, 25)).days
            px = max(6.5, 15.5 - days * 0.08)
        else:
            px = 6.8 + (d.toordinal() % 30) * 0.03
        bars.append({"date": d.isoformat(), "close": round(px, 2), "volume": 1})
        d += timedelta(days=1)
    return bars


def test_egan_with_anchors_can_buy():
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", mos_live=_mv(0.86)),
        valuation_range={"gap_to_median": 0.86, "fair_px_med": 12.24},
        price_bars=_bars_spike_crash(),
    )
    assert wf.stages[0].status == "known"  # L0
    assert wf.stages[1].status == "known"  # L1 anchors
    assert wf.stages[4].status == "known"  # L4 catalyst
    assert wf.aggregate.stance == "BUY"
    assert wf.aggregate.horizon_years in (1, 2, 3)
    assert wf.aggregate.confidence in ("med", "high")
    assert any(n["id"] == "F6" and n["result"] == "BUY" for n in wf.aggregate.flowchart)


def test_unknown_catalyst_blocks_buy():
    """Same tape + metrics but ticker not in anchor catalog → UNKNOWN, not BUY."""
    wf = build_close_call_waterfall(
        ticker="ZZZZ",
        universe_version="uv_test",
        vector=_vec(ticker="ZZZZ", mos_live=_mv(0.86)),
        valuation_range={"gap_to_median": 0.86},
        price_bars=_bars_spike_crash(),
    )
    assert wf.stages[4].status == "unknown"
    assert wf.aggregate.stance == "UNKNOWN"
    assert "Catalyst" in " ".join(wf.aggregate.blockers) or any(
        "catalyst" in b.lower() or "UNKNOWN" in b for b in wf.aggregate.blockers
    )


def test_kill_blocks_buy():
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", kill_active=True, mos_live=_mv(0.5)),
        valuation_range={"gap_to_median": 0.5},
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance == "OUT"
    assert wf.aggregate.stance != "BUY"


def test_unknown_kill_blocks_buy():
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", kill_active=None, mos_live=_mv(0.5)),
        valuation_range={"gap_to_median": 0.5},
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance == "UNKNOWN"
    assert wf.aggregate.stance != "BUY"


def test_negative_mos_is_hold_not_buy():
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", mos_live=_mv(-0.1)),
        valuation_range={"gap_to_median": -0.1},
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance in ("HOLD", "OUT")
    assert wf.aggregate.stance != "BUY"


def test_normalize_fmp_events_anchor_shape():
    from app.services.catalyst_event_service import normalize_fmp_events

    anchors = normalize_fmp_events(
        "ACME",
        press=[{"title": "ACME wins deal", "publishedDate": "2025-11-01", "url": "https://ex/1"}],
        earnings=[{"date": "2025-10-28", "epsActual": 0.4, "epsEstimated": 0.3}],
        news=[{"title": "Wire blurb", "publishedDate": "2025-11-02", "url": "https://ex/2"}],
    )
    assert len(anchors) == 3
    kinds = {a["kind"] for a in anchors}
    assert kinds == {"press_coverage", "earnings_release"}
    for a in anchors:
        assert a["ticker"] == "ACME"
        assert a["date"]
        assert a["title"]
        assert a["source"]
        assert a["locator"]


def test_non_date_labels_never_become_catalyst_anchors():
    from app.services.catalyst_event_service import anchors_from_claim_locator, normalize_fmp_events

    anchors = normalize_fmp_events(
        "ACME",
        press=[{"title": "Quarterly update", "publishedDate": "2025Q3"}],
        earnings=[{"date": "2025Q3"}],
    )
    assert anchors == []
    assert (
        anchors_from_claim_locator(
            "Transcript quarter label",
            {"date": "2025Q3", "source": "av_transcripts_raw"},
        )
        is None
    )


def test_window_filter_drops_out_of_window_cached_anchors(tmp_path, monkeypatch):
    from app.services import catalyst_event_service as ces
    from app.services.close_call_service import _anchors_for

    monkeypatch.setattr(ces, "CACHE_DIR", tmp_path)
    ces._memory.clear()
    ces.write_cache(
        "ZZZZ",
        [
            {
                "ticker": "ZZZZ",
                "date": "2020-01-01",
                "kind": "press_coverage",
                "title": "Ancient news",
                "locator": "x",
                "source": "fmp_press_releases",
            },
            {
                "ticker": "ZZZZ",
                "date": "2025-11-05",
                "kind": "earnings_release",
                "title": "In-window earnings",
                "locator": "y",
                "source": "fmp_earnings",
            },
        ],
    )
    event = {
        "peak_date": "2025-10-20",
        "trough_date": "2025-11-15",
        "drawdown": -0.4,
    }
    kept, miss = _anchors_for("ZZZZ", event, include_cached=True)
    assert miss == ""
    assert len(kept) == 1
    assert kept[0]["title"] == "In-window earnings"


def test_cached_anchors_plus_l0_yields_l1_l4_known(tmp_path, monkeypatch):
    from app.services import catalyst_event_service as ces

    monkeypatch.setattr(ces, "CACHE_DIR", tmp_path)
    ces._memory.clear()
    # Align with synthetic tape peak ~2025-10-20, trough in Nov
    ces.write_cache(
        "CACH",
        [
            {
                "ticker": "CACH",
                "date": "2025-11-06",
                "kind": "press_coverage",
                "title": "CACH guidance cut",
                "locator": "https://ex/cach",
                "source": "fmp_press_releases",
            }
        ],
    )
    wf = build_close_call_waterfall(
        ticker="CACH",
        universe_version="uv_test",
        vector=_vec(ticker="CACH", mos_live=_mv(0.86)),
        valuation_range={"gap_to_median": 0.86, "fair_px_med": 12.24},
        price_bars=_bars_spike_crash(),
        include_cached_anchors=True,
    )
    assert wf.stages[0].status == "known"
    assert wf.stages[1].status == "known"
    assert wf.stages[4].status == "known"
    assert wf.aggregate.stance == "BUY"


def test_missing_cached_anchors_stay_unknown(tmp_path, monkeypatch):
    from app.services import catalyst_event_service as ces

    monkeypatch.setattr(ces, "CACHE_DIR", tmp_path)
    ces._memory.clear()
    wf = build_close_call_waterfall(
        ticker="NOAN",
        universe_version="uv_test",
        vector=_vec(ticker="NOAN", mos_live=_mv(0.86)),
        valuation_range={"gap_to_median": 0.86},
        price_bars=_bars_spike_crash(),
    )
    assert wf.stages[1].status == "unknown"
    assert wf.stages[4].status == "unknown"
    assert wf.aggregate.stance == "UNKNOWN"


def test_db_claim_anchors_via_extra_pass_l1():
    from app.services.catalyst_event_service import anchors_from_claim_locator

    a = anchors_from_claim_locator(
        "SEC 8-K: Results",
        {
            "date": "2025-11-06",
            "kind": "8-K",
            "locator": "https://sec.gov/x",
            "source": "sec_edgar",
            "role": "sec_event",
        },
    )
    assert a is not None
    wf = build_close_call_waterfall(
        ticker="DBCL",
        universe_version="uv_test",
        vector=_vec(ticker="DBCL", mos_live=_mv(0.86)),
        valuation_range={"gap_to_median": 0.86, "fair_px_med": 12.24},
        price_bars=_bars_spike_crash(),
        extra_anchors=[a],
    )
    assert wf.stages[1].status == "known"
    assert wf.stages[4].status == "known"


def test_live_gap_closed_blocks_buy_despite_sealed_mos():
    """Sealed MoS+ is not enough when live vs-target has already closed."""
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", mos_live=_mv(0.50)),
        valuation_range={"gap_to_median": -0.05, "fair_px_med": 12.24, "price_live": 13.0},
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance == "HOLD"
    assert any(n["id"] == "F3b" and n["result"] == "FAIL" for n in wf.aggregate.flowchart)
    assert any("tape" in b.lower() or "vs-target" in b.lower() for b in wf.aggregate.blockers)


def test_missing_live_gap_is_unknown_not_buy():
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", mos_live=_mv(0.86)),
        valuation_range={"fair_px_med": 12.24},  # no gap_to_median
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance == "UNKNOWN"
    assert any(n["id"] == "F3b" and n["result"] == "UNKNOWN" for n in wf.aggregate.flowchart)


def test_stale_quote_gap_is_unknown_not_pass():
    """A >30d-old cached quote must not clear the live F3b gate."""
    wf = build_close_call_waterfall(
        ticker="EGAN",
        universe_version="uv_test",
        vector=_vec(ticker="EGAN", mos_live=_mv(0.86)),
        valuation_range={
            "gap_to_median": 0.40,
            "fair_px_med": 12.24,
            "price_live": 9.0,
            "price_stale": True,
        },
        price_bars=_bars_spike_crash(),
    )
    assert wf.aggregate.stance != "BUY"
    assert any(n["id"] == "F3b" and n["result"] == "UNKNOWN" for n in wf.aggregate.flowchart)
