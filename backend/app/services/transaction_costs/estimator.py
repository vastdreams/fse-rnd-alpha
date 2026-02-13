# TransactionCostEstimator: academic-literature-calibrated cost estimation for portfolios.
import logging
from typing import Dict

from app.core.logging import get_logger
from app.services.transaction_costs.constants import SP500_COSTS
from app.services.transaction_costs.models import TransactionCostBreakdown, NetOfCostReturn

logger = get_logger(__name__)


class TransactionCostEstimator:
    """Estimate transaction costs for portfolio implementation.
    Uses academic literature estimates calibrated to market cap and liquidity.
    """

    def __init__(
        self,
        universe: str = "sp500",
        cost_model: str = "conservative"
    ):
        self.universe = universe
        self.cost_model = cost_model
        self._load_cost_parameters()

    def _load_cost_parameters(self) -> None:
        """Load cost parameters based on universe and model."""
        if self.universe == "sp500":
            base_costs = SP500_COSTS.copy()
        elif self.universe == "russell1000":
            base_costs = {
                "bid_ask_spread": 0.0015,
                "market_impact": 0.0008,
                "commission": 0.0001,
                "annual_turnover": 0.45,
            }
        else:  # russell3000 or all
            base_costs = {
                "bid_ask_spread": 0.0040,
                "market_impact": 0.0020,
                "commission": 0.0001,
                "annual_turnover": 0.50,
            }
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
        trade_size_pct: float = 0.05,
        market_cap_quintile: int = 5,
    ) -> TransactionCostBreakdown:
        """Estimate costs for a single trade, adjusted for market cap quintile."""
        cap_multiplier = {5: 1.0, 4: 1.5, 3: 2.5, 2: 4.0, 1: 8.0}.get(market_cap_quintile, 1.0)
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
        """Estimate annual trading costs for a portfolio."""
        turnover_map = {
            "annual": 0.40,
            "quarterly": 0.80,
            "monthly": 1.20,
        }
        turnover = turnover_map.get(rebalancing_frequency, 0.40)
        avg_bid_ask = self.bid_ask
        avg_market_impact = self.market_impact * (1.0 / n_holdings)
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
        """Compute net-of-cost returns and premium analysis."""
        strategy_costs = self.estimate_portfolio_cost(n_holdings, rebalancing_frequency)
        strategy_annual_cost = strategy_costs.annual_trading_cost
        benchmark_cost = 0.0003  # 3bp for index fund
        strategy_net = gross_return - strategy_annual_cost
        benchmark_net = benchmark_return - benchmark_cost
        gross_premium = gross_return - benchmark_return
        net_premium = strategy_net - benchmark_net
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
