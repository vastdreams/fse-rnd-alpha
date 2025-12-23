"""
PATH: backend/app/services/transaction_costs.py
PURPOSE:
  - Model transaction costs for realistic portfolio implementation
  - Estimate bid-ask spreads, market impact, and total trading costs
  - Provide net-of-cost return analysis for research validity

ROLE IN ARCHITECTURE:
  - Service layer for transaction cost modeling
  - Used by rolling_window.py and portfolio_optimizer.py for net returns

MAIN EXPORTS:
  - TransactionCostEstimator: Main cost estimation class
  - estimate_trading_costs: Helper function for quick estimates
  - COST_MODELS: Dictionary of available cost models

NON-RESPONSIBILITIES:
  - Does not execute actual trades
  - Does not fetch real-time bid-ask quotes

NOTES FOR FUTURE AI:
  - Cost estimates are based on academic literature (Novy-Marx & Velikov 2016)
  - Small-cap and low-liquidity adjustments are critical
  - Update DEFAULT_COSTS periodically based on market conditions

REFERENCES:
  - Novy-Marx, R. & Velikov, M. (2016). "A taxonomy of anomalies and their trading costs"
  - Frazzini, A., Israel, R., & Moskowitz, T. (2018). "Trading costs"
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


# ==============================================================================
# Default Cost Parameters (Based on Academic Literature)
# ==============================================================================

# Novy-Marx & Velikov (2016) estimates for US equities
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
    # Market impact (price movement due to trade)
    "market_impact": {
        1: 0.0100,  # 1.00% for smallest
        2: 0.0050,  # 0.50%
        3: 0.0025,  # 0.25%
        4: 0.0012,  # 0.12%
        5: 0.0005,  # 0.05% for largest
    },
    # Commission (largely eliminated for retail, small for institutional)
    "commission": 0.0001,  # 1bp per trade
    
    # Annual portfolio turnover assumptions
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


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class TransactionCostBreakdown:
    """Detailed breakdown of transaction costs for a trade or portfolio."""
    
    # One-way costs
    bid_ask_cost: float          # Half-spread paid
    market_impact_cost: float    # Price movement from trade
    commission_cost: float       # Broker commission
    
    # Totals
    one_way_total: float         # Sum of above
    round_trip_total: float      # one_way * 2
    
    # For portfolios
    annual_turnover: float = 0.40
    annual_trading_cost: float = 0.0  # round_trip * turnover
    
    # Metadata
    cost_model: str = "sp500_default"
    assumptions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "bid_ask_cost_pct": round(self.bid_ask_cost * 100, 3),
            "market_impact_cost_pct": round(self.market_impact_cost * 100, 3),
            "commission_cost_pct": round(self.commission_cost * 100, 3),
            "one_way_total_pct": round(self.one_way_total * 100, 3),
            "round_trip_total_pct": round(self.round_trip_total * 100, 3),
            "annual_turnover_pct": round(self.annual_turnover * 100, 1),
            "annual_trading_cost_pct": round(self.annual_trading_cost * 100, 3),
            "cost_model": self.cost_model,
            "assumptions": self.assumptions,
        }


@dataclass
class NetOfCostReturn:
    """Return analysis adjusted for transaction costs."""
    
    gross_return: float          # Before costs
    trading_cost: float          # Annual trading cost
    net_return: float            # gross - trading_cost
    
    # Comparison
    benchmark_gross: float = 0.0
    benchmark_net: float = 0.0
    
    # Premium calculations
    gross_premium: float = 0.0   # strategy_gross - benchmark_gross
    net_premium: float = 0.0     # strategy_net - benchmark_net
    
    # How much of premium survives costs
    premium_capture_rate: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "gross_return_pct": round(self.gross_return * 100, 2),
            "trading_cost_pct": round(self.trading_cost * 100, 3),
            "net_return_pct": round(self.net_return * 100, 2),
            "benchmark_gross_pct": round(self.benchmark_gross * 100, 2),
            "benchmark_net_pct": round(self.benchmark_net * 100, 2),
            "gross_premium_pct": round(self.gross_premium * 100, 2),
            "net_premium_pct": round(self.net_premium * 100, 2),
            "premium_capture_rate_pct": round(self.premium_capture_rate * 100, 1),
        }


# ==============================================================================
# Transaction Cost Estimator
# ==============================================================================

class TransactionCostEstimator:
    """
    Estimate transaction costs for portfolio implementation.
    
    Uses academic literature estimates calibrated to market cap and liquidity.
    Designed for S&P 500 universe but can adjust for smaller caps.
    """
    
    def __init__(
        self,
        universe: str = "sp500",
        cost_model: str = "conservative"
    ):
        """
        Initialize cost estimator.
        
        Args:
            universe: "sp500", "russell1000", "russell3000"
            cost_model: "conservative", "moderate", "aggressive"
        """
        self.universe = universe
        self.cost_model = cost_model
        self._load_cost_parameters()
    
    def _load_cost_parameters(self) -> None:
        """Load cost parameters based on universe and model."""
        
        # Universe adjustments
        if self.universe == "sp500":
            base_costs = SP500_COSTS.copy()
        elif self.universe == "russell1000":
            # Slightly higher costs for mid-caps
            base_costs = {
                "bid_ask_spread": 0.0015,
                "market_impact": 0.0008,
                "commission": 0.0001,
                "annual_turnover": 0.45,
            }
        else:  # russell3000 or all
            # Higher costs for small-caps
            base_costs = {
                "bid_ask_spread": 0.0040,
                "market_impact": 0.0020,
                "commission": 0.0001,
                "annual_turnover": 0.50,
            }
        
        # Model adjustments (conservative adds buffer)
        if self.cost_model == "conservative":
            multiplier = 1.5
        elif self.cost_model == "aggressive":
            multiplier = 0.75
        else:  # moderate
            multiplier = 1.0
        
        self.bid_ask = base_costs["bid_ask_spread"] * multiplier
        self.market_impact = base_costs["market_impact"] * multiplier
        self.commission = base_costs["commission"]
        self.annual_turnover = base_costs["annual_turnover"]
    
    def estimate_trade_cost(
        self,
        trade_size_pct: float = 0.05,  # 5% of position
        market_cap_quintile: int = 5,   # 5 = largest
    ) -> TransactionCostBreakdown:
        """
        Estimate costs for a single trade.
        
        Args:
            trade_size_pct: Trade size as percent of avg daily volume
            market_cap_quintile: 1-5 (5 = largest, most liquid)
            
        Returns:
            TransactionCostBreakdown with detailed costs
        """
        # Adjust for market cap
        cap_multiplier = {5: 1.0, 4: 1.5, 3: 2.5, 2: 4.0, 1: 8.0}.get(market_cap_quintile, 1.0)
        
        # Calculate components
        bid_ask = self.bid_ask * cap_multiplier
        market_impact = self.market_impact * cap_multiplier * (trade_size_pct / 0.05)
        commission = self.commission
        
        one_way = bid_ask + market_impact + commission
        round_trip = one_way * 2
        annual = round_trip * self.annual_turnover
        
        return TransactionCostBreakdown(
            bid_ask_cost=bid_ask,
            market_impact_cost=market_impact,
            commission_cost=commission,
            one_way_total=one_way,
            round_trip_total=round_trip,
            annual_turnover=self.annual_turnover,
            annual_trading_cost=annual,
            cost_model=f"{self.universe}_{self.cost_model}",
            assumptions={
                "trade_size_pct": f"{trade_size_pct*100:.1f}%",
                "market_cap_quintile": str(market_cap_quintile),
                "rebalancing": "annual",
            }
        )
    
    def estimate_portfolio_cost(
        self,
        n_holdings: int = 20,
        rebalancing_frequency: str = "annual",
    ) -> TransactionCostBreakdown:
        """
        Estimate annual trading costs for a portfolio.
        
        Args:
            n_holdings: Number of holdings in portfolio
            rebalancing_frequency: "annual", "quarterly", "monthly"
            
        Returns:
            TransactionCostBreakdown for portfolio
        """
        # Turnover based on rebalancing frequency
        turnover_map = {
            "annual": 0.40,
            "quarterly": 0.80,
            "monthly": 1.20,
        }
        turnover = turnover_map.get(rebalancing_frequency, 0.40)
        
        # Average trade cost for portfolio
        avg_bid_ask = self.bid_ask
        avg_market_impact = self.market_impact * (1.0 / n_holdings)  # Smaller trades
        commission = self.commission
        
        one_way = avg_bid_ask + avg_market_impact + commission
        round_trip = one_way * 2
        annual = round_trip * turnover
        
        return TransactionCostBreakdown(
            bid_ask_cost=avg_bid_ask,
            market_impact_cost=avg_market_impact,
            commission_cost=commission,
            one_way_total=one_way,
            round_trip_total=round_trip,
            annual_turnover=turnover,
            annual_trading_cost=annual,
            cost_model=f"{self.universe}_{self.cost_model}",
            assumptions={
                "n_holdings": str(n_holdings),
                "rebalancing": rebalancing_frequency,
                "source": "Novy-Marx & Velikov (2016)",
            }
        )
    
    def compute_net_returns(
        self,
        gross_return: float,
        benchmark_return: float = 0.10,
        n_holdings: int = 20,
        rebalancing_frequency: str = "annual",
    ) -> NetOfCostReturn:
        """
        Compute net-of-cost returns and premium analysis.
        
        Args:
            gross_return: Strategy gross annual return (decimal, e.g., 0.12 = 12%)
            benchmark_return: Benchmark gross return (typically S&P 500)
            n_holdings: Number of portfolio holdings
            rebalancing_frequency: Rebalancing frequency
            
        Returns:
            NetOfCostReturn with full analysis
        """
        # Strategy costs
        strategy_costs = self.estimate_portfolio_cost(n_holdings, rebalancing_frequency)
        strategy_annual_cost = strategy_costs.annual_trading_cost
        
        # Benchmark costs (assume low-cost index fund)
        benchmark_cost = 0.0003  # 3bp for index fund
        
        # Net returns
        strategy_net = gross_return - strategy_annual_cost
        benchmark_net = benchmark_return - benchmark_cost
        
        # Premium analysis
        gross_premium = gross_return - benchmark_return
        net_premium = strategy_net - benchmark_net
        
        # How much premium survives costs
        if gross_premium > 0:
            capture_rate = net_premium / gross_premium
        else:
            capture_rate = 1.0
        
        return NetOfCostReturn(
            gross_return=gross_return,
            trading_cost=strategy_annual_cost,
            net_return=strategy_net,
            benchmark_gross=benchmark_return,
            benchmark_net=benchmark_net,
            gross_premium=gross_premium,
            net_premium=net_premium,
            premium_capture_rate=max(0, capture_rate),
        )


# ==============================================================================
# Helper Functions
# ==============================================================================

def estimate_rd_strategy_costs(
    rd_premium_gross: float = 0.04,  # 4% premium vs benchmark (decimal)
    market_return: float = 0.10,      # 10% market return
    universe: str = "sp500",
    n_holdings: int = 20,
) -> Dict:
    """
    Estimate transaction costs for the R&D factor strategy.
    
    This is the key function for research validity - shows whether
    the R&D premium survives realistic trading costs.
    
    Args:
        rd_premium_gross: Gross premium vs benchmark (decimal)
        market_return: Benchmark market return
        universe: Stock universe
        n_holdings: Portfolio size
        
    Returns:
        Dictionary with cost analysis for papers/methodology
    """
    estimator = TransactionCostEstimator(universe=universe, cost_model="moderate")
    
    # High R&D portfolio (long-only) vs benchmark
    q5_gross = market_return + rd_premium_gross
    q5_analysis = estimator.compute_net_returns(
        gross_return=q5_gross,
        benchmark_return=market_return,
        n_holdings=n_holdings,
    )

    # Net premium vs benchmark (net-of-cost)
    net_premium = q5_analysis.net_premium
    
    # Cost breakdown
    portfolio_costs = estimator.estimate_portfolio_cost(n_holdings)
    
    # Premium capture rate = (net premium) / (gross premium). Undefined if gross premium <= 0.
    capture_rate_pct: float | None
    if rd_premium_gross > 0:
        capture_rate_pct = round(net_premium / rd_premium_gross * 100, 1)
    else:
        capture_rate_pct = None

    return {
        "gross_rd_premium_pct": round(rd_premium_gross * 100, 2),
        "net_rd_premium_pct": round(net_premium * 100, 2),
        # Backward-compatible field name (historically used in UI); this is a CAPTURE RATE, not a net premium.
        "premium_after_costs_pct": capture_rate_pct,
        # Canonical / clearer name for UI going forward
        "premium_capture_rate_pct": capture_rate_pct,
        "q5_gross_return_pct": round(q5_gross * 100, 2),
        "q5_net_return_pct": round(q5_analysis.net_return * 100, 2),
        # Benchmark return context
        "q1_gross_return_pct": round(q5_analysis.benchmark_gross * 100, 2),
        "q1_net_return_pct": round(q5_analysis.benchmark_net * 100, 2),
        "annual_trading_cost_pct": round(portfolio_costs.annual_trading_cost * 100, 3),
        "cost_breakdown": portfolio_costs.to_dict(),
        "methodology_note": (
            "Transaction costs estimated using Novy-Marx & Velikov (2016) methodology. "
            f"Assumes {portfolio_costs.assumptions['rebalancing']} rebalancing, "
            f"{portfolio_costs.annual_turnover*100:.0f}% annual turnover, "
            f"and {universe.upper()} liquidity characteristics."
        ),
        "is_premium_significant": net_premium > 0.02,  # >2% net premium
    }

