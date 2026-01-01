"""
PATH: backend/app/db/models.py
PURPOSE:
  - SQLAlchemy ORM models for all database tables
  - Mirrors existing schema from src/models/orm/

ROLE IN ARCHITECTURE:
  - Data model layer
"""

from __future__ import annotations

from datetime import datetime, date as date_type
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, 
    Text, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base


class Company(Base):
    """Company master table."""
    __tablename__ = "companies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    cik: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company_years: Mapped[List["CompanyYearCore"]] = relationship(back_populates="company")


class CompanyYearCore(Base):
    """Company-year data core table."""
    __tablename__ = "company_year_core"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    cik: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filing_date: Mapped[Optional[date_type]] = mapped_column(Date)
    sec_accession_id: Mapped[Optional[str]] = mapped_column(String(50))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(50))
    report_path: Mapped[Optional[str]] = mapped_column(String(500))
    report_hash: Mapped[Optional[str]] = mapped_column(String(64))
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_company_year"),
        Index("ix_company_year_ticker_year", "ticker", "fiscal_year"),
    )
    
    # Relationships
    company: Mapped["Company"] = relationship(back_populates="company_years")
    financials_core: Mapped[Optional["FinancialsCore"]] = relationship(back_populates="company_year", uselist=False)
    financials_ratios: Mapped[Optional["FinancialsRatios"]] = relationship(back_populates="company_year", uselist=False)
    text_factor_rd: Mapped[Optional["TextFactorRD"]] = relationship(back_populates="company_year", uselist=False)
    annual_report: Mapped[Optional["AnnualReport"]] = relationship(back_populates="company_year", uselist=False)


class FinancialsCore(Base):
    """Core financial data from XBRL."""
    __tablename__ = "financials_core"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_year_id: Mapped[int] = mapped_column(Integer, ForeignKey("company_year_core.id"), unique=True, nullable=False)
    
    # Income Statement
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    cost_of_revenue: Mapped[Optional[float]] = mapped_column(Float)
    gross_profit: Mapped[Optional[float]] = mapped_column(Float)
    rd_expense: Mapped[Optional[float]] = mapped_column(Float)
    sga_expense: Mapped[Optional[float]] = mapped_column(Float)
    operating_income: Mapped[Optional[float]] = mapped_column(Float)
    ebit: Mapped[Optional[float]] = mapped_column(Float)
    interest_expense: Mapped[Optional[float]] = mapped_column(Float)
    pretax_income: Mapped[Optional[float]] = mapped_column(Float)
    income_tax: Mapped[Optional[float]] = mapped_column(Float)
    net_income: Mapped[Optional[float]] = mapped_column(Float)
    eps_basic: Mapped[Optional[float]] = mapped_column(Float)
    eps_diluted: Mapped[Optional[float]] = mapped_column(Float)
    
    # Balance Sheet
    total_assets: Mapped[Optional[float]] = mapped_column(Float)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Float)
    short_term_investments: Mapped[Optional[float]] = mapped_column(Float)
    accounts_receivable: Mapped[Optional[float]] = mapped_column(Float)
    inventory: Mapped[Optional[float]] = mapped_column(Float)
    ppe_net: Mapped[Optional[float]] = mapped_column(Float)
    goodwill: Mapped[Optional[float]] = mapped_column(Float)
    intangible_assets: Mapped[Optional[float]] = mapped_column(Float)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float)
    short_term_debt: Mapped[Optional[float]] = mapped_column(Float)
    long_term_debt: Mapped[Optional[float]] = mapped_column(Float)
    total_equity: Mapped[Optional[float]] = mapped_column(Float)
    retained_earnings: Mapped[Optional[float]] = mapped_column(Float)
    
    # Cash Flow
    cash_from_operations: Mapped[Optional[float]] = mapped_column(Float)
    cash_from_investing: Mapped[Optional[float]] = mapped_column(Float)
    cash_from_financing: Mapped[Optional[float]] = mapped_column(Float)
    capex: Mapped[Optional[float]] = mapped_column(Float)
    depreciation_amortization: Mapped[Optional[float]] = mapped_column(Float)
    dividends_paid: Mapped[Optional[float]] = mapped_column(Float)
    share_repurchases: Mapped[Optional[float]] = mapped_column(Float)
    
    # Metadata
    source: Mapped[Optional[str]] = mapped_column(String(50))
    quality_flag: Mapped[Optional[str]] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company_year: Mapped["CompanyYearCore"] = relationship(back_populates="financials_core")


class FinancialsRatios(Base):
    """Computed financial ratios."""
    __tablename__ = "financials_ratios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_year_id: Mapped[int] = mapped_column(Integer, ForeignKey("company_year_core.id"), unique=True, nullable=False)
    
    # Profitability
    gross_margin: Mapped[Optional[float]] = mapped_column(Float)
    operating_margin: Mapped[Optional[float]] = mapped_column(Float)
    net_margin: Mapped[Optional[float]] = mapped_column(Float)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    roa: Mapped[Optional[float]] = mapped_column(Float)
    roic: Mapped[Optional[float]] = mapped_column(Float)
    
    # Leverage
    debt_to_equity: Mapped[Optional[float]] = mapped_column(Float)
    debt_to_assets: Mapped[Optional[float]] = mapped_column(Float)
    interest_coverage: Mapped[Optional[float]] = mapped_column(Float)
    
    # Liquidity
    current_ratio: Mapped[Optional[float]] = mapped_column(Float)
    quick_ratio: Mapped[Optional[float]] = mapped_column(Float)
    working_capital: Mapped[Optional[float]] = mapped_column(Float)
    
    # Cash Flow
    cfo_to_net_income: Mapped[Optional[float]] = mapped_column(Float)
    fcf: Mapped[Optional[float]] = mapped_column(Float)
    fcf_margin: Mapped[Optional[float]] = mapped_column(Float)
    dividend_coverage: Mapped[Optional[float]] = mapped_column(Float)
    cash_conversion: Mapped[Optional[float]] = mapped_column(Float)
    
    # Growth
    revenue_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    eps_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    fcf_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    
    # R&D Specific
    rd_intensity: Mapped[Optional[float]] = mapped_column(Float)
    rd_change_yoy: Mapped[Optional[float]] = mapped_column(Float)
    rd_3y_trend: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationships
    company_year: Mapped["CompanyYearCore"] = relationship(back_populates="financials_ratios")


class TextFactorRD(Base):
    """R&D text factors extracted from annual reports."""
    __tablename__ = "text_factor_rd"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_year_id: Mapped[int] = mapped_column(Integer, ForeignKey("company_year_core.id"), unique=True, nullable=False)
    
    # Mention counts
    rd_mentions_count: Mapped[Optional[int]] = mapped_column(Integer)
    research_mentions_count: Mapped[Optional[int]] = mapped_column(Integer)
    development_mentions_count: Mapped[Optional[int]] = mapped_column(Integer)
    innovation_mentions_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Section analysis
    rd_section_length_words: Mapped[Optional[int]] = mapped_column(Integer)
    rd_tone_score: Mapped[Optional[float]] = mapped_column(Float)
    rd_sentiment_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    rd_reporting_style: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Sections found
    rd_sections_found: Mapped[Optional[list]] = mapped_column(JSON)
    rd_primary_section: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Focus areas
    rd_focus_tags: Mapped[Optional[list]] = mapped_column(JSON)
    rd_technology_areas: Mapped[Optional[list]] = mapped_column(JSON)
    rd_geographic_mentions: Mapped[Optional[list]] = mapped_column(JSON)
    
    # Numbers and trends
    rd_numbers_mentioned: Mapped[Optional[list]] = mapped_column(JSON)
    rd_percentages_mentioned: Mapped[Optional[list]] = mapped_column(JSON)
    rd_trends_mentioned: Mapped[Optional[list]] = mapped_column(JSON)
    
    # Key content
    rd_key_paragraphs: Mapped[Optional[list]] = mapped_column(JSON)
    rd_strategic_priorities: Mapped[Optional[list]] = mapped_column(JSON)
    rd_competitive_mentions: Mapped[Optional[list]] = mapped_column(JSON)
    
    # Metadata
    extraction_version: Mapped[Optional[str]] = mapped_column(String(50))
    extraction_timestamp: Mapped[Optional[str]] = mapped_column(String(50))  # Stored as string in original DB
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float)
    verification_status: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Relationships
    company_year: Mapped["CompanyYearCore"] = relationship(back_populates="text_factor_rd")


class AnnualReport(Base):
    """Annual report file metadata."""
    __tablename__ = "annual_reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_year_id: Mapped[int] = mapped_column(Integer, ForeignKey("company_year_core.id"), unique=True, nullable=False)
    cik: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    filing_date: Mapped[Optional[date_type]] = mapped_column(Date)
    accession_id: Mapped[Optional[str]] = mapped_column(String(50))
    form_type: Mapped[str] = mapped_column(String(20), default="10-K")
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    file_format: Mapped[Optional[str]] = mapped_column(String(20))
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    document_count: Mapped[Optional[int]] = mapped_column(Integer)
    has_xbrl: Mapped[Optional[bool]] = mapped_column(Boolean)
    xbrl_url: Mapped[Optional[str]] = mapped_column(String(500))
    sections_found: Mapped[Optional[list]] = mapped_column(JSON)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company_year: Mapped["CompanyYearCore"] = relationship(back_populates="annual_report")


class Price(Base):
    """Stock price data."""
    __tablename__ = "prices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float)
    high: Mapped[Optional[float]] = mapped_column(Float)
    low: Mapped[Optional[float]] = mapped_column(Float)
    close: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[Optional[int]] = mapped_column(Integer)
    adjusted_close: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
    )


# ============================================================================
# FMP Data Models (from Financial Modeling Prep API)
# ============================================================================

class SP500Company(Base):
    """S&P 500 constituent companies."""
    __tablename__ = "sp500_companies"
    
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    sub_sector: Mapped[Optional[str]] = mapped_column(String(100))
    headquarters: Mapped[Optional[str]] = mapped_column(String(200))
    cik: Mapped[Optional[str]] = mapped_column(String(20))
    founded: Mapped[Optional[str]] = mapped_column(String(20))
    added_date: Mapped[Optional[date_type]] = mapped_column(Date)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)


class FMPIncomeStatement(Base):
    """FMP Income Statement data."""
    __tablename__ = "fmp_income_statements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period: Mapped[Optional[str]] = mapped_column(String(10))
    date: Mapped[Optional[date_type]] = mapped_column(Date)
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    cost_of_revenue: Mapped[Optional[float]] = mapped_column(Float)
    gross_profit: Mapped[Optional[float]] = mapped_column(Float)
    rd_expenses: Mapped[Optional[float]] = mapped_column(Float)
    # R&D reporting status: 'reported' (has value), 'zero' (explicitly 0), 'missing' (null/not disclosed)
    rd_status: Mapped[Optional[str]] = mapped_column(String(20), default='reported')
    sga_expenses: Mapped[Optional[float]] = mapped_column(Float)
    operating_expenses: Mapped[Optional[float]] = mapped_column(Float)
    operating_income: Mapped[Optional[float]] = mapped_column(Float)
    interest_expense: Mapped[Optional[float]] = mapped_column(Float)
    ebitda: Mapped[Optional[float]] = mapped_column(Float)
    net_income: Mapped[Optional[float]] = mapped_column(Float)
    eps: Mapped[Optional[float]] = mapped_column(Float)
    eps_diluted: Mapped[Optional[float]] = mapped_column(Float)
    shares_out: Mapped[Optional[int]] = mapped_column(Integer)
    
    __table_args__ = (
        UniqueConstraint("symbol", "fiscal_year", "period", name="uq_fmp_income"),
    )


class FMPBalanceSheet(Base):
    """FMP Balance Sheet data."""
    __tablename__ = "fmp_balance_sheets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period: Mapped[Optional[str]] = mapped_column(String(10))
    date: Mapped[Optional[date_type]] = mapped_column(Date)
    total_assets: Mapped[Optional[float]] = mapped_column(Float)
    total_current_assets: Mapped[Optional[float]] = mapped_column(Float)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Float)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float)
    total_current_liabilities: Mapped[Optional[float]] = mapped_column(Float)
    long_term_debt: Mapped[Optional[float]] = mapped_column(Float)
    total_debt: Mapped[Optional[float]] = mapped_column(Float)
    total_equity: Mapped[Optional[float]] = mapped_column(Float)
    retained_earnings: Mapped[Optional[float]] = mapped_column(Float)
    
    __table_args__ = (
        UniqueConstraint("symbol", "fiscal_year", "period", name="uq_fmp_balance"),
    )


class FMPCashFlow(Base):
    """FMP Cash Flow data."""
    __tablename__ = "fmp_cash_flows"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period: Mapped[Optional[str]] = mapped_column(String(10))
    date: Mapped[Optional[date_type]] = mapped_column(Date)
    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    investing_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    financing_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    capital_expenditure: Mapped[Optional[float]] = mapped_column(Float)
    free_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    dividends_paid: Mapped[Optional[float]] = mapped_column(Float)
    stock_repurchased: Mapped[Optional[float]] = mapped_column(Float)
    
    __table_args__ = (
        UniqueConstraint("symbol", "fiscal_year", "period", name="uq_fmp_cashflow"),
    )


class FMPDailyPrice(Base):
    """FMP Daily Price data."""
    __tablename__ = "fmp_daily_prices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float)
    high: Mapped[Optional[float]] = mapped_column(Float)
    low: Mapped[Optional[float]] = mapped_column(Float)
    close: Mapped[Optional[float]] = mapped_column(Float)
    adj_close: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[Optional[int]] = mapped_column(Integer)
    change_pct: Mapped[Optional[float]] = mapped_column(Float)
    vwap: Mapped[Optional[float]] = mapped_column(Float)
    
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_fmp_price"),
    )


class FMPDividend(Base):
    """
    FMP dividend events (ex-dividend dates).

    WHY THIS EXISTS:
      Our Tier-1 price ingestion uses the FMP *stable* EOD endpoint which provides split-adjusted
      closes but does not provide vendor `adjClose` (dividend-adjusted close). To construct a
      total-return proxy (TSR) suitable for publication, we ingest dividend events separately
      and combine them with split-adjusted closes in the return calculator.
    """

    __tablename__ = "fmp_dividends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)  # ex-dividend date

    dividend: Mapped[Optional[float]] = mapped_column(Float)  # raw dividend per share (vendor)
    adj_dividend: Mapped[Optional[float]] = mapped_column(Float)  # split-adjusted dividend per share (preferred)

    declaration_date: Mapped[Optional[date_type]] = mapped_column(Date)
    record_date: Mapped[Optional[date_type]] = mapped_column(Date)
    payment_date: Mapped[Optional[date_type]] = mapped_column(Date)

    frequency: Mapped[Optional[str]] = mapped_column(String(20))
    yield_pct: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_fmp_dividend"),
    )


class FMPAnnualReturn(Base):
    """FMP computed annual returns."""
    __tablename__ = "fmp_annual_returns"
    
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    annual_return: Mapped[Optional[float]] = mapped_column(Float)
    volatility: Mapped[Optional[float]] = mapped_column(Float)
    start_price: Mapped[Optional[float]] = mapped_column(Float)
    end_price: Mapped[Optional[float]] = mapped_column(Float)


# ============================================================================
# Research Analysis Models (500-Company Cohort with Rolling Windows)
# ============================================================================

class ResearchCohort(Base):
    """500-company research cohort with window classification."""
    __tablename__ = "research_cohort"
    
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Data coverage
    years_with_data: Mapped[int] = mapped_column(Integer, default=0)
    years_with_rd: Mapped[int] = mapped_column(Integer, default=0)
    first_year: Mapped[Optional[int]] = mapped_column(Integer)
    last_year: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Window eligibility flags
    has_5yr_window: Mapped[bool] = mapped_column(Boolean, default=False)
    has_10yr_window: Mapped[bool] = mapped_column(Boolean, default=False)
    has_20yr_window: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # R&D metrics
    avg_rd_intensity: Mapped[Optional[float]] = mapped_column(Float)
    total_rd_spend: Mapped[Optional[float]] = mapped_column(Float)
    rd_profile: Mapped[Optional[str]] = mapped_column(String(20))  # High/Medium/Low
    
    # Data quality
    data_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    has_price_data: Mapped[bool] = mapped_column(Boolean, default=False)
    has_return_data: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RollingWindowResult(Base):
    """
    Pre-computed rolling window analysis results.
    
    PUBLICATION FIX (Dec 2025):
    - Added return_convention field to distinguish calendar vs July-June results
    - Added computation_run_id for versioning/reproducibility
    - Updated unique constraint to include return_convention
    
    This allows storing multiple result sets (e.g., one with calendar returns,
    one with July-June returns) without overwriting.
    """
    __tablename__ = "rolling_window_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # '5yr', '10yr', '20yr'
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quintile: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 (1=Low R&D, 5=High R&D)
    
    # Computation metadata (PUBLICATION FIX Dec 2025)
    return_convention: Mapped[str] = mapped_column(
        String(20), nullable=False, default="july_june", index=True
    )  # 'july_june' (Fama-French) or 'calendar' (legacy)
    computation_run_id: Mapped[Optional[str]] = mapped_column(String(36))  # UUID for reproducibility
    data_tier: Mapped[str] = mapped_column(
        String(10), nullable=False, default="tier1"
    )  # 'tier1' (FMP) or 'tier2' (CRSP/Compustat)
    
    # Portfolio statistics
    n_companies: Mapped[int] = mapped_column(Integer, default=0)
    avg_rd_intensity: Mapped[Optional[float]] = mapped_column(Float)
    median_rd_intensity: Mapped[Optional[float]] = mapped_column(Float)
    
    # Return statistics
    avg_return: Mapped[Optional[float]] = mapped_column(Float)
    median_return: Mapped[Optional[float]] = mapped_column(Float)
    total_return: Mapped[Optional[float]] = mapped_column(Float)  # Cumulative
    annualized_return: Mapped[Optional[float]] = mapped_column(Float)
    
    # Risk metrics
    volatility: Mapped[Optional[float]] = mapped_column(Float)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    
    # Additional metrics
    avg_market_cap: Mapped[Optional[float]] = mapped_column(Float)
    sector_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        # Updated constraint to include return_convention for versioning
        UniqueConstraint(
            "window_type", "start_year", "end_year", "quintile", "return_convention",
            name="uq_window_quintile_convention"
        ),
        Index("ix_rolling_window_type", "window_type"),
        Index("ix_rolling_window_convention", "return_convention"),
    )


class AnovaResult(Base):
    """
    ANOVA test results for quintile comparisons.
    
    PUBLICATION FIX (Dec 2025):
    - Added return_convention and data_tier fields for versioning
    """
    __tablename__ = "anova_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2000-2005"
    test_type: Mapped[str] = mapped_column(String(50), default="one_way_anova")
    
    # Computation metadata (PUBLICATION FIX Dec 2025)
    return_convention: Mapped[str] = mapped_column(
        String(20), nullable=False, default="july_june"
    )  # 'july_june' or 'calendar'
    data_tier: Mapped[str] = mapped_column(
        String(10), nullable=False, default="tier1"
    )  # 'tier1' (FMP) or 'tier2' (CRSP)
    computation_run_id: Mapped[Optional[str]] = mapped_column(String(36))  # UUID
    
    # ANOVA statistics
    f_statistic: Mapped[Optional[float]] = mapped_column(Float)
    p_value: Mapped[Optional[float]] = mapped_column(Float)
    eta_squared: Mapped[Optional[float]] = mapped_column(Float)  # Effect size
    omega_squared: Mapped[Optional[float]] = mapped_column(Float)  # Adjusted effect size
    
    # Significance
    significant_005: Mapped[bool] = mapped_column(Boolean, default=False)  # p < 0.05
    significant_001: Mapped[bool] = mapped_column(Boolean, default=False)  # p < 0.01
    
    # Group statistics
    group_means: Mapped[Optional[dict]] = mapped_column(JSON)  # {quintile: mean}
    group_stds: Mapped[Optional[dict]] = mapped_column(JSON)   # {quintile: std}
    group_ns: Mapped[Optional[dict]] = mapped_column(JSON)     # {quintile: n}
    
    # Post-hoc results
    tukey_results: Mapped[Optional[dict]] = mapped_column(JSON)  # Pairwise comparisons
    
    # T-test: High vs Low R&D
    high_low_t_stat: Mapped[Optional[float]] = mapped_column(Float)
    high_low_p_value: Mapped[Optional[float]] = mapped_column(Float)
    high_low_diff: Mapped[Optional[float]] = mapped_column(Float)  # Q5 - Q1 difference
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint(
            "window_type", "period", "test_type", "return_convention",
            name="uq_anova_period_convention"
        ),
    )


class FactorPremium(Base):
    """
    R&D factor premium time series.
    
    PUBLICATION FIX (Dec 2025):
    - Added return_convention and data_tier fields for versioning
    - Updated unique constraint to include return_convention
    """
    __tablename__ = "factor_premiums"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Computation metadata (PUBLICATION FIX Dec 2025)
    return_convention: Mapped[str] = mapped_column(
        String(20), nullable=False, default="july_june"
    )  # 'july_june' or 'calendar'
    data_tier: Mapped[str] = mapped_column(
        String(10), nullable=False, default="tier1"
    )  # 'tier1' (FMP) or 'tier2' (CRSP)
    computation_run_id: Mapped[Optional[str]] = mapped_column(String(36))  # UUID
    
    # R&D Factor Premium (High R&D - Low R&D returns)
    rd_premium: Mapped[Optional[float]] = mapped_column(Float)
    rd_premium_t_stat: Mapped[Optional[float]] = mapped_column(Float)
    
    # Market factors for comparison
    market_return: Mapped[Optional[float]] = mapped_column(Float)
    smb_factor: Mapped[Optional[float]] = mapped_column(Float)  # Size factor
    hml_factor: Mapped[Optional[float]] = mapped_column(Float)  # Value factor
    
    # Quintile returns for the year
    q1_return: Mapped[Optional[float]] = mapped_column(Float)
    q2_return: Mapped[Optional[float]] = mapped_column(Float)
    q3_return: Mapped[Optional[float]] = mapped_column(Float)
    q4_return: Mapped[Optional[float]] = mapped_column(Float)
    q5_return: Mapped[Optional[float]] = mapped_column(Float)
    
    # Number of companies per quintile
    q1_n: Mapped[Optional[int]] = mapped_column(Integer)
    q2_n: Mapped[Optional[int]] = mapped_column(Integer)
    q3_n: Mapped[Optional[int]] = mapped_column(Integer)
    q4_n: Mapped[Optional[int]] = mapped_column(Integer)
    q5_n: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("year", "return_convention", name="uq_factor_year_convention"),
    )


class ComputationRun(Base):
    """
    Tracks computation runs for reproducibility and audit.
    
    Each run of the research pipeline (rolling windows, factor premiums, etc.)
    creates a ComputationRun record with metadata about what was computed
    and under what settings.
    
    TIER-2 UPGRADE (Dec 2025):
    - Enables tracking of Tier-1 vs Tier-2 computations
    - Stores git commit for exact code versioning
    - Links to all results computed in this run via computation_run_id
    """
    __tablename__ = "computation_runs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    
    # What was computed
    computation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'rolling_windows', 'factor_premiums', 'anova', 'full_pipeline'
    
    # Settings used
    return_convention: Mapped[str] = mapped_column(String(20), nullable=False)  # 'july_june' or 'calendar'
    data_tier: Mapped[str] = mapped_column(String(10), nullable=False)  # 'tier1' or 'tier2'
    window_types: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., '5yr,10yr,20yr'
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Code versioning
    git_commit: Mapped[Optional[str]] = mapped_column(String(40))  # SHA
    git_branch: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Execution metadata
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")  # 'running', 'completed', 'failed'
    
    # Results summary
    records_created: Mapped[Optional[int]] = mapped_column(Integer)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (
        Index("ix_computation_run_type", "computation_type"),
        Index("ix_computation_run_tier", "data_tier"),
    )


class PublicationSnapshot(Base):
    """
    Frozen, publication-ready snapshot of research outputs.

    This is intentionally **separate** from the rolling/anova/factor tables to:
      - Pin a stable manuscript dataset for submission
      - Avoid relying on computation_run_id consistency across multiple tables
      - Keep the website paper pages resilient even if some live endpoints fail
    """
    __tablename__ = "publication_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Provenance / reproducibility
    return_convention: Mapped[str] = mapped_column(String(20), nullable=False, default="july_june")
    data_tier: Mapped[str] = mapped_column(String(10), nullable=False, default="tier1")
    built_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    git_commit: Mapped[Optional[str]] = mapped_column(String(40))
    git_branch: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Frozen payload
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)



# ==============================================================================
# ETF Selection and Market Forecast Tables
# ==============================================================================

class ETFSelectionHistory(Base):
    """
    Historical ETF selections for transparency and backtesting.
    
    Records every selection decision with complete scoring breakdown,
    enabling users to see exactly why companies were/weren't selected.
    """
    __tablename__ = "etf_selection_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Selection metadata
    selection_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    as_of_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    universe: Mapped[str] = mapped_column(String(20), nullable=False, default="sp500")  # sp500, russell1000, etc.
    n_holdings: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    selection_method: Mapped[str] = mapped_column(String(50), nullable=False, default="rd_alpha")
    
    # Company info
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Scoring components
    rd_intensity: Mapped[Optional[float]] = mapped_column(Float)
    rd_intensity_capped: Mapped[Optional[float]] = mapped_column(Float)
    sector_adjustment: Mapped[Optional[float]] = mapped_column(Float)
    momentum_factor: Mapped[Optional[float]] = mapped_column(Float)
    quality_score: Mapped[Optional[float]] = mapped_column(Float)
    volatility: Mapped[Optional[float]] = mapped_column(Float)
    
    # Final outputs
    raw_score: Mapped[Optional[float]] = mapped_column(Float)
    final_score: Mapped[Optional[float]] = mapped_column(Float, index=True)
    weight: Mapped[Optional[float]] = mapped_column(Float)
    selection_rank: Mapped[Optional[int]] = mapped_column(Integer)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Additional data
    years_of_data: Mapped[Optional[int]] = mapped_column(Integer)
    latest_revenue: Mapped[Optional[float]] = mapped_column(Float)
    latest_rd_expense: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_etf_selection_date_symbol", "selection_date", "symbol"),
        Index("ix_etf_selection_year_universe", "as_of_year", "universe"),
    )


class MarketForecast(Base):
    """
    S&P 500 consensus forecasts from major investment banks.
    
    Stores forecasts with full attribution for transparency.
    Updated periodically (quarterly) from bank research.
    """
    __tablename__ = "market_forecasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Forecast metadata
    forecast_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    forecast_type: Mapped[str] = mapped_column(String(20), nullable=False, default="sp500")  # sp500, nasdaq, etc.
    
    # Forecast values (level)
    forecast_low: Mapped[Optional[float]] = mapped_column(Float)
    forecast_mid: Mapped[Optional[float]] = mapped_column(Float)
    forecast_high: Mapped[Optional[float]] = mapped_column(Float)
    
    # Implied returns
    return_low: Mapped[Optional[float]] = mapped_column(Float)
    return_mid: Mapped[Optional[float]] = mapped_column(Float)
    return_high: Mapped[Optional[float]] = mapped_column(Float)
    
    # Attribution
    source: Mapped[Optional[str]] = mapped_column(String(255))
    methodology: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Actual (filled in after year ends)
    actual_level: Mapped[Optional[float]] = mapped_column(Float)
    actual_return: Mapped[Optional[float]] = mapped_column(Float)
    forecast_error: Mapped[Optional[float]] = mapped_column(Float)  # Actual - Mid forecast
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("forecast_date", "target_year", "forecast_type", name="uq_forecast_date_year_type"),
        Index("ix_forecast_target_year", "target_year"),
    )


# ==============================================================================
# Research Metrics Tables (First-Principles Integration)
# ==============================================================================

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


# ==============================================================================
# TIER 2 UPGRADE PATH: CRSP/Compustat Stub Tables
# ==============================================================================
# These tables are placeholders for a future upgrade to CRSP/Compustat data,
# which is the gold standard for top-tier academic publications (JF, JFE, RFS).
# 
# Current implementation (Tier 1) uses FMP API data.
# Tier 2 would require WRDS institutional access.
# ==============================================================================

class CRSPMonthlyStock(Base):
    """
    CRSP Monthly Stock Data (Tier 2 - STUB).
    
    This is a placeholder for CRSP monthly stock file data.
    Requires WRDS institutional access to populate.
    
    Key fields from CRSP:
    - PERMNO: Permanent security identifier (survives ticker changes)
    - RET: Monthly return including dividends
    - DLRET: Delisting return (critical for survivorship)
    - PRC: Price (negative = bid/ask average)
    - SHROUT: Shares outstanding
    - CFACPR: Cumulative factor for price adjustment
    """
    __tablename__ = "crsp_monthly_stock"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    
    # Returns
    ret: Mapped[Optional[float]] = mapped_column(Float)  # Monthly return
    dlret: Mapped[Optional[float]] = mapped_column(Float)  # Delisting return
    
    # Price and shares
    prc: Mapped[Optional[float]] = mapped_column(Float)  # Price (neg = bid/ask avg)
    shrout: Mapped[Optional[int]] = mapped_column(Integer)  # Shares outstanding (000s)
    
    # Adjustment factors
    cfacpr: Mapped[Optional[float]] = mapped_column(Float)  # Cumulative price adjustment
    cfacshr: Mapped[Optional[float]] = mapped_column(Float)  # Cumulative share adjustment
    
    # Security info
    ticker: Mapped[Optional[str]] = mapped_column(String(20))
    exchcd: Mapped[Optional[int]] = mapped_column(Integer)  # Exchange code
    shrcd: Mapped[Optional[int]] = mapped_column(Integer)  # Share code
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("permno", "date", name="uq_crsp_permno_date"),
        Index("ix_crsp_date", "date"),
    )


class CRSPCompustatLink(Base):
    """
    CRSP-Compustat Link Table (Tier 2 - STUB).
    
    Maps between CRSP PERMNO and Compustat GVKEY.
    Essential for merging stock returns with accounting data.
    
    Source: WRDS CCM (CRSP-Compustat Merged) database.
    """
    __tablename__ = "crsp_compustat_link"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gvkey: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Link validity period
    linkdt: Mapped[Optional[date_type]] = mapped_column(Date)  # Link start date
    linkenddt: Mapped[Optional[date_type]] = mapped_column(Date)  # Link end date
    
    # Link type and priority
    linktype: Mapped[Optional[str]] = mapped_column(String(5))  # LU, LC, LS, etc.
    linkprim: Mapped[Optional[str]] = mapped_column(String(1))  # P, C, J
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_ccm_gvkey", "gvkey"),
    )


class CompustatAnnual(Base):
    """
    Compustat Annual Fundamentals (Tier 2 - STUB).
    
    Annual accounting data from Compustat.
    Contains R&D expense (XRD), revenue (REVT), and other fundamentals.
    
    Source: WRDS Compustat North America Fundamentals Annual.
    """
    __tablename__ = "compustat_annual"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gvkey: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    datadate: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    fyear: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Key fundamentals for R&D research
    xrd: Mapped[Optional[float]] = mapped_column(Float)  # R&D Expense
    revt: Mapped[Optional[float]] = mapped_column(Float)  # Revenue
    at: Mapped[Optional[float]] = mapped_column(Float)  # Total Assets
    ceq: Mapped[Optional[float]] = mapped_column(Float)  # Common Equity
    csho: Mapped[Optional[float]] = mapped_column(Float)  # Shares Outstanding
    prcc_f: Mapped[Optional[float]] = mapped_column(Float)  # Fiscal year-end price
    
    # Additional accounting items
    ni: Mapped[Optional[float]] = mapped_column(Float)  # Net Income
    oibdp: Mapped[Optional[float]] = mapped_column(Float)  # Operating Income
    sale: Mapped[Optional[float]] = mapped_column(Float)  # Sales
    
    # Industry classification
    sic: Mapped[Optional[str]] = mapped_column(String(4))  # SIC code
    naics: Mapped[Optional[str]] = mapped_column(String(6))  # NAICS code
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("gvkey", "datadate", name="uq_compustat_gvkey_date"),
        Index("ix_compustat_fyear", "fyear"),
    )


class CRSPS500Constituent(Base):
    """
    CRSP S&P 500 Historical Constituents (Tier 2 - STUB).
    
    Official point-in-time S&P 500 membership from CRSP.
    This is the gold standard for survivorship-bias-free research.
    
    Source: CRSP S&P 500 Universe.
    """
    __tablename__ = "crsp_sp500_constituents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Membership dates
    start_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date_type]] = mapped_column(Date)  # NULL = still member
    
    # Security info at time of membership
    ticker: Mapped[Optional[str]] = mapped_column(String(20))
    comnam: Mapped[Optional[str]] = mapped_column(String(255))  # Company name
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_crsp_sp500_dates", "start_date", "end_date"),
    )


