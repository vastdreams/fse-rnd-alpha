"""URL validation utilities for SEC filing downloads."""
import re
from typing import Optional, Tuple
from urllib.parse import urlparse
import requests
from src.logging.logger import get_logger
from src.utils.rate_limiter import get_sec_rate_limiter

logger = get_logger(__name__)


def validate_sec_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SEC URL before download (Stage 1: URL validation).
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is empty"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"
    
    # Must be HTTPS
    if parsed.scheme != "https":
        return False, f"URL must use HTTPS, got: {parsed.scheme}"
    
    # Must be from sec.gov
    if "sec.gov" not in parsed.netloc.lower():
        return False, f"URL must be from sec.gov domain, got: {parsed.netloc}"
    
    # Check for known bad patterns in URL
    bad_patterns = [
        "/search/",
        "/search-filings",
        "/edgar/quickedgar",
        "quickedgar.htm",
        "quickedgar.html",
        "index.htm",
        "index.html",
    ]
    
    url_lower = url.lower()
    for pattern in bad_patterns:
        if pattern in url_lower:
            return False, f"URL contains invalid pattern: {pattern}"
    
    # Check URL structure for SEC archives
    if "/archives/edgar/data/" not in url_lower:
        # Might be a valid SEC URL but not an archive URL
        logger.warning(f"URL does not appear to be an archive URL: {url}")
    
    return True, None


def validate_url_headers(url: str, headers: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validate URL by checking headers (Stage 2: Header validation).
    
    Args:
        url: URL to validate
        headers: Headers to use for request
        
    Returns:
        Tuple of (is_valid, error_message, response_headers)
    """
    # Apply rate limiting
    rate_limiter = get_sec_rate_limiter()
    rate_limiter.acquire()
    
    try:
        # HEAD request to check headers
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=False)
        
        # Check status code
        if response.status_code != 200:
            return False, f"URL returned status code {response.status_code}", None
        
        # Check content-type
        content_type = response.headers.get("Content-Type", "").lower()
        
        # Should be HTML or text
        if not any(ct in content_type for ct in ["text/html", "text/plain", "application/xhtml"]):
            logger.warning(f"Unexpected content type: {content_type}")
        
        # Check content-length (search pages are usually small)
        content_length = response.headers.get("Content-Length")
        if content_length:
            size = int(content_length)
            if size < 1024:  # Less than 1KB - suspiciously small
                return False, f"URL content too small ({size} bytes) - likely invalid", response.headers
        
        # Check for redirect to search page
        location = response.headers.get("Location", "")
        if location and ("search" in location.lower() or "quickedgar" in location.lower()):
            return False, f"URL redirects to search page: {location}", response.headers
        
        return True, None, response.headers
        
    except requests.Timeout:
        return False, "Request timed out", None
    except requests.RequestException as e:
        return False, f"Request failed: {e}", None
    except Exception as e:
        return False, f"Unexpected error: {e}", None


def validate_url_content_preview(url: str, headers: dict, preview_bytes: int = 2048) -> Tuple[bool, Optional[str]]:
    """
    Validate URL by checking content preview (Stage 3: Content preview).
    
    Args:
        url: URL to validate
        headers: Headers to use for request
        preview_bytes: Number of bytes to fetch for preview
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Apply rate limiting
    rate_limiter = get_sec_rate_limiter()
    rate_limiter.acquire()
    
    try:
        # GET request with range header to fetch only first bytes
        range_headers = headers.copy()
        range_headers["Range"] = f"bytes=0-{preview_bytes}"
        
        response = requests.get(url, headers=range_headers, timeout=10, allow_redirects=False)
        
        # Check status code (206 for partial content, 200 for full)
        if response.status_code not in [200, 206]:
            return False, f"Content preview returned status code {response.status_code}"
        
        # Check if redirected to search page
        if "Search Filings" in response.text:
            return False, "Content preview contains 'Search Filings' - likely search page"
        
        # Check if looks like SEC search/navigation page
        content_lower = response.text.lower()
        search_indicators = [
            "search filings",
            "quick edgar",
            "quickedgar",
            "edgar search",
        ]
        
        for indicator in search_indicators:
            if indicator in content_lower:
                return False, f"Content preview contains '{indicator}' - likely search page"
        
        # Check if has some content that looks like a 10-K
        # 10-Ks typically have company name, form 10-k, etc. in first 2KB
        positive_indicators = [
            "form 10-k",
            "form 10k",
            "annual report",
            "united states",
            "securities and exchange commission",
        ]
        
        has_positive = any(indicator in content_lower for indicator in positive_indicators)
        
        if not has_positive and len(response.text) > 500:
            # Might be valid but doesn't have clear indicators
            logger.warning(f"Content preview doesn't have clear 10-K indicators for {url}")
        
        return True, None
        
    except requests.Timeout:
        return False, "Content preview request timed out"
    except requests.RequestException as e:
        return False, f"Content preview request failed: {e}"
    except Exception as e:
        return False, f"Unexpected error during content preview: {e}"


def validate_sec_filing_url(url: str, headers: dict, multi_stage: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Multi-stage validation of SEC filing URL.
    
    Performs:
    1. URL structure validation
    2. Header validation (content-type, size)
    3. Content preview validation
    
    Args:
        url: URL to validate
        headers: Headers to use for requests
        multi_stage: If True, perform all validation stages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Stage 1: URL validation
    is_valid, error = validate_sec_url(url)
    if not is_valid:
        return False, f"URL validation failed: {error}"
    
    if not multi_stage:
        return True, None
    
    # Stage 2: Header validation
    is_valid, error, _ = validate_url_headers(url, headers)
    if not is_valid:
        return False, f"Header validation failed: {error}"
    
    # Stage 3: Content preview validation
    is_valid, error = validate_url_content_preview(url, headers)
    if not is_valid:
        return False, f"Content preview validation failed: {error}"
    
    logger.debug(f"URL passed all validation stages: {url[:80]}...")
    return True, None

