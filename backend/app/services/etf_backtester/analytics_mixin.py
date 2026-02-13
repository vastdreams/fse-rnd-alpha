"""
PATH: backend/app/services/etf_backtester/analytics_mixin.py
PURPOSE: Mixin providing calculation / analytics methods for the ETF backtester.
WHY: Isolates pure computation (performance metrics, turnover, yearly aggregation) from data I/O.
"""

from typing import Dict, List, Optional, Tuple
from datetime import date
from calendar import monthrange

import numpy as np

from app.services.etf_backtester.data_classes import (
    Holding,
    MonthlyPortfolioReturn,
    PerformanceMetrics,
    FORMATION_MONTH,
    BENCHMARK_SYMBOL,
    DEFAULT_RISK_FREE_RATE,
)


class AnalyticsMixin:
    """
    Mixin that provides pure-computation methods for backtesting analytics.

    Expects the consumer class to also mix in PriceDataMixin (for data access)
    and to define:
        self._delisting_cache: Dict[str, date]
    """

    def _generate_month_sequence(self, start_year: int, end_year: int) -> List[Tuple[int, int]]:
        """Generate sequence of (year, month) tuples from July start_year to June end_year+1."""
        months = []

        for year in range(start_year, end_year + 2):
            if year == start_year:
                # First year: July-December
                for month in range(FORMATION_MONTH, 13):
                    months.append((year, month))
            elif year == end_year + 1:
                # Last year: January-June
                for month in range(1, FORMATION_MONTH):
                    months.append((year, month))
            else:
                # Middle years: July-December and January-June
                for month in range(FORMATION_MONTH, 13):
                    months.append((year, month))
                # Next calendar year's Jan-June
                for month in range(1, FORMATION_MONTH):
                    months.append((year + 1, month))

        # Remove duplicates and sort
        months = sorted(set(months))

        # Filter to valid range
        start_date = date(start_year, FORMATION_MONTH, 1)
        end_date = date(end_year + 1, FORMATION_MONTH - 1, 28)  # June end_year+1

        return [(y, m) for y, m in months if start_date <= date(y, m, 1) <= end_date]

    async def _calculate_monthly_return(
        self,
        year: int,
        month: int,
        holdings: List[Holding],
    ) -> MonthlyPortfolioReturn:
        """Calculate portfolio return for a single month."""

        # Get month-end date
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)

        # Previous month end
        if month == 1:
            prev_month_end = date(year - 1, 12, 31)
        else:
            _, prev_last = monthrange(year, month - 1)
            prev_month_end = date(year, month - 1, prev_last)

        portfolio_return = 0.0
        total_weight = 0.0
        n_delistings = 0

        for h in holdings:
            weight = h.weight
            symbol = h.symbol

            # Check for delisting
            if symbol in self._delisting_cache:
                delist_date = self._delisting_cache[symbol]
                if prev_month_end < delist_date <= month_end:
                    # Delisting happened this month: compute return to the delist date (cash thereafter).
                    start_price = await self._get_price_near_date(symbol, prev_month_end)
                    end_price = await self._get_price_near_date(symbol, delist_date)
                    if start_price is not None and end_price is not None and start_price > 0:
                        ret = (end_price - start_price) / start_price
                        portfolio_return += weight * float(ret)
                        total_weight += weight
                        n_delistings += 1
                    continue
                elif delist_date <= prev_month_end:
                    # Already delisted
                    continue

            # Get monthly return from prices
            ret = await self._get_monthly_return(symbol, year, month)
            if ret is not None:
                portfolio_return += weight * ret
                total_weight += weight

        # Renormalize for missing
        if total_weight > 0:
            portfolio_return = portfolio_return / total_weight
        else:
            portfolio_return = 0.0

        # Get benchmark return (SPY)
        benchmark_return = await self._get_monthly_return(BENCHMARK_SYMBOL, year, month)
        if benchmark_return is None:
            benchmark_return = 0.0

        # Get S&P 500 return from Fama-French
        sp500_return = await self._get_ff_market_return(year, month)
        if sp500_return is None:
            sp500_return = benchmark_return  # Fallback

        return MonthlyPortfolioReturn(
            year=year,
            month=month,
            date=month_end,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            sp500_return=sp500_return,
            excess_vs_benchmark=portfolio_return - benchmark_return,
            excess_vs_sp500=portfolio_return - sp500_return,
            n_holdings=len(holdings),
            n_delistings=n_delistings,
            effective_weight=total_weight,
        )

    def _calculate_turnover(
        self,
        prev_weights: Dict[str, float],
        curr_weights: Dict[str, float],
    ) -> float:
        """Calculate one-way turnover (0.5 * sum of absolute weight changes)."""
        all_symbols = set(prev_weights.keys()) | set(curr_weights.keys())
        total_change = sum(
            abs(curr_weights.get(s, 0.0) - prev_weights.get(s, 0.0))
            for s in all_symbols
        )
        return 0.5 * total_change

    def _calculate_performance(
        self,
        monthly_returns: List[float],
        monthly_data: List[MonthlyPortfolioReturn],
    ) -> PerformanceMetrics:
        """Calculate performance metrics from monthly return series."""
        if not monthly_returns:
            return PerformanceMetrics(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0,
            )

        # Total return (compound)
        total_return = float(np.prod([1 + r for r in monthly_returns]) - 1)

        # Annualized return (CAGR)
        n_months = len(monthly_returns)
        n_years = n_months / 12
        if n_years > 0:
            annualized_return = float((1 + total_return) ** (1 / n_years) - 1)
        else:
            annualized_return = 0.0

        # Annualized volatility (monthly std * sqrt(12))
        if len(monthly_returns) > 1:
            volatility = float(np.std(monthly_returns, ddof=1)) * np.sqrt(12)
        else:
            volatility = 0.0

        # Sharpe ratio (using average annual RF over period)
        years_in_period = sorted(set(m.year for m in monthly_data))
        avg_rf = DEFAULT_RISK_FREE_RATE  # Simplified

        excess_return = annualized_return - avg_rf
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0.0

        # Max drawdown
        cumulative = np.cumprod([1 + r for r in monthly_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        return PerformanceMetrics(
            total_return=total_return * 100,
            annualized_return=annualized_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown * 100,
        )

    def _aggregate_to_yearly(
        self,
        monthly_returns: List[MonthlyPortfolioReturn],
    ) -> List[Dict]:
        """Aggregate monthly returns to yearly (July-June) for backward compatibility."""
        # Group by fiscal year (July T to June T+1 = fiscal year T)
        by_fiscal_year: Dict[int, List[MonthlyPortfolioReturn]] = {}

        for m in monthly_returns:
            if m.month >= FORMATION_MONTH:
                fiscal_year = m.year
            else:
                fiscal_year = m.year - 1

            if fiscal_year not in by_fiscal_year:
                by_fiscal_year[fiscal_year] = []
            by_fiscal_year[fiscal_year].append(m)

        yearly_data = []

        for fiscal_year in sorted(by_fiscal_year.keys()):
            months = by_fiscal_year[fiscal_year]

            # Compound monthly returns
            port_returns = [m.portfolio_return for m in months]
            bench_returns = [m.benchmark_return for m in months]
            sp500_returns = [m.sp500_return for m in months]

            port_annual = float(np.prod([1 + r for r in port_returns]) - 1)
            bench_annual = float(np.prod([1 + r for r in bench_returns]) - 1)
            sp500_annual = float(np.prod([1 + r for r in sp500_returns]) - 1)

            yearly_data.append({
                "year": fiscal_year,
                "portfolio_return": round(port_annual * 100, 2),
                "benchmark_return": round(bench_annual * 100, 2),
                "sp500_return": round(sp500_annual * 100, 2),
                "excess_return": round((port_annual - bench_annual) * 100, 2),
                "excess_vs_sp500": round((port_annual - sp500_annual) * 100, 2),
                "n_months": len(months),
            })

        return yearly_data
