"""R&D company-year aggregated schema."""
from pydantic import BaseModel
from typing import List, Optional, Dict


class KeyParagraph(BaseModel):
    """Key R&D paragraph with metadata."""
    page: Optional[int] = None
    section: Optional[str] = None
    text: str


class RNDCompanyYearFactors(BaseModel):
    """Aggregated R&D factors for a company-year."""
    rd_mentions_count: int = 0
    rd_section_length_words: int = 0
    rd_tone_score: float = 0.0  # -1 to +1
    rd_reporting_style: str = "unknown"  # quantitative_explicit, qualitative_only, boilerplate, unknown
    rd_focus_tags: List[str] = []
    rd_key_paragraphs: List[KeyParagraph] = []

