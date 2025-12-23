"""Compute R&D factors (numeric + text) for all company years using V2 extraction."""
# Setup path - must be first
import _setup_path  # noqa: F401

import argparse
from typing import List, Optional
from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.factors.rd.rd_numeric_engine import compute_rd_numeric_factors
from src.factors.rd.rd_text_engine import extract_rd_text_factors  # V1 (backward compatibility)
from src.factors.rd.rd_text_engine_v2 import extract_rd_text_factors_v2  # V2 (comprehensive)
from src.logging.logger import get_logger

logger = get_logger(__name__)


def compute_all_rd_factors(
    use_v2: bool = True,
    force_recompute: bool = False,
    company_year_ids: Optional[List[int]] = None,
):
    """Compute R&D factors.
    
    Args:
        use_v2: If True, use comprehensive V2 extraction. If False, use V1.
        force_recompute: If True, recompute even if already extracted.
        company_year_ids: Optional list of company_year_core IDs to process (default: all).
    """
    extraction_func = extract_rd_text_factors_v2 if use_v2 else extract_rd_text_factors
    version_str = "V2 (comprehensive)" if use_v2 else "V1 (legacy)"
    
    with db_session_scope() as session:
        q = session.query(CompanyYearCore)
        if company_year_ids:
            q = q.filter(CompanyYearCore.id.in_(company_year_ids))
        company_years = q.all()
        logger.info(f"Computing R&D factors for {len(company_years)} company years using {version_str}")
        
        for company_year in company_years:
            logger.info(f"Processing {company_year.ticker} {company_year.fiscal_year}")
            
            # Compute numeric factors
            try:
                compute_rd_numeric_factors(company_year.id)
                logger.info(f"Computed numeric R&D factors for {company_year.ticker} {company_year.fiscal_year}")
            except Exception as e:
                logger.error(f"Error computing numeric factors for {company_year.ticker} {company_year.fiscal_year}: {e}")
            
            # Extract text factors
            try:
                if use_v2:
                    result = extraction_func(company_year.id)
                    if result:
                        logger.info(
                            f"Extracted text R&D factors (V2) for {company_year.ticker} {company_year.fiscal_year}: "
                            f"{result.rd_mentions_count} mentions, confidence: {result.extraction_confidence:.2f}"
                        )
                    else:
                        logger.warning(f"No R&D factors extracted for {company_year.ticker} {company_year.fiscal_year}")
                else:
                    result = extraction_func(company_year.id)
                    if result:
                        logger.info(f"Extracted text R&D factors (V1) for {company_year.ticker} {company_year.fiscal_year}")
            except Exception as e:
                logger.error(f"Error extracting text factors for {company_year.ticker} {company_year.fiscal_year}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute R&D factors for all company years")
    parser.add_argument(
        "--v1",
        action="store_true",
        help="Use V1 extraction (legacy) instead of V2 (default: V2)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation even if already extracted"
    )
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated company_year_core IDs to process (default: all)",
    )
    
    args = parser.parse_args()
    
    ids_list = [int(x) for x in args.ids.split(",") if x.strip().isdigit()] if args.ids else None
    
    compute_all_rd_factors(
        use_v2=not args.v1,
        force_recompute=args.force,
        company_year_ids=ids_list,
    )

