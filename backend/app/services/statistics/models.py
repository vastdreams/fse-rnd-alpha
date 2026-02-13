"""
PATH: backend/app/services/statistics/models.py
PURPOSE: Dataclass result types for statistical analysis module.
WHY: Shared across all mixin files; extracted to avoid circular imports.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AnovaTestResult:
    """Result from ANOVA test."""
    f_statistic: float
    p_value: float
    eta_squared: float
    omega_squared: float
    significant_005: bool
    significant_001: bool
    group_means: Dict[int, float]
    group_stds: Dict[int, float]
    group_ns: Dict[int, int]
    tukey_results: Optional[Dict]


@dataclass  
class TTestResult:
    """Result from t-test."""
    t_statistic: float
    p_value: float
    mean_diff: float
    effect_size: float  # Cohen's d
    significant: bool


@dataclass
class HACResult:
    """
    Result from HAC (Heteroskedasticity and Autocorrelation Consistent) adjusted t-test.
    
    Used for overlapping window analysis where observations are not independent.
    Newey-West standard errors account for serial correlation in the data.
    """
    mean: float
    std_error_hac: float
    t_statistic_hac: float
    p_value_hac: float
    significant: bool
    n_observations: int
    lags_used: int
    note: str = "HAC-adjusted for overlapping window autocorrelation"


@dataclass
class RegressionResult:
    """Result from regression analysis."""
    alpha: float
    alpha_t_stat: float
    alpha_p_value: float
    betas: Dict[str, float]
    beta_t_stats: Dict[str, float]
    beta_p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    n_observations: int
