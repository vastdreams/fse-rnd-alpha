"""
PATH: research/backend/app/services/portfolio_optimizer/forecast.py
PURPOSE: Forecast-vs-actual comparison and baseline R&D premium retrieval
WHY: Separates projection/forecast logic from core selection and backtesting
DEPENDENCIES:
  - app.db.models: ORM models for rolling-window results and returns
  - .models: shared dataclasses
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    RollingWindowResult, FMPAnnualReturn, JulyJuneReturn,
)

from .models import PortfolioHolding

logger = logging.getLogger(__name__)


async def _get_baseline_rd_premium_pct(
    session: AsyncSession,
    *,
    window_type: str,
    return_convention: str,
    data_tier: str = "tier1",
) -> float:
    """
    Get the baseline Q5-Q1 premium (percentage points) from stored rolling-window aggregates.

    IMPORTANT:
      - Reads pre-computed RollingWindowResult rows (publication pipeline output).
      - Powers portfolio "projection"/"forecast" UI features without hardcoding numbers.

    Args:
        session: DB session
        window_type: "5yr" / "10yr" / "20yr"
        return_convention: "july_june" or "calendar"
        data_tier: "tier1" or "tier2"

    Returns:
        Premium in percentage points (e.g., 7.11 means +7.11% per year).
        Returns 0.0 if inputs are unavailable.
    """
    result = await session.execute(
        select(RollingWindowResult.quintile, func.avg(RollingWindowResult.avg_return))
        .where(
            RollingWindowResult.window_type == window_type,
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == data_tier,
            RollingWindowResult.quintile.in_([1, 5]),
            RollingWindowResult.avg_return.isnot(None),
        )
        .group_by(RollingWindowResult.quintile)
    )
    rows = result.fetchall()
    by_q = {int(q): float(avg) for q, avg in rows if q is not None and avg is not None}
    if 1 not in by_q or 5 not in by_q:
        return 0.0
    return float(by_q[5] - by_q[1])


class ForecastMixin:
    """
    Mixin providing forecast-vs-actual comparison for PortfolioOptimizer.

    Expects the composing class to set:
      - self.session: AsyncSession
      - self.use_july_june: bool
    And provide (via other mixins):
      - self.select_top_rd_companies_for_year()
    """

    session: AsyncSession
    use_july_june: bool

    async def get_forecast_vs_actual(
        self,
        as_of_year: int,
        n_holdings: int = 20,
        method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None
    ) -> Dict:
        """
        Compare forecasted returns (based on R&D premium) vs actual returns.

        If as_of_year is in the past, we can compare what we would have
        forecasted vs what actually happened.
        """
        current_year = datetime.now().year

        holdings = await self.select_top_rd_companies_for_year(
            as_of_year=as_of_year,
            n=n_holdings,
            method=method,
            sectors=sectors
        )

        symbols = [h.symbol for h in holdings]
        weights = [h.weight for h in holdings]

        # Baseline premium from stored rolling-window results
        return_convention = "july_june" if self.use_july_june else "calendar"
        premium_pct = await _get_baseline_rd_premium_pct(
            self.session,
            window_type="5yr",
            return_convention=return_convention,
            data_tier="tier1",
        )
        premium = premium_pct / 100.0  # pct points -> decimal

        # Benchmark return for the period
        if self.use_july_june:
            formation_year = as_of_year - 1
            bench_result = await self.session.execute(
                select(func.avg(JulyJuneReturn.annualized_return))
                .where(
                    JulyJuneReturn.formation_year == formation_year,
                    JulyJuneReturn.data_tier == "tier1",
                    JulyJuneReturn.annualized_return.isnot(None),
                )
            )
            bench_raw = bench_result.scalar()
            benchmark_return = float(bench_raw) if bench_raw is not None else 0.08
        else:
            bench_result = await self.session.execute(
                select(func.avg(FMPAnnualReturn.annual_return))
                .where(FMPAnnualReturn.year == as_of_year)
            )
            bench_raw = bench_result.scalar()
            benchmark_return = float(bench_raw) if bench_raw is not None else 0.08

        # Projection: benchmark + baseline premium
        forecast_return = benchmark_return + premium

        # Calculate actual portfolio return
        actual_return = 0.0
        valid_w = 0.0
        for symbol, weight in zip(symbols, weights):
            if self.use_july_june:
                formation_year = as_of_year - 1
                result = await self.session.execute(
                    select(JulyJuneReturn.annualized_return)
                    .where(
                        JulyJuneReturn.symbol == symbol,
                        JulyJuneReturn.formation_year == formation_year,
                        JulyJuneReturn.data_tier == "tier1",
                    )
                )
                r = result.scalar()
            else:
                result = await self.session.execute(
                    select(FMPAnnualReturn.annual_return)
                    .where(
                        FMPAnnualReturn.symbol == symbol,
                        FMPAnnualReturn.year == as_of_year
                    )
                )
                r = result.scalar()
            if r is not None:
                actual_return += float(r) * weight
                valid_w += weight

        if valid_w > 0:
            actual_return = actual_return / valid_w

        is_historical = as_of_year < current_year
        forecast_error = (actual_return - forecast_return) if is_historical else None

        return {
            "year": as_of_year,
            "is_historical": is_historical,
            "forecast_return": round(forecast_return * 100, 2),
            "actual_return": round(actual_return * 100, 2) if is_historical else None,
            "benchmark_return": round(benchmark_return * 100, 2),
            "forecast_premium": round(premium * 100, 2),
            "forecast_error": round(forecast_error * 100, 2) if forecast_error is not None else None,
            "holdings_count": len(holdings),
            "avg_rd_intensity": round(sum(h.rd_intensity for h in holdings) / len(holdings), 2) if holdings else 0,
            "top_holdings": [
                {"symbol": h.symbol, "sector": h.sector, "rd_intensity": round(h.rd_intensity, 1)}
                for h in holdings[:5]
            ]
        }
