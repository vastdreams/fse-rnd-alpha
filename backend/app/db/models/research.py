"""
PATH: backend/app/db/models/research.py
PURPOSE: Research analysis ORM models (cohort, rolling windows, ANOVA, factor premiums, computation runs, snapshots).
WHY: Core tables for the 500-company R&D research pipeline with rolling-window analysis.
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
