"""
PATH: backend/app/db/models/tier2.py
PURPOSE: CRSP/Compustat Tier-2 stub ORM models for future WRDS upgrade.
WHY: Placeholders for gold-standard academic data (CRSP monthly stock, Compustat annual, linkage, S&P 500).
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
