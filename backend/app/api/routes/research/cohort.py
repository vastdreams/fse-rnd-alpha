"""
PATH: backend/app/api/routes/research/cohort.py
PURPOSE: Cohort listing, summary, data-quality, and window-filter endpoints.
"""
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.api.routes.research.schemas import (
    CohortCompanyResponse, CohortSummaryResponse, QuintileResponse,
    WindowResultResponse, AnovaResultResponse, FactorPremiumResponse,
    ComputeJobResponse, PublicationSnapshotMetaResponse,
    PublicationSnapshotResponse, BuildPublicationSnapshotRequest,
    DataQualityResponse,
)

router = APIRouter()


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

