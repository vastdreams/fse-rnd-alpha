from sqlalchemy import Column, String, Integer, Date, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class AnnualReport(BaseModel):
    """Annual report filing metadata and file paths."""
    __tablename__ = "annual_reports"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, unique=True, index=True)
    cik = Column(String, nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    filing_date = Column(Date, nullable=True)
    accession_id = Column(String, nullable=True, index=True)
    form_type = Column(String, default="10-K", nullable=True)  # 10-K, 10-Q, 20-F, etc.
    file_path = Column(String, nullable=True)  # Path to raw HTML/PDF
    file_hash = Column(String, nullable=True)  # SHA256 hash of file
    file_size_bytes = Column(Integer, nullable=True)
    file_format = Column(String, nullable=True)  # html, pdf, txt
    extraction_status = Column(String, default="pending", nullable=True)  # pending, extracted, failed, partial
    
    # Enhanced metadata from SEC filing
    document_count = Column(Integer, nullable=True)  # Number of documents in filing
    has_xbrl = Column(Boolean, default=False, nullable=True)  # Whether filing includes XBRL
    xbrl_url = Column(String, nullable=True)  # URL to XBRL instance document
    sections_found = Column(JSONB, nullable=True)  # List of sections found: ["Item 1", "Item 7", "Item 8", etc.]
    total_pages = Column(Integer, nullable=True)  # Total pages in document
    word_count = Column(Integer, nullable=True)  # Total word count
    
    # Relationships
    company_year = relationship("CompanyYearCore", back_populates="annual_report")
    text_chunks = relationship("TextChunk", back_populates="annual_report")

