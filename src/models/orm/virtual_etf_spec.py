from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class VirtualETFSpec(BaseModel):
    """Virtual ETF specification from factor rules and constraints."""
    __tablename__ = "virtual_etf_specs"

    etf_name = Column(String, nullable=False, unique=True, index=True)
    factor_id = Column(String, nullable=False, index=True)
    universe = Column(String, nullable=True)  # top500, pilot_top50, custom
    rebalance_frequency = Column(String, default="annual", nullable=True)  # annual, quarterly, monthly
    max_holdings = Column(Integer, nullable=True)
    min_weight = Column(Float, nullable=True)
    max_weight = Column(Float, nullable=True)
    spec_json = Column(JSONB, nullable=True)  # Full VirtualETFSpec JSON
    is_active = Column(String, default="true", nullable=True)

