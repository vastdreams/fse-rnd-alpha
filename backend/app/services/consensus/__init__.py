"""
PATH: backend/app/services/consensus/__init__.py
PURPOSE: Provider-neutral licensed consensus layer (PIT snapshots).
"""

from app.services.consensus.base import (
    ConsensusEstimate,
    ConsensusUnavailable,
    NormalizedConsensus,
    PriceTargetSummary,
)
from app.services.consensus.service import (
    fetch_and_store_consensus,
    latest_stored_consensus,
)

__all__ = [
    "ConsensusEstimate",
    "ConsensusUnavailable",
    "NormalizedConsensus",
    "PriceTargetSummary",
    "fetch_and_store_consensus",
    "latest_stored_consensus",
]
