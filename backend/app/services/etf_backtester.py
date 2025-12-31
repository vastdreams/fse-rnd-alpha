"""
PATH: backend/app/services/etf_backtester.py
PURPOSE:
  - Monthly return simulation for ETF backtesting
  - Annual July reconstitution with equal-weight rebalancing
  - Delisting handling with return adjustment
  - Turnover tracking and net-of-cost series

ROLE IN ARCHITECTURE:
  - Called by PortfolioOptimizer.backtest_rd_etf() for monthly granularity
  - Uses ETFUniverseBuilder for point-in-time eligibility
  - Uses RDAlphaScorer for holdings selection

MAIN EXPORTS:
  - ETFBacktester: Main backtesting engine
  - MonthlyBacktestResult: Complete backtest result with all metrics

NON-RESPONSIBILITIES:
  - Does not determine eligibility (see etf_universe.py)
  - Does not score companies (see rd_alpha_scorer.py)
  - Does not manage forecasts (see market_forecasts.py)

NOTES FOR FUTURE AI:
  - Formation date: July 1 of as_of_year
  - Holdings held July T to June T+1
  - Equal-weight at formation, drift during year
  - Delistings apply delisting return in month of delisting
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import date, timedelta
from calendar import monthrange
import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FMPDailyPrice,
    DelistingReturn,
    FamaFrenchFactor,
    RiskFreeRate,
)
from app.services.etf_universe import EligibilityResult, EligibilityMode
from app.services.transaction_costs import TransactionCostEstimator

logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration
# ==============================================================================

# Formation month (1=January, 7=July)
FORMATION_MONTH = 7

# Default risk-free rate when database has no data
DEFAULT_RISK_FREE_RATE = 0.02  # 2% annual

# Benchmark symbol for S&P 500 (SPY ETF)
BENCHMARK_SYMBOL = "SPY"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class MonthlyReturn:
    """Single month return for a holding."""
    symbol: str
    year: int
    month: int
    return_pct: float
    is_delisting: bool = False


@dataclass
class MonthlyPortfolioReturn:
    """Portfolio return for a single month."""
    year: int
    month: int
    date: date
    portfolio_return: float       # Weighted return
    benchmark_return: float       # SPY return
    sp500_return: float           # S&P 500 return (from FF factors)
    excess_vs_benchmark: float
    excess_vs_sp500: float
    n_holdings: int
    n_delistings: int
    
    # Weight-adjusted for missing returns
    effective_weight: float


@dataclass
class PerformanceMetrics:
    """Standard performance metrics."""
    total_return: float           # Total cumulative return (%)
    annualized_return: float      # CAGR (%)
    volatility: float             # Annualized volatility (%)
    sharpe_ratio: float           # Risk-adjusted return
    max_drawdown: float           # Maximum peak-to-trough drawdown (%)
    
    # Additional metrics
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "total_return": round(self.total_return, 2),
            "annualized_return": round(self.annualized_return, 2),
            "volatility": round(self.volatility, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 2),
        }


@dataclass
class TurnoverMetrics:
    """Turnover statistics."""
    by_year: List[Dict]
    avg_turnover_pct: float
    max_turnover_pct: float
    total_cost_pct: float
    
    def to_dict(self) -> Dict:
        return {
            "by_year": self.by_year,
            "avg_turnover_pct": round(self.avg_turnover_pct, 1),
            "max_turnover_pct": round(self.max_turnover_pct, 1),
            "total_cost_pct": round(self.total_cost_pct, 2),
        }


@dataclass
class Holding:
    """Single holding in portfolio."""
    symbol: str
    name: str
    sector: str
    weight: float
    rd_intensity: float


@dataclass
class MonthlyBacktestResult:
    """Complete monthly backtest result."""
    period: str
    start_year: int
    end_year: int
    n_holdings: int
    
    # Eligibility info
    eligibility_mode: EligibilityMode
    eligibility_warnings: List[str]
    
    # Holdings
    initial_holdings: List[Holding]
    holdings_by_year: Dict[int, List[Holding]]
    
    # Performance
    portfolio_performance: PerformanceMetrics
    benchmark_performance: PerformanceMetrics
    sp500_performance: PerformanceMetrics
    
    # Net of costs
    portfolio_performance_net: PerformanceMetrics
    
    # Excess returns
    excess_vs_benchmark: float
    excess_vs_sp500: float
    
    # Turnover
    turnover: TurnoverMetrics
    
    # Monthly series (for charting)
    monthly_data: List[Dict]
    
    # Yearly aggregates (backward compatible)
    yearly_data: List[Dict]
    
    # Metadata
    meta: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "period": self.period,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "n_holdings": self.n_holdings,
            "meta": self.meta,
            "holdings": [
                {
                    "symbol": h.symbol,
                    "name": h.name,
                    "sector": h.sector,
                    "weight": round(h.weight * 100, 2),
                    "rd_intensity": round(h.rd_intensity, 2),
                }
                for h in self.initial_holdings
            ],
            "holdings_by_year": {
                y: [
                    {
                        "symbol": h.symbol,
                        "name": h.name,
                        "sector": h.sector,
                        "weight": round(h.weight * 100, 2),
                        "rd_intensity": round(h.rd_intensity, 2),
                    }
                    for h in holdings
                ]
                for y, holdings in self.holdings_by_year.items()
            },
            "portfolio_performance": self.portfolio_performance.to_dict(),
            "benchmark_performance": self.benchmark_performance.to_dict(),
            "sp500_performance": self.sp500_performance.to_dict(),
            "portfolio_performance_net": self.portfolio_performance_net.to_dict(),
            "excess_return": round(self.excess_vs_benchmark, 2),
            "excess_vs_sp500": round(self.excess_vs_sp500, 2),
            "turnover": self.turnover.to_dict(),
            "monthly_data": self.monthly_data,
            "yearly_data": self.yearly_data,
        }


# ==============================================================================
# ETF Backtester
# ==============================================================================

class ETFBacktester:
    """
    Monthly ETF backtester with annual July reconstitution.
    
    Simulation Rules:
    - Formation date: July 1 of as_of_year
    - Equal-weight at formation (1/n for each holding)
    - Hold July T through June T+1
    - Reconstitute + rebalance each July
    - Delistings: apply delisting return, remove from portfolio, renormalize
    
    Return Calculation:
    - Monthly returns from month-end adjusted close prices
    - Portfolio return = weighted average of constituent returns
    - Missing returns: renormalize weights among available
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._rf_cache: Dict[int, float] = {}
        self._price_cache: Dict[Tuple[str, int, int], Optional[float]] = {}
        # Delisting handling for survivorship bias:
        # We cache delist dates (not “delist returns”), and compute the month’s return from prices
        # up to the delist date (cash earns 0% thereafter in that month).
        self._delisting_cache: Dict[str, date] = {}
    
    async def run_backtest(
        self,
        start_year: int,
        end_year: int,
        holdings_by_year: Dict[int, List[Holding]],
        eligibility_result: Optional[EligibilityResult] = None,
        cost_model: str = "moderate",
    ) -> MonthlyBacktestResult:
        """
        Run monthly backtest with provided holdings.
        
        Args:
            start_year: First year of backtest (July start_year to June start_year+1 is first period)
            end_year: Last year of backtest
            holdings_by_year: Dict mapping year -> list of holdings (selected at July of that year)
            eligibility_result: Eligibility metadata from universe builder
            cost_model: Transaction cost model ("low", "moderate", "high")
            
        Returns:
            MonthlyBacktestResult with full metrics and series
        """
        # Pre-load caches
        await self._load_delistings(holdings_by_year)
        
        # Generate month sequence: July start_year through June end_year+1
        months = self._generate_month_sequence(start_year, end_year)
        
        # Calculate monthly returns
        monthly_returns: List[MonthlyPortfolioReturn] = []
        turnover_by_year: List[Dict] = []
        prev_weights: Dict[str, float] = {}
        
        for year, month in months:
            # Determine which year's holdings to use
            # July T uses holdings selected in year T
            # Aug-Dec T uses holdings from year T
            # Jan-Jun T+1 uses holdings from year T
            if month >= FORMATION_MONTH:
                holdings_year = year
            else:
                holdings_year = year - 1
            
            holdings = holdings_by_year.get(holdings_year, [])
            if not holdings:
                continue
            
            # Check for reconstitution (July = new holdings)
            if month == FORMATION_MONTH:
                curr_weights = {h.symbol: h.weight for h in holdings}
                
                # Calculate turnover
                if prev_weights:
                    turnover = self._calculate_turnover(prev_weights, curr_weights)
                else:
                    turnover = 0.0  # First period
                
                turnover_by_year.append({
                    "year": year,
                    "turnover": round(turnover, 4),
                    "turnover_pct": round(turnover * 100, 1),
                    "n_holdings": len(holdings),
                })
                
                prev_weights = curr_weights.copy()
            
            # Calculate portfolio return for this month
            month_result = await self._calculate_monthly_return(
                year=year,
                month=month,
                holdings=holdings,
            )
            monthly_returns.append(month_result)
        
        if not monthly_returns:
            raise ValueError(f"No returns calculated for period {start_year}-{end_year}")
        
        # Aggregate to performance metrics
        portfolio_returns = [m.portfolio_return for m in monthly_returns]
        benchmark_returns = [m.benchmark_return for m in monthly_returns]
        sp500_returns = [m.sp500_return for m in monthly_returns]
        
        # Calculate performance metrics
        portfolio_perf = self._calculate_performance(portfolio_returns, monthly_returns)
        benchmark_perf = self._calculate_performance(benchmark_returns, monthly_returns)
        sp500_perf = self._calculate_performance(sp500_returns, monthly_returns)
        
        # Net-of-cost performance
        cost_estimator = TransactionCostEstimator(universe="sp500", cost_model=cost_model)
        n_holdings = len(holdings_by_year.get(start_year, []))
        cost_template = cost_estimator.estimate_portfolio_cost(n_holdings=n_holdings, rebalancing_frequency="annual")
        round_trip_cost = cost_template.round_trip_total
        
        # Apply costs based on realized turnover
        total_cost = 0.0
        for t in turnover_by_year[1:]:  # Skip first year (formation)
            total_cost += round_trip_cost * t.get("turnover", 0.0)
        
        portfolio_returns_net = portfolio_returns.copy()
        # Distribute costs across months (simplified)
        cost_per_month = total_cost / len(portfolio_returns_net) if portfolio_returns_net else 0
        portfolio_returns_net = [r - cost_per_month for r in portfolio_returns_net]
        portfolio_perf_net = self._calculate_performance(portfolio_returns_net, monthly_returns)
        
        # Aggregate to yearly data (backward compatible)
        yearly_data = self._aggregate_to_yearly(monthly_returns)
        
        # Build monthly data for charting
        monthly_data = [
            {
                "year": m.year,
                "month": m.month,
                "date": m.date.isoformat(),
                "portfolio_return": round(m.portfolio_return * 100, 2),
                "benchmark_return": round(m.benchmark_return * 100, 2),
                "sp500_return": round(m.sp500_return * 100, 2),
                "excess_vs_benchmark": round(m.excess_vs_benchmark * 100, 2),
                "excess_vs_sp500": round(m.excess_vs_sp500 * 100, 2),
                "n_holdings": m.n_holdings,
                "n_delistings": m.n_delistings,
            }
            for m in monthly_returns
        ]
        
        # Turnover metrics
        turnover_values = [t.get("turnover", 0.0) for t in turnover_by_year[1:]]
        turnover_metrics = TurnoverMetrics(
            by_year=turnover_by_year,
            avg_turnover_pct=float(np.mean(turnover_values) * 100) if turnover_values else 0.0,
            max_turnover_pct=float(np.max(turnover_values) * 100) if turnover_values else 0.0,
            total_cost_pct=total_cost * 100,
        )
        
        # Build meta
        meta = {
            "return_convention": "july_june",
            "return_granularity": "monthly",
            "formation_month": "July",
            "weighting": "equal_weight",
            "rebalancing": "annual",
            "benchmark": "SPY",
            "cost_model": cost_model,
        }
        
        if eligibility_result:
            meta.update(eligibility_result.to_meta_dict())
        
        return MonthlyBacktestResult(
            period=f"{start_year}-{end_year}",
            start_year=start_year,
            end_year=end_year,
            n_holdings=n_holdings,
            eligibility_mode=eligibility_result.mode if eligibility_result else EligibilityMode.PROVISIONAL,
            eligibility_warnings=eligibility_result.warnings if eligibility_result else [],
            initial_holdings=holdings_by_year.get(start_year, []),
            holdings_by_year=holdings_by_year,
            portfolio_performance=portfolio_perf,
            benchmark_performance=benchmark_perf,
            sp500_performance=sp500_perf,
            portfolio_performance_net=portfolio_perf_net,
            excess_vs_benchmark=portfolio_perf.annualized_return - benchmark_perf.annualized_return,
            excess_vs_sp500=portfolio_perf.annualized_return - sp500_perf.annualized_return,
            turnover=turnover_metrics,
            monthly_data=monthly_data,
            yearly_data=yearly_data,
            meta=meta,
        )
    
    def _generate_month_sequence(self, start_year: int, end_year: int) -> List[Tuple[int, int]]:
        """Generate sequence of (year, month) tuples from July start_year to June end_year+1."""
        months = []
        
        for year in range(start_year, end_year + 2):
            if year == start_year:
                # First year: July-December
                for month in range(FORMATION_MONTH, 13):
                    months.append((year, month))
            elif year == end_year + 1:
                # Last year: January-June
                for month in range(1, FORMATION_MONTH):
                    months.append((year, month))
            else:
                # Middle years: July-December and January-June
                for month in range(FORMATION_MONTH, 13):
                    months.append((year, month))
                # Next calendar year's Jan-June
                for month in range(1, FORMATION_MONTH):
                    months.append((year + 1, month))
                    
        # Remove duplicates and sort
        months = sorted(set(months))
        
        # Filter to valid range
        start_date = date(start_year, FORMATION_MONTH, 1)
        end_date = date(end_year + 1, FORMATION_MONTH - 1, 28)  # June end_year+1
        
        return [(y, m) for y, m in months if start_date <= date(y, m, 1) <= end_date]
    
    async def _load_delistings(self, holdings_by_year: Dict[int, List[Holding]]):
        """Pre-load delisting data for all symbols."""
        all_symbols = set()
        for holdings in holdings_by_year.values():
            for h in holdings:
                all_symbols.add(h.symbol)
        
        if not all_symbols:
            return
        
        result = await self.session.execute(
            select(
                DelistingReturn.symbol,
                DelistingReturn.delist_date,
            )
            .where(DelistingReturn.symbol.in_(all_symbols))
        )
        
        for symbol, delist_date in result.fetchall():
            if symbol and delist_date:
                self._delisting_cache[str(symbol)] = delist_date
    
    async def _calculate_monthly_return(
        self,
        year: int,
        month: int,
        holdings: List[Holding],
    ) -> MonthlyPortfolioReturn:
        """Calculate portfolio return for a single month."""
        
        # Get month-end date
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)
        
        # Previous month end
        if month == 1:
            prev_month_end = date(year - 1, 12, 31)
        else:
            _, prev_last = monthrange(year, month - 1)
            prev_month_end = date(year, month - 1, prev_last)
        
        portfolio_return = 0.0
        total_weight = 0.0
        n_delistings = 0
        
        for h in holdings:
            weight = h.weight
            symbol = h.symbol
            
            # Check for delisting
            if symbol in self._delisting_cache:
                delist_date = self._delisting_cache[symbol]
                if prev_month_end < delist_date <= month_end:
                    # Delisting happened this month: compute return to the delist date (cash thereafter).
                    start_price = await self._get_price_near_date(symbol, prev_month_end)
                    end_price = await self._get_price_near_date(symbol, delist_date)
                    if start_price is not None and end_price is not None and start_price > 0:
                        ret = (end_price - start_price) / start_price
                        portfolio_return += weight * float(ret)
                        total_weight += weight
                        n_delistings += 1
                    continue
                elif delist_date <= prev_month_end:
                    # Already delisted
                    continue
            
            # Get monthly return from prices
            ret = await self._get_monthly_return(symbol, year, month)
            if ret is not None:
                portfolio_return += weight * ret
                total_weight += weight
        
        # Renormalize for missing
        if total_weight > 0:
            portfolio_return = portfolio_return / total_weight
        else:
            portfolio_return = 0.0
        
        # Get benchmark return (SPY)
        benchmark_return = await self._get_monthly_return(BENCHMARK_SYMBOL, year, month)
        if benchmark_return is None:
            benchmark_return = 0.0
        
        # Get S&P 500 return from Fama-French
        sp500_return = await self._get_ff_market_return(year, month)
        if sp500_return is None:
            sp500_return = benchmark_return  # Fallback
        
        return MonthlyPortfolioReturn(
            year=year,
            month=month,
            date=month_end,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            sp500_return=sp500_return,
            excess_vs_benchmark=portfolio_return - benchmark_return,
            excess_vs_sp500=portfolio_return - sp500_return,
            n_holdings=len(holdings),
            n_delistings=n_delistings,
            effective_weight=total_weight,
        )
    
    async def _get_monthly_return(
        self,
        symbol: str,
        year: int,
        month: int,
    ) -> Optional[float]:
        """Get monthly return for a symbol from price data."""
        cache_key = (symbol, year, month)
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        # Get month-end and previous month-end prices
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)
        
        if month == 1:
            prev_month_end = date(year - 1, 12, 31)
        else:
            _, prev_last = monthrange(year, month - 1)
            prev_month_end = date(year, month - 1, prev_last)
        
        # Query for closest prices to month-end dates
        end_price = await self._get_price_near_date(symbol, month_end)
        start_price = await self._get_price_near_date(symbol, prev_month_end)
        
        if end_price is None or start_price is None or start_price <= 0:
            self._price_cache[cache_key] = None
            return None
        
        ret = (end_price - start_price) / start_price
        self._price_cache[cache_key] = ret
        return ret
    
    async def _get_price_near_date(
        self,
        symbol: str,
        target_date: date,
        window_days: int = 5,
    ) -> Optional[float]:
        """Get adjusted close price near a target date."""
        result = await self.session.execute(
            select(FMPDailyPrice.adj_close, FMPDailyPrice.close)
            .where(
                FMPDailyPrice.symbol == symbol,
                FMPDailyPrice.date >= target_date - timedelta(days=window_days),
                FMPDailyPrice.date <= target_date,
            )
            .order_by(FMPDailyPrice.date.desc())
            .limit(1)
        )
        row = result.fetchone()
        
        if row:
            return float(row[0]) if row[0] else (float(row[1]) if row[1] else None)
        return None
    
    async def _get_ff_market_return(self, year: int, month: int) -> Optional[float]:
        """Get S&P 500 return from Fama-French factors."""
        result = await self.session.execute(
            select(FamaFrenchFactor.mkt_rf, FamaFrenchFactor.rf)
            .where(
                FamaFrenchFactor.frequency == "monthly",
                func.extract("year", FamaFrenchFactor.date) == year,
                func.extract("month", FamaFrenchFactor.date) == month,
            )
            .limit(1)
        )
        row = result.fetchone()
        
        if row and row[0] is not None and row[1] is not None:
            return float(row[0]) + float(row[1])
        return None
    
    async def _get_risk_free_rate(self, year: int) -> float:
        """Get annual risk-free rate."""
        if year in self._rf_cache:
            return self._rf_cache[year]
        
        result = await self.session.execute(
            select(func.avg(RiskFreeRate.rate_annual_pct))
            .where(
                RiskFreeRate.date >= date(year, 1, 1),
                RiskFreeRate.date <= date(year, 12, 31),
            )
        )
        avg_rate = result.scalar()
        
        if avg_rate is not None:
            rate = float(avg_rate) / 100
        else:
            rate = DEFAULT_RISK_FREE_RATE
        
        self._rf_cache[year] = rate
        return rate
    
    def _calculate_turnover(
        self,
        prev_weights: Dict[str, float],
        curr_weights: Dict[str, float],
    ) -> float:
        """Calculate one-way turnover (0.5 * sum of absolute weight changes)."""
        all_symbols = set(prev_weights.keys()) | set(curr_weights.keys())
        total_change = sum(
            abs(curr_weights.get(s, 0.0) - prev_weights.get(s, 0.0))
            for s in all_symbols
        )
        return 0.5 * total_change
    
    def _calculate_performance(
        self,
        monthly_returns: List[float],
        monthly_data: List[MonthlyPortfolioReturn],
    ) -> PerformanceMetrics:
        """Calculate performance metrics from monthly return series."""
        if not monthly_returns:
            return PerformanceMetrics(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0,
            )
        
        # Total return (compound)
        total_return = float(np.prod([1 + r for r in monthly_returns]) - 1)
        
        # Annualized return (CAGR)
        n_months = len(monthly_returns)
        n_years = n_months / 12
        if n_years > 0:
            annualized_return = float((1 + total_return) ** (1 / n_years) - 1)
        else:
            annualized_return = 0.0
        
        # Annualized volatility (monthly std * sqrt(12))
        if len(monthly_returns) > 1:
            volatility = float(np.std(monthly_returns, ddof=1)) * np.sqrt(12)
        else:
            volatility = 0.0
        
        # Sharpe ratio (using average annual RF over period)
        years_in_period = sorted(set(m.year for m in monthly_data))
        avg_rf = DEFAULT_RISK_FREE_RATE  # Simplified
        
        excess_return = annualized_return - avg_rf
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0.0
        
        # Max drawdown
        cumulative = np.cumprod([1 + r for r in monthly_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        return PerformanceMetrics(
            total_return=total_return * 100,
            annualized_return=annualized_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown * 100,
        )
    
    def _aggregate_to_yearly(
        self,
        monthly_returns: List[MonthlyPortfolioReturn],
    ) -> List[Dict]:
        """Aggregate monthly returns to yearly (July-June) for backward compatibility."""
        # Group by fiscal year (July T to June T+1 = fiscal year T)
        by_fiscal_year: Dict[int, List[MonthlyPortfolioReturn]] = {}
        
        for m in monthly_returns:
            if m.month >= FORMATION_MONTH:
                fiscal_year = m.year
            else:
                fiscal_year = m.year - 1
            
            if fiscal_year not in by_fiscal_year:
                by_fiscal_year[fiscal_year] = []
            by_fiscal_year[fiscal_year].append(m)
        
        yearly_data = []
        
        for fiscal_year in sorted(by_fiscal_year.keys()):
            months = by_fiscal_year[fiscal_year]
            
            # Compound monthly returns
            port_returns = [m.portfolio_return for m in months]
            bench_returns = [m.benchmark_return for m in months]
            sp500_returns = [m.sp500_return for m in months]
            
            port_annual = float(np.prod([1 + r for r in port_returns]) - 1)
            bench_annual = float(np.prod([1 + r for r in bench_returns]) - 1)
            sp500_annual = float(np.prod([1 + r for r in sp500_returns]) - 1)
            
            yearly_data.append({
                "year": fiscal_year,
                "portfolio_return": round(port_annual * 100, 2),
                "benchmark_return": round(bench_annual * 100, 2),
                "sp500_return": round(sp500_annual * 100, 2),
                "excess_return": round((port_annual - bench_annual) * 100, 2),
                "excess_vs_sp500": round((port_annual - sp500_annual) * 100, 2),
                "n_months": len(months),
            })
        
        return yearly_data

