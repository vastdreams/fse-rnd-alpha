"""SEC filing crawler - download 10-K annual reports."""
import os
import time
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from config.settings import get_settings
from src.logging.logger import get_logger
from src.utils.rate_limiter import get_sec_rate_limiter
from src.ingestion.url_validator import validate_sec_filing_url
from src.ingestion.sec_submissions_api import get_company_10k_filings
from src.ai.client import call_gpt

logger = get_logger(__name__)
settings = get_settings()

SEC_BASE_URL = "https://www.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"


def get_sec_headers() -> Dict[str, str]:
    """Get headers for SEC API requests."""
    return {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def get_company_submissions(cik: str) -> Optional[Dict]:
    """
    Get company submissions from SEC using modern JSON API (preferred) or HTML fallback.
    
    First tries the modern JSON API, falls back to HTML parsing if needed.
    
    Args:
        cik: Company CIK
        
    Returns:
        Dictionary with 'cik' and 'filings' list, or None on error
    """
    # Try modern JSON API first (preferred method)
    try:
        json_result = get_company_10k_filings(cik, max_filings=5)
        if json_result and json_result.get("filings"):
            logger.info(f"Successfully fetched {len(json_result['filings'])} filings using JSON API for CIK {cik}")
            return json_result
        elif json_result:
            # JSON API worked but no filings found
            logger.info(f"JSON API returned no filings for CIK {cik}")
            return json_result
    except Exception as e:
        logger.warning(f"JSON API failed for CIK {cik}, falling back to HTML parsing: {e}")
    
    # Fallback to HTML parsing if JSON API fails or returns no results
    logger.info(f"Using HTML parsing fallback for CIK {cik}")
    return _get_company_submissions_html(cik)


def _get_company_submissions_html(cik: str) -> Optional[Dict]:
    """
    Fallback method: Get company submissions using HTML parsing.
    
    This is kept as fallback in case JSON API is unavailable.
    """
    # Apply rate limiting
    rate_limiter = get_sec_rate_limiter()
    rate_limiter.acquire()
    
    cik_clean = cik.lstrip("0")
    url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar?action=getcompany&CIK={cik_clean}&type=10-K&dateb=&owner=exclude&count=100"
    
    try:
        headers = get_sec_headers()
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML - look for all possible table structures
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        filings = []
        
        # Method 1: Find all links that contain "10-K" or accession numbers
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Look for accession numbers in href or text
            if "accession" in href.lower() or ("10-k" in text.lower() and len(text) > 10):
                # Try to extract accession
                accession = None
                if "accession_number=" in href:
                    accession = href.split("accession_number=")[1].split("&")[0]
                elif "accession-number=" in href:
                    accession = href.split("accession-number=")[1].split("&")[0]
                elif text and len(text.replace("-", "")) == 20:  # Accession format
                    accession = text.replace("-", "")
                
                if accession:
                    # Find the parent row to get date
                    row = link.find_parent("tr")
                    if row:
                        cols = row.find_all("td")
                        if len(cols) >= 4:
                            date_str = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                            filing_type = cols[0].get_text(strip=True) if cols else "10-K"
                            
                            filings.append({
                                "filing_type": filing_type,
                                "date": date_str,
                                "accession": accession,
                                "href": href
                            })
        
        # Method 2: Try table parsing as fallback
        if not filings:
            table = soup.find("table")
            if table:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        filing_type = cols[0].get_text(strip=True)
                        if "10-K" in filing_type:
                            link = row.find("a", href=True)
                            if link:
                                href = link.get("href", "")
                                # Try to get accession from various places
                                accession = None
                                if "accession" in href:
                                    if "=" in href:
                                        accession = href.split("=")[-1].split("&")[0]
                                else:
                                    # Look in the link text
                                    link_text = link.get_text(strip=True)
                                    if link_text and len(link_text.replace("-", "")) >= 15:
                                        accession = link_text.replace("-", "")
                                
                                date_str = cols[-1].get_text(strip=True) if len(cols) > 3 else ""
                                
                                if accession:
                                    filings.append({
                                        "filing_type": filing_type,
                                        "date": date_str,
                                        "accession": accession,
                                        "href": href
                                    })
        
        if filings:
            # Remove duplicates and sort by date
            seen = set()
            unique_filings = []
            for f in filings:
                acc = f.get("accession", "")
                if acc and acc not in seen:
                    seen.add(acc)
                    unique_filings.append(f)
            
            filings_sorted = sorted(unique_filings, key=lambda x: x.get("date", ""), reverse=True)
            logger.info(f"Found {len(filings_sorted)} 10-K filings using HTML parsing for CIK {cik}")
            return {"cik": cik, "filings": filings_sorted[:5]}
        
        logger.warning(f"No 10-K filings found for CIK {cik}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching submissions via HTML for CIK {cik}: {e}")
        return None


def get_filing_document_url(cik: str, accession: str, ticker: Optional[str] = None) -> Optional[str]:
    """Get the URL for the main 10-K document (narrative version, not XBRL-only)."""
    accession_clean = accession.replace("-", "")
    cik_padded = cik.zfill(10)

    # Prefer complete submission text file if reachable
    candidate_txt_url = f"{SEC_ARCHIVES_URL}/{cik_padded}/{accession_clean}/{accession}.txt"
    try:
        head_resp = requests.head(candidate_txt_url, headers=get_sec_headers(), timeout=10, allow_redirects=True)
        if head_resp.status_code == 200:
            size = int(head_resp.headers.get("Content-Length", "0") or 0)
            if size > 500000:  # likely full narrative
                logger.info(f"Selected complete submission text file: {candidate_txt_url} (size {size} bytes)")
                return candidate_txt_url
    except Exception as e:
        logger.debug(f"Complete submission txt check failed: {e}")

    index_url = f"{SEC_ARCHIVES_URL}/{cik_padded}/{accession_clean}/index.html"
    logger.info(f"Fetching index page: {index_url}")

    rate_limiter = get_sec_rate_limiter()
    rate_limiter.acquire()

    try:
        resp = requests.get(index_url, headers=get_sec_headers(), timeout=10)
        if resp.status_code == 200:
            if "Search Filings" in resp.text or "search-filings" in resp.url:
                logger.warning(f"Got redirected to search page for {accession}")
                return None

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            doc_links = []

            # Parse table rows to read file descriptions and sizes (when present)
            for row in soup.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                link_tag = row.find("a", href=True)
                if not link_tag:
                    continue

                href = link_tag.get("href", "")
                text = link_tag.get_text(strip=True)
                description = cells[2].get_text(strip=True).lower() if len(cells) >= 3 else ""
                size_bytes = 0
                try:
                    size_text = cells[-1].get_text(strip=True).replace(",", "")
                    if size_text.isdigit():
                        size_bytes = int(size_text)
                except Exception:
                    size_bytes = 0

                if not (href.endswith(".htm") or href.endswith(".html")):
                    continue

                href_lower = href.lower()

                # Skip navigation/search/exhibit-like files
                if any(x in href_lower for x in ["/search/", "search.htm", "search.html", "search-filings", "/edgar/quickedgar", "quickedgar.htm"]):
                    continue
                if any(x in href_lower for x in ["ex-", "exhibit", "cover", "summary", "graphic", "xsl", "xsd"]):
                    continue
                if href_lower == "index.htm" or href_lower == "index.html" or href_lower.endswith("/index.htm") or href_lower.endswith("/index.html"):
                    continue
                if href_lower.startswith("/") and "/archives/" not in href_lower and "/edgar/" not in href_lower:
                    continue
                if "index" in href_lower:
                    continue

                priority = 0
                # Highest: complete submission / full text
                if "complete submission" in description or "complete text" in description:
                    priority = 12
                # Prefer main 10-K narrative (non-xbrl HTML)
                elif ("10-k" in href_lower or "10k" in href_lower) and "ixbrl" not in href_lower and "xbrl" not in href_lower:
                    priority = 9
                # Allow .txt complete file when large
                elif href_lower.endswith(".txt"):
                    priority = 8
                elif ticker and href_lower.startswith(ticker.lower()) and "ixbrl" not in href_lower:
                    priority = 7
                elif href_lower.startswith(accession_clean.lower()):
                    priority = 5
                elif len(href) > 10 and "/archives/" in href_lower:
                    priority = 2

                # Deprioritize obvious XBRL-only files
                if any(x in href_lower for x in ["ixbrl", "xbrl", "r1.htm", "r2.htm"]) or any(x in description for x in ["xbrl", "ixbrl"]):
                    priority = max(0, priority - 6)

                if priority > 0:
                    doc_links.append((priority, size_bytes, href, text, description))

            # Prefer complete submission text file if available
            complete_rows = [
                (p, sz, h, t, d) for (p, sz, h, t, d) in doc_links
                if "complete submission" in (d or "")
            ]
            if complete_rows:
                # pick largest complete submission file
                complete_rows.sort(key=lambda x: x[1], reverse=True)
                doc_href = complete_rows[0][2]
                if doc_href.startswith("/"):
                    full_url = f"{SEC_BASE_URL}{doc_href}"
                elif doc_href.startswith("http"):
                    full_url = doc_href
                else:
                    full_url = f"{SEC_ARCHIVES_URL}/{cik_padded}/{accession_clean}/{doc_href}"
                logger.info(f"Selected complete submission file: {full_url}")
                return full_url

            # Fallback: simple link parsing if table parsing failed
            if not doc_links:
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if href in ["/", "/index.htm", "/index.html", "index.htm", "index.html"]:
                        continue
                    if not (href.endswith(".htm") or href.endswith(".html")):
                        continue
                    href_lower = href.lower()
                    if any(x in href_lower for x in ["/search/", "search.htm", "search-filings", "/edgar/quickedgar", "quickedgar.htm"]):
                        continue
                    if any(x in href_lower for x in ["ex-", "exhibit", "cover", "summary", "graphic", "xsl", "xsd"]):
                        continue
                    if href_lower.startswith("/") and "/archives/" not in href_lower and "/edgar/" not in href_lower:
                        continue

                    priority = 0
                    if "10-k" in href_lower or "10k" in href_lower:
                        priority = 3
                    elif ticker and href_lower.startswith(ticker.lower()):
                        priority = 2
                    elif href_lower.startswith(accession_clean.lower()):
                        priority = 2
                    if priority > 0:
                        doc_links.append((priority, 0, href, text, ""))

            if doc_links:
                # Sort by priority then size (descending)
                doc_links.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _, _, doc_href, _, _ = doc_links[0]

                if doc_href.startswith("/"):
                    full_url = f"{SEC_BASE_URL}{doc_href}"
                elif doc_href.startswith("http"):
                    full_url = doc_href
                else:
                    full_url = f"{SEC_ARCHIVES_URL}/{cik_padded}/{accession_clean}/{doc_href}"

                logger.info(f"Found document URL: {full_url} (priority: {doc_links[0][0]})")
                return full_url

            logger.warning(f"No document links found in index for {accession}")
        else:
            logger.warning(f"Index page returned status {resp.status_code} for {accession}")
    except Exception as e:
        logger.error(f"Error fetching index for {accession}: {e}")

    # Fallback: try common document names
    common_names = [
        f"{accession_clean}.htm",
        f"{accession_clean}.html",
        "a10k.htm",
        "10k.htm",
        "10-k.htm",
        "d10k.htm",
    ]

    for doc_name in common_names:
        url = f"{SEC_ARCHIVES_URL}/{cik_padded}/{accession_clean}/{doc_name}"
        try:
            resp = requests.head(url, headers=get_sec_headers(), timeout=5)
            if resp.status_code == 200:
                logger.info(f"Found document at fallback URL: {url}")
                return url
        except Exception as e:
            logger.debug(f"Fallback URL {url} failed: {e}")
            continue

    logger.error(f"Could not find document URL for accession {accession}")
    return None


def download_filing(url: str, save_path: Path, max_retries: int = 3, validate_url: bool = True) -> bool:
    """
    Download a filing document with retry logic and URL validation.
    
    Args:
        url: URL to download
        save_path: Path to save the file
        max_retries: Maximum number of retry attempts
        validate_url: Whether to validate URL before download (default: True)
        
    Returns:
        True if download successful, False otherwise
    """
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    from requests.exceptions import HTTPError, Timeout, ConnectionError, RequestException
    
    # Pre-validate URL before attempting download
    if validate_url:
        headers = get_sec_headers()
        is_valid, error_msg = validate_sec_filing_url(url, headers, multi_stage=True)
        if not is_valid:
            logger.error(f"URL validation failed, skipping download: {error_msg}")
            return False
    
    # Retry logic with comprehensive error handling
    def should_retry(exception):
        """Determine if an exception should trigger a retry."""
        if isinstance(exception, HTTPError):
            # Retry on server errors and rate limits
            status_code = exception.response.status_code if hasattr(exception, 'response') else None
            return status_code in [429, 500, 502, 503, 504]
        if isinstance(exception, (Timeout, ConnectionError)):
            return True
        if isinstance(exception, RequestException):
            # Retry on network errors
            return True
        return False
    
    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=False  # Don't re-raise, handle gracefully
    )
    def _download_with_retry():
        # Apply rate limiting before download
        rate_limiter = get_sec_rate_limiter()
        rate_limiter.acquire()
        
        response = requests.get(url, headers=get_sec_headers(), timeout=60, allow_redirects=True)
        response.raise_for_status()
        return response
    
    try:
        response = _download_with_retry()
        
        if response is None:
            logger.error(f"Download failed after {max_retries} retries: {url}")
            return False
        
        # Check if we got redirected to search page
        if "Search Filings" in response.text or "search-filings" in response.url:
            logger.error(f"Download redirected to search page: {response.url}")
            return False
        
        # Check file size (suspiciously small files might be errors)
        content_size = len(response.content)
        if content_size < 1024:  # Less than 1KB
            logger.warning(f"Downloaded file is suspiciously small ({content_size} bytes): {url}")
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check disk space before writing
        try:
            stat = os.statvfs(save_path.parent)
            free_space = stat.f_bavail * stat.f_frsize
            if free_space < content_size * 2:  # Need at least 2x file size free
                logger.error(f"Insufficient disk space to save file: {save_path}")
                return False
        except AttributeError:
            # Windows doesn't have statvfs, skip check
            pass
        
        # Write file
        try:
            save_path.write_bytes(response.content)
        except PermissionError as e:
            logger.error(f"Permission denied writing to {save_path}: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error writing to {save_path}: {e}")
            return False

        # Quick content sanity check to avoid XBRL-only files when we expect narrative
        try:
            sample_text = response.text[:6000]
            sample_lower = sample_text.lower()
            xbrl_tags = sample_lower.count("<ix:") + sample_lower.count("xbrl") + sample_lower.count("nonnumeric")
            readable_chars = sum(1 for c in sample_lower if c.isalpha())
            is_xbrl_heavy = xbrl_tags > 50 and readable_chars < 2000

            # Optional GPT mini guard to classify content
            def gpt_guard(text: str) -> Optional[bool]:
                prompt = (
                    "You are validating a downloaded SEC filing document. "
                    "Decide if this snippet is the main human-readable 10-K narrative (YES) "
                    "or an XBRL/exhibit/index/search page (NO). "
                    "Respond with a single word: YES or NO.\n\n"
                    f"Snippet:\n{text[:2500]}"
                )
                try:
                    resp = call_gpt(prompt=prompt, model="gpt-4o-mini", temperature=0, max_tokens=3)
                    if not resp or not hasattr(resp, "content"):
                        return None
                    answer = str(resp.content).strip().upper()
                    if answer.startswith("Y"):
                        return True
                    if answer.startswith("N"):
                        return False
                    return None
                except Exception as e:
                    logger.debug(f"GPT guard failed: {e}")
                    return None

            if is_xbrl_heavy:
                logger.warning(f"Downloaded file appears to be XBRL-heavy (possibly not the narrative doc): {save_path}")
                guard = gpt_guard(sample_text)
                if guard is False:
                    logger.error(f"GPT guard flagged non-narrative content for {save_path}; halting use of this file.")
                    return False
        except Exception as e:
            logger.debug(f"Content validation skipped for {save_path}: {e}")
        
        logger.info(f"Downloaded filing to {save_path} ({len(response.content)} bytes)")
        return True
        
    except HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        logger.error(f"HTTP error downloading {url}: {status_code} - {e}")
        return False
    except Timeout as e:
        logger.error(f"Timeout downloading {url} after {max_retries} attempts: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error downloading {url}: {e}")
        return False
    except RequestException as e:
        logger.error(f"Request error downloading {url} after {max_retries} attempts: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}", exc_info=True)
        return False


def calculate_file_hash(file_path: Path, timeout_seconds: int = 300) -> str:
    """
    Calculate SHA256 hash of file with error handling and timeout.
    
    Args:
        file_path: Path to file to hash
        timeout_seconds: Maximum time to spend hashing (default 5 minutes)
        
    Returns:
        SHA256 hash string in format "sha256:..."
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
        TimeoutError: If hashing takes too long
        OSError: For other file system errors
    """
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout_context(seconds):
        """Context manager for timeout handling."""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"File hash calculation timed out after {seconds} seconds")
        
        # Set up signal handler for timeout (Unix only)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Windows doesn't support SIGALRM, skip timeout
            yield
    
    # Validate file exists and is readable
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"Cannot read file: {file_path}")
    
    # Calculate hash with timeout protection
    sha256_hash = hashlib.sha256()
    file_size = file_path.stat().st_size
    
    # For very large files, log progress
    if file_size > 100 * 1024 * 1024:  # > 100MB
        logger.info(f"Hashing large file: {file_path.name} ({file_size / (1024*1024):.1f} MB)")
    
    try:
        # Use timeout context if available (Unix)
        if hasattr(signal, 'SIGALRM'):
            with timeout_context(timeout_seconds):
                with open(file_path, "rb") as f:
                    bytes_read = 0
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                        bytes_read += len(byte_block)
                        
                        # Log progress for very large files
                        if file_size > 100 * 1024 * 1024 and bytes_read % (10 * 1024 * 1024) == 0:
                            progress = (bytes_read / file_size) * 100
                            logger.debug(f"Hashing progress: {progress:.1f}%")
        else:
            # Windows - no timeout support, but still calculate hash
            with open(file_path, "rb") as f:
                bytes_read = 0
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    bytes_read += len(byte_block)
        
        hash_value = f"sha256:{sha256_hash.hexdigest()}"
        logger.debug(f"File hash calculated: {hash_value[:20]}... for {file_path.name}")
        return hash_value
        
    except FileNotFoundError:
        raise
    except PermissionError:
        raise
    except TimeoutError:
        raise
    except Exception as e:
        logger.error(f"Error calculating file hash for {file_path}: {e}")
        raise OSError(f"Failed to calculate file hash: {e}") from e


def crawl_company_filings(cik: str, ticker: str, years: int = 5) -> List[Dict]:
    """Crawl SEC filings for a company and download 10-Ks."""
    logger.info(f"Crawling filings for {ticker} (CIK: {cik})")
    
    submissions = get_company_submissions(cik)
    if not submissions or not submissions.get("filings"):
        logger.warning(f"No filings found for {ticker}")
        return []
    
    filings_data = []
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "annual_reports" / cik
    
    for filing in submissions["filings"][:years]:
        accession = filing.get("accession")
        if not accession:
            continue
        
        # Get document URL
        doc_url = get_filing_document_url(cik, accession, ticker=ticker)
        if not doc_url:
            logger.warning(f"Could not find document URL for {accession}")
            continue
        
        # Determine fiscal year from date
        date_str = filing.get("date", "")
        try:
            filing_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            fiscal_year = filing_date.year
        except:
            try:
                # Try alternative date format
                filing_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                fiscal_year = filing_date.year
            except:
                fiscal_year = None
        
        # Save path
        year_dir = data_dir / str(fiscal_year) if fiscal_year else data_dir
        file_ext = ".txt" if doc_url.lower().endswith(".txt") else ".html"
        filename = f"{ticker.lower()}_10k_{fiscal_year}{file_ext}" if fiscal_year else f"{ticker.lower()}_10k_{accession}{file_ext}"
        save_path = year_dir / filename
        
        # Check if already downloaded and valid
        should_download = True
        if save_path.exists():
            # Check if file is actually a 10-K or just SEC search page
            try:
                with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                    preview = f.read(1000).lower()
                    if "search filings" in preview or ("sec.gov" in preview and "10-k" not in preview and "form 10-k" not in preview):
                        logger.warning(f"Existing file appears to be SEC search page, will re-download: {save_path}")
                        save_path.unlink()  # Delete invalid file
                    else:
                        logger.info(f"File already exists and looks valid: {save_path}")
                        file_hash = calculate_file_hash(save_path)
                        should_download = False
            except Exception as e:
                logger.warning(f"Error checking existing file, will re-download: {e}")
                if save_path.exists():
                    save_path.unlink()
        
        if should_download:
            # Download (rate limiting is handled inside download_filing)
            validate_url = not doc_url.lower().endswith(".txt")
            if download_filing(doc_url, save_path, validate_url=validate_url):
                file_hash = calculate_file_hash(save_path)
            else:
                logger.error(f"Failed to download {doc_url}")
                continue
        
        # Determine file format from file extension
        file_format = "html"
        if save_path.suffix.lower() == ".pdf":
            file_format = "pdf"
        elif save_path.suffix.lower() in [".htm", ".html"]:
            file_format = "html"
        elif save_path.suffix.lower() == ".txt":
            file_format = "txt"
        
        filings_data.append({
            "cik": cik,
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_date": filing_date,
            "accession_id": accession,
            "file_path": str(save_path.relative_to(Path(__file__).parent.parent.parent)),
            "file_hash": file_hash,
            "file_size_bytes": save_path.stat().st_size if save_path.exists() else 0,
            "file_format": file_format,
        })
    
    return filings_data

