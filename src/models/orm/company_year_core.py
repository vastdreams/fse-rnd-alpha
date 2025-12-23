from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class CompanyYearCore(BaseModel):
    """Core company-year record linking all data for a given fiscal year."""
    __tablename__ = "company_year_core"

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    cik = Column(String, nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    filing_date = Column(Date, nullable=True)
    sec_accession_id = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    country = Column(String, default="US", nullable=True)
    report_path = Column(String, nullable=True)
    report_hash = Column(String, nullable=True)
    data_version = Column(String, default="v1", nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="company_years")
    financials_core = relationship("FinancialsCore", back_populates="company_year", uselist=False)
    financials_ratios = relationship("FinancialsRatios", back_populates="company_year", uselist=False)
    annual_report = relationship("AnnualReport", back_populates="company_year", uselist=False)
    text_factor_rd = relationship("TextFactorRD", back_populates="company_year", uselist=False)
    factor_values = relationship("FactorValue", back_populates="company_year")
    backtest_results = relationship("BacktestResult", back_populates="company_year")
    
    __table_args__ = (
        {"comment": "Core company-year record linking all financial and factor data"}
    )

