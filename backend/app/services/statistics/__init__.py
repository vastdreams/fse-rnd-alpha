"""
PATH: backend/app/services/statistics/__init__.py
PURPOSE: Facade — compose all mixin classes into the public StatisticalAnalyzer.
WHY: Allows external code to continue importing from `app.services.statistics`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.statistics.models import (
    AnovaTestResult,
    TTestResult,
    HACResult,
    RegressionResult,
)
from app.services.statistics.anova import AnovaMixin
from app.services.statistics.tests import TestsMixin
from app.services.statistics.annual_hml import AnnualHMLMixin
from app.services.statistics.delisting import DelistingMixin
from app.services.statistics.regression import RegressionMixin
from app.services.statistics.fama_macbeth import FamaMacBethMixin
from app.services.statistics.double_sort import DoubleSortMixin
from app.services.statistics.fama_macbeth_monthly import FamaMacBethMonthlyMixin


class StatisticalAnalyzer(
    AnovaMixin,
    TestsMixin,
    AnnualHMLMixin,
    DelistingMixin,
    RegressionMixin,
    FamaMacBethMixin,
    DoubleSortMixin,
    FamaMacBethMonthlyMixin,
):
    """
    Statistical analysis service for R&D research.
    
    Provides:
    - One-way ANOVA for quintile comparisons
    - T-tests for high vs low R&D portfolios
    - Fama-French + R&D factor regression
    - Descriptive statistics
    
    PUBLICATION FIX (Dec 2025):
    - Added use_july_june parameter for versioning
    - Results now tagged with return_convention and data_tier
    """
    
    def __init__(self, session: AsyncSession, use_july_june: bool = True, data_tier: str = "tier1"):
        self.session = session
        self.use_july_june = use_july_june
        self.data_tier = data_tier


__all__ = [
    "StatisticalAnalyzer",
    "AnovaTestResult",
    "TTestResult",
    "HACResult",
    "RegressionResult",
]
