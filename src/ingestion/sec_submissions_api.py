"""SEC Submissions JSON API - modern API for getting company filings."""
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from config.settings import get_settings
from src.logging.logger import get_logger
from src.utils.rate_limiter import get_sec_rate_limiter
from src.utils.cik_validation import normalize_cik, validate_cik

logger = get_logger(__name__)
settings = get_settings()

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def get_sec_headers() -> Dict[str, str]:
    """Get headers for SEC API requests."""
    return {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }


def get_company_submissions_json(cik: str) -> Optional[Dict]:
    """
    Get company submissions using SEC's modern JSON API.
    
    This is more reliable than HTML parsing and provides structured data.
    
    Args:
        cik: Company CIK (will be normalized)
        
    Returns:
        Dictionary with company submissions data, or None on error
    """
    # Validate and normalize CIK
    if not validate_cik(cik):
        logger.error(f"Invalid CIK format: {cik}")
        return None
    
    try:
        cik_normalized = normalize_cik(cik)
    except ValueError as e:
        logger.error(f"CIK normalization failed: {e}")
        return None
    
    # Apply rate limiting
    rate_limiter = get_sec_rate_limiter()
    rate_limiter.acquire()
    
    url = SEC_SUBMISSIONS_URL.format(cik=cik_normalized)
    
    try:
        response = requests.get(url, headers=get_sec_headers(), timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if not isinstance(data, dict):
            logger.error(f"Invalid response format from SEC API: expected dict, got {type(data)}")
            return None
        
        if "filings" not in data:
            logger.warning(f"No 'filings' key in SEC API response for CIK {cik}")
            return data  # Return what we got, might still be useful
        
        logger.info(f"Successfully fetched submissions JSON for CIK {cik}")
        return data
        
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"CIK not found in SEC database: {cik}")
        else:
            logger.error(f"HTTP error fetching submissions for CIK {cik}: {e}")
        return None
    except requests.Timeout:
        logger.error(f"Timeout fetching submissions for CIK {cik}")
        return None
    except requests.RequestException as e:
        logger.error(f"Request error fetching submissions for CIK {cik}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from SEC API for CIK {cik}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching submissions for CIK {cik}: {e}", exc_info=True)
        return None


def extract_10k_filings_from_submissions(submissions: Dict, max_filings: int = 5) -> List[Dict]:
    """
    Extract 10-K filings from SEC submissions JSON response.
    
    Args:
        submissions: JSON response from SEC submissions API
        max_filings: Maximum number of filings to return
        
    Returns:
        List of filing dictionaries with form, date, accession, etc.
    """
    if not submissions or "filings" not in submissions:
        return []
    
    filings_data = submissions["filings"]
    
    # Handle both 'recent' and legacy formats
    if "recent" in filings_data:
        recent = filings_data["recent"]
    else:
        # Fallback for different response structure
        logger.warning("Submissions JSON doesn't have 'recent' key, trying alternate structure")
        recent = filings_data
    
    # Extract form types, dates, and accession numbers
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    report_dates = recent.get("reportDate", [])
    
    # Filter for 10-K filings
    ten_k_filings = []
    for i, form in enumerate(forms):
        if form and "10-K" in form.upper():
            # Ensure we have all required data
            if i < len(accession_numbers) and i < len(filing_dates):
                filing = {
                    "filing_type": form,
                    "date": filing_dates[i] if i < len(filing_dates) else "",
                    "accession": accession_numbers[i] if i < len(accession_numbers) else "",
                    "report_date": report_dates[i] if i < len(report_dates) else "",
                    "accession_number": accession_numbers[i] if i < len(accession_numbers) else "",
                }
                ten_k_filings.append(filing)
    
    # Sort by date (most recent first)
    ten_k_filings.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    logger.info(f"Found {len(ten_k_filings)} 10-K filings, returning first {max_filings}")
    return ten_k_filings[:max_filings]


def get_company_10k_filings(cik: str, max_filings: int = 5) -> Optional[Dict]:
    """
    Get 10-K filings for a company using SEC JSON API.
    
    This is the main function to use - it combines API fetch and parsing.
    
    Args:
        cik: Company CIK
        max_filings: Maximum number of filings to return
        
    Returns:
        Dictionary with 'cik' and 'filings' list, or None on error
    """
    submissions = get_company_submissions_json(cik)
    
    if not submissions:
        return None
    
    # Get company name if available
    company_name = submissions.get("name", "")
    entity_type = submissions.get("entityType", "")
    
    filings = extract_10k_filings_from_submissions(submissions, max_filings=max_filings)
    
    if not filings:
        logger.warning(f"No 10-K filings found for CIK {cik}")
        return None
    
    return {
        "cik": cik,
        "name": company_name,
        "entity_type": entity_type,
        "filings": filings,
    }

