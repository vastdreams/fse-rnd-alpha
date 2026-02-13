"""
PATH: backend/app/api/routes/companies/list_detail.py
PURPOSE: Company listing, detail, and price history endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.db.models import Company, CompanyYearCore, FinancialsCore, FinancialsRatios, TextFactorRD, Price
from app.api.routes.companies.models import (
    CompanyListItem, CompanyDetail, YearData,
    Financials, IncomeStatement, BalanceSheet, CashFlow,
    RatiosResponse, TextFactorsResponse,
)


router = APIRouter()


@router.get("/", response_model=List[CompanyListItem])
async def list_companies(
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all companies with summary stats."""
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.company_years))
        .offset(skip)
        .limit(limit)
    )
    companies = result.scalars().all()
    
    items = []
    for company in companies:
        latest_year = max(company.company_years, key=lambda y: y.fiscal_year, default=None)
        items.append(CompanyListItem(
            id=company.id,
            ticker=company.ticker,
            name=company.name,
            cik=company.cik,
            sector=latest_year.sector if latest_year else None,
            industry=latest_year.industry if latest_year else None,
            years_available=len(company.company_years),
        ))
    
    return items


@router.get("/{ticker}", response_model=CompanyDetail)
async def get_company_detail(
    ticker: str,
    session: AsyncSession = Depends(get_session),
):
    """Get comprehensive company details."""
    ticker_upper = ticker.upper()
    
    # Get company with all relationships
    result = await session.execute(
        select(Company)
        .where(Company.ticker == ticker_upper)
        .options(
            selectinload(Company.company_years)
            .selectinload(CompanyYearCore.financials_core),
            selectinload(Company.company_years)
            .selectinload(CompanyYearCore.financials_ratios),
            selectinload(Company.company_years)
            .selectinload(CompanyYearCore.text_factor_rd),
            selectinload(Company.company_years)
            .selectinload(CompanyYearCore.annual_report),
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker_upper} not found")
    
    # Build years data
    years_data = []
    for cy in sorted(company.company_years, key=lambda y: y.fiscal_year, reverse=True):
        year_data = YearData(
            fiscal_year=cy.fiscal_year,
            filing_date=cy.filing_date.isoformat() if cy.filing_date else None,
            sector=cy.sector,
            industry=cy.industry,
        )
        
        # Financials
        if cy.financials_core:
            fc = cy.financials_core
            year_data.financials = Financials(
                income_statement=IncomeStatement(
                    revenue=fc.revenue,
                    cost_of_revenue=fc.cost_of_revenue,
                    gross_profit=fc.gross_profit,
                    rd_expense=fc.rd_expense,
                    sga_expense=fc.sga_expense,
                    operating_income=fc.operating_income,
                    net_income=fc.net_income,
                    eps_basic=fc.eps_basic,
                    eps_diluted=fc.eps_diluted,
                ),
                balance_sheet=BalanceSheet(
                    total_assets=fc.total_assets,
                    cash_and_equivalents=fc.cash_and_equivalents,
                    total_liabilities=fc.total_liabilities,
                    total_equity=fc.total_equity,
                    long_term_debt=fc.long_term_debt,
                ),
                cash_flow=CashFlow(
                    cash_from_operations=fc.cash_from_operations,
                    cash_from_investing=fc.cash_from_investing,
                    cash_from_financing=fc.cash_from_financing,
                    capex=fc.capex,
                ),
            )
        
        # Ratios
        if cy.financials_ratios:
            fr = cy.financials_ratios
            year_data.ratios = RatiosResponse(
                rd_intensity=fr.rd_intensity,
                gross_margin=fr.gross_margin,
                operating_margin=fr.operating_margin,
                net_margin=fr.net_margin,
                roe=fr.roe,
                roa=fr.roa,
            )
        
        # Text factors
        if cy.text_factor_rd:
            tf = cy.text_factor_rd
            year_data.rd_text_factors = TextFactorsResponse(
                rd_mentions_count=tf.rd_mentions_count,
                rd_tone_score=tf.rd_tone_score,
                rd_section_length_words=tf.rd_section_length_words,
                extraction_confidence=tf.extraction_confidence,
            )
        
        years_data.append(year_data)
    
    # Get price data count
    price_result = await session.execute(
        select(func.count(Price.id)).where(Price.ticker == ticker_upper)
    )
    price_count = price_result.scalar() or 0
    
    return CompanyDetail(
        company=CompanyListItem(
            id=company.id,
            ticker=company.ticker,
            name=company.name,
            cik=company.cik,
            years_available=len(company.company_years),
        ),
        years=years_data,
        price_data={"price_points": price_count},
    )


@router.get("/{ticker}/prices")
async def get_company_prices(
    ticker: str,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(1000, ge=1, le=5000),
):
    """Get price data for a company."""
    result = await session.execute(
        select(Price)
        .where(Price.ticker == ticker.upper())
        .order_by(desc(Price.date))
        .limit(limit)
    )
    prices = result.scalars().all()
    
    return [
        {
            "date": p.date.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
            "adjusted_close": p.adjusted_close,
        }
        for p in prices
    ]
