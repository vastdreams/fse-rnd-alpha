# Utility functions for R&D intensity capping, winsorization, and known-company validation.
from typing import List, Dict, Optional
import numpy as np

from app.services.sanity_checks.constants import (
    MAX_RD_INTENSITY_ABSOLUTE, MAX_RD_INTENSITY_BIOTECH, HIGH_RD_SECTORS,
)
from app.services.sanity_checks.checker import SanityChecker


def cap_rd_intensity(
    intensity: float,
    sector: Optional[str] = None,
    cap: float = MAX_RD_INTENSITY_ABSOLUTE
) -> float:
    """Quick utility to cap R&D intensity at a maximum value.

    NOTE: For high-R&D sectors (Healthcare, Biotech, Pharma), we use a HIGHER cap
    (MAX_RD_INTENSITY_BIOTECH = 200%) to allow for pre-revenue biotech companies.
    The logic uses max() not min() to allow the sector-specific cap to override.
    """
    try:
        intensity_float = float(intensity) if intensity is not None else None
    except (TypeError, ValueError):
        return 0.0
    if intensity_float is None or np.isnan(intensity_float):
        return 0.0
    if sector and sector in HIGH_RD_SECTORS:
        effective_cap = max(cap, MAX_RD_INTENSITY_BIOTECH)
    else:
        effective_cap = cap
    return min(max(intensity_float, 0), effective_cap)


def winsorize_series(
    values: List[float],
    lower_pct: int = 1,
    upper_pct: int = 99
) -> List[float]:
    """Winsorize a list of values at specified percentiles."""
    checker = SanityChecker()
    result, _ = checker.winsorize_array(values, lower_pct, upper_pct)
    return result


def validate_known_companies(data: List[Dict]) -> Dict[str, str]:
    """Validate R&D intensity for well-known companies against expected ranges.
    Returns dict of warnings for any anomalies.
    """
    expected = {
        "AAPL": (3, 15),
        "MSFT": (8, 20),
        "GOOG": (10, 25),
        "GOOGL": (10, 25),
        "AMZN": (8, 20),
        "TSLA": (2, 15),
        "META": (15, 35),
        "NVDA": (15, 30),
    }
    warnings = {}
    for record in data:
        symbol = record.get("symbol", "")
        intensity = record.get("rd_intensity", 0)
        if symbol in expected:
            low, high = expected[symbol]
            if intensity < low or intensity > high:
                warnings[symbol] = (
                    f"R&D intensity {intensity:.1f}% outside expected range "
                    f"[{low}%, {high}%]"
                )
    return warnings
