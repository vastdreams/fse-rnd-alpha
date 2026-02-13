"""
PATH: backend/app/db/models/etf.py
PURPOSE: ETF selection and market forecast ORM models.
WHY: Separates ETF portfolio construction and market outlook tables from research models.
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
