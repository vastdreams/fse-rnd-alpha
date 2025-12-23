"""
PATH: backend/app/services/sanity_checks.py
PURPOSE:
  - Data validation and sanity checks for R&D research
  - Winsorization and outlier handling
  - Ensure research results are publication-ready
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


# ==============================================================================
# Constants for Validation
# ==============================================================================

# R&D Intensity Bounds (as percentage: 10 = 10%)
MAX_RD_INTENSITY_NORMAL = 50.0      # 50% cap for mature companies
MAX_RD_INTENSITY_BIOTECH = 200.0    # Higher cap for pre-revenue biotech/pharma
MAX_RD_INTENSITY_ABSOLUTE = 100.0   # Absolute cap for most analyses

# Minimum Revenue Threshold (in dollars)
MIN_REVENUE_THRESHOLD = 100_000_000  # $100M minimum revenue

# Return Bounds (as decimal: 0.10 = 10%)
MIN_ANNUAL_RETURN = -0.99   # -99% (near total loss)
MAX_ANNUAL_RETURN = 10.0    # 1000% gain (very generous)

# Winsorization Percentiles
WINSORIZE_LOWER = 1    # 1st percentile
WINSORIZE_UPPER = 99   # 99th percentile

# Sectors with typically high R&D (allow higher caps)
HIGH_RD_SECTORS = {
    "Healthcare",
    "Biotechnology", 
    "Pharmaceuticals",
    "Health Care",
}


def determine_rd_status(rd_expense_value) -> str:
    """
    Determine R&D reporting status.
    
    Args:
        rd_expense_value: Raw R&D expense value from data source
        
    Returns:
        'reported': Has a positive value
        'zero': Explicitly reported as zero
        'missing': NULL or not disclosed
    """
    if rd_expense_value is None:
        return 'missing'
    elif rd_expense_value == 0:
        return 'zero'
    else:
        return 'reported'


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    original_value: float
    adjusted_value: float
    reason: Optional[str] = None


@dataclass
class DataQualityMetrics:
    """Metrics for data quality reporting."""
    total_records: int
    valid_records: int
    outliers_capped: int
    missing_values: int
    coverage_pct: float
    outlier_pct: float
    winsorization_applied: bool


# ==============================================================================
# Sanity Checker Class
# ==============================================================================

class SanityChecker:
    """
    Comprehensive sanity checking for R&D research data.
    
    Provides:
    - R&D intensity validation and capping
    - Return validation
    - Revenue threshold filtering
    - Winsorization utilities
    - Data quality metrics
    """
    
    def __init__(
        self,
        max_rd_intensity: float = MAX_RD_INTENSITY_ABSOLUTE,
        min_revenue: float = MIN_REVENUE_THRESHOLD,
        winsorize: bool = True
    ):
        self.max_rd_intensity = max_rd_intensity
        self.min_revenue = min_revenue
        self.winsorize = winsorize
        
        # Track statistics
        self._outliers_capped = 0
        self._records_validated = 0
    
    def validate_rd_intensity(
        self,
        intensity: float,
        sector: Optional[str] = None,
        revenue: Optional[float] = None
    ) -> ValidationResult:
        """
        Validate and potentially cap R&D intensity.
        
        Args:
            intensity: R&D intensity as percentage (10 = 10%)
            sector: Company sector (for sector-specific caps)
            revenue: Company revenue (for pre-revenue biotech handling)
            
        Returns:
            ValidationResult with potentially adjusted value
        """
        if intensity is None or np.isnan(intensity) or np.isinf(intensity):
            return ValidationResult(
                is_valid=False,
                original_value=intensity or 0,
                adjusted_value=0,
                reason="Invalid value (null/NaN/Inf)"
            )
        
        # Determine appropriate cap based on sector
        if sector and sector in HIGH_RD_SECTORS:
            cap = MAX_RD_INTENSITY_BIOTECH
        else:
            cap = self.max_rd_intensity
        
        # Check if value is an outlier
        if intensity > cap:
            self._outliers_capped += 1
            return ValidationResult(
                is_valid=True,  # Still valid, just capped
                original_value=intensity,
                adjusted_value=cap,
                reason=f"Capped from {intensity:.1f}% to {cap:.1f}% (outlier)"
            )
        
        if intensity < 0:
            return ValidationResult(
                is_valid=False,
                original_value=intensity,
                adjusted_value=0,
                reason="Negative R&D intensity (invalid)"
            )
        
        self._records_validated += 1
        return ValidationResult(
            is_valid=True,
            original_value=intensity,
            adjusted_value=intensity,
            reason=None
        )
    
    def validate_return(
        self,
        annual_return: float,
        as_decimal: bool = True
    ) -> ValidationResult:
        """
        Validate annual return value.
        
        Args:
            annual_return: Return value
            as_decimal: If True, return is decimal (0.10 = 10%), else percentage
            
        Returns:
            ValidationResult with potentially adjusted value
        """
        if annual_return is None or np.isnan(annual_return) or np.isinf(annual_return):
            return ValidationResult(
                is_valid=False,
                original_value=annual_return or 0,
                adjusted_value=0,
                reason="Invalid value (null/NaN/Inf)"
            )
        
        # Convert to decimal if needed
        value = annual_return if as_decimal else annual_return / 100
        
        # Check bounds
        if value < MIN_ANNUAL_RETURN:
            return ValidationResult(
                is_valid=True,
                original_value=annual_return,
                adjusted_value=MIN_ANNUAL_RETURN if as_decimal else MIN_ANNUAL_RETURN * 100,
                reason=f"Capped at minimum return ({MIN_ANNUAL_RETURN * 100:.0f}%)"
            )
        
        if value > MAX_ANNUAL_RETURN:
            return ValidationResult(
                is_valid=True,
                original_value=annual_return,
                adjusted_value=MAX_ANNUAL_RETURN if as_decimal else MAX_ANNUAL_RETURN * 100,
                reason=f"Capped at maximum return ({MAX_ANNUAL_RETURN * 100:.0f}%)"
            )
        
        return ValidationResult(
            is_valid=True,
            original_value=annual_return,
            adjusted_value=annual_return,
            reason=None
        )
    
    def validate_revenue(self, revenue: float) -> bool:
        """Check if revenue meets minimum threshold."""
        if revenue is None or np.isnan(revenue):
            return False
        return revenue >= self.min_revenue
    
    def winsorize_array(
        self,
        values: List[float],
        lower_pct: int = WINSORIZE_LOWER,
        upper_pct: int = WINSORIZE_UPPER
    ) -> Tuple[List[float], int]:
        """
        Winsorize an array of values at specified percentiles.
        
        Args:
            values: List of values to winsorize
            lower_pct: Lower percentile cutoff (default 1)
            upper_pct: Upper percentile cutoff (default 99)
            
        Returns:
            Tuple of (winsorized_values, count_adjusted)
        """
        if not values:
            return [], 0
        
        arr = np.array([v for v in values if v is not None and not np.isnan(v)])
        if len(arr) == 0:
            return [], 0
        
        lower_bound = np.percentile(arr, lower_pct)
        upper_bound = np.percentile(arr, upper_pct)
        
        adjusted = 0
        result = []
        
        for v in values:
            if v is None or np.isnan(v):
                result.append(v)
            elif v < lower_bound:
                result.append(lower_bound)
                adjusted += 1
            elif v > upper_bound:
                result.append(upper_bound)
                adjusted += 1
            else:
                result.append(v)
        
        return result, adjusted
    
    def validate_rd_intensity_batch(
        self,
        data: List[Dict],
        intensity_key: str = "rd_intensity",
        sector_key: str = "sector",
        revenue_key: str = "revenue"
    ) -> Tuple[List[Dict], DataQualityMetrics]:
        """
        Validate and clean a batch of R&D intensity data.
        
        Args:
            data: List of dicts containing intensity, sector, revenue
            intensity_key: Key for R&D intensity field
            sector_key: Key for sector field
            revenue_key: Key for revenue field
            
        Returns:
            Tuple of (cleaned_data, quality_metrics)
        """
        total = len(data)
        valid = 0
        capped = 0
        missing = 0
        
        cleaned = []
        
        for record in data:
            intensity = record.get(intensity_key)
            sector = record.get(sector_key)
            revenue = record.get(revenue_key)
            
            # Check for missing intensity
            if intensity is None:
                missing += 1
                continue
            
            # Check revenue threshold
            if revenue is not None and revenue < self.min_revenue:
                continue
            
            # Validate and potentially cap intensity
            result = self.validate_rd_intensity(intensity, sector, revenue)
            
            if result.is_valid:
                valid += 1
                if result.adjusted_value != result.original_value:
                    capped += 1
                
                # Create cleaned record
                cleaned_record = record.copy()
                cleaned_record[intensity_key] = result.adjusted_value
                cleaned_record["_intensity_capped"] = result.adjusted_value != result.original_value
                cleaned_record["_original_intensity"] = result.original_value
                cleaned.append(cleaned_record)
        
        metrics = DataQualityMetrics(
            total_records=total,
            valid_records=valid,
            outliers_capped=capped,
            missing_values=missing,
            coverage_pct=round(valid / total * 100, 1) if total > 0 else 0,
            outlier_pct=round(capped / valid * 100, 1) if valid > 0 else 0,
            winsorization_applied=self.winsorize
        )
        
        return cleaned, metrics
    
    def get_quality_summary(self) -> Dict:
        """Get summary of validation statistics."""
        return {
            "records_validated": self._records_validated,
            "outliers_capped": self._outliers_capped,
            "outlier_rate": round(
                self._outliers_capped / self._records_validated * 100, 2
            ) if self._records_validated > 0 else 0,
            "max_rd_intensity_cap": self.max_rd_intensity,
            "min_revenue_threshold": self.min_revenue
        }
    
    def reset_stats(self):
        """Reset validation statistics."""
        self._outliers_capped = 0
        self._records_validated = 0


# ==============================================================================
# Utility Functions
# ==============================================================================

def cap_rd_intensity(
    intensity: float,
    sector: Optional[str] = None,
    cap: float = MAX_RD_INTENSITY_ABSOLUTE
) -> float:
    """
    Quick utility to cap R&D intensity at a maximum value.
    
    Args:
        intensity: R&D intensity as percentage
        sector: Optional sector for sector-specific caps
        cap: Maximum allowed value (can be overridden by sector-specific cap)
        
    Returns:
        Capped intensity value
        
    NOTE: For high-R&D sectors (Healthcare, Biotech, Pharma), we use a HIGHER cap
    (MAX_RD_INTENSITY_BIOTECH = 200%) to allow for pre-revenue biotech companies.
    The logic uses max() not min() to allow the sector-specific cap to override.
    """
    # Convert to float to handle Decimal types from SQL
    try:
        intensity_float = float(intensity) if intensity is not None else None
    except (TypeError, ValueError):
        return 0.0
        
    if intensity_float is None or np.isnan(intensity_float):
        return 0.0
    
    if sector and sector in HIGH_RD_SECTORS:
        # Use the HIGHER of the two caps for high-R&D sectors
        # This allows biotech to have up to 200% R&D intensity
        effective_cap = max(cap, MAX_RD_INTENSITY_BIOTECH)
    else:
        effective_cap = cap
    
    return min(max(intensity_float, 0), effective_cap)


def winsorize_series(
    values: List[float],
    lower_pct: int = 1,
    upper_pct: int = 99
) -> List[float]:
    """
    Winsorize a list of values at specified percentiles.
    
    Args:
        values: Input values
        lower_pct: Lower percentile (default 1)
        upper_pct: Upper percentile (default 99)
        
    Returns:
        Winsorized values
    """
    checker = SanityChecker()
    result, _ = checker.winsorize_array(values, lower_pct, upper_pct)
    return result


def validate_known_companies(data: List[Dict]) -> Dict[str, str]:
    """
    Validate R&D intensity for well-known companies.
    
    Known approximate R&D intensities:
    - AAPL: ~7-8%
    - MSFT: ~12-14%
    - GOOG: ~15-16%
    - AMZN: ~12-14%
    - TSLA: ~4-6%
    - MRNA: ~50-100% (biotech)
    
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

