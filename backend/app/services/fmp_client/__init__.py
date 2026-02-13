"""
PATH: backend/app/services/fmp_client/__init__.py
PURPOSE: Re-export all public symbols for backward-compatible import path
WHY: Consumers import from app.services.fmp_client — this preserves that contract
"""

from app.services.fmp_client.base import FMPClientBase, FMP_BASE_URL, FMP_API_KEY
from app.services.fmp_client.bulk_mixin import FMPBulkMixin
from app.services.fmp_client.individual_mixin import FMPIndividualMixin
from app.services.fmp_client.client import FMPClient, test_fmp_connection

__all__ = [
    # Base
    "FMPClientBase",
    "FMP_BASE_URL",
    "FMP_API_KEY",
    # Mixins
    "FMPBulkMixin",
    "FMPIndividualMixin",
    # Composed client
    "FMPClient",
    "test_fmp_connection",
]
