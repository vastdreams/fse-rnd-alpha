# PATH: src/ingestion/xbrl_ingestor.py
# PURPOSE:
#   - Fetch SEC CompanyFacts JSON and extract yearly financial facts for ingestion.
#
# ROLE IN ARCHITECTURE:
#   - Data ingestion layer for XBRL/CompanyFacts prior to DB persistence.
#
# MAIN EXPORTS:
#   - fetch_company_facts(): download and validate CompanyFacts JSON.
#   - extract_financial_facts(): map XBRL tags to canonical financial fields.
#   - ingest_company_xbrl(): orchestrate fetch + extract for requested fiscal years.
#
# NON-RESPONSIBILITIES:
#   - Does NOT write to database tables directly.
#   - Does NOT compute financial ratios or text factors.
#
# NOTES FOR FUTURE AI:
#   - If SEC responses omit a requested fiscal year, we currently fall back to the
#     most recent available year (<= target) to avoid empty financials; log clearly
#     when fallback is used. Replace with fresher data once newer CompanyFacts
#     are accessible.
"""XBRL ingestor - fetch CompanyFacts JSON from SEC and extract financial data."""
import json
import requests
from pathlib import Path
from typing import Dict, Optional, List
from config.settings import get_settings
from src.logging.logger import get_logger
from src.utils.date_utils import parse_date, calculate_fiscal_year, validate_fiscal_year_match
from src.ingestion.xbrl_schemas import validate_company_facts, validate_fact_structure
from src.ingestion.xbrl_tag_mapping import get_tag_mapper

logger = get_logger(__name__)
settings = get_settings()

SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def get_sec_headers() -> Dict[str, str]:
    """Get headers for SEC API requests."""
    return {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }


def fetch_company_facts(cik: str) -> Optional[Dict]:
    """
    Fetch CompanyFacts JSON for a given CIK with retry logic.
    
    Args:
        cik: Company CIK
        
    Returns:
        CompanyFacts JSON dictionary or None on error
    """
    from src.utils.cik_validation import normalize_cik, validate_cik
    from src.utils.rate_limiter import get_sec_rate_limiter
    from src.utils.retry_handler import retry_with_backoff
    from requests.exceptions import HTTPError, Timeout, ConnectionError, RequestException
    
    # Validate and normalize CIK
    if not validate_cik(cik):
        logger.error(f"Invalid CIK format: {cik}")
        return None
    
    try:
        cik_padded = normalize_cik(cik)
    except ValueError as e:
        logger.error(f"CIK normalization failed: {e}")
        return None
    
    url = SEC_COMPANYFACTS_URL.format(cik=cik_padded)
    
    @retry_with_backoff(
        max_attempts=3,
        initial_wait=2.0,
        max_wait=30.0,
        retryable_exceptions=[HTTPError, Timeout, ConnectionError, RequestException],
    )
    def _fetch_with_retry():
        # Apply rate limiting
        rate_limiter = get_sec_rate_limiter()
        rate_limiter.acquire()
        
        response = requests.get(url, headers=get_sec_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    
    try:
        data = _fetch_with_retry()
        
        if data:
            # Validate response structure
            validated = validate_company_facts(data)
            if validated:
                # Return validated data as dict (for compatibility)
                return data
            else:
                # Validation failed but data might still be usable
                logger.warning(f"CompanyFacts validation failed for CIK {cik}, using unvalidated data")
                return data
        
        return None
        
    except HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        if status_code == 404:
            logger.warning(f"CompanyFacts not found for CIK {cik}")
        else:
            logger.error(f"HTTP error fetching CompanyFacts for CIK {cik}: {status_code} - {e}")
        return None
    except Timeout:
        logger.error(f"Timeout fetching CompanyFacts for CIK {cik}")
        return None
    except ConnectionError as e:
        logger.error(f"Connection error fetching CompanyFacts for CIK {cik}: {e}")
        return None
    except RequestException as e:
        logger.error(f"Request error fetching CompanyFacts for CIK {cik}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching CompanyFacts for CIK {cik}: {e}", exc_info=True)
        return None


def save_company_facts(cik: str, data: Dict) -> Path:
    """Save CompanyFacts JSON to disk."""
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "xbrl"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = data_dir / f"CIK{cik}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved CompanyFacts to {file_path}")
    return file_path


def extract_financial_facts(company_facts: Dict, fiscal_year: int) -> Dict:
    """Extract financial facts for a specific fiscal year."""
    facts = company_facts.get("facts", {})
    extracted = {}
    company_cik = company_facts.get("cik")
    
    # Map of XBRL tags to canonical field names
    tag_mapping = {
        "us-gaap:Revenues": "revenue",
        "us-gaap:SalesRevenueNet": "revenue",
        "us-gaap:CostOfRevenue": "cost_of_revenue",
        "us-gaap:GrossProfit": "gross_profit",
        "us-gaap:ResearchAndDevelopmentExpense": "rd_expense",
        "us-gaap:SellingGeneralAndAdministrativeExpense": "sga_expense",
        "us-gaap:OperatingIncomeLoss": "operating_income",
        "us-gaap:IncomeBeforeEquityMethodInvestments": "ebit",
        "us-gaap:InterestExpense": "interest_expense",
        "us-gaap:IncomeBeforeTax": "pretax_income",
        "us-gaap:IncomeTaxExpenseBenefit": "income_tax",
        "us-gaap:NetIncomeLoss": "net_income",
        "us-gaap:EarningsPerShareBasic": "eps_basic",
        "us-gaap:EarningsPerShareDiluted": "eps_diluted",
        "us-gaap:Assets": "total_assets",
        "us-gaap:CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
        "us-gaap:ShortTermInvestments": "short_term_investments",
        "us-gaap:AccountsReceivableNetCurrent": "accounts_receivable",
        "us-gaap:InventoryNet": "inventory",
        "us-gaap:PropertyPlantAndEquipmentNet": "ppe_net",
        "us-gaap:Goodwill": "goodwill",
        "us-gaap:IntangibleAssetsNetExcludingGoodwill": "intangible_assets",
        "us-gaap:Liabilities": "total_liabilities",
        "us-gaap:ShortTermDebt": "short_term_debt",
        "us-gaap:LongTermDebt": "long_term_debt",
        "us-gaap:Equity": "total_equity",
        "us-gaap:RetainedEarningsAccumulatedDeficit": "retained_earnings",
        "us-gaap:NetCashProvidedByUsedInOperatingActivities": "cash_from_operations",
        "us-gaap:NetCashProvidedByUsedInInvestingActivities": "cash_from_investing",
        "us-gaap:NetCashProvidedByUsedInFinancingActivities": "cash_from_financing",
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment": "capex",
        "us-gaap:DepreciationDepletionAndAmortization": "depreciation_amortization",
        "us-gaap:PaymentsOfDividends": "dividends_paid",
    }
    
    # Process each GAAP taxonomy
    for taxonomy in ["us-gaap", "dei"]:
        if taxonomy not in facts:
            continue
        
        taxonomy_facts = facts[taxonomy]
        
        for tag, field_name in tag_mapping.items():
            tag_key = tag.split(":")[-1]  # CompanyFacts omits namespace prefixes
            if tag_key not in taxonomy_facts:
                continue
            
            tag_data = taxonomy_facts[tag_key]
            units = tag_data.get("units", {})
            
            # Look for USD values (prefer USD, then USD/shares, etc.)
            unit_key = None
            for key in ["USD", "USD/shares", "shares"]:
                if key in units:
                    unit_key = key
                    break
            
            if not unit_key:
                continue
            
            selected_value = None
            fallback_value = None
            fallback_year = None
            
            # Find value for the fiscal year, with fallback to latest <= target year
            for fact in units[unit_key]:
                end_date = fact.get("end", "")
                if not end_date:
                    continue
                
                # Skip quarterly data
                if "Q" in end_date.upper():
                    continue
                
                fact_fiscal_year = calculate_fiscal_year(end_date)
                
                # If parsing fails, try regex match on year to avoid false positives
                if not fact_fiscal_year:
                    import re
                    year_pattern = r"\b(19|20)\d{2}\b"
                    year_match = re.search(year_pattern, end_date)
                    if year_match:
                        fact_fiscal_year = int(year_match.group(0))
                
                value = fact.get("val")
                if value is None:
                    continue
                
                if fact_fiscal_year == fiscal_year:
                    selected_value = value
                    break
                
                if fact_fiscal_year and fact_fiscal_year <= fiscal_year:
                    if fallback_year is None or fact_fiscal_year > fallback_year:
                        fallback_year = fact_fiscal_year
                        fallback_value = value
            
            chosen_value = selected_value
            if chosen_value is None and fallback_value is not None:
                chosen_value = fallback_value
                logger.warning(
                    {
                        "component": "xbrl_ingestor",
                        "function": "extract_financial_facts",
                        "event_type": "fallback",
                        "cik": company_cik,
                        "requested_fiscal_year": fiscal_year,
                        "fallback_year": fallback_year,
                        "field": field_name,
                    }
                )
            
            if chosen_value is not None:
                try:
                    extracted[field_name] = float(chosen_value)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value to float: {chosen_value} for {field_name}")
    
    return extracted


def ingest_company_xbrl(cik: str, fiscal_years: List[int]) -> Dict:
    """Ingest XBRL data for a company and extract facts for specified years."""
    logger.info(f"Ingesting XBRL for CIK {cik}")
    
    # Fetch CompanyFacts
    company_facts = fetch_company_facts(cik)
    if not company_facts:
        return {}
    
    # Save raw JSON
    save_company_facts(cik, company_facts)
    
    # Extract facts for each year
    all_facts = {}
    for year in fiscal_years:
        facts = extract_financial_facts(company_facts, year)
        if facts:
            all_facts[year] = facts
    
    return all_facts

