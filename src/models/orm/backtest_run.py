from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import BaseModel


class BacktestRun(BaseModel):
    """Metadata for each backtest execution."""
    __tablename__ = "backtest_runs"

    spec_hash = Column(String, nullable=False, index=True)
    factor_id = Column(String, nullable=False, index=True)
    universe = Column(String, nullable=True)  # top500, pilot_top50, custom
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    formation_schedule = Column(String, nullable=True)  # annual, quarterly
    holding_period_years = Column(Integer, nullable=True)
    spec_json = Column(JSONB, nullable=True)  # Full BacktestSpec JSON
    status = Column(String, default="pending", nullable=True)  # pending, running, completed, failed
    started_at = Column(Date, nullable=True)
    completed_at = Column(Date, nullable=True)

