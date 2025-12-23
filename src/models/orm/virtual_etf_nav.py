from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Index
from .base_model import BaseModel


class VirtualETFNav(BaseModel):
    """NAV/time series for each Virtual ETF."""
    __tablename__ = "virtual_etf_navs"

    etf_spec_id = Column(Integer, ForeignKey("virtual_etf_specs.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    nav = Column(Float, nullable=False)
    total_return = Column(Float, nullable=True)
    
    __table_args__ = (
        Index("idx_etf_date", "etf_spec_id", "date"),
        {"comment": "Virtual ETF NAV and performance time series"}
    )

