# Core computation mixin: single-symbol July-June return calculation.
import logging
from typing import List, Dict, Optional
from datetime import date
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FMPDailyPrice, FMPDividend, SP500HistoricalConstituent
from app.services.return_calculator.constants import (
    SQRT_252, MIN_TRADING_DAYS, MIN_TRADING_DAYS_REMOVED_IN_WINDOW,
    PRICE_MODE_TOTAL_RETURN_DIVIDENDS, PRICE_MODE_PRICE_ONLY,
    PRICE_MODE_ADJ_CLOSE_ONLY, PRICE_MODE_ADJ_CLOSE_FALLBACK_CLOSE,
)
from app.services.return_calculator.models import JulyJuneReturnResult

logger = logging.getLogger(__name__)


class ComputeMixin:
    """Mixin providing core July-June return computation for a single symbol."""

    session: AsyncSession
    data_tier: str
    price_mode: str
    _removed_dates_by_symbol: Optional[Dict[str, List[date]]]

    async def _ensure_removed_dates_cache(self) -> None:
        """Cache index-removal dates to allow shorter histories for delisted/acquired symbols."""
        if self._removed_dates_by_symbol is not None:
            return
        result = await self.session.execute(
            select(SP500HistoricalConstituent.symbol, SP500HistoricalConstituent.removed_date)
            .where(SP500HistoricalConstituent.removed_date.isnot(None))
        )
        mapping: Dict[str, List[date]] = {}
        for symbol, removed_date in result.fetchall():
            if symbol and removed_date:
                mapping.setdefault(str(symbol), []).append(removed_date)
        self._removed_dates_by_symbol = mapping

    async def compute_july_june_return(
        self,
        symbol: str,
        formation_year: int
    ) -> Optional[JulyJuneReturnResult]:
        """Compute July-June return for a single symbol and formation year.
        For formation_year=2019: returns July 1, 2020 to June 30, 2021.
        """
        return_start_year = formation_year + 1
        return_end_year = formation_year + 2
        start_date = date(return_start_year, 7, 1)
        end_date = date(return_end_year, 6, 30)

        await self._ensure_removed_dates_cache()
        removed_dates = (self._removed_dates_by_symbol or {}).get(symbol, [])
        is_removed_in_window = any(
            (start_date <= d <= end_date) for d in removed_dates
        )
        min_days_required = (
            MIN_TRADING_DAYS_REMOVED_IN_WINDOW if is_removed_in_window else MIN_TRADING_DAYS
        )

        if self.data_tier != "tier1":
            raise ValueError(
                f"JulyJuneReturnCalculator supports Tier-1 (FMPDailyPrice) only. Got data_tier={self.data_tier!r}."
            )
        # Normalize legacy price_mode strings
        effective_price_mode = self.price_mode
        if self.price_mode == PRICE_MODE_ADJ_CLOSE_ONLY:
            effective_price_mode = PRICE_MODE_TOTAL_RETURN_DIVIDENDS
        elif self.price_mode == PRICE_MODE_ADJ_CLOSE_FALLBACK_CLOSE:
            effective_price_mode = PRICE_MODE_PRICE_ONLY

        include_dividends = effective_price_mode == PRICE_MODE_TOTAL_RETURN_DIVIDENDS

        result = await self.session.execute(
            select(
                FMPDailyPrice.date,
                FMPDailyPrice.close,
                FMPDividend.adj_dividend,
                FMPDividend.dividend,
            )
            .outerjoin(
                FMPDividend,
                and_(
                    FMPDividend.symbol == FMPDailyPrice.symbol,
                    FMPDividend.date == FMPDailyPrice.date,
                ),
            )
            .where(
                FMPDailyPrice.symbol == symbol,
                FMPDailyPrice.date >= start_date,
                FMPDailyPrice.date <= end_date,
                FMPDailyPrice.close.isnot(None),
                FMPDailyPrice.close > 0,
            )
            .order_by(FMPDailyPrice.date)
        )
        rows = result.fetchall()

        price_list: List[float] = []
        dividend_list: List[float] = []
        dividend_days = 0
        adj_close_days = 0
        close_fallback_days = 0

        for r in rows:
            close = float(r.close) if r.close is not None else None
            if close is not None and close > 0:
                price_list.append(close)
                close_fallback_days += 1
                div = None
                if r.adj_dividend is not None:
                    div = float(r.adj_dividend)
                elif r.dividend is not None:
                    div = float(r.dividend)
                div = div if (div is not None and div > 0) else 0.0
                dividend_list.append(div)
                if div > 0:
                    dividend_days += 1

        trading_days = len(price_list)
        if trading_days < min_days_required:
            logger.debug(
                f"Insufficient data for {symbol} formation year {formation_year}: {trading_days} days "
                f"(price_mode={self.price_mode}, removed_in_window={is_removed_in_window})"
            )
            return None

        july_start_price = price_list[0]
        june_end_price = price_list[-1]

        if trading_days <= 1:
            total_return = 0.0
            annualized_volatility = 0.0
        else:
            daily_returns = []
            for i in range(1, trading_days):
                numerator = price_list[i]
                if include_dividends:
                    numerator += dividend_list[i]
                daily_returns.append((numerator / price_list[i - 1]) - 1.0)
            total_return = float(np.prod([1.0 + r for r in daily_returns]) - 1.0)
            daily_std = float(np.std(daily_returns)) if len(daily_returns) > 1 else 0.0
            annualized_volatility = daily_std * SQRT_252

        annualized_return = float(total_return)
        return JulyJuneReturnResult(
            symbol=symbol,
            formation_year=formation_year,
            july_start_price=july_start_price,
            june_end_price=june_end_price,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=annualized_volatility,
            trading_days=trading_days,
            price_mode=effective_price_mode,
            adj_close_days=adj_close_days,
            close_fallback_days=close_fallback_days,
            dividend_days=dividend_days,
        )
