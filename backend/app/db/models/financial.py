"""
PATH: backend/app/db/models/financial.py
PURPOSE: Financial-domain ORM models (FinancialsCore, FinancialsRatios, TextFactorRD, Price).
WHY: Core financial data tables derived from XBRL, computed ratios, text analysis, and prices.
DEPENDENCIES:
  - base: shared SQLAlchemy imports & Base
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.db.models.base import (
    Base, datetime, date_type, Optional, List,
    Integer, String, Float, Boolean, Date, DateTime, Text, JSON,
    ForeignKey, Index, UniqueConstraint,
    relationship, Mapped, mapped_column,
)

if TYPE_CHECKING:
    from app.db.models.company import CompanyYearCore


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
