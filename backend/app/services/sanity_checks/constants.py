# Constants and thresholds for R&D data validation and sanity checks.
import numpy as np

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
    """Determine R&D reporting status: 'reported', 'zero', or 'missing'."""
    if rd_expense_value is None:
        return 'missing'
    elif rd_expense_value == 0:
        return 'zero'
    else:
        return 'reported'
