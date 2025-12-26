"""
PATH: backend/app/services/rd_alpha_scorer.py
PURPOSE:
  - Research-based R&D Alpha scoring engine for ETF selection
  - Implements sector-agnostic weighting to prevent tech/biotech overconcentration
  - Integrates findings from Papers 1-4 into a unified selection formula

ROLE IN ARCHITECTURE:
  - Core scoring service for ETF portfolio construction
  - Used by portfolio_optimizer.py and portfolio API endpoints

MAIN EXPORTS:
  - RDAlphaScore: Dataclass for individual company scores
  - RDAlphaScorer: Main scoring engine class

NON-RESPONSIBILITIES:
  - Does not handle portfolio backtesting (see portfolio_optimizer.py)
  - Does not manage market forecasts (see market_forecasts.py)

NOTES FOR FUTURE AI:
  - The formula weights are calibrated based on research findings
  - Sector adjustments prevent natural tech/biotech overweight
  - Update SP500_SECTOR_WEIGHTS periodically from S&P data
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from sqlalchemy import select, func, desc, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ResearchCohort, FMPIncomeStatement, 
    FMPAnnualReturn, SP500Company,
    MomentumCache, VolatilityCache
)
from app.services.sanity_checks import (
    cap_rd_intensity, 
    MIN_REVENUE_THRESHOLD,
    MAX_RD_INTENSITY_ABSOLUTE,
    HIGH_RD_SECTORS
)
from app.services.momentum_service import MomentumCalculator
from app.services.volatility_service import VolatilityCalculator
from app.core.logging import get_logger
from app.core.formulas import validate_formula_output

logger = get_logger(__name__)


# ==============================================================================
# S&P 500 Sector Weights (Updated Dec 2024)
# ==============================================================================

# Based on S&P 500 GICS sector composition
# Source: S&P Dow Jones Indices
SP500_SECTOR_WEIGHTS = {
    "Technology": 0.295,           # ~29.5% - Largest sector
    "Information Technology": 0.295,  # Alternate name
    "Healthcare": 0.125,           # ~12.5%
    "Health Care": 0.125,          # Alternate name
    "Financials": 0.130,           # ~13.0%
    "Consumer Discretionary": 0.105,  # ~10.5%
    "Communication Services": 0.085,  # ~8.5%
    "Industrials": 0.085,          # ~8.5%
    "Consumer Staples": 0.060,     # ~6.0%
    "Energy": 0.040,               # ~4.0%
    "Utilities": 0.025,            # ~2.5%
    "Real Estate": 0.025,          # ~2.5%
    "Materials": 0.025,            # ~2.5%
    "Basic Materials": 0.025,      # Alternate name
}

# Sector-specific R&D intensity caps (based on Paper 1 findings)
SECTOR_RD_CAPS = {
    "Healthcare": 2.00,            # 200% - biotech can have high R&D
    "Health Care": 2.00,
    "Biotechnology": 2.00,
    "Pharmaceuticals": 2.00,
    "Technology": 1.00,            # 100%
    "Information Technology": 1.00,
    "default": 1.00,               # 100% for all others
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class RDAlphaScore:
    """
    Complete scoring breakdown for a single company.
    
    The final_score combines:
    - R&D intensity (primary factor from Paper 1)
    - Sector adjustment (prevents overconcentration from Paper 2)
    - Momentum factor (R&D premium persistence from Paper 3)
    - Quality score (data reliability)
    - Volatility normalization (risk adjustment from Paper 4)
    """
    symbol: str
    name: str
    sector: str
    industry: Optional[str] = None
    
    # Component scores
    rd_intensity: float = 0.0              # Raw R&D/Revenue ratio
    rd_intensity_capped: float = 0.0       # After sector-specific cap
    sector_adjustment: float = 1.0         # Diversification factor
    momentum_factor: float = 1.0           # Based on prior performance
    quality_score: float = 1.0             # Data quality (0-1)
    volatility: float = 0.20               # 3-year historical volatility
    
    # Final outputs
    raw_score: float = 0.0                 # Before sector constraints
    final_score: float = 0.0               # After all adjustments
    weight: float = 0.0                    # Portfolio weight
    selection_rank: int = 0                # Rank in selection
    
    # Metadata
    years_of_data: int = 0
    latest_revenue: float = 0.0
    latest_rd_expense: float = 0.0


@dataclass 
class SectorWeight:
    """Sector weight target vs actual."""
    sector: str
    target_weight: float      # Based on S&P 500 with adjustments
    actual_weight: float      # Current portfolio weight
    min_weight: float         # Floor constraint
    max_weight: float         # Ceiling constraint
    company_count: int        # Number of companies from this sector
    adjustment_needed: float  # Positive = add, negative = reduce


@dataclass
class SelectionMethodology:
    """Complete methodology documentation."""
    formula: str
    formula_latex: str
    components: Dict[str, str]
    sector_constraints: Dict[str, Dict[str, float]]
    research_citations: List[str]
    parameters: Dict[str, float]
    last_updated: str


# ==============================================================================
# R&D Alpha Scorer
# ==============================================================================

class RDAlphaScorer:
    """
    Research-based scoring engine for R&D Alpha ETF selection.
    
    Formula:
    R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility
    
    Where:
    - RD_Intensity = min(R&D/Revenue, Sector_Cap)
    - Sector_Adj = SP500_Sector_Weight / HighRD_Sector_Weight
    - Momentum = 1 + (Prior_3yr_Excess_Return × 0.1)
    - Quality = Data_Quality_Score / 100
    - Volatility = Historical_3yr_StdDev (floored at 0.10)
    """
    
    # Portfolio constraints
    MAX_SECTOR_WEIGHT = 0.25       # No sector > 25%
    MIN_SECTOR_WEIGHT = 0.02       # At least 2% per included sector
    MIN_COMPANIES_PER_SECTOR = 1   # At least 1 company per included sector
    DEFAULT_VOLATILITY = 0.25      # Default if no volatility data
    VOLATILITY_FLOOR = 0.10       # Minimum volatility to prevent extreme scores
    
    # Momentum bounds (from Paper 3)
    MIN_MOMENTUM_FACTOR = 0.5
    MAX_MOMENTUM_FACTOR = 2.0
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._momentum_calculator: Optional[MomentumCalculator] = None
        self._volatility_calculator: Optional[VolatilityCalculator] = None
    
    @property
    def momentum_calculator(self) -> MomentumCalculator:
        """Lazy initialization of momentum calculator."""
        if self._momentum_calculator is None:
            self._momentum_calculator = MomentumCalculator(self.session)
        return self._momentum_calculator
    
    @property
    def volatility_calculator(self) -> VolatilityCalculator:
        """Lazy initialization of volatility calculator."""
        if self._volatility_calculator is None:
            self._volatility_calculator = VolatilityCalculator(self.session)
        return self._volatility_calculator
    
    async def calculate_alpha_scores(
        self,
        universe: str = "sp500",
        as_of_year: Optional[int] = None,
        min_years_data: int = 3,
        min_revenue: float = MIN_REVENUE_THRESHOLD
    ) -> List[RDAlphaScore]:
        """
        Calculate R&D Alpha scores for all eligible companies.
        
        Args:
            universe: "sp500", "russell1000", or "russell3000"
            as_of_year: Point-in-time year for selection (None = latest)
            min_years_data: Minimum years of R&D data required
            min_revenue: Minimum revenue threshold
            
        Returns:
            List of RDAlphaScore objects, sorted by final_score descending
            
        SURVIVORSHIP BIAS FIX (Dec 2025):
            When as_of_year is provided, filters by historical S&P 500 constituents
            to ensure only companies that were in the index at that time are included.
            This prevents look-ahead bias from including future IPOs like HOOD, COIN, MRNA.
        """
        import time
        from datetime import date
        start_time = time.perf_counter()
        
        logger.log_step(
            "Calculate R&D Alpha Scores",
            step_number=1,
            total_steps=3,
            data={"universe": universe, "as_of_year": as_of_year}
        )
        
        # SURVIVORSHIP BIAS FIX: Get point-in-time S&P 500 constituents
        # This prevents including companies like HOOD, COIN, MRNA in historical backtests
        # when they weren't public/in the index yet
        historical_constituents: Optional[set] = None
        if as_of_year is not None:
            from app.db.models import SP500HistoricalConstituent
            point_in_time_date = date(as_of_year, 7, 1)  # July 1 of selection year (Fama-French convention)
            try:
                hist_result = await self.session.execute(
                    select(SP500HistoricalConstituent.symbol)
                    .where(
                        SP500HistoricalConstituent.added_date <= point_in_time_date,
                        (SP500HistoricalConstituent.removed_date == None) | 
                        (SP500HistoricalConstituent.removed_date >= point_in_time_date)
                    )
                )
                historical_constituents = {r[0] for r in hist_result.fetchall() if r[0]}
                
                if historical_constituents:
                    logger.info(f"Point-in-time filter: {len(historical_constituents)} S&P 500 constituents as of {as_of_year}")
                else:
                    # No historical data - fall back to using all companies but log warning
                    logger.warning(f"No historical S&P 500 data for {as_of_year} - backtest may have survivorship bias")
                    historical_constituents = None
            except Exception as e:
                logger.warning(f"Could not load historical constituents: {e} - backtest may have survivorship bias")
                historical_constituents = None
        
        # Get eligible companies from research cohort
        query = select(ResearchCohort).where(
            ResearchCohort.years_with_data >= min_years_data,
            ResearchCohort.avg_rd_intensity > 0
        )
        
        # Apply historical constituent filter if available
        if historical_constituents:
            query = query.where(ResearchCohort.symbol.in_(historical_constituents))
        
        result = await self.session.execute(query)
        cohort_companies = result.scalars().all()
        
        logger.log_db_query(
            operation="SELECT",
            table="research_cohort",
            rows_affected=len(cohort_companies),
            duration_ms=(time.perf_counter() - start_time) * 1000
        )
        
        # Calculate sector representation in high-R&D universe
        sector_counts = {}
        for c in cohort_companies:
            sector = c.sector or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        total_companies = len(cohort_companies)
        high_rd_sector_weights = {
            s: count / total_companies 
            for s, count in sector_counts.items()
        }
        
        scores = []
        
        for company in cohort_companies:
            score = await self._calculate_company_score(
                company,
                high_rd_sector_weights,
                as_of_year
            )
            if score:
                scores.append(score)
        
        # Sort by final score descending
        scores.sort(key=lambda x: x.final_score, reverse=True)
        
        # Assign ranks
        for i, score in enumerate(scores):
            score.selection_rank = i + 1
        
        logger.log_step(
            "Scores calculated and ranked",
            step_number=3,
            total_steps=3,
            data={
                "total_scored": len(scores),
                "top_score": scores[0].final_score if scores else 0,
                "sectors_represented": len(set(s.sector for s in scores))
            },
            duration_ms=(time.perf_counter() - start_time) * 1000
        )
        
        return scores
    
    async def _calculate_company_score(
        self,
        company: ResearchCohort,
        high_rd_sector_weights: Dict[str, float],
        as_of_year: Optional[int] = None
    ) -> Optional[RDAlphaScore]:
        """Calculate score for a single company."""
        
        sector = company.sector or "Unknown"
        
        # 1. R&D Intensity (capped by sector)
        rd_intensity = float(company.avg_rd_intensity) if company.avg_rd_intensity else 0.0
        sector_cap = SECTOR_RD_CAPS.get(sector, SECTOR_RD_CAPS["default"])
        rd_intensity_capped = min(rd_intensity / 100.0, sector_cap)  # Convert from % to ratio
        
        if rd_intensity_capped <= 0:
            return None
        
        # 2. Sector Adjustment Factor
        # Penalizes sectors that are overrepresented in high-R&D universe
        sp500_weight = SP500_SECTOR_WEIGHTS.get(sector, 0.05)  # Default 5%
        high_rd_weight = high_rd_sector_weights.get(sector, 0.10)  # Default 10%
        
        # Adjustment: sectors overrepresented get lower adjustment
        # Tech is ~30% of S&P but ~50% of high-R&D, so adjustment = 0.30/0.50 = 0.6
        sector_adjustment = min(sp500_weight / max(high_rd_weight, 0.01), 2.0)
        
        # 3. Momentum Factor (from Paper 3 - Pricing Factor research)
        # Uses real 3-year excess returns vs benchmark
        momentum_factor = await self._get_real_momentum(
            company.symbol, 
            as_of_year or datetime.now().year
        )
        
        # 4. Quality Score (existing metric)
        quality_score = float(company.data_quality_score or 50) / 100.0
        
        # 5. Volatility (from Paper 4 - Value Creation research)
        # Uses real 3-year historical volatility from daily prices
        volatility = await self._get_real_volatility(
            company.symbol,
            as_of_year or datetime.now().year
        )
        
        # Calculate raw score
        raw_score = (
            rd_intensity_capped * 
            sector_adjustment * 
            momentum_factor * 
            quality_score
        ) / volatility
        
        return RDAlphaScore(
            symbol=company.symbol,
            name=company.name or company.symbol,
            sector=sector,
            industry=None,  # Would need additional data
            rd_intensity=rd_intensity,
            rd_intensity_capped=rd_intensity_capped * 100,  # Back to percentage for display
            sector_adjustment=sector_adjustment,
            momentum_factor=momentum_factor,
            quality_score=quality_score,
            volatility=volatility,
            raw_score=raw_score,
            final_score=raw_score,  # Will be adjusted in apply_sector_constraints
            weight=0.0,
            selection_rank=0,
            years_of_data=company.years_with_data or 0,
            latest_revenue=0.0,  # Would need to fetch
            latest_rd_expense=0.0,  # Would need to fetch
        )
    
    async def _get_real_momentum(
        self,
        symbol: str,
        as_of_year: int
    ) -> float:
        """
        Get real momentum factor from cached or computed data.
        
        Uses 3-year prior excess returns vs benchmark (Paper 3 research).
        Falls back to neutral (1.0) if no data available.
        """
        try:
            # Try to get from cache first
            cached = await self.session.execute(
                select(MomentumCache.momentum_factor)
                .where(
                    MomentumCache.symbol == symbol,
                    MomentumCache.as_of_year == as_of_year
                )
            )
            result = cached.scalar_one_or_none()
            
            if result is not None:
                return max(self.MIN_MOMENTUM_FACTOR, min(self.MAX_MOMENTUM_FACTOR, result))
            
            # Compute on-the-fly if not cached
            momentum = await self.momentum_calculator.compute_momentum(symbol, as_of_year)
            if momentum:
                return momentum.momentum_factor
            
        except Exception as e:
            logger.debug(f"Error getting momentum for {symbol}: {e}")
        
        # Return neutral if no data
        return 1.0
    
    async def _get_real_volatility(
        self,
        symbol: str,
        as_of_year: int
    ) -> float:
        """
        Get real volatility from cached or computed data.
        
        Uses 3-year trailing daily returns (Paper 4 research).
        Falls back to default (0.25) if no data available.
        """
        try:
            # Try to get from cache first
            cached = await self.session.execute(
                select(VolatilityCache.volatility_3yr)
                .where(
                    VolatilityCache.symbol == symbol,
                    VolatilityCache.as_of_year == as_of_year
                )
            )
            result = cached.scalar_one_or_none()
            
            if result is not None:
                return max(self.VOLATILITY_FLOOR, result)
            
            # Compute on-the-fly if not cached
            vol = await self.volatility_calculator.compute_volatility(symbol, as_of_year)
            if vol:
                return vol.volatility_3yr
            
        except Exception as e:
            logger.debug(f"Error getting volatility for {symbol}: {e}")
        
        # Return default if no data
        return self.DEFAULT_VOLATILITY
    
    async def apply_sector_constraints(
        self,
        scores: List[RDAlphaScore],
        n_holdings: int = 20
    ) -> Tuple[List[RDAlphaScore], List[SectorWeight]]:
        """
        Apply sector diversification constraints to selection.
        
        Ensures no single sector exceeds MAX_SECTOR_WEIGHT and
        attempts to include representation from multiple sectors.
        
        Returns:
            Tuple of (selected holdings, sector weight breakdown)
        """
        if not scores:
            return [], []
        
        # Calculate target sector weights
        sectors_in_universe = set(s.sector for s in scores)
        target_weights = {}
        
        for sector in sectors_in_universe:
            sp500_weight = SP500_SECTOR_WEIGHTS.get(sector, 0.05)
            target = min(sp500_weight * 1.5, self.MAX_SECTOR_WEIGHT)
            target_weights[sector] = {
                "target": target,
                "min": max(sp500_weight * 0.5, self.MIN_SECTOR_WEIGHT),
                "max": self.MAX_SECTOR_WEIGHT,
            }
        
        # Select companies with sector constraints
        selected = []
        sector_counts = {}
        sector_scores = {}
        
        for score in scores:
            sector = score.sector
            current_count = sector_counts.get(sector, 0)
            
            # Calculate how much weight this sector already has
            current_weight = current_count / n_holdings if n_holdings > 0 else 0
            
            # Check if sector is at max capacity
            if current_weight >= self.MAX_SECTOR_WEIGHT:
                continue
            
            # Add company
            selected.append(score)
            sector_counts[sector] = current_count + 1
            sector_scores[sector] = sector_scores.get(sector, []) + [score]
            
            if len(selected) >= n_holdings:
                break
        
        # Calculate final weights (equal weight within sector constraints)
        total_selected = len(selected)
        for score in selected:
            score.weight = 1.0 / total_selected if total_selected > 0 else 0.0
        
        # Build sector weight breakdown
        sector_weight_info = []
        for sector in sectors_in_universe:
            count = sector_counts.get(sector, 0)
            actual_weight = count / total_selected if total_selected > 0 else 0
            target_info = target_weights.get(sector, {"target": 0.05, "min": 0.02, "max": 0.25})
            
            sector_weight_info.append(SectorWeight(
                sector=sector,
                target_weight=target_info["target"],
                actual_weight=actual_weight,
                min_weight=target_info["min"],
                max_weight=target_info["max"],
                company_count=count,
                adjustment_needed=target_info["target"] - actual_weight,
            ))
        
        # Sort by actual weight descending
        sector_weight_info.sort(key=lambda x: x.actual_weight, reverse=True)
        
        # Update ranks for selected
        for i, score in enumerate(selected):
            score.selection_rank = i + 1
        
        return selected, sector_weight_info
    
    def get_selection_methodology(self) -> SelectionMethodology:
        """
        Return complete documentation of the selection methodology.
        
        Provides transparency on how companies are selected and weighted.
        """
        return SelectionMethodology(
            formula="R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility",
            formula_latex=r"\text{Score} = \frac{\text{RD}_{\text{cap}} \times \text{Sector}_{\text{adj}} \times \text{Momentum} \times \text{Quality}}{\sigma}",
            components={
                "RD_Intensity": "R&D Expense / Revenue, capped at sector-specific maximum (100% default, 200% for biotech/pharma). From Paper 1.",
                "Sector_Adjustment": "S&P 500 sector weight / High-R&D universe sector weight. Prevents tech/biotech overconcentration. From Paper 2.",
                "Momentum": "1 + (Prior 3-year excess return vs S&P 500 × 0.1). Uses real historical returns. From Paper 3.",
                "Quality": "Data quality score from 0-1. Based on years of data and consistency.",
                "Volatility": "3-year trailing annualized volatility from daily returns, floored at 10%. Uses real price data. From Paper 4.",
            },
            sector_constraints={
                "max_sector_weight": {"value": self.MAX_SECTOR_WEIGHT, "description": "No single sector > 25%"},
                "min_sector_weight": {"value": self.MIN_SECTOR_WEIGHT, "description": "Minimum 2% per included sector"},
                "momentum_bounds": {"value": f"{self.MIN_MOMENTUM_FACTOR}-{self.MAX_MOMENTUM_FACTOR}", "description": "Momentum factor capped between 0.5 and 2.0"},
            },
            research_citations=[
                "Paper 1: R&D intensity as primary alpha factor (Q5 outperforms Q1 by ~10% annually)",
                "Paper 2: Industry patterns - tech/biotech naturally dominate, requiring sector adjustment",
                "Paper 3: Pricing factor - R&D premium persists over time, using real 3-year excess returns",
                "Paper 4: Value Creation - volatility normalization using real 3-year daily price data",
                "Fama-French: July-June return convention for look-ahead bias elimination",
            ],
            parameters={
                "rd_cap_default": 1.0,
                "rd_cap_biotech": 2.0,
                "max_sector_weight": self.MAX_SECTOR_WEIGHT,
                "min_sector_weight": self.MIN_SECTOR_WEIGHT,
                "volatility_floor": self.VOLATILITY_FLOOR,
                "momentum_sensitivity": 0.1,
                "momentum_min": self.MIN_MOMENTUM_FACTOR,
                "momentum_max": self.MAX_MOMENTUM_FACTOR,
            },
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )
    
    async def get_all_candidates_with_scores(
        self,
        as_of_year: Optional[int] = None,
        limit: int = 100
    ) -> List[RDAlphaScore]:
        """
        Get all candidate companies with their scores for transparency.
        
        Returns full list so users can see why companies were/weren't selected.
        """
        scores = await self.calculate_alpha_scores(
            universe="sp500",
            as_of_year=as_of_year
        )
        return scores[:limit]

