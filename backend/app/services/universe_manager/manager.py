"""
PATH: backend/app/services/universe_manager/manager.py
PURPOSE: UniverseManager class — public API for universe operations
WHY: Orchestrates universe queries, sector breakdown, and expansion planning
FLOW:
  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
  │ universe str │ →  │ UniverseManager  │ →  │ UniverseInfo / List  │
  └──────────────┘    └──────────────────┘    └──────────────────────┘
DEPENDENCIES:
  - definitions.py: UNIVERSE_DEFINITIONS, UNIVERSE_SECTOR_WEIGHTS, data classes
  - queries_mixin.py: private DB query methods
RELATED:
  - definitions.py: static data
  - queries_mixin.py: DB access layer
"""

import logging
from typing import List, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.universe_manager.definitions import (
    UNIVERSE_DEFINITIONS,
    UNIVERSE_SECTOR_WEIGHTS,
    UniverseInfo,
    UniverseSectorBreakdown,
)
from app.services.universe_manager.queries_mixin import UniverseQueriesMixin

logger = logging.getLogger(__name__)


# ==============================================================================
# Universe Manager
# ==============================================================================

class UniverseManager(UniverseQueriesMixin):
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
