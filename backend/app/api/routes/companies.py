"""
PATH: backend/app/api/routes/companies.py
PURPOSE:
  - Company-related API endpoints
  - List, detail, financials, prices

ROLE IN ARCHITECTURE:
  - API route layer
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.db.models import Company, CompanyYearCore, FinancialsCore, FinancialsRatios, TextFactorRD, AnnualReport, Price
from pydantic import BaseModel


router = APIRouter()


# Pydantic response models
class CompanyListItem(BaseModel):
    id: int
    ticker: str
    name: str
    cik: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    years_available: int = 0

    class Config:
        from_attributes = True


class IncomeStatement(BaseModel):
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    rd_expense: Optional[float] = None
    sga_expense: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None


class BalanceSheet(BaseModel):
    total_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    long_term_debt: Optional[float] = None


class CashFlow(BaseModel):
    cash_from_operations: Optional[float] = None
    cash_from_investing: Optional[float] = None
    cash_from_financing: Optional[float] = None
    capex: Optional[float] = None


class Financials(BaseModel):
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlow


class RatiosResponse(BaseModel):
    rd_intensity: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None


class TextFactorsResponse(BaseModel):
    rd_mentions_count: Optional[int] = None
    rd_tone_score: Optional[float] = None
    rd_section_length_words: Optional[int] = None
    extraction_confidence: Optional[float] = None


class YearData(BaseModel):
    fiscal_year: int
    filing_date: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    financials: Optional[Financials] = None
    ratios: Optional[RatiosResponse] = None
    rd_text_factors: Optional[TextFactorsResponse] = None

    class Config:
        from_attributes = True


class CompanyDetail(BaseModel):
    company: CompanyListItem
    years: List[YearData]
    price_data: dict

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CompanyListItem])
async def list_companies(
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all companies with summary stats."""
    # Get companies with year count
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


# Annual Reports Response Models
class AnnualReportSummary(BaseModel):
    fiscal_year: int
    filing_date: Optional[str] = None
    form_type: str
    accession_id: Optional[str] = None
    file_format: Optional[str] = None
    file_size_mb: Optional[float] = None
    has_xbrl: Optional[bool] = None
    word_count: Optional[int] = None
    sections_found: Optional[List[str]] = None
    rd_mentions: Optional[int] = None
    rd_tone_score: Optional[float] = None
    rd_section_length: Optional[int] = None
    sec_url: Optional[str] = None

    class Config:
        from_attributes = True


class AnnualReportsResponse(BaseModel):
    symbol: str
    company_name: str
    total_filings: int
    years_covered: List[int]
    filings: List[AnnualReportSummary]
    rd_analysis_summary: dict

    class Config:
        from_attributes = True


@router.get("/{ticker}/annual-reports", response_model=AnnualReportsResponse)
async def get_company_annual_reports(
    ticker: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get SEC 10-K annual report filings with R&D analysis.
    
    Returns:
    - List of available 10-K filings by year
    - R&D mentions and sentiment from text analysis
    - Links to SEC EDGAR
    """
    ticker_upper = ticker.upper()
    
    # Get company
    company_result = await session.execute(
        select(Company).where(Company.ticker == ticker_upper)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker_upper} not found")
    
    # Get all company years with annual reports and text factors
    cy_result = await session.execute(
        select(CompanyYearCore)
        .where(CompanyYearCore.company_id == company.id)
        .options(
            selectinload(CompanyYearCore.annual_report),
            selectinload(CompanyYearCore.text_factor_rd),
        )
        .order_by(desc(CompanyYearCore.fiscal_year))
    )
    company_years = cy_result.scalars().all()
    
    filings = []
    rd_mentions_total = 0
    rd_tone_scores = []
    
    for cy in company_years:
        ar = cy.annual_report
        tf = cy.text_factor_rd
        
        filing = AnnualReportSummary(
            fiscal_year=cy.fiscal_year,
            filing_date=cy.filing_date.isoformat() if cy.filing_date else None,
            form_type=ar.form_type if ar else "10-K",
            accession_id=ar.accession_id if ar else cy.sec_accession_id,
            file_format=ar.file_format if ar else None,
            file_size_mb=round(ar.file_size_bytes / 1e6, 2) if ar and ar.file_size_bytes else None,
            has_xbrl=ar.has_xbrl if ar else None,
            word_count=ar.word_count if ar else None,
            sections_found=ar.sections_found if ar else None,
            rd_mentions=tf.rd_mentions_count if tf else None,
            rd_tone_score=round(tf.rd_tone_score, 3) if tf and tf.rd_tone_score else None,
            rd_section_length=tf.rd_section_length_words if tf else None,
            sec_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={company.cik}&type=10-K&dateb=&owner=include&count=40" if company.cik else None
        )
        filings.append(filing)
        
        if tf and tf.rd_mentions_count:
            rd_mentions_total += tf.rd_mentions_count
        if tf and tf.rd_tone_score:
            rd_tone_scores.append(tf.rd_tone_score)
    
    # Calculate R&D analysis summary
    rd_summary = {
        "total_rd_mentions": rd_mentions_total,
        "avg_rd_tone": round(sum(rd_tone_scores) / len(rd_tone_scores), 3) if rd_tone_scores else None,
        "years_with_rd_analysis": len([f for f in filings if f.rd_mentions is not None]),
        "trend": "increasing" if len(rd_tone_scores) >= 2 and rd_tone_scores[0] > rd_tone_scores[-1] else "stable"
    }
    
    return AnnualReportsResponse(
        symbol=ticker_upper,
        company_name=company.name,
        total_filings=len(filings),
        years_covered=[f.fiscal_year for f in filings],
        filings=filings,
        rd_analysis_summary=rd_summary
    )
