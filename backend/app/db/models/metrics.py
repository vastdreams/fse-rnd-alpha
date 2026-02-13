"""
PATH: backend/app/db/models/metrics.py
PURPOSE: Research metrics ORM models (returns, momentum, volatility, risk-free rate, constituents, delisting, FF factors).
WHY: Tables for first-principles research metrics, market benchmarks, and survivorship-bias data.
DEPENDENCIES:
  - base: shared SQLAlchemy imports & Base
"""

from __future__ import annotations

from app.db.models.base import (
    Base, datetime, date_type, Optional, List,
    Integer, String, Float, Boolean, Date, DateTime, Text, JSON,
    ForeignKey, Index, UniqueConstraint,
    relationship, Mapped, mapped_column,
)


class JulyJuneReturn(Base):
    """
    Fama-French style returns: July T to June T+1.

    This eliminates look-ahead bias by ensuring FY(T-1) data is fully
    available (filed by March) before portfolio formation in July.

    Timeline:
    - FY 2019 ends Dec 31, 2019
    - 10-K filed by March 2020
    - Portfolio formed July 1, 2020 (formation_year = 2019)
    - Returns measured July 2020 - June 2021

    TIER-2 UPGRADE (Dec 2025):
    - Added data_tier to distinguish FMP (tier1) vs CRSP (tier2) returns
    - Added permno for CRSP linkage
    - PK is now (symbol, formation_year, data_tier)
    """
    __tablename__ = "july_june_returns"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    formation_year: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data_tier: Mapped[str] = mapped_column(
        String(10), primary_key=True, default="tier1"
    )  # 'tier1' (FMP daily) or 'tier2' (CRSP monthly)

    # CRSP linkage (Tier-2 only)
    permno: Mapped[Optional[int]] = mapped_column(Integer, index=True)

    # Price data
    july_start_price: Mapped[Optional[float]] = mapped_column(Float)
    june_end_price: Mapped[Optional[float]] = mapped_column(Float)

    # Return calculations
    total_return: Mapped[Optional[float]] = mapped_column(Float)  # (June_end / July_start) - 1
    annualized_return: Mapped[Optional[float]] = mapped_column(Float)

    # Volatility during the period
    volatility: Mapped[Optional[float]] = mapped_column(Float)  # Daily std * sqrt(252) or monthly * sqrt(12)

    # Data quality
    trading_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Computation provenance
    computation_run_id: Mapped[Optional[str]] = mapped_column(String(36))  # UUID

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_july_june_tier", "data_tier"),
    )


class MomentumCache(Base):
    """
    Cached 3-year momentum calculations.

    Based on Paper 3 findings: R&D premium persists over time.
    Momentum factor rewards companies with consistent prior performance.

    Formula:
    - Prior 3-year compound return for company
    - Compare to S&P 500 benchmark (or market average)
    - Excess return = Company - Benchmark
    - Momentum Factor = 1 + (excess_return_3yr * 0.1)
    """
    __tablename__ = "momentum_cache"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    as_of_year: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 3-year cumulative return (T-3 to T-1)
    cumulative_return_3yr: Mapped[Optional[float]] = mapped_column(Float)
    benchmark_return_3yr: Mapped[Optional[float]] = mapped_column(Float)  # S&P 500 same period
    excess_return_3yr: Mapped[Optional[float]] = mapped_column(Float)  # Company - Benchmark

    # Annualized
    annualized_return: Mapped[Optional[float]] = mapped_column(Float)
    annualized_excess: Mapped[Optional[float]] = mapped_column(Float)

    # Computed momentum factor
    momentum_factor: Mapped[Optional[float]] = mapped_column(Float)  # 1 + (excess * 0.1)

    # Data quality
    years_available: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VolatilityCache(Base):
    """
    Cached volatility calculations.

    Based on Paper 4 findings: Risk normalization ensures high-volatility
    companies don't dominate purely on R&D intensity.

    Formula:
    - Daily returns = (P_t / P_{t-1}) - 1
    - Daily std = std(daily_returns) over trailing 756 days (3 years)
    - Annualized volatility = daily_std * sqrt(252)
    """
    __tablename__ = "volatility_cache"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    as_of_year: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 3-year volatility (trailing, ending June 30)
    volatility_3yr: Mapped[Optional[float]] = mapped_column(Float)  # Annualized std dev

    # Components
    daily_std: Mapped[Optional[float]] = mapped_column(Float)
    trading_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Comparison to market
    market_volatility: Mapped[Optional[float]] = mapped_column(Float)  # S&P 500 same period
    relative_volatility: Mapped[Optional[float]] = mapped_column(Float)  # Company / Market

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskFreeRate(Base):
    """
    Historical risk-free rate data.

    Source: Ken French Data Library (1-month T-bill rate)
    Used for Sharpe ratio calculations and factor model analysis.
    """
    __tablename__ = "risk_free_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, unique=True, nullable=False, index=True)
    rate_annual_pct: Mapped[float] = mapped_column(Float, nullable=False)  # Annual percentage (e.g., 2.0 = 2%)
    rate_monthly: Mapped[Optional[float]] = mapped_column(Float)  # Monthly rate (continuous)
    source: Mapped[str] = mapped_column(String(50), default='FF_RF')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SP500HistoricalConstituent(Base):
    """
    Historical S&P 500 constituents.

    Tracks which companies were in the S&P 500 at each point in time.
    Required for survivorship-bias-free analysis.

    Data Sources:
    - fmp_historical: From FMP historical constituent API (most reliable)
    - estimated_from_data: Estimated from first year of financial data
    - current_member: Currently in index, add date estimated

    PUBLICATION FIX (Dec 2025): No longer uses placeholder dates (1900-01-01).
    All dates are either from FMP API or estimated from data availability.
    """
    __tablename__ = "sp500_historical_constituents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    permno: Mapped[Optional[int]] = mapped_column(Integer)  # CRSP permanent number

    # Membership period
    added_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    removed_date: Mapped[Optional[date_type]] = mapped_column(Date)
    removal_reason: Mapped[Optional[str]] = mapped_column(String(100))  # 'delisted', 'acquired', 'dropped', 'market_cap'

    # Company info at time of membership
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100))

    # Data provenance (added Dec 2025 for publication transparency)
    membership_source: Mapped[Optional[str]] = mapped_column(String(50))  # 'fmp_historical', 'estimated_from_data', 'current_member'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_sp500_hist_symbol_dates", "symbol", "added_date", "removed_date"),
    )


class DelistingReturn(Base):
    """
    Delisting returns for companies that exit the index.

    CRSP provides delisting returns (dlret) for stocks that delist.
    Critical for avoiding bias in return calculations.
    """
    __tablename__ = "delisting_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    permno: Mapped[Optional[int]] = mapped_column(Integer)
    delist_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    delist_return: Mapped[float] = mapped_column(Float, nullable=False)  # As decimal (e.g., -0.30 for -30%)
    delist_code: Mapped[Optional[int]] = mapped_column(Integer)  # CRSP delist code
    reason: Mapped[Optional[str]] = mapped_column(String(100))  # 'acquired', 'bankruptcy', etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "delist_date", name="uq_delist_symbol_date"),
    )


class FamaFrenchFactor(Base):
    """
    Fama-French factor data for spanning tests.

    Source: Ken French Data Library
    Contains MKT-RF, SMB, HML, RMW, CMA, and MOM factors.
    """
    __tablename__ = "ff_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)  # 'daily', 'monthly', 'annual'

    # FF3 Factors
    mkt_rf: Mapped[Optional[float]] = mapped_column(Float)  # Market excess return
    smb: Mapped[Optional[float]] = mapped_column(Float)     # Small minus Big
    hml: Mapped[Optional[float]] = mapped_column(Float)     # High minus Low (value)

    # FF5 Additional Factors
    rmw: Mapped[Optional[float]] = mapped_column(Float)     # Robust minus Weak (profitability)
    cma: Mapped[Optional[float]] = mapped_column(Float)     # Conservative minus Aggressive (investment)

    # Momentum
    mom: Mapped[Optional[float]] = mapped_column(Float)     # Momentum factor

    # Risk-free rate (for convenience)
    rf: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "frequency", name="uq_ff_date_freq"),
    )
