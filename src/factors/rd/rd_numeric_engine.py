"""R&D numeric engine - compute R&D intensity and trends from financials."""
from typing import Optional, List
from src.db.connection import db_session_scope
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.company_year_core import CompanyYearCore
from src.logging.logger import get_logger

logger = get_logger(__name__)


def compute_rd_numeric_factors(company_year_id: int) -> Optional[FinancialsRatios]:
    """Compute R&D numeric factors (intensity, change, trend) from financials."""
    with db_session_scope() as session:
        company_year = session.query(CompanyYearCore).filter_by(id=company_year_id).first()
        if not company_year:
            return None
        
        financials = company_year.financials_core
        if not financials:
            return None
        
        # Get or create ratios record
        ratios = session.query(FinancialsRatios).filter_by(company_year_id=company_year_id).first()
        if not ratios:
            ratios = FinancialsRatios(company_year_id=company_year_id)
            session.add(ratios)
        
        # Calculate R&D intensity
        if financials.rd_expense and financials.revenue and financials.revenue > 0:
            ratios.rd_intensity = financials.rd_expense / financials.revenue
        
        # Calculate R&D change YoY (need previous year)
        if company_year.fiscal_year:
            prev_year = session.query(CompanyYearCore).filter_by(
                company_id=company_year.company_id,
                fiscal_year=company_year.fiscal_year - 1
            ).first()
            
            if prev_year and prev_year.financials_core and prev_year.financials_core.rd_expense:
                if financials.rd_expense:
                    ratios.rd_change_yoy = (
                        (financials.rd_expense - prev_year.financials_core.rd_expense) /
                        prev_year.financials_core.rd_expense
                    )
        
        # Calculate 3-year trend (simplified - would need 3 years of data)
        # For now, just set to None
        
        session.commit()
        return ratios

