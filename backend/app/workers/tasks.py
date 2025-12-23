"""
PATH: backend/app/workers/tasks.py
PURPOSE:
  - Celery task definitions
  - SEC crawling, XBRL ingestion, factor computation

ROLE IN ARCHITECTURE:
  - Background task definitions
"""

import logging
from typing import Optional, List

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def crawl_company_task(self, ticker: str, cik: str, years: int = 20) -> dict:
    """
    Crawl SEC filings for a single company.
    
    This task is rate-limited to 10/s to comply with SEC API limits.
    Runs in parallel across 4 workers.
    
    Args:
        ticker: Company ticker symbol
        cik: Company CIK number
        years: Number of years to look back
        
    Returns:
        dict with crawl results
    """
    try:
        logger.info(f"Starting crawl for {ticker} (CIK: {cik})")
        
        # Import here to avoid circular imports
        # These would be ported from the existing src/ingestion modules
        # from src.ingestion.sec_crawler import crawl_company_filings
        
        # Placeholder - actual implementation would call existing crawler
        # filings = crawl_company_filings(cik, ticker, years=years)
        
        result = {
            "ticker": ticker,
            "cik": cik,
            "status": "success",
            "filings_count": 0,  # Would be len(filings)
        }
        
        logger.info(f"Completed crawl for {ticker}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Crawl failed for {ticker}: {e}")
        self.retry(countdown=60, exc=e)


@celery_app.task(bind=True, max_retries=2)
def ingest_xbrl_task(self, cik: str, fiscal_years: List[int]) -> dict:
    """
    Ingest XBRL financial facts for a company.
    
    Args:
        cik: Company CIK number
        fiscal_years: List of fiscal years to ingest
        
    Returns:
        dict with ingestion results
    """
    try:
        logger.info(f"Starting XBRL ingest for CIK {cik}")
        
        # Placeholder - actual implementation would call existing ingestor
        # from src.ingestion.xbrl_ingestor import ingest_company_xbrl
        # facts = ingest_company_xbrl(cik, fiscal_years)
        
        result = {
            "cik": cik,
            "status": "success",
            "years_ingested": len(fiscal_years),
        }
        
        logger.info(f"Completed XBRL ingest for CIK {cik}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"XBRL ingest failed for CIK {cik}: {e}")
        self.retry(countdown=30, exc=e)


@celery_app.task(bind=True)
def compute_factors_task(self, company_year_id: int, force: bool = False) -> dict:
    """
    Compute R&D factors for a company-year.
    
    Args:
        company_year_id: Database ID of company_year_core record
        force: Whether to recompute existing factors
        
    Returns:
        dict with computation results
    """
    try:
        logger.info(f"Computing factors for company_year_id {company_year_id}")
        
        # Placeholder - actual implementation would call existing factor engine
        # from src.factors.rd.rd_factor_engine import compute_rd_factors
        
        result = {
            "company_year_id": company_year_id,
            "status": "success",
            "factors_computed": ["rd_intensity", "rd_tone_score"],
        }
        
        logger.info(f"Completed factor computation for {company_year_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Factor computation failed for {company_year_id}: {e}")
        raise


@celery_app.task
def batch_crawl_companies(company_list: List[dict], years: int = 20) -> dict:
    """
    Dispatch crawl tasks for multiple companies.
    
    Args:
        company_list: List of dicts with ticker and cik
        years: Years to look back
        
    Returns:
        dict with batch status
    """
    from celery import group
    
    tasks = [
        crawl_company_task.s(c["ticker"], c["cik"], years)
        for c in company_list
    ]
    
    job = group(tasks)
    result = job.apply_async()
    
    return {
        "batch_id": result.id,
        "total_companies": len(company_list),
        "status": "dispatched",
    }
