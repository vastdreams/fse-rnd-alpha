"""Inspect actual data in database."""
import _setup_path  # noqa: F401

from src.db.connection import db_session_scope
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.annual_report import AnnualReport

with db_session_scope() as session:
    # Check text factors
    print("=== TEXT FACTORS ===")
    text_factors = session.query(TextFactorRD, CompanyYearCore).join(
        CompanyYearCore, TextFactorRD.company_year_id == CompanyYearCore.id
    ).limit(5).all()
    for tf, cy in text_factors:
        print(f"\n{cy.ticker} {cy.fiscal_year}:")
        print(f"  Tone Score: {tf.rd_tone_score}")
        print(f"  Mentions: {tf.rd_mentions_count}")
        print(f"  Focus Tags: {tf.rd_focus_tags}")
        print(f"  Key Paragraphs: {len(tf.rd_key_paragraphs) if tf.rd_key_paragraphs else 0} paragraphs")
    
    # Check annual reports
    print("\n=== ANNUAL REPORTS ===")
    reports = session.query(AnnualReport).join(CompanyYearCore).limit(3).all()
    for r in reports:
        cy = r.company_year_core
        print(f"\n{cy.ticker} {cy.fiscal_year}:")
        print(f"  Report Path: {r.report_path}")
        print(f"  File Size: {r.file_size_bytes} bytes" if r.file_size_bytes else "  File Size: N/A")
        print(f"  Text Chunks: {session.query().filter_by(annual_report_id=r.id).count() if hasattr(r, 'text_chunks') else 'N/A'}")

