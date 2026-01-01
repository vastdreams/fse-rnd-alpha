"""
Publication Snapshot Service

Builds and serves frozen, publication-ready snapshots of research outputs.

Rationale:
  - A single snapshot pins all tables/metrics used by the on-site manuscript.
  - Avoids relying on computation_run_id consistency across multiple result tables.
  - Improves robustness: paper pages render even if some live computations fail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PublicationSnapshot, ResearchCohort, FactorPremium, FMPIncomeStatement
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


def _json_safe(obj: Any) -> Any:
    """
    Convert objects that commonly appear in analytics output into JSON-safe types.
    """
    if obj is None:
        return None

    # Datetimes
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Numpy scalars
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()

    # Plain python primitives
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Containers
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return [_json_safe(v) for v in sorted(obj)]

    # Fallback: try to coerce numpy arrays, decimals, etc.
    try:
        if hasattr(obj, "tolist"):
            return _json_safe(obj.tolist())
    except Exception:
        pass

    return str(obj)


async def get_active_snapshot(session: AsyncSession) -> Optional[PublicationSnapshot]:
    result = await session.execute(
        select(PublicationSnapshot)
        .where(PublicationSnapshot.is_active.is_(True))
        .order_by(PublicationSnapshot.built_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


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

    # Delisting-return sensitivity (publication robustness; computed on annual non-overlapping series)
    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["delisting_sensitivity"] = _json_safe(await stats.compute_delisting_sensitivity(use_july_june=use_july_june))
    except Exception as e:
        payload["delisting_sensitivity"] = {"error": str(e)}

    # Point-in-time membership diagnostics (publication defensibility)
    try:
        from datetime import date as _date
        from collections import Counter
        from app.db.models import SP500HistoricalConstituent, JulyJuneReturn
        # NOTE: Using global 'select' and 'func' imports to avoid Python 3.11+ scoping issues

        membership_rows = await session.execute(
            select(
                SP500HistoricalConstituent.symbol,
                SP500HistoricalConstituent.added_date,
                SP500HistoricalConstituent.removed_date,
                SP500HistoricalConstituent.membership_source,
            )
        )
        spans = membership_rows.fetchall()

        # Study years: derive from the returns table so diagnostics align with what we can actually compute.
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

        # Additions/removals during the study window (span events, not unique symbols)
        if years:
            start_date = _date(int(years[0]), 1, 1)
            end_date = _date(int(years[-1]), 12, 31)
            n_additions = sum(1 for _, added, _, _ in spans if added and start_date <= added <= end_date)
            n_removals = sum(1 for _, _, removed, _ in spans if removed and start_date <= removed <= end_date)
        else:
            n_additions = 0
            n_removals = 0

        counts = [v.get("n_constituents", 0) for v in members_by_year.values() if v.get("n_constituents", 0) > 0]
        payload["membership_diagnostics"] = {
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

        payload["rd_leaderboard"] = [
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
        payload["rd_leaderboard_limit"] = rd_leaderboard_limit

        # Top 3 per sector (presentation form that avoids cross-sector concentration)
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

            # Sort sectors by their #1 leader intensity (descending) for stable ordering in the paper.
            payload["rd_leaderboard_by_sector"] = {
                sector: leaders
                for sector, leaders in sorted(
                    by_sector.items(),
                    key=lambda kv: float(kv[1][0].get("avg_rd_intensity") or 0.0) if kv[1] else 0.0,
                    reverse=True,
                )
            }
        except Exception as e:
            payload["rd_leaderboard_by_sector"] = {"error": str(e)}
    except Exception as e:
        payload["rd_leaderboard"] = {"error": str(e)}

    # R&D trends over time (Tier-1 descriptive; used for context figures in Main Paper)
    try:
        # Publication rule: income-statement FY coverage for the current calendar year is
        # typically incomplete. For publication-facing "trend" exhibits, only include
        # full historical fiscal years up to (build_year - 1).
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
        analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        gross_results = await analyzer.aggregate_windows("5yr")

        estimator = TransactionCostEstimator(universe="sp500", cost_model="moderate")
        portfolio_costs = estimator.estimate_portfolio_cost(n_holdings=100)  # ~100 per quintile
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

        payload["net_of_cost_returns"] = {
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
        from app.services.portfolio_optimizer import PortfolioOptimizer

        # Default to the platform’s “modern” backtest window, but pin end_year to available
        # annual series if present (keeps the exhibit internally consistent with the snapshot).
        end_year = 2023
        if isinstance(payload.get("factor_premiums"), list):
            years = [
                int(p.get("year"))
                for p in payload.get("factor_premiums", [])
                if isinstance(p, dict) and isinstance(p.get("year"), int)
            ]
            if years:
                end_year = max(years)

        start_year = 2010 if end_year >= 2010 else max(1995, end_year - 13)

        optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
        payload["investable_backtest"] = _json_safe(
            await optimizer.backtest_rd_etf(
                start_year=int(start_year),
                end_year=int(end_year),
                n_holdings=20,
                selection_method="rd_alpha",
                sectors=None,
                use_point_in_time=True,
            )
        )
    except Exception as e:
        payload["investable_backtest"] = {"error": str(e)}

    # Transaction cost analysis (benchmark-relative; consistent with investable_backtest)
    try:
        inv = payload.get("investable_backtest")
        if isinstance(inv, dict) and isinstance(inv.get("portfolio_performance"), dict) and isinstance(inv.get("benchmark_performance"), dict):
            meta = inv.get("meta") if isinstance(inv.get("meta"), dict) else {}
            n_holdings = int(meta.get("n_holdings") or 20)
            # Publication-facing benchmark: SPY (cap-weighted S&P 500 total-return proxy via adj_close).
            # Keep the cohort equal-weight benchmark as a secondary comparison in the backtest payload.
            benchmark_universe = "SPY_adj_close_total_return_proxy"

            # Prefer the strategy spread versus SPY for practitioner-facing reporting.
            gross_premium_pct = inv.get("excess_vs_sp500") if isinstance(inv.get("excess_vs_sp500"), (int, float)) else inv.get("excess_return")

            # Net premium vs SPY: strategy net annualized return minus SPY annualized return.
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
                # Fallback: benchmark-relative net premium (legacy cohort benchmark).
                net_premium_pct = inv.get("excess_return_net")

            # Trading cost estimate from realized turnover (excluding first year by construction in backtest)
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

            # Cost sensitivity band (reviewer-friendly): show net premium under alternative
            # per-100% turnover cost assumptions (in basis points).
            cost_sensitivity = []
            if isinstance(avg_turnover_pct, (int, float)) and isinstance(gross_premium_pct, (int, float)):
                for bps in [5, 10, 25, 50]:
                    cost_per_100pct_turnover_pct = float(bps) / 100.0  # 5bp -> 0.05%
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

            payload["transaction_costs"] = {
                # Backward-compatible fields used by LaTeX asset generation
                "annual_trading_cost_pct": round(float(annual_trading_cost_pct), 3) if annual_trading_cost_pct is not None else None,
                "gross_rd_premium_pct": round(float(gross_premium_pct), 2) if isinstance(gross_premium_pct, (int, float)) else None,
                "net_rd_premium_pct": round(float(net_premium_pct), 2) if isinstance(net_premium_pct, (int, float)) else None,
                "premium_after_costs_pct": capture_rate_pct,
                "premium_capture_rate_pct": capture_rate_pct,
                "cost_sensitivity": cost_sensitivity,
                # Transparency / definitions
                "definition": {
                    "strategy": f"Top-{n_holdings} R&D strategy (annual reconstitution)",
                    "benchmark": benchmark_universe,
                    "gross_premium": "strategy_gross_annualized_return − SPY_gross_annualized_return (total returns via adj_close)",
                    "net_premium": "strategy_net_annualized_return − SPY_gross_annualized_return (total returns via adj_close)",
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
        else:
            # Fallback: provide a clearly labeled model-based estimate so tables can still render.
            payload["transaction_costs"] = _json_safe(
                estimate_rd_strategy_costs(
                    rd_premium_gross=0.04,
                    market_return=0.10,
                    universe="sp500",
                    n_holdings=20,
                )
            )
            payload["transaction_costs"]["note"] = "Fallback estimate (investable_backtest unavailable)."
    except Exception as e:
        payload["transaction_costs"] = {"error": str(e)}

    # Robustness analyzers (best-effort; snapshot should still build if missing factor tables)
    try:
        # Import lazily to avoid import-time failures if optional deps are missing
        from app.services.factor_tests import FactorSpanningAnalyzer
        from app.services.ff_factors_ingest import ensure_ff_factors_populated

        annual = payload.get("annual_hml_premium", {})
        hml_rd_series: Dict[int, float] = {}
        if isinstance(annual, dict) and isinstance(annual.get("annual_premiums"), list):
            for p in annual["annual_premiums"]:
                if not isinstance(p, dict):
                    continue
                year = (p.get("formation_year", 0) + 1) if use_july_june else p.get("year", 0)
                prem = p.get("hml_premium")
                if isinstance(year, int) and isinstance(prem, (int, float)):
                    # Spanning tests operate in decimal returns. Annual HML premium is stored in percent.
                    hml_rd_series[int(year)] = float(prem) / 100.0

        # Ensure factor inputs exist before computing spanning tests.
        payload["ff_factors_status"] = _json_safe(await ensure_ff_factors_populated(session))

        spanning_analyzer = FactorSpanningAnalyzer(session)
        # Publication upgrade: use monthly spanning (annual July reconstitution, monthly observations)
        # to improve regression stability versus a short annual sample.
        if hml_rd_series:
            payload["spanning_tests_full"] = _json_safe(
                await spanning_analyzer.run_all_spanning_tests_monthly(
                    start_return_year=min(hml_rd_series.keys()),
                    end_return_year=max(hml_rd_series.keys()),
                    data_tier=data_tier,
                    use_july_june=use_july_june,
                )
            )
        else:
            payload["spanning_tests_full"] = {"error": "No annual series available to define spanning window."}
    except Exception as e:
        payload["spanning_tests_full"] = {"error": str(e)}

    try:
        from app.services.factor_tests import MispricingAnalyzer

        analyzer = MispricingAnalyzer(session)
        payload["mispricing_tests"] = _json_safe(
            await analyzer.run_mispricing_tests(
                1995,
                2024,
                use_july_june=use_july_june,
                data_tier=data_tier,
            )
        )
    except Exception as e:
        payload["mispricing_tests"] = {"error": str(e)}

    try:
        stats = StatisticalAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
        payload["double_sort_analysis"] = _json_safe(
            await stats.run_double_sort_analysis(1995, 2024, use_july_june=use_july_june)
        )
    except Exception as e:
        payload["double_sort_analysis"] = {"error": str(e)}

    return payload


async def create_publication_snapshot(
    session: AsyncSession,
    *,
    label: str,
    payload: Dict[str, Any],
    return_convention: str,
    data_tier: str,
    notes: Optional[str] = None,
    git_commit: Optional[str] = None,
    git_branch: Optional[str] = None,
    set_active: bool = True,
) -> PublicationSnapshot:
    snapshot_id = str(uuid.uuid4())

    if set_active:
        await session.execute(
            update(PublicationSnapshot)
            .where(PublicationSnapshot.is_active.is_(True))
            .values(is_active=False)
        )

    snap = PublicationSnapshot(
        id=snapshot_id,
        label=label,
        is_active=set_active,
        return_convention=return_convention,
        data_tier=data_tier,
        built_at=datetime.utcnow(),
        git_commit=git_commit,
        git_branch=git_branch,
        notes=notes,
        payload=_json_safe(payload),
    )
    session.add(snap)
    await session.commit()
    return snap


