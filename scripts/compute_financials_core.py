"""Compute financial ratios from financials core."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.financials.ratios import calculate_ratios
from src.logging.logger import get_logger

logger = get_logger(__name__)


def compute_all_ratios():
    """Compute ratios for all company years with financials."""
    with db_session_scope() as session:
        company_years = session.query(CompanyYearCore).join(FinancialsCore).all()
        logger.info(f"Computing ratios for {len(company_years)} company years")
        
        for company_year in company_years:
            financials = company_year.financials_core
            if not financials:
                continue
            
            # Calculate ratios
            ratios_dict = calculate_ratios(financials)
            
            # Get or create ratios record
            ratios = session.query(FinancialsRatios).filter_by(
                company_year_id=company_year.id
            ).first()
            
            if not ratios:
                ratios = FinancialsRatios(company_year_id=company_year.id)
                session.add(ratios)
            
            # Update ratios
            for field, value in ratios_dict.items():
                if hasattr(ratios, field):
                    setattr(ratios, field, value)
            
            session.commit()
            logger.info(f"Computed ratios for {company_year.ticker} {company_year.fiscal_year}")


if __name__ == "__main__":
    compute_all_ratios()

