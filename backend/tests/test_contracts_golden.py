"""
PATH: backend/tests/test_contracts_golden.py
PURPOSE: Golden tests for W1 contracts — these encode the locked ship rules.
If any of these fail, the corresponding kill criterion in the redesign plan
has been violated. Do not weaken assertions to make code pass.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.contracts.research import (
    BookHolding,
    DeepSeekAuditRun,
    DeepSeekOutputKind,
    FinalReview,
    MetricValue,
    MetricVector,
    RankedRow,
    RankRecipe,
    ResearchCompleteness,
    SavedBook,
    SourceKind,
    SourceSnapshot,
)

NOW = datetime(2026, 7, 12, 0, 0, 0)


def _completeness(**kw):
    base = dict(
        grade="B",
        filing_fetched=True,
        claims_n=12,
        dcf_reproducible=True,
        overlay_fill_rate=0.8,
        competitor_map_filled=True,
        asof_freshness_days=10,
    )
    base.update(kw)
    return ResearchCompleteness(**base)


# ---------------------------------------------------------------------------
# PIT / look-ahead
# ---------------------------------------------------------------------------

class TestPointInTime:
    def test_source_snapshot_rejects_lookahead(self):
        with pytest.raises(ValidationError):
            SourceSnapshot(
                snapshot_id="s1",
                kind=SourceKind.SEC_10K,
                ticker="FRSH",
                as_of_date=date(2026, 1, 31),
                available_date=date(2025, 12, 1),  # knowable before period end = nonsense
                fetched_at=NOW,
                locator="0001834255-26-000012",
                content_sha256="deadbeef",
            )

    def test_metric_value_requires_pit_pair(self):
        with pytest.raises(ValidationError):
            MetricValue(value=0.53)  # value without PIT dates is forbidden

    def test_metric_value_unknown_is_legal(self):
        mv = MetricValue()  # Unknown stays Unknown — never imputed
        assert mv.value is None

    def test_metric_value_rejects_available_before_asof(self):
        with pytest.raises(ValidationError):
            MetricValue(
                value=1.0,
                as_of_date=date(2026, 3, 31),
                available_date=date(2026, 2, 1),
            )


# ---------------------------------------------------------------------------
# DeepSeek scope — map only, never metric values
# ---------------------------------------------------------------------------

class TestDeepSeekScope:
    def test_output_kinds_exclude_metric_value(self):
        kinds = {k.value for k in DeepSeekOutputKind}
        assert "metric_value" not in kinds
        assert kinds == {"ai_map", "ai_gap", "ai_runthrough", "ai_peer_propose", "ai_consistency"}

    def test_run_cannot_claim_metric_kind(self):
        with pytest.raises(ValidationError):
            DeepSeekAuditRun(
                run_id="d1",
                job="filing_map",
                ticker="DOCU",
                output_kind="metric_value",  # type: ignore[arg-type]
                output={},
                started_at=NOW,
            )

    def test_valid_map_run(self):
        run = DeepSeekAuditRun(
            run_id="d2",
            job="filing_map",
            ticker="DOCU",
            output_kind=DeepSeekOutputKind.AI_MAP,
            output={"item1": {"locator": "Item 1, para 3"}},
            started_at=NOW,
        )
        assert run.status == "pending"


# ---------------------------------------------------------------------------
# Reviewer path — reviewer_passed only via FinalReview
# ---------------------------------------------------------------------------

class TestFinalReview:
    def test_ranked_row_defaults_unreviewed(self):
        row = RankedRow(
            ticker="PCTY",
            recipe_id="R3",
            universe_version="u-2026-07-12",
            rank=1,
            score=0.91,
            contributions={"rd_prod": 0.4, "mos_live": 0.51},
            completeness_grade="A",
            freshness_ok=True,
            kill_active=False,
        )
        assert row.reviewer_passed is None  # unreviewed by default, never True

    def test_final_review_requires_trigger(self):
        with pytest.raises(ValidationError):
            FinalReview(
                review_id="r1",
                trigger="because_i_said_so",  # type: ignore[arg-type]
                checklist={},
                passed=True,
                reviewed_at=NOW,
            )


# ---------------------------------------------------------------------------
# Recipes — formula must always be present
# ---------------------------------------------------------------------------

class TestRecipes:
    def test_recipe_requires_both_formulas(self):
        with pytest.raises(ValidationError):
            RankRecipe(  # type: ignore[call-arg]
                recipe_id="R3",
                name="Sustainable-moat underpriced",
                # formula_human / formula_exact missing on purpose
                axes=["rd_prod", "mos_live"],
                benchmark_vs="vs high rd_int low rd_prod",
            )

    def test_all_nine_recipe_ids_valid(self):
        for i in range(1, 10):
            r = RankRecipe(
                recipe_id=f"R{i}",  # type: ignore[arg-type]
                name=f"recipe {i}",
                formula_human="one-liner",
                formula_exact="expr",
                axes=["mos_live"],
                benchmark_vs="benchmark",
            )
            assert r.recipe_id == f"R{i}"


# ---------------------------------------------------------------------------
# Metric vector — completeness is mandatory, missing stays missing
# ---------------------------------------------------------------------------

class TestMetricVector:
    def test_vector_requires_completeness(self):
        with pytest.raises(ValidationError):
            MetricVector(  # type: ignore[call-arg]
                ticker="WDAY",
                universe_version="u-2026-07-12",
                computed_at=NOW,
            )

    def test_vector_with_unknowns(self):
        v = MetricVector(
            ticker="WDAY",
            universe_version="u-2026-07-12",
            computed_at=NOW,
            completeness=_completeness(grade="Incomplete", overlay_fill_rate=0.2),
        )
        assert v.retention.value is None
        assert v.completeness.grade == "Incomplete"


# ---------------------------------------------------------------------------
# Book — no auto-seed, weights sane, override required text
# ---------------------------------------------------------------------------

class TestSavedBook:
    def _book(self, holdings):
        return SavedBook(
            book_id="b1",
            user_id="u1",
            name="My Book",
            holdings=holdings,
            created_at=NOW,
            updated_at=NOW,
        )

    def test_book_starts_empty(self):
        book = self._book([])
        assert book.holdings == []

    def test_weights_over_100_rejected(self):
        holdings = [
            BookHolding(ticker="FRSH", weight_pct=60, added_at=NOW),
            BookHolding(ticker="PCTY", weight_pct=50, added_at=NOW),
        ]
        with pytest.raises(ValidationError):
            self._book(holdings)

    def test_valid_weighted_book(self):
        holdings = [
            BookHolding(ticker="FRSH", weight_pct=60, added_at=NOW),
            BookHolding(ticker="PCTY", weight_pct=40, added_at=NOW),
        ]
        book = self._book(holdings)
        assert book.research_only_ack is True
