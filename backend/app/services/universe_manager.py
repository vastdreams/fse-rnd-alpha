"""
PATH: backend/app/services/universe_manager.py
PURPOSE:
  - Manages different stock universes (S&P 500, Russell 1000, Russell 3000)
  - Provides sector composition data for each universe
  - Enables broader selection beyond S&P 500

ROLE IN ARCHITECTURE:
  - Data source for RDAlphaScorer universe selection
  - Used by portfolio API for universe-specific analysis

MAIN EXPORTS:
  - UniverseManager: Main class for universe operations
  - UNIVERSE_DEFINITIONS: Static universe metadata

NON-RESPONSIBILITIES:
  - Does not fetch real-time constituent lists (uses database)
  - Does not handle individual company data

NOTES FOR FUTURE AI:
  - Russell indices reconstitute annually in June
  - Consider adding API integration for live constituent lists
  - Sector weights should be updated quarterly
"""

import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SP500Company, ResearchCohort, FMPIncomeStatement

logger = logging.getLogger(__name__)


# ==============================================================================
# Universe Definitions
# ==============================================================================

UNIVERSE_DEFINITIONS = {
    "sp500": {
        "name": "S&P 500",
        "description": "500 largest US companies by market cap",
        "approximate_size": 500,
        "market_cap_threshold": "Large Cap ($10B+)",
        "reconstitution": "Quarterly (March, June, September, December)",
        "index_provider": "S&P Dow Jones Indices",
    },
    "russell1000": {
        "name": "Russell 1000",
        "description": "1000 largest US companies by market cap",
        "approximate_size": 1000,
        "market_cap_threshold": "Large + Mid Cap",
        "reconstitution": "Annual (June)",
        "index_provider": "FTSE Russell",
    },
    "russell3000": {
        "name": "Russell 3000",
        "description": "3000 largest US companies by market cap",
        "approximate_size": 3000,
        "market_cap_threshold": "Large + Mid + Small Cap",
        "reconstitution": "Annual (June)",
        "index_provider": "FTSE Russell",
    },
    "all": {
        "name": "All Companies",
        "description": "All companies with R&D data in database",
        "approximate_size": None,
        "market_cap_threshold": "Any",
        "reconstitution": "N/A",
        "index_provider": "Internal Database",
    },
}

# Sector weights by universe (approximate, based on index composition)
# These are estimates and should be updated periodically
UNIVERSE_SECTOR_WEIGHTS = {
    "sp500": {
        "Technology": 0.295,
        "Information Technology": 0.295,
        "Healthcare": 0.125,
        "Health Care": 0.125,
        "Financials": 0.130,
        "Consumer Discretionary": 0.105,
        "Communication Services": 0.085,
        "Industrials": 0.085,
        "Consumer Staples": 0.060,
        "Energy": 0.040,
        "Utilities": 0.025,
        "Real Estate": 0.025,
        "Materials": 0.025,
    },
    "russell1000": {
        "Technology": 0.280,
        "Information Technology": 0.280,
        "Healthcare": 0.130,
        "Health Care": 0.130,
        "Financials": 0.125,
        "Consumer Discretionary": 0.110,
        "Communication Services": 0.080,
        "Industrials": 0.095,
        "Consumer Staples": 0.055,
        "Energy": 0.045,
        "Utilities": 0.025,
        "Real Estate": 0.030,
        "Materials": 0.025,
    },
    "russell3000": {
        "Technology": 0.260,
        "Information Technology": 0.260,
        "Healthcare": 0.140,
        "Health Care": 0.140,
        "Financials": 0.120,
        "Consumer Discretionary": 0.115,
        "Communication Services": 0.075,
        "Industrials": 0.105,
        "Consumer Staples": 0.050,
        "Energy": 0.050,
        "Utilities": 0.025,
        "Real Estate": 0.035,
        "Materials": 0.025,
    },
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class UniverseInfo:
    """Metadata about a stock universe."""
    code: str
    name: str
    description: str
    approximate_size: Optional[int]
    market_cap_threshold: str
    reconstitution: str
    index_provider: str
    actual_count: int = 0
    with_rd_data: int = 0


@dataclass
class UniverseSectorBreakdown:
    """Sector composition of a universe."""
    universe: str
    sector: str
    target_weight: float       # Index weight
    actual_count: int          # Companies in our database
    with_rd_data: int          # Companies with R&D data
    coverage_pct: float        # % of sector covered


@dataclass
class UniverseCompany:
    """Company in a universe with key metrics."""
    symbol: str
    name: str
    sector: str
    market_cap: Optional[float]
    has_rd_data: bool
    rd_intensity: Optional[float]


# ==============================================================================
# Universe Manager
# ==============================================================================

class UniverseManager:
    """
    Manages stock universes for ETF selection.
    
    Supports:
    - S&P 500 (current default)
    - Russell 1000 (mid + large cap)
    - Russell 3000 (small + mid + large cap)
    - All companies in database
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_universe_info(self, universe: str = "sp500") -> UniverseInfo:
        """
        Get metadata about a specific universe.
        
        Args:
            universe: Universe code ("sp500", "russell1000", "russell3000", "all")
            
        Returns:
            UniverseInfo with metadata and current counts
        """
        if universe not in UNIVERSE_DEFINITIONS:
            raise ValueError(f"Unknown universe: {universe}. Valid: {list(UNIVERSE_DEFINITIONS.keys())}")
        
        defn = UNIVERSE_DEFINITIONS[universe]
        
        # Get actual counts from database
        if universe == "sp500":
            actual_count = await self._count_sp500_companies()
            with_rd = await self._count_sp500_with_rd()
        elif universe == "all":
            actual_count = await self._count_all_companies()
            with_rd = await self._count_all_with_rd()
        else:
            # Russell universes - use all companies as proxy for now
            # In production, would filter by market cap
            actual_count = await self._count_all_companies()
            with_rd = await self._count_all_with_rd()
        
        return UniverseInfo(
            code=universe,
            name=defn["name"],
            description=defn["description"],
            approximate_size=defn["approximate_size"],
            market_cap_threshold=defn["market_cap_threshold"],
            reconstitution=defn["reconstitution"],
            index_provider=defn["index_provider"],
            actual_count=actual_count,
            with_rd_data=with_rd,
        )
    
    async def get_available_universes(self) -> List[UniverseInfo]:
        """Get info on all available universes."""
        universes = []
        for code in UNIVERSE_DEFINITIONS:
            info = await self.get_universe_info(code)
            universes.append(info)
        return universes
    
    async def get_universe_companies(
        self,
        universe: str = "sp500",
        with_rd_only: bool = True
    ) -> List[str]:
        """
        Get list of company symbols in a universe.
        
        Args:
            universe: Universe code
            with_rd_only: Only include companies with R&D data
            
        Returns:
            List of ticker symbols
        """
        if universe == "sp500":
            return await self._get_sp500_symbols(with_rd_only)
        elif universe == "all":
            return await self._get_all_symbols(with_rd_only)
        else:
            # Russell universes - use all with R&D as proxy
            return await self._get_all_symbols(with_rd_only)
    
    async def get_universe_sectors(
        self,
        universe: str = "sp500"
    ) -> List[UniverseSectorBreakdown]:
        """
        Get sector breakdown for a universe.
        
        Returns target weights and actual coverage.
        """
        target_weights = UNIVERSE_SECTOR_WEIGHTS.get(
            universe, 
            UNIVERSE_SECTOR_WEIGHTS["sp500"]
        )
        
        # Get actual sector counts from database
        if universe == "sp500":
            sector_counts = await self._get_sp500_sector_counts()
        else:
            sector_counts = await self._get_all_sector_counts()
        
        breakdowns = []
        for sector, weight in target_weights.items():
            # Skip alternate names (handled as primary)
            if sector in ["Information Technology", "Health Care"]:
                continue
            
            counts = sector_counts.get(sector, {"total": 0, "with_rd": 0})
            
            breakdowns.append(UniverseSectorBreakdown(
                universe=universe,
                sector=sector,
                target_weight=weight,
                actual_count=counts["total"],
                with_rd_data=counts["with_rd"],
                coverage_pct=counts["with_rd"] / max(counts["total"], 1) * 100,
            ))
        
        # Sort by target weight descending
        breakdowns.sort(key=lambda x: x.target_weight, reverse=True)
        
        return breakdowns
    
    def get_sector_weight(self, universe: str, sector: str) -> float:
        """Get target weight for a specific sector in a universe."""
        weights = UNIVERSE_SECTOR_WEIGHTS.get(universe, UNIVERSE_SECTOR_WEIGHTS["sp500"])
        return weights.get(sector, 0.05)  # Default 5%
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    async def _count_sp500_companies(self) -> int:
        """Count S&P 500 companies in database."""
        result = await self.session.execute(
            select(func.count(SP500Company.symbol))
        )
        return result.scalar() or 0
    
    async def _count_sp500_with_rd(self) -> int:
        """Count S&P 500 companies with R&D data."""
        result = await self.session.execute(
            select(func.count(distinct(ResearchCohort.symbol))).where(
                ResearchCohort.avg_rd_intensity > 0
            )
        )
        return result.scalar() or 0
    
    async def _count_all_companies(self) -> int:
        """Count all companies with financial data."""
        result = await self.session.execute(
            select(func.count(distinct(FMPIncomeStatement.symbol)))
        )
        return result.scalar() or 0
    
    async def _count_all_with_rd(self) -> int:
        """Count all companies with R&D data."""
        result = await self.session.execute(
            select(func.count(distinct(FMPIncomeStatement.symbol))).where(
                FMPIncomeStatement.rd_expenses > 0
            )
        )
        return result.scalar() or 0
    
    async def _get_sp500_symbols(self, with_rd_only: bool) -> List[str]:
        """Get S&P 500 company symbols."""
        if with_rd_only:
            # Join with research cohort
            result = await self.session.execute(
                select(ResearchCohort.symbol).where(
                    ResearchCohort.avg_rd_intensity > 0
                )
            )
        else:
            result = await self.session.execute(
                select(SP500Company.symbol)
            )
        return [row[0] for row in result.fetchall()]
    
    async def _get_all_symbols(self, with_rd_only: bool) -> List[str]:
        """Get all company symbols."""
        if with_rd_only:
            result = await self.session.execute(
                select(distinct(FMPIncomeStatement.symbol)).where(
                    FMPIncomeStatement.rd_expenses > 0
                )
            )
        else:
            result = await self.session.execute(
                select(distinct(FMPIncomeStatement.symbol))
            )
        return [row[0] for row in result.fetchall()]
    
    async def _get_sp500_sector_counts(self) -> Dict[str, Dict[str, int]]:
        """Get sector counts for S&P 500."""
        # Total by sector
        total_result = await self.session.execute(
            select(
                SP500Company.sector,
                func.count(SP500Company.symbol)
            ).group_by(SP500Company.sector)
        )
        totals = {row[0]: {"total": row[1], "with_rd": 0} for row in total_result.fetchall()}
        
        # With R&D data
        rd_result = await self.session.execute(
            select(
                ResearchCohort.sector,
                func.count(ResearchCohort.symbol)
            ).where(
                ResearchCohort.avg_rd_intensity > 0
            ).group_by(ResearchCohort.sector)
        )
        
        for row in rd_result.fetchall():
            sector = row[0]
            if sector in totals:
                totals[sector]["with_rd"] = row[1]
            else:
                totals[sector] = {"total": row[1], "with_rd": row[1]}
        
        return totals
    
    async def _get_all_sector_counts(self) -> Dict[str, Dict[str, int]]:
        """Get sector counts for all companies."""
        # Use research cohort for consistent sector data
        result = await self.session.execute(
            select(
                ResearchCohort.sector,
                func.count(ResearchCohort.symbol)
            ).group_by(ResearchCohort.sector)
        )
        
        return {
            row[0]: {"total": row[1], "with_rd": row[1]} 
            for row in result.fetchall()
        }
    
    async def get_universe_expansion_requirements(
        self,
        target_universe: str = "russell3000"
    ) -> Dict:
        """
        Get requirements for expanding to a larger universe.
        
        Returns:
            Dict with data requirements, gaps, and recommendations
        """
        if target_universe not in UNIVERSE_DEFINITIONS:
            raise ValueError(f"Unknown universe: {target_universe}")
        
        current_info = await self.get_universe_info("sp500")
        target_defn = UNIVERSE_DEFINITIONS[target_universe]
        
        # Estimate additional data needed
        if target_universe == "russell1000":
            additional_companies = 500  # ~500 more than S&P 500
            estimated_with_rd = int(additional_companies * 0.4)  # ~40% report R&D
        elif target_universe == "russell3000":
            additional_companies = 2500  # ~2500 more than S&P 500
            estimated_with_rd = int(additional_companies * 0.35)  # Higher pct of small caps don't report
        else:
            additional_companies = 0
            estimated_with_rd = 0
        
        return {
            "current_universe": {
                "code": "sp500",
                "companies_with_data": current_info.actual_count,
                "companies_with_rd": current_info.with_rd_data,
            },
            "target_universe": {
                "code": target_universe,
                "name": target_defn["name"],
                "approximate_size": target_defn["approximate_size"],
            },
            "expansion_requirements": {
                "additional_companies_needed": additional_companies,
                "estimated_with_rd_data": estimated_with_rd,
                "data_source_options": [
                    {
                        "source": "FMP API (current)",
                        "endpoint": "/api/v3/financial-statements/income-statement/{symbol}",
                        "cost": "API call quota",
                        "coverage": "Good for public companies",
                    },
                    {
                        "source": "SEC EDGAR",
                        "endpoint": "https://www.sec.gov/cgi-bin/browse-edgar",
                        "cost": "Free",
                        "coverage": "All US public companies, requires parsing",
                    },
                    {
                        "source": "Compustat (WRDS)",
                        "endpoint": "Via WRDS subscription",
                        "cost": "Academic subscription",
                        "coverage": "Complete historical data",
                    },
                ],
            },
            "implementation_steps": [
                "1. Obtain Russell 3000 constituent list (FTSE Russell or Bloomberg)",
                "2. Fetch income statements for all additional companies from FMP API",
                "3. Store in FMPIncomeStatement table with sector classification",
                "4. Run compute_research_metrics.py to populate caches",
                "5. Update UniverseManager.get_universe_companies() to filter by market cap",
                "6. Test analysis with expanded universe",
            ],
            "estimated_effort": {
                "api_calls": additional_companies * 20,  # ~20 years per company
                "database_storage_mb": int(additional_companies * 0.1),  # ~0.1MB per company
                "processing_time_hours": 2 + (additional_companies / 1000),
            },
            "research_considerations": [
                "Russell 3000 includes small-caps with higher trading costs",
                "Small-cap R&D firms have less analyst coverage (potentially higher mispricing)",
                "Transaction cost analysis becomes more critical for small-caps",
                "Consider separate analysis for large-cap vs small-cap subsets",
            ],
        }


# ==============================================================================
# API-Ready Universe Configuration
# ==============================================================================

def get_supported_universes() -> List[str]:
    """Get list of supported universe codes."""
    return list(UNIVERSE_DEFINITIONS.keys())


def get_universe_config(universe: str) -> Dict:
    """Get full configuration for a universe."""
    if universe not in UNIVERSE_DEFINITIONS:
        raise ValueError(f"Unknown universe: {universe}")
    
    return {
        **UNIVERSE_DEFINITIONS[universe],
        "sector_weights": UNIVERSE_SECTOR_WEIGHTS.get(universe, {}),
    }
