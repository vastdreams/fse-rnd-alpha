"""
PATH: backend/app/api/routes/portfolio/models.py
PURPOSE: Pydantic response models shared across portfolio route modules.
WHY: Avoids circular imports and keeps model definitions in one place.
"""

from typing import List
from pydantic import BaseModel


class HoldingResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    weight: float
    rd_intensity: float


class PerformanceResponse(BaseModel):
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float


class YearlyDataResponse(BaseModel):
    year: int
    portfolio_return: float
    benchmark_return: float
    excess_return: float


class BacktestResponse(BaseModel):
    period: str
    holdings: List[dict]
    portfolio_performance: PerformanceResponse
    benchmark_performance: PerformanceResponse
    excess_return: float
    yearly_data: List[YearlyDataResponse]


class SectorAllocationResponse(BaseModel):
    sector: str
    weight: float


class WindowResponse(BaseModel):
    window_id: str
    window_type: str
    start_year: int
    end_year: int
    label: str
