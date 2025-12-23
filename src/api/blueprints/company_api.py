"""Comprehensive company data API endpoints."""
from flask import Blueprint, jsonify, send_file
from src.db.connection import db_session_scope
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.annual_report import AnnualReport
from src.models.orm.text_chunk import TextChunk
from src.models.orm.price import Price
from sqlalchemy import func, desc
from src.logging.logger import get_logger
import os

logger = get_logger(__name__)
company_api_bp = Blueprint("company_api", __name__, url_prefix="/api/companies")


@company_api_bp.route("/", methods=["GET"])
def list_companies():
    """List all companies with summary stats."""
    with db_session_scope() as session:
        companies = session.query(Company).all()
        result = []
        for company in companies:
            # Get latest company year
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
            
            # Count years
            year_count = session.query(func.count(CompanyYearCore.id)).filter_by(
                company_id=company.id
            ).scalar()
            stats["years_available"] = year_count
            
            result.append(stats)
        
        return jsonify(result)


@company_api_bp.route("/<ticker>", methods=["GET"])
def get_company_detail(ticker):
    """Get comprehensive company details."""
    ticker_upper = ticker.upper()
    logger.info(f"Fetching company detail for ticker: {ticker_upper}")
    
    with db_session_scope() as session:
        company = session.query(Company).filter_by(ticker=ticker_upper).first()
        if not company:
            # Log available tickers for debugging
            all_tickers = [c.ticker for c in session.query(Company).all()]
            logger.warning(f"Company {ticker_upper} not found. Available tickers: {all_tickers}")
            return jsonify({"error": f"Company {ticker_upper} not found", "available_tickers": all_tickers}), 404
        
        # Get all company years
        company_years = session.query(CompanyYearCore).filter_by(
            company_id=company.id
        ).order_by(desc(CompanyYearCore.fiscal_year)).all()
        
        years_data = []
        for cy in company_years:
            year_data = {
                "fiscal_year": cy.fiscal_year,
                "filing_date": cy.filing_date.isoformat() if cy.filing_date else None,
                "sector": cy.sector,
                "industry": cy.industry,
                "sec_accession_id": cy.sec_accession_id,
            }
            
            # Financials
            if cy.financials_core:
                fc = cy.financials_core
                year_data["financials"] = {
                    "income_statement": {
                        "revenue": fc.revenue,
                        "cost_of_revenue": fc.cost_of_revenue,
                        "gross_profit": fc.gross_profit,
                        "rd_expense": fc.rd_expense,
                        "sga_expense": fc.sga_expense,
                        "operating_income": fc.operating_income,
                        "ebit": fc.ebit,
                        "interest_expense": fc.interest_expense,
                        "pretax_income": fc.pretax_income,
                        "income_tax": fc.income_tax,
                        "net_income": fc.net_income,
                        "eps_basic": fc.eps_basic,
                        "eps_diluted": fc.eps_diluted,
                    },
                    "balance_sheet": {
                        "total_assets": fc.total_assets,
                        "cash_and_equivalents": fc.cash_and_equivalents,
                        "short_term_investments": fc.short_term_investments,
                        "accounts_receivable": fc.accounts_receivable,
                        "inventory": fc.inventory,
                        "ppe_net": fc.ppe_net,
                        "goodwill": fc.goodwill,
                        "intangible_assets": fc.intangible_assets,
                        "total_liabilities": fc.total_liabilities,
                        "short_term_debt": fc.short_term_debt,
                        "long_term_debt": fc.long_term_debt,
                        "total_equity": fc.total_equity,
                        "retained_earnings": fc.retained_earnings,
                    },
                    "cash_flow": {
                        "cash_from_operations": fc.cash_from_operations,
                        "cash_from_investing": fc.cash_from_investing,
                        "cash_from_financing": fc.cash_from_financing,
                        "capex": fc.capex,
                        "depreciation_amortization": fc.depreciation_amortization,
                        "dividends_paid": fc.dividends_paid,
                        "share_repurchases": fc.share_repurchases,
                    },
                    "currency": fc.currency,
                    "quality_flag": fc.quality_flag,
                }
            
            # Ratios
            if cy.financials_ratios:
                fr = cy.financials_ratios
                year_data["ratios"] = {
                    "profitability": {
                        "gross_margin": fr.gross_margin,
                        "operating_margin": fr.operating_margin,
                        "net_margin": fr.net_margin,
                        "roe": fr.roe,
                        "roa": fr.roa,
                        "roic": fr.roic,
                    },
                    "leverage": {
                        "debt_to_equity": fr.debt_to_equity,
                        "debt_to_assets": fr.debt_to_assets,
                        "interest_coverage": fr.interest_coverage,
                    },
                    "liquidity": {
                        "current_ratio": fr.current_ratio,
                        "quick_ratio": fr.quick_ratio,
                        "working_capital": fr.working_capital,
                    },
                    "cash_flow": {
                        "cfo_to_net_income": fr.cfo_to_net_income,
                        "fcf": fr.fcf,
                        "fcf_margin": fr.fcf_margin,
                        "dividend_coverage": fr.dividend_coverage,
                        "cash_conversion": fr.cash_conversion,
                    },
                    "growth": {
                        "revenue_growth_yoy": fr.revenue_growth_yoy,
                        "eps_growth_yoy": fr.eps_growth_yoy,
                        "fcf_growth_yoy": fr.fcf_growth_yoy,
                    },
                    "rd_specific": {
                        "rd_intensity": fr.rd_intensity,
                        "rd_change_yoy": fr.rd_change_yoy,
                        "rd_3y_trend": fr.rd_3y_trend,
                    },
                }
            
            # Text factors
            if cy.text_factor_rd:
                tf = cy.text_factor_rd
                year_data["rd_text_factors"] = {
                    "tone_score": tf.rd_tone_score,
                    "mentions_count": tf.rd_mentions_count,
                    "section_length_words": tf.rd_section_length_words,
                    "reporting_style": tf.rd_reporting_style,
                    "focus_tags": tf.rd_focus_tags or [],
                    "key_paragraphs": tf.rd_key_paragraphs or [],
                    "extraction_version": tf.extraction_version,
                    "extraction_timestamp": tf.extraction_timestamp,
                }
            
            # Annual report info
            report = session.query(AnnualReport).filter_by(
                company_year_id=cy.id
            ).first()
            if report:
                # Determine file format from file_path
                file_format = "html"
                if report.file_path:
                    if report.file_path.endswith(".pdf"):
                        file_format = "pdf"
                    elif report.file_path.endswith(".html") or report.file_path.endswith(".htm"):
                        file_format = "html"
                
                year_data["annual_report"] = {
                    "report_path": report.file_path or cy.report_path,
                    "file_size_bytes": report.file_size_bytes,
                    "file_format": file_format,
                    "download_url": f"/api/companies/{ticker}/reports/{cy.fiscal_year}/download",
                }
            
            years_data.append(year_data)
        
        # Price data summary
        price_data = session.query(
            func.min(Price.date).label("first_date"),
            func.max(Price.date).label("last_date"),
            func.count(Price.id).label("price_points"),
        ).filter_by(ticker=ticker.upper()).first()
        
        result = {
            "company": {
                "id": company.id,
                "ticker": company.ticker,
                "name": company.name,
                "cik": company.cik,
            },
            "years": years_data,
            "price_data": {
                "first_date": price_data.first_date.isoformat() if price_data and price_data.first_date else None,
                "last_date": price_data.last_date.isoformat() if price_data and price_data.last_date else None,
                "price_points": price_data.price_points if price_data else 0,
            },
        }
        
        return jsonify(result)


@company_api_bp.route("/<ticker>/financials/<int:year>", methods=["GET"])
def get_company_financials(ticker, year):
    """Get financials for a specific company year."""
    with db_session_scope() as session:
        cy = session.query(CompanyYearCore).filter_by(
            ticker=ticker.upper(),
            fiscal_year=year
        ).first()
        
        if not cy:
            return jsonify({"error": "Company year not found"}), 404
        
        result = {}
        if cy.financials_core:
            result["financials"] = {
                "income_statement": {k: v for k, v in cy.financials_core.__dict__.items() 
                                  if k in ["revenue", "cost_of_revenue", "gross_profit", "rd_expense", 
                                          "sga_expense", "operating_income", "ebit", "interest_expense",
                                          "pretax_income", "income_tax", "net_income", "eps_basic", "eps_diluted"]},
                "balance_sheet": {k: v for k, v in cy.financials_core.__dict__.items()
                                if k in ["total_assets", "cash_and_equivalents", "short_term_investments",
                                        "accounts_receivable", "inventory", "ppe_net", "goodwill",
                                        "intangible_assets", "total_liabilities", "short_term_debt",
                                        "long_term_debt", "total_equity", "retained_earnings"]},
                "cash_flow": {k: v for k, v in cy.financials_core.__dict__.items()
                            if k in ["cash_from_operations", "cash_from_investing", "cash_from_financing",
                                    "capex", "depreciation_amortization", "dividends_paid", "share_repurchases"]},
            }
        
        return jsonify(result)


@company_api_bp.route("/<ticker>/reports/<int:year>/download", methods=["GET"])
def download_report(ticker, year):
    """Download annual report file."""
    from pathlib import Path
    import os
    
    with db_session_scope() as session:
        cy = session.query(CompanyYearCore).filter_by(
            ticker=ticker.upper(),
            fiscal_year=year
        ).first()
        
        if not cy:
            logger.error(f"Company year not found: {ticker} {year}")
            return jsonify({"error": "Company year not found"}), 404
        
        report = session.query(AnnualReport).filter_by(
            company_year_id=cy.id
        ).first()
        
        # Check both report.file_path and company_year.report_path
        report_path_str = None
        if report and report.file_path:
            report_path_str = report.file_path
        elif cy.report_path:
            report_path_str = cy.report_path
        
        if not report_path_str:
            logger.error(f"No report path found for {ticker} {year}")
            return jsonify({"error": "Report path not found"}), 404
        
        # Check if it's a URL (shouldn't be, but handle it)
        if report_path_str.startswith("http://") or report_path_str.startswith("https://"):
            logger.error(f"Report path is a URL, not a file path: {report_path_str}")
            return jsonify({"error": "Invalid report path (URL instead of file path)"}), 500
        
        # Make absolute path
        project_root = Path(__file__).parent.parent.parent.parent
        report_path = Path(report_path_str)
        
        # If relative, make it relative to project root
        if not report_path.is_absolute():
            abs_path = project_root / report_path
        else:
            abs_path = report_path
        
        # Normalize the path
        abs_path = abs_path.resolve()
        
        logger.info(f"Attempting to download: {abs_path}")
        
        if not abs_path.exists():
            logger.error(f"Report file not found on disk: {abs_path}")
            # Try alternative path construction
            # Files are stored as: data/raw/annual_reports/{cik}/{year}/{ticker}_10k_{year}.html
            alt_path = project_root / "data" / "raw" / "annual_reports" / cy.cik / str(year) / f"{ticker.lower()}_10k_{year}.html"
            if alt_path.exists():
                abs_path = alt_path
                logger.info(f"Found file at alternative path: {abs_path}")
            else:
                return jsonify({"error": f"Report file not found on disk: {abs_path}"}), 404
        
        # Determine file format
        file_format = "html"
        if str(abs_path).endswith(".pdf"):
            file_format = "pdf"
        elif str(abs_path).endswith(".htm"):
            file_format = "html"
        
        # Verify it's actually a file and not a directory
        if not abs_path.is_file():
            logger.error(f"Path is not a file: {abs_path}")
            return jsonify({"error": "Invalid file path"}), 500
        
        logger.info(f"Serving file: {abs_path} ({abs_path.stat().st_size} bytes)")
        
        return send_file(
            str(abs_path),
            as_attachment=True,
            download_name=f"{ticker}_{year}_10K.{file_format}",
            mimetype="text/html" if file_format == "html" else "application/pdf",
        )


@company_api_bp.route("/<ticker>/text-chunks/<int:year>", methods=["GET"])
def get_text_chunks(ticker, year):
    """Get text chunks for a company year."""
    with db_session_scope() as session:
        cy = session.query(CompanyYearCore).filter_by(
            ticker=ticker.upper(),
            fiscal_year=year
        ).first()
        
        if not cy:
            return jsonify({"error": "Company year not found"}), 404
        
        report = session.query(AnnualReport).filter_by(
            company_year_id=cy.id
        ).first()
        
        if not report:
            return jsonify({"error": "Report not found"}), 404
        
        chunks = session.query(TextChunk).filter_by(
            annual_report_id=report.id
        ).order_by(TextChunk.chunk_id).all()
        
        result = []
        for chunk in chunks:
            result.append({
                "chunk_id": chunk.chunk_id,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_id": chunk.section_id,
                "section_title": chunk.section_title,
                "text_content": chunk.text_content,
                "token_count": chunk.token_count,
            })
        
        return jsonify(result)


@company_api_bp.route("/<ticker>/prices", methods=["GET"])
def get_company_prices(ticker):
    """Get price data for a company."""
    with db_session_scope() as session:
        prices = session.query(Price).filter_by(
            ticker=ticker.upper()
        ).order_by(Price.date).all()
        
        result = []
        for price in prices:
            result.append({
                "date": price.date.isoformat(),
                "open": price.open,
                "high": price.high,
                "low": price.low,
                "close": price.close,
                "volume": price.volume,
                "adjusted_close": price.adjusted_close,
            })
        
        return jsonify(result)


@company_api_bp.route("/stats/summary", methods=["GET"])
def get_stats_summary():
    """Get comprehensive statistics summary."""
    with db_session_scope() as session:
        stats = {
            "companies": {
                "total": session.query(func.count(Company.id)).scalar(),
                "with_financials": session.query(func.count(CompanyYearCore.id)).join(
                    FinancialsCore
                ).scalar(),
                "with_ratios": session.query(func.count(CompanyYearCore.id)).join(
                    FinancialsRatios
                ).scalar(),
                "with_text_factors": session.query(func.count(CompanyYearCore.id)).join(
                    TextFactorRD
                ).scalar(),
            },
            "company_years": {
                "total": session.query(func.count(CompanyYearCore.id)).scalar(),
                "with_financials": session.query(func.count(CompanyYearCore.id)).join(
                    FinancialsCore
                ).scalar(),
                "with_ratios": session.query(func.count(CompanyYearCore.id)).join(
                    FinancialsRatios
                ).scalar(),
                "with_text_factors": session.query(func.count(CompanyYearCore.id)).join(
                    TextFactorRD
                ).scalar(),
            },
            "annual_reports": {
                "total": session.query(func.count(AnnualReport.id)).scalar(),
                "total_size_bytes": session.query(func.sum(AnnualReport.file_size_bytes)).scalar() or 0,
            },
            "text_chunks": {
                "total": session.query(func.count(TextChunk.id)).scalar(),
            },
            "prices": {
                "total_records": session.query(func.count(Price.id)).scalar(),
                "unique_tickers": session.query(func.count(func.distinct(Price.ticker))).scalar(),
            },
        }
        
        return jsonify(stats)

