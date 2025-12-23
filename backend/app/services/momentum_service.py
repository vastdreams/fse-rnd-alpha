"""
PATH: backend/app/services/momentum_service.py
PURPOSE:
  - Calculates momentum factor based on Paper 3 findings
  - Computes 3-year prior excess returns vs benchmark
  - Rewards companies with consistent prior performance

ROLE IN ARCHITECTURE:
  - Provides momentum data for RDAlphaScorer
  - Uses JulyJuneReturn data for look-ahead bias-free calculation
  - Populates MomentumCache table

MAIN EXPORTS:
  - MomentumCalculator: Main computation class

NON-RESPONSIBILITIES:
  - Does not compute volatility (see volatility_service.py)
  - Does not handle portfolio scoring (see rd_alpha_scorer.py)

NOTES FOR FUTURE AI:
  - Momentum sensitivity of 0.1 is from Paper 3 research
  - Cap momentum factor between 0.5 and 2.0 to prevent extreme values
  - Use July-June returns for consistency with Fama-French
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import (
    MomentumCache, JulyJuneReturn, 
    FMPAnnualReturn, FMPDailyPrice
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Constants (from Paper 3 research)
# ==============================================================================

# Momentum sensitivity: how much weight to give excess returns
MOMENTUM_SENSITIVITY = 0.1  # 10% of excess return added to base factor

# Caps to prevent extreme values
MIN_MOMENTUM_FACTOR = 0.5
MAX_MOMENTUM_FACTOR = 2.0

# Years of prior returns for momentum calculation
MOMENTUM_LOOKBACK_YEARS = 3


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class MomentumResult:
    """Result of momentum calculation."""
    symbol: str
    as_of_year: int
    cumulative_return_3yr: float
    benchmark_return_3yr: float
    excess_return_3yr: float
    annualized_return: float
    annualized_excess: float
    momentum_factor: float
    years_available: int


# ==============================================================================
# Momentum Calculator
# ==============================================================================

class MomentumCalculator:
    """
    Calculates momentum factor based on Paper 3 findings.
    
    Formula from research:
    - Prior 3-year compound return for company
    - Compare to S&P 500 benchmark
    - Excess return = Company - Benchmark
    - Momentum Factor = 1 + (excess_return_3yr * SENSITIVITY)
    
    Paper 3 finding: "R&D premium persists over time (~10% annual, t-stat ~3.4)"
    This suggests past R&D outperformers tend to continue outperforming.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._market_returns_cache: Dict[int, float] = {}
    
    async def compute_momentum(
        self,
        symbol: str,
        as_of_year: int,
        use_july_june: bool = True
    ) -> Optional[MomentumResult]:
        """
        Compute momentum for a single symbol.
        
        Args:
            symbol: Stock ticker
            as_of_year: Year for which to compute momentum
                       Uses returns from (as_of_year - 3) to (as_of_year - 1)
            use_july_june: Use July-June returns (True) or calendar-year (False)
        
        Returns:
            MomentumResult or None if insufficient data
        """
        # Get returns for T-3, T-2, T-1
        years_needed = [as_of_year - 3, as_of_year - 2, as_of_year - 1]
        
        if use_july_june:
            returns = await self._get_july_june_returns(symbol, years_needed)
        else:
            returns = await self._get_calendar_returns(symbol, years_needed)
        
        if not returns:
            return None
        
        years_available = len(returns)
        
        # Calculate compound return
        cumulative = 1.0
        for year in sorted(returns.keys()):
            cumulative *= (1 + returns[year])
        cumulative_return = cumulative - 1
        
        # Get benchmark returns for same period
        benchmark_returns = await self._get_benchmark_returns(years_needed, use_july_june)
        benchmark_cumulative = 1.0
        for year in sorted(benchmark_returns.keys()):
            if year in returns:  # Only count years where we have company data
                benchmark_cumulative *= (1 + benchmark_returns.get(year, 0.08))
        benchmark_return = benchmark_cumulative - 1
        
        # Calculate excess return
        excess_return = cumulative_return - benchmark_return
        
        # Annualize
        annualized_return = ((1 + cumulative_return) ** (1 / years_available)) - 1 if years_available > 0 else 0
        annualized_excess = ((1 + excess_return) ** (1 / years_available)) - 1 if years_available > 0 and (1 + excess_return) > 0 else excess_return / max(years_available, 1)
        
        # Calculate momentum factor
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
        self,
        symbol: str,
        years: List[int]
    ) -> Dict[int, float]:
        """Get July-June returns from cache."""
        result = await self.session.execute(
            select(JulyJuneReturn.formation_year, JulyJuneReturn.total_return)
            .where(
                JulyJuneReturn.symbol == symbol,
                JulyJuneReturn.formation_year.in_(years),
                JulyJuneReturn.total_return.isnot(None)
            )
        )
        return {r[0]: r[1] for r in result.fetchall()}
    
    async def _get_calendar_returns(
        self,
        symbol: str,
        years: List[int]
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
        """
        Get market benchmark returns.
        
        Uses SPY as proxy for S&P 500.
        Falls back to 8% annual if no data.
        """
        if use_july_june:
            result = await self.session.execute(
                select(JulyJuneReturn.formation_year, JulyJuneReturn.total_return)
                .where(
                    JulyJuneReturn.symbol == market_symbol,
                    JulyJuneReturn.formation_year.in_(years),
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
        
        # Fill missing years with historical average (8%)
        for year in years:
            if year not in returns:
                returns[year] = 0.08
        
        return returns
    
    async def precompute_all_momentum(
        self,
        start_year: int,
        end_year: int,
        symbols: Optional[List[str]] = None,
        use_july_june: bool = True
    ) -> Dict[str, Dict[int, MomentumResult]]:
        """
        Batch compute momentum for all symbols.
        
        Args:
            start_year: First as_of_year (needs 3 years prior data)
            end_year: Last as_of_year
            symbols: Optional list of symbols (None = all with data)
            use_july_june: Use July-June returns
        
        Returns:
            Dict[symbol, Dict[as_of_year, MomentumResult]]
        """
        # Get all symbols with return data
        if symbols is None:
            if use_july_june:
                result = await self.session.execute(
                    select(func.distinct(JulyJuneReturn.symbol))
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
        """
        Save computed momentum to database.
        
        Returns:
            Number of records saved
        """
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
        """
        Get momentum factor for scoring.
        
        Returns cached value or computes on-the-fly if not cached.
        Falls back to default (neutral 1.0) if no data.
        """
        cached = await self.get_momentum(symbol, as_of_year)
        if cached and cached.momentum_factor:
            return cached.momentum_factor
        
        # Compute on-the-fly
        result = await self.compute_momentum(symbol, as_of_year)
        if result:
            return result.momentum_factor
        
        return default

