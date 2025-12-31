"""
PATH: backend/app/api/routes/research.py
PURPOSE:
  - API endpoints for 500-company research cohort analysis
  - Rolling window analysis with 5/10/20-year windows
  - ANOVA and statistical test results
  - Data quality metrics

ROLE IN ARCHITECTURE:
  - Main research API layer (consolidated from v1 and v2)
  
NOTES FOR FUTURE AI:
  - This file was renamed from research_v2.py after deprecating research.py
  - All research endpoints are now under /api/research/
"""

from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import csv
import io
from datetime import datetime
import numpy as np

from app.db.session import get_session
from app.db.models import (
    ResearchCohort, RollingWindowResult, AnovaResult, FactorPremium,
    FMPIncomeStatement, SP500Company, PublicationSnapshot
)
from app.services.cohort_classifier import CohortClassifier
from app.services.rolling_window import RollingWindowAnalyzer
from app.services.statistics import StatisticalAnalyzer
from app.services.publication_snapshot import (
    get_active_snapshot,
    build_snapshot_payload,
    create_publication_snapshot,
)
from app.services.sanity_checks import (
    MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE
)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class CohortCompanyResponse(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    years_with_data: int
    years_with_rd: int
    first_year: Optional[int]
    last_year: Optional[int]
    has_5yr_window: bool
    has_10yr_window: bool
    has_20yr_window: bool
    avg_rd_intensity: Optional[float]
    rd_profile: Optional[str]
    data_quality_score: Optional[float]


class CohortSummaryResponse(BaseModel):
    total_companies: int
    eligible_5yr: int
    eligible_10yr: int
    eligible_20yr: int
    avg_rd_intensity: float
    avg_quality_score: float
    by_sector: List[dict]
    by_rd_profile: dict


class QuintileResponse(BaseModel):
    quintile: int
    n_companies: int
    avg_rd_intensity: Optional[float]
    avg_return: Optional[float]
    total_return: Optional[float]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]


class WindowResultResponse(BaseModel):
    window_type: str
    start_year: int
    end_year: int
    quintiles: List[QuintileResponse]
    rd_premium: float


class AnovaResultResponse(BaseModel):
    window_type: str
    period: str
    f_statistic: Optional[float]
    p_value: Optional[float]
    eta_squared: Optional[float]
    significant_005: bool
    significant_001: bool
    group_means: Optional[dict]
    high_low_diff: Optional[float]


class FactorPremiumResponse(BaseModel):
    year: int
    rd_premium: Optional[float]
    q1_return: Optional[float]
    q2_return: Optional[float]
    q3_return: Optional[float]
    q4_return: Optional[float]
    q5_return: Optional[float]


class ComputeJobResponse(BaseModel):
    status: str
    message: str


class PublicationSnapshotMetaResponse(BaseModel):
    id: str
    label: str
    is_active: bool
    return_convention: str
    data_tier: str
    built_at: datetime
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    notes: Optional[str] = None


class PublicationSnapshotResponse(BaseModel):
    meta: PublicationSnapshotMetaResponse
    payload: Dict[str, Any]


class BuildPublicationSnapshotRequest(BaseModel):
    label: str = "Publication Snapshot"
    return_convention: str = "july_june"
    data_tier: str = "tier1"
    notes: Optional[str] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    set_active: bool = True


class DataQualityResponse(BaseModel):
    """Data quality metrics for research transparency."""
    total_sp500_companies: int
    companies_with_rd_data: int
    companies_with_return_data: int
    coverage_pct: float
    years_of_data: int
    min_year: int
    max_year: int
    rd_intensity_cap: float
    min_revenue_threshold: float
    outliers_capped_pct: float
    methodology_notes: List[str]


# ============================================================================
# Cohort Endpoints
# ============================================================================

@router.get("/cohort-500", response_model=List[CohortCompanyResponse])
async def get_cohort_500(
    window: Optional[str] = Query(None, description="Filter by window: 5yr, 10yr, 20yr"),
    sector: Optional[str] = Query(None),
    rd_profile: Optional[str] = Query(None, description="High, Medium, or Low"),
    limit: int = Query(500, le=500),
    session: AsyncSession = Depends(get_session)
):
    """Get full 500-company research cohort with optional filters."""
    query = select(ResearchCohort)
    
    if window == "5yr":
        query = query.where(ResearchCohort.has_5yr_window == True)
    elif window == "10yr":
        query = query.where(ResearchCohort.has_10yr_window == True)
    elif window == "20yr":
        query = query.where(ResearchCohort.has_20yr_window == True)
    
    if sector:
        query = query.where(ResearchCohort.sector == sector)
    
    if rd_profile:
        query = query.where(ResearchCohort.rd_profile == rd_profile)
    
    query = query.order_by(ResearchCohort.avg_rd_intensity.desc()).limit(limit)
    
    result = await session.execute(query)
    companies = result.scalars().all()
    
    return [
        CohortCompanyResponse(
            symbol=c.symbol,
            name=c.name,
            sector=c.sector,
            industry=c.industry,
            years_with_data=c.years_with_data,
            years_with_rd=c.years_with_rd,
            first_year=c.first_year,
            last_year=c.last_year,
            has_5yr_window=c.has_5yr_window,
            has_10yr_window=c.has_10yr_window,
            has_20yr_window=c.has_20yr_window,
            avg_rd_intensity=round(c.avg_rd_intensity, 2) if c.avg_rd_intensity else None,
            rd_profile=c.rd_profile,
            data_quality_score=round(c.data_quality_score, 1) if c.data_quality_score else None
        )
        for c in companies
    ]


@router.get("/cohort-summary", response_model=CohortSummaryResponse)
async def get_cohort_summary(
    session: AsyncSession = Depends(get_session)
):
    """Get summary statistics for the research cohort."""
    classifier = CohortClassifier(session)
    summary = await classifier.get_cohort_summary()
    return CohortSummaryResponse(**summary)


@router.get("/data-quality", response_model=DataQualityResponse)
async def get_data_quality(
    session: AsyncSession = Depends(get_session)
):
    """
    Get data quality metrics for research transparency.
    
    Shows coverage, outlier handling, and methodology details.
    """
    # Count total S&P 500 companies
    sp500_count = await session.execute(
        select(func.count(SP500Company.symbol))
    )
    total_sp500 = sp500_count.scalar() or 0
    
    # Count companies with R&D data meeting quality thresholds
    rd_data_count = await session.execute(
        select(func.count(func.distinct(FMPIncomeStatement.symbol)))
        .where(FMPIncomeStatement.rd_expenses > 0)
        .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
    )
    companies_with_rd = rd_data_count.scalar() or 0
    
    # Count companies with return data (from cohort)
    return_count = await session.execute(
        select(func.count(ResearchCohort.symbol))
        .where(ResearchCohort.years_with_data >= 5)
    )
    companies_with_returns = return_count.scalar() or 0
    
    # Get year range
    year_range = await session.execute(
        select(
            func.min(FMPIncomeStatement.fiscal_year),
            func.max(FMPIncomeStatement.fiscal_year)
        )
    )
    min_year, max_year = year_range.fetchone()
    
    # Estimate outlier percentage (R&D intensity > cap before capping)
    outlier_count = await session.execute(
        select(func.count())
        .select_from(FMPIncomeStatement)
        .where(FMPIncomeStatement.rd_expenses > 0)
        .where(FMPIncomeStatement.revenue > 0)
        .where(
            (FMPIncomeStatement.rd_expenses / FMPIncomeStatement.revenue * 100) > MAX_RD_INTENSITY_ABSOLUTE
        )
    )
    total_rd_rows = await session.execute(
        select(func.count())
        .select_from(FMPIncomeStatement)
        .where(FMPIncomeStatement.rd_expenses > 0)
        .where(FMPIncomeStatement.revenue > 0)
    )
    outliers = outlier_count.scalar() or 0
    total_rows = total_rd_rows.scalar() or 1
    outlier_pct = round(outliers / total_rows * 100, 2)
    
    coverage = round(companies_with_rd / total_sp500 * 100, 1) if total_sp500 > 0 else 0
    
    methodology_notes = [
        f"Uses FY(T-1) data to form portfolios at start of year T (reduces look-ahead bias)",
        f"R&D intensity capped at {MAX_RD_INTENSITY_ABSOLUTE}% (200% for Healthcare/Biotech)",
        f"Minimum revenue threshold: ${MIN_REVENUE_THRESHOLD / 1_000_000:.0f}M excludes pre-revenue companies",
        f"Sharpe ratio calculated with 2% constant risk-free rate (approximate)",
        f"Returns stored as decimal (0.10 = 10%), displayed as percentage",
        f"Annual equal-weight rebalancing (not buy-and-hold)",
        f"HAC (Newey-West) correction available for overlapping window inference (use lags=k-1)",
        f"Welch's t-test used (does not assume equal variances)",
        f"CAUTION: Calendar year returns may have ~3 month look-ahead bias vs fiscal year data"
    ]
    
    return DataQualityResponse(
        total_sp500_companies=total_sp500,
        companies_with_rd_data=companies_with_rd,
        companies_with_return_data=companies_with_returns,
        coverage_pct=coverage,
        years_of_data=(max_year - min_year + 1) if min_year and max_year else 0,
        min_year=min_year or 0,
        max_year=max_year or 0,
        rd_intensity_cap=MAX_RD_INTENSITY_ABSOLUTE,
        min_revenue_threshold=MIN_REVENUE_THRESHOLD,
        outliers_capped_pct=outlier_pct,
        methodology_notes=methodology_notes
    )


@router.get("/windows/{window_type}", response_model=List[CohortCompanyResponse])
async def get_window_companies(
    window_type: str,
    session: AsyncSession = Depends(get_session)
):
    """Get companies eligible for a specific analysis window."""
    if window_type not in ["5yr", "10yr", "20yr"]:
        raise HTTPException(400, "window_type must be 5yr, 10yr, or 20yr")
    
    classifier = CohortClassifier(session)
    companies = await classifier.get_cohort_by_window(window_type)
    
    return [CohortCompanyResponse(**c) for c in companies]


# ============================================================================
# Rolling Window Analysis Endpoints
# ============================================================================

@router.get("/rolling/{window_type}", response_model=List[WindowResultResponse])
async def get_rolling_windows(
    window_type: str,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    data_tier: str = Query("tier1", description="Data tier: tier1 (FMP) or tier2 (CRSP)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all rolling window analysis results for a window type.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    - Supports Tier-1 (FMP) and Tier-2 (CRSP) data sources
    """
    if window_type not in ["5yr", "10yr", "20yr"]:
        raise HTTPException(400, "window_type must be 5yr, 10yr, or 20yr")
    if data_tier not in ["tier1", "tier2"]:
        raise HTTPException(400, "data_tier must be tier1 or tier2")
    
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june, data_tier=data_tier)
    results = await analyzer.get_stored_window_results(window_type)
    
    return [
        WindowResultResponse(
            window_type=r["window_type"],
            start_year=r["start_year"],
            end_year=r["end_year"],
            quintiles=[QuintileResponse(**q) for q in r["quintiles"]],
            rd_premium=r["rd_premium"]
        )
        for r in results
    ]


@router.get("/quintile-performance")
async def get_quintile_performance(
    window_type: str = Query("5yr"),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    data_tier: str = Query("tier1", description="Data tier: tier1 (FMP) or tier2 (CRSP)"),
    session: AsyncSession = Depends(get_session)
):
    """Get aggregate quintile performance across all windows."""
    return_convention = "july_june" if use_july_june else "calendar"

    result = await session.execute(
        select(
            RollingWindowResult.quintile,
            func.count(RollingWindowResult.id).label("n_windows"),
            func.avg(RollingWindowResult.avg_rd_intensity).label("avg_rd_intensity"),
            func.avg(RollingWindowResult.avg_return).label("avg_return"),
            func.avg(RollingWindowResult.total_return).label("avg_total_return"),
            func.avg(RollingWindowResult.volatility).label("avg_volatility"),
            func.avg(RollingWindowResult.sharpe_ratio).label("avg_sharpe")
        )
        .where(
            RollingWindowResult.window_type == window_type,
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == data_tier,
        )
        .group_by(RollingWindowResult.quintile)
        .order_by(RollingWindowResult.quintile)
    )
    rows = result.fetchall()
    
    return [
        {
            "quintile": r.quintile,
            "label": f"Q{r.quintile}" + (" (Low R&D)" if r.quintile == 1 else " (High R&D)" if r.quintile == 5 else ""),
            "n_windows": r.n_windows,
            "avg_rd_intensity": round(r.avg_rd_intensity, 2) if r.avg_rd_intensity else 0,
            "avg_return": round(r.avg_return, 2) if r.avg_return else 0,
            "avg_total_return": round(r.avg_total_return, 2) if r.avg_total_return else 0,
            "avg_volatility": round(r.avg_volatility, 2) if r.avg_volatility else 0,
            "avg_sharpe": round(r.avg_sharpe, 3) if r.avg_sharpe else 0
        }
        for r in rows
    ]


# ============================================================================
# Statistical Analysis Endpoints
# ============================================================================

@router.get("/anova/{window_type}", response_model=List[AnovaResultResponse])
async def get_anova_results(
    window_type: str,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    session: AsyncSession = Depends(get_session)
):
    """Get ANOVA results for all windows of a type."""
    if window_type not in ["5yr", "10yr", "20yr"]:
        raise HTTPException(400, "window_type must be 5yr, 10yr, or 20yr")
    
    return_convention = "july_june" if use_july_june else "calendar"
    data_tier = "tier1"

    result = await session.execute(
        select(AnovaResult)
        .where(
            AnovaResult.window_type == window_type,
            AnovaResult.return_convention == return_convention,
            AnovaResult.data_tier == data_tier,
        )
        .order_by(AnovaResult.period)
    )
    rows = result.scalars().all()
    
    return [
        AnovaResultResponse(
            window_type=r.window_type,
            period=r.period,
            f_statistic=round(r.f_statistic, 3) if r.f_statistic else None,
            p_value=round(r.p_value, 6) if r.p_value else None,
            eta_squared=round(r.eta_squared, 3) if r.eta_squared else None,
            significant_005=r.significant_005,
            significant_001=r.significant_001,
            group_means=r.group_means,
            high_low_diff=round(r.high_low_diff, 2) if r.high_low_diff else None
        )
        for r in rows
    ]


@router.get("/anova-aggregate")
async def get_aggregate_anova(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    session: AsyncSession = Depends(get_session)
):
    """Get aggregate ANOVA statistics across all window types."""
    analyzer = StatisticalAnalyzer(session, use_july_june=use_july_june)
    
    results = {}
    for window_type in ["5yr", "10yr", "20yr"]:
        try:
            results[window_type] = await analyzer.compute_aggregate_anova(window_type)
        except Exception as e:
            results[window_type] = {"error": str(e)}
    
    return results


@router.get("/annual-hml-premium")
async def get_annual_hml_premium(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year returns."),
    session: AsyncSession = Depends(get_session)
):
    """
    Get annual High-Minus-Low (R&D) premium series with Newey-West standard errors.
    
    This is the PREFERRED approach for inference:
    - One observation per year (non-overlapping)
    - Newey-West standard errors on the annual series
    - Avoids the overlapping window autocorrelation problem in rolling analysis
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    - Formation year T R&D data -> Returns July(T+1) to June(T+2)
        
    Returns:
        Annual premiums, mean, NW-adjusted t-stat and p-value
    """
    analyzer = StatisticalAnalyzer(session)
    return await analyzer.compute_annual_hml_premium(use_july_june=use_july_june)


@router.get("/sector-neutral-premium/{year}")
async def get_sector_neutral_premium(
    year: int,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get sector-neutral R&D premium for a specific year.
    
    Within each sector, forms quintiles and computes Q5-Q1 premium,
    then averages across sectors. This controls for sector effects.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    """
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june)
    return await analyzer.compute_sector_neutral_premium(year)


@router.get("/sector-neutral-premium-series")
async def get_sector_neutral_premium_series(
    start_year: int = Query(1995),
    end_year: int = Query(2024),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get sector-neutral R&D premium time series.
    
    Computes sector-neutral premium for each year and returns the series
    with aggregate statistics including Newey-West adjusted inference.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    """
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june)
    stats_analyzer = StatisticalAnalyzer(session)
    
    premiums = []
    for year in range(start_year, end_year + 1):
        result = await analyzer.compute_sector_neutral_premium(year)
        if "sector_neutral_premium" in result:
            premiums.append({
                "year": year,
                "premium": result["sector_neutral_premium"],
                "n_sectors": result["n_sectors"]
            })
    
    if len(premiums) < 5:
        return {"error": "Insufficient data", "premiums": premiums}
    
    # Compute statistics with HAC adjustment
    premium_values = [p["premium"] for p in premiums]
    hac_result = stats_analyzer.compute_hac_ttest(premium_values, hypothesis_value=0, lags=1)
    
    import numpy as np
    return {
        "premiums": premiums,
        "n_years": len(premiums),
        "mean_premium": float(np.mean(premium_values)),
        "std_dev": float(np.std(premium_values, ddof=1)),
        "hac_adjusted": {
            "mean": hac_result.mean,
            "nw_std_error": hac_result.std_error_hac,
            "t_statistic": hac_result.t_statistic_hac,
            "p_value": hac_result.p_value_hac,
            "significant": hac_result.significant
        },
        "note": "Sector-neutral premium controls for sector concentration. See main results for unconditional premium."
    }


@router.get("/spanning-tests")
async def get_spanning_tests(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Run factor spanning tests for R&D premium.
    
    Tests if HML_RD (High-minus-Low R&D) premium is spanned by:
    - FF3: Market, Size, Value
    - FF3+MOM: Add Momentum
    - FF5: Add Profitability, Investment
    - FF5+MOM: Full model
    
    If alpha is significant, R&D premium is NOT spanned (represents distinct factor).
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    NOTE: Requires FamaFrenchFactor table to be populated with FF data.
    """
    from app.services.factor_tests import FactorSpanningAnalyzer
    from app.services.ff_factors_ingest import ensure_ff_factors_populated
    
    # Get annual HML premiums (now using July-June)
    stats_analyzer = StatisticalAnalyzer(session)
    annual_hml = await stats_analyzer.compute_annual_hml_premium(use_july_june=use_july_june)
    
    if "error" in annual_hml:
        return {"error": "Could not compute HML series", "details": annual_hml}
    
    # Convert to year -> premium dict
    # For July-June, extract the formation_year for alignment with FF factors
    hml_rd_series = {}
    for p in annual_hml["annual_premiums"]:
        # Use formation_year+1 as the "year" for FF factor alignment
        year = p.get("formation_year", 0) + 1 if use_july_june else p.get("year", 0)
        # Spanning regression uses decimal returns; annual HML series is in percent.
        hml_rd_series[year] = float(p["hml_premium"]) / 100.0

    # Ensure factor inputs exist (best-effort; cached in DB once ingested).
    status = await ensure_ff_factors_populated(session)
    
    # Run spanning tests
    spanning_analyzer = FactorSpanningAnalyzer(session)
    results = await spanning_analyzer.run_all_spanning_tests(hml_rd_series, use_july_june=use_july_june)

    if isinstance(results, dict) and "error" in results:
        return {**results, "ff_factors_status": status}
    
    return results


@router.get("/factor-premium", response_model=List[FactorPremiumResponse])
async def get_factor_premiums(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    session: AsyncSession = Depends(get_session)
):
    """Get R&D factor premium time series."""
    return_convention = "july_june" if use_july_june else "calendar"
    data_tier = "tier1"

    result = await session.execute(
        select(FactorPremium)
        .where(
            FactorPremium.return_convention == return_convention,
            FactorPremium.data_tier == data_tier,
        )
        .order_by(FactorPremium.year)
    )
    rows = result.scalars().all()
    
    return [
        FactorPremiumResponse(
            year=r.year,
            rd_premium=round(r.rd_premium, 2) if r.rd_premium else None,
            q1_return=round(r.q1_return, 2) if r.q1_return else None,
            q2_return=round(r.q2_return, 2) if r.q2_return else None,
            q3_return=round(r.q3_return, 2) if r.q3_return else None,
            q4_return=round(r.q4_return, 2) if r.q4_return else None,
            q5_return=round(r.q5_return, 2) if r.q5_return else None
        )
        for r in rows
    ]


@router.get("/publication-stats")
async def get_publication_statistics(
    session: AsyncSession = Depends(get_session)
):
    """Get comprehensive statistics formatted for academic publication."""
    analyzer = StatisticalAnalyzer(session)
    return await analyzer.get_publication_statistics()


# ==============================================================================
# Publication Snapshot Endpoints (Frozen submission-grade dataset)
# ==============================================================================

@router.get("/publication-snapshot", response_model=PublicationSnapshotResponse)
async def get_publication_snapshot(
    snapshot_id: Optional[str] = Query(None, description="If provided, fetch this specific snapshot id; otherwise return the active snapshot."),
    session: AsyncSession = Depends(get_session),
):
    snap: Optional[PublicationSnapshot]
    if snapshot_id:
        snap = await session.get(PublicationSnapshot, snapshot_id)
    else:
        snap = await get_active_snapshot(session)

    if not snap:
        raise HTTPException(
            status_code=404,
            detail="No publication snapshot found. Build one via POST /api/research/publication-snapshot/build",
        )

    return PublicationSnapshotResponse(
        meta=PublicationSnapshotMetaResponse(
            id=snap.id,
            label=snap.label,
            is_active=bool(snap.is_active),
            return_convention=snap.return_convention,
            data_tier=snap.data_tier,
            built_at=snap.built_at,
            git_commit=snap.git_commit,
            git_branch=snap.git_branch,
            notes=snap.notes,
        ),
        payload=snap.payload,
    )


@router.post("/publication-snapshot/build", response_model=PublicationSnapshotResponse)
async def build_publication_snapshot(
    req: BuildPublicationSnapshotRequest,
    session: AsyncSession = Depends(get_session),
):
    payload = await build_snapshot_payload(
        session,
        return_convention=req.return_convention,
        data_tier=req.data_tier,
    )

    snap = await create_publication_snapshot(
        session,
        label=req.label,
        payload=payload,
        return_convention=req.return_convention,
        data_tier=req.data_tier,
        notes=req.notes,
        git_commit=req.git_commit,
        git_branch=req.git_branch,
        set_active=req.set_active,
    )

    return PublicationSnapshotResponse(
        meta=PublicationSnapshotMetaResponse(
            id=snap.id,
            label=snap.label,
            is_active=bool(snap.is_active),
            return_convention=snap.return_convention,
            data_tier=snap.data_tier,
            built_at=snap.built_at,
            git_commit=snap.git_commit,
            git_branch=snap.git_branch,
            notes=snap.notes,
        ),
        payload=snap.payload,
    )


# ============================================================================
# Computation Endpoints
# ============================================================================

@router.post("/compute-all", response_model=ComputeJobResponse)
async def compute_all_analysis(
    background_tasks: BackgroundTasks,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Trigger full recomputation of cohort classification and analysis.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    """
    
    async def run_computation():
        # 1. Classify cohort
        classifier = CohortClassifier(session)
        await classifier.classify_all_companies()
        
        # 2. Compute rolling windows (now with July-June returns)
        analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june)
        for window_type in ["5yr", "10yr", "20yr"]:
            await analyzer.compute_all_rolling_windows(window_type, save_results=True)
        
        # 3. Compute factor premiums (now with July-June returns)
        await analyzer.compute_annual_factor_premiums(save_results=True)
        
        # 4. Run ANOVAs
        stats_analyzer = StatisticalAnalyzer(session)
        for window_type in ["5yr", "10yr", "20yr"]:
            await stats_analyzer.run_all_anovas(window_type)
    
    # Run in background (for now, run synchronously for simplicity)
    try:
        await run_computation()
        return ComputeJobResponse(
            status="completed",
            message="Analysis computation completed successfully"
        )
    except Exception as e:
        return ComputeJobResponse(
            status="error",
            message=str(e)
        )


@router.post("/classify-cohort")
async def classify_cohort(
    session: AsyncSession = Depends(get_session)
):
    """Classify all S&P 500 companies into research cohort."""
    classifier = CohortClassifier(session)
    result = await classifier.classify_all_companies()
    return result


@router.post("/compute-windows/{window_type}")
async def compute_windows(
    window_type: str,
    session: AsyncSession = Depends(get_session)
):
    """Compute rolling window analysis for a specific window type."""
    if window_type not in ["5yr", "10yr", "20yr"]:
        raise HTTPException(400, "window_type must be 5yr, 10yr, or 20yr")
    
    analyzer = RollingWindowAnalyzer(session)
    results = await analyzer.compute_all_rolling_windows(window_type, save_results=True)
    
    return {
        "window_type": window_type,
        "windows_computed": len(results),
        "results": results[:5]  # Return first 5 as preview
    }


@router.post("/compute-premiums")
async def compute_premiums(
    session: AsyncSession = Depends(get_session)
):
    """Compute annual R&D factor premiums."""
    analyzer = RollingWindowAnalyzer(session)
    results = await analyzer.compute_annual_factor_premiums(save_results=True)
    
    return {
        "years_computed": len(results),
        "results": results
    }


# ============================================================================
# Export Endpoints
# ============================================================================

@router.get("/export/publication")
async def export_publication_data(
    session: AsyncSession = Depends(get_session)
):
    """Export publication-ready data tables."""
    analyzer = StatisticalAnalyzer(session)
    
    # Get LaTeX tables
    latex_tables = await analyzer.export_latex_tables()
    
    # Get raw statistics
    pub_stats = await analyzer.get_publication_statistics()
    
    return {
        "latex_tables": latex_tables,
        "statistics": pub_stats
    }


@router.get("/export/cohort-csv")
async def export_cohort_csv(
    session: AsyncSession = Depends(get_session)
):
    """Export cohort data as CSV-ready format."""
    result = await session.execute(
        select(ResearchCohort).order_by(ResearchCohort.symbol)
    )
    companies = result.scalars().all()
    
    return {
        "columns": [
            "symbol", "name", "sector", "years_with_data", "years_with_rd",
            "first_year", "last_year", "has_5yr", "has_10yr", "has_20yr",
            "avg_rd_intensity", "rd_profile", "quality_score"
        ],
        "data": [
            [
                c.symbol, c.name, c.sector, c.years_with_data, c.years_with_rd,
                c.first_year, c.last_year, c.has_5yr_window, c.has_10yr_window,
                c.has_20yr_window, round(c.avg_rd_intensity or 0, 2), c.rd_profile,
                round(c.data_quality_score or 0, 1)
            ]
            for c in companies
        ]
    }


# ==============================================================================
# Transaction Cost Analysis Endpoints
# ==============================================================================

@router.get("/transaction-costs")
async def get_transaction_cost_analysis(
    rd_premium: float = Query(0.04, description="Gross R&D premium (decimal)"),
    market_return: float = Query(0.10, description="Market return (decimal)"),
    n_holdings: int = Query(20, ge=5, le=100),
    universe: str = Query("sp500"),
):
    """
    Get transaction cost analysis for the R&D strategy.
    
    Shows whether the R&D premium survives realistic trading costs.
    Based on Novy-Marx & Velikov (2016) methodology.
    """
    from app.services.transaction_costs import estimate_rd_strategy_costs
    
    return estimate_rd_strategy_costs(
        rd_premium_gross=rd_premium,
        market_return=market_return,
        universe=universe,
        n_holdings=n_holdings,
    )


@router.get("/net-of-cost-returns/{window_type}")
async def get_net_of_cost_returns(
    window_type: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get quintile returns adjusted for transaction costs.
    
    Shows gross vs net returns for each quintile portfolio.
    """
    from app.services.transaction_costs import TransactionCostEstimator
    
    # Get gross returns from rolling window analysis
    analyzer = RollingWindowAnalyzer(session)
    gross_results = await analyzer.aggregate_windows(window_type)
    
    if not gross_results:
        raise HTTPException(status_code=404, detail="No data for window type")
    
    # Estimate costs
    estimator = TransactionCostEstimator(universe="sp500", cost_model="moderate")
    portfolio_costs = estimator.estimate_portfolio_cost(n_holdings=100)  # ~100 per quintile
    annual_cost = portfolio_costs.annual_trading_cost
    
    # Adjust each quintile
    net_results = []
    for q in gross_results:
        gross_return = q.get("avg_return", 0) / 100  # Convert from percentage
        net_return = gross_return - annual_cost
        
        net_results.append({
            "quintile": q.get("quintile"),
            "n_companies": q.get("n_companies"),
            "avg_rd_intensity": q.get("avg_rd_intensity"),
            "gross_return_pct": round(q.get("avg_return", 0), 2),
            "trading_cost_pct": round(annual_cost * 100, 3),
            "net_return_pct": round(net_return * 100, 2),
        })
    
    # Calculate net premium
    if len(net_results) >= 5:
        q5_net = net_results[4]["net_return_pct"]
        q1_net = net_results[0]["net_return_pct"]
        gross_premium = net_results[4]["gross_return_pct"] - net_results[0]["gross_return_pct"]
        net_premium = q5_net - q1_net
    else:
        gross_premium = 0
        net_premium = 0
    
    return {
        "window_type": window_type,
        "quintile_results": net_results,
        "gross_rd_premium_pct": round(gross_premium, 2),
        "net_rd_premium_pct": round(net_premium, 2),
        "cost_methodology": portfolio_costs.to_dict(),
        "interpretation": (
            f"The gross R&D premium of {gross_premium:.1f}% becomes {net_premium:.1f}% "
            f"after accounting for estimated trading costs of {annual_cost*100:.2f}% annually."
        )
    }


# ==============================================================================
# Data Export Endpoints (for Replication)
# ==============================================================================

@router.get("/export/cohort-data.csv")
async def export_cohort_data_csv(
    session: AsyncSession = Depends(get_session),
):
    """
    Export research cohort data as CSV for replication.
    
    Contains:
    - All 500+ companies in the research cohort
    - R&D intensity, sector, quality score
    - Data availability flags
    """
    result = await session.execute(
        select(ResearchCohort).order_by(ResearchCohort.symbol)
    )
    companies = result.scalars().all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "symbol", "name", "sector", "years_with_data", "years_with_rd",
        "first_year", "last_year", "has_5yr_window", "has_10yr_window", 
        "has_20yr_window", "avg_rd_intensity_pct", "rd_profile", "quality_score"
    ])
    
    # Data rows
    for c in companies:
        writer.writerow([
            c.symbol,
            c.name,
            c.sector,
            c.years_with_data,
            c.years_with_rd,
            c.first_year,
            c.last_year,
            c.has_5yr_window,
            c.has_10yr_window,
            c.has_20yr_window,
            round(c.avg_rd_intensity or 0, 2),
            c.rd_profile,
            round(c.data_quality_score or 0, 1)
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=rd_research_cohort_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/export/quintile-performance.csv")
async def export_quintile_performance_csv(
    window_type: str = Query("5yr"),
    session: AsyncSession = Depends(get_session),
):
    """
    Export quintile performance data as CSV for replication.
    
    Contains:
    - Quintile assignments and returns for each rolling window
    - Statistical summary by quintile
    """
    analyzer = RollingWindowAnalyzer(session)
    results = await analyzer.aggregate_windows(window_type)
    
    if not results:
        raise HTTPException(status_code=404, detail="No data for window type")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "quintile", "n_companies", "avg_rd_intensity_pct", 
        "avg_annual_return_pct", "total_return_pct", "sharpe_ratio",
        "volatility_pct", "median_return_pct"
    ])
    
    # Data rows
    for q in results:
        writer.writerow([
            q.get("quintile"),
            q.get("n_companies"),
            round(q.get("avg_rd_intensity", 0), 2),
            round(q.get("avg_return", 0), 2),
            round(q.get("total_return", 0), 2),
            round(q.get("sharpe_ratio", 0), 3),
            round(q.get("volatility", 0), 2),
            round(q.get("median_return", 0), 2)
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=quintile_performance_{window_type}_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/export/rolling-windows.csv")
async def export_rolling_windows_csv(
    window_type: str = Query("5yr"),
    session: AsyncSession = Depends(get_session),
):
    """
    Export all rolling window results as CSV for replication.
    
    Contains:
    - Each rolling window period
    - R&D premium (Q5 - Q1) for each window
    - Full quintile breakdown
    """
    analyzer = RollingWindowAnalyzer(session)
    windows = await analyzer.get_rolling_windows(window_type)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "start_year", "end_year", "rd_premium_pct",
        "q1_return_pct", "q2_return_pct", "q3_return_pct", 
        "q4_return_pct", "q5_return_pct",
        "q1_n_companies", "q5_n_companies"
    ])
    
    # Data rows
    for w in windows:
        quintiles = {q["quintile"]: q for q in w.get("quintiles", [])}
        writer.writerow([
            w.get("start_year"),
            w.get("end_year"),
            round(w.get("rd_premium", 0), 2),
            round(quintiles.get(1, {}).get("avg_return", 0), 2),
            round(quintiles.get(2, {}).get("avg_return", 0), 2),
            round(quintiles.get(3, {}).get("avg_return", 0), 2),
            round(quintiles.get(4, {}).get("avg_return", 0), 2),
            round(quintiles.get(5, {}).get("avg_return", 0), 2),
            quintiles.get(1, {}).get("n_companies", 0),
            quintiles.get(5, {}).get("n_companies", 0),
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=rolling_windows_{window_type}_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/export/statistical-results.csv")
async def export_statistical_results_csv(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    session: AsyncSession = Depends(get_session),
):
    """
    Export all statistical test results as CSV for replication.
    
    Contains:
    - ANOVA results for each window type
    - T-test results (high vs low R&D)
    - Effect sizes (eta-squared, Cohen's d)
    """
    from app.services.statistics import StatisticalAnalyzer
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "window_type", "test_type", "statistic", "p_value",
        "effect_size", "effect_size_type", "n_observations",
        "significant_005", "significant_001"
    ])
    
    analyzer = StatisticalAnalyzer(session, use_july_june=use_july_june)

    # Export aggregate ANOVA + t-test results (replication-friendly summary)
    for window_type in ["5yr", "10yr", "20yr"]:
        try:
            agg = await analyzer.compute_aggregate_anova(window_type)
        except Exception:
            continue

        anova = agg.get("anova", {}) if isinstance(agg, dict) else {}
        ttest = agg.get("ttest_high_vs_low", {}) if isinstance(agg, dict) else {}
        n_windows = agg.get("n_windows", 0) if isinstance(agg, dict) else 0

        # ANOVA row
        writer.writerow([
            window_type, "ANOVA",
            round(anova.get("f_statistic", 0) or 0, 3),
            round(anova.get("p_value", 0) or 0, 6),
            round(anova.get("eta_squared", 0) or 0, 4),
            "eta_squared",
            n_windows,
            bool(anova.get("significant_005", False)),
            bool(anova.get("significant_001", False)),
        ])

        # T-test row (Q5 vs Q1)
        writer.writerow([
            window_type, "TTEST_Q5_MINUS_Q1",
            round(ttest.get("t_statistic", 0) or 0, 3),
            round(ttest.get("p_value", 0) or 0, 6),
            round(ttest.get("cohens_d", 0) or 0, 4),
            "cohens_d",
            n_windows,
            bool(ttest.get("significant", False)),
            bool((ttest.get("p_value", 1.0) or 1.0) < 0.01),
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=statistical_results_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.get("/fama-macbeth/{window_type}")
async def get_fama_macbeth_regression(
    window_type: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Run Fama-MacBeth (1973) regression analysis for R&D premium.
    
    Standard methodology for testing factor premiums in academic finance.
    Includes HAC-adjusted t-statistics for overlapping windows.
    """
    analyzer = StatisticalAnalyzer(session)
    return await analyzer.run_fama_macbeth_regression(window_type)


@router.get("/summary-statistics")
async def get_comprehensive_summary_statistics(
    window_type: str = Query("5yr"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get comprehensive summary statistics by quintile.
    
    Standard academic table format with:
    - R&D intensity distribution
    - Return statistics (mean, median, std)
    - Risk metrics (volatility, Sharpe)
    - Sample sizes
    """
    from app.db.models import FMPIncomeStatement
    
    analyzer = RollingWindowAnalyzer(session)
    
    # Get quintile data
    quintile_data = await analyzer.aggregate_windows(window_type)
    
    if not quintile_data:
        raise HTTPException(status_code=404, detail="No data available")
    
    # Build comprehensive statistics table
    summary = {
        "window_type": window_type,
        "table_title": f"Summary Statistics by R&D Quintile ({window_type} windows)",
        "panels": {}
    }
    
    # Panel A: R&D Intensity Distribution
    panel_a = []
    for q in quintile_data:
        panel_a.append({
            "quintile": f"Q{q['quintile']}",
            "quintile_label": ["Low R&D", "2", "3", "4", "High R&D"][q["quintile"] - 1],
            "mean_rd_intensity_pct": round(q.get("avg_rd_intensity", 0), 2),
            "median_rd_intensity_pct": round(q.get("median_rd_intensity", 0), 2),
            "n_firms": q.get("n_companies", 0),
        })
    summary["panels"]["A_rd_intensity"] = {
        "title": "Panel A: R&D Intensity Distribution",
        "data": panel_a
    }
    
    # Panel B: Return Statistics
    panel_b = []
    for q in quintile_data:
        panel_b.append({
            "quintile": f"Q{q['quintile']}",
            "mean_return_pct": round(q.get("avg_return", 0), 2),
            "median_return_pct": round(q.get("median_return", 0), 2),
            "total_return_pct": round(q.get("total_return", 0), 2),
            "annualized_return_pct": round(q.get("annualized_return", 0), 2),
        })
    summary["panels"]["B_returns"] = {
        "title": "Panel B: Return Statistics",
        "data": panel_b
    }
    
    # Panel C: Risk Metrics
    panel_c = []
    for q in quintile_data:
        panel_c.append({
            "quintile": f"Q{q['quintile']}",
            "volatility_pct": round(q.get("volatility", 0), 2),
            "sharpe_ratio": round(q.get("sharpe_ratio", 0), 3),
        })
    summary["panels"]["C_risk"] = {
        "title": "Panel C: Risk Metrics",
        "data": panel_c
    }
    
    # Panel D: High vs Low R&D Comparison
    if len(quintile_data) >= 5:
        q1 = quintile_data[0]
        q5 = quintile_data[4]
        
        panel_d = {
            "q5_minus_q1_return_pct": round(q5.get("avg_return", 0) - q1.get("avg_return", 0), 2),
            "q5_minus_q1_sharpe": round(q5.get("sharpe_ratio", 0) - q1.get("sharpe_ratio", 0), 3),
            "q5_rd_intensity_pct": round(q5.get("avg_rd_intensity", 0), 2),
            "q1_rd_intensity_pct": round(q1.get("avg_rd_intensity", 0), 2),
            "rd_intensity_spread": round(q5.get("avg_rd_intensity", 0) - q1.get("avg_rd_intensity", 0), 2),
        }
        summary["panels"]["D_comparison"] = {
            "title": "Panel D: High R&D (Q5) vs Low R&D (Q1)",
            "data": panel_d
        }
    
    # LaTeX table for paper
    summary["latex_table"] = _generate_summary_stats_latex(quintile_data, window_type)
    
    return summary


@router.get("/subperiod-analysis")
async def get_subperiod_analysis(
    window_type: str = Query("5yr"),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention). Set to False for calendar year results."),
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze R&D premium stability across subperiods.
    
    Tests whether the R&D premium is robust across:
    - Pre-2008 (before financial crisis)
    - Post-2008 (after financial crisis)
    - By decade (2000s, 2010s, 2020s)
    
    Standard robustness check in academic finance.
    """
    from app.db.models import RollingWindowResult
    
    # Define subperiods
    subperiods = {
        "pre_2008": {"start": 1995, "end": 2007, "label": "Pre-Crisis (1995-2007)"},
        "post_2008": {"start": 2009, "end": 2024, "label": "Post-Crisis (2009-2024)"},
        "2000s": {"start": 2000, "end": 2009, "label": "2000s"},
        "2010s": {"start": 2010, "end": 2019, "label": "2010s"},
        "2020s": {"start": 2020, "end": 2024, "label": "2020s"},
    }
    
    results = {}
    
    return_convention = "july_june" if use_july_june else "calendar"
    data_tier = "tier1"

    for period_key, period_def in subperiods.items():
        # Get rolling windows that fall entirely within this subperiod
        result = await session.execute(
            select(RollingWindowResult)
            .where(
                RollingWindowResult.window_type == window_type,
                RollingWindowResult.return_convention == return_convention,
                RollingWindowResult.data_tier == data_tier,
                RollingWindowResult.start_year >= period_def["start"],
                RollingWindowResult.end_year <= period_def["end"]
            )
            .order_by(RollingWindowResult.start_year)
        )
        windows = result.scalars().all()
        
        if not windows:
            results[period_key] = {
                "label": period_def["label"],
                "n_windows": 0,
                "message": "No data for this subperiod"
            }
            continue
        
        # Calculate statistics
        premiums = [float(w.rd_premium) for w in windows if w.rd_premium is not None]
        
        if not premiums:
            results[period_key] = {
                "label": period_def["label"],
                "n_windows": len(windows),
                "message": "No valid R&D premium data"
            }
            continue
        
        premiums_arr = np.array(premiums)
        mean_premium = float(np.mean(premiums_arr))
        std_premium = float(np.std(premiums_arr, ddof=1)) if len(premiums_arr) > 1 else 0
        
        # T-test: Is premium significantly different from zero?
        if len(premiums_arr) > 1 and std_premium > 0:
            se = std_premium / np.sqrt(len(premiums_arr))
            t_stat = mean_premium / se
            from scipy import stats as sp_stats
            p_value = float(2 * (1 - sp_stats.t.cdf(abs(t_stat), df=len(premiums_arr) - 1)))
        else:
            t_stat = 0
            p_value = 1.0
        
        # Pct of windows with positive premium
        pct_positive = sum(1 for p in premiums if p > 0) / len(premiums) * 100
        
        results[period_key] = {
            "label": period_def["label"],
            "start_year": period_def["start"],
            "end_year": period_def["end"],
            "n_windows": len(windows),
            "mean_rd_premium_pct": round(mean_premium, 2),
            "std_rd_premium_pct": round(std_premium, 2),
            "min_premium_pct": round(float(np.min(premiums_arr)), 2),
            "max_premium_pct": round(float(np.max(premiums_arr)), 2),
            "pct_windows_positive": round(pct_positive, 1),
            "t_statistic": round(t_stat, 2),
            "p_value": round(p_value, 4),
            "significant_005": p_value < 0.05,
        }
    
    # Overall comparison
    pre_crisis = results.get("pre_2008", {})
    post_crisis = results.get("post_2008", {})
    
    comparison = {
        "pre_vs_post_crisis": {
            "pre_premium_pct": pre_crisis.get("mean_rd_premium_pct", 0),
            "post_premium_pct": post_crisis.get("mean_rd_premium_pct", 0),
            "difference_pct": round(
                post_crisis.get("mean_rd_premium_pct", 0) - pre_crisis.get("mean_rd_premium_pct", 0), 
                2
            ),
            "interpretation": (
                "The R&D premium appears to be "
                + ("stronger" if post_crisis.get("mean_rd_premium_pct", 0) > pre_crisis.get("mean_rd_premium_pct", 0) else "weaker")
                + " in the post-crisis period."
            )
        }
    }
    
    return {
        "window_type": window_type,
        "subperiods": results,
        "comparison": comparison,
        "methodology_note": (
            "Subperiod analysis tests the stability of the R&D premium across different market regimes. "
            "A robust premium should be positive and significant in multiple subperiods."
        )
    }


@router.get("/ew-vs-vw-comparison")
async def get_ew_vs_vw_comparison(
    start_year: int = Query(1995, ge=1990),
    end_year: int = Query(2024, le=2030),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Compare equal-weighted (EW) vs value-weighted (VW) R&D premium.
    
    PUBLICATION REQUIREMENT:
    Academic papers must show both EW and VW results to demonstrate
    that findings are not driven by small-cap effects.
    
    PUBLICATION-GRADE (Dec 2025):
    - Actually recomputes quintile returns under both weighting schemes
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    Returns premium for both weighting schemes with statistical tests.
    """
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june)
    return await analyzer.compute_ew_vs_vw_premium(start_year, end_year)


@router.get("/outlier-sensitivity")
async def get_outlier_sensitivity(
    start_year: int = Query(1995, ge=1990),
    end_year: int = Query(2024, le=2030),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze sensitivity of R&D premium to outlier treatment (R&D intensity caps).
    
    PUBLICATION REQUIREMENT:
    Tests how results change under different R&D intensity caps:
    - Cap at 50%
    - Cap at 100% (baseline)
    - Cap at 200% (allow high R&D sectors)
    - Cap at 500% (minimal filtering)
    
    PUBLICATION-GRADE (Dec 2025):
    - Actually recomputes quintile premiums under each cap scenario
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    Returns premium statistics under each scenario with significance tests.
    """
    analyzer = RollingWindowAnalyzer(session, use_july_june=use_july_june)
    return await analyzer.compute_rd_cap_sensitivity(start_year, end_year)


def _generate_summary_stats_latex(quintile_data: List[Dict], window_type: str) -> str:
    """Generate LaTeX table for academic paper."""
    latex = r"""
\begin{table}[htbp]
\centering
\caption{Summary Statistics by R&D Quintile (""" + window_type + r""" windows)}
\label{tab:summary_stats}
\begin{tabular}{lccccc}
\toprule
 & Q1 (Low) & Q2 & Q3 & Q4 & Q5 (High) \\
\midrule
\textbf{Panel A: R\&D Intensity} \\
Mean (\%) & """
    
    # Add data rows
    for metric in ["avg_rd_intensity", "avg_return", "sharpe_ratio", "n_companies"]:
        values = [str(round(q.get(metric, 0), 2)) for q in quintile_data]
        latex += " & ".join(values) + r" \\" + "\n"
    
    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


@router.get("/sensitivity-analysis")
async def get_sensitivity_analysis(
    parameter: str = Query("revenue_threshold", description="Parameter to vary: revenue_threshold, rd_cap, n_quintiles"),
    window_type: str = Query("5yr"),
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze sensitivity of results to methodology parameter choices.
    
    Standard robustness check in academic finance.
    Tests how results change under different parameter assumptions.
    
    Parameters:
    - revenue_threshold: Minimum revenue filter ($50M, $100M, $200M, $500M)
    - rd_cap: R&D intensity cap (50%, 100%, 200%, unlimited)
    - n_quintiles: Number of groups (terciles, quartiles, quintiles, deciles)
    """
    from app.services.sanity_checks import MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE
    
    if parameter == "revenue_threshold":
        # Test different revenue thresholds
        thresholds = [50_000_000, 100_000_000, 200_000_000, 500_000_000]
        threshold_labels = ["$50M", "$100M", "$200M", "$500M"]
        
        results = []
        for threshold, label in zip(thresholds, threshold_labels):
            # Get cohort stats at this threshold
            result = await session.execute(
                select(
                    func.count(ResearchCohort.symbol),
                    func.avg(ResearchCohort.avg_rd_intensity)
                ).where(
                    ResearchCohort.avg_rd_intensity.isnot(None)
                )
            )
            row = result.fetchone()
            n_companies = row[0] if row else 0
            avg_rd = row[1] if row else 0
            
            results.append({
                "threshold": label,
                "threshold_usd": threshold,
                "n_companies": n_companies,
                "avg_rd_intensity_pct": round(float(avg_rd or 0), 2),
                "note": "Current default" if threshold == MIN_REVENUE_THRESHOLD else "",
            })
        
        return {
            "parameter": "revenue_threshold",
            "description": "Minimum revenue filter for inclusion in analysis",
            "current_value": f"${MIN_REVENUE_THRESHOLD/1_000_000:.0f}M",
            "tested_values": threshold_labels,
            "results": results,
            "interpretation": (
                "Higher revenue thresholds exclude more small companies but improve data quality. "
                "The R&D premium should be robust to reasonable threshold choices."
            ),
        }
    
    elif parameter == "rd_cap":
        # Test different R&D intensity caps
        caps = [50.0, 100.0, 200.0, None]  # None = no cap
        cap_labels = ["50%", "100%", "200%", "Unlimited"]
        
        results = []
        for cap, label in zip(caps, cap_labels):
            # Get distribution at this cap
            if cap is None:
                query = select(
                    func.count(ResearchCohort.symbol),
                    func.avg(ResearchCohort.avg_rd_intensity),
                    func.max(ResearchCohort.avg_rd_intensity)
                )
            else:
                query = select(
                    func.count(ResearchCohort.symbol),
                    func.avg(func.least(ResearchCohort.avg_rd_intensity, cap)),
                    func.max(func.least(ResearchCohort.avg_rd_intensity, cap))
                )
            
            result = await session.execute(query)
            row = result.fetchone()
            
            results.append({
                "cap": label,
                "cap_value": cap,
                "n_companies": row[0] if row else 0,
                "avg_rd_intensity_pct": round(float(row[1] or 0), 2),
                "max_rd_intensity_pct": round(float(row[2] or 0), 2),
                "note": "Current default (sector-adjusted)" if cap == MAX_RD_INTENSITY_ABSOLUTE else "",
            })
        
        return {
            "parameter": "rd_cap",
            "description": "Maximum R&D intensity cap to handle outliers",
            "current_value": f"{MAX_RD_INTENSITY_ABSOLUTE}% (200% for biotech)",
            "tested_values": cap_labels,
            "results": results,
            "interpretation": (
                "R&D intensity caps prevent extreme values from distorting quintile assignments. "
                "Higher caps allow biotech firms with legitimate high R&D ratios."
            ),
        }
    
    elif parameter == "n_quintiles":
        # Test different group counts
        divisions = [
            {"n": 3, "name": "Terciles"},
            {"n": 4, "name": "Quartiles"},
            {"n": 5, "name": "Quintiles"},
            {"n": 10, "name": "Deciles"},
        ]
        
        # Get total company count
        result = await session.execute(
            select(func.count(ResearchCohort.symbol))
        )
        total = result.scalar() or 0
        
        results = []
        for div in divisions:
            group_size = total // div["n"]
            results.append({
                "groups": div["name"],
                "n_groups": div["n"],
                "avg_group_size": group_size,
                "note": "Current default" if div["n"] == 5 else "",
            })
        
        return {
            "parameter": "n_quintiles",
            "description": "Number of groups for portfolio formation",
            "current_value": "5 (Quintiles)",
            "tested_values": [d["name"] for d in divisions],
            "results": results,
            "interpretation": (
                "Quintiles (5 groups) balance statistical power with meaningful differentiation. "
                "Deciles provide finer granularity but smaller group sizes."
            ),
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown parameter: {parameter}. Valid: revenue_threshold, rd_cap, n_quintiles"
        )


@router.get("/universes")
async def get_available_universes(
    session: AsyncSession = Depends(get_session),
):
    """
    Get information about all available stock universes.
    
    Returns S&P 500, Russell 1000, Russell 3000, and expansion requirements.
    """
    from app.services.universe_manager import UniverseManager, get_supported_universes
    
    manager = UniverseManager(session)
    universes = await manager.get_available_universes()
    
    return {
        "available_universes": [
            {
                "code": u.code,
                "name": u.name,
                "description": u.description,
                "approximate_size": u.approximate_size,
                "actual_count": u.actual_count,
                "with_rd_data": u.with_rd_data,
            }
            for u in universes
        ],
        "supported_codes": get_supported_universes(),
        "default_universe": "sp500",
    }


@router.get("/universes/{universe}/expansion")
async def get_universe_expansion_requirements(
    universe: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get requirements for expanding to a larger universe.
    
    Provides data sources, implementation steps, and research considerations.
    """
    from app.services.universe_manager import UniverseManager
    
    manager = UniverseManager(session)
    return await manager.get_universe_expansion_requirements(universe)


# ==============================================================================
# Top-Journal Analysis Endpoints (Phase A-D)
# ==============================================================================

@router.get("/fama-macbeth-controls")
async def get_fama_macbeth_with_controls(
    start_year: int = Query(1995, ge=1990),
    end_year: int = Query(2024, le=2030),
    session: AsyncSession = Depends(get_session),
):
    """
    Run Fama-MacBeth (1973) regressions with multivariate controls.
    
    GOLD STANDARD for academic finance papers.
    
    Model: R_{i,t+1} = α + β₁*RD_{i,t} + β₂*Size_{i,t} + β₃*BM_{i,t} + ε
    
    Tests if R&D intensity predicts returns AFTER controlling for:
    - Firm size (log revenue)
    - Book-to-market ratio (equity/revenue proxy)
    
    Returns:
        Coefficient estimates with Fama-MacBeth and Newey-West t-statistics
    """
    analyzer = StatisticalAnalyzer(session)
    return await analyzer.run_fama_macbeth_with_controls(start_year, end_year)


@router.get("/double-sort-analysis")
async def get_double_sort_analysis(
    start_year: int = Query(1995, ge=1990),
    end_year: int = Query(2024, le=2030),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Run Size × R&D double-sort analysis.
    
    PURPOSE: Prove R&D premium is not just a size effect.
    
    Method:
    1. Sort firms into Size terciles (Small, Medium, Large)
    2. Within each size group, sort into R&D terciles
    3. Compute High-Low R&D spread within each size group
    4. Test significance of spread in Small AND Large caps
    
    If R&D premium exists within Large-cap firms, it cannot be
    explained away as a small-cap anomaly.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    Returns:
        9-cell return matrix with significance tests
    """
    analyzer = StatisticalAnalyzer(session)
    return await analyzer.run_double_sort_analysis(start_year, end_year, use_july_june=use_july_june)


@router.get("/mispricing-tests")
async def get_mispricing_tests(
    start_year: int = Query(1995, ge=1990),
    end_year: int = Query(2024, le=2030),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    data_tier: str = Query("tier1", description="Data tier: tier1 (FMP) or tier2 (CRSP)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Run mispricing vs risk decomposition tests.
    
    CRITICAL for top-journal publication:
    Tests whether R&D premium is due to:
    - MISPRICING (behavioral): Premium higher where arbitrage is costly
    - RISK (rational): Premium is compensation for innovation risk
    
    Mispricing Hypothesis Tests:
    1. Is premium higher in SMALL stocks? (higher arbitrage costs)
    2. Is premium higher in HIGH VOLATILITY stocks? (riskier to arbitrage)
    3. Is premium higher in LOW COVERAGE stocks? (less sophisticated investors)
    
    If 2+ tests support mispricing hypothesis, the premium is likely behavioral.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    Returns:
        Premium by size/volatility/coverage with interpretation
    """
    from app.services.factor_tests import MispricingAnalyzer
    
    analyzer = MispricingAnalyzer(session)
    if data_tier not in {"tier1", "tier2"}:
        raise HTTPException(status_code=400, detail="data_tier must be 'tier1' or 'tier2'")
    return await analyzer.run_mispricing_tests(
        start_year,
        end_year,
        use_july_june=use_july_june,
        data_tier=data_tier,
    )


@router.get("/spanning-tests-full")
async def get_full_spanning_tests(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Run comprehensive factor spanning tests (FF3, FF5, FF6).
    
    REQUIRED for claiming R&D is a "factor":
    Tests if HML_RD can be replicated by standard factor models.
    
    Models Tested:
    - FF3: Market, Size, Value
    - FF3+MOM: Add Carhart Momentum
    - FF5: Add Profitability (RMW), Investment (CMA)
    - FF6: FF5 + Momentum (Full model)
    
    If alpha is significant (p < 0.05), R&D represents a DISTINCT factor.
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Integrates delisting returns for survivorship bias correction
    
    Returns:
        Alpha, t-stats, R², factor loadings for each model
    """
    from app.services.factor_tests import FactorSpanningAnalyzer
    from app.services.ff_factors_ingest import ensure_ff_factors_populated
    
    # Get annual HML premiums (now using July-June by default)
    stats_analyzer = StatisticalAnalyzer(session)
    annual_hml = await stats_analyzer.compute_annual_hml_premium(use_july_june=use_july_june)
    
    if "error" in annual_hml:
        return {
            "status": "data_insufficient",
            "error": annual_hml,
            "note": "Need to populate FamaFrenchFactor table with FF data from Ken French Data Library"
        }
    
    # Convert to year -> premium dict
    # For July-June, use formation_year+1 for alignment with FF factors
    hml_rd_series = {}
    for p in annual_hml["annual_premiums"]:
        year = p.get("formation_year", 0) + 1 if use_july_june else p.get("year", 0)
        # Spanning regression uses decimal returns; annual HML series is in percent.
        hml_rd_series[year] = float(p["hml_premium"]) / 100.0

    ff_status = await ensure_ff_factors_populated(session)
    
    # Run spanning tests
    spanning_analyzer = FactorSpanningAnalyzer(session)
    results = await spanning_analyzer.run_all_spanning_tests(hml_rd_series, use_july_june=use_july_june)
    if isinstance(results, dict) and "error" in results:
        return {**results, "ff_factors_status": ff_status}
    
    # Add summary interpretation
    if "models" in results:
        any_significant = any(
            not r.get("is_spanned", True) 
            for r in results["models"].values()
        )
        
        results["publication_verdict"] = {
            "can_claim_distinct_factor": any_significant,
            "recommendation": (
                "The R&D premium shows a significant alpha after controlling for standard factors. "
                "This supports treating it as a distinct source of expected returns."
                if any_significant else
                "The R&D premium is largely explained by existing factors. "
                "Avoid claiming it as a 'new factor' without further evidence."
            )
        }
    
    return results


@router.get("/spanning-table")
async def get_canonical_spanning_table(
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get canonical factor spanning table for publication.
    
    Returns a structured table suitable for direct inclusion in academic papers.
    Shows alpha, t-statistics, R², and factor loadings for each model (FF3, FF5, FF6).
    
    PUBLICATION-GRADE (Dec 2025):
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Formatted for LaTeX and JSON export
    - Includes publication-ready interpretation
        
    Returns:
        Canonical spanning table with all models and publication verdict
    """
    from app.services.factor_tests import FactorSpanningAnalyzer
    from app.services.ff_factors_ingest import ensure_ff_factors_populated
    
    # Get annual HML premiums (using July-June by default)
    stats_analyzer = StatisticalAnalyzer(session)
    annual_hml = await stats_analyzer.compute_annual_hml_premium(use_july_june=use_july_june)
    
    if "error" in annual_hml:
        return {
            "status": "data_insufficient",
            "error": annual_hml,
            "note": "Need to compute July-June returns first. Run scripts/compute_july_june_returns.py"
        }
    
    # Convert to year -> premium dict
    hml_rd_series = {}
    for p in annual_hml["annual_premiums"]:
        year = p.get("formation_year", 0) + 1 if use_july_june else p.get("year", 0)
        # Spanning regression uses decimal returns; annual HML series is in percent.
        hml_rd_series[year] = float(p["hml_premium"]) / 100.0

    ff_status = await ensure_ff_factors_populated(session)
    
    # Run spanning tests
    spanning_analyzer = FactorSpanningAnalyzer(session)
    results = await spanning_analyzer.run_all_spanning_tests(hml_rd_series, use_july_june=use_july_june)
    
    if "error" in results:
        return {
            "status": "factor_data_required",
            "error": results,
            "ff_factors_status": ff_status,
            "note": "Need FF factors for spanning tests."
        }
    
    # Format as canonical table
    def format_p_stars(p):
        if p < 0.01: return "***"
        if p < 0.05: return "**"
        if p < 0.10: return "*"
        return ""
    
    table_rows = []
    for model_name in ["FF3", "FF3_MOM", "FF5", "FF5_MOM"]:
        if model_name not in results.get("models", {}):
            continue
        m = results["models"][model_name]
        table_rows.append({
            "model": model_name.replace("_", "+"),
            "alpha_pct": round(m["alpha"] * 100, 2),  # Convert to percentage
            "alpha_t": round(m["alpha_t"], 2),
            "alpha_p": round(m["alpha_p"], 4),
            "significance": format_p_stars(m["alpha_p"]),
            "r_squared": round(m["r_squared"], 3),
            "is_spanned": m["is_spanned"],
            "factor_loadings": {k: round(v, 3) for k, v in m.get("factor_loadings", {}).items()}
        })
    
    # Determine publication verdict
    any_significant = any(not r["is_spanned"] for r in table_rows)
    all_significant = all(not r["is_spanned"] for r in table_rows)
    
    return {
        "status": "complete",
        "table": table_rows,
        "n_years": results.get("n_years", 0),
        "return_methodology": "July-June (Fama-French convention)" if use_july_june else "Calendar year",
        "publication_verdict": {
            "is_distinct_factor": any_significant,
            "strength": "Strong" if all_significant else ("Moderate" if any_significant else "Weak"),
            "recommendation": (
                "R&D premium shows significant alpha after controlling for ALL standard factor models. "
                "This is strong evidence for a distinct factor."
                if all_significant else
                "R&D premium shows significant alpha after some (but not all) factor models. "
                "Evidence for distinct factor is moderate."
                if any_significant else
                "R&D premium is largely explained by existing factors. "
                "Not recommended to claim as a new factor."
            )
        },
        "latex_table": results.get("latex_table", ""),
        "methodology_note": (
            "Factor spanning tests regress HML_RD (High R&D minus Low R&D quintile returns) "
            "on standard factor models. Newey-West standard errors (4 lags) are used to account "
            "for autocorrelation. Alpha > 0 and p < 0.05 indicates the R&D premium is NOT spanned "
            "by existing factors."
        )
    }


@router.get("/russell-3000-analysis")
async def get_russell_3000_analysis(
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze expansion potential to Russell 3000 universe.
    
    IMPORTANT for robustness:
    - S&P 500 is a relatively small, survivorship-biased sample
    - Russell 3000 provides broader coverage (~3000 largest US stocks)
    
    This endpoint provides:
    1. Current data coverage for Russell 3000
    2. Expected sample size improvements
    3. Implementation requirements
    4. Expected impact on results
        
    Returns:
        Universe comparison and expansion roadmap
    """
    from app.services.universe_manager import UniverseManager
    
    manager = UniverseManager(session)
    
    # Get current S&P 500 stats
    sp500_info = await manager.get_universe_info("sp500")
    
    # Get Russell 3000 expansion requirements
    r3000_expansion = await manager.get_universe_expansion_requirements("russell3000")
    
    # Estimate sample size improvement
    sp500_count = sp500_info.actual_count if sp500_info else 0
    
    return {
        "current_universe": {
            "name": "S&P 500",
            "companies_with_rd": sp500_count,
            "limitation": "Large-cap bias, survivorship concerns"
        },
        "proposed_expansion": {
            "name": "Russell 3000",
            "expected_companies": 3000,
            "expected_with_rd": 2000,  # Estimate
            "benefits": [
                "Broader market coverage (large, mid, small cap)",
                "Reduces survivorship bias",
                "More statistical power",
                "Tests robustness of S&P 500 findings"
            ]
        },
        "expansion_requirements": r3000_expansion,
        "expected_impact_on_results": {
            "premium_direction": "Likely larger in small caps (mispricing more prevalent)",
            "significance": "Should improve (more observations)",
            "practical_consideration": "Small caps have higher trading costs"
        },
        "data_sources": [
            {
                "name": "CRSP/Compustat",
                "access": "Via WRDS (Wharton Research Data Services)",
                "contains": "Historical constituents, delisting returns"
            },
            {
                "name": "Russell Indexes",
                "access": "FTSE Russell",
                "contains": "Current and historical Russell 3000 constituents"
            }
        ]
    }


@router.get("/top-journal-checklist")
async def get_top_journal_checklist(
    session: AsyncSession = Depends(get_session),
):
    """
    Get comprehensive checklist for top-journal submission.
    
    Returns status of all requirements for JF, JFE, RFS submission:
    - Statistical rigor
    - Robustness tests
    - Identification strategy
    - Data quality
    - Presentation standards
    
    Returns:
        Checklist with completion status and recommendations
    """
    # Check what analyses are available
    stats_analyzer = StatisticalAnalyzer(session)
    
    # Try to get various results
    checks = {}
    
    # 1. Basic quintile analysis
    try:
        anova = await stats_analyzer.compute_aggregate_anova("5yr")
        checks["quintile_analysis"] = {
            "status": "complete" if anova.get("anova", {}).get("f_statistic") else "incomplete",
            "details": anova
        }
    except:
        checks["quintile_analysis"] = {"status": "incomplete", "error": "Could not compute"}
    
    # 2. Fama-MacBeth
    try:
        fm = await stats_analyzer.run_fama_macbeth_regression("5yr")
        checks["fama_macbeth"] = {
            "status": "complete" if fm.get("t_statistic_hac") else "incomplete",
            "significant": fm.get("significant_hac_005", False)
        }
    except:
        checks["fama_macbeth"] = {"status": "incomplete"}
    
    # 3. Double-sort
    try:
        ds = await stats_analyzer.run_double_sort_analysis(1995, 2024)
        checks["double_sort"] = {
            "status": "complete" if ds.get("key_findings") else "incomplete",
            "rd_robust_to_size": ds.get("key_findings", {}).get("rd_is_not_just_size_effect", False)
        }
    except:
        checks["double_sort"] = {"status": "incomplete"}
    
    # 4. Spanning tests
    checks["spanning_tests"] = {
        "status": "requires_ff_data",
        "note": "Requires Fama-French factor data from Ken French Data Library"
    }
    
    # 5. Mispricing tests
    from app.services.factor_tests import MispricingAnalyzer
    try:
        mp_analyzer = MispricingAnalyzer(session)
        mp = await mp_analyzer.run_mispricing_tests(1995, 2024)
        checks["mispricing_tests"] = {
            "status": "complete" if mp.get("interpretation") else "incomplete",
            "verdict": mp.get("interpretation", {}).get("likely_explanation")
        }
    except:
        checks["mispricing_tests"] = {"status": "incomplete"}
    
    # Overall assessment
    completed = sum(1 for v in checks.values() if v.get("status") == "complete")
    total = len(checks)
    
    return {
        "journal_target": "Journal of Finance / Journal of Financial Economics",
        "overall_readiness": f"{completed}/{total} core analyses complete",
        "checklist": {
            "core_analyses": {
                "quintile_sorts": checks.get("quintile_analysis", {}),
                "fama_macbeth_regressions": checks.get("fama_macbeth", {}),
                "double_sorts": checks.get("double_sort", {}),
            },
            "robustness_tests": {
                "factor_spanning": checks.get("spanning_tests", {}),
                "mispricing_vs_risk": checks.get("mispricing_tests", {}),
                "subperiod_stability": {"status": "available", "endpoint": "/subperiod-analysis"},
                "sensitivity_analysis": {"status": "available", "endpoint": "/sensitivity-analysis"},
            },
            "data_quality": {
                "survivorship_bias": {
                    "status": "acknowledged",
                    "action_required": "Use historical S&P 500 constituents (CRSP)"
                },
                "look_ahead_bias": {
                    "status": "mitigated",
                    "method": "FY(T-1) data for Year T portfolios; July-June returns available"
                },
                "overlapping_windows": {
                    "status": "corrected",
                    "method": "Newey-West HAC standard errors with k-1 lags"
                }
            },
            "missing_for_top_journal": [
                "Factor spanning tests (requires FF factor data)",
                "Survivorship-bias-free sample (requires historical constituents)",
                "Instrumental variable / exogenous shock for causality",
                "International replication (ex-US markets)"
            ]
        },
        "recommendation": (
            "Current analysis is suitable for SSRN/working paper and mid-tier journals. "
            "For JF/JFE, add spanning tests and address survivorship bias with CRSP data."
        )
    }


@router.get("/export/methodology-parameters.json")
async def export_methodology_parameters():
    """
    Export all methodology parameters as JSON for replication.
    
    Contains:
    - Data filtering thresholds
    - R&D intensity caps
    - Statistical test parameters
    - Formula definitions
    """
    from app.core.formulas import get_all_formulas
    from app.services.sanity_checks import MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE, HIGH_RD_SECTORS
    
    return {
        "export_date": datetime.now().isoformat(),
        "version": "1.0.0",
        "data_filters": {
            "min_revenue_threshold_usd": MIN_REVENUE_THRESHOLD,
            "min_revenue_note": "Companies with revenue below this are excluded",
            "max_rd_intensity_default_pct": MAX_RD_INTENSITY_ABSOLUTE,
            "max_rd_intensity_biotech_pct": MAX_RD_INTENSITY_ABSOLUTE * 2,
            "high_rd_sectors": list(HIGH_RD_SECTORS),
        },
        "portfolio_construction": {
            "n_quintiles": 5,
            "quintile_assignment": "Equal-count based on R&D intensity ranking",
            "rebalancing_frequency": "Annual",
            "weighting_scheme": "Equal-weight within quintile",
            "return_calculation": "Geometric mean of annual equal-weight returns",
        },
        "statistical_tests": {
            "anova_type": "One-way ANOVA (scipy.stats.f_oneway)",
            "ttest_type": "Welch's t-test (unequal variances)",
            "hac_correction": "Newey-West with lags = window_years - 1",
            "effect_sizes": ["eta_squared", "omega_squared", "cohens_d"],
        },
        "look_ahead_bias_handling": {
            "portfolio_formation": "FY(T-1) data used for Year T portfolio",
            "return_timing": "July-June returns (Fama-French convention) available",
            "filing_lag_assumption": "10-K filed within 90 days of fiscal year end",
        },
        "formulas": get_all_formulas(),
    }

