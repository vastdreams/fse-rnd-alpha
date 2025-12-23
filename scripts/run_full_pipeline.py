"""Run full pipeline: crawl -> ingest -> compute."""
# Setup path - must be first
import _setup_path  # noqa: F401

from scripts.crawl_sec_filings import crawl_and_store_filings
from scripts.ingest_xbrl_facts import ingest_financials
from scripts.compute_financials_core import compute_all_ratios
from scripts.compute_rd_factors import compute_all_rd_factors
from src.logging.logger import get_logger

logger = get_logger(__name__)


def run_pipeline():
    """Run the full data pipeline."""
    logger.info("Starting full pipeline...")
    
    # Step 1: Crawl SEC filings
    logger.info("Step 1: Crawling SEC filings...")
    crawl_and_store_filings()
    
    # Step 2: Ingest XBRL financials
    logger.info("Step 2: Ingesting XBRL financials...")
    ingest_financials()
    
    # Step 3: Compute financial ratios
    logger.info("Step 3: Computing financial ratios...")
    compute_all_ratios()
    
    # Step 4: Compute R&D factors
    logger.info("Step 4: Computing R&D factors...")
    compute_all_rd_factors()
    
    logger.info("Pipeline completed!")


if __name__ == "__main__":
    run_pipeline()
