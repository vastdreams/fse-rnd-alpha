# Return calculator package: July-June returns per Fama-French convention using FMP daily prices.
from app.services.return_calculator.constants import (
    TRADING_DAYS_PER_YEAR,
    SQRT_252,
    MIN_TRADING_DAYS,
    MIN_TRADING_DAYS_REMOVED_IN_WINDOW,
    PRICE_MODE_TOTAL_RETURN_DIVIDENDS,
    PRICE_MODE_PRICE_ONLY,
    PRICE_MODE_ADJ_CLOSE_ONLY,
    PRICE_MODE_ADJ_CLOSE_FALLBACK_CLOSE,
)
from app.services.return_calculator.models import JulyJuneReturnResult
from app.services.return_calculator.calculator import JulyJuneReturnCalculator

__all__ = [
    "TRADING_DAYS_PER_YEAR",
    "SQRT_252",
    "MIN_TRADING_DAYS",
    "MIN_TRADING_DAYS_REMOVED_IN_WINDOW",
    "PRICE_MODE_TOTAL_RETURN_DIVIDENDS",
    "PRICE_MODE_PRICE_ONLY",
    "PRICE_MODE_ADJ_CLOSE_ONLY",
    "PRICE_MODE_ADJ_CLOSE_FALLBACK_CLOSE",
    "JulyJuneReturnResult",
    "JulyJuneReturnCalculator",
]
