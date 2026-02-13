"""
PATH: backend/app/api/routes/fmp/rd_analysis.py
PURPOSE: R&D leaderboard, sector breakdown, and trend endpoints
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.sanity_checks import cap_rd_intensity, MIN_REVENUE_THRESHOLD
from app.api.routes.fmp.models import RDLeaderboard


router = APIRouter()


@router.get("/rd/leaderboard", response_model=List[RDLeaderboard])
async def get_rd_leaderboard(
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
):
    """Get top R&D spenders ranked by R&D intensity."""
    
    # Use standard minimum revenue filter for consistency with research cohort
    result = await session.execute(text("""
        SELECT 
            i.symbol,
            c.name,
            c.sector,
            AVG(i.rd_expenses / NULLIF(i.revenue, 0)) as avg_rd_intensity,
            SUM(i.rd_expenses) as total_rd_spend,
            COUNT(*) as years_of_data
        FROM fmp_income_statements i
        JOIN sp500_companies c ON i.symbol = c.symbol
        WHERE i.rd_expenses > 0 AND i.revenue >= :min_revenue
        GROUP BY i.symbol, c.name, c.sector
        HAVING COUNT(*) >= 5
        ORDER BY avg_rd_intensity DESC
        LIMIT :limit
    """), {"limit": limit, "min_revenue": MIN_REVENUE_THRESHOLD})
    
    rows = result.fetchall()
    
    # Apply R&D intensity cap for display (200% for healthcare, 100% for others)
    return [
        RDLeaderboard(
            symbol=r.symbol,
            name=r.name,
            sector=r.sector,
            avg_rd_intensity=round(cap_rd_intensity(r.avg_rd_intensity * 100, r.sector), 2),
            total_rd_spend=r.total_rd_spend,
            years_of_data=r.years_of_data,
        )
        for r in rows
    ]


@router.get("/rd/by-sector")
async def get_rd_by_sector(session: AsyncSession = Depends(get_session)):
    """Get R&D statistics grouped by sector."""
    
    # Use standard minimum revenue filter for consistency with research cohort
    result = await session.execute(text("""
        SELECT 
            c.sector,
            COUNT(DISTINCT i.symbol) as company_count,
            AVG(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as avg_rd_intensity,
            SUM(i.rd_expenses) as total_rd_spend,
            AVG(i.rd_expenses) as avg_rd_spend
        FROM fmp_income_statements i
        JOIN sp500_companies c ON i.symbol = c.symbol
        WHERE i.rd_expenses > 0 AND i.revenue >= :min_revenue AND c.sector IS NOT NULL
        GROUP BY c.sector
        ORDER BY avg_rd_intensity DESC
    """), {"min_revenue": MIN_REVENUE_THRESHOLD})
    
    # Apply R&D intensity cap for display (200% for healthcare, 100% for others)
    return [
        {"sector": r.sector, "company_count": r.company_count,
         "avg_rd_intensity": round(cap_rd_intensity(r.avg_rd_intensity, r.sector), 2),
         "total_rd_spend": r.total_rd_spend,
         "avg_rd_spend": round(r.avg_rd_spend, 0)}
        for r in result.fetchall()
    ]


@router.get("/rd/trends")
async def get_rd_trends(session: AsyncSession = Depends(get_session)):
    """Get R&D intensity trends over time."""
    
    # Use standard minimum revenue filter for consistency with research cohort
    max_complete_fiscal_year = datetime.utcnow().year - 1
    result = await session.execute(text("""
        SELECT 
            fiscal_year,
            COUNT(DISTINCT symbol) as companies,
            AVG(rd_expenses / NULLIF(revenue, 0)) * 100 as avg_rd_intensity,
            SUM(rd_expenses) as total_rd_spend
        FROM fmp_income_statements
        WHERE rd_expenses > 0
          AND revenue >= :min_revenue
          AND fiscal_year <= :max_year
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """), {"min_revenue": MIN_REVENUE_THRESHOLD, "max_year": max_complete_fiscal_year})
    
    return [
        {"year": r.fiscal_year, "companies": r.companies,
         "avg_rd_intensity": round(r.avg_rd_intensity, 2),
         "total_rd_spend": r.total_rd_spend}
        for r in result.fetchall()
    ]
