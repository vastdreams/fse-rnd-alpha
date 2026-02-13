"""
PATH: backend/app/services/rd_alpha_scorer/data_classes.py
PURPOSE: Dataclass definitions and sector-weight constants for the R&D Alpha scorer.
WHY: Extracted to break dependency cycles and keep each module under ~300 lines.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field


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
    rd_intensity: float = 0.0              # Raw R&D/Revenue ratio (%)
    rd_intensity_capped: float = 0.0       # After sector-specific cap (%)
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

    # Point-in-time tracking (Dec 2025)
    fiscal_year_used: Optional[int] = None  # FY(T-1) for backtest
    data_source: str = "cohort_avg"         # "cohort_avg" or "point_in_time"


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
