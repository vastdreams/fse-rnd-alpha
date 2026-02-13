# Batch computation and persistence mixin for momentum data.
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import MomentumCache, JulyJuneReturn, FMPAnnualReturn
from app.services.momentum_service.constants import MomentumResult

logger = logging.getLogger(__name__)


class PersistenceMixin:
    """Mixin providing batch momentum computation, DB persistence, and cache lookups."""

    session: AsyncSession
    data_tier: str

    async def precompute_all_momentum(
        self,
        start_year: int,
        end_year: int,
        symbols: Optional[List[str]] = None,
        use_july_june: bool = True
    ) -> Dict[str, Dict[int, MomentumResult]]:
        """Batch compute momentum for all symbols across year range."""
        if symbols is None:
            if use_july_june:
                result = await self.session.execute(
                    select(func.distinct(JulyJuneReturn.symbol))
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
            else:
                result = await self.session.execute(
                    select(func.distinct(FMPAnnualReturn.symbol))
                )
            symbols = [r[0] for r in result.fetchall()]
        logger.info(f"Computing momentum for {len(symbols)} symbols, "
                   f"years {start_year}-{end_year}")
        results: Dict[str, Dict[int, MomentumResult]] = {}
        for i, symbol in enumerate(symbols):
            if (i + 1) % 100 == 0:
                logger.info(f"Processing {i + 1}/{len(symbols)}")
            results[symbol] = {}
            for year in range(start_year, end_year + 1):
                momentum = await self.compute_momentum(symbol, year, use_july_june)
                if momentum:
                    results[symbol][year] = momentum
        return results

    async def save_momentum_cache(
        self,
        results: Dict[str, Dict[int, MomentumResult]]
    ) -> int:
        """Save computed momentum to database. Returns number of records saved."""
        count = 0
        for symbol, year_results in results.items():
            for year, momentum in year_results.items():
                stmt = insert(MomentumCache).values(
                    symbol=momentum.symbol,
                    as_of_year=momentum.as_of_year,
                    cumulative_return_3yr=momentum.cumulative_return_3yr,
                    benchmark_return_3yr=momentum.benchmark_return_3yr,
                    excess_return_3yr=momentum.excess_return_3yr,
                    annualized_return=momentum.annualized_return,
                    annualized_excess=momentum.annualized_excess,
                    momentum_factor=momentum.momentum_factor,
                    years_available=momentum.years_available,
                    created_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=["symbol", "as_of_year"],
                    set_={
                        "cumulative_return_3yr": momentum.cumulative_return_3yr,
                        "benchmark_return_3yr": momentum.benchmark_return_3yr,
                        "excess_return_3yr": momentum.excess_return_3yr,
                        "annualized_return": momentum.annualized_return,
                        "annualized_excess": momentum.annualized_excess,
                        "momentum_factor": momentum.momentum_factor,
                        "years_available": momentum.years_available,
                    }
                )
                await self.session.execute(stmt)
                count += 1
        await self.session.commit()
        logger.info(f"Saved {count} momentum records")
        return count

    async def get_momentum(
        self,
        symbol: str,
        as_of_year: int
    ) -> Optional[MomentumCache]:
        """Get cached momentum from database."""
        result = await self.session.execute(
            select(MomentumCache).where(
                MomentumCache.symbol == symbol,
                MomentumCache.as_of_year == as_of_year
            )
        )
        return result.scalar_one_or_none()

    async def get_momentum_factor(
        self,
        symbol: str,
        as_of_year: int,
        default: float = 1.0
    ) -> float:
        """Get momentum factor for scoring. Returns cached, on-the-fly, or default (1.0)."""
        cached = await self.get_momentum(symbol, as_of_year)
        if cached and cached.momentum_factor:
            return cached.momentum_factor
        result = await self.compute_momentum(symbol, as_of_year)
        if result:
            return result.momentum_factor
        return default
