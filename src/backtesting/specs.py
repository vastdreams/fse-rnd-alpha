"""Backtest specification models."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class BacktestSpec(BaseModel):
    """Backtest specification."""
    factor_id: str  # e.g., "RND_v1"
    universe: List[str]  # List of tickers or "pilot_top10"
    start_year: int
    end_year: int
    formation_schedule: str = "annual"  # annual, quarterly
    holding_period_years: int = 1
    rebalance_frequency: str = "annual"  # annual, quarterly
    num_buckets: int = 10  # deciles
    weighting: str = "equal"  # equal, value_weighted
    neutralization: Optional[str] = None  # industry, sector, market_cap
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return self.model_dump()

