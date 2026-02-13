# Batch computation and persistence mixin for July-June returns.
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import FMPDailyPrice, JulyJuneReturn
from app.services.return_calculator.models import JulyJuneReturnResult

logger = logging.getLogger(__name__)


class PersistenceMixin:
    """Mixin providing batch computation, persistence, and DB lookups for July-June returns."""

    session: AsyncSession
    data_tier: str

    async def compute_all_july_june_returns(
        self,
        start_formation_year: int,
        end_formation_year: int,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict[int, JulyJuneReturnResult]]:
        """Batch compute July-June returns for all symbols across formation years."""
        if symbols is None:
            result = await self.session.execute(
                select(func.distinct(FMPDailyPrice.symbol))
            )
            symbols = [r[0] for r in result.fetchall()]
        logger.info(f"Computing July-June returns for {len(symbols)} symbols, "
                   f"years {start_formation_year}-{end_formation_year}")
        results: Dict[str, Dict[int, JulyJuneReturnResult]] = {}
        for i, symbol in enumerate(symbols):
            if (i + 1) % 100 == 0:
                logger.info(f"Processing {i + 1}/{len(symbols)}")
            results[symbol] = {}
            for year in range(start_formation_year, end_formation_year + 1):
                ret = await self.compute_july_june_return(symbol, year)
                if ret:
                    results[symbol][year] = ret
        return results

    async def save_july_june_returns(
        self,
        results: Dict[str, Dict[int, JulyJuneReturnResult]]
    ) -> int:
        """Save computed returns to database. Returns number of records saved."""
        count = 0
        for symbol, year_results in results.items():
            for year, ret in year_results.items():
                stmt = insert(JulyJuneReturn).values(
                    symbol=ret.symbol,
                    formation_year=ret.formation_year,
                    data_tier=self.data_tier,
                    july_start_price=ret.july_start_price,
                    june_end_price=ret.june_end_price,
                    total_return=ret.total_return,
                    annualized_return=ret.annualized_return,
                    volatility=ret.volatility,
                    trading_days=ret.trading_days,
                    created_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=["symbol", "formation_year", "data_tier"],
                    set_={
                        "july_start_price": ret.july_start_price,
                        "june_end_price": ret.june_end_price,
                        "total_return": ret.total_return,
                        "annualized_return": ret.annualized_return,
                        "volatility": ret.volatility,
                        "trading_days": ret.trading_days,
                    }
                )
                await self.session.execute(stmt)
                count += 1
        await self.session.commit()
        logger.info(f"Saved {count} July-June return records")
        return count

    async def get_july_june_return(
        self,
        symbol: str,
        formation_year: int,
        *,
        data_tier: Optional[str] = None,
    ) -> Optional[JulyJuneReturn]:
        """Get cached July-June return from database."""
        effective_tier = data_tier or self.data_tier
        result = await self.session.execute(
            select(JulyJuneReturn).where(
                JulyJuneReturn.symbol == symbol,
                JulyJuneReturn.formation_year == formation_year,
                JulyJuneReturn.data_tier == effective_tier,
            )
        )
        return result.scalar_one_or_none()

    async def get_market_return(
        self,
        formation_year: int,
        market_symbol: str = "SPY"
    ) -> Optional[float]:
        """Get market (S&P 500) return for the July-June period via SPY."""
        ret = await self.get_july_june_return(market_symbol, formation_year)
        if ret:
            return ret.total_return
        result = await self.compute_july_june_return(market_symbol, formation_year)
        return result.total_return if result else None
