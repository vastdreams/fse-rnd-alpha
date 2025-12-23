"""
PATH: backend/app/api/routes/stats.py
PURPOSE:
  - Statistics and summary API endpoints
  - Database counts, unified filings view

ROLE IN ARCHITECTURE:
  - API route layer
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import (
    Company, CompanyYearCore, FinancialsCore, FinancialsRatios,
    TextFactorRD, AnnualReport, Price
)


router = APIRouter()


class StatsSummary(BaseModel):
    companies: dict
    company_years: dict
    annual_reports: dict
    text_chunks: dict
    prices: dict


class UnifiedFiling(BaseModel):
    ticker: str
    cik: str
    fiscal_year: int
    file_format: Optional[str] = None
    file_size_mb: Optional[float] = None
    extraction_status: Optional[str] = None
    report_path: Optional[str] = None
    company_year_id: int
    annual_report_id: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/summary", response_model=StatsSummary)
async def get_stats_summary(session: AsyncSession = Depends(get_session)):
    """Get comprehensive database statistics."""
    # Companies
    companies_total = await session.scalar(select(func.count(Company.id)))
    companies_with_financials = await session.scalar(
        select(func.count(func.distinct(CompanyYearCore.company_id)))
        .join(FinancialsCore, FinancialsCore.company_year_id == CompanyYearCore.id)
    )
    companies_with_ratios = await session.scalar(
        select(func.count(func.distinct(CompanyYearCore.company_id)))
        .join(FinancialsRatios, FinancialsRatios.company_year_id == CompanyYearCore.id)
    )
    companies_with_text = await session.scalar(
        select(func.count(func.distinct(CompanyYearCore.company_id)))
        .join(TextFactorRD, TextFactorRD.company_year_id == CompanyYearCore.id)
    )
    
    # Company years
    cy_total = await session.scalar(select(func.count(CompanyYearCore.id)))
    cy_with_financials = await session.scalar(
        select(func.count(CompanyYearCore.id))
        .join(FinancialsCore, FinancialsCore.company_year_id == CompanyYearCore.id)
    )
    cy_with_ratios = await session.scalar(
        select(func.count(CompanyYearCore.id))
        .join(FinancialsRatios, FinancialsRatios.company_year_id == CompanyYearCore.id)
    )
    cy_with_text = await session.scalar(
        select(func.count(CompanyYearCore.id))
        .join(TextFactorRD, TextFactorRD.company_year_id == CompanyYearCore.id)
    )
    
    # Annual reports
    ar_total = await session.scalar(select(func.count(AnnualReport.id)))
    ar_total_size = await session.scalar(select(func.sum(AnnualReport.file_size_bytes))) or 0
    
    # Prices
    prices_total = await session.scalar(select(func.count(Price.id)))
    prices_tickers = await session.scalar(select(func.count(func.distinct(Price.ticker))))
    
    return StatsSummary(
        companies={
            "total": companies_total or 0,
            "with_financials": companies_with_financials or 0,
            "with_ratios": companies_with_ratios or 0,
            "with_text_factors": companies_with_text or 0,
        },
        company_years={
            "total": cy_total or 0,
            "with_financials": cy_with_financials or 0,
            "with_ratios": cy_with_ratios or 0,
            "with_text_factors": cy_with_text or 0,
        },
        annual_reports={
            "total": ar_total or 0,
            "total_size_bytes": ar_total_size,
        },
        text_chunks={
            "total": 0,  # TextChunk model not migrated yet
        },
        prices={
            "total_records": prices_total or 0,
            "unique_tickers": prices_tickers or 0,
        },
    )


@router.get("/unified/filings", response_model=dict)
async def get_unified_filings(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(300, ge=1, le=1000),
):
    """Get unified filings view with all metadata."""
    result = await session.execute(
        select(
            CompanyYearCore.ticker,
            CompanyYearCore.cik,
            CompanyYearCore.fiscal_year,
            AnnualReport.file_format,
            AnnualReport.file_size_bytes,
            AnnualReport.extraction_status,
            CompanyYearCore.report_path,
            CompanyYearCore.id.label("company_year_id"),
            AnnualReport.id.label("annual_report_id"),
        )
        .outerjoin(AnnualReport, AnnualReport.company_year_id == CompanyYearCore.id)
        .order_by(CompanyYearCore.ticker, CompanyYearCore.fiscal_year.desc())
        .limit(limit)
    )
    
    rows = result.all()
    return {
        "rows": [
            {
                "ticker": row.ticker,
                "cik": row.cik,
                "fiscal_year": row.fiscal_year,
                "file_format": row.file_format,
                "file_size_mb": round(row.file_size_bytes / 1e6, 2) if row.file_size_bytes else None,
                "extraction_status": row.extraction_status,
                "report_path": row.report_path,
                "company_year_id": row.company_year_id,
                "annual_report_id": row.annual_report_id,
            }
            for row in rows
        ],
        "total": len(rows),
    }
