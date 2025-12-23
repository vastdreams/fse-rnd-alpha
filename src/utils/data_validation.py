"""Comprehensive data validation utilities."""
from typing import Any, Optional, Dict, List, Callable
from src.logging.logger import get_logger

logger = get_logger(__name__)


def validate_type(value: Any, expected_type: type, field_name: str = "value") -> bool:
    """
    Validate that value is of expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        field_name: Name of field for error messages
        
    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return True  # None is allowed (nullable fields)
    
    if not isinstance(value, expected_type):
        logger.warning(f"{field_name} has wrong type: expected {expected_type.__name__}, got {type(value).__name__}")
        return False
    
    return True


def validate_numeric_range(
    value: Optional[float],
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "value"
) -> bool:
    """
    Validate that numeric value is within range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value (None = no minimum)
        max_value: Maximum allowed value (None = no maximum)
        field_name: Name of field for error messages
        
    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return True  # None is allowed
    
    if not isinstance(value, (int, float)):
        logger.warning(f"{field_name} is not numeric: {type(value)}")
        return False
    
    if not (isinstance(value, float) or isinstance(value, int)):
        return False
    
    # Check for NaN or Infinity
    import math
    if math.isnan(value) or math.isinf(value):
        logger.warning(f"{field_name} is NaN or Infinity: {value}")
        return False
    
    if min_value is not None and value < min_value:
        logger.warning(f"{field_name} is below minimum {min_value}: {value}")
        return False
    
    if max_value is not None and value > max_value:
        logger.warning(f"{field_name} is above maximum {max_value}: {value}")
        return False
    
    return True


def validate_financial_value(
    value: Optional[float],
    field_name: str = "value",
    allow_negative: bool = True,
    max_abs_value: Optional[float] = None
) -> bool:
    """
    Validate financial value with reasonable constraints.
    
    Args:
        value: Financial value to validate
        field_name: Name of field
        allow_negative: Whether negative values are allowed
        max_abs_value: Maximum absolute value (e.g., 1e15 for very large companies)
        
    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return True
    
    # Type check
    if not validate_type(value, (int, float), field_name):
        return False
    
    # Range check
    if max_abs_value:
        if not validate_numeric_range(value, -max_abs_value, max_abs_value, field_name):
            return False
    
    # Negative check
    if not allow_negative and value < 0:
        logger.warning(f"{field_name} is negative but should be positive: {value}")
        return False
    
    return True


def validate_ratio(ratio: Optional[float], field_name: str = "ratio") -> bool:
    """
    Validate financial ratio (typically between -10 and 10).
    
    Args:
        ratio: Ratio value to validate
        field_name: Name of field
        
    Returns:
        True if valid, False otherwise
    """
    if ratio is None:
        return True
    
    # Ratios can be negative (losses, negative equity, etc.)
    # But extremely large ratios are suspicious
    return validate_numeric_range(ratio, -100, 100, field_name)


def validate_balance_sheet_equation(
    assets: Optional[float],
    liabilities: Optional[float],
    equity: Optional[float],
    tolerance: float = 0.01
) -> Dict[str, Any]:
    """
    Validate balance sheet equation: Assets = Liabilities + Equity.
    
    Args:
        assets: Total assets
        liabilities: Total liabilities
        equity: Total equity
        tolerance: Tolerance for rounding errors (as percentage)
        
    Returns:
        Dictionary with validation result and details
    """
    result = {
        "valid": True,
        "error": None,
        "difference": None,
        "difference_percent": None,
    }
    
    if assets is None or liabilities is None or equity is None:
        result["valid"] = False
        result["error"] = "Missing required values"
        return result
    
    # Calculate expected assets
    expected_assets = (liabilities or 0) + (equity or 0)
    actual_assets = assets or 0
    
    # Calculate difference
    difference = abs(actual_assets - expected_assets)
    result["difference"] = difference
    
    # Calculate percentage difference
    if expected_assets != 0:
        difference_percent = (difference / abs(expected_assets)) * 100
        result["difference_percent"] = difference_percent
        
        # Check if within tolerance
        if difference_percent > tolerance * 100:
            result["valid"] = False
            result["error"] = f"Balance sheet equation imbalance: {difference_percent:.2f}%"
            logger.warning(
                f"Balance sheet equation validation failed: "
                f"Assets={actual_assets}, Liabilities+Equity={expected_assets}, "
                f"Difference={difference_percent:.2f}%"
            )
    else:
        if difference > 0:
            result["valid"] = False
            result["error"] = "Balance sheet equation imbalance with zero expected"
    
    return result


def validate_data_quality(data: Dict[str, Any], validation_rules: Dict[str, Callable]) -> Dict[str, Any]:
    """
    Validate data against a set of validation rules.
    
    Args:
        data: Data dictionary to validate
        validation_rules: Dictionary mapping field names to validation functions
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "field_results": {},
    }
    
    for field_name, validator_func in validation_rules.items():
        value = data.get(field_name)
        
        try:
            is_valid = validator_func(value)
            
            results["field_results"][field_name] = {
                "valid": is_valid,
                "value": value,
            }
            
            if not is_valid:
                results["valid"] = False
                results["errors"].append(f"Validation failed for {field_name}: {value}")
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error for {field_name}: {e}")
    
    return results
