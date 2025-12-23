# PATH: scripts/create_unified_filings_view.py
# PURPOSE:
#   - Create or replace a SQL VIEW `unified_filings` that joins companies,
#     company_year_core, and annual_reports for quick inspection.
#
# ROLE IN ARCHITECTURE:
#   - DB maintenance helper; makes a canonical read-only reference table.
#
# MAIN EXPORTS:
#   - create_view(): executes CREATE OR REPLACE VIEW unified_filings
#   - CLI entrypoint (python scripts/create_unified_filings_view.py)
#
# NON-RESPONSIBILITIES:
#   - Does NOT alter base tables or run ingestion.
#   - Does NOT perform factor computations.
#
# NOTES FOR FUTURE AI:
#   - Extend the SELECT with manifest status when/if stored in DB.
#   - If you add partitions, consider a MATERIALIZED VIEW plus refresh schedule.

# Setup path - must be first
import _setup_path  # noqa: F401

from sqlalchemy import text

from src.db.connection import db_session_scope
from src.logging.logger import get_logger

logger = get_logger(__name__)

VIEW_SQL = """
CREATE OR REPLACE VIEW unified_filings AS
SELECT
    cy.id               AS company_year_id,
    c.id                AS company_id,
    ar.id               AS annual_report_id,
    c.ticker            AS ticker,
    c.name              AS name,
    c.cik               AS cik,
    cy.fiscal_year      AS fiscal_year,
    cy.filing_date      AS filing_date,
    cy.sec_accession_id AS sec_accession_id,
    cy.report_path      AS report_path,
    cy.report_hash      AS report_hash,
    cy.data_version     AS data_version,
    ar.file_format      AS file_format,
    ar.file_size_bytes  AS file_size_bytes,
    ar.extraction_status AS extraction_status,
    ar.form_type        AS form_type,
    cy.created_at       AS created_at,
    cy.updated_at       AS updated_at
FROM company_year_core cy
JOIN companies c ON cy.company_id = c.id
LEFT JOIN annual_reports ar ON ar.company_year_id = cy.id;
"""


def create_view():
    """Create or replace the unified_filings SQL view."""
    with db_session_scope() as session:
        session.execute(text(VIEW_SQL))
        session.commit()
    logger.info("unified_filings view created/refreshed.")


if __name__ == "__main__":
    create_view()


