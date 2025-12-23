"""Regression analysis for factor loadings and risk-adjusted returns."""
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from src.logging.logger import get_logger

logger = get_logger(__name__)


def calculate_factor_loading(
    factor_values: List[float],
    returns: List[float]
) -> Dict[str, float]:
    """Calculate factor loading (beta) via regression."""
    if len(factor_values) != len(returns) or len(factor_values) < 2:
        return {}
    
    try:
        # Simple linear regression: returns = alpha + beta * factor
        factor_array = np.array(factor_values)
        returns_array = np.array(returns)
        
        # Remove NaN values
        mask = ~(np.isnan(factor_array) | np.isnan(returns_array))
        factor_clean = factor_array[mask]
        returns_clean = returns_array[mask]
        
        if len(factor_clean) < 2:
            return {}
        
        # Calculate beta (slope)
        factor_mean = np.mean(factor_clean)
        returns_mean = np.mean(returns_clean)
        
        numerator = np.sum((factor_clean - factor_mean) * (returns_clean - returns_mean))
        denominator = np.sum((factor_clean - factor_mean) ** 2)
        
        if denominator == 0:
            return {}
        
        beta = numerator / denominator
        alpha = returns_mean - beta * factor_mean
        
        # Calculate R-squared
        y_pred = alpha + beta * factor_clean
        ss_res = np.sum((returns_clean - y_pred) ** 2)
        ss_tot = np.sum((returns_clean - returns_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Calculate standard error
        n = len(factor_clean)
        if n > 2:
            mse = ss_res / (n - 2)
            se_beta = np.sqrt(mse / denominator) if denominator > 0 else 0
            t_stat = beta / se_beta if se_beta > 0 else 0
        else:
            se_beta = 0
            t_stat = 0
        
        return {
            "beta": float(beta),
            "alpha": float(alpha),
            "r_squared": float(r_squared),
            "se_beta": float(se_beta),
            "t_stat": float(t_stat),
            "n": n,
        }
    except Exception as e:
        logger.error(f"Error in regression: {e}")
        return {}


def calculate_risk_adjusted_returns(
    returns: List[float],
    risk_free_rate: float = 0.0
) -> Dict[str, float]:
    """Calculate risk-adjusted return metrics."""
    if not returns:
        return {}
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns)
    
    # Sharpe ratio (annualized if monthly returns)
    sharpe = (mean_excess / std_excess * np.sqrt(12)) if std_excess > 0 else 0
    
    # Information ratio (active return / tracking error)
    info_ratio = mean_excess / std_excess if std_excess > 0 else 0
    
    # Sortino ratio (downside deviation)
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else std_excess
    sortino = (mean_excess / downside_std * np.sqrt(12)) if downside_std > 0 else 0
    
    return {
        "sharpe_ratio": float(sharpe),
        "information_ratio": float(info_ratio),
        "sortino_ratio": float(sortino),
        "mean_excess_return": float(mean_excess),
        "volatility": float(std_excess),
    }


def multi_factor_regression(
    returns: List[float],
    factors: Dict[str, List[float]]
) -> Dict[str, float]:
    """Multi-factor regression (simplified - would use OLS in production)."""
    # For now, return single-factor results
    # In production, use statsmodels or scikit-learn for proper OLS
    if not factors or not returns:
        return {}
    
    # Use first factor for now
    factor_name = list(factors.keys())[0]
    factor_values = factors[factor_name]
    
    return calculate_factor_loading(factor_values, returns)

