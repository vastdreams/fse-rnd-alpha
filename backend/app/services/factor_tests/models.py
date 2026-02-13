"""
PATH: backend/app/services/factor_tests/models.py
PURPOSE: Dataclasses and type definitions for factor spanning tests
WHY: Shared types used across all factor test modules
"""

from typing import Dict
from dataclasses import dataclass


@dataclass
class SpanningTestResult:
    """Result from factor spanning test."""
    model_name: str  # e.g., "FF3", "FF5", "FF5+MOM"
    alpha: float     # Intercept (excess return)
    alpha_se: float  # Standard error (Newey-West)
    alpha_t: float   # t-statistic
    alpha_p: float   # p-value
    is_spanned: bool  # True if alpha is NOT significant (can be explained by factors)
    r_squared: float
    n_observations: int
    factor_loadings: Dict[str, float]  # Beta coefficients
    factor_t_stats: Dict[str, float]   # t-statistics for betas
