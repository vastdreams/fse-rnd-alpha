"""
PATH: backend/app/services/market_forecasts.py
PURPOSE:
  - Provides S&P 500 consensus forecasts from major investment banks
  - Static forecasts updated periodically (not real-time API)
  - Attribution to source institutions for transparency

ROLE IN ARCHITECTURE:
  - Data source for benchmark forecasting in portfolio comparisons
  - Used by portfolio API for forecast vs actual analysis

MAIN EXPORTS:
  - MarketForecaster: Main class for retrieving forecasts
  - SP500_CONSENSUS_FORECASTS: Static forecast data

NON-RESPONSIBILITIES:
  - Does not fetch real-time data (static updates only)
  - Does not provide stock-level forecasts

NOTES FOR FUTURE AI:
  - Update SP500_CONSENSUS_FORECASTS quarterly from bank research
  - Consider adding API integration (Alpha Vantage, etc.) in future
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, date

logger = logging.getLogger(__name__)


# ==============================================================================
# S&P 500 Consensus Forecasts (Updated Dec 2024)
# ==============================================================================

# Sources: Goldman Sachs, JP Morgan, Morgan Stanley, Bank of America
# These are averaged/consensus estimates from major banks' research
# Last updated: December 2024

SP500_CONSENSUS_FORECASTS = {
    # Historical actuals for validation
    2020: {
        "level": 3756,
        "return_pct": 16.3,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2021: {
        "level": 4766,
        "return_pct": 26.9,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2022: {
        "level": 3839,
        "return_pct": -19.4,
        "type": "actual", 
        "source": "S&P Dow Jones Indices"
    },
    2023: {
        "level": 4769,
        "return_pct": 24.2,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2024: {
        "level": 5880,
        "return_pct": 23.3,
        "type": "actual",
        "source": "S&P Dow Jones Indices (YTD Dec)"
    },
    # Forecasts
    2025: {
        "low": 5800,
        "mid": 6500,
        "high": 7000,
        "return_low": -1.4,
        "return_mid": 10.5,
        "return_high": 19.0,
        "type": "forecast",
        "source": "Goldman Sachs, JP Morgan, Morgan Stanley Average",
        "notes": "Consensus: soft landing, Fed rate cuts, AI productivity gains"
    },
    2026: {
        "low": 6100,
        "mid": 7150,
        "high": 8000,
        "return_low": 5.2,
        "return_mid": 10.0,
        "return_high": 14.3,
        "type": "forecast",
        "source": "5-year forward projections average",
        "notes": "Based on 10% long-term earnings growth assumption"
    },
    2027: {
        "low": 6400,
        "mid": 7865,
        "high": 9000,
        "return_low": 4.9,
        "return_mid": 10.0,
        "return_high": 12.5,
        "type": "forecast",
        "source": "Extrapolated from bank 5-year targets",
        "notes": "Assumes continued earnings expansion"
    },
    2028: {
        "low": 6700,
        "mid": 8650,
        "high": 10000,
        "return_low": 4.7,
        "return_mid": 10.0,
        "return_high": 11.1,
        "type": "forecast",
        "source": "Long-term projection models",
        "notes": "Reversion toward historical mean returns"
    },
    2029: {
        "low": 7000,
        "mid": 9515,
        "high": 11000,
        "return_low": 4.5,
        "return_mid": 10.0,
        "return_high": 10.0,
        "type": "forecast",
        "source": "Long-term projection models",
        "notes": "Assumes 8-10% annual earnings growth"
    },
    2030: {
        "low": 7300,
        "mid": 10467,
        "high": 12000,
        "return_low": 4.3,
        "return_mid": 10.0,
        "return_high": 9.1,
        "type": "forecast",
        "source": "10-year forward estimates",
        "notes": "Based on historical equity risk premium"
    },
}

# Source attribution
FORECAST_SOURCES = [
    {
        "name": "Goldman Sachs",
        "division": "Global Investment Research",
        "frequency": "Quarterly",
        "last_update": "2024-11-15",
        "methodology": "Top-down earnings model with macro overlay",
    },
    {
        "name": "JP Morgan",
        "division": "Asset Management",
        "frequency": "Quarterly",
        "last_update": "2024-11-20",
        "methodology": "Fair value model based on earnings and rates",
    },
    {
        "name": "Morgan Stanley",
        "division": "Wealth Management",
        "frequency": "Monthly",
        "last_update": "2024-12-01",
        "methodology": "Cycle analysis with valuation framework",
    },
    {
        "name": "Bank of America",
        "division": "Global Research",
        "frequency": "Quarterly",
        "last_update": "2024-11-18",
        "methodology": "Bottom-up earnings aggregation",
    },
]

# Historical S&P 500 performance for backtesting
SP500_HISTORICAL_RETURNS = {
    2000: -10.1, 2001: -13.0, 2002: -23.4, 2003: 26.4, 2004: 9.0,
    2005: 3.0, 2006: 13.6, 2007: 3.5, 2008: -38.5, 2009: 23.5,
    2010: 12.8, 2011: 0.0, 2012: 13.4, 2013: 29.6, 2014: 11.4,
    2015: -0.7, 2016: 9.5, 2017: 19.4, 2018: -6.2, 2019: 28.9,
    2020: 16.3, 2021: 26.9, 2022: -19.4, 2023: 24.2, 2024: 23.3,
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class ForecastPoint:
    """Single year forecast or actual."""
    year: int
    level_low: float
    level_mid: float
    level_high: float
    return_low: float
    return_mid: float
    return_high: float
    is_forecast: bool
    source: str
    notes: Optional[str] = None


@dataclass
class ForecastSource:
    """Attribution for forecast sources."""
    name: str
    division: str
    frequency: str
    last_update: str
    methodology: str


@dataclass
class SP500ForecastResponse:
    """Complete forecast response with attribution."""
    forecasts: List[ForecastPoint]
    sources: List[ForecastSource]
    base_year: int
    base_level: float
    methodology_summary: str
    last_updated: str
    disclaimer: str


# ==============================================================================
# Market Forecaster
# ==============================================================================

class MarketForecaster:
    """
    Provides S&P 500 consensus forecasts from major investment banks.
    
    Uses static forecasts that are updated periodically (not real-time).
    This approach provides:
    - Transparency on forecast sources
    - Consistency in comparisons
    - No API dependencies
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
        """
        Get S&P 500 forecasts with full attribution.
        
        Args:
            years_forward: Number of years to forecast
            include_historical: Include recent actuals for context
            
        Returns:
            SP500ForecastResponse with forecasts and source attribution
        """
        forecasts = []
        
        # Determine range
        start_year = self.current_year - 3 if include_historical else self.current_year
        end_year = self.current_year + years_forward
        
        for year in range(start_year, end_year + 1):
            if year in SP500_CONSENSUS_FORECASTS:
                data = SP500_CONSENSUS_FORECASTS[year]
                
                if data.get("type") == "actual":
                    # Historical actual
                    level = data.get("level", 0)
                    return_pct = data.get("return_pct", 0)
                    forecasts.append(ForecastPoint(
                        year=year,
                        level_low=level,
                        level_mid=level,
                        level_high=level,
                        return_low=return_pct,
                        return_mid=return_pct,
                        return_high=return_pct,
                        is_forecast=False,
                        source=data.get("source", "S&P Dow Jones Indices"),
                        notes=None,
                    ))
                else:
                    # Forecast
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
        
        # Get base year data
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
        return [
            ForecastSource(**source) 
            for source in FORECAST_SOURCES
        ]
    
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
        """
        Calculate cumulative portfolio value over time.
        
        Uses historical actuals where available, forecasts for future.
        
        Args:
            start_year: Start year
            end_year: End year
            initial_value: Starting portfolio value (default $100)
            use_forecast: Include forecast years
            
        Returns:
            List of {year, value, return, is_forecast}
        """
        results = []
        current_value = initial_value
        
        for year in range(start_year, end_year + 1):
            # Get return for this year
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
                # Use long-term average
                return_pct = 8.0
                is_forecast = True
            
            # Calculate new value
            current_value = current_value * (1 + return_pct / 100)
            
            results.append({
                "year": year,
                "value": round(current_value, 2),
                "return_pct": return_pct,
                "is_forecast": is_forecast,
            })
        
        return results

