"""
PATH: backend/app/api/routes/research/computation.py
PURPOSE: Trigger cohort classification, rolling windows, and premium computation.
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

