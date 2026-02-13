"""
PATH: backend/app/api/routes/fmp/models.py
PURPOSE: Pydantic response models for FMP endpoints
"""

from typing import List, Optional
from pydantic import BaseModel


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
