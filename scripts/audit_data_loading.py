"""Audit script to check why data isn't loading in the dashboard."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.db.connection import db_session_scope
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.annual_report import AnnualReport
from sqlalchemy import func, desc
from src.logging.logger import get_logger

logger = get_logger(__name__)


def audit_data_loading():
    """Audit why data isn't loading."""
    print("=" * 80)
    print("DATA LOADING AUDIT")
    print("=" * 80)
    
    with db_session_scope() as session:
        # 1. Check companies
        companies = session.query(Company).all()
        print(f"\n1. COMPANIES: {len(companies)} total")
        if companies:
            print(f"   Sample companies:")
            for c in companies[:5]:
                print(f"     - {c.ticker}: {c.name} (ID: {c.id})")
        
        # 2. Check company years
        company_years = session.query(CompanyYearCore).all()
        print(f"\n2. COMPANY YEARS: {len(company_years)} total")
        if company_years:
            # Group by company
            by_company = {}
            for cy in company_years:
                if cy.ticker not in by_company:
                    by_company[cy.ticker] = []
                by_company[cy.ticker].append(cy.fiscal_year)
            
            print(f"   Companies with years: {len(by_company)}")
            for ticker, years in list(by_company.items())[:5]:
                print(f"     - {ticker}: {sorted(years)}")
        
        # 3. Check financials
        financials = session.query(FinancialsCore).all()
        print(f"\n3. FINANCIALS CORE: {len(financials)} total")
        
        # 4. Check ratios
        ratios = session.query(FinancialsRatios).all()
        print(f"\n4. FINANCIALS RATIOS: {len(ratios)} total")
        
        # 5. Check text factors
        text_factors = session.query(TextFactorRD).all()
        print(f"\n5. TEXT FACTORS R&D: {len(text_factors)} total")
        
        # 6. Check annual reports
        reports = session.query(AnnualReport).all()
        print(f"\n6. ANNUAL REPORTS: {len(reports)} total")
        
        # 7. Test API endpoint logic
        print(f"\n7. TESTING API ENDPOINT LOGIC:")
        companies_list = session.query(Company).all()
        result = []
        for company in companies_list[:3]:  # Test with first 3
            latest_cy = session.query(CompanyYearCore).filter_by(
                company_id=company.id
            ).order_by(desc(CompanyYearCore.fiscal_year)).first()
            
            stats = {
                "id": company.id,
                "ticker": company.ticker,
                "name": company.name,
                "cik": company.cik,
                "sector": latest_cy.sector if latest_cy else None,
                "industry": latest_cy.industry if latest_cy else None,
            }
            
            year_count = session.query(func.count(CompanyYearCore.id)).filter_by(
                company_id=company.id
            ).scalar()
            stats["years_available"] = year_count
            result.append(stats)
        
        print(f"   API would return {len(result)} companies (sample):")
        for r in result:
            print(f"     - {r['ticker']}: {r['name']} ({r['years_available']} years)")
        
        # 8. Check for missing relationships
        print(f"\n8. CHECKING RELATIONSHIPS:")
        companies_without_years = []
        for company in companies[:10]:
            cy_count = session.query(func.count(CompanyYearCore.id)).filter_by(
                company_id=company.id
            ).scalar()
            if cy_count == 0:
                companies_without_years.append(company.ticker)
        
        if companies_without_years:
            print(f"   WARNING: {len(companies_without_years)} companies have no company years:")
            print(f"     {companies_without_years[:5]}")
        else:
            print(f"   ✓ All sampled companies have company years")
        
        # 9. Check R&D summary endpoint logic
        print(f"\n9. TESTING R&D SUMMARY ENDPOINT:")
        company_years_with_rd = session.query(CompanyYearCore).join(
            TextFactorRD
        ).limit(5).all()
        print(f"   Company years with R&D factors: {len(company_years_with_rd)}")
        if company_years_with_rd:
            for cy in company_years_with_rd[:3]:
                rd_intensity = None
                if cy.financials_ratios and cy.financials_ratios.rd_intensity is not None:
                    rd_intensity = cy.financials_ratios.rd_intensity
                elif cy.financials_core and cy.financials_core.revenue and cy.financials_core.revenue > 0:
                    rd_expense = cy.financials_core.rd_expense or 0
                    rd_intensity = rd_expense / cy.financials_core.revenue if cy.financials_core.revenue > 0 else None
                
                print(f"     - {cy.ticker} {cy.fiscal_year}: intensity={rd_intensity}, tone={cy.text_factor_rd.rd_tone_score if cy.text_factor_rd else None}")
        
        print("\n" + "=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    audit_data_loading()

