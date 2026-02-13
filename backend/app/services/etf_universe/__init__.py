"""
PATH: backend/app/services/etf_universe/__init__.py
PURPOSE: Re-export all public symbols for backward-compatible import path
WHY: Consumers import from app.services.etf_universe — this preserves that contract
"""

from app.services.etf_universe.data_classes import (
    EligibilityMode,
    EligibilityResult,
    GateResult,
    MIN_LISTING_AGE_DAYS,
    MIN_LIQUIDITY_TRADING_DAYS,
    MIN_LIQUIDITY_DOLLAR_VOLUME,
    MIN_REVENUE,
)
from app.services.etf_universe.gates_mixin import ETFUniverseGatesMixin
from app.services.etf_universe.builder import (
    ETFUniverseBuilder,
    get_eligible_universe,
)

__all__ = [
    # Data classes & enums
    "EligibilityMode",
    "EligibilityResult",
    "GateResult",
    # Constants
    "MIN_LISTING_AGE_DAYS",
    "MIN_LIQUIDITY_TRADING_DAYS",
    "MIN_LIQUIDITY_DOLLAR_VOLUME",
    "MIN_REVENUE",
    # Mixin (for extension)
    "ETFUniverseGatesMixin",
    # Builder
    "ETFUniverseBuilder",
    "get_eligible_universe",
]
