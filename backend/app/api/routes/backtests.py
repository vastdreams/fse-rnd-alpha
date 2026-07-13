"""
PATH: backend/app/api/routes/backtests.py
PURPOSE:
  - Backtest API endpoints
  - Run, list, and retrieve backtest results

ROLE IN ARCHITECTURE:
  - API route layer
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.routes.auth import require_operator


router = APIRouter()


class BacktestRequest(BaseModel):
    factor_id: str
    universe: List[str]
    start_year: int
    end_year: int
    rebalance_frequency: str = "annual"
    long_only: bool = True


class BacktestResult(BaseModel):
    id: str
    status: str
    factor_id: str
    start_year: int
    end_year: int
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    created_at: datetime


# In-memory store for demo (would use DB in production)
_backtests: dict = {}


@router.post("/run", response_model=BacktestResult)
async def run_backtest(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(require_operator),
):
    """Backtesting is intentionally unavailable until it is persisted and reproducible."""
    raise HTTPException(
        status_code=501,
        detail="Backtest execution is disabled in the public release.",
    )


@router.get("/", response_model=List[BacktestResult])
async def list_backtests(user: dict = Depends(require_operator)):
    """List all backtests."""
    return list(_backtests.values())


@router.get("/{backtest_id}", response_model=BacktestResult)
async def get_backtest(
    backtest_id: str,
    user: dict = Depends(require_operator),
):
    """Get backtest details."""
    if backtest_id not in _backtests:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return _backtests[backtest_id]


@router.get("/{backtest_id}/results")
async def get_backtest_results(
    backtest_id: str,
    user: dict = Depends(require_operator),
):
    """Get detailed backtest results including equity curve."""
    if backtest_id not in _backtests:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    # Mock equity curve data
    return {
        "equity_curve": [
            {"date": "2020-01-01", "value": 100},
            {"date": "2021-01-01", "value": 110},
            {"date": "2022-01-01", "value": 105},
            {"date": "2023-01-01", "value": 125},
        ],
        "holdings": [],
        "trades": [],
    }
