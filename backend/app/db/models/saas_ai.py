"""
PATH: backend/app/db/models/saas_ai.py
PURPOSE: Raw cache tables for the SaaS AI Repricing study (own-the-data layer).
WHY:
  - Alpha Vantage (transcripts/fundamentals) and Sharadar (point-in-time fundamentals,
    prices, reference data) are paid sources. We persist every pull permanently so the
    study is fully reproducible and we never re-pay for the same data.
  - Each table keeps the full vendor payload (JSONB) plus extracted key columns so the
    research layer can query without re-parsing raw JSON.
DEPENDENCIES:
  - base: shared SQLAlchemy imports & Base
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB

from app.db.models.base import (
    Base, datetime, date_type, Optional,
    Integer, String, Float, Date, DateTime,
    UniqueConstraint, Mapped, mapped_column,
)


class AVTranscriptRaw(Base):
    """Alpha Vantage EARNINGS_CALL_TRANSCRIPT payload, one row per (symbol, quarter)."""
    __tablename__ = "av_transcripts_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(8), nullable=False)  # e.g. "2025Q1"
    source: Mapped[str] = mapped_column(String(30), default="alphavantage")
    n_segments: Mapped[Optional[int]] = mapped_column(Integer)
    transcript: Mapped[Optional[dict]] = mapped_column(JSONB)  # full list of speaker segments
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "quarter", "source", name="uq_av_transcript"),
    )


class AVFundamentalsRaw(Base):
    """Alpha Vantage fundamentals payload, one row per (symbol, statement_type).

    statement_type in {OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW, EARNINGS,
    LISTING_STATUS}. LISTING_STATUS is stored once under symbol="__ALL__".
    """
    __tablename__ = "av_fundamentals_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    statement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "statement_type", name="uq_av_fundamentals"),
    )


class SharadarSF1(Base):
    """Sharadar SF1 fundamentals. datekey is the point-in-time filing date (no look-ahead)."""
    __tablename__ = "sharadar_sf1"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(8), nullable=False)  # ARQ/ARY/MRQ/MRY/ART/MRT
    datekey: Mapped[date_type] = mapped_column(Date, nullable=False)   # filing date (PIT anchor)
    calendardate: Mapped[Optional[date_type]] = mapped_column(Date, index=True)
    reportperiod: Mapped[Optional[date_type]] = mapped_column(Date)
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    rnd: Mapped[Optional[float]] = mapped_column(Float)
    gp: Mapped[Optional[float]] = mapped_column(Float)
    netinc: Mapped[Optional[float]] = mapped_column(Float)
    fcf: Mapped[Optional[float]] = mapped_column(Float)
    ev: Mapped[Optional[float]] = mapped_column(Float)
    marketcap: Mapped[Optional[float]] = mapped_column(Float)
    row: Mapped[Optional[dict]] = mapped_column(JSONB)  # full SF1 row
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "dimension", "datekey", name="uq_sharadar_sf1"),
    )


class SharadarSEP(Base):
    """Sharadar SEP end-of-day equity prices (adjusted + unadjusted)."""
    __tablename__ = "sharadar_sep"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float)
    high: Mapped[Optional[float]] = mapped_column(Float)
    low: Mapped[Optional[float]] = mapped_column(Float)
    close: Mapped[Optional[float]] = mapped_column(Float)
    closeadj: Mapped[Optional[float]] = mapped_column(Float)
    closeunadj: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_sharadar_sep"),
    )


class SharadarTickers(Base):
    """Sharadar TICKERS reference data (one row per table_name/permaticker/ticker)."""
    __tablename__ = "sharadar_tickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(10), nullable=False)  # SF1/SEP/SFP
    permaticker: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    exchange: Mapped[Optional[str]] = mapped_column(String(30))
    isdelisted: Mapped[Optional[str]] = mapped_column(String(5))
    category: Mapped[Optional[str]] = mapped_column(String(60))
    sector: Mapped[Optional[str]] = mapped_column(String(60))
    industry: Mapped[Optional[str]] = mapped_column(String(120))
    siccode: Mapped[Optional[str]] = mapped_column(String(10))
    scalemarketcap: Mapped[Optional[str]] = mapped_column(String(40))
    firstpricedate: Mapped[Optional[date_type]] = mapped_column(Date)
    lastpricedate: Mapped[Optional[date_type]] = mapped_column(Date)
    row: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("table_name", "permaticker", "ticker", name="uq_sharadar_tickers"),
    )
