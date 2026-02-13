"""
PATH: backend/app/services/etf_backtester/price_data_mixin.py
PURPOSE: Mixin providing price/return data access for the ETF backtester.
WHY: Isolates all database I/O (price lookups, delisting data, risk-free rates, FF factors) from analytics logic.
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from calendar import monthrange

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FMPDailyPrice,
    DelistingReturn,
    FamaFrenchFactor,
    RiskFreeRate,
)
from app.services.etf_backtester.data_classes import (
    Holding,
    DEFAULT_RISK_FREE_RATE,
)


class PriceDataMixin:
    """
    Mixin that provides price / return data access methods.

    Expects the consumer class to define:
        self.session: AsyncSession
        self._rf_cache: Dict[int, float]
        self._price_cache: Dict[Tuple[str, int, int], Optional[float]]
        self._delisting_cache: Dict[str, date]
    """

    async def _load_delistings(self, holdings_by_year: Dict[int, List[Holding]]):
        """Pre-load delisting data for all symbols."""
        all_symbols = set()
        for holdings in holdings_by_year.values():
            for h in holdings:
                all_symbols.add(h.symbol)

        if not all_symbols:
            return

        result = await self.session.execute(
            select(
                DelistingReturn.symbol,
                DelistingReturn.delist_date,
            )
            .where(DelistingReturn.symbol.in_(all_symbols))
        )

        for symbol, delist_date in result.fetchall():
            if symbol and delist_date:
                self._delisting_cache[str(symbol)] = delist_date

    async def _get_monthly_return(
        self,
        symbol: str,
        year: int,
        month: int,
    ) -> Optional[float]:
        """Get monthly return for a symbol from price data."""
        cache_key = (symbol, year, month)
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        # Get month-end and previous month-end prices
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)

        if month == 1:
            prev_month_end = date(year - 1, 12, 31)
        else:
            _, prev_last = monthrange(year, month - 1)
            prev_month_end = date(year, month - 1, prev_last)

        # Query for closest prices to month-end dates
        end_price = await self._get_price_near_date(symbol, month_end)
        start_price = await self._get_price_near_date(symbol, prev_month_end)

        if end_price is None or start_price is None or start_price <= 0:
            self._price_cache[cache_key] = None
            return None

        ret = (end_price - start_price) / start_price
        self._price_cache[cache_key] = ret
        return ret

    async def _get_price_near_date(
        self,
        symbol: str,
        target_date: date,
        window_days: int = 5,
    ) -> Optional[float]:
        """Get adjusted close price near a target date."""
        result = await self.session.execute(
            select(FMPDailyPrice.adj_close, FMPDailyPrice.close)
            .where(
                FMPDailyPrice.symbol == symbol,
                FMPDailyPrice.date >= target_date - timedelta(days=window_days),
                FMPDailyPrice.date <= target_date,
            )
            .order_by(FMPDailyPrice.date.desc())
            .limit(1)
        )
        row = result.fetchone()

        if row:
            return float(row[0]) if row[0] else (float(row[1]) if row[1] else None)
        return None

    async def _get_ff_market_return(self, year: int, month: int) -> Optional[float]:
        """Get S&P 500 return from Fama-French factors."""
        result = await self.session.execute(
            select(FamaFrenchFactor.mkt_rf, FamaFrenchFactor.rf)
            .where(
                FamaFrenchFactor.frequency == "monthly",
                func.extract("year", FamaFrenchFactor.date) == year,
                func.extract("month", FamaFrenchFactor.date) == month,
            )
            .limit(1)
        )
        row = result.fetchone()

        if row and row[0] is not None and row[1] is not None:
            return float(row[0]) + float(row[1])
        return None

    async def _get_risk_free_rate(self, year: int) -> float:
        """Get annual risk-free rate."""
        if year in self._rf_cache:
            return self._rf_cache[year]

        result = await self.session.execute(
            select(func.avg(RiskFreeRate.rate_annual_pct))
            .where(
                RiskFreeRate.date >= date(year, 1, 1),
                RiskFreeRate.date <= date(year, 12, 31),
            )
        )
        avg_rate = result.scalar()

        if avg_rate is not None:
            rate = float(avg_rate) / 100
        else:
            rate = DEFAULT_RISK_FREE_RATE

        self._rf_cache[year] = rate
        return rate
