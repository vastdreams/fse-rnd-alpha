"""
PATH: backend/app/api/routes/factors.py
PURPOSE:
  - R&D factor API endpoints
  - Summary, detail, and cross-company analysis

ROLE IN ARCHITECTURE:
  - API route layer
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import CompanyYearCore, FinancialsRatios, TextFactorRD


router = APIRouter()


class RDFactorSummary(BaseModel):
    ticker: str
    fiscal_year: int
    rd_intensity: Optional[float] = None
    rd_tone_score: Optional[float] = None
    rd_mentions: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/rd/summary", response_model=List[RDFactorSummary])
async def get_rd_factor_summary(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(500, ge=1, le=2000),
):
    """Get R&D factor summary across all companies."""
    result = await session.execute(
        select(
            CompanyYearCore.ticker,
            CompanyYearCore.fiscal_year,
            FinancialsRatios.rd_intensity,
            TextFactorRD.rd_tone_score,
            TextFactorRD.rd_mentions_count,
        )
        .outerjoin(FinancialsRatios, CompanyYearCore.id == FinancialsRatios.company_year_id)
        .outerjoin(TextFactorRD, CompanyYearCore.id == TextFactorRD.company_year_id)
        .order_by(CompanyYearCore.ticker, CompanyYearCore.fiscal_year.desc())
        .limit(limit)
    )
    
    rows = result.all()
    return [
        RDFactorSummary(
            ticker=row.ticker,
            fiscal_year=row.fiscal_year,
            rd_intensity=row.rd_intensity,
            rd_tone_score=row.rd_tone_score,
            rd_mentions=row.rd_mentions_count,
        )
        for row in rows
    ]


@router.get("/rd/top")
async def get_top_rd_companies(
    session: AsyncSession = Depends(get_session),
    metric: str = Query("rd_intensity", regex="^(rd_intensity|rd_tone_score|rd_mentions_count)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get top companies by R&D metric."""
    if metric == "rd_intensity":
        order_col = FinancialsRatios.rd_intensity
        join_model = FinancialsRatios
    elif metric == "rd_tone_score":
        order_col = TextFactorRD.rd_tone_score
        join_model = TextFactorRD
    else:
        order_col = TextFactorRD.rd_mentions_count
        join_model = TextFactorRD
    
    result = await session.execute(
        select(
            CompanyYearCore.ticker,
            CompanyYearCore.fiscal_year,
            order_col,
        )
        .join(join_model, CompanyYearCore.id == join_model.company_year_id)
        .where(order_col.isnot(None))
        .order_by(order_col.desc())
        .limit(limit)
    )
    
    return [
        {"ticker": row[0], "fiscal_year": row[1], metric: row[2]}
        for row in result.all()
    ]


@router.get("/rd/distribution")
async def get_rd_distribution(
    session: AsyncSession = Depends(get_session),
    fiscal_year: Optional[int] = None,
):
    """Get R&D intensity distribution statistics."""
    query = select(
        func.count(FinancialsRatios.id).label("count"),
        func.avg(FinancialsRatios.rd_intensity).label("mean"),
        func.min(FinancialsRatios.rd_intensity).label("min"),
        func.max(FinancialsRatios.rd_intensity).label("max"),
    ).join(CompanyYearCore, CompanyYearCore.id == FinancialsRatios.company_year_id)
    
    if fiscal_year:
        query = query.where(CompanyYearCore.fiscal_year == fiscal_year)
    
    result = await session.execute(query)
    row = result.one()
    
    return {
        "count": row.count,
        "mean": float(row.mean) if row.mean else None,
        "min": float(row.min) if row.min else None,
        "max": float(row.max) if row.max else None,
    }
