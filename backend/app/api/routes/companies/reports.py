"""
PATH: backend/app/api/routes/companies/reports.py
PURPOSE: SEC 10-K annual report filing endpoint with R&D analysis
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.db.models import Company, CompanyYearCore
from app.api.routes.companies.models import (
    AnnualReportSummary, AnnualReportsResponse,
)


router = APIRouter()


@router.get("/{ticker}/annual-reports", response_model=AnnualReportsResponse)
async def get_company_annual_reports(
    ticker: str,
    session: AsyncSession = Depends(get_session),
):
    """Get SEC 10-K annual report filings with R&D analysis."""
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
