"""
PATH: backend/tests/test_rank_engine.py
PURPOSE: Golden tests for the W2a rank engine. Encodes plan kill criteria:
- variable-N output (no fixed shortlist)
- missing values excluded, never imputed (R6 rule)
- PIT: future available_date treated as unknown
- R2 == strict Table-20 membership
- R8 segregated from FCF+ recipes
- reviewer_passed never set by ranking
"""

from datetime import date, datetime

from app.contracts.recipes import PRESET_RECIPES
from app.contracts.research import (
    MetricValue,
    MetricVector,
    ResearchCompleteness,
)
from app.services.rank_service import RankEngine, RankRequest

NOW = datetime(2026, 7, 12)
ASOF = date(2026, 7, 1)
UV = "u-test-1"


def recipe(rid):
    return next(r for r in PRESET_RECIPES if r.recipe_id == rid)


def mv(value, avail=date(2026, 6, 1)):
    if value is None:
        return MetricValue()
    return MetricValue(value=value, as_of_date=date(2026, 3, 31), available_date=avail)


def vector(ticker, **overrides):
    defaults = dict(
        ticker=ticker,
        universe_version=UV,
        computed_at=NOW,
        route="fcf_positive",
        kill_active=False,
        carve_out=False,
        table20_pass_count=12,
        mos_live=mv(0.2),
        mos_snapshot=mv(0.2),
        rd_prod=mv(0.5),
        rd_int=mv(0.15),
        rd_mom=mv(0.1),
        rd_capital=mv(0.3),
        roic=mv(0.12),
        gm=mv(0.75),
        fcfm_sbc=mv(0.18),
        rule40=mv(45.0),
        retention=mv(1.1),
        concentration=mv(0.05),
        offering_quality_z=mv(0.8),
        ret_12m=mv(0.25),
        rev_cagr=mv(0.2),
        dilution_ann=mv(0.02),
        runway_yrs=mv(5.0),
        completeness=ResearchCompleteness(
            grade="A",
            filing_fetched=True,
            claims_n=20,
            dcf_reproducible=True,
            overlay_fill_rate=0.9,
            competitor_map_filled=True,
            asof_freshness_days=5,
        ),
    )
    defaults.update(overrides)
    return MetricVector(**defaults)


ENGINE = RankEngine()


def run(rid, vectors, as_of=ASOF):
    return ENGINE.rank(vectors, RankRequest(recipe=recipe(rid), universe_version=UV, as_of=as_of))


class TestVariableN:
    def test_output_length_equals_survivors_not_fixed(self):
        vs = [vector(f"T{i}") for i in range(23)]
        rows = run("R3", vs)
        assert len(rows) == 23  # every survivor ranks — no top-10 truncation

    def test_kill_active_excluded(self):
        vs = [vector("GOOD"), vector("KILLED", kill_active=True)]
        rows = run("R3", vs)
        assert [r.ticker for r in rows] == ["GOOD"]

    def test_unknown_kill_is_excluded_fail_closed(self):
        vs = [vector("GOOD"), vector("UNKNOWN", kill_active=None)]
        rows = run("R3", vs)
        assert [r.ticker for r in rows] == ["GOOD"]


class TestMissingNeverImputed:
    def test_r6_excludes_undisclosed_retention(self):
        vs = [vector("HAS"), vector("NONE", retention=mv(None))]
        rows = run("R6", vs)
        assert [r.ticker for r in rows] == ["HAS"]

    def test_r3_excludes_missing_mos(self):
        vs = [vector("HAS"), vector("NOMOS", mos_live=mv(None))]
        rows = run("R3", vs)
        assert [r.ticker for r in rows] == ["HAS"]


class TestPointInTime:
    def test_future_available_date_is_unknown(self):
        # Retention becomes knowable AFTER the panel as_of → treated as missing → excluded from R6
        future = vector("FUT", retention=mv(1.3, avail=date(2026, 7, 15)))
        rows = run("R6", [vector("OK"), future])
        assert [r.ticker for r in rows] == ["OK"]


class TestTable20:
    def test_r2_strict_membership(self):
        vs = [
            vector("PASS12", table20_pass_count=12),
            vector("PASS11", table20_pass_count=11),
            vector("PASS6", table20_pass_count=6),
        ]
        rows = run("R2", vs)
        assert [r.ticker for r in rows] == ["PASS12"]


class TestRouteSegregation:
    def test_prefcf_never_in_fcf_recipes(self):
        vs = [vector("FCF"), vector("PRE", route="pre_fcf")]
        for rid in ["R1", "R2", "R3", "R5", "R6", "R7"]:
            tickers = [r.ticker for r in run(rid, vs)]
            assert "PRE" not in tickers, f"pre-FCF leaked into {rid}"

    def test_r8_only_prefcf(self):
        vs = [vector("FCF"), vector("PRE", route="pre_fcf")]
        rows = run("R8", vs)
        assert [r.ticker for r in rows] == ["PRE"]

    def test_r8_unknown_kill_is_excluded(self):
        vs = [vector("SAFE", route="pre_fcf"), vector("UNKNOWN", route="pre_fcf", kill_active=None)]
        rows = run("R8", vs)
        assert [r.ticker for r in rows] == ["SAFE"]


class TestScoring:
    def test_better_mos_ranks_higher_in_r6(self):
        vs = [
            vector("CHEAP", mos_live=mv(0.5), retention=mv(1.1)),
            vector("DEAR", mos_live=mv(-0.1), retention=mv(1.1)),
        ]
        rows = run("R6", vs)
        assert rows[0].ticker == "CHEAP"
        assert rows[0].rank == 1 and rows[1].rank == 2

    def test_contributions_present_for_every_axis(self):
        rows = run("R7", [vector("A"), vector("B"), vector("C")])
        for row in rows:
            assert set(row.contributions) == {"roic", "gm", "fcfm_sbc", "mos_live", "ret_12m"}

    def test_reviewer_never_set_by_engine(self):
        rows = run("R3", [vector("A"), vector("B")])
        assert all(r.reviewer_passed is None for r in rows)


class TestCompletenessSeparateAxis:
    def test_incomplete_still_ranks_but_carries_grade(self):
        inc = vector(
            "INC",
            completeness=ResearchCompleteness(
                grade="Incomplete",
                filing_fetched=False,
                claims_n=0,
                dcf_reproducible=False,
                overlay_fill_rate=0.0,
                competitor_map_filled=False,
                asof_freshness_days=None,
            ),
        )
        rows = run("R7", [vector("OK"), inc])
        by_ticker = {r.ticker: r for r in rows}
        # completeness ≠ attractiveness: INC ranks if metrics exist, grade visible
        assert by_ticker["INC"].completeness_grade == "Incomplete"

    def test_stale_flag_carried(self):
        stale = vector(
            "STALE",
            completeness=ResearchCompleteness(
                grade="B",
                filing_fetched=True,
                claims_n=10,
                dcf_reproducible=True,
                overlay_fill_rate=0.7,
                competitor_map_filled=True,
                asof_freshness_days=90,
                stale=True,
            ),
        )
        rows = run("R7", [vector("OK"), stale])
        by_ticker = {r.ticker: r for r in rows}
        assert by_ticker["STALE"].freshness_ok is False
