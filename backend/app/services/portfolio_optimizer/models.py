"""
PATH: research/backend/app/services/portfolio_optimizer/models.py
PURPOSE: Shared data models and constants for portfolio optimization
WHY: Centralizes dataclasses and constants used across all optimizer modules
DEPENDENCIES:
  - app.services.sanity_checks: canonical threshold values
"""

from dataclasses import dataclass

from app.services.sanity_checks import (
    MIN_REVENUE_THRESHOLD,
    MAX_RD_INTENSITY_ABSOLUTE,
)

# Minimum revenue for inclusion (filter out pre-revenue companies with extreme ratios)
MIN_REVENUE = MIN_REVENUE_THRESHOLD  # $100M

# Maximum R&D intensity cap (prevents outliers like 4800%)
MAX_RD_INTENSITY = MAX_RD_INTENSITY_ABSOLUTE  # 100%


@dataclass
class PortfolioHolding:
    """Single holding in the portfolio."""
    symbol: str
    name: str
    sector: str
    weight: float
    rd_intensity: float
    quality_score: float


@dataclass
class PortfolioPerformance:
    """Performance metrics for a portfolio."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    years: int
