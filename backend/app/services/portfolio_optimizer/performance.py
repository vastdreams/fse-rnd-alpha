"""
PATH: research/backend/app/services/portfolio_optimizer/performance.py
PURPOSE: Portfolio performance calculation and benchmark comparison
WHY: Isolates return/risk metric calculations from selection and backtesting logic
DEPENDENCIES:
  - app.db.models: ORM models for return data and risk-free rates
  - numpy: statistical calculations
  - .models: shared dataclasses
"""

import logging
from typing import List, Dict
from datetime import datetime

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FMPAnnualReturn

from .models import PortfolioHolding, PortfolioPerformance

logger = logging.getLogger(__name__)


class PerformanceMixin:
    """
    Mixin providing performance calculation methods for PortfolioOptimizer.

    Expects the composing class to set:
      - self.session: AsyncSession
      - self.use_july_june: bool
      - self._rf_cache: dict
      - self.DEFAULT_RISK_FREE_RATE: float
    """

    session: AsyncSession
    use_july_june: bool
    _rf_cache: dict
    DEFAULT_RISK_FREE_RATE: float

    async def get_risk_free_rate(self, year: int) -> float:
        """
        Get risk-free rate for a specific year from database.

        Uses RiskFreeRate table if available, otherwise falls back to default.
        This standardizes RF usage across research and ETF metrics.

        Args:
            year: Calendar year

        Returns:
            Annual risk-free rate as decimal (e.g., 0.02 for 2%)
        """
        if year in self._rf_cache:
            return self._rf_cache[year]

        from app.db.models import RiskFreeRate
        from datetime import date

        result = await self.session.execute(
            select(func.avg(RiskFreeRate.rate_annual_pct))
            .where(
                RiskFreeRate.date >= date(year, 1, 1),
                RiskFreeRate.date <= date(year, 12, 31)
            )
        )
        avg_rate = result.scalar()

        if avg_rate is not None:
            rate = avg_rate / 100  # Convert percentage to decimal
            self._rf_cache[year] = rate
            return rate

        return self.DEFAULT_RISK_FREE_RATE

    async def get_available_windows(self) -> List[Dict]:
        """Get list of available time windows for analysis."""
        windows = []
        current_year = datetime.now().year

        for start in range(1995, current_year - 4):
            windows.append({
                "window_id": f"5yr_{start}_{start+4}",
                "window_type": "5yr",
                "start_year": start,
                "end_year": start + 4,
                "label": f"{start}-{start+4}"
            })

        for start in range(1995, current_year - 9):
            windows.append({
                "window_id": f"10yr_{start}_{start+9}",
                "window_type": "10yr",
                "start_year": start,
                "end_year": start + 9,
                "label": f"{start}-{start+9}"
            })

        return windows

    async def calculate_portfolio_returns(
        self,
        symbols: List[str],
        weights: List[float],
        start_year: int,
        end_year: int
    ) -> PortfolioPerformance:
        """
        Calculate portfolio performance over a period.

        PUBLICATION FIX (Dec 2025):
        - Supports July-June returns (Fama-French convention) via self.use_july_june
        - Delistings handled upstream in the July-June return series
        """
        from app.db.models import JulyJuneReturn

        annual_returns = []

        for year in range(start_year, end_year + 1):
            year_return = 0.0
            valid_weights = 0.0

            for symbol, weight in zip(symbols, weights):
                ret = None

                if self.use_july_june:
                    formation_year = year - 1
                    result = await self.session.execute(
                        select(JulyJuneReturn.annualized_return)
                        .where(
                            JulyJuneReturn.symbol == symbol,
                            JulyJuneReturn.formation_year == formation_year,
                            JulyJuneReturn.data_tier == "tier1",
                        )
                    )
                    ret = result.scalar()
                else:
                    result = await self.session.execute(
                        select(FMPAnnualReturn.annual_return)
                        .where(
                            FMPAnnualReturn.symbol == symbol,
                            FMPAnnualReturn.year == year
                        )
                    )
                    ret = result.scalar()

                if ret is not None:
                    year_return += float(ret) * weight
                    valid_weights += weight

            if valid_weights > 0:
                year_return = year_return / valid_weights
                annual_returns.append(float(year_return))

        if not annual_returns:
            return PortfolioPerformance(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0, years=0
            )

        # Time-varying risk-free rate from database
        rf_rates = []
        for year in range(start_year, end_year + 1):
            rf = await self.get_risk_free_rate(year)
            rf_rates.append(rf)
        avg_rf = float(np.mean(rf_rates)) if rf_rates else self.DEFAULT_RISK_FREE_RATE

        total_return = float(np.prod([1 + r for r in annual_returns]) - 1)
        annualized_return = float(np.mean(annual_returns))
        volatility = float(np.std(annual_returns, ddof=1)) if len(annual_returns) > 1 else 0

        excess_return = annualized_return - avg_rf
        sharpe_ratio = float(excess_return / volatility) if volatility > 0 else 0

        cumulative = np.cumprod([1 + r for r in annual_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns))

        return PortfolioPerformance(
            total_return=round(total_return * 100, 2),
            annualized_return=round(annualized_return * 100, 2),
            volatility=round(volatility * 100, 2),
            sharpe_ratio=round(sharpe_ratio, 3),
            max_drawdown=round(max_drawdown * 100, 2),
            years=len(annual_returns)
        )

    async def calculate_benchmark_returns(
        self,
        benchmark_type: str,
        start_year: int,
        end_year: int
    ) -> PortfolioPerformance:
        """
        Calculate benchmark performance.

        Types:
        - "sp500": S&P 500 proxy (equal weight of all companies)
        - "equal_weight": Equal weight S&P 500
        - "sector_matched": Match sector weights to portfolio
        """
        result = await self.session.execute(
            select(FMPAnnualReturn.symbol).distinct()
        )
        all_symbols = [r[0] for r in result.fetchall()]

        if not all_symbols:
            return PortfolioPerformance(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0, years=0
            )

        weights = [1.0 / len(all_symbols)] * len(all_symbols)

        return await self.calculate_portfolio_returns(
            all_symbols, weights, start_year, end_year
        )

    async def get_sector_allocation(
        self,
        holdings: List[PortfolioHolding]
    ) -> List[Dict]:
        """Get sector allocation of portfolio."""
        sector_weights: Dict[str, float] = {}

        for h in holdings:
            sector_weights[h.sector] = sector_weights.get(h.sector, 0) + h.weight

        return [
            {"sector": s, "weight": round(w * 100, 2)}
            for s, w in sorted(sector_weights.items(), key=lambda x: -x[1])
        ]
