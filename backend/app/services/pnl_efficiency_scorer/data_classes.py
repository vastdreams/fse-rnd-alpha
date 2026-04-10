"""
PATH: backend/app/services/pnl_efficiency_scorer/data_classes.py
PURPOSE: Dataclass definitions for the PNL Efficiency Alpha scorer.
"""

from typing import Optional
from dataclasses import dataclass


PNL_COMPONENT_NAMES = {
    "gross_efficiency": "Gross Efficiency (1 - COGS/Revenue)",
    "overhead_efficiency": "Overhead Efficiency (1 - SGA/Revenue)",
    "operating_efficiency": "Operating Efficiency (1 - OpEx/Revenue)",
    "profit_conversion": "Profit Conversion (Net Income/Revenue)",
}


@dataclass
class PnlEfficiencyScore:
    """
    Complete scoring breakdown for a single company under PNL Efficiency Alpha.

    The composite score is an equal-weight average of four sector-relative
    z-scored components, winsorized at +/- 3 standard deviations.
    """
    symbol: str
    name: str
    sector: str
    industry: Optional[str] = None

    # Raw ratios (0-1 scale, higher is better for all after sign flip)
    gross_efficiency: float = 0.0
    overhead_efficiency: float = 0.0
    operating_efficiency: float = 0.0
    profit_conversion: float = 0.0

    # Sector-relative z-scores (winsorized)
    gross_efficiency_z: float = 0.0
    overhead_efficiency_z: float = 0.0
    operating_efficiency_z: float = 0.0
    profit_conversion_z: float = 0.0

    # Composite
    composite_z: float = 0.0
    sector_percentile: float = 0.0

    # Portfolio integration
    final_score: float = 0.0
    weight: float = 0.0
    selection_rank: int = 0

    # Source metadata
    revenue: float = 0.0
    fiscal_year_used: Optional[int] = None
    data_source: str = "fmp_income_statements"
    coverage_flags: int = 0  # bitmask: bit0=cogs, bit1=sga, bit2=opex, bit3=net_income
