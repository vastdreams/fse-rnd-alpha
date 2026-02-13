"""
PATH: backend/app/services/etf_backtester/backtester.py
PURPOSE: Main ETFBacktester class composing PriceDataMixin + AnalyticsMixin.
WHY: Keeps the orchestrating run_backtest method in its own small module while mixins handle concerns.

ROLE IN ARCHITECTURE:
  - Called by PortfolioOptimizer.backtest_rd_etf() for monthly granularity
  - Uses ETFUniverseBuilder for point-in-time eligibility
  - Uses RDAlphaScorer for holdings selection

NOTES FOR FUTURE AI:
  - Formation date: July 1 of as_of_year
  - Holdings held July T to June T+1
  - Equal-weight at formation, drift during year
  - Delistings apply delisting return in month of delisting
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import date

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.etf_backtester.data_classes import (
    Holding,
    MonthlyBacktestResult,
    MonthlyPortfolioReturn,
    TurnoverMetrics,
    FORMATION_MONTH,
)
from app.services.etf_universe import EligibilityResult, EligibilityMode
from app.services.transaction_costs import TransactionCostEstimator
from app.services.etf_backtester.price_data_mixin import PriceDataMixin
from app.services.etf_backtester.analytics_mixin import AnalyticsMixin

logger = logging.getLogger(__name__)


class ETFBacktester(PriceDataMixin, AnalyticsMixin):
    """
    Monthly ETF backtester with annual July reconstitution.

    Simulation Rules:
    - Formation date: July 1 of as_of_year
    - Equal-weight at formation (1/n for each holding)
    - Hold July T through June T+1
    - Reconstitute + rebalance each July
    - Delistings: apply delisting return, remove from portfolio, renormalize

    Return Calculation:
    - Monthly returns from month-end adjusted close prices
    - Portfolio return = weighted average of constituent returns
    - Missing returns: renormalize weights among available
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._rf_cache: Dict[int, float] = {}
        self._price_cache: Dict[Tuple[str, int, int], Optional[float]] = {}
        # Delisting handling for survivorship bias:
        # We cache delist dates (not "delist returns"), and compute the month's return from prices
        # up to the delist date (cash earns 0% thereafter in that month).
        self._delisting_cache: Dict[str, date] = {}

    async def run_backtest(
        self,
        start_year: int,
        end_year: int,
        holdings_by_year: Dict[int, List[Holding]],
        eligibility_result: Optional[EligibilityResult] = None,
        cost_model: str = "moderate",
    ) -> MonthlyBacktestResult:
        """
        Run monthly backtest with provided holdings.

        Args:
            start_year: First year of backtest (July start_year to June start_year+1 is first period)
            end_year: Last year of backtest
            holdings_by_year: Dict mapping year -> list of holdings (selected at July of that year)
            eligibility_result: Eligibility metadata from universe builder
            cost_model: Transaction cost model ("low", "moderate", "high")

        Returns:
            MonthlyBacktestResult with full metrics and series
        """
        # Pre-load caches
        await self._load_delistings(holdings_by_year)

        # Generate month sequence: July start_year through June end_year+1
        months = self._generate_month_sequence(start_year, end_year)

        # Calculate monthly returns
        monthly_returns: List[MonthlyPortfolioReturn] = []
        turnover_by_year: List[Dict] = []
        prev_weights: Dict[str, float] = {}

        for year, month in months:
            # Determine which year's holdings to use
            # July T uses holdings selected in year T
            # Aug-Dec T uses holdings from year T
            # Jan-Jun T+1 uses holdings from year T
            if month >= FORMATION_MONTH:
                holdings_year = year
            else:
                holdings_year = year - 1

            holdings = holdings_by_year.get(holdings_year, [])
            if not holdings:
                continue

            # Check for reconstitution (July = new holdings)
            if month == FORMATION_MONTH:
                curr_weights = {h.symbol: h.weight for h in holdings}

                # Calculate turnover
                if prev_weights:
                    turnover = self._calculate_turnover(prev_weights, curr_weights)
                else:
                    turnover = 0.0  # First period

                turnover_by_year.append({
                    "year": year,
                    "turnover": round(turnover, 4),
                    "turnover_pct": round(turnover * 100, 1),
                    "n_holdings": len(holdings),
                })

                prev_weights = curr_weights.copy()

            # Calculate portfolio return for this month
            month_result = await self._calculate_monthly_return(
                year=year,
                month=month,
                holdings=holdings,
            )
            monthly_returns.append(month_result)

        if not monthly_returns:
            raise ValueError(f"No returns calculated for period {start_year}-{end_year}")

        # Aggregate to performance metrics
        portfolio_returns = [m.portfolio_return for m in monthly_returns]
        benchmark_returns = [m.benchmark_return for m in monthly_returns]
        sp500_returns = [m.sp500_return for m in monthly_returns]

        # Calculate performance metrics
        portfolio_perf = self._calculate_performance(portfolio_returns, monthly_returns)
        benchmark_perf = self._calculate_performance(benchmark_returns, monthly_returns)
        sp500_perf = self._calculate_performance(sp500_returns, monthly_returns)

        # Net-of-cost performance
        cost_estimator = TransactionCostEstimator(universe="sp500", cost_model=cost_model)
        n_holdings = len(holdings_by_year.get(start_year, []))
        cost_template = cost_estimator.estimate_portfolio_cost(n_holdings=n_holdings, rebalancing_frequency="annual")
        round_trip_cost = cost_template.round_trip_total

        # Apply costs based on realized turnover
        total_cost = 0.0
        for t in turnover_by_year[1:]:  # Skip first year (formation)
            total_cost += round_trip_cost * t.get("turnover", 0.0)

        portfolio_returns_net = portfolio_returns.copy()
        # Distribute costs across months (simplified)
        cost_per_month = total_cost / len(portfolio_returns_net) if portfolio_returns_net else 0
        portfolio_returns_net = [r - cost_per_month for r in portfolio_returns_net]
        portfolio_perf_net = self._calculate_performance(portfolio_returns_net, monthly_returns)

        # Aggregate to yearly data (backward compatible)
        yearly_data = self._aggregate_to_yearly(monthly_returns)

        # Build monthly data for charting
        monthly_data = [
            {
                "year": m.year,
                "month": m.month,
                "date": m.date.isoformat(),
                "portfolio_return": round(m.portfolio_return * 100, 2),
                "benchmark_return": round(m.benchmark_return * 100, 2),
                "sp500_return": round(m.sp500_return * 100, 2),
                "excess_vs_benchmark": round(m.excess_vs_benchmark * 100, 2),
                "excess_vs_sp500": round(m.excess_vs_sp500 * 100, 2),
                "n_holdings": m.n_holdings,
                "n_delistings": m.n_delistings,
            }
            for m in monthly_returns
        ]

        # Turnover metrics
        turnover_values = [t.get("turnover", 0.0) for t in turnover_by_year[1:]]
        turnover_metrics = TurnoverMetrics(
            by_year=turnover_by_year,
            avg_turnover_pct=float(np.mean(turnover_values) * 100) if turnover_values else 0.0,
            max_turnover_pct=float(np.max(turnover_values) * 100) if turnover_values else 0.0,
            total_cost_pct=total_cost * 100,
        )

        # Build meta
        meta = {
            "return_convention": "july_june",
            "return_granularity": "monthly",
            "formation_month": "July",
            "weighting": "equal_weight",
            "rebalancing": "annual",
            "benchmark": "SPY",
            "cost_model": cost_model,
        }

        if eligibility_result:
            meta.update(eligibility_result.to_meta_dict())

        return MonthlyBacktestResult(
            period=f"{start_year}-{end_year}",
            start_year=start_year,
            end_year=end_year,
            n_holdings=n_holdings,
            eligibility_mode=eligibility_result.mode if eligibility_result else EligibilityMode.PROVISIONAL,
            eligibility_warnings=eligibility_result.warnings if eligibility_result else [],
            initial_holdings=holdings_by_year.get(start_year, []),
            holdings_by_year=holdings_by_year,
            portfolio_performance=portfolio_perf,
            benchmark_performance=benchmark_perf,
            sp500_performance=sp500_perf,
            portfolio_performance_net=portfolio_perf_net,
            excess_vs_benchmark=portfolio_perf.annualized_return - benchmark_perf.annualized_return,
            excess_vs_sp500=portfolio_perf.annualized_return - sp500_perf.annualized_return,
            turnover=turnover_metrics,
            monthly_data=monthly_data,
            yearly_data=yearly_data,
            meta=meta,
        )
