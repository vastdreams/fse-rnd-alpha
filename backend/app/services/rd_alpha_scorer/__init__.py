"""
PATH: backend/app/services/rd_alpha_scorer/__init__.py
PURPOSE: Re-export all public symbols so existing ``from app.services.rd_alpha_scorer import …`` works unchanged.
"""

from app.services.rd_alpha_scorer.scorer import RDAlphaScorer
from app.services.rd_alpha_scorer.data_classes import (
    RDAlphaScore,
    SectorWeight,
    SelectionMethodology,
    SP500_SECTOR_WEIGHTS,
    SECTOR_RD_CAPS,
)

__all__ = [
    "RDAlphaScorer",
    "RDAlphaScore",
    "SectorWeight",
    "SelectionMethodology",
    "SP500_SECTOR_WEIGHTS",
    "SECTOR_RD_CAPS",
]
