"""
PATH: backend/app/services/etf_backtester/data_classes.py
PURPOSE: Dataclass definitions and configuration constants for the ETF backtester.
WHY: Extracted so both mixin modules and the main backtester can import cleanly without cycles.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import date

from app.services.etf_universe import EligibilityResult, EligibilityMode


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
