"""Date and fiscal year utilities for financial data."""
from datetime import datetime
from typing import Optional, Tuple
from src.logging.logger import get_logger

logger = get_logger(__name__)


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string in various formats.
    
    Supports:
    - YYYY-MM-DD
    - MM/DD/YYYY
    - YYYYMMDD
    - Other common formats
    
    Args:
        date_str: Date string to parse
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Common date formats to try
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y%m%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    logger.warning(f"Could not parse date string: {date_str}")
    return None


def extract_year_from_date(date_str: str) -> Optional[int]:
    """
    Extract year from date string.
    
    Args:
        date_str: Date string
        
    Returns:
        Year as integer or None
    """
    dt = parse_date(date_str)
    if dt:
        return dt.year
    
    # Try to extract 4-digit year directly
    import re
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        return int(year_match.group(0))
    
    return None


def calculate_fiscal_year(end_date_str: str, fiscal_year_end_month: int = 12) -> Optional[int]:
    """
    Calculate fiscal year from fiscal year end date.
    
    Fiscal year is typically the calendar year of the fiscal year end.
    However, if fiscal year ends in early months (Jan-Mar), the fiscal year
    might be the previous calendar year.
    
    Example:
    - FY end: Feb 28, 2024 → FY 2023 (fiscal year ending in early 2024 belongs to FY 2023)
    - FY end: Dec 31, 2023 → FY 2023
    
    Args:
        end_date_str: Fiscal year end date string
        fiscal_year_end_month: Month when fiscal year ends (default: 12 = December)
        
    Returns:
        Fiscal year as integer or None
    """
    dt = parse_date(end_date_str)
    if not dt:
        return None
    
    year = dt.year
    month = dt.month
    
    # If fiscal year ends in first quarter (Jan-Mar), it's usually part of previous FY
    # This is a common pattern for retailers (e.g., FY ends in January/February)
    if fiscal_year_end_month <= 3 and month <= 3:
        # FY ending in Q1 belongs to previous calendar year
        return year - 1
    
    # Otherwise, fiscal year is the same as calendar year of end date
    return year


def parse_fiscal_year_from_date(date_str: str) -> Optional[int]:
    """
    Parse fiscal year from date string, handling various formats.
    
    Args:
        date_str: Date string (could be end date or filing date)
        
    Returns:
        Fiscal year as integer or None
    """
    # First, try to parse as date
    dt = parse_date(date_str)
    if dt:
        return dt.year
    
    # Try to extract year from string
    year = extract_year_from_date(date_str)
    return year


def validate_fiscal_year_match(date_str: str, target_year: int, strict: bool = False) -> bool:
    """
    Validate that a date string matches a target fiscal year.
    
    Args:
        date_str: Date string to check
        target_year: Target fiscal year
        strict: If True, requires exact match. If False, allows year in date string.
        
    Returns:
        True if matches, False otherwise
    """
    if not date_str:
        return False
    
    # Extract year from date string
    year = extract_year_from_date(date_str)
    if year is None:
        return False
    
    if strict:
        # Strict match: year must exactly equal target year
        return year == target_year
    else:
        # Lenient match: check if target year appears in date string
        return str(target_year) in str(date_str) and year == target_year


def parse_end_date_for_fiscal_year(end_date: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse fiscal year from end date string.
    
    Returns both calendar year and calculated fiscal year.
    
    Args:
        end_date: Fiscal year end date string
        
    Returns:
        Tuple of (calendar_year, fiscal_year)
    """
    dt = parse_date(end_date)
    if not dt:
        return None, None
    
    calendar_year = dt.year
    month = dt.month
    
    # Calculate fiscal year
    # If end date is in Q1 (Jan-Mar), likely belongs to previous FY
    fiscal_year = calendar_year
    if month <= 3:
        # Might be previous fiscal year, but need more context
        # For now, assume same year unless we have fiscal year end month info
        pass
    
    return calendar_year, fiscal_year

