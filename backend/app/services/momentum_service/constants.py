# Constants and data classes for momentum factor calculation (Paper 3 research).
from dataclasses import dataclass

# Momentum sensitivity: how much weight to give excess returns
MOMENTUM_SENSITIVITY = 0.1  # 10% of excess return added to base factor

# Caps to prevent extreme values
MIN_MOMENTUM_FACTOR = 0.5
MAX_MOMENTUM_FACTOR = 2.0

# Years of prior returns for momentum calculation
MOMENTUM_LOOKBACK_YEARS = 3


@dataclass
class MomentumResult:
    """Result of momentum calculation."""
    symbol: str
    as_of_year: int
    cumulative_return_3yr: float
    benchmark_return_3yr: float
    excess_return_3yr: float
    annualized_return: float
    annualized_excess: float
    momentum_factor: float
    years_available: int
