"""
PATH: backend/app/api/routes/research/pnl_efficiency.py
PURPOSE: PNL Efficiency Alpha research endpoints — scores, quintiles, methodology.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.pnl_efficiency_scorer import PnlEfficiencyScorer

router = APIRouter(prefix="/pnl-efficiency", tags=["PNL Efficiency Alpha"])


class PnlScoreResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: Optional[str] = None
    gross_efficiency: float
    overhead_efficiency: float
    operating_efficiency: float
    profit_conversion: float
    gross_efficiency_z: float
    overhead_efficiency_z: float
    operating_efficiency_z: float
    profit_conversion_z: float
    composite_z: float
    sector_percentile: float
    final_score: float
    revenue: float
    fiscal_year_used: Optional[int] = None
    selection_rank: int


class PnlQuintileResponse(BaseModel):
    quintile: int
    label: str
    n_companies: int
    avg_composite_z: float
    avg_gross_eff: float
    avg_overhead_eff: float
    avg_operating_eff: float
    avg_profit_conv: float


class PnlMethodologyResponse(BaseModel):
    name: str
    components: dict
    scoring_method: str
    normalization: str
    winsorization: str
    phase: str
    excluded: list


@router.get("/scores", response_model=List[PnlScoreResponse])
async def get_pnl_scores(
    year: Optional[int] = Query(None, ge=1995, le=2030),
    limit: int = Query(100, ge=1, le=500),
    sector: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Get PNL Efficiency Alpha scores for S&P 500 companies."""
    scorer = PnlEfficiencyScorer(session)
    scores = await scorer.calculate_scores(as_of_year=year)

    if sector:
        scores = [s for s in scores if s.sector == sector]

    return [
        PnlScoreResponse(
            symbol=s.symbol,
            name=s.name,
            sector=s.sector,
            industry=s.industry,
            gross_efficiency=round(s.gross_efficiency, 4),
            overhead_efficiency=round(s.overhead_efficiency, 4),
            operating_efficiency=round(s.operating_efficiency, 4),
            profit_conversion=round(s.profit_conversion, 4),
            gross_efficiency_z=round(s.gross_efficiency_z, 3),
            overhead_efficiency_z=round(s.overhead_efficiency_z, 3),
            operating_efficiency_z=round(s.operating_efficiency_z, 3),
            profit_conversion_z=round(s.profit_conversion_z, 3),
            composite_z=round(s.composite_z, 3),
            sector_percentile=s.sector_percentile,
            final_score=round(s.final_score, 3),
            revenue=s.revenue,
            fiscal_year_used=s.fiscal_year_used,
            selection_rank=s.selection_rank,
        )
        for s in scores[:limit]
    ]


@router.get("/quintiles", response_model=List[PnlQuintileResponse])
async def get_pnl_quintiles(
    year: Optional[int] = Query(None, ge=1995, le=2030),
    session: AsyncSession = Depends(get_session),
):
    """Get quintile breakdown of PNL efficiency scores."""
    scorer = PnlEfficiencyScorer(session)
    scores = await scorer.calculate_scores(as_of_year=year)

    if not scores:
        return []

    n = len(scores)
    quintile_size = n // 5
    quintiles = []

    for q in range(1, 6):
        if q < 5:
            start = (q - 1) * quintile_size
            end = q * quintile_size
        else:
            start = (q - 1) * quintile_size
            end = n
        group = scores[start:end]

        if not group:
            continue

        avg = lambda attr: sum(getattr(s, attr) for s in group) / len(group)

        label = f"Q{q}"
        if q == 1:
            label += " (Most Efficient)"
        elif q == 5:
            label += " (Least Efficient)"

        quintiles.append(PnlQuintileResponse(
            quintile=q,
            label=label,
            n_companies=len(group),
            avg_composite_z=round(avg("composite_z"), 3),
            avg_gross_eff=round(avg("gross_efficiency"), 4),
            avg_overhead_eff=round(avg("overhead_efficiency"), 4),
            avg_operating_eff=round(avg("operating_efficiency"), 4),
            avg_profit_conv=round(avg("profit_conversion"), 4),
        ))

    return quintiles


@router.get("/methodology", response_model=PnlMethodologyResponse)
async def get_pnl_methodology():
    """Return PNL Efficiency Alpha methodology documentation."""
    return PnlMethodologyResponse(
        name="PNL Efficiency Alpha",
        components={
            "gross_efficiency": "1 - (COGS / Revenue) — measures production efficiency",
            "overhead_efficiency": "1 - (SGA / Revenue) — measures overhead leanness",
            "operating_efficiency": "1 - (OpEx / Revenue) — measures total operating leverage",
            "profit_conversion": "Net Income / Revenue — measures bottom-line conversion",
        },
        scoring_method="Equal-weight average of four sector-relative z-scored components",
        normalization="Within-sector z-scoring using same-year sector peers (min 5 peers required)",
        winsorization="Z-scores capped at +/- 3 standard deviations",
        phase="Phase 1 — Operating efficiency only. Labor efficiency (payroll, headcount) deferred to Phase 2.",
        excluded=[
            "Employee count (requires annual report extraction — not yet available historically)",
            "Payroll expense (not standardized in structured FMP data)",
            "R&D intensity (covered separately by R&D Alpha)",
        ],
    )
