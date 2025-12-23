from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class TextChunk(BaseModel):
    """Chunked text segments from annual reports with section and page metadata."""
    __tablename__ = "text_chunks"

    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)
    chunk_id = Column(String, nullable=False, index=True)  # e.g., "sec-mdna-1"
    section_id = Column(String, nullable=True, index=True)  # e.g., "sec-mdna"
    section_title = Column(String, nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    text_content = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # Relationships
    annual_report = relationship("AnnualReport", back_populates="text_chunks")

