"""
PATH: backend/app/api/routes/fmp.py
PURPOSE:
  - API endpoints for FMP (Financial Modeling Prep) data
  - S&P 500 companies, financials, prices, returns
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import (
    SP500Company, FMPIncomeStatement, FMPBalanceSheet, 
    FMPCashFlow, FMPDailyPrice, FMPAnnualReturn
)
from app.services.sanity_checks import (
    cap_rd_intensity, 
    MAX_RD_INTENSITY_BIOTECH,
    MIN_REVENUE_THRESHOLD
)


router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class SP500CompanyResponse(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    sub_sector: Optional[str]
    cik: Optional[str]
    years_data: int = 0
    latest_revenue: Optional[float] = None
    latest_rd_expense: Optional[float] = None
    rd_intensity: Optional[float] = None

class OverviewStats(BaseModel):
    total_companies: int
    total_income_statements: int
    total_balance_sheets: int
    total_cash_flows: int
    total_price_records: int
    total_annual_returns: int
    year_range: dict
    companies_with_rd: int
    avg_rd_intensity: Optional[float]

class CompanyFinancials(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    income_statements: List[dict]
    balance_sheets: List[dict]
    cash_flows: List[dict]
    annual_returns: List[dict]
    rd_analysis: dict

class RDLeaderboard(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    avg_rd_intensity: float
    total_rd_spend: float
    years_of_data: int


# ============================================================================
# Overview Endpoints
# ============================================================================

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


# ============================================================================
# Companies Endpoints
# ============================================================================

@router.get("/companies", response_model=List[SP500CompanyResponse])
async def list_sp500_companies(
    session: AsyncSession = Depends(get_session),
    sector: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List S&P 500 companies with summary stats."""
    
    # Base query
    query = select(SP500Company)
    if sector:
        query = query.where(SP500Company.sector == sector)
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    companies = result.scalars().all()
    
    response = []
    for c in companies:
        # Get latest financials
        latest = await session.execute(
            select(FMPIncomeStatement)
            .where(FMPIncomeStatement.symbol == c.symbol)
            .order_by(desc(FMPIncomeStatement.fiscal_year))
            .limit(1)
        )
        latest_fin = latest.scalar_one_or_none()
        
        # Count years
        years_count = await session.scalar(
            select(func.count(FMPIncomeStatement.id))
            .where(FMPIncomeStatement.symbol == c.symbol)
        )
        
        rd_intensity = None
        if latest_fin and latest_fin.revenue and latest_fin.rd_expenses:
            rd_intensity = round((latest_fin.rd_expenses / latest_fin.revenue) * 100, 2)
        
        response.append(SP500CompanyResponse(
            symbol=c.symbol,
            name=c.name,
            sector=c.sector,
            sub_sector=c.sub_sector,
            cik=c.cik,
            years_data=years_count or 0,
            latest_revenue=latest_fin.revenue if latest_fin else None,
            latest_rd_expense=latest_fin.rd_expenses if latest_fin else None,
            rd_intensity=rd_intensity,
        ))
    
    return response


@router.get("/companies/{symbol}", response_model=CompanyFinancials)
async def get_company_financials(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get full financial data for a company."""
    from app.db.models import ResearchCohort
    
    symbol = symbol.upper()
    
    # Get company from SP500 table
    company = await session.scalar(
        select(SP500Company).where(SP500Company.symbol == symbol)
    )
    
    # Fallback to research cohort if not found
    cohort_company = None
    if not company:
        cohort_company = await session.scalar(
            select(ResearchCohort).where(ResearchCohort.symbol == symbol)
        )
        if not cohort_company:
            raise HTTPException(404, f"Company {symbol} not found")
    
    company_name = company.name if company else (cohort_company.name if cohort_company else symbol)
    company_sector = company.sector if company else (cohort_company.sector if cohort_company else None)
    
    # Income statements
    income_result = await session.execute(
        select(FMPIncomeStatement)
        .where(FMPIncomeStatement.symbol == symbol)
        .order_by(desc(FMPIncomeStatement.fiscal_year))
    )
    income_stmts = income_result.scalars().all()
    
    # Balance sheets
    balance_result = await session.execute(
        select(FMPBalanceSheet)
        .where(FMPBalanceSheet.symbol == symbol)
        .order_by(desc(FMPBalanceSheet.fiscal_year))
    )
    balance_sheets = balance_result.scalars().all()
    
    # Cash flows
    cf_result = await session.execute(
        select(FMPCashFlow)
        .where(FMPCashFlow.symbol == symbol)
        .order_by(desc(FMPCashFlow.fiscal_year))
    )
    cash_flows = cf_result.scalars().all()
    
    # Annual returns
    returns_result = await session.execute(
        select(FMPAnnualReturn)
        .where(FMPAnnualReturn.symbol == symbol)
        .order_by(desc(FMPAnnualReturn.year))
    )
    returns = returns_result.scalars().all()
    
    # R&D Analysis
    rd_data = [
        {"year": i.fiscal_year, "rd_expense": i.rd_expenses, "revenue": i.revenue,
         "rd_intensity": round((i.rd_expenses / i.revenue) * 100, 2) if i.revenue and i.rd_expenses else None}
        for i in income_stmts if i.rd_expenses
    ]
    
    total_rd = sum(i.rd_expenses or 0 for i in income_stmts)
    avg_intensity = sum(d["rd_intensity"] or 0 for d in rd_data) / len(rd_data) if rd_data else 0
    
    return CompanyFinancials(
        symbol=symbol,
        name=company_name,
        sector=company_sector,
        income_statements=[
            {"fiscal_year": i.fiscal_year, "revenue": i.revenue, "gross_profit": i.gross_profit,
             "rd_expenses": i.rd_expenses, "operating_income": i.operating_income,
             "net_income": i.net_income, "eps": i.eps, "ebitda": i.ebitda}
            for i in income_stmts
        ],
        balance_sheets=[
            {"fiscal_year": b.fiscal_year, "total_assets": b.total_assets,
             "total_liabilities": b.total_liabilities, "total_equity": b.total_equity,
             "cash": b.cash_and_equivalents, "total_debt": b.total_debt}
            for b in balance_sheets
        ],
        cash_flows=[
            {"fiscal_year": c.fiscal_year, "operating_cf": c.operating_cash_flow,
             "investing_cf": c.investing_cash_flow, "financing_cf": c.financing_cash_flow,
             "free_cash_flow": c.free_cash_flow, "capex": c.capital_expenditure}
            for c in cash_flows
        ],
        annual_returns=[
            {"year": r.year, "annual_return": round(r.annual_return * 100, 2) if r.annual_return else None,
             "volatility": round(r.volatility * 100, 2) if r.volatility else None}
            for r in returns
        ],
        rd_analysis={
            "total_rd_spend": total_rd,
            "avg_rd_intensity": round(avg_intensity, 2),
            "years_with_rd": len(rd_data),
            "rd_by_year": rd_data,
        }
    )


@router.get("/companies/{symbol}/prices")
async def get_company_prices(
    symbol: str,
    session: AsyncSession = Depends(get_session),
    days: int = Query(252, ge=1, le=7500),
):
    """Get price history for a company."""
    result = await session.execute(
        select(FMPDailyPrice)
        .where(FMPDailyPrice.symbol == symbol.upper())
        .order_by(desc(FMPDailyPrice.date))
        .limit(days)
    )
    prices = result.scalars().all()
    
    return [
        {"date": p.date.isoformat(), "open": p.open, "high": p.high, "low": p.low,
         "close": p.close, "adj_close": p.adj_close, "volume": p.volume}
        for p in reversed(prices)
    ]


# ============================================================================
# R&D Analysis Endpoints
# ============================================================================

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


# ============================================================================
# Returns Analysis Endpoints
# ============================================================================

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

