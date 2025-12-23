"""
PATH: backend/app/services/volatility_service.py
PURPOSE:
  - Calculates volatility from historical price data
  - Based on Paper 4 findings: Risk normalization for scoring
  - Uses trailing 3-year daily returns

ROLE IN ARCHITECTURE:
  - Provides volatility data for RDAlphaScorer
  - Uses FMPDailyPrice data for granular calculation
  - Populates VolatilityCache table

MAIN EXPORTS:
  - VolatilityCalculator: Main computation class

NON-RESPONSIBILITIES:
  - Does not compute momentum (see momentum_service.py)
  - Does not handle portfolio scoring (see rd_alpha_scorer.py)

NOTES FOR FUTURE AI:
  - Annualized volatility = daily_std * sqrt(252)
  - Floor volatility at 10% to prevent extreme scores
  - Use trailing 3 years of data ending June 30 for consistency
  - Uses adj_close for TOTAL RETURN volatility (includes dividends and splits)
  - PUBLICATION FIX (Dec 2025): Switched from close to adj_close for academic standards
"""

import logging
from typing import List, Dict, Optional
from datetime import date, datetime
from dataclasses import dataclass
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import VolatilityCache, FMPDailyPrice

logger = logging.getLogger(__name__)


# ==============================================================================
# Constants
# ==============================================================================

TRADING_DAYS_PER_YEAR = 252
SQRT_252 = np.sqrt(TRADING_DAYS_PER_YEAR)

# 3 years of trading days
VOLATILITY_LOOKBACK_DAYS = 756

# Minimum trading days for valid calculation
MIN_TRADING_DAYS_VOLATILITY = 500  # ~2 years

# Volatility floor (from Paper 4 research)
VOLATILITY_FLOOR = 0.10  # 10% minimum

# Default volatility if no data
DEFAULT_VOLATILITY = 0.25  # 25%


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class VolatilityResult:
    """Result of volatility calculation."""
    symbol: str
    as_of_year: int
    volatility_3yr: float
    daily_std: float
    trading_days: int
    market_volatility: Optional[float] = None
    relative_volatility: Optional[float] = None


# ==============================================================================
# Volatility Calculator
# ==============================================================================

class VolatilityCalculator:
    """
    Calculates volatility from Paper 4 (Value Creation / Risk Normalization).
    
    Formula:
    - Daily returns = (P_t / P_{t-1}) - 1
    - Daily std = std(daily_returns) over trailing 756 days (3 years)
    - Annualized volatility = daily_std * sqrt(252)
    
    From Paper 4: "Risk normalization ensures high-volatility 
    companies don't dominate purely on R&D intensity."
    
    The volatility calculation ends on June 30 of the as_of_year to align
    with Fama-French portfolio formation convention.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._market_volatility_cache: Dict[int, float] = {}
    
    async def compute_volatility(
        self,
        symbol: str,
        as_of_year: int
    ) -> Optional[VolatilityResult]:
        """
        Compute volatility for a single symbol.
        
        Args:
            symbol: Stock ticker
            as_of_year: Year for which to compute volatility
                       Uses trailing 3 years of daily data ending June 30
        
        Returns:
            VolatilityResult or None if insufficient data
        """
        # Calculate date range (trailing 3 years ending June 30)
        end_date = date(as_of_year, 6, 30)
        start_date = date(as_of_year - 3, 7, 1)
        
        # Get daily prices
        # CRITICAL FIX: Use adj_close for consistent total return volatility
        # Falls back to close if adj_close not available
        result = await self.session.execute(
            select(
                FMPDailyPrice.date,
                func.coalesce(FMPDailyPrice.adj_close, FMPDailyPrice.close).label("price")
            )
            .where(
                FMPDailyPrice.symbol == symbol,
                FMPDailyPrice.date >= start_date,
                FMPDailyPrice.date <= end_date,
                (FMPDailyPrice.adj_close.isnot(None)) | (FMPDailyPrice.close.isnot(None)),
                (FMPDailyPrice.adj_close > 0) | (FMPDailyPrice.close > 0)
            )
            .order_by(FMPDailyPrice.date)
        )
        
        prices = result.fetchall()
        
        if len(prices) < MIN_TRADING_DAYS_VOLATILITY:
            logger.debug(f"Insufficient data for {symbol} volatility year {as_of_year}: {len(prices)} days")
            return None
        
        # Extract prices (using adjusted close for total return volatility)
        price_list = [float(p.price) for p in prices]
        daily_returns = np.diff(price_list) / price_list[:-1]
        
        # Calculate standard deviation
        daily_std = np.std(daily_returns)
        
        # Annualize
        volatility_3yr = daily_std * SQRT_252
        
        # Floor at minimum
        volatility_3yr = max(VOLATILITY_FLOOR, volatility_3yr)
        
        return VolatilityResult(
            symbol=symbol,
            as_of_year=as_of_year,
            volatility_3yr=volatility_3yr,
            daily_std=daily_std,
            trading_days=len(prices)
        )
    
    async def compute_volatility_with_market(
        self,
        symbol: str,
        as_of_year: int,
        market_symbol: str = "SPY"
    ) -> Optional[VolatilityResult]:
        """
        Compute volatility with market comparison.
        
        Returns volatility along with relative volatility (company/market).
        """
        result = await self.compute_volatility(symbol, as_of_year)
        if not result:
            return None
        
        # Get market volatility
        market_vol = await self._get_market_volatility(as_of_year, market_symbol)
        
        result.market_volatility = market_vol
        result.relative_volatility = result.volatility_3yr / market_vol if market_vol > 0 else 1.0
        
        return result
    
    async def _get_market_volatility(
        self,
        as_of_year: int,
        market_symbol: str = "SPY"
    ) -> float:
        """
        Get market (S&P 500) volatility.
        
        Uses SPY as proxy. Caches results.
        """
        if as_of_year in self._market_volatility_cache:
            return self._market_volatility_cache[as_of_year]
        
        result = await self.compute_volatility(market_symbol, as_of_year)
        
        if result:
            self._market_volatility_cache[as_of_year] = result.volatility_3yr
            return result.volatility_3yr
        
        # Default market volatility (~16% historical average)
        return 0.16
    
    async def precompute_all_volatility(
        self,
        start_year: int,
        end_year: int,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict[int, VolatilityResult]]:
        """
        Batch compute volatility for all symbols.
        
        Args:
            start_year: First as_of_year (needs 3 years prior data)
            end_year: Last as_of_year
            symbols: Optional list of symbols (None = all with data)
        
        Returns:
            Dict[symbol, Dict[as_of_year, VolatilityResult]]
        """
        # Get all symbols with daily price data
        if symbols is None:
            result = await self.session.execute(
                select(func.distinct(FMPDailyPrice.symbol))
            )
            symbols = [r[0] for r in result.fetchall()]
        
        logger.info(f"Computing volatility for {len(symbols)} symbols, "
                   f"years {start_year}-{end_year}")
        
        # Pre-compute market volatility for all years
        for year in range(start_year, end_year + 1):
            await self._get_market_volatility(year)
        
        results: Dict[str, Dict[int, VolatilityResult]] = {}
        
        for i, symbol in enumerate(symbols):
            if (i + 1) % 100 == 0:
                logger.info(f"Processing {i + 1}/{len(symbols)}")
            
            results[symbol] = {}
            
            for year in range(start_year, end_year + 1):
                vol = await self.compute_volatility_with_market(symbol, year)
                if vol:
                    results[symbol][year] = vol
        
        return results
    
    async def save_volatility_cache(
        self,
        results: Dict[str, Dict[int, VolatilityResult]]
    ) -> int:
        """
        Save computed volatility to database.
        
        Returns:
            Number of records saved
        """
        count = 0
        
        for symbol, year_results in results.items():
            for year, vol in year_results.items():
                stmt = insert(VolatilityCache).values(
                    symbol=vol.symbol,
                    as_of_year=vol.as_of_year,
                    volatility_3yr=vol.volatility_3yr,
                    daily_std=vol.daily_std,
                    trading_days=vol.trading_days,
                    market_volatility=vol.market_volatility,
                    relative_volatility=vol.relative_volatility,
                    created_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=["symbol", "as_of_year"],
                    set_={
                        "volatility_3yr": vol.volatility_3yr,
                        "daily_std": vol.daily_std,
                        "trading_days": vol.trading_days,
                        "market_volatility": vol.market_volatility,
                        "relative_volatility": vol.relative_volatility,
                    }
                )
                
                await self.session.execute(stmt)
                count += 1
        
        await self.session.commit()
        logger.info(f"Saved {count} volatility records")
        
        return count
    
    async def get_volatility(
        self,
        symbol: str,
        as_of_year: int
    ) -> Optional[VolatilityCache]:
        """Get cached volatility from database."""
        result = await self.session.execute(
            select(VolatilityCache).where(
                VolatilityCache.symbol == symbol,
                VolatilityCache.as_of_year == as_of_year
            )
        )
        return result.scalar_one_or_none()
    
    async def get_volatility_value(
        self,
        symbol: str,
        as_of_year: int,
        default: float = DEFAULT_VOLATILITY
    ) -> float:
        """
        Get volatility for scoring.
        
        Returns cached value or computes on-the-fly if not cached.
        Falls back to default (25%) if no data.
        """
        cached = await self.get_volatility(symbol, as_of_year)
        if cached and cached.volatility_3yr:
            return max(VOLATILITY_FLOOR, cached.volatility_3yr)
        
        # Compute on-the-fly
        result = await self.compute_volatility(symbol, as_of_year)
        if result:
            return result.volatility_3yr
        
        return default

