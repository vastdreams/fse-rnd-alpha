"""Input validation utilities."""
import re
from typing import Optional
from src.utils.exceptions import ValidationError


def validate_ticker(ticker: str) -> str:
    """Validate and normalize ticker symbol."""
    if not ticker:
        raise ValidationError("Ticker cannot be empty")
    
    ticker = ticker.strip().upper()
    
    # Ticker should be 1-5 uppercase letters/numbers
    if not re.match(r"^[A-Z0-9]{1,5}$", ticker):
        raise ValidationError(f"Invalid ticker format: {ticker}")
    
    return ticker


def validate_cik(cik: str) -> str:
    """Validate and normalize CIK."""
    if not cik:
        raise ValidationError("CIK cannot be empty")
    
    # Remove leading zeros for validation, but keep original format
    cik_clean = cik.strip().lstrip("0")
    
    if not cik_clean.isdigit() or len(cik_clean) > 10:
        raise ValidationError(f"Invalid CIK format: {cik}")
    
    # Pad with leading zeros to 10 digits
    return cik.strip().zfill(10)


def validate_year(year: int, min_year: int = 1990, max_year: Optional[int] = None) -> int:
    """Validate fiscal year."""
    if max_year is None:
        from datetime import datetime
        max_year = datetime.now().year + 1
    
    if not isinstance(year, int):
        raise ValidationError(f"Year must be an integer, got: {type(year)}")
    
    if year < min_year or year > max_year:
        raise ValidationError(f"Year must be between {min_year} and {max_year}, got: {year}")
    
    return year


def validate_accession_id(accession: str) -> str:
    """Validate SEC accession number format."""
    if not accession:
        raise ValidationError("Accession ID cannot be empty")
    
    # Format: CIK-YYMMDDSSSS-XXXXXX
    pattern = r"^\d{10}-\d{2}\d{6}-\d{6}$"
    if not re.match(pattern, accession):
        raise ValidationError(f"Invalid accession ID format: {accession}")
    
    return accession.strip()


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got: {type(value)}")
    
    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()
