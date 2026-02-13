"""
PATH: backend/app/api/routes/donations/__init__.py
PURPOSE: Assembles donations sub-routers and re-exports public helpers
"""

from fastapi import APIRouter
from app.api.routes.donations.endpoints import router as _endpoints

router = APIRouter()
router.include_router(_endpoints)

# Re-export function used by admin routes
from app.api.routes.donations.helpers import get_all_donations  # noqa: E402, F401
