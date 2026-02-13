"""
PATH: backend/app/api/routes/research/transaction_costs.py
PURPOSE: Transaction cost analysis and net-of-cost return endpoints.
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

