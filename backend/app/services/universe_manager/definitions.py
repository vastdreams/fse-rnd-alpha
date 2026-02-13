"""
PATH: backend/app/services/universe_manager/definitions.py
PURPOSE: Static universe metadata, sector weights, and data classes
WHY: Pure data/schema definitions separated from DB queries and business logic
FLOW:
  ┌──────────────────────┐    ┌───────────────────────┐    ┌───────────────┐
  │ UNIVERSE_DEFINITIONS │ →  │ UNIVERSE_SECTOR_WGTS  │ →  │ Data classes  │
  └──────────────────────┘    └───────────────────────┘    └───────────────┘
DEPENDENCIES: None (pure data)
"""

from typing import Dict, Optional
from dataclasses import dataclass


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
