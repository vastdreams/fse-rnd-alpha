"""Portfolio attribution and factor exposure analysis."""
from typing import List, Dict
import pandas as pd
from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.logging.logger import get_logger

logger = get_logger(__name__)


def calculate_portfolio_exposures(
    portfolio: Dict[str, float],
    formation_year: int
) -> Dict[str, float]:
    """Calculate weighted factor exposures for a portfolio."""
    exposures = {
        "rd_intensity": 0.0,
        "rd_tone": 0.0,
        "roe": 0.0,
        "net_margin": 0.0,
        "debt_to_equity": 0.0,
        "fcf_margin": 0.0,
    }
    
    with db_session_scope() as session:
        total_weight = 0.0
        
        for ticker, weight in portfolio.items():
            if weight == 0:
                continue
            
            company_year = session.query(CompanyYearCore).filter_by(
                ticker=ticker,
                fiscal_year=formation_year
            ).first()
            
            if not company_year:
                continue
            
            # R&D intensity
            if company_year.financials_ratios and company_year.financials_ratios.rd_intensity:
                exposures["rd_intensity"] += weight * company_year.financials_ratios.rd_intensity
            
            # R&D tone
            if company_year.text_factor_rd and company_year.text_factor_rd.rd_tone_score is not None:
                exposures["rd_tone"] += weight * company_year.text_factor_rd.rd_tone_score
            
            # Financial metrics
            if company_year.financials_ratios:
                if company_year.financials_ratios.roe:
                    exposures["roe"] += weight * company_year.financials_ratios.roe
                if company_year.financials_ratios.net_margin:
                    exposures["net_margin"] += weight * company_year.financials_ratios.net_margin
                if company_year.financials_ratios.debt_to_equity:
                    exposures["debt_to_equity"] += weight * company_year.financials_ratios.debt_to_equity
                if company_year.financials_ratios.fcf_margin:
                    exposures["fcf_margin"] += weight * company_year.financials_ratios.fcf_margin
            
            total_weight += abs(weight)
        
        # Normalize if needed
        if total_weight > 0:
            for key in exposures:
                exposures[key] = exposures[key] / total_weight if total_weight > 0 else 0
    
    return exposures


def attribute_portfolio_return(
    portfolio_return: float,
    exposures: Dict[str, float],
    factor_returns: Dict[str, float]
) -> Dict[str, float]:
    """Attribute portfolio return to factor exposures."""
    attribution = {}
    
    for factor, exposure in exposures.items():
        if factor in factor_returns:
            attribution[factor] = exposure * factor_returns[factor]
        else:
            attribution[factor] = 0.0
    
    # Residual (unexplained)
    explained = sum(attribution.values())
    attribution["residual"] = portfolio_return - explained
    
    return attribution


def calculate_factor_correlations(
    formation_year: int,
    universe: List[str]
) -> pd.DataFrame:
    """Calculate correlation matrix between factors."""
    with db_session_scope() as session:
        company_years = session.query(CompanyYearCore).filter(
            CompanyYearCore.fiscal_year == formation_year,
            CompanyYearCore.ticker.in_(universe)
        ).all()
        
        data = []
        for cy in company_years:
            row = {"ticker": cy.ticker}
            
            if cy.financials_ratios:
                row["rd_intensity"] = cy.financials_ratios.rd_intensity
                row["roe"] = cy.financials_ratios.roe
                row["net_margin"] = cy.financials_ratios.net_margin
                row["fcf_margin"] = cy.financials_ratios.fcf_margin
            
            if cy.text_factor_rd:
                row["rd_tone"] = cy.text_factor_rd.rd_tone_score
            
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Calculate correlation
        numeric_cols = df.select_dtypes(include=[float]).columns
        if len(numeric_cols) > 1:
            return df[numeric_cols].corr()
    
    return pd.DataFrame()

