"""
PATH: backend/app/api/routes/fmp/__init__.py
PURPOSE: Assembles FMP sub-routers into a single router
"""

from fastapi import APIRouter
from app.api.routes.fmp.overview import router as _overview
from app.api.routes.fmp.companies_endpoints import router as _companies
from app.api.routes.fmp.rd_analysis import router as _rd

router = APIRouter()
router.include_router(_overview)
router.include_router(_companies)
router.include_router(_rd)
