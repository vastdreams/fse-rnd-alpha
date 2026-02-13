"""
PATH: backend/app/api/routes/companies/__init__.py
PURPOSE: Assembles companies sub-routers into a single router
"""

from fastapi import APIRouter
from app.api.routes.companies.list_detail import router as _list_detail
from app.api.routes.companies.reports import router as _reports

router = APIRouter()
router.include_router(_list_detail)
router.include_router(_reports)
