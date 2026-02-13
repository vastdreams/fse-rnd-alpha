# Core computation mixin: momentum factor calculation from prior 3-year returns.
import logging
from typing import List, Dict, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JulyJuneReturn, FMPAnnualReturn
from app.services.momentum_service.constants import (
    MOMENTUM_SENSITIVITY, MIN_MOMENTUM_FACTOR, MAX_MOMENTUM_FACTOR, MomentumResult,
)

logger = logging.getLogger(__name__)


class ComputeMixin:
    """Mixin providing core momentum computation from July-June or calendar returns."""

    session: AsyncSession
    data_tier: str
    _market_returns_cache: Dict[int, float]

    async def compute_momentum(
        self,
        symbol: str,
        as_of_year: int,
        use_july_june: bool = True
    ) -> Optional[MomentumResult]:
        """Compute momentum for a single symbol.
        Uses returns from (as_of_year - 3) to (as_of_year - 1).
        """
        years_needed = [as_of_year - 3, as_of_year - 2, as_of_year - 1]
        if use_july_june:
            returns = await self._get_july_june_returns(symbol, years_needed)
        else:
            returns = await self._get_calendar_returns(symbol, years_needed)
        if not returns:
            return None
        years_available = len(returns)
        cumulative = 1.0
        for year in sorted(returns.keys()):
            cumulative *= (1 + returns[year])
        cumulative_return = cumulative - 1
        benchmark_returns = await self._get_benchmark_returns(years_needed, use_july_june)
        benchmark_cumulative = 1.0
        for year in sorted(benchmark_returns.keys()):
            if year in returns:
                benchmark_cumulative *= (1 + benchmark_returns.get(year, 0.08))
        benchmark_return = benchmark_cumulative - 1
        excess_return = cumulative_return - benchmark_return
        annualized_return = ((1 + cumulative_return) ** (1 / years_available)) - 1 if years_available > 0 else 0
        annualized_excess = ((1 + excess_return) ** (1 / years_available)) - 1 if years_available > 0 and (1 + excess_return) > 0 else excess_return / max(years_available, 1)
        raw_momentum = 1.0 + (excess_return * MOMENTUM_SENSITIVITY)
        momentum_factor = max(MIN_MOMENTUM_FACTOR, min(MAX_MOMENTUM_FACTOR, raw_momentum))
        return MomentumResult(
            symbol=symbol,
            as_of_year=as_of_year,
            cumulative_return_3yr=cumulative_return,
            benchmark_return_3yr=benchmark_return,
            excess_return_3yr=excess_return,
            annualized_return=annualized_return,
            annualized_excess=annualized_excess,
            momentum_factor=momentum_factor,
            years_available=years_available
        )

    async def _get_july_june_returns(
        self, symbol: str, years: List[int]
    ) -> Dict[int, float]:
        """Get July-June returns from cache."""
        result = await self.session.execute(
            select(JulyJuneReturn.formation_year, JulyJuneReturn.total_return)
            .where(
                JulyJuneReturn.symbol == symbol,
                JulyJuneReturn.formation_year.in_(years),
                JulyJuneReturn.data_tier == self.data_tier,
                JulyJuneReturn.total_return.isnot(None)
            )
        )
        return {r[0]: r[1] for r in result.fetchall()}

    async def _get_calendar_returns(
        self, symbol: str, years: List[int]
    ) -> Dict[int, float]:
        """Get calendar-year returns from FMPAnnualReturn."""
        result = await self.session.execute(
            select(FMPAnnualReturn.year, FMPAnnualReturn.annual_return)
            .where(
                FMPAnnualReturn.symbol == symbol,
                FMPAnnualReturn.year.in_(years),
                FMPAnnualReturn.annual_return.isnot(None)
            )
        )
        return {r[0]: r[1] for r in result.fetchall()}

    async def _get_benchmark_returns(
        self,
        years: List[int],
        use_july_june: bool = True,
        market_symbol: str = "SPY"
    ) -> Dict[int, float]:
        """Get market benchmark returns via SPY. Falls back to 8% annual if no data."""
        if use_july_june:
            result = await self.session.execute(
                select(JulyJuneReturn.formation_year, JulyJuneReturn.total_return)
                .where(
                    JulyJuneReturn.symbol == market_symbol,
                    JulyJuneReturn.formation_year.in_(years),
                    JulyJuneReturn.data_tier == self.data_tier,
                    JulyJuneReturn.total_return.isnot(None)
                )
            )
        else:
            result = await self.session.execute(
                select(FMPAnnualReturn.year, FMPAnnualReturn.annual_return)
                .where(
                    FMPAnnualReturn.symbol == market_symbol,
                    FMPAnnualReturn.year.in_(years),
                    FMPAnnualReturn.annual_return.isnot(None)
                )
            )
        returns = {r[0]: r[1] for r in result.fetchall()}
        for year in years:
            if year not in returns:
                returns[year] = 0.08
        return returns
