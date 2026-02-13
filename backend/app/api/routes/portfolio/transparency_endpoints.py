"""
PATH: backend/app/api/routes/portfolio/transparency_endpoints.py
PURPOSE: R&D Alpha scoring transparency endpoints — methodology, holdings breakdown, sector weights, candidate list.
WHY: Separated from core_endpoints to respect the ~300-line budget.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.rd_alpha_scorer import RDAlphaScorer

router = APIRouter()


@router.get("/methodology")
async def get_selection_methodology():
    """
    Get complete documentation of the R&D Alpha selection formula.
    
    Returns the formula, component explanations, sector constraints,
    research citations, and parameter values for full transparency.
    """
    from app.services.rd_alpha_scorer import RDAlphaScorer
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    
    # Create a minimal scorer to get methodology (doesn't need session)
    class MockSession:
        pass
    
    # Get methodology from class
    scorer = RDAlphaScorer(None)  # type: ignore
    methodology = scorer.get_selection_methodology()
    
    return {
        "formula": methodology.formula,
        "formula_latex": methodology.formula_latex,
        "components": methodology.components,
        "sector_constraints": methodology.sector_constraints,
        "research_citations": methodology.research_citations,
        "parameters": methodology.parameters,
        "last_updated": methodology.last_updated,
    }


@router.get("/rd-alpha-holdings")
async def get_rd_alpha_holdings(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    year: Optional[int] = Query(None, ge=1995, le=2030)
):
    """
    Get R&D Alpha ETF holdings using the new sector-agnostic scoring formula.
    
    This uses the research-based selection formula that:
    - Caps R&D intensity by sector
    - Applies sector adjustment to prevent tech/biotech overweight
    - Includes momentum and quality factors
    - Normalizes by volatility
    - Uses point-in-time FY(T-1) financials for backtests
    
    ETF20 R&D ALPHA SELECTION:
    Formation date is July 1 of the given year.
    Holdings are selected using only data available at formation.
    """
    scorer = RDAlphaScorer(session)
    
    # Calculate scores for all candidates (returns tuple with eligibility result)
    all_scores, eligibility_result = await scorer.calculate_alpha_scores(
        universe="sp500",
        as_of_year=year
    )
    
    # Apply sector constraints and get final selection
    selected, sector_weights = await scorer.apply_sector_constraints(
        all_scores, n_holdings=n
    )
    
    response = {
        "holdings": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "weight": round(s.weight * 100, 2),
                "rd_intensity": round(s.rd_intensity, 2),
                "rd_intensity_capped": round(s.rd_intensity_capped, 2),
                "sector_adjustment": round(s.sector_adjustment, 3),
                "momentum_factor": round(s.momentum_factor, 3),
                "quality_score": round(s.quality_score, 3),
                "final_score": round(s.final_score, 4),
                "rank": s.selection_rank,
                "fiscal_year_used": s.fiscal_year_used,
                "data_source": s.data_source,
            }
            for s in selected
        ],
        "sector_weights": [
            {
                "sector": sw.sector,
                "target_weight": round(sw.target_weight * 100, 1),
                "actual_weight": round(sw.actual_weight * 100, 1),
                "min_weight": round(sw.min_weight * 100, 1),
                "max_weight": round(sw.max_weight * 100, 1),
                "company_count": sw.company_count,
                "adjustment_needed": round(sw.adjustment_needed * 100, 1),
            }
            for sw in sector_weights
        ],
        "total_candidates": len(all_scores),
        "selected_count": len(selected),
    }
    
    # Add eligibility metadata if available
    if eligibility_result:
        response["eligibility"] = eligibility_result.to_meta_dict()
        response["eligibility"]["warnings"] = eligibility_result.warnings
    
    return response


@router.get("/sector-weights")
async def get_sector_weight_targets(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    year: Optional[int] = Query(None, ge=1995, le=2030)
):
    """
    Get target vs actual sector weights for the R&D Alpha ETF.
    
    Shows how the portfolio is diversified and what adjustments
    would be needed to match target weights.
    """
    scorer = RDAlphaScorer(session)
    
    all_scores, _ = await scorer.calculate_alpha_scores(
        universe="sp500",
        as_of_year=year
    )
    
    _, sector_weights = await scorer.apply_sector_constraints(
        all_scores, n_holdings=n
    )
    
    return [
        {
            "sector": sw.sector,
            "target_weight": round(sw.target_weight * 100, 1),
            "actual_weight": round(sw.actual_weight * 100, 1),
            "min_weight": round(sw.min_weight * 100, 1),
            "max_weight": round(sw.max_weight * 100, 1),
            "company_count": sw.company_count,
            "adjustment_needed": round(sw.adjustment_needed * 100, 1),
            "status": (
                "overweight" if sw.actual_weight > sw.max_weight else
                "underweight" if sw.actual_weight < sw.min_weight else
                "on_target"
            ),
        }
        for sw in sector_weights
    ]


@router.get("/selection-candidates")
async def get_all_selection_candidates(
    session: AsyncSession = Depends(get_db),
    year: Optional[int] = Query(None, ge=1995, le=2030),
    limit: int = Query(100, ge=10, le=500)
):
    """
    Get all candidate companies with their R&D Alpha scores.
    
    Provides full transparency on why companies were or weren't selected.
    Useful for understanding the selection process.
    """
    scorer = RDAlphaScorer(session)
    
    all_scores, eligibility_result = await scorer.get_all_candidates_with_scores(
        as_of_year=year,
        limit=limit
    )
    
    response = {
        "candidates": [
            {
                "rank": s.selection_rank,
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "rd_intensity": round(s.rd_intensity, 2),
                "rd_intensity_capped": round(s.rd_intensity_capped, 2),
                "sector_adjustment": round(s.sector_adjustment, 3),
                "momentum_factor": round(s.momentum_factor, 3),
                "quality_score": round(s.quality_score, 3),
                "volatility": round(s.volatility, 3),
                "final_score": round(s.final_score, 4),
                "years_of_data": s.years_of_data,
                "fiscal_year_used": s.fiscal_year_used,
                "data_source": s.data_source,
            }
            for s in all_scores
        ],
        "total_candidates": len(all_scores),
        "as_of_year": year,
    }
    
    # Add eligibility metadata if available
    if eligibility_result:
        response["eligibility"] = eligibility_result.to_meta_dict()
        response["eligibility"]["warnings"] = eligibility_result.warnings
    
    return response
