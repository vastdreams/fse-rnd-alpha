"""
PATH: backend/app/api/routes/research/statistical_analysis.py
PURPOSE: ANOVA, HML premium, spanning tests, factor premium, and publication stats.
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

