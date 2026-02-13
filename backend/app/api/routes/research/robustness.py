"""
PATH: backend/app/api/routes/research/robustness.py
PURPOSE: Sub-period analysis, EW-vs-VW comparison, and outlier sensitivity endpoints.
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

