"""
PATH: backend/app/api/routes/research/fama_macbeth_routes.py
PURPOSE: Fama-MacBeth regression and comprehensive summary-statistics endpoints.
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


# ---------- helper used by /summary-statistics ----------

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

