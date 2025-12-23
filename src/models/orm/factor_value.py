from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class FactorValue(BaseModel):
    """Generic factor values table for cross-factor analytics."""
    __tablename__ = "factor_values"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, index=True)
    factor_id = Column(String, ForeignKey("factor_specs.factor_id"), nullable=False, index=True)
    factor_name = Column(String, nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_categorical = Column(String, nullable=True)
    value_json = Column(JSONB, nullable=True)  # Full structured output from GPT
    data_source = Column(String, nullable=True)  # xbrl, annual_report_text, etc.
    quality_flag = Column(String, default="ok", nullable=True)
    extraction_version = Column(String, nullable=True)
    extraction_timestamp = Column(String, nullable=True)
    
    # Relationships
    company_year = relationship("CompanyYearCore", back_populates="factor_values")

