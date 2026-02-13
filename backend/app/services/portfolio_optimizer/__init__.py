"""
PATH: research/backend/app/services/portfolio_optimizer/__init__.py
PURPOSE: Re-export public API for backward-compatible imports
WHY: Consumers import from app.services.portfolio_optimizer — this preserves that contract

Public API:
  - PortfolioOptimizer: main class (selection + performance + forecast + backtest)
  - PortfolioHolding, PortfolioPerformance: data models
  - _get_baseline_rd_premium_pct: standalone helper for R&D premium lookup
"""

from .models import PortfolioHolding, PortfolioPerformance, MIN_REVENUE, MAX_RD_INTENSITY
from .optimizer import PortfolioOptimizer
from .forecast import _get_baseline_rd_premium_pct

__all__ = [
    "PortfolioOptimizer",
    "PortfolioHolding",
    "PortfolioPerformance",
    "MIN_REVENUE",
    "MAX_RD_INTENSITY",
    "_get_baseline_rd_premium_pct",
]
