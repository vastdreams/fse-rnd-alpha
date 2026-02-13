"""
PATH: backend/app/services/rolling_window/_models.py
PURPOSE: Data models for rolling window analysis results
WHY: Shared dataclasses used across all rolling-window sub-modules
"""

from dataclasses import dataclass
from typing import List


@dataclass
class QuintileResult:
    """Result for a single quintile in a window."""
    quintile: int
    n_companies: int
    symbols: List[str]
    avg_rd_intensity: float
    median_rd_intensity: float
    avg_return: float
    median_return: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float  # Maximum drawdown in percent (e.g., -25.0 means -25%)
