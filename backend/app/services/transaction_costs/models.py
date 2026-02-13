# Data classes for transaction cost breakdowns and net-of-cost return analysis.
from typing import Dict
from dataclasses import dataclass, field


@dataclass
class TransactionCostBreakdown:
    """Detailed breakdown of transaction costs for a trade or portfolio."""
    bid_ask_cost: float          # Half-spread paid (one-way)
    market_impact_cost: float    # Price movement from trade (one-way)
    commission_cost: float       # Broker commission (one-way)
    one_way_total: float         # Sum of above
    round_trip_total: float      # one_way * 2
    annual_turnover: float = 0.40
    annual_trading_cost: float = 0.0  # round_trip * turnover
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
    benchmark_gross: float = 0.0
    benchmark_net: float = 0.0
    gross_premium: float = 0.0   # strategy_gross - benchmark_gross
    net_premium: float = 0.0     # strategy_net - benchmark_net
    premium_capture_rate: float = 1.0  # How much of premium survives costs

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
