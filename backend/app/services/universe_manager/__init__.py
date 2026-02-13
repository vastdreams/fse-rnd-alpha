"""
PATH: backend/app/services/universe_manager/__init__.py
PURPOSE: Re-export all public symbols for backward-compatible import path
WHY: Consumers import from app.services.universe_manager — this preserves that contract
"""

from app.services.universe_manager.definitions import (
    UNIVERSE_DEFINITIONS,
    UNIVERSE_SECTOR_WEIGHTS,
    UniverseInfo,
    UniverseSectorBreakdown,
    UniverseCompany,
)
from app.services.universe_manager.queries_mixin import UniverseQueriesMixin
from app.services.universe_manager.manager import (
    UniverseManager,
    get_supported_universes,
    get_universe_config,
)

__all__ = [
    # Definitions & data classes
    "UNIVERSE_DEFINITIONS",
    "UNIVERSE_SECTOR_WEIGHTS",
    "UniverseInfo",
    "UniverseSectorBreakdown",
    "UniverseCompany",
    # Mixin (for extension)
    "UniverseQueriesMixin",
    # Manager
    "UniverseManager",
    "get_supported_universes",
    "get_universe_config",
]
