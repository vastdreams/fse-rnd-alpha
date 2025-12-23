"""CIK (Central Index Key) validation and normalization utilities."""
import re
from typing import Optional
from src.logging.logger import get_logger

logger = get_logger(__name__)


def validate_cik(cik: str) -> bool:
    """
    Validate CIK format.
    
    CIK should be 1-10 digits.
    
    Args:
        cik: CIK string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not cik:
        return False
    
    cik_str = str(cik).strip()
    
    # CIK should be 1-10 digits
    pattern = r'^\d{1,10}$'
    is_valid = bool(re.match(pattern, cik_str))
    
    if not is_valid:
        logger.warning(f"Invalid CIK format: {cik} (must be 1-10 digits)")
    
    return is_valid


def normalize_cik(cik: str) -> str:
    """
    Normalize CIK to 10-digit format with leading zeros.
    
    Args:
        cik: CIK string (with or without leading zeros)
        
    Returns:
        10-digit CIK string with leading zeros
        
    Raises:
        ValueError: If CIK is invalid
    """
    if not cik:
        raise ValueError("CIK cannot be empty")
    
    cik_str = str(cik).strip()
    
    # Validate format
    if not validate_cik(cik_str):
        raise ValueError(f"Invalid CIK format: {cik}")
    
    # Remove leading zeros, then pad to 10 digits
    cik_clean = cik_str.lstrip("0") or "0"
    cik_padded = cik_clean.zfill(10)
    
    return cik_padded


def format_cik_for_sec_url(cik: str) -> str:
    """
    Format CIK for use in SEC URLs (10 digits with leading zeros).
    
    Args:
        cik: CIK string
        
    Returns:
        Formatted CIK for SEC URLs
    """
    return normalize_cik(cik)


def format_cik_for_api(cik: str) -> str:
    """
    Format CIK for SEC API calls (can use unpadded for some endpoints).
    
    Args:
        cik: CIK string
        
    Returns:
        Formatted CIK (10-digit padded)
    """
    return normalize_cik(cik)

