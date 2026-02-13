"""
PATH: backend/app/services/fmp_client/client.py
PURPOSE: Composed FMPClient class combining all mixins + convenience functions
WHY: Single import target that assembles base + bulk + individual capabilities
FLOW:
  ┌───────────────┐    ┌──────────────────┐    ┌───────────────┐
  │ FMPClientBase │ →  │ + Bulk + Indiv.  │ →  │ FMPClient     │
  └───────────────┘    └──────────────────┘    └───────────────┘
DEPENDENCIES:
  - base.py: connection management
  - bulk_mixin.py: bulk data methods
  - individual_mixin.py: per-symbol methods
"""

from typing import Optional
import logging

from app.services.fmp_client.base import FMPClientBase
from app.services.fmp_client.bulk_mixin import FMPBulkMixin
from app.services.fmp_client.individual_mixin import FMPIndividualMixin

logger = logging.getLogger(__name__)


class FMPClient(FMPClientBase, FMPBulkMixin, FMPIndividualMixin):
    """
    Async client for Financial Modeling Prep API.
    
    Provides methods for bulk data retrieval optimized for
    large-scale ingestion (500+ companies, 30+ years).
    
    Composed from:
    - FMPClientBase: connection management, _get() with retries
    - FMPBulkMixin: bulk financial statements, batch utilities
    - FMPIndividualMixin: per-symbol statements, prices, dividends
    """
    pass


# ============================================================================
# Convenience Functions
# ============================================================================

async def test_fmp_connection(api_key: str) -> bool:
    """
    Test FMP API connection.
    
    Args:
        api_key: FMP API key.
        
    Returns:
        True if connection successful.
    """
    async with FMPClient(api_key) as client:
        sp500 = await client.get_sp500_constituents()
        if sp500:
            logger.info(f"FMP connection OK. Found {len(sp500)} S&P 500 companies.")
            return True
        return False
