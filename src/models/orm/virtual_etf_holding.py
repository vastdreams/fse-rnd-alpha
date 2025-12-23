from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Index
from .base_model import BaseModel


class VirtualETFHolding(BaseModel):
    """Holdings for a Virtual ETF at a given rebalance date."""
    __tablename__ = "virtual_etf_holdings"

    etf_spec_id = Column(Integer, ForeignKey("virtual_etf_specs.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    rebalance_date = Column(Date, nullable=False, index=True)
    weight = Column(Float, nullable=False)
    factor_value = Column(Float, nullable=True)  # Factor value that led to inclusion
    
    __table_args__ = (
        Index("idx_etf_rebalance", "etf_spec_id", "rebalance_date"),
        {"comment": "Virtual ETF holdings at each rebalance"}
    )

