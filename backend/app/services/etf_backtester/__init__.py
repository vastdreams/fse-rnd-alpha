"""
PATH: backend/app/services/etf_backtester/__init__.py
PURPOSE: Re-export all public symbols from the etf_backtester package.
"""

from app.services.etf_backtester.backtester import ETFBacktester
from app.services.etf_backtester.data_classes import (
    MonthlyReturn,
    MonthlyPortfolioReturn,
    PerformanceMetrics,
    TurnoverMetrics,
    Holding,
    MonthlyBacktestResult,
    FORMATION_MONTH,
    DEFAULT_RISK_FREE_RATE,
    BENCHMARK_SYMBOL,
)

__all__ = [
    "ETFBacktester",
    "MonthlyReturn",
    "MonthlyPortfolioReturn",
    "PerformanceMetrics",
    "TurnoverMetrics",
    "Holding",
    "MonthlyBacktestResult",
    "FORMATION_MONTH",
    "DEFAULT_RISK_FREE_RATE",
    "BENCHMARK_SYMBOL",
]
