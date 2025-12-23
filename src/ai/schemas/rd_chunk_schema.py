"""R&D chunk-level extraction schema."""
from pydantic import BaseModel
from typing import List, Optional


class RDSentence(BaseModel):
    """R&D-related sentence with page reference."""
    text: str
    page: Optional[int] = None


class RDChunkSignals(BaseModel):
    """R&D signals extracted from a single chunk."""
    chunk_id: str
    factor_family: str = "R&D"
    signals: dict = {
        "rd_mentions": 0,
        "rd_sentences": [],
        "topics": [],
        "tone_score": 0.0,  # -1 to +1
        "explicit_numbers": [],
    }

