"""
PATH: backend/app/api/routes/research/advanced_analysis.py
PURPOSE: Sensitivity analysis and stock-universe endpoints.
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

