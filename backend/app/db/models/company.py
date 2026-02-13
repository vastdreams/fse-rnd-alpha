"""
PATH: backend/app/db/models/company.py
PURPOSE: Company-domain ORM models (Company, CompanyYearCore, AnnualReport).
WHY: Core entity tables that link companies to their annual filings and data.
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
