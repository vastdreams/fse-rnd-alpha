# MarketForecaster: S&P 500 consensus forecasts from major investment banks.
import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.services.market_forecasts.data import (
    SP500_CONSENSUS_FORECASTS, FORECAST_SOURCES, SP500_HISTORICAL_RETURNS,
)
from app.services.market_forecasts.models import (
    ForecastPoint, ForecastSource, SP500ForecastResponse,
)

logger = logging.getLogger(__name__)


class MarketForecaster:
    """Provides S&P 500 consensus forecasts from major investment banks.
    Uses static forecasts updated periodically (not real-time). No API dependencies.
    """

    DISCLAIMER = (
        "Forecasts are consensus estimates from major investment banks and are "
        "provided for informational purposes only. Past performance does not "
        "guarantee future results. Actual market returns may differ significantly."
    )

    def __init__(self):
        self.current_year = datetime.now().year

    def get_sp500_forecast(
        self,
        years_forward: int = 10,
        include_historical: bool = True
    ) -> SP500ForecastResponse:
        """Get S&P 500 forecasts with full attribution."""
        forecasts = []
        start_year = self.current_year - 3 if include_historical else self.current_year
        end_year = self.current_year + years_forward
        for year in range(start_year, end_year + 1):
            if year in SP500_CONSENSUS_FORECASTS:
                data = SP500_CONSENSUS_FORECASTS[year]
                if data.get("type") == "actual":
                    level = data.get("level", 0)
                    return_pct = data.get("return_pct", 0)
                    forecasts.append(ForecastPoint(
                        year=year,
                        level_low=level, level_mid=level, level_high=level,
                        return_low=return_pct, return_mid=return_pct, return_high=return_pct,
                        is_forecast=False,
                        source=data.get("source", "S&P Dow Jones Indices"),
                        notes=None,
                    ))
                else:
                    forecasts.append(ForecastPoint(
                        year=year,
                        level_low=data.get("low", 0),
                        level_mid=data.get("mid", 0),
                        level_high=data.get("high", 0),
                        return_low=data.get("return_low", 0),
                        return_mid=data.get("return_mid", 0),
                        return_high=data.get("return_high", 0),
                        is_forecast=True,
                        source=data.get("source", "Consensus"),
                        notes=data.get("notes"),
                    ))
        base_data = SP500_CONSENSUS_FORECASTS.get(self.current_year, {})
        base_level = base_data.get("level", base_data.get("mid", 5880))
        return SP500ForecastResponse(
            forecasts=forecasts,
            sources=self.get_forecast_sources(),
            base_year=self.current_year,
            base_level=base_level,
            methodology_summary=(
                "Consensus forecasts are averaged from Goldman Sachs, JP Morgan, "
                "Morgan Stanley, and Bank of America research. Low/mid/high scenarios "
                "represent bear/base/bull case projections."
            ),
            last_updated="2024-12-15",
            disclaimer=self.DISCLAIMER,
        )

    def get_forecast_sources(self) -> List[ForecastSource]:
        """Get attribution for all forecast sources."""
        return [ForecastSource(**source) for source in FORECAST_SOURCES]

    def get_historical_return(self, year: int) -> Optional[float]:
        """Get historical S&P 500 return for a specific year."""
        return SP500_HISTORICAL_RETURNS.get(year)

    def get_historical_returns(
        self,
        start_year: int = 2000,
        end_year: Optional[int] = None
    ) -> Dict[int, float]:
        """Get historical returns for a range of years."""
        end = end_year or self.current_year
        return {
            year: return_pct
            for year, return_pct in SP500_HISTORICAL_RETURNS.items()
            if start_year <= year <= end
        }

    def calculate_cumulative_value(
        self,
        start_year: int,
        end_year: int,
        initial_value: float = 100.0,
        use_forecast: bool = True
    ) -> List[Dict]:
        """Calculate cumulative portfolio value over time using actuals + forecasts."""
        results = []
        current_value = initial_value
        for year in range(start_year, end_year + 1):
            if year in SP500_HISTORICAL_RETURNS:
                return_pct = SP500_HISTORICAL_RETURNS[year]
                is_forecast = False
            elif use_forecast and year in SP500_CONSENSUS_FORECASTS:
                data = SP500_CONSENSUS_FORECASTS[year]
                if data.get("type") == "forecast":
                    return_pct = data.get("return_mid", 8.0)
                    is_forecast = True
                else:
                    return_pct = data.get("return_pct", 0)
                    is_forecast = False
            else:
                return_pct = 8.0
                is_forecast = True
            current_value = current_value * (1 + return_pct / 100)
            results.append({
                "year": year,
                "value": round(current_value, 2),
                "return_pct": return_pct,
                "is_forecast": is_forecast,
            })
        return results
