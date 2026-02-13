"""
PATH: research/backend/app/services/portfolio_optimizer/optimizer.py
PURPOSE: Main PortfolioOptimizer class composing all mixin capabilities
WHY: Single entry point that combines selection, performance, forecast, and backtest logic
FLOW:
  ┌────────────────┐   ┌──────────────────┐   ┌─────────────────┐   ┌────────────────┐
  │ SelectionMixin │ + │ PerformanceMixin │ + │  ForecastMixin  │ + │ BacktesterMixin│
  └────────────────┘   └──────────────────┘   └─────────────────┘   └────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │  PortfolioOptimizer  │
                    └──────────────────────┘
DEPENDENCIES:
  - .selection: company selection strategies
  - .performance: return/risk metric calculations
  - .forecast: forecast-vs-actual comparison
  - .backtester: full backtest engine
"""

from sqlalchemy.ext.asyncio import AsyncSession

from .selection import SelectionMixin
from .performance import PerformanceMixin
from .forecast import ForecastMixin
from .backtester import BacktesterMixin


class PortfolioOptimizer(
    SelectionMixin,
    PerformanceMixin,
    ForecastMixin,
    BacktesterMixin,
):
    """
    Optimizes R&D-focused portfolio construction.

    PUBLICATION FIX (Dec 2025):
    - Supports July-June returns (Fama-French convention) via use_july_june flag
    - Integrates delisting returns for survivorship bias correction
    - Uses standardized risk-free rate from RiskFreeRate table
    """

    # Default risk-free rate when database has no data
    DEFAULT_RISK_FREE_RATE = 0.02  # 2% annual

    def __init__(self, session: AsyncSession, use_july_june: bool = True):
        """
        Initialize portfolio optimizer.

        Args:
            session: Database session
            use_july_june: If True (default), use July-June returns (Fama-French convention)
                          to eliminate look-ahead bias. Set False for calendar year returns.
        """
        self.session = session
        self.use_july_june = use_july_june
        self._rf_cache = {}  # Cache for risk-free rates
