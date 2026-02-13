"""
PATH: backend/app/api/routes/companies/models.py
PURPOSE: Pydantic response models for company endpoints
"""

from typing import List, Optional
from pydantic import BaseModel


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
