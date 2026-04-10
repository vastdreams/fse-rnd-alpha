"""
PATH: backend/app/api/routes/research/__init__.py
PURPOSE: Assemble all research sub-routers into a single router.
"""
from fastapi import APIRouter

from app.api.routes.research.schemas import *  # noqa: F401,F403
from app.api.routes.research.cohort import router as cohort_router
from app.api.routes.research.rolling_quintile import router as rolling_router
from app.api.routes.research.statistical_analysis import router as stats_router
from app.api.routes.research.publication import router as pub_router
from app.api.routes.research.computation import router as compute_router
from app.api.routes.research.exports import router as export_router
from app.api.routes.research.transaction_costs import router as txn_router
from app.api.routes.research.fama_macbeth_routes import router as fm_router
from app.api.routes.research.robustness import router as robust_router
from app.api.routes.research.advanced_analysis import router as advanced_router
from app.api.routes.research.top_journal import router as journal_router
from app.api.routes.research.pnl_efficiency import router as pnl_router
from app.api.routes.research.pnl_factor_tests import router as pnl_factor_tests_router

router = APIRouter()
router.include_router(cohort_router)
router.include_router(rolling_router)
router.include_router(stats_router)
router.include_router(pub_router)
router.include_router(compute_router)
router.include_router(export_router)
router.include_router(txn_router)
router.include_router(fm_router)
router.include_router(robust_router)
router.include_router(advanced_router)
router.include_router(journal_router)
router.include_router(pnl_router)
router.include_router(pnl_factor_tests_router)
