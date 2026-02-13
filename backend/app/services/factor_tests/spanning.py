"""
PATH: backend/app/services/factor_tests/spanning.py
PURPOSE: FactorSpanningAnalyzer — main class combining all spanning test mixins
WHY: Single entry point preserving the original class interface
FLOW:
  ┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
  │ FF factor data │ -> │ OLS regression   │ -> │ Annual / monthly │
  │ (FactorData)   │    │ (Regression)     │    │ orchestration    │
  └───────────────┘    └──────────────────┘    └──────────────────┘
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.factor_tests.factor_data import FactorDataMixin
from app.services.factor_tests.spanning_regression import SpanningRegressionMixin
from app.services.factor_tests.spanning_annual import SpanningAnnualTestsMixin
from app.services.factor_tests.spanning_monthly import SpanningMonthlyTestsMixin


class FactorSpanningAnalyzer(
    FactorDataMixin,
    SpanningRegressionMixin,
    SpanningAnnualTestsMixin,
    SpanningMonthlyTestsMixin,
):
    """
    Tests if R&D premium is spanned by standard factor models.

    Methodology:
    1. Construct monthly or annual HML_RD returns (Q5 - Q1)
    2. Regress HML_RD on factor models:
       - FF3: MKT-RF, SMB, HML
       - FF3 + MOM: Add momentum factor
       - FF5: Add RMW, CMA
    3. Test if alpha (intercept) is significantly different from zero
    4. If alpha > 0 and significant: HML_RD is NOT spanned (distinct premium)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
