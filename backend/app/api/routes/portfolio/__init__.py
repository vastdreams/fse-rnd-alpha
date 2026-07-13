"""
PATH: backend/app/api/routes/portfolio/__init__.py
PURPOSE: Merge sub-routers into a single ``router`` so ``main.py`` can still do ``portfolio.router``.
"""

from fastapi import APIRouter, Depends

from app.api.routes.auth import get_current_user
from app.api.routes.portfolio.core_endpoints import router as _core
from app.api.routes.portfolio.transparency_endpoints import router as _transparency
from app.api.routes.portfolio.universe_endpoints import router as _universe

# The legacy ETF/research endpoints expose derived portfolio data. Keep their
# response shape intact, but require the same durable authenticated account as
# the rest of the active investor surface rather than relying on a frontend
# route guard.
router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(_core)
router.include_router(_transparency)
router.include_router(_universe)

# Re-export response models for any direct importers
from app.api.routes.portfolio.models import (  # noqa: F401, E402
    HoldingResponse,
    PerformanceResponse,
    YearlyDataResponse,
    BacktestResponse,
    SectorAllocationResponse,
    WindowResponse,
)

__all__ = [
    "router",
    "HoldingResponse",
    "PerformanceResponse",
    "YearlyDataResponse",
    "BacktestResponse",
    "SectorAllocationResponse",
    "WindowResponse",
]
