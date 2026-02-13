# MomentumCalculator: momentum factor based on Paper 3 (prior 3-year excess returns).
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.momentum_service._compute import ComputeMixin
from app.services.momentum_service._persistence import PersistenceMixin


class MomentumCalculator(ComputeMixin, PersistenceMixin):
    """Calculates momentum factor based on Paper 3 findings.
    Formula: Momentum Factor = 1 + (excess_return_3yr * 0.1), capped [0.5, 2.0].
    Paper 3 finding: 'R&D premium persists over time (~10% annual, t-stat ~3.4)'.
    """

    def __init__(self, session: AsyncSession, *, data_tier: str = "tier1"):
        self.session = session
        self.data_tier = data_tier
        self._market_returns_cache: Dict[int, float] = {}
