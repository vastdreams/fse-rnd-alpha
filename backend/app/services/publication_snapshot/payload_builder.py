# EXEMPTION: 824 lines — Irreducible data-assembly pipeline; splitting would fragment the snapshot build flow
"""
PATH: backend/app/services/publication_snapshot/payload_builder.py
PURPOSE: Builds the full snapshot payload by reading current database state (read-only).
WHY: The build_snapshot_payload function is the largest single unit (~740 lines); isolated here for maintainability.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date as _date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    PublicationSnapshot,
    ResearchCohort,
    FactorPremium,
    FMPIncomeStatement,
    JulyJuneReturn,
    SP500HistoricalConstituent,
)
from app.services.cohort_classifier import CohortClassifier
from app.services.statistics import StatisticalAnalyzer
from app.services.rolling_window import RollingWindowAnalyzer
from app.services.transaction_costs import estimate_rd_strategy_costs, TransactionCostEstimator
from app.services.sanity_checks import (
    MIN_REVENUE_THRESHOLD,
    MAX_RD_INTENSITY_ABSOLUTE,
    MAX_RD_INTENSITY_BIOTECH,
    MIN_ANNUAL_RETURN,
    MAX_ANNUAL_RETURN,
    WINSORIZE_LOWER,
    WINSORIZE_UPPER,
    cap_rd_intensity,
)

from app.services.publication_snapshot.helpers import (
    _json_safe,
    load_backtest_window_config,
)

logger = logging.getLogger(__name__)


async def build_snapshot_payload(
    session: AsyncSession,
    *,
    return_convention: str = "july_june",
    data_tier: str = "tier1",
) -> Dict[str, Any]:
    """
    Build the snapshot payload from the current database state.

    Note: This function should not mutate research tables; it only reads them.
    """
    use_july_june = return_convention == "july_june"

    payload: Dict[str, Any] = {
        "schema_version": 2,
        "built_at": datetime.utcnow().isoformat(),
        "return_convention": return_convention,
        "data_tier": data_tier,
    }

    # Methodology parameters (frozen metadata so the manuscript can cite exact filters/assumptions)
    try:
        payload["methodology_parameters"] = {
            "universe": "sp500",
            "period_filter": "FY",
            "portfolio_construction": {
                "n_quintiles": 5,
                "weighting": "equal_weight_within_quintile",
                "rebalance_frequency": "annual",
            },
            "return_convention": return_convention,
            "data_tier": data_tier,
            "filters": {
                "min_revenue_threshold_usd": float(MIN_REVENUE_THRESHOLD),
                "rd_expenses_nonnegative": True,
                "rd_intensity_capping": {
                    "default_cap_pct": float(MAX_RD_INTENSITY_ABSOLUTE),
                    "high_rd_sector_cap_pct": float(MAX_RD_INTENSITY_BIOTECH),
                    "cap_function": "cap_rd_intensity",
                },
            },
            "sanity_check_constants": {
                "winsorize_lower_pct": int(WINSORIZE_LOWER),
                "winsorize_upper_pct": int(WINSORIZE_UPPER),
                "min_annual_return_decimal": float(MIN_ANNUAL_RETURN),
                "max_annual_return_decimal": float(MAX_ANNUAL_RETURN),
            },
            "notes": [
                "Rolling windows are overlapping and should be treated as descriptive; primary inference uses annual non-overlapping HML series where available.",
            ],
        }
    except Exception as e:
        payload["methodology_parameters"] = {"error": str(e)}

    # Backtest window configuration (auto-detected or default)
    try:
        window_config = load_backtest_window_config()
        if window_config:
            payload["backtest_window"] = {
                "earliest_formation_year": window_config.get("earliest_formation_year"),
                "latest_formation_year": window_config.get("latest_formation_year"),
                "backtest_start_year": window_config.get("backtest_start_year"),
                "backtest_end_year": window_config.get("backtest_end_year"),
                "backtest_period_label": window_config.get("backtest_period_label"),
                "n_formation_years": window_config.get("n_formation_years"),
                "detection_date": window_config.get("detection_date"),
                "source": "auto_detected",
            }
        else:
            # Default fallback based on available data
            yr_result = await session.execute(
                select(func.min(JulyJuneReturn.formation_year), func.max(JulyJuneReturn.formation_year))
                .where(JulyJuneReturn.data_tier == data_tier)
            )
            min_fy, max_fy = yr_result.fetchone()
            if min_fy is not None and max_fy is not None:
                payload["backtest_window"] = {
                    "earliest_formation_year": int(min_fy),
                    "latest_formation_year": int(max_fy),
                    "backtest_start_year": int(min_fy) + 1,
                    "backtest_end_year": int(max_fy) + 2,
                    "backtest_period_label": f"Jul{int(min_fy)+1}-Jun{int(max_fy)+2}",
                    "n_formation_years": int(max_fy) - int(min_fy) + 1,
                    "source": "computed_from_data",
                }
            else:
                payload["backtest_window"] = {"source": "unavailable"}
    except Exception as e:
        payload["backtest_window"] = {"error": str(e)}

    # Cohort summary (counts/coverage)
    try:
        classifier = CohortClassifier(session)
        payload["cohort_summary"] = _json_safe(await classifier.get_cohort_summary())
    except Exception as e:
        payload["cohort_summary"] = {"error": str(e)}

    # Aggregate ANOVA (headline premiums)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["aggregate_anova"] = {
            "5yr": _json_safe(await stats.compute_aggregate_anova("5yr")),
            "10yr": _json_safe(await stats.compute_aggregate_anova("10yr")),
            "20yr": _json_safe(await stats.compute_aggregate_anova("20yr")),
        }
    except Exception as e:
        payload["aggregate_anova"] = {"error": str(e)}

    # Annual HML premium series (for table/charting)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["annual_hml_premium"] = _json_safe(await stats.compute_annual_hml_premium(use_july_june=use_july_june))
    except Exception as e:
        payload["annual_hml_premium"] = {"error": str(e)}

    # Sector-neutral annual HML premium (robustness; addresses sector concentration critique)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["annual_hml_premium_sector_neutral"] = _json_safe(
            await stats.compute_sector_neutral_annual_hml_premium(use_july_june=use_july_june)
        )
    except Exception as e:
        payload["annual_hml_premium_sector_neutral"] = {"error": str(e)}

    # Factor premium time series (used by Paper 3)
    try:
        result = await session.execute(
            select(FactorPremium)
            .where(
                FactorPremium.return_convention == return_convention,
                FactorPremium.data_tier == data_tier,
            )
            .order_by(FactorPremium.year)
        )
        rows = result.scalars().all()
        payload["factor_premiums"] = [
            {
                "year": int(r.year),
                "rd_premium": float(round(r.rd_premium, 2)) if r.rd_premium is not None else None,
                "q1_return": float(round(r.q1_return, 2)) if r.q1_return is not None else None,
                "q2_return": float(round(r.q2_return, 2)) if r.q2_return is not None else None,
                "q3_return": float(round(r.q3_return, 2)) if r.q3_return is not None else None,
                "q4_return": float(round(r.q4_return, 2)) if r.q4_return is not None else None,
                "q5_return": float(round(r.q5_return, 2)) if r.q5_return is not None else None,
            }
            for r in rows
        ]
    except Exception as e:
        payload["factor_premiums"] = {"error": str(e)}

    # Publication stats (pre-formatted summary used across paper pages)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["publication_stats"] = _json_safe(await stats.get_publication_statistics())
    except Exception as e:
        payload["publication_stats"] = {"error": str(e)}

    # Fama-MacBeth monthly cross-sectional regressions (PRIMARY INFERENCE for significance)
    # Uses monthly returns and cross-sectional regressions with controls (Size, B/M)
    try:
        from app.db.models import JulyJuneReturn as _JJR
        # Derive return year bounds from available data (same as annual series)
        yrs_result = await session.execute(
            select(func.min(_JJR.formation_year), func.max(_JJR.formation_year))
            .where(_JJR.data_tier == data_tier)
        )
        min_fy, max_fy = yrs_result.fetchone()
        if min_fy is not None and max_fy is not None:
            fm_start = int(min_fy) + 1  # Return year starts one after formation year
            fm_end = int(max_fy) + 1
            stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
            payload["fama_macbeth_monthly"] = _json_safe(
                await stats.run_fama_macbeth_monthly_with_controls(
                    start_return_year=fm_start,
                    end_return_year=fm_end,
                    nw_lags=12,
                    winsor_p=0.01,
                    data_tier=data_tier,
                )
            )
        else:
            payload["fama_macbeth_monthly"] = {"error": "Could not determine return year bounds"}
    except Exception as e:
        logger.exception("Fama-MacBeth monthly failed")
        payload["fama_macbeth_monthly"] = {"error": str(e)}

    # Delisting-return sensitivity (publication robustness; computed on annual non-overlapping series)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["delisting_sensitivity"] = _json_safe(await stats.compute_delisting_sensitivity(use_july_june=use_july_june))
    except Exception as e:
        payload["delisting_sensitivity"] = {"error": str(e)}

    # Point-in-time membership diagnostics (publication defensibility)
    try:
        payload["membership_diagnostics"] = await _build_membership_diagnostics(
            session, use_july_june=use_july_june, return_convention=return_convention, data_tier=data_tier,
        )
    except Exception as e:
        payload["membership_diagnostics"] = {"error": str(e)}

    # Sector context (computed from ResearchCohort so it stays tier-consistent)
    try:
        sector_result = await session.execute(
            select(
                ResearchCohort.sector.label("sector"),
                func.count(ResearchCohort.symbol).label("company_count"),
                func.avg(ResearchCohort.avg_rd_intensity).label("avg_rd_intensity"),
                func.sum(ResearchCohort.total_rd_spend).label("total_rd_spend"),
            )
            .where(ResearchCohort.sector.isnot(None))
            .group_by(ResearchCohort.sector)
            .order_by(desc(func.avg(ResearchCohort.avg_rd_intensity)))
        )
        payload["rd_by_sector"] = [
            {
                "sector": str(r.sector),
                "company_count": int(r.company_count or 0),
                "avg_rd_intensity": float(round(r.avg_rd_intensity, 2)) if r.avg_rd_intensity is not None else 0.0,
                "total_rd_spend": float(round(r.total_rd_spend, 2)) if r.total_rd_spend is not None else 0.0,
            }
            for r in sector_result.fetchall()
        ]
    except Exception as e:
        payload["rd_by_sector"] = {"error": str(e)}

    # R&D leaderboard (tier-consistent; computed from ResearchCohort)
    try:
        payload.update(await _build_rd_leaderboard(session))
    except Exception as e:
        payload["rd_leaderboard"] = {"error": str(e)}

    # R&D trends over time (Tier-1 descriptive; used for context figures in Main Paper)
    try:
        max_complete_fiscal_year = datetime.utcnow().year - 1
        trend_result = await session.execute(
            select(
                FMPIncomeStatement.fiscal_year.label("year"),
                func.count(func.distinct(FMPIncomeStatement.symbol)).label("companies"),
                (func.avg(FMPIncomeStatement.rd_expenses / func.nullif(FMPIncomeStatement.revenue, 0)) * 100).label("avg_rd_intensity"),
                func.sum(FMPIncomeStatement.rd_expenses).label("total_rd_spend"),
            )
            .where(FMPIncomeStatement.period == "FY")
            .where(FMPIncomeStatement.rd_expenses > 0)
            .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
            .where(FMPIncomeStatement.fiscal_year <= max_complete_fiscal_year)
            .group_by(FMPIncomeStatement.fiscal_year)
            .order_by(FMPIncomeStatement.fiscal_year)
        )
        payload["rd_trends"] = [
            {
                "year": int(r.year),
                "companies": int(r.companies or 0),
                "avg_rd_intensity": float(round(r.avg_rd_intensity, 2)) if r.avg_rd_intensity is not None else 0.0,
                "total_rd_spend": float(r.total_rd_spend or 0.0),
            }
            for r in trend_result.fetchall()
        ]
    except Exception as e:
        payload["rd_trends"] = {"error": str(e)}

    # Net-of-cost returns (paper implementability)
    try:
        payload["net_of_cost_returns"] = await _build_net_of_cost_returns(
            session, use_july_june=use_july_june, data_tier=data_tier,
        )
    except Exception as e:
        payload["net_of_cost_returns"] = {"error": str(e)}

    # Rolling-window aggregates (risk/drawdown context per quintile)
    try:
        analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["rolling_window_aggregates"] = {
            "5yr": _json_safe(await analyzer.aggregate_windows("5yr")),
            "10yr": _json_safe(await analyzer.aggregate_windows("10yr")),
            "20yr": _json_safe(await analyzer.aggregate_windows("20yr")),
        }
    except Exception as e:
        payload["rolling_window_aggregates"] = {"error": str(e)}

    # Rolling-window time series (stored windows; enables time-series figures in Main Paper)
    try:
        analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["rolling_windows"] = {
            "5yr": _json_safe(await analyzer.get_stored_window_results("5yr")),
            "10yr": _json_safe(await analyzer.get_stored_window_results("10yr")),
            "20yr": _json_safe(await analyzer.get_stored_window_results("20yr")),
        }
    except Exception as e:
        payload["rolling_windows"] = {"error": str(e)}

    # Transaction costs (computed after investable_backtest so definitions align)
    payload["transaction_costs"] = {"status": "pending", "note": "Populated after investable_backtest (benchmark-relative definition)."}

    # Investable strategy backtest (best-effort; frozen benchmark comparison for Main Paper)
    try:
        payload["investable_backtest"] = await _build_investable_backtest(
            session, payload=payload, use_july_june=use_july_june, data_tier=data_tier,
        )
    except Exception as e:
        payload["investable_backtest"] = {"error": str(e)}

    # Transaction cost analysis (benchmark-relative; consistent with investable_backtest)
    try:
        payload["transaction_costs"] = await _build_transaction_costs(payload)
    except Exception as e:
        payload["transaction_costs"] = {"error": str(e)}

    # Robustness analyzers (best-effort; snapshot should still build if missing factor tables)
    try:
        payload.update(await _build_robustness_tests(
            session, payload=payload, use_july_june=use_july_june, data_tier=data_tier,
        ))
    except Exception as e:
        payload["spanning_tests_full"] = {"error": str(e)}

    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["double_sort_analysis"] = _json_safe(
            await stats.run_double_sort_analysis(1995, 2024, use_july_june=use_july_june)
        )
    except Exception as e:
        payload["double_sort_analysis"] = {"error": str(e)}

    return payload


# ==========================================================================
# Private helpers — each tackles one logical section of the payload
# ==========================================================================


async def _build_membership_diagnostics(
    session: AsyncSession,
    *,
    use_july_june: bool,
    return_convention: str,
    data_tier: str,
) -> Dict[str, Any]:
    """Point-in-time membership diagnostics (publication defensibility)."""
    membership_rows = await session.execute(
        select(
            SP500HistoricalConstituent.symbol,
            SP500HistoricalConstituent.added_date,
            SP500HistoricalConstituent.removed_date,
            SP500HistoricalConstituent.membership_source,
        )
    )
    spans = membership_rows.fetchall()

    if use_july_june:
        yrs_result = await session.execute(
            select(func.min(JulyJuneReturn.formation_year), func.max(JulyJuneReturn.formation_year))
            .where(JulyJuneReturn.data_tier == data_tier)
        )
        min_fy, max_fy = yrs_result.fetchone()
        start_return_year = int(min_fy) + 1 if min_fy is not None else None
        end_return_year = int(max_fy) + 1 if max_fy is not None else None
    else:
        start_return_year = 1995
        end_return_year = 2024

    years: List[int] = []
    if start_return_year and end_return_year and start_return_year <= end_return_year:
        years = list(range(int(start_return_year), int(end_return_year) + 1))

    members_by_year: Dict[int, Dict[str, Any]] = {}
    union_members: set[str] = set()
    membership_source_totals: Counter = Counter()

    for y in years:
        formation_date = _date(int(y), 7, 1) if use_july_june else _date(int(y), 1, 1)
        members: List[Tuple[str, str]] = []
        for sym, added, removed, src in spans:
            if not sym or not added:
                continue
            if added <= formation_date and (removed is None or removed >= formation_date):
                members.append((str(sym), str(src or "unknown")))

        unique_syms = sorted({m[0] for m in members})
        union_members.update(unique_syms)

        src_counts = Counter([m[1] for m in members])
        membership_source_totals.update(src_counts)

        members_by_year[int(y)] = {
            "formation_date": formation_date.isoformat(),
            "n_constituents": len(unique_syms),
            "membership_source_counts": dict(src_counts),
        }

    if years:
        start_date = _date(int(years[0]), 1, 1)
        end_date = _date(int(years[-1]), 12, 31)
        n_additions = sum(1 for _, added, _, _ in spans if added and start_date <= added <= end_date)
        n_removals = sum(1 for _, _, removed, _ in spans if removed and start_date <= removed <= end_date)
    else:
        n_additions = 0
        n_removals = 0

    counts = [v.get("n_constituents", 0) for v in members_by_year.values() if v.get("n_constituents", 0) > 0]
    return {
        "mode": "point_in_time_membership" if spans else "unavailable",
        "return_convention": return_convention,
        "data_tier": data_tier,
        "years": years,
        "per_year": members_by_year,
        "summary": {
            "unique_tickers_union": len(union_members),
            "avg_constituents_per_year": float(round(sum(counts) / len(counts), 2)) if counts else None,
            "min_constituents_per_year": int(min(counts)) if counts else None,
            "max_constituents_per_year": int(max(counts)) if counts else None,
            "n_years_with_membership": int(len(counts)),
            "n_additions_spans": int(n_additions),
            "n_removals_spans": int(n_removals),
            "membership_source_totals": dict(membership_source_totals),
        },
        "notes": [
            "Membership is evaluated at portfolio formation date (July 1 for July–June convention).",
            "Counts are based on SP500HistoricalConstituent spans; if spans are missing for a year, the analysis falls back to available-data universes and diagnostics will show low/zero counts.",
        ],
    }


async def _build_rd_leaderboard(session: AsyncSession) -> Dict[str, Any]:
    """R&D leaderboard (tier-consistent; computed from ResearchCohort)."""
    rd_leaderboard_limit = 100
    base_query = (
        select(ResearchCohort)
        .where(ResearchCohort.avg_rd_intensity.isnot(None))
        .where(ResearchCohort.avg_rd_intensity > 0)
        .where(ResearchCohort.years_with_rd >= 5)
    )
    result = await session.execute(
        base_query.order_by(desc(ResearchCohort.avg_rd_intensity)).limit(rd_leaderboard_limit)
    )
    rows = result.scalars().all()

    payload_chunk: Dict[str, Any] = {}
    payload_chunk["rd_leaderboard"] = [
        {
            "symbol": r.symbol,
            "name": r.name,
            "sector": r.sector,
            "avg_rd_intensity": float(round(cap_rd_intensity(float(r.avg_rd_intensity or 0.0), sector=r.sector), 2))
            if r.avg_rd_intensity is not None
            else 0.0,
            "total_rd_spend": float(r.total_rd_spend or 0.0),
            "years_of_data": int(r.years_with_rd or 0),
        }
        for r in rows
    ]
    payload_chunk["rd_leaderboard_limit"] = rd_leaderboard_limit

    # Top 3 per sector
    try:
        result_all = await session.execute(base_query)
        all_rows = result_all.scalars().all()
        by_sector: Dict[str, list[Dict[str, Any]]] = {}

        for r in all_rows:
            sector_key = str(r.sector) if r.sector else "Unknown"
            by_sector.setdefault(sector_key, []).append(
                {
                    "symbol": r.symbol,
                    "name": r.name,
                    "sector": r.sector,
                    "avg_rd_intensity": float(round(cap_rd_intensity(float(r.avg_rd_intensity or 0.0), sector=r.sector), 2))
                    if r.avg_rd_intensity is not None
                    else 0.0,
                    "total_rd_spend": float(r.total_rd_spend or 0.0),
                    "years_of_data": int(r.years_with_rd or 0),
                }
            )

        for sector, leaders in by_sector.items():
            leaders.sort(key=lambda x: float(x.get("avg_rd_intensity") or 0.0), reverse=True)
            by_sector[sector] = leaders[:3]

        payload_chunk["rd_leaderboard_by_sector"] = {
            sector: leaders
            for sector, leaders in sorted(
                by_sector.items(),
                key=lambda kv: float(kv[1][0].get("avg_rd_intensity") or 0.0) if kv[1] else 0.0,
                reverse=True,
            )
        }
    except Exception as e:
        payload_chunk["rd_leaderboard_by_sector"] = {"error": str(e)}

    return payload_chunk


async def _build_net_of_cost_returns(
    session: AsyncSession,
    *,
    use_july_june: bool,
    data_tier: str,
) -> Dict[str, Any]:
    """Net-of-cost returns (paper implementability)."""
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
    gross_results = await analyzer.aggregate_windows("5yr")

    estimator = TransactionCostEstimator(universe="sp500", cost_model="moderate")
    portfolio_costs = estimator.estimate_portfolio_cost(n_holdings=100)
    annual_cost = float(portfolio_costs.annual_trading_cost)

    net_results = []
    for q in gross_results:
        gross_return = float(q.get("avg_return", 0) or 0) / 100.0
        net_return = gross_return - annual_cost
        net_results.append(
            {
                "quintile": int(q.get("quintile") or 0),
                "n_companies": int(q.get("n_companies") or 0),
                "avg_rd_intensity": q.get("avg_rd_intensity"),
                "gross_return_pct": round(float(q.get("avg_return", 0) or 0), 2),
                "trading_cost_pct": round(annual_cost * 100, 3),
                "net_return_pct": round(net_return * 100, 2),
            }
        )

    gross_premium = 0.0
    net_premium = 0.0
    if len(net_results) >= 5:
        q5_net = float(net_results[4]["net_return_pct"])
        q1_net = float(net_results[0]["net_return_pct"])
        gross_premium = float(net_results[4]["gross_return_pct"]) - float(net_results[0]["gross_return_pct"])
        net_premium = q5_net - q1_net

    return {
        "5yr": {
            "window_type": "5yr",
            "quintile_results": net_results,
            "gross_rd_premium_pct": round(gross_premium, 2),
            "net_rd_premium_pct": round(net_premium, 2),
            "cost_methodology": portfolio_costs.to_dict(),
            "interpretation": (
                f"The gross R&D premium of {gross_premium:.1f}% becomes {net_premium:.1f}% "
                f"after accounting for estimated trading costs of {annual_cost*100:.2f}% annually."
            ),
        }
    }


async def _build_investable_backtest(
    session: AsyncSession,
    *,
    payload: Dict[str, Any],
    use_july_june: bool,
    data_tier: str,
) -> Dict[str, Any]:
    """Investable strategy backtest (best-effort; frozen benchmark comparison for Main Paper)."""
    from app.services.portfolio_optimizer import PortfolioOptimizer

    start_year = 2001

    end_year = 2024
    if isinstance(payload.get("factor_premiums"), list):
        years = [
            int(p.get("year"))
            for p in payload.get("factor_premiums", [])
            if isinstance(p, dict) and isinstance(p.get("year"), int)
        ]
        if years:
            end_year = max(years)

    spy_max_formation_year = await session.scalar(
        select(func.max(JulyJuneReturn.formation_year))
        .where(JulyJuneReturn.symbol == "SPY", JulyJuneReturn.data_tier == data_tier)
    )
    if spy_max_formation_year is not None:
        spy_end_year = int(spy_max_formation_year) + 1
        end_year = min(end_year, spy_end_year)

    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    return _json_safe(
        await optimizer.backtest_rd_etf(
            start_year=int(start_year),
            end_year=int(end_year),
            n_holdings=20,
            selection_method="rd_alpha",
            sectors=None,
            use_point_in_time=True,
        )
    )


async def _build_transaction_costs(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Transaction cost analysis (benchmark-relative; consistent with investable_backtest)."""
    inv = payload.get("investable_backtest")
    if not (isinstance(inv, dict) and isinstance(inv.get("portfolio_performance"), dict) and isinstance(inv.get("benchmark_performance"), dict)):
        # Fallback: provide a clearly labeled model-based estimate
        fallback = _json_safe(
            estimate_rd_strategy_costs(
                rd_premium_gross=0.04,
                market_return=0.10,
                universe="sp500",
                n_holdings=20,
            )
        )
        fallback["note"] = "Fallback estimate (investable_backtest unavailable)."
        return fallback

    meta = inv.get("meta") if isinstance(inv.get("meta"), dict) else {}
    n_holdings = int(meta.get("n_holdings") or 20)
    benchmark_universe = "SPY_total_return_proxy_close_plus_dividends"

    gross_premium_pct = inv.get("excess_vs_sp500") if isinstance(inv.get("excess_vs_sp500"), (int, float)) else inv.get("excess_return")

    net_premium_pct = None
    try:
        port_net = inv.get("portfolio_performance_net") if isinstance(inv.get("portfolio_performance_net"), dict) else {}
        sp500_perf = inv.get("sp500_performance") if isinstance(inv.get("sp500_performance"), dict) else {}
        port_net_ann = port_net.get("annualized_return")
        sp500_ann = sp500_perf.get("annualized_return")
        if isinstance(port_net_ann, (int, float)) and isinstance(sp500_ann, (int, float)):
            net_premium_pct = float(port_net_ann) - float(sp500_ann)
    except Exception:
        net_premium_pct = None

    if net_premium_pct is None and isinstance(inv.get("excess_return_net"), (int, float)):
        net_premium_pct = inv.get("excess_return_net")

    turnover_meta = inv.get("turnover") if isinstance(inv.get("turnover"), dict) else {}
    avg_turnover_pct = turnover_meta.get("avg_turnover_pct")

    cost_meta = inv.get("cost_assumptions") if isinstance(inv.get("cost_assumptions"), dict) else {}
    round_trip_cost_per_100pct_turnover_pct = cost_meta.get("round_trip_cost_per_100pct_turnover_pct")

    annual_trading_cost_pct = None
    if isinstance(avg_turnover_pct, (int, float)) and isinstance(round_trip_cost_per_100pct_turnover_pct, (int, float)):
        annual_trading_cost_pct = float(round_trip_cost_per_100pct_turnover_pct) * (float(avg_turnover_pct) / 100.0)

    capture_rate_pct = None
    if isinstance(gross_premium_pct, (int, float)) and isinstance(net_premium_pct, (int, float)) and float(gross_premium_pct) != 0.0:
        capture_rate_pct = round(float(net_premium_pct) / float(gross_premium_pct) * 100.0, 1)

    cost_sensitivity = []
    if isinstance(avg_turnover_pct, (int, float)) and isinstance(gross_premium_pct, (int, float)):
        for bps in [5, 10, 25, 50]:
            cost_per_100pct_turnover_pct = float(bps) / 100.0
            annual_cost_pct = cost_per_100pct_turnover_pct * (float(avg_turnover_pct) / 100.0)
            net_prem = float(gross_premium_pct) - float(annual_cost_pct)
            capture = round(net_prem / float(gross_premium_pct) * 100.0, 1) if float(gross_premium_pct) != 0.0 else None
            cost_sensitivity.append(
                {
                    "assumption_bps_per_100pct_turnover": int(bps),
                    "annual_trading_cost_pct": round(float(annual_cost_pct), 3),
                    "net_premium_pct": round(float(net_prem), 2),
                    "premium_capture_rate_pct": capture,
                }
            )

    inv_period = inv.get("period", "")
    backtest_start_year = None
    backtest_end_year = None
    backtest_n_periods = None
    backtest_period_label = None
    if isinstance(inv_period, str) and "-" in inv_period:
        parts = inv_period.split("-")
        try:
            backtest_start_year = int(parts[0])
            backtest_end_year = int(parts[1])
            backtest_n_periods = backtest_end_year - backtest_start_year + 1
            backtest_period_label = f"Jul{backtest_start_year}-Jun{backtest_end_year + 1}"
        except (ValueError, IndexError):
            pass

    return {
        "annual_trading_cost_pct": round(float(annual_trading_cost_pct), 3) if annual_trading_cost_pct is not None else None,
        "gross_rd_premium_pct": round(float(gross_premium_pct), 2) if isinstance(gross_premium_pct, (int, float)) else None,
        "net_rd_premium_pct": round(float(net_premium_pct), 2) if isinstance(net_premium_pct, (int, float)) else None,
        "premium_after_costs_pct": capture_rate_pct,
        "premium_capture_rate_pct": capture_rate_pct,
        "cost_sensitivity": cost_sensitivity,
        "period_years": inv_period,
        "period_label": backtest_period_label,
        "backtest_start_year": backtest_start_year,
        "backtest_end_year": backtest_end_year,
        "n_periods": backtest_n_periods,
        "definition": {
            "strategy": f"Top-{n_holdings} R&D strategy (annual reconstitution)",
            "benchmark": benchmark_universe,
            "gross_premium": "strategy_gross_annualized_return − SPY_gross_annualized_return (total returns via close+dividends proxy)",
            "net_premium": "strategy_net_annualized_return − SPY_gross_annualized_return (total returns via close+dividends proxy)",
            "turnover_definition": "0.5 * sum |w_t − w_{t-1}| (first year excluded from averages)",
            "annual_cost_approx": "round_trip_cost_per_100pct_turnover × realized_turnover",
        },
        "turnover": turnover_meta,
        "cost_assumptions": cost_meta,
        "strategy_returns": {
            "gross_annualized_return_pct": inv.get("portfolio_performance", {}).get("annualized_return"),
            "net_annualized_return_pct": inv.get("portfolio_performance_net", {}).get("annualized_return"),
        },
        "benchmark_returns": {
            "gross_annualized_return_pct": inv.get("sp500_performance", {}).get("annualized_return"),
            "net_annualized_return_pct": inv.get("sp500_performance", {}).get("annualized_return"),
        },
        "secondary_benchmark_returns": {
            "benchmark": "research_cohort_equal_weight",
            "gross_annualized_return_pct": inv.get("benchmark_performance", {}).get("annualized_return"),
            "net_annualized_return_pct": inv.get("benchmark_performance_net", {}).get("annualized_return"),
        },
        "note": "Transaction-cost summary is derived from the investable backtest using realized turnover (preferred).",
    }


async def _build_robustness_tests(
    session: AsyncSession,
    *,
    payload: Dict[str, Any],
    use_july_june: bool,
    data_tier: str,
) -> Dict[str, Any]:
    """Robustness analyzers (best-effort; snapshot should still build if missing factor tables)."""
    from app.services.factor_tests import FactorSpanningAnalyzer
    from app.services.ff_factors_ingest import ensure_ff_factors_populated

    result_chunk: Dict[str, Any] = {}

    annual = payload.get("annual_hml_premium", {})
    hml_rd_series: Dict[int, float] = {}
    if isinstance(annual, dict) and isinstance(annual.get("annual_premiums"), list):
        for p in annual["annual_premiums"]:
            if not isinstance(p, dict):
                continue
            year = (p.get("formation_year", 0) + 1) if use_july_june else p.get("year", 0)
            prem = p.get("hml_premium")
            if isinstance(year, int) and isinstance(prem, (int, float)):
                hml_rd_series[int(year)] = float(prem) / 100.0

    result_chunk["ff_factors_status"] = _json_safe(await ensure_ff_factors_populated(session))

    spanning_analyzer = FactorSpanningAnalyzer(session)
    if hml_rd_series:
        result_chunk["spanning_tests_full"] = _json_safe(
            await spanning_analyzer.run_all_spanning_tests_monthly(
                start_return_year=min(hml_rd_series.keys()),
                end_return_year=max(hml_rd_series.keys()),
                data_tier=data_tier,
                use_july_june=use_july_june,
            )
        )
    else:
        result_chunk["spanning_tests_full"] = {"error": "No annual series available to define spanning window."}

    try:
        from app.services.factor_tests import MispricingAnalyzer

        analyzer = MispricingAnalyzer(session)
        result_chunk["mispricing_tests"] = _json_safe(
            await analyzer.run_mispricing_tests(
                1995,
                2024,
                use_july_june=use_july_june,
                data_tier=data_tier,
            )
        )
    except Exception as e:
        result_chunk["mispricing_tests"] = {"error": str(e)}

    try:
        from app.services.factor_tests import LiquidityModerationAnalyzer

        liquidity_analyzer = LiquidityModerationAnalyzer(session)
        result_chunk["liquidity_moderation"] = _json_safe(
            await liquidity_analyzer.run_liquidity_moderation_tests(
                start_formation_year=2000,
                end_formation_year=2024,
                data_tier=data_tier,
            )
        )
    except Exception as e:
        result_chunk["liquidity_moderation"] = {"error": str(e)}

    return result_chunk
