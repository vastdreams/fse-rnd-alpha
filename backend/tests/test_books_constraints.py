"""
PATH: backend/tests/test_books_constraints.py
PURPOSE: W5 — the breach wall must block: kill-active names, overweights,
stale names, and Incomplete overweight; overrides are the only way through.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.api.routes.books import DEFAULT_CONSTRAINTS, _db_timestamp, evaluate_breaches
from app.contracts.research import BookConstraint, BookHolding

NOW = datetime(2026, 7, 12)


def h(ticker: str, w: float, override: Optional[str] = None) -> BookHolding:
    return BookHolding(ticker=ticker, weight_pct=w, added_at=NOW, override_reason=override)


class TestBreachWall:
    def test_normalizes_public_iso_timestamp_to_legacy_utc_column(self):
        assert _db_timestamp(
            datetime(2026, 7, 12, 10, tzinfo=timezone(timedelta(hours=10)))
        ) == datetime(
            2026, 7, 12, 0
        )

    def test_kill_active_blocks(self):
        flags = {"WDAY": {"kill_active": True, "completeness_grade": "A", "stale": False}}
        breaches = evaluate_breaches([h("WDAY", 10)], DEFAULT_CONSTRAINTS, flags)
        assert any(b["kind"] == "ban_kill_active" for b in breaches)

    def test_kill_active_override_passes(self):
        flags = {"WDAY": {"kill_active": True, "completeness_grade": "A", "stale": False}}
        breaches = evaluate_breaches([h("WDAY", 10, "accepting kill risk, thesis X")], DEFAULT_CONSTRAINTS, flags)
        assert not any(b["kind"] == "ban_kill_active" for b in breaches)

    def test_unknown_kill_blocks_fail_closed(self):
        flags = {"UNKNOWN": {"kill_active": None, "completeness_grade": "A", "stale": False}}
        breaches = evaluate_breaches([h("UNKNOWN", 10)], DEFAULT_CONSTRAINTS, flags)
        assert any(b["kind"] == "ban_kill_active" for b in breaches)

    def test_overweight_blocks(self):
        breaches = evaluate_breaches([h("FRSH", 50)], DEFAULT_CONSTRAINTS, {})
        assert any(b["kind"] == "max_name_pct" for b in breaches)

    def test_stale_blocks_without_override(self):
        flags = {"OLD": {"kill_active": False, "completeness_grade": "B", "stale": True}}
        breaches = evaluate_breaches([h("OLD", 5)], DEFAULT_CONSTRAINTS, flags)
        assert any(b["kind"] == "stale" for b in breaches)

    def test_incomplete_cap(self):
        flags = {
            "INC1": {"kill_active": False, "completeness_grade": "Incomplete", "stale": False},
            "INC2": {"kill_active": False, "completeness_grade": "Incomplete", "stale": False},
        }
        breaches = evaluate_breaches(
            [h("INC1", 15), h("INC2", 15)],
            [BookConstraint(kind="max_incomplete_pct", limit=20.0)],
            flags,
        )
        assert any(b["kind"] == "max_incomplete_pct" for b in breaches)

    def test_clean_book_passes(self):
        flags = {"FRSH": {"kill_active": False, "completeness_grade": "A", "stale": False}}
        assert evaluate_breaches([h("FRSH", 10)], DEFAULT_CONSTRAINTS, flags) == []

    def test_weights_over_100_block(self):
        breaches = evaluate_breaches([h("A1", 60), h("B2", 60)], [], {})
        assert any(b["kind"] == "weights_sum" for b in breaches)

    def test_disabled_constraint_ignored(self):
        c = [BookConstraint(kind="max_name_pct", limit=15.0, enabled=False)]
        flags = {"FRSH": {"kill_active": False, "stale": False}}
        assert evaluate_breaches([h("FRSH", 50)], c, flags) == []

    def test_unknown_kill_and_freshness_remain_fail_closed_when_hidden(self):
        constraints = [BookConstraint(kind="ban_kill_active", enabled=False)]
        breaches = evaluate_breaches([h("UNKNOWN", 10)], constraints, {})

        assert {breach["kind"] for breach in breaches} == {"ban_kill_active", "stale"}

    def test_unknown_incomplete_grade_counts_against_cap(self):
        breaches = evaluate_breaches(
            [h("UNV1", 15), h("UNV2", 15)],
            [BookConstraint(kind="max_incomplete_pct", limit=20.0)],
            {
                "UNV1": {"kill_active": False, "stale": False},
                "UNV2": {"kill_active": False, "stale": False},
            },
        )

        assert any(breach["kind"] == "max_incomplete_pct" for breach in breaches)
