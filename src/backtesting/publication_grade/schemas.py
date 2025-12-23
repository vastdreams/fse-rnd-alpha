# PATH: src/backtesting/publication_grade/schemas.py
# PURPOSE:
#   - Define data schemas for publication-grade portfolio analysis
#   - Strong typing for all intermediate and output data structures
#
# ROLE IN ARCHITECTURE:
#   - Domain schemas used by portfolio engine and inference modules
#
# NOTES FOR FUTURE AI:
#   - All returns are stored in DECIMAL form (0.10 = 10%)
#   - Dates use ISO format strings for serialization
#   - Quintiles: Q1=lowest factor, Q5=highest factor

from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional, Any
from enum import Enum


class FormationTiming(Enum):
    """When portfolios are formed each year."""
    JANUARY = "january"      # Form Jan 1 (aggressive, potential look-ahead)
    JUNE_END = "june_end"    # Form June 30 (Fama-French convention)
    JULY = "july"            # Form July 1 (standard academic convention)


class RDTreatment(Enum):
    """How to handle zero vs missing R&D."""
    EXCLUDE_ZERO = "exclude_zero"          # Current (problematic) behavior
    INCLUDE_ZERO = "include_zero"          # Zero is valid observation
    SEPARATE_BUCKET = "separate_bucket"     # Zero gets own bucket


@dataclass
class FormationPeriod:
    """
    Represents a single portfolio formation period.
    
    At formation_date, we use accounting data from fiscal_year_used
    (which should be fully disclosed by formation_date).
    """
    formation_date: date           # When portfolio is formed (e.g., July 1, 2020)
    fiscal_year_used: int          # FY used for ranking (e.g., FY2019)
    holding_start: date            # Start of holding period (= formation_date)
    holding_end: date              # End of holding period (e.g., June 30, 2021)
    
    def __post_init__(self):
        """Validate that fiscal year is properly lagged."""
        formation_year = self.formation_date.year
        # FY used should be at least 6 months before formation
        # (Allows time for 10-K filing)
        if self.fiscal_year_used >= formation_year:
            raise ValueError(
                f"Look-ahead bias: FY{self.fiscal_year_used} not available at {self.formation_date}. "
                f"Use FY{formation_year - 1} or earlier."
            )


@dataclass
class CompanyFactorData:
    """Factor data for a single company at formation."""
    ticker: str
    cik: Optional[str] = None
    
    # R&D data (from fiscal_year_used)
    rd_expense: Optional[float] = None        # Raw R&D expense (USD)
    revenue: Optional[float] = None           # Revenue (USD)
    rd_intensity: Optional[float] = None      # rd_expense / revenue (decimal)
    rd_intensity_winsorized: Optional[float] = None  # After outlier treatment
    
    # Filing metadata
    fiscal_year: Optional[int] = None
    filing_date: Optional[date] = None        # When 10-K was filed with SEC
    
    # Data quality flags
    rd_is_zero: bool = False                  # Explicitly reported as zero
    rd_is_missing: bool = False               # Not reported / NULL
    is_eligible: bool = True                  # Meets all eligibility criteria


@dataclass
class PortfolioReturn:
    """
    Return for a portfolio over a single period.
    
    This is the fundamental building block - we compute statistics
    from a TIME SERIES of these, not from cross-sectional averages.
    """
    period_start: date
    period_end: date
    quintile: int                    # 1-5 (1=low, 5=high)
    
    # Portfolio return (equal-weighted)
    return_ew: float                 # Decimal (0.10 = 10%)
    
    # Optional: value-weighted return
    return_vw: Optional[float] = None
    
    # Portfolio composition
    n_stocks: int = 0
    tickers: List[str] = field(default_factory=list)
    
    # Factor exposure at formation
    avg_factor_value: float = 0.0   # Average R&D intensity in quintile


@dataclass
class QuintileTimeSeries:
    """
    Full time series of returns for a quintile.
    This is what we use for proper statistical inference.
    """
    quintile: int
    returns: List[PortfolioReturn]
    
    @property
    def return_series(self) -> List[float]:
        """Extract just the return values."""
        return [r.return_ew for r in self.returns]
    
    @property
    def n_periods(self) -> int:
        return len(self.returns)
    
    def mean_return(self) -> float:
        """Arithmetic mean of returns (decimal)."""
        if not self.returns:
            return 0.0
        return sum(r.return_ew for r in self.returns) / len(self.returns)
    
    def geometric_mean_return(self) -> float:
        """Geometric mean (compound) return (decimal)."""
        if not self.returns:
            return 0.0
        product = 1.0
        for r in self.returns:
            product *= (1 + r.return_ew)
        return product ** (1 / len(self.returns)) - 1
    
    def volatility(self) -> float:
        """Standard deviation of returns (time-series, not cross-sectional)."""
        import numpy as np
        if len(self.returns) < 2:
            return 0.0
        return float(np.std([r.return_ew for r in self.returns], ddof=1))


@dataclass 
class FactorPremiumSeries:
    """
    Time series of Q5 - Q1 spreads (the "R&D factor" return).
    This is what we regress against Fama-French factors.
    """
    periods: List[date]
    premiums: List[float]           # Q5 return - Q1 return each period
    
    # Components
    q5_returns: List[float]
    q1_returns: List[float]
    
    @property
    def mean_premium(self) -> float:
        if not self.premiums:
            return 0.0
        return sum(self.premiums) / len(self.premiums)


@dataclass
class InferenceResult:
    """
    Results of statistical inference with proper standard errors.
    """
    # Point estimates
    mean_return: float              # Annualized mean return (decimal)
    volatility: float               # Annualized volatility
    sharpe_ratio: float             # (mean - rf) / vol
    
    # Inference with HAC standard errors
    t_statistic: float              # t = mean / HAC_se
    p_value: float
    standard_error: float           # HAC (Newey-West) SE
    confidence_interval_95: tuple   # (lower, upper)
    
    # Sample info
    n_observations: int
    n_lags_used: int                # For Newey-West
    
    # Quality flags
    overlapping_returns: bool = False
    hac_adjustment_applied: bool = True


@dataclass
class BacktestOutput:
    """
    Complete backtest output suitable for publication.
    Auto-generates paper numbers to prevent drift.
    """
    # Metadata
    run_timestamp: str
    data_version: str
    commit_hash: Optional[str] = None
    
    # Configuration
    formation_timing: FormationTiming = FormationTiming.JULY
    rd_treatment: RDTreatment = RDTreatment.INCLUDE_ZERO
    rebalance_frequency: str = "annual"
    
    # Core results
    quintile_series: Dict[int, QuintileTimeSeries] = field(default_factory=dict)
    factor_premium_series: Optional[FactorPremiumSeries] = None
    
    # Statistical inference
    quintile_inference: Dict[int, InferenceResult] = field(default_factory=dict)
    premium_inference: Optional[InferenceResult] = None
    
    # Factor regression results (FF3/FF5)
    factor_regression: Optional[Dict[str, Any]] = None
    
    def to_paper_numbers(self) -> Dict[str, str]:
        """
        Generate exact numbers for paper insertion.
        Call this to get publication-ready statistics.
        """
        numbers = {
            "run_timestamp": self.run_timestamp,
            "data_version": self.data_version,
        }
        
        if self.premium_inference:
            pi = self.premium_inference
            numbers["rd_premium_annual_pct"] = f"{pi.mean_return * 100:.2f}"
            numbers["rd_premium_tstat"] = f"{pi.t_statistic:.2f}"
            numbers["rd_premium_pvalue"] = f"{pi.p_value:.4f}"
            numbers["rd_premium_sharpe"] = f"{pi.sharpe_ratio:.2f}"
        
        for q, inf in self.quintile_inference.items():
            numbers[f"q{q}_return_annual_pct"] = f"{inf.mean_return * 100:.2f}"
            numbers[f"q{q}_volatility_pct"] = f"{inf.volatility * 100:.2f}"
            numbers[f"q{q}_tstat"] = f"{inf.t_statistic:.2f}"
        
        return numbers

