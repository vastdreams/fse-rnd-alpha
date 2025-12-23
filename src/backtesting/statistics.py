"""Backtest statistics calculation."""
from typing import List, Dict, Optional
import numpy as np
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
from src.logging.logger import get_logger

logger = get_logger(__name__)


def calculate_returns(
    prices: Dict[str, List[float]],
    holding_period_months: int = 12
) -> Dict[str, float]:
    """Calculate returns for each ticker."""
    returns = {}
    
    for ticker, price_series in prices.items():
        if len(price_series) < 2:
            continue
        
        # Simple return calculation
        start_price = price_series[0]
        end_price = price_series[-1] if len(price_series) > holding_period_months else price_series[-1]
        
        if start_price and start_price > 0:
            ret = (end_price - start_price) / start_price
            returns[ticker] = ret
    
    return returns


def calculate_portfolio_return(
    portfolio: Dict[str, float],
    returns: Dict[str, float]
) -> float:
    """Calculate portfolio return."""
    total_return = 0.0
    
    for ticker, weight in portfolio.items():
        if ticker in returns:
            total_return += weight * returns[ticker]
    
    return total_return


def calculate_statistics(
    returns: List[float]
) -> Dict[str, float]:
    """Calculate statistical measures for returns."""
    if not returns:
        return {}
    
    returns_array = np.array(returns)
    
    stats_dict = {
        "mean": float(np.mean(returns_array)),
        "std": float(np.std(returns_array)),
        "sharpe": None,
        "t_stat": None,
        "n": len(returns),
    }
    
    # Sharpe ratio (assuming risk-free rate = 0 for simplicity)
    if stats_dict["std"] > 0:
        stats_dict["sharpe"] = stats_dict["mean"] / stats_dict["std"] * np.sqrt(12)  # Annualized
    
    # t-statistic
    if stats_dict["n"] > 1 and stats_dict["std"] > 0:
        se = stats_dict["std"] / np.sqrt(stats_dict["n"])
        stats_dict["t_stat"] = stats_dict["mean"] / se if se > 0 else None
        stats_dict["stderr"] = float(se)
    
    return stats_dict


def calculate_drawdown(returns: List[float]) -> float:
    """Calculate maximum drawdown."""
    if not returns:
        return 0.0
    
    cumulative = np.cumprod(1 + np.array(returns))
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    
    return float(np.min(drawdown))

