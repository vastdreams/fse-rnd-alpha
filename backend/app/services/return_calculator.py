"""
PATH: backend/app/services/return_calculator.py
PURPOSE:
  - Computes July-June returns per Fama-French convention
  - Eliminates look-ahead bias in portfolio formation
  - Uses daily price data to calculate returns and volatility

ROLE IN ARCHITECTURE:
  - Core computation service for research-grade returns
  - Used by momentum and volatility services
  - Populates JulyJuneReturn table

MAIN EXPORTS:
  - JulyJuneReturnCalculator: Main computation class

NON-RESPONSIBILITIES:
  - Does not handle portfolio construction (see portfolio_optimizer.py)
  - Does not compute scoring (see rd_alpha_scorer.py)

NOTES FOR FUTURE AI:
  - Fama-French convention: July T to June T+1 for FY(T-1) data
  - formation_year refers to the fiscal year data used, not the return period
  - Uses adj_close for TOTAL RETURNS (includes dividends and splits)
  - Falls back to close if adj_close not available
  - PUBLICATION FIX (Dec 2025): Switched from close to adj_close for academic standards
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from dataclasses import dataclass
import numpy as np
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import FMPDailyPrice, JulyJuneReturn, FMPAnnualReturn

logger = logging.getLogger(__name__)


# ==============================================================================
# Constants
# ==============================================================================

TRADING_DAYS_PER_YEAR = 252
SQRT_252 = np.sqrt(TRADING_DAYS_PER_YEAR)

# Minimum trading days required for valid return calculation
MIN_TRADING_DAYS = 200  # ~80% of a year


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class JulyJuneReturnResult:
    """Result of July-June return calculation."""
    symbol: str
    formation_year: int
    july_start_price: float
    june_end_price: float
    total_return: float
    annualized_return: float
    volatility: float
    trading_days: int


# ==============================================================================
# July-June Return Calculator
# ==============================================================================

class JulyJuneReturnCalculator:
    """
    Computes July-June returns per Fama-French convention.
    
    Timeline Example:
    - FY 2019 ends Dec 31, 2019
    - 10-K filed by March 2020
    - Portfolio formed July 1, 2020 (formation_year = 2019)
    - Returns measured July 1, 2020 - June 30, 2021
    
    This ensures no look-ahead bias: when forming portfolios in July 2020,
    we only use FY 2019 data which was publicly available by March 2020.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def compute_july_june_return(
        self,
        symbol: str,
        formation_year: int
    ) -> Optional[JulyJuneReturnResult]:
        """
        Compute July-June return for a single symbol and formation year.
        
        Args:
            symbol: Stock ticker
            formation_year: The fiscal year data used (e.g., 2019)
                           Returns are July(formation_year+1) to June(formation_year+2)
        
        Returns:
            JulyJuneReturnResult or None if insufficient data
        """
        # Calculate date range
        # For formation_year = 2019: July 1, 2020 to June 30, 2021
        return_start_year = formation_year + 1
        return_end_year = formation_year + 2
        
        start_date = date(return_start_year, 7, 1)
        end_date = date(return_end_year, 6, 30)
        
        # Get all daily prices in the period
        # CRITICAL FIX: Use adj_close for TOTAL RETURNS (includes dividends and splits)
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
                # At least one price must exist
                (FMPDailyPrice.adj_close.isnot(None)) | (FMPDailyPrice.close.isnot(None)),
                (FMPDailyPrice.adj_close > 0) | (FMPDailyPrice.close > 0)
            )
            .order_by(FMPDailyPrice.date)
        )
        
        prices = result.fetchall()
        
        if len(prices) < MIN_TRADING_DAYS:
            logger.debug(f"Insufficient data for {symbol} formation year {formation_year}: {len(prices)} days")
            return None
        
        # Extract prices (using adjusted close for total return calculation)
        price_list = [float(p.price) for p in prices]
        
        july_start_price = price_list[0]
        june_end_price = price_list[-1]
        
        # Calculate total return
        total_return = (june_end_price / july_start_price) - 1
        
        # Annualize (assuming ~252 trading days)
        days = len(prices)
        years = days / TRADING_DAYS_PER_YEAR
        annualized_return = ((1 + total_return) ** (1 / years)) - 1 if years > 0 else 0
        
        # Calculate volatility from daily returns
        daily_returns = np.diff(price_list) / price_list[:-1]
        daily_std = np.std(daily_returns) if len(daily_returns) > 1 else 0
        annualized_volatility = daily_std * SQRT_252
        
        return JulyJuneReturnResult(
            symbol=symbol,
            formation_year=formation_year,
            july_start_price=july_start_price,
            june_end_price=june_end_price,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=annualized_volatility,
            trading_days=days
        )
    
    async def compute_all_july_june_returns(
        self,
        start_formation_year: int,
        end_formation_year: int,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict[int, JulyJuneReturnResult]]:
        """
        Batch compute July-June returns for all symbols.
        
        Args:
            start_formation_year: First formation year (inclusive)
            end_formation_year: Last formation year (inclusive)
            symbols: Optional list of symbols to process (None = all with data)
        
        Returns:
            Dict[symbol, Dict[formation_year, JulyJuneReturnResult]]
        """
        # Get all symbols with daily price data if not specified
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
        """
        Save computed returns to database.
        
        Returns:
            Number of records saved
        """
        count = 0
        
        for symbol, year_results in results.items():
            for year, ret in year_results.items():
                # Upsert logic
                stmt = insert(JulyJuneReturn).values(
                    symbol=ret.symbol,
                    formation_year=ret.formation_year,
                    july_start_price=ret.july_start_price,
                    june_end_price=ret.june_end_price,
                    total_return=ret.total_return,
                    annualized_return=ret.annualized_return,
                    volatility=ret.volatility,
                    trading_days=ret.trading_days,
                    created_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=["symbol", "formation_year"],
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
        formation_year: int
    ) -> Optional[JulyJuneReturn]:
        """Get cached July-June return from database."""
        result = await self.session.execute(
            select(JulyJuneReturn).where(
                JulyJuneReturn.symbol == symbol,
                JulyJuneReturn.formation_year == formation_year
            )
        )
        return result.scalar_one_or_none()
    
    async def get_market_return(
        self,
        formation_year: int,
        market_symbol: str = "SPY"
    ) -> Optional[float]:
        """
        Get market (S&P 500) return for the July-June period.
        
        Uses SPY as proxy for S&P 500.
        """
        ret = await self.get_july_june_return(market_symbol, formation_year)
        if ret:
            return ret.total_return
        
        # Fallback: compute on the fly
        result = await self.compute_july_june_return(market_symbol, formation_year)
        return result.total_return if result else None

