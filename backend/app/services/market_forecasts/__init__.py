# Market forecasts package: S&P 500 consensus forecasts from major investment banks.
from app.services.market_forecasts.data import (
    SP500_CONSENSUS_FORECASTS,
    FORECAST_SOURCES,
    SP500_HISTORICAL_RETURNS,
)
from app.services.market_forecasts.models import (
    ForecastPoint,
    ForecastSource,
    SP500ForecastResponse,
)
from app.services.market_forecasts.forecaster import MarketForecaster

__all__ = [
    "SP500_CONSENSUS_FORECASTS",
    "FORECAST_SOURCES",
    "SP500_HISTORICAL_RETURNS",
    "ForecastPoint",
    "ForecastSource",
    "SP500ForecastResponse",
    "MarketForecaster",
]
