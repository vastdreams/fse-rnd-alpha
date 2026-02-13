"""
PATH: backend/app/api/routes/research/rolling_quintile.py
PURPOSE: Rolling-window analysis and quintile-performance endpoints.
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

