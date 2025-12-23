"""Normalize financial data (units, fiscal year alignment, restatements)."""
from typing import Dict, Optional
from src.utils.data_validation import validate_type, validate_financial_value
from src.logging.logger import get_logger

logger = get_logger(__name__)


def normalize_units(value: float, unit: str, target_unit: str = "USD", shares_outstanding: Optional[float] = None) -> Optional[float]:
    """
    Normalize financial values to target unit (default USD).
    
    Args:
        value: Value to normalize
        unit: Current unit (USD, USD/shares, shares, etc.)
        target_unit: Target unit (default: USD)
        shares_outstanding: Shares outstanding (required for USD/shares conversion)
        
    Returns:
        Normalized value or None if conversion not possible
    """
    # Validate inputs
    if not validate_type(value, (int, float), "value"):
        logger.error(f"Invalid value type for unit normalization: {type(value)}")
        return None
    
    if not isinstance(unit, str):
        logger.error(f"Invalid unit type: {type(unit)}")
        return None
    
    # Handle common unit conversions
    if unit == target_unit:
        return float(value)
    
    if unit == "USD" and target_unit == "USD":
        return float(value)
    
    elif unit == "USD/shares" and target_unit == "USD":
        if shares_outstanding is None or shares_outstanding <= 0:
            logger.warning(f"Cannot convert USD/shares to USD without shares outstanding")
            return None
        return float(value) * shares_outstanding
    
    elif unit == "shares" and target_unit == "USD":
        # Cannot convert shares to USD without price
        logger.warning(f"Cannot convert shares to USD without price information")
        return None
    
    elif unit in ["thousands", "K"] and target_unit == "USD":
        return float(value) * 1000
    
    elif unit in ["millions", "M"] and target_unit == "USD":
        return float(value) * 1000000
    
    elif unit in ["billions", "B"] and target_unit == "USD":
        return float(value) * 1000000000
    
    else:
        logger.warning(f"Unknown unit conversion: {unit} -> {target_unit}")
        return float(value)  # Return as-is with warning


def align_fiscal_year(data: Dict, target_year: int) -> Optional[Dict]:
    """Align financial data to target fiscal year."""
    # For now, simple lookup
    return data.get(target_year)


def handle_restatements(data: Dict, prefer_latest: bool = True) -> Dict:
    """Handle restatements - prefer latest non-restated values."""
    # For now, return as-is
    # In production, would check for restatement flags
    return data

