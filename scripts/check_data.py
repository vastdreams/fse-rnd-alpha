"""Check if data exists in database."""
import _setup_path  # noqa: F401

from src.db.connection import db_session_scope
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.text_factor_rd import TextFactorRD
from sqlalchemy import func

with db_session_scope() as session:
    companies = session.query(func.count(Company.id)).scalar()
    company_years = session.query(func.count(CompanyYearCore.id)).scalar()
    financials_core = session.query(func.count(FinancialsCore.id)).scalar()
    ratios = session.query(func.count(FinancialsRatios.id)).scalar()
    text_factors = session.query(func.count(TextFactorRD.id)).scalar()
    
    print(f"Companies: {companies}")
    print(f"Company Years: {company_years}")
    print(f"FinancialsCore: {financials_core}")
    print(f"Financial Ratios: {ratios}")
    print(f"Text Factors: {text_factors}")
    
    # Check if we have joined data
    joined = session.query(CompanyYearCore).join(
        FinancialsRatios
    ).join(TextFactorRD).count()
    print(f"Company Years with both ratios and text factors: {joined}")
    
    # Show sample
    if joined > 0:
        sample = session.query(CompanyYearCore).join(
            FinancialsRatios
        ).join(TextFactorRD).first()
        print(f"\nSample data:")
        print(f"  Ticker: {sample.ticker}")
        print(f"  Year: {sample.fiscal_year}")
        print(f"  R&D Intensity: {sample.financials_ratios.rd_intensity}")
        print(f"  R&D Tone: {sample.text_factor_rd.rd_tone_score}")

