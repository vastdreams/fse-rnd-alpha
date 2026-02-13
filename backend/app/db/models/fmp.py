"""
PATH: backend/app/db/models/fmp.py
PURPOSE: Financial Modeling Prep (FMP) API data models.
WHY: Separates vendor-specific data tables from internal research models.
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
