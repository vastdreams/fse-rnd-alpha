# Data class for July-June return calculation results.
from dataclasses import dataclass


@dataclass
class JulyJuneReturnResult:
    """Result of July-June return calculation."""
    symbol: str
    formation_year: int
    july_start_price: float
    june_end_price: float
    total_return: float
    annualized_return: float
    volatility: float
    trading_days: int
    price_mode: str
    adj_close_days: int
    close_fallback_days: int
    dividend_days: int
