"""
PATH: backend/app/api/routes/fmp/companies_endpoints.py
PURPOSE: S&P 500 company listing, detail, and price endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import (
    SP500Company, FMPIncomeStatement, FMPBalanceSheet,
    FMPCashFlow, FMPDailyPrice, FMPAnnualReturn
)
from app.api.routes.fmp.models import SP500CompanyResponse, CompanyFinancials


router = APIRouter()


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
