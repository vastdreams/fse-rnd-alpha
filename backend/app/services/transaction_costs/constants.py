# Default cost parameters based on academic literature (Novy-Marx & Velikov 2016).

# All values are one-way costs (multiply by 2 for round-trip)
DEFAULT_COSTS = {
    # By market cap quintile (1 = smallest, 5 = largest)
    "bid_ask_spread": {
        1: 0.0150,  # 1.50% for smallest quintile
        2: 0.0075,  # 0.75%
        3: 0.0040,  # 0.40%
        4: 0.0020,  # 0.20%
        5: 0.0010,  # 0.10% for largest quintile (S&P 500 average)
    },
    "market_impact": {
        1: 0.0100,  # 1.00% for smallest
        2: 0.0050,  # 0.50%
        3: 0.0025,  # 0.25%
        4: 0.0012,  # 0.12%
        5: 0.0005,  # 0.05% for largest
    },
    "commission": 0.0001,  # 1bp per trade
    "turnover_assumptions": {
        "annual_rebalance": 0.40,   # 40% turnover for annual rebalancing
        "quarterly_rebalance": 0.80, # 80% turnover for quarterly
        "monthly_rebalance": 1.20,   # 120% turnover for monthly
    }
}

# S&P 500 specific costs (lower due to high liquidity)
SP500_COSTS = {
    "bid_ask_spread": 0.0008,      # 8bp average
    "market_impact": 0.0003,        # 3bp average
    "commission": 0.0001,           # 1bp
    "annual_turnover": 0.40,        # 40% for annual rebalancing
}
