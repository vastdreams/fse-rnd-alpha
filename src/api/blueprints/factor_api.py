"""Factor API endpoints."""
from flask import Blueprint, jsonify
from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.text_factor_rd import TextFactorRD
from src.logging.logger import get_logger

logger = get_logger(__name__)
factor_api_bp = Blueprint("factor_api", __name__, url_prefix="/api/factors")


@factor_api_bp.route("/rd/summary", methods=["GET"])
def get_rd_summary():
    """Get R&D factor summary for all companies."""
    with db_session_scope() as session:
        # Get all company years with text factors (ratios optional)
        company_years = session.query(CompanyYearCore).join(
            TextFactorRD
        ).all()
        
        summary = []
        for cy in company_years:
            if cy.text_factor_rd:
                # Calculate R&D intensity from financials if available
                rd_intensity = None
                if cy.financials_ratios and cy.financials_ratios.rd_intensity is not None:
                    rd_intensity = cy.financials_ratios.rd_intensity
                elif cy.financials_core and cy.financials_core.revenue and cy.financials_core.revenue > 0:
                    # Calculate on the fly if we have raw financials
                    rd_expense = cy.financials_core.rd_expense or 0
                    rd_intensity = rd_expense / cy.financials_core.revenue if cy.financials_core.revenue > 0 else None
                
                summary.append({
                    "ticker": cy.ticker,
                    "year": cy.fiscal_year,
                    "rd_intensity": rd_intensity,
                    "rd_tone_score": cy.text_factor_rd.rd_tone_score,
                    "rd_mentions": cy.text_factor_rd.rd_mentions_count,
                    "rd_focus_tags": cy.text_factor_rd.rd_focus_tags or [],
                })
        
        return jsonify(summary)


@factor_api_bp.route("/rd/company/<ticker>", methods=["GET"])
def get_company_rd(ticker):
    """Get R&D factors for a specific company."""
    with db_session_scope() as session:
        company_years = session.query(CompanyYearCore).filter_by(
            ticker=ticker.upper()
        ).order_by(CompanyYearCore.fiscal_year.desc()).all()
        
        data = []
        for cy in company_years:
            item = {
                "year": cy.fiscal_year,
                "ticker": cy.ticker,
            }
            
            if cy.financials_ratios:
                item["rd_intensity"] = cy.financials_ratios.rd_intensity
                item["rd_expense"] = cy.financials_core.rd_expense if cy.financials_core else None
                item["revenue"] = cy.financials_core.revenue if cy.financials_core else None
            
            if cy.text_factor_rd:
                item["rd_tone_score"] = cy.text_factor_rd.rd_tone_score
                item["rd_mentions"] = cy.text_factor_rd.rd_mentions_count
                item["rd_focus_tags"] = cy.text_factor_rd.rd_focus_tags or []
                item["rd_key_paragraphs"] = cy.text_factor_rd.rd_key_paragraphs or []
            
            data.append(item)
        
        return jsonify(data)

