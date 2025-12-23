from sqlalchemy import Column, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class FinancialsRatios(BaseModel):
    """Derived financial ratios per company-year."""
    __tablename__ = "financials_ratios"

    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, unique=True, index=True)
    
    # Profitability
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_margin = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)  # Return on Equity
    roa = Column(Float, nullable=True)  # Return on Assets
    roic = Column(Float, nullable=True)  # Return on Invested Capital
    
    # Leverage & Capital Structure
    debt_to_equity = Column(Float, nullable=True)
    debt_to_assets = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)
    
    # Liquidity & Working Capital
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    working_capital = Column(Float, nullable=True)
    
    # Cash Flow & Quality of Earnings
    cfo_to_net_income = Column(Float, nullable=True)
    fcf = Column(Float, nullable=True)  # Free Cash Flow
    fcf_margin = Column(Float, nullable=True)
    dividend_coverage = Column(Float, nullable=True)
    cash_conversion = Column(Float, nullable=True)
    
    # Growth
    revenue_growth_yoy = Column(Float, nullable=True)
    eps_growth_yoy = Column(Float, nullable=True)
    fcf_growth_yoy = Column(Float, nullable=True)
    
    # R&D specific
    rd_intensity = Column(Float, nullable=True)  # R&D / Revenue
    rd_change_yoy = Column(Float, nullable=True)
    rd_3y_trend = Column(Float, nullable=True)
    
    # Relationships
    company_year = relationship("CompanyYearCore", back_populates="financials_ratios")

