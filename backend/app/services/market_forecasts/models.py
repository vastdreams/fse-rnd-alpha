# Data classes for market forecast responses and source attribution.
from typing import List, Optional
from dataclasses import dataclass


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
