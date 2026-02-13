# EXEMPTION: 563 lines — Eight tightly-coupled top-journal analysis endpoints sharing complex SQL queries
"""
PATH: backend/app/api/routes/research/top_journal.py
PURPOSE: Top-journal submission endpoints (FM controls, double-sort, mispricing,
         spanning tests, Russell 3000, checklist, methodology export).
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


