# PATH: src/backtesting/publication_grade/inference.py
# PURPOSE:
#   - Proper statistical inference with HAC (Newey-West) standard errors
#   - Handle overlapping returns correctly
#   - Generate publication-grade t-statistics and p-values
#
# ROLE IN ARCHITECTURE:
#   - Statistical inference layer for portfolio analysis
#
# METHODOLOGY:
#   - Newey-West HAC estimator for autocorrelation-robust standard errors
#   - Automatic lag selection based on sample size
#   - Properly handles overlapping long-horizon returns
#
# NOTES FOR FUTURE AI:
#   - Standard t-tests are INVALID with overlapping returns
#   - Always use HAC errors for factor return inference
#   - Report lags used for reproducibility

import logging
from typing import List, Optional, Tuple
import numpy as np

from .schemas import (
    QuintileTimeSeries,
    FactorPremiumSeries,
    InferenceResult
)

logger = logging.getLogger(__name__)


class NeweyWestInference:
    """
    Newey-West HAC (Heteroskedasticity and Autocorrelation Consistent) inference.
    
    Standard errors are adjusted for:
    1. Heteroskedasticity (varying variance)
    2. Autocorrelation (serial correlation from overlapping returns)
    
    This is REQUIRED for valid inference with:
    - Overlapping long-horizon returns
    - Monthly factor returns (which may have persistence)
    - Any time series with potential serial correlation
    """
    
    def __init__(self, risk_free_rate: float = 0.0):
        """
        Initialize inference engine.
        
        Args:
            risk_free_rate: Annual risk-free rate (decimal, e.g., 0.02 for 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    @staticmethod
    def optimal_lags(n_obs: int) -> int:
        """
        Compute optimal number of lags for Newey-West.
        
        Uses common rule: lags = floor(4 * (n/100)^(2/9))
        From Newey-West (1994).
        """
        return int(np.floor(4 * (n_obs / 100) ** (2/9)))
    
    @staticmethod
    def newey_west_variance(
        residuals: np.ndarray,
        n_lags: int
    ) -> float:
        """
        Compute Newey-West HAC variance estimator.
        
        V_NW = Σ_0 + Σ_{j=1}^{lags} w_j (Σ_j + Σ_j')
        
        where w_j = 1 - j/(lags+1) (Bartlett kernel)
        and Σ_j = (1/n) Σ_{t=j+1}^{n} e_t * e_{t-j}
        
        Args:
            residuals: Demeaned returns (e_t = r_t - mean)
            n_lags: Number of lags to include
            
        Returns:
            HAC variance estimate
        """
        n = len(residuals)
        
        # Lag-0 autocovariance (just variance)
        gamma_0 = np.sum(residuals ** 2) / n
        
        # Sum of weighted autocovariances
        weighted_sum = 0.0
        
        for j in range(1, n_lags + 1):
            # Bartlett weight
            w_j = 1 - j / (n_lags + 1)
            
            # Lag-j autocovariance
            gamma_j = np.sum(residuals[j:] * residuals[:-j]) / n
            
            # Newey-West adds both directions
            weighted_sum += 2 * w_j * gamma_j
        
        nw_variance = gamma_0 + weighted_sum
        
        return nw_variance
    
    def compute_inference(
        self,
        returns: List[float],
        annualize: bool = True,
        periods_per_year: int = 1
    ) -> InferenceResult:
        """
        Compute inference statistics with Newey-West HAC standard errors.
        
        Args:
            returns: List of returns (decimal form)
            annualize: Whether to annualize mean and volatility
            periods_per_year: Number of return periods per year (1=annual, 12=monthly)
            
        Returns:
            InferenceResult with properly computed statistics
        """
        if not returns or len(returns) < 5:
            return InferenceResult(
                mean_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                t_statistic=0.0,
                p_value=1.0,
                standard_error=0.0,
                confidence_interval_95=(0.0, 0.0),
                n_observations=len(returns) if returns else 0,
                n_lags_used=0,
                overlapping_returns=False,
                hac_adjustment_applied=False
            )
        
        returns_array = np.array(returns)
        n = len(returns_array)
        
        # Point estimates
        mean_return = np.mean(returns_array)
        volatility = np.std(returns_array, ddof=1)
        
        # Annualize if requested
        if annualize:
            mean_return_ann = mean_return * periods_per_year
            volatility_ann = volatility * np.sqrt(periods_per_year)
        else:
            mean_return_ann = mean_return
            volatility_ann = volatility
        
        # Sharpe ratio
        excess_return = mean_return_ann - self.risk_free_rate
        sharpe = excess_return / volatility_ann if volatility_ann > 0 else 0.0
        
        # Newey-West HAC standard error
        n_lags = self.optimal_lags(n)
        residuals = returns_array - mean_return
        
        nw_variance = self.newey_west_variance(residuals, n_lags)
        nw_se_mean = np.sqrt(nw_variance / n)  # SE of mean
        
        # Annualize SE if needed
        if annualize:
            nw_se_mean_ann = nw_se_mean * periods_per_year
        else:
            nw_se_mean_ann = nw_se_mean
        
        # t-statistic and p-value
        t_stat = mean_return_ann / nw_se_mean_ann if nw_se_mean_ann > 0 else 0.0
        
        # Two-sided p-value (using normal approximation for large n)
        try:
            from scipy.stats import t as t_dist
            p_value = 2 * (1 - t_dist.cdf(abs(t_stat), df=n-1))
        except ImportError:
            # Fallback: normal approximation
            from scipy.stats import norm
            p_value = 2 * (1 - norm.cdf(abs(t_stat)))
        except:
            p_value = 0.0 if abs(t_stat) > 3 else 1.0
        
        # 95% confidence interval
        critical_value = 1.96  # z for 95% CI
        ci_lower = mean_return_ann - critical_value * nw_se_mean_ann
        ci_upper = mean_return_ann + critical_value * nw_se_mean_ann
        
        return InferenceResult(
            mean_return=mean_return_ann,
            volatility=volatility_ann,
            sharpe_ratio=sharpe,
            t_statistic=t_stat,
            p_value=p_value,
            standard_error=nw_se_mean_ann,
            confidence_interval_95=(ci_lower, ci_upper),
            n_observations=n,
            n_lags_used=n_lags,
            overlapping_returns=n_lags > 0,
            hac_adjustment_applied=True
        )
    
    def compute_quintile_inference(
        self,
        quintile_series: QuintileTimeSeries,
        periods_per_year: int = 1
    ) -> InferenceResult:
        """Compute inference for a single quintile."""
        return self.compute_inference(
            quintile_series.return_series,
            annualize=True,
            periods_per_year=periods_per_year
        )
    
    def compute_premium_inference(
        self,
        premium_series: FactorPremiumSeries,
        periods_per_year: int = 1
    ) -> InferenceResult:
        """Compute inference for Q5-Q1 factor premium."""
        return self.compute_inference(
            premium_series.premiums,
            annualize=True,
            periods_per_year=periods_per_year
        )
    
    def compare_quintiles(
        self,
        q_high: QuintileTimeSeries,
        q_low: QuintileTimeSeries
    ) -> dict:
        """
        Statistical test for difference between two quintiles.
        
        Uses paired difference test with HAC errors.
        """
        # Align periods
        high_by_period = {r.period_start: r.return_ew for r in q_high.returns}
        low_by_period = {r.period_start: r.return_ew for r in q_low.returns}
        
        common_periods = set(high_by_period.keys()) & set(low_by_period.keys())
        
        if len(common_periods) < 10:
            return {
                "difference": 0.0,
                "t_stat": 0.0,
                "p_value": 1.0,
                "n_common": len(common_periods)
            }
        
        differences = [
            high_by_period[p] - low_by_period[p]
            for p in sorted(common_periods)
        ]
        
        inference = self.compute_inference(differences, annualize=True)
        
        return {
            "difference": inference.mean_return,
            "t_stat": inference.t_statistic,
            "p_value": inference.p_value,
            "n_common": len(common_periods),
            "ci_95": inference.confidence_interval_95
        }

