from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class BacktestResult(BaseModel):
    __tablename__ = "backtest_results"

    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)
    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=True, index=True)
    spec_hash = Column(String, nullable=False, index=True)
    formation_year = Column(Integer, nullable=False, index=True)
    horizon_years = Column(Integer, nullable=False)
    industry = Column(String, nullable=True)
    bucket = Column(String, nullable=False)  # decile_1, decile_10, long_short, etc.
    mean_ret = Column(Float, nullable=False)
    t_stat = Column(Float, nullable=True)
    n = Column(Integer, nullable=False)
    stderr = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Relationships
    company_year = relationship("CompanyYearCore", back_populates="backtest_results")
