# EXEMPTION: 327 lines — Six CSV/JSON export endpoints with shared streaming patterns
"""
PATH: backend/app/api/routes/research/exports.py
PURPOSE: Publication-data and CSV replication-export endpoints.
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
# Data Export Endpoints (CSV for Replication)
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

