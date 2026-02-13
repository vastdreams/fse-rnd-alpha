# SanityChecker class for comprehensive R&D research data validation.
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

from app.services.sanity_checks.constants import (
    MAX_RD_INTENSITY_ABSOLUTE, MAX_RD_INTENSITY_BIOTECH,
    MIN_REVENUE_THRESHOLD, MIN_ANNUAL_RETURN, MAX_ANNUAL_RETURN,
    WINSORIZE_LOWER, WINSORIZE_UPPER, HIGH_RD_SECTORS,
)
from app.services.sanity_checks.models import ValidationResult, DataQualityMetrics

logger = logging.getLogger(__name__)


class SanityChecker:
    """Comprehensive sanity checking for R&D research data:
    R&D intensity validation/capping, return validation, revenue filtering,
    winsorization, and data quality metrics.
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
        self._outliers_capped = 0
        self._records_validated = 0

    def validate_rd_intensity(
        self,
        intensity: float,
        sector: Optional[str] = None,
        revenue: Optional[float] = None
    ) -> ValidationResult:
        """Validate and potentially cap R&D intensity (percentage, e.g. 10 = 10%)."""
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
        if intensity > cap:
            self._outliers_capped += 1
            return ValidationResult(
                is_valid=True,
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
        """Validate annual return value, capping at MIN/MAX bounds."""
        if annual_return is None or np.isnan(annual_return) or np.isinf(annual_return):
            return ValidationResult(
                is_valid=False,
                original_value=annual_return or 0,
                adjusted_value=0,
                reason="Invalid value (null/NaN/Inf)"
            )
        value = annual_return if as_decimal else annual_return / 100
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
        """Winsorize an array of values at specified percentiles. Returns (values, count_adjusted)."""
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
        """Validate and clean a batch of R&D intensity data. Returns (cleaned_data, metrics)."""
        total = len(data)
        valid = 0
        capped = 0
        missing = 0
        cleaned = []
        for record in data:
            intensity = record.get(intensity_key)
            sector = record.get(sector_key)
            revenue = record.get(revenue_key)
            if intensity is None:
                missing += 1
                continue
            if revenue is not None and revenue < self.min_revenue:
                continue
            result = self.validate_rd_intensity(intensity, sector, revenue)
            if result.is_valid:
                valid += 1
                if result.adjusted_value != result.original_value:
                    capped += 1
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
