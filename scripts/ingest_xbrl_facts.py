"""Ingest XBRL financial facts and store in database."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.ingestion.xbrl_ingestor import ingest_company_xbrl
from src.db.connection import db_session_scope
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.logging.logger import get_logger

logger = get_logger(__name__)


def ingest_financials():
    """Ingest XBRL financial facts for all companies in DB (all years)."""
    with db_session_scope() as session:
        company_rows = session.query(Company).all()
        logger.info(f"Ingesting financials for {len(company_rows)} companies")
        
        for company in company_rows:
            ticker = company.ticker
            cik = company.cik
            logger.info(f"Processing {ticker}")
            
            company_years = session.query(CompanyYearCore).filter_by(
                company_id=company.id
            ).all()
            if not company_years:
                logger.warning(f"No company years found for {ticker}")
                continue
            
            fiscal_years = [cy.fiscal_year for cy in company_years if cy.fiscal_year]
            if not fiscal_years:
                logger.warning(f"No fiscal years for {ticker}")
                continue
            
            all_facts = ingest_company_xbrl(cik, fiscal_years)
            
            for year, facts in all_facts.items():
                company_year = next((cy for cy in company_years if cy.fiscal_year == year), None)
                if not company_year:
                    continue
                
                financials = session.query(FinancialsCore).filter_by(
                    company_year_id=company_year.id
                ).first()
                if not financials:
                    financials = FinancialsCore(company_year_id=company_year.id)
                    session.add(financials)
                
                for field, value in facts.items():
                    if hasattr(financials, field):
                        setattr(financials, field, value)
            
            session.commit()
            logger.info(f"Stored financials for {ticker}: years={sorted(fiscal_years)}")


if __name__ == "__main__":
    ingest_financials()

