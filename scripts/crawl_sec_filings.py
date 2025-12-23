"""Crawl SEC filings for pilot companies."""
# Setup path - must be first
import _setup_path  # noqa: F401

import time
from src.ingestion.universe_builder import get_pilot_companies
from src.ingestion.sec_crawler import crawl_company_filings
from src.db.connection import db_session_scope
from src.models.orm.company import Company
from src.models.orm.annual_report import AnnualReport
from src.models.orm.company_year_core import CompanyYearCore
from src.logging.logger import get_logger

logger = get_logger(__name__)


def crawl_and_store_filings():
    """Crawl SEC filings for all pilot companies and store in DB."""
    companies = get_pilot_companies()
    logger.info(f"Crawling filings for {len(companies)} companies")
    
    with db_session_scope() as session:
        for company_data in companies:
            ticker = company_data["ticker"]
            cik = company_data["cik"]
            name = company_data["name"]
            
            logger.info(f"Processing {ticker} ({name})")
            
            # Get or create company
            company = session.query(Company).filter_by(ticker=ticker).first()
            if not company:
                company = Company(
                    ticker=ticker,
                    cik=cik,
                    name=name,
                )
                session.add(company)
                session.commit()
            
            # Crawl filings
            filings_data = crawl_company_filings(cik, ticker, years=3)  # Last 3 years for testing
            
            for filing in filings_data:
                # Check if annual_report already exists by accession_id
                existing_report = session.query(AnnualReport).filter_by(
                    cik=cik,
                    accession_id=filing["accession_id"]
                ).first()
                
                if existing_report:
                    logger.info(f"Filing already exists: {filing['accession_id']}")
                    continue
                
                # Get or create company_year_core
                company_year = session.query(CompanyYearCore).filter_by(
                    company_id=company.id,
                    fiscal_year=filing["fiscal_year"]
                ).first()
                
                if not company_year:
                    company_year = CompanyYearCore(
                        company_id=company.id,
                        ticker=ticker,
                        cik=cik,
                        fiscal_year=filing["fiscal_year"],
                        filing_date=filing["filing_date"],
                        sec_accession_id=filing["accession_id"],
                        report_path=filing["file_path"],
                        report_hash=filing["file_hash"],
                    )
                    session.add(company_year)
                    session.flush()  # Flush to get the ID
                else:
                    # Update existing company_year with new filing info
                    company_year.filing_date = filing["filing_date"]
                    company_year.sec_accession_id = filing["accession_id"]
                    company_year.report_path = filing["file_path"]
                    company_year.report_hash = filing["file_hash"]
                
                # Check if annual_report already exists for this company_year_id
                existing_annual = session.query(AnnualReport).filter_by(
                    company_year_id=company_year.id
                ).first()
                
                if existing_annual:
                    # Update existing annual_report
                    existing_annual.cik = cik
                    existing_annual.fiscal_year = filing["fiscal_year"]
                    existing_annual.filing_date = filing["filing_date"]
                    existing_annual.accession_id = filing["accession_id"]
                    existing_annual.file_path = filing["file_path"]
                    existing_annual.file_hash = filing["file_hash"]
                    existing_annual.file_size_bytes = filing["file_size_bytes"]
                    existing_annual.file_format = filing.get("file_format", "html")
                    logger.info(f"Updated filing: {ticker} {filing['fiscal_year']}")
                else:
                    # Create new annual_report
                    annual_report = AnnualReport(
                        company_year_id=company_year.id,
                        cik=cik,
                        fiscal_year=filing["fiscal_year"],
                        filing_date=filing["filing_date"],
                        accession_id=filing["accession_id"],
                        file_path=filing["file_path"],
                        file_hash=filing["file_hash"],
                        file_size_bytes=filing["file_size_bytes"],
                        file_format=filing.get("file_format", "html"),
                        extraction_status="pending",
                    )
                    session.add(annual_report)
                    logger.info(f"Stored filing: {ticker} {filing['fiscal_year']}")
                
                session.commit()
            
            time.sleep(2)  # Rate limiting between companies


if __name__ == "__main__":
    crawl_and_store_filings()

