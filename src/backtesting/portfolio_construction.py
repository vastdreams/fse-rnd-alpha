"""Portfolio construction from factor ranks."""
from typing import List, Dict, Tuple
from src.logging.logger import get_logger

logger = get_logger(__name__)


def assign_buckets(
    factor_values: Dict[str, float],
    num_buckets: int = 10
) -> Dict[str, int]:
    """Assign companies to buckets based on factor values."""
    if not factor_values:
        return {}
    
    # Sort by factor value
    sorted_companies = sorted(factor_values.items(), key=lambda x: x[1], reverse=True)
    
    # Assign to buckets
    bucket_size = len(sorted_companies) // num_buckets
    buckets = {}
    
    for i, (ticker, value) in enumerate(sorted_companies):
        bucket = min(i // bucket_size, num_buckets - 1) if bucket_size > 0 else 0
        buckets[ticker] = bucket
    
    return buckets


def build_long_short_portfolio(
    buckets: Dict[str, int],
    num_buckets: int = 10,
    long_bucket: int = 9,  # Top decile
    short_bucket: int = 0,  # Bottom decile
) -> Dict[str, float]:
    """Build long-short portfolio from buckets."""
    portfolio = {}
    
    long_tickers = [t for t, b in buckets.items() if b == long_bucket]
    short_tickers = [t for t, b in buckets.items() if b == short_bucket]
    
    if long_tickers:
        long_weight = 1.0 / len(long_tickers)
        for ticker in long_tickers:
            portfolio[ticker] = long_weight
    
    if short_tickers:
        short_weight = -1.0 / len(short_tickers)
        for ticker in short_tickers:
            portfolio[ticker] = short_weight
    
    return portfolio


def build_long_only_portfolio(
    buckets: Dict[str, int],
    target_bucket: int = 9,  # Top decile
    weighting: str = "equal"
) -> Dict[str, float]:
    """Build long-only portfolio from a specific bucket."""
    portfolio = {}
    
    target_tickers = [t for t, b in buckets.items() if b == target_bucket]
    
    if not target_tickers:
        return portfolio
    
    if weighting == "equal":
        weight = 1.0 / len(target_tickers)
        for ticker in target_tickers:
            portfolio[ticker] = weight
    # TODO: Add value-weighted option
    
    return portfolio

