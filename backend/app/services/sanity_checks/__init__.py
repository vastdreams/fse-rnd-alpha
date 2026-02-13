# Sanity checks package: data validation, winsorization, and outlier handling for R&D research.
from app.services.sanity_checks.constants import (
    MAX_RD_INTENSITY_NORMAL,
    MAX_RD_INTENSITY_BIOTECH,
    MAX_RD_INTENSITY_ABSOLUTE,
    MIN_REVENUE_THRESHOLD,
    MIN_ANNUAL_RETURN,
    MAX_ANNUAL_RETURN,
    WINSORIZE_LOWER,
    WINSORIZE_UPPER,
    HIGH_RD_SECTORS,
    determine_rd_status,
)
from app.services.sanity_checks.models import ValidationResult, DataQualityMetrics
from app.services.sanity_checks.checker import SanityChecker
from app.services.sanity_checks.utils import (
    cap_rd_intensity,
    winsorize_series,
    validate_known_companies,
)

__all__ = [
    "MAX_RD_INTENSITY_NORMAL",
    "MAX_RD_INTENSITY_BIOTECH",
    "MAX_RD_INTENSITY_ABSOLUTE",
    "MIN_REVENUE_THRESHOLD",
    "MIN_ANNUAL_RETURN",
    "MAX_ANNUAL_RETURN",
    "WINSORIZE_LOWER",
    "WINSORIZE_UPPER",
    "HIGH_RD_SECTORS",
    "determine_rd_status",
    "ValidationResult",
    "DataQualityMetrics",
    "SanityChecker",
    "cap_rd_intensity",
    "winsorize_series",
    "validate_known_companies",
]
