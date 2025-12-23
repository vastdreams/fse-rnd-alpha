from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class TextFactorRD(BaseModel):
    """R&D-specific text factors extracted from annual reports."""
    __tablename__ = "text_factor_rd"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, unique=True, index=True)
    
    # Basic counts and metrics
    rd_mentions_count = Column(Integer, default=0, nullable=True)
    research_mentions_count = Column(Integer, default=0, nullable=True)  # "Research" mentions separately
    development_mentions_count = Column(Integer, default=0, nullable=True)  # "Development" mentions
    innovation_mentions_count = Column(Integer, default=0, nullable=True)  # "Innovation" mentions
    rd_section_length_words = Column(Integer, default=0, nullable=True)
    
    # Sentiment and tone
    rd_tone_score = Column(Float, nullable=True)  # -1 to +1
    rd_sentiment_breakdown = Column(JSONB, nullable=True)  # {"positive": 0.3, "neutral": 0.5, "negative": 0.2}
    
    # Reporting style and structure
    rd_reporting_style = Column(String, nullable=True)  # quantitative_explicit, qualitative_only, boilerplate, unknown
    rd_sections_found = Column(JSONB, nullable=True)  # ["Item 1", "Item 7", "MD&A", etc.] where R&D mentioned
    rd_primary_section = Column(String, nullable=True)  # Main section where R&D is discussed
    
    # Topics and focus areas
    rd_focus_tags = Column(JSONB, nullable=True)  # ["AI", "Cloud", "Robotics", "Biotech"]
    rd_technology_areas = Column(JSONB, nullable=True)  # Detailed technology breakdown
    rd_geographic_mentions = Column(JSONB, nullable=True)  # Geographic locations mentioned with R&D
    
    # Quantitative data extracted
    rd_numbers_mentioned = Column(JSONB, nullable=True)  # [{"value": 1000000, "unit": "USD", "context": "R&D spending", "page": 45}]
    rd_percentages_mentioned = Column(JSONB, nullable=True)  # [{"value": 15.5, "unit": "%", "context": "R&D as % of revenue", "page": 45}]
    rd_trends_mentioned = Column(JSONB, nullable=True)  # [{"direction": "increasing", "context": "R&D investment", "page": 45}]
    
    # Narrative analysis
    rd_key_paragraphs = Column(JSONB, nullable=True)  # Array of {page, section, text, relevance_score}
    rd_strategic_priorities = Column(JSONB, nullable=True)  # Strategic priorities mentioned
    rd_competitive_mentions = Column(JSONB, nullable=True)  # Competitive positioning mentions
    
    # Verification and quality
    extraction_version = Column(String, default="rd_text_agent_v2", nullable=True)
    extraction_timestamp = Column(String, nullable=True)
    extraction_confidence = Column(Float, nullable=True)  # 0.0 to 1.0 - confidence in extraction quality
    verification_status = Column(String, nullable=True)  # verified, unverified, needs_review
    
    # Relationships
    company_year = relationship("CompanyYearCore", back_populates="text_factor_rd")

