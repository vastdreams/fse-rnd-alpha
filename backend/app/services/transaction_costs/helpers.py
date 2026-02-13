# Helper functions for R&D strategy transaction cost analysis.
from typing import Dict

from app.services.transaction_costs.estimator import TransactionCostEstimator


def estimate_rd_strategy_costs(
    rd_premium_gross: float = 0.04,  # 4% premium vs benchmark (decimal)
    market_return: float = 0.10,      # 10% market return
    universe: str = "sp500",
    n_holdings: int = 20,
) -> Dict:
    """Estimate transaction costs for the R&D factor strategy.
    Shows whether the R&D premium survives realistic trading costs.
    """
    estimator = TransactionCostEstimator(universe=universe, cost_model="moderate")

    q5_gross = market_return + rd_premium_gross
    q5_analysis = estimator.compute_net_returns(
        gross_return=q5_gross,
        benchmark_return=market_return,
        n_holdings=n_holdings,
    )

    net_premium = q5_analysis.net_premium
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
