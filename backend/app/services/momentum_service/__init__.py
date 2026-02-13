# Momentum service package: 3-year prior excess returns for momentum factor scoring.
from app.services.momentum_service.constants import (
    MOMENTUM_SENSITIVITY,
    MIN_MOMENTUM_FACTOR,
    MAX_MOMENTUM_FACTOR,
    MOMENTUM_LOOKBACK_YEARS,
    MomentumResult,
)
from app.services.momentum_service.calculator import MomentumCalculator

__all__ = [
    "MOMENTUM_SENSITIVITY",
    "MIN_MOMENTUM_FACTOR",
    "MAX_MOMENTUM_FACTOR",
    "MOMENTUM_LOOKBACK_YEARS",
    "MomentumResult",
    "MomentumCalculator",
]
