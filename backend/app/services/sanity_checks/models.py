# Data classes for validation results and quality metrics.
from typing import Optional
from dataclasses import dataclass


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
