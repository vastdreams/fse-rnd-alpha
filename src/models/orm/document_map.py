from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class DocumentMap(BaseModel):
    """Structured document map with sections and chunks metadata."""
    __tablename__ = "document_maps"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, index=True)
    document_structure = Column(JSONB, nullable=True)  # Full DocumentMap JSON structure
    sections_count = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    extraction_version = Column(String, default="v1", nullable=True)

