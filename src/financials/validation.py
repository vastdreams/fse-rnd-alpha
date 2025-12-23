"""Financial data quality validation and checks."""
from typing import Dict, Optional, List, Tuple
from src.models.orm.financials_core import FinancialsCore
from src.utils.data_validation import (
    validate_financial_value,
    validate_ratio,
    validate_balance_sheet_equation,
)
from src.logging.logger import get_logger

logger = get_logger(__name__)


def validate_financials_core(financials: FinancialsCore) -> Dict[str, Any]:
    """
    Validate financial core data for quality and consistency.
    
    Args:
        financials: FinancialsCore object to validate
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {},
    }
    
    # Check 1: Revenue should be positive
    if financials.revenue is not None:
        if financials.revenue < 0:
            results["errors"].append(f"Revenue is negative: {financials.revenue}")
            results["valid"] = False
        results["checks"]["revenue_positive"] = financials.revenue >= 0
    
    # Check 2: Balance sheet equation
    if all(v is not None for v in [financials.total_assets, financials.total_liabilities, financials.total_equity]):
        balance_check = validate_balance_sheet_equation(
            financials.total_assets,
            financials.total_liabilities,
            financials.total_equity,
            tolerance=0.01  # 1% tolerance for rounding
        )
        results["checks"]["balance_sheet_equation"] = balance_check
        if not balance_check["valid"]:
            results["warnings"].append(f"Balance sheet equation imbalance: {balance_check.get('error')}")
    
    # Check 3: Reasonable value ranges
    max_reasonable_value = 1e15  # Very large but possible for mega-caps
    
    if financials.revenue:
        if not validate_financial_value(financials.revenue, "revenue", allow_negative=False, max_abs_value=max_reasonable_value):
            results["warnings"].append("Revenue value outside reasonable range")
    
    if financials.net_income is not None:
        # Net income can be negative (losses)
        if not validate_financial_value(financials.net_income, "net_income", allow_negative=True, max_abs_value=max_reasonable_value):
            results["warnings"].append("Net income value outside reasonable range")
    
    # Check 4: Ratios consistency
    if financials.revenue and financials.revenue > 0:
        if financials.gross_profit is not None:
            gross_margin = financials.gross_profit / financials.revenue
            if not validate_ratio(gross_margin, "gross_margin"):
                results["warnings"].append(f"Gross margin ratio outside reasonable range: {gross_margin}")
        
        if financials.operating_income is not None:
            operating_margin = financials.operating_income / financials.revenue
            if not validate_ratio(operating_margin, "operating_margin"):
                results["warnings"].append(f"Operating margin ratio outside reasonable range: {operating_margin}")
    
    # Check 5: R&D expense should not exceed revenue
    if financials.rd_expense is not None and financials.revenue and financials.revenue > 0:
        if financials.rd_expense > financials.revenue:
            results["warnings"].append(f"R&D expense ({financials.rd_expense}) exceeds revenue ({financials.revenue})")
    
    # Check 6: Assets should be positive
    if financials.total_assets is not None:
        if financials.total_assets < 0:
            results["errors"].append(f"Total assets is negative: {financials.total_assets}")
            results["valid"] = False
    
    # Check 7: Equity can be negative (deficit)
    # This is valid for some companies, so just log as info
    if financials.total_equity is not None:
        if financials.total_equity < 0:
            logger.info(f"Total equity is negative (deficit): {financials.total_equity}")
    
    return results


def calculate_data_quality_score(financials: FinancialsCore) -> Dict[str, Any]:
    """
    Calculate data quality score for financial data.
    
    Args:
        financials: FinancialsCore object
        
    Returns:
        Dictionary with quality score and details
    """
    validation = validate_financials_core(financials)
    
    # Calculate completeness score
    required_fields = [
        "revenue", "net_income", "total_assets",
        "total_liabilities", "total_equity"
    ]
    
    completed_fields = sum(
        1 for field in required_fields
        if getattr(financials, field, None) is not None
    )
    completeness_score = completed_fields / len(required_fields) if required_fields else 0.0
    
    # Calculate consistency score (based on validation checks)
    consistency_score = 1.0
    if validation["errors"]:
        consistency_score -= 0.5  # Errors reduce score significantly
    if validation["warnings"]:
        consistency_score -= len(validation["warnings"]) * 0.1  # Warnings reduce score
    
    consistency_score = max(0.0, consistency_score)
    
    # Overall quality score
    quality_score = (completeness_score * 0.6) + (consistency_score * 0.4)
    
    return {
        "quality_score": quality_score,
        "completeness_score": completeness_score,
        "consistency_score": consistency_score,
        "validation": validation,
        "missing_fields": [
            field for field in required_fields
            if getattr(financials, field, None) is None
        ],
    }


def validate_ratio_ranges(ratios: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """
    Validate that ratios are within reasonable ranges.
    
    Args:
        ratios: Dictionary of ratio values
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "warnings": [],
    }
    
    # Reasonable ranges for common ratios
    ratio_ranges = {
        "gross_margin": (0.0, 1.0),  # 0-100%
        "operating_margin": (-0.5, 1.0),  # Can be negative (losses)
        "net_margin": (-0.5, 1.0),  # Can be negative
        "rd_intensity": (0.0, 1.0),  # 0-100%
        "roe": (-10.0, 10.0),  # Can be negative or very high
        "roa": (-1.0, 1.0),  # -100% to 100%
        "debt_to_equity": (0.0, 50.0),  # Can be very high
        "debt_to_assets": (0.0, 1.0),  # 0-100%
        "interest_coverage": (-100.0, 1000.0),  # Wide range
        "fcf_margin": (-1.0, 1.0),  # -100% to 100%
    }
    
    for ratio_name, (min_val, max_val) in ratio_ranges.items():
        if ratio_name in ratios and ratios[ratio_name] is not None:
            ratio_value = ratios[ratio_name]
            
            if ratio_value < min_val or ratio_value > max_val:
                results["warnings"].append(
                    f"Ratio {ratio_name} ({ratio_value}) outside expected range [{min_val}, {max_val}]"
                )
    
    return results

