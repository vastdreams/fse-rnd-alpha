from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class FactorSpec(BaseModel):
    """Factor specification registry (R&D_v1, ESG_v1, etc.)."""
    __tablename__ = "factor_specs"

    factor_id = Column(String, unique=True, nullable=False, index=True)  # e.g., "RND_v1"
    factor_family = Column(String, nullable=False)  # R&D, ESG, Gender, Governance
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    spec_json = Column(JSONB, nullable=True)  # Full FactorSpec JSON from config/factors.yml
    version = Column(String, default="v1", nullable=True)
    is_active = Column(String, default="true", nullable=True)

