from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class TextFactorGeneric(BaseModel):
    """Generic text factor table for ESG, gender, governance, etc."""
    __tablename__ = "text_factor_generic"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, index=True)
    factor_id = Column(String, nullable=False, index=True)  # e.g., "ESG_v1", "GENDER_v1", "GOV_v1"
    factor_name = Column(String, nullable=False)
    value_json = Column(JSONB, nullable=True)  # Full structured output from GPT agent
    data_source = Column(String, default="annual_report", nullable=True)
    quality_flag = Column(String, default="ok", nullable=True)
    extraction_version = Column(String, nullable=True)
    extraction_timestamp = Column(String, nullable=True)
    
    __table_args__ = (
        {"comment": "Generic text factors (ESG, gender, governance, etc.)"}
    )

