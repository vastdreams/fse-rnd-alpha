"""
PATH: backend/app/services/statistics/tests.py
PURPOSE: T-test and HAC-adjusted t-test methods.
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional
import numpy as np
from scipy import stats

from app.core.logging import get_logger
from app.services.statistics.models import TTestResult, HACResult

logger = get_logger(__name__)


class TestsMixin:
    """Mixin providing t-test and HAC-adjusted t-test methods."""

    def run_ttest(
        self,
        group1: List[float],
        group2: List[float]
    ) -> TTestResult:
        """
        Run independent samples t-test (Welch's t-test for unequal variances).
        
        Args:
            group1: Returns for low R&D (Q1)
            group2: Returns for high R&D (Q5)
            
        Returns:
            TTestResult where:
            - mean_diff = Q5_mean - Q1_mean (positive if high R&D outperforms)
            - t_statistic has same sign as mean_diff
            - Significant if p < 0.05
            
        NOTE: Uses Welch's t-test (equal_var=False) as returns typically have 
        unequal variances across quintiles. This is more robust than Student's t-test.
        """
        if not group1 or not group2:
            return TTestResult(
                t_statistic=0,
                p_value=1,
                mean_diff=0,
                effect_size=0,
                significant=False
            )
        
        arr1 = np.array(group1)  # Q1 (low R&D)
        arr2 = np.array(group2)  # Q5 (high R&D)
        
        # Mean difference: Q5 - Q1 (positive means high R&D outperforms)
        mean_diff = np.mean(arr2) - np.mean(arr1)
        
        # Welch's t-test (unequal variances) - more robust for returns data
        # Pass (arr2, arr1) so t-stat has same sign as mean_diff
        # When mean(arr2) > mean(arr1), t-stat will be positive
        t_stat, p_value = stats.ttest_ind(arr2, arr1, equal_var=False, nan_policy="omit")
        
        # Cohen's d effect size (same sign convention as mean_diff)
        # CORRECTED: Use average variance formula for unequal variances
        # This is appropriate since we use Welch's t-test which assumes unequal variances
        # Formula: d = (mean2 - mean1) / sqrt((var1 + var2) / 2)
        var1 = np.var(arr1, ddof=1)
        var2 = np.var(arr2, ddof=1)
        avg_sd = np.sqrt((var1 + var2) / 2)
        cohens_d = mean_diff / avg_sd if avg_sd > 0 else 0
        
        return TTestResult(
            t_statistic=float(t_stat) if not np.isnan(t_stat) else 0,
            p_value=float(p_value) if not np.isnan(p_value) else 1,
            mean_diff=float(mean_diff),
            effect_size=float(cohens_d),
            significant=bool(p_value < 0.05) if not np.isnan(p_value) else False
        )
    
    def compute_hac_ttest(
        self,
        series: List[float],
        hypothesis_value: float = 0,
        lags: Optional[int] = None,
        window_years: Optional[int] = None
    ) -> HACResult:
        """
        Compute HAC (Newey-West) adjusted t-test for a time series.
        
        CRITICAL for overlapping window analysis where observations are 
        not independent. Standard t-tests assume iid observations, which
        is violated when using overlapping windows.
        
        Args:
            series: Time series of observations (e.g., rolling window premiums)
            hypothesis_value: Value to test against (default 0)
            lags: Number of lags for HAC. If None and window_years provided,
                  uses window_years - 1. Otherwise uses Newey-West rule of thumb.
            window_years: Window length for overlapping window analysis.
                         If provided, uses lags = window_years - 1 to properly
                         account for overlap-induced autocorrelation.
            
        Returns:
            HACResult with corrected standard errors and p-values
            
        Reference:
            Newey & West (1987), "A Simple, Positive Semi-definite, 
            Heteroskedasticity and Autocorrelation Consistent Covariance Matrix"
            
        NOTE: For k-year overlapping windows, the standard Newey-West lag selection
        rule is insufficient. We need lags >= k-1 to capture all induced autocorrelation.
        """
        # Convert to floats and filter out None/NaN values
        clean_series = []
        for x in series:
            if x is None:
                continue
            try:
                fx = float(x)
                if not np.isnan(fx):
                    clean_series.append(fx)
            except (TypeError, ValueError):
                continue
        arr = np.array(clean_series)
        n = len(arr)
        
        if n < 3:
            return HACResult(
                mean=0,
                std_error_hac=0,
                t_statistic_hac=0,
                p_value_hac=1,
                significant=False,
                n_observations=n,
                lags_used=0,
                note="Insufficient observations for HAC estimation"
            )
        
        # Calculate optimal lag length
        # CRITICAL: For overlapping k-year windows, use lags = k-1, not the default rule
        if lags is not None:
            pass  # Use provided lags
        elif window_years is not None:
            # For k-year overlapping windows, use k-1 lags
            lags = max(1, window_years - 1)
        else:
            # Default: Newey-West rule of thumb (only appropriate for non-overlapping data)
            lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
        
            lags = max(1, min(lags, n - 1))  # Ensure valid range
        
        # Sample mean
        mean = np.mean(arr)
        
        # Center the series
        centered = arr - mean
        
        # Compute HAC variance using Bartlett kernel (Newey-West)
        # Variance = (1/n) * sum of weighted autocovariances
        
        # Autocovariance at lag 0
        gamma_0 = np.sum(centered ** 2) / n
        
        # Sum of weighted autocovariances for lags 1 to lags
        hac_variance = gamma_0
        for j in range(1, lags + 1):
            # Bartlett kernel weight
            weight = 1 - j / (lags + 1)
            # Autocovariance at lag j
            gamma_j = np.sum(centered[j:] * centered[:-j]) / n
            # Add twice (for positive and negative lags)
            hac_variance += 2 * weight * gamma_j
        
        # HAC standard error
        std_error_hac = np.sqrt(hac_variance / n)
        
        if std_error_hac <= 0:
            return HACResult(
                mean=float(mean),
                std_error_hac=0,
                t_statistic_hac=0,
                p_value_hac=1,
                significant=False,
                n_observations=n,
                lags_used=lags,
                note="Zero variance in series"
            )
        
        # HAC-adjusted t-statistic
        t_stat_hac = (mean - hypothesis_value) / std_error_hac
        
        # Two-tailed p-value
        p_value_hac = 2 * (1 - stats.t.cdf(abs(t_stat_hac), df=n - 1))
        
        lag_note = f"Newey-West HAC with {lags} lags"
        if window_years:
            lag_note += f" (k-1 for {window_years}-year overlapping windows)"
        else:
            lag_note += " (default rule, may underestimate SE for overlapping data)"
        
        return HACResult(
            mean=float(mean),
            std_error_hac=float(std_error_hac),
            t_statistic_hac=float(t_stat_hac),
            p_value_hac=float(p_value_hac),
            significant=bool(p_value_hac < 0.05),
            n_observations=n,
            lags_used=lags,
            note=lag_note
        )
