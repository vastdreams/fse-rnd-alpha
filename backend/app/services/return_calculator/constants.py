# Constants for July-June return calculation per Fama-French convention.
import numpy as np

TRADING_DAYS_PER_YEAR = 252
SQRT_252 = np.sqrt(TRADING_DAYS_PER_YEAR)

# Minimum trading days required for valid return calculation
MIN_TRADING_DAYS = 200  # ~80% of a year
# Minimum when symbol exits the index mid-window (reduces survivorship bias)
MIN_TRADING_DAYS_REMOVED_IN_WINDOW = 20

# How we construct returns for Tier-1:
# - total_return_dividends: split-adjusted close + ex-dividend cashflows → total-return proxy
# - price_only: split-adjusted close only → price-return sensitivity mode
PRICE_MODE_TOTAL_RETURN_DIVIDENDS = "total_return_dividends"
PRICE_MODE_PRICE_ONLY = "price_only"

# Backwards-compatible aliases used by older CLI/scripts/docs.
PRICE_MODE_ADJ_CLOSE_ONLY = "adj_close_only"
PRICE_MODE_ADJ_CLOSE_FALLBACK_CLOSE = "adj_close_fallback_close"
