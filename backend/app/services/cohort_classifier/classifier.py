# CohortClassifier: classifies companies into research cohorts based on data availability.
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cohort_classifier._coverage import CoverageAnalysisMixin
from app.services.cohort_classifier._classification import ClassificationMixin
from app.services.cohort_classifier._queries import QueryMixin


class CohortClassifier(CoverageAnalysisMixin, ClassificationMixin, QueryMixin):
    """Classifies companies into research cohorts based on data availability.
    Window Requirements: 5/10/20 consecutive years of R&D and return data.
    """

    def __init__(self, session: AsyncSession):
        self.session = session


async def classify_cohort_windows(session: AsyncSession) -> Dict:
    """Convenience function to classify 500 companies into rolling window cohorts."""
    classifier = CohortClassifier(session)
    return await classifier.classify_all_companies()
