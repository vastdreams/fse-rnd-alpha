"""Enhanced R&D extraction schema with comprehensive structured data capture."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from decimal import Decimal


class RDNumericMention(BaseModel):
    """Numeric R&D value mentioned in text."""
    value: float
    unit: str = Field(default="USD", description="Currency or unit (USD, millions, percentage, etc.)")
    context: str = Field(description="Context of the number (e.g., 'R&D spending', 'R&D as % of revenue')")
    page: Optional[int] = None
    section: Optional[str] = None
    year_reference: Optional[str] = None  # "2024", "prior year", "three-year average", etc.
    is_comparative: bool = Field(default=False, description="Whether this is a comparison to another period")


class RDTrendMention(BaseModel):
    """Trend or directional mention about R&D."""
    direction: Literal["increasing", "decreasing", "stable", "volatile", "accelerating", "decelerating"]
    context: str = Field(description="What is trending (e.g., 'R&D investment', 'innovation pipeline')")
    page: Optional[int] = None
    section: Optional[str] = None
    magnitude: Optional[str] = None  # "significantly", "moderately", "slightly"
    timeframe: Optional[str] = None  # "over the past year", "in Q4", etc.


class RDTechnologyArea(BaseModel):
    """Technology area or research focus mentioned."""
    name: str = Field(description="Technology area name (e.g., 'Artificial Intelligence', 'Cloud Computing')")
    mentions: int = Field(default=1, description="Number of times mentioned")
    context: List[str] = Field(default_factory=list, description="Contexts where mentioned")
    pages: List[int] = Field(default_factory=list, description="Pages where mentioned")


class RDKeyParagraph(BaseModel):
    """Key R&D paragraph with enhanced metadata."""
    page: Optional[int] = None
    section: Optional[str] = None
    section_title: Optional[str] = None
    text: str = Field(description="Paragraph text (max 1000 chars)")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score for R&D analysis")
    contains_numbers: bool = Field(default=False, description="Whether paragraph contains numeric R&D data")
    contains_strategy: bool = Field(default=False, description="Whether paragraph discusses R&D strategy")
    sentiment: Literal["positive", "neutral", "negative"] = Field(default="neutral")


class RDChunkSignalsV2(BaseModel):
    """Enhanced R&D signals extracted from a single chunk."""
    chunk_id: str
    factor_family: str = "R&D"
    
    # Mention counts (comprehensive)
    rd_mentions: int = 0
    research_mentions: int = 0  # "Research" specifically
    development_mentions: int = 0  # "Development" specifically
    innovation_mentions: int = 0  # "Innovation" mentions
    r_and_d_mentions: int = 0  # "R&D" or "R and D" mentions
    
    # Sentences and text
    rd_sentences: List[Dict[str, Any]] = Field(default_factory=list, description="R&D-related sentences with metadata")
    
    # Topics and technology areas
    topics: List[str] = Field(default_factory=list, description="High-level topics (e.g., 'AI', 'Cloud')")
    technology_areas: List[RDTechnologyArea] = Field(default_factory=list, description="Detailed technology areas")
    
    # Quantitative data
    explicit_numbers: List[RDNumericMention] = Field(default_factory=list, description="Numeric R&D values")
    percentages: List[RDNumericMention] = Field(default_factory=list, description="Percentage values related to R&D")
    trends: List[RDTrendMention] = Field(default_factory=list, description="Trend mentions")
    
    # Sentiment and tone
    tone_score: float = Field(default=0.0, ge=-1.0, le=1.0, description="Tone score: -1 (defensive) to +1 (opportunity-focused)")
    sentiment_breakdown: Dict[str, float] = Field(default_factory=dict, description="Sentiment breakdown: positive, neutral, negative")
    
    # Section and location
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    
    # Strategic context
    strategic_priorities: List[str] = Field(default_factory=list, description="Strategic priorities mentioned")
    competitive_mentions: List[str] = Field(default_factory=list, description="Competitive positioning mentions")
    
    # Quality indicators
    has_quantitative_data: bool = Field(default=False, description="Whether chunk contains quantitative R&D data")
    has_qualitative_narrative: bool = Field(default=False, description="Whether chunk contains qualitative R&D narrative")
    is_boilerplate: bool = Field(default=False, description="Whether chunk appears to be boilerplate text")


class RNDCompanyYearFactorsV2(BaseModel):
    """Enhanced aggregated R&D factors for a company-year."""
    # Comprehensive mention counts
    rd_mentions_count: int = 0
    research_mentions_count: int = 0
    development_mentions_count: int = 0
    innovation_mentions_count: int = 0
    r_and_d_mentions_count: int = 0
    
    # Text metrics
    rd_section_length_words: int = 0
    total_rd_paragraphs: int = 0
    
    # Sentiment and tone
    rd_tone_score: float = 0.0
    sentiment_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Reporting style
    rd_reporting_style: str = "unknown"
    rd_sections_found: List[str] = Field(default_factory=list)
    rd_primary_section: Optional[str] = None
    
    # Topics and technology
    rd_focus_tags: List[str] = Field(default_factory=list)
    rd_technology_areas: List[RDTechnologyArea] = Field(default_factory=list)
    rd_geographic_mentions: List[str] = Field(default_factory=list)
    
    # Quantitative data
    rd_numbers_mentioned: List[RDNumericMention] = Field(default_factory=list)
    rd_percentages_mentioned: List[RDNumericMention] = Field(default_factory=list)
    rd_trends_mentioned: List[RDTrendMention] = Field(default_factory=list)
    
    # Narrative
    rd_key_paragraphs: List[RDKeyParagraph] = Field(default_factory=list)
    rd_strategic_priorities: List[str] = Field(default_factory=list)
    rd_competitive_mentions: List[str] = Field(default_factory=list)
    
    # Quality
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: str = "unverified"

