"""
PATH: backend/app/api/routes/fmp/overview.py
PURPOSE: Overview stats, returns summary, and sector list endpoints
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import (
    SP500Company, FMPIncomeStatement, FMPBalanceSheet,
    FMPCashFlow, FMPDailyPrice, FMPAnnualReturn
)
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD
from app.api.routes.fmp.models import OverviewStats


router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
async def get_fmp_overview(session: AsyncSession = Depends(get_session)):
    """Get comprehensive FMP data statistics."""
    
    # Counts
    companies = await session.scalar(select(func.count(SP500Company.symbol)))
    income = await session.scalar(select(func.count(FMPIncomeStatement.id)))
    balance = await session.scalar(select(func.count(FMPBalanceSheet.id)))
    cashflow = await session.scalar(select(func.count(FMPCashFlow.id)))
    prices = await session.scalar(select(func.count(FMPDailyPrice.id)))
    returns = await session.scalar(select(func.count()).select_from(FMPAnnualReturn))
    
    # Year range
    min_year = await session.scalar(select(func.min(FMPIncomeStatement.fiscal_year)))
    max_year = await session.scalar(select(func.max(FMPIncomeStatement.fiscal_year)))
    
    # R&D stats - use standard minimum revenue filter for consistency
    # This matches the research cohort filter for apples-to-apples comparison
    rd_companies = await session.scalar(
        select(func.count(func.distinct(FMPIncomeStatement.symbol)))
        .where(FMPIncomeStatement.rd_expenses > 0)
        .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
    )
    
    # Average R&D intensity (rd_expense / revenue)
    avg_rd = await session.scalar(
        select(func.avg(FMPIncomeStatement.rd_expenses / func.nullif(FMPIncomeStatement.revenue, 0)))
        .where(FMPIncomeStatement.rd_expenses > 0)
        .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
    )
    
    return OverviewStats(
        total_companies=companies or 0,
        total_income_statements=income or 0,
        total_balance_sheets=balance or 0,
        total_cash_flows=cashflow or 0,
        total_price_records=prices or 0,
        total_annual_returns=returns or 0,
        year_range={"min": min_year, "max": max_year},
        companies_with_rd=rd_companies or 0,
        avg_rd_intensity=round(avg_rd * 100, 2) if avg_rd else None,
    )


@router.get("/returns/summary")
async def get_returns_summary(session: AsyncSession = Depends(get_session)):
    """Get returns summary statistics."""
    
    result = await session.execute(text("""
        SELECT 
            year,
            COUNT(*) as companies,
            AVG(annual_return) * 100 as avg_return,
            AVG(volatility) * 100 as avg_volatility,
            MIN(annual_return) * 100 as min_return,
            MAX(annual_return) * 100 as max_return
        FROM fmp_annual_returns
        WHERE annual_return IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
    """))
    
    return [
        {"year": r.year, "companies": r.companies,
         "avg_return": round(r.avg_return, 2),
         "avg_volatility": round(r.avg_volatility, 2) if r.avg_volatility else None,
         "min_return": round(r.min_return, 2),
         "max_return": round(r.max_return, 2)}
        for r in result.fetchall()
    ]


@router.get("/sectors")
async def get_sectors(session: AsyncSession = Depends(get_session)):
    """Get list of sectors with company counts."""
    
    result = await session.execute(text("""
        SELECT sector, COUNT(*) as count
        FROM sp500_companies
        WHERE sector IS NOT NULL
        GROUP BY sector
        ORDER BY count DESC
    """))
    
    return [{"sector": r.sector, "count": r.count} for r in result.fetchall()]
