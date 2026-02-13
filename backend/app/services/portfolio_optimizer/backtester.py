# EXEMPTION: 342 lines — Complex backtest orchestration with tightly-coupled monthly loop; splitting would fragment the simulation
"""
PATH: research/backend/app/services/portfolio_optimizer/backtester.py
PURPOSE: Full backtest engine for R&D ETF strategy with turnover and cost analysis
WHY: The backtest loop is the largest single algorithm; isolating it keeps other modules focused
NOTE: Exceeds 300-line limit — backtest_rd_etf is a single cohesive algorithm
      whose clarity would degrade if further decomposed across files.
DEPENDENCIES:
  - app.db.models: ORM models for returns and research cohort
  - app.services.transaction_costs: cost estimation
  - numpy: statistical calculations
  - .models: shared dataclasses
"""

import logging
from typing import List, Dict, Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchCohort, FMPAnnualReturn

from .models import PortfolioHolding

logger = logging.getLogger(__name__)


class BacktesterMixin:
    """
    Mixin providing the full backtest engine for PortfolioOptimizer.

    Expects the composing class to set:
      - self.session: AsyncSession
      - self.use_july_june: bool
      - self.DEFAULT_RISK_FREE_RATE: float
    And provide (via other mixins):
      - self.select_top_rd_companies_for_year()
      - self.select_top_rd_companies()
      - self.get_risk_free_rate()
    """

    session: AsyncSession
    use_july_june: bool
    DEFAULT_RISK_FREE_RATE: float

    async def _perf_from_series(
        self,
        annual_returns: List[float],
        years_used: List[int],
    ) -> Dict[str, float]:
        """Compute summary performance metrics from an annual return series."""
        if not annual_returns:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
            }

        total_return = float(np.prod([1 + r for r in annual_returns]) - 1)
        n_years = len(annual_returns)
        annualized_return = float((1 + total_return) ** (1 / n_years) - 1) if n_years > 0 else 0.0
        volatility = float(np.std(annual_returns)) if n_years > 1 else 0.0

        rf_rates = [await self.get_risk_free_rate(int(y)) for y in years_used] if years_used else []
        avg_rf = float(np.mean(rf_rates)) if rf_rates else self.DEFAULT_RISK_FREE_RATE
        excess = annualized_return - avg_rf
        sharpe = float(excess / volatility) if volatility > 0 else 0.0

        cumulative = np.cumprod([1 + r for r in annual_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else 0.0

        return {
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(annualized_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown": round(max_drawdown * 100, 2),
        }

    async def backtest_rd_etf(
        self,
        start_year: int,
        end_year: int,
        n_holdings: int = 20,
        selection_method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None,
        use_point_in_time: bool = True
    ) -> Dict:
        """
        Run full backtest of R&D ETF strategy.

        Returns:
        - Portfolio performance
        - Benchmark comparisons
        - Holdings (start year + year-by-year)
        - Year-by-year returns
        """
        years = list(range(start_year, end_year + 1))

        # --- 1) Annual reconstitution (point-in-time) ---
        holdings_by_year: Dict[int, List[PortfolioHolding]] = {}
        universe_portfolio_symbols: set[str] = set()

        for year in years:
            if use_point_in_time:
                year_holdings = await self.select_top_rd_companies_for_year(
                    as_of_year=year, n=n_holdings,
                    method=selection_method, sectors=sectors,
                )
            else:
                year_holdings = await self.select_top_rd_companies(
                    n=n_holdings, method=selection_method,
                    sectors=sectors, min_years=5,
                )

            holdings_by_year[int(year)] = year_holdings
            for h in year_holdings:
                universe_portfolio_symbols.add(str(h.symbol))

        start_holdings = holdings_by_year.get(int(start_year), [])

        # Benchmark universe (S&P 500 proxy): research cohort symbols
        bench_result = await self.session.execute(select(ResearchCohort.symbol))
        benchmark_symbols = [r[0] for r in bench_result.fetchall() if r and r[0]]
        if not benchmark_symbols:
            benchmark_symbols = list({*universe_portfolio_symbols})

        # Prefetch returns for the universe + period
        from app.db.models import JulyJuneReturn

        sp500_proxy_symbol = "SPY"
        universe_symbols = sorted({*universe_portfolio_symbols, *benchmark_symbols, sp500_proxy_symbol})

        returns_map: Dict[Tuple[str, int], float] = {}
        if self.use_july_june:
            formation_years = [y - 1 for y in years]
            ret_result = await self.session.execute(
                select(JulyJuneReturn.symbol, JulyJuneReturn.formation_year, JulyJuneReturn.annualized_return)
                .where(
                    JulyJuneReturn.symbol.in_(universe_symbols),
                    JulyJuneReturn.formation_year.in_(formation_years),
                    JulyJuneReturn.data_tier == "tier1",
                    JulyJuneReturn.annualized_return.isnot(None),
                )
            )
            for sym, formation_year, ret in ret_result.fetchall():
                if sym is None or formation_year is None or ret is None:
                    continue
                returns_map[(str(sym), int(formation_year) + 1)] = float(ret)
        else:
            ret_result = await self.session.execute(
                select(FMPAnnualReturn.symbol, FMPAnnualReturn.year, FMPAnnualReturn.annual_return)
                .where(
                    FMPAnnualReturn.symbol.in_(universe_symbols),
                    FMPAnnualReturn.year.in_(years),
                    FMPAnnualReturn.annual_return.isnot(None),
                )
            )
            for sym, year, ret in ret_result.fetchall():
                if sym is None or year is None or ret is None:
                    continue
                returns_map[(str(sym), int(year))] = float(ret)

        portfolio_annual_returns: List[float] = []
        portfolio_years: List[int] = []
        benchmark_annual_returns: List[float] = []
        benchmark_years: List[int] = []

        sp500_returns_map: Dict[int, float] = {}
        for year in years:
            spy_ret = returns_map.get((sp500_proxy_symbol, year))
            if spy_ret is not None:
                sp500_returns_map[int(year)] = float(spy_ret)

        sp500_annual_returns: List[float] = []
        yearly_data: List[Dict[str, float]] = []
        turnover_by_year: List[Dict[str, float]] = []

        # Net-of-cost series
        from app.services.transaction_costs import TransactionCostEstimator
        cost_estimator = TransactionCostEstimator(universe="sp500", cost_model="moderate")
        portfolio_cost_template = cost_estimator.estimate_portfolio_cost(
            n_holdings=n_holdings, rebalancing_frequency="annual"
        )
        round_trip_cost_per_full_turnover = float(portfolio_cost_template.round_trip_total)
        benchmark_cost = 0.0003  # 3bp proxy
        portfolio_annual_returns_net: List[float] = []
        benchmark_annual_returns_net: List[float] = []

        prev_weights: Dict[str, float] = {}

        for year in years:
            year_holdings = holdings_by_year.get(int(year), [])
            symbols = [h.symbol for h in year_holdings]
            weights = [float(h.weight) for h in year_holdings]
            curr_weights = {str(sym): float(w) for sym, w in zip(symbols, weights)}

            # Turnover calculation
            if prev_weights:
                keys = set(prev_weights.keys()) | set(curr_weights.keys())
                gross_turnover = 0.5 * sum(abs(curr_weights.get(k, 0.0) - prev_weights.get(k, 0.0)) for k in keys)
                n_added = len([k for k in curr_weights if k not in prev_weights])
                n_removed = len([k for k in prev_weights if k not in curr_weights])
            else:
                gross_turnover = 0.0
                n_added = len(curr_weights)
                n_removed = 0

            turnover_by_year.append({
                "year": int(year),
                "turnover": round(float(gross_turnover), 4),
                "turnover_pct": round(float(gross_turnover) * 100, 1),
                "n_added": float(n_added),
                "n_removed": float(n_removed),
            })

            # Portfolio return (weighted; renormalize for missing returns)
            port_return = 0.0
            valid_w = 0.0
            for sym, w in zip(symbols, weights):
                ret = returns_map.get((sym, year))
                if ret is None:
                    continue
                port_return += float(ret) * float(w)
                valid_w += float(w)

            if valid_w > 0:
                port_return = port_return / valid_w
                portfolio_annual_returns.append(float(port_return))
                portfolio_years.append(int(year))
            else:
                port_return = 0.0

            # Benchmark return (equal-weight mean)
            bench_vals: List[float] = []
            for sym in benchmark_symbols:
                ret = returns_map.get((sym, year))
                if ret is None:
                    continue
                bench_vals.append(float(ret))

            bench_return = float(np.mean(bench_vals)) if bench_vals else 0.0
            benchmark_annual_returns.append(float(bench_return))
            benchmark_years.append(int(year))

            # Net-of-cost approximation
            annual_cost = round_trip_cost_per_full_turnover * float(gross_turnover)
            port_return_net = float(port_return) - float(annual_cost)
            bench_return_net = float(bench_return) - float(benchmark_cost)
            portfolio_annual_returns_net.append(port_return_net)
            benchmark_annual_returns_net.append(bench_return_net)

            sp500_return = sp500_returns_map.get(year, None)
            if sp500_return is not None:
                sp500_annual_returns.append(float(sp500_return))

            yearly_data.append({
                "year": int(year),
                "portfolio_return": round(port_return * 100, 2),
                "benchmark_return": round(bench_return * 100, 2),
                "sp500_return": round(sp500_return * 100, 2) if sp500_return is not None else None,
                "excess_return": round((port_return - bench_return) * 100, 2),
                "excess_vs_sp500": round((port_return - sp500_return) * 100, 2) if sp500_return is not None else None,
                "turnover_pct": round(float(gross_turnover) * 100, 1),
                "portfolio_return_net": round(port_return_net * 100, 2),
                "benchmark_return_net": round(bench_return_net * 100, 2),
                "excess_return_net": round((port_return_net - bench_return_net) * 100, 2),
            })

            prev_weights = curr_weights

        # --- Summarize performance ---
        portfolio_perf = await self._perf_from_series(portfolio_annual_returns, portfolio_years)
        benchmark_perf = await self._perf_from_series(benchmark_annual_returns, benchmark_years)
        sp500_perf = await self._perf_from_series(sp500_annual_returns, [y for y in years if y in sp500_returns_map])
        portfolio_perf_net = await self._perf_from_series(portfolio_annual_returns_net, portfolio_years)
        benchmark_perf_net = await self._perf_from_series(benchmark_annual_returns_net, benchmark_years)

        turnover_vals = [float(t.get("turnover", 0.0)) for t in turnover_by_year[1:]]
        avg_turnover = float(np.mean(turnover_vals)) if turnover_vals else 0.0
        max_turnover = float(np.max(turnover_vals)) if turnover_vals else 0.0

        return {
            "period": f"{start_year}-{end_year}",
            "meta": {
                "return_convention": "july_june" if self.use_july_june else "calendar",
                "benchmark_universe": "research_cohort_equal_weight",
                "sp500_proxy": "SPY_total_return_proxy_close_plus_dividends",
                "selection_method": selection_method,
                "n_holdings": int(n_holdings),
                "use_point_in_time": bool(use_point_in_time),
                "reconstitution": "annual",
            },
            "holdings": [
                {
                    "symbol": h.symbol,
                    "name": h.name,
                    "sector": h.sector,
                    "weight": round(h.weight * 100, 2),
                    "rd_intensity": round(h.rd_intensity, 2),
                }
                for h in start_holdings
            ],
            "holdings_by_year": {
                int(y): [
                    {
                        "symbol": h.symbol,
                        "name": h.name,
                        "sector": h.sector,
                        "weight": round(float(h.weight) * 100, 2),
                        "rd_intensity": round(float(h.rd_intensity), 2),
                    }
                    for h in holdings_by_year.get(int(y), [])
                ]
                for y in years
            },
            "portfolio_performance": portfolio_perf,
            "benchmark_performance": benchmark_perf,
            "sp500_performance": sp500_perf,
            "excess_return": round(float(portfolio_perf.get("annualized_return", 0.0)) - float(benchmark_perf.get("annualized_return", 0.0)), 2),
            "excess_vs_sp500": round(float(portfolio_perf.get("annualized_return", 0.0)) - float(sp500_perf.get("annualized_return", 0.0)), 2) if sp500_perf.get("annualized_return") else None,
            "portfolio_performance_net": portfolio_perf_net,
            "benchmark_performance_net": benchmark_perf_net,
            "excess_return_net": round(float(portfolio_perf_net.get("annualized_return", 0.0)) - float(benchmark_perf_net.get("annualized_return", 0.0)), 2),
            "turnover": {
                "avg_turnover_pct": round(avg_turnover * 100, 1),
                "max_turnover_pct": round(max_turnover * 100, 1),
                "by_year": turnover_by_year,
                "note": "Turnover is computed as 0.5 * sum |w_t - w_{t-1}|. First year turnover reflects initial formation and is excluded from averages.",
            },
            "cost_assumptions": {
                "cost_model": f"sp500_{cost_estimator.cost_model}",
                "round_trip_cost_per_100pct_turnover_pct": round(round_trip_cost_per_full_turnover * 100, 3),
                "benchmark_cost_pct": round(benchmark_cost * 100, 3),
                "note": "Net-of-cost series is a simple approximation: annual trading cost is proportional to realized turnover using literature-calibrated cost parameters.",
            },
            "yearly_data": yearly_data,
        }
