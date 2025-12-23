# PATH: src/api/blueprints/unified_api.py
# PURPOSE:
#   - Serve a unified "filings" dataset that joins companies, company_year_core,
#     and annual_reports for quick inspection and de-duplication.
#
# ROLE IN ARCHITECTURE:
#   - API layer to expose a master reference table for UI and exports.
#
# MAIN EXPORTS:
#   - GET /api/unified/filings       : paginated JSON of unified filings
#   - GET /api/unified/filings/export: CSV export of unified filings snapshot
#
# NON-RESPONSIBILITIES:
#   - Does NOT mutate data or trigger crawls/ingestion.
#   - Does NOT perform factor computations.
#
# NOTES FOR FUTURE AI:
#   - If manifest status is stored in DB later, extend the SELECT to include it.
#   - Keep limits conservative to avoid oversized payloads; consider pagination
#     cursors if this grows.

import io
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import and_, func, or_

from src.db.connection import db_session_scope
from src.logging.logger import get_logger
from src.models.orm.annual_report import AnnualReport
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore

logger = get_logger(__name__)
unified_api_bp = Blueprint("unified_api", __name__, url_prefix="/api/unified")


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert SQLAlchemy row dict to JSON-serializable structure."""
    return {
        "company_year_id": row.get("company_year_id"),
        "company_id": row.get("company_id"),
        "annual_report_id": row.get("annual_report_id"),
        "ticker": row.get("ticker"),
        "name": row.get("name"),
        "cik": row.get("cik"),
        "fiscal_year": row.get("fiscal_year"),
        "filing_date": row.get("filing_date").isoformat() if row.get("filing_date") else None,
        "sec_accession_id": row.get("sec_accession_id"),
        "report_path": row.get("report_path"),
        "report_hash": row.get("report_hash"),
        "file_format": row.get("file_format"),
        "file_size_bytes": row.get("file_size_bytes"),
        "extraction_status": row.get("extraction_status"),
        "form_type": row.get("form_type"),
        "data_version": row.get("data_version"),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _base_query(session):
    """Build the unified filings query (company + company_year + annual_report)."""
    return (
        session.query(
            CompanyYearCore.id.label("company_year_id"),
            Company.id.label("company_id"),
            AnnualReport.id.label("annual_report_id"),
            Company.ticker.label("ticker"),
            Company.name.label("name"),
            Company.cik.label("cik"),
            CompanyYearCore.fiscal_year.label("fiscal_year"),
            CompanyYearCore.filing_date.label("filing_date"),
            CompanyYearCore.sec_accession_id.label("sec_accession_id"),
            CompanyYearCore.report_path.label("report_path"),
            CompanyYearCore.report_hash.label("report_hash"),
            CompanyYearCore.data_version.label("data_version"),
            AnnualReport.file_format.label("file_format"),
            AnnualReport.file_size_bytes.label("file_size_bytes"),
            AnnualReport.extraction_status.label("extraction_status"),
            AnnualReport.form_type.label("form_type"),
            CompanyYearCore.created_at.label("created_at"),
            CompanyYearCore.updated_at.label("updated_at"),
        )
        .join(Company, CompanyYearCore.company_id == Company.id)
        .outerjoin(AnnualReport, AnnualReport.company_year_id == CompanyYearCore.id)
    )


def _apply_filters(query, ticker: Optional[str], fiscal_year: Optional[int], search: Optional[str]):
    """Apply optional filters to the unified query."""
    if ticker:
        query = query.filter(Company.ticker.ilike(f"%{ticker}%"))
    if fiscal_year:
        query = query.filter(CompanyYearCore.fiscal_year == fiscal_year)
    if search:
        query = query.filter(
            or_(
                Company.ticker.ilike(f"%{search}%"),
                Company.name.ilike(f"%{search}%"),
                Company.cik.ilike(f"%{search}%"),
            )
        )
    return query


@unified_api_bp.route("/filings", methods=["GET"])
def list_unified_filings():
    """Return paginated unified filings table for UI."""
    limit = min(int(request.args.get("limit", 500)), 5000)
    offset = int(request.args.get("offset", 0))
    ticker = request.args.get("ticker")
    year_param = request.args.get("year")
    search = request.args.get("q")
    fiscal_year = int(year_param) if year_param and year_param.isdigit() else None

    with db_session_scope() as session:
        base_q = _apply_filters(_base_query(session), ticker, fiscal_year, search)
        total = base_q.count()
        rows = (
            base_q.order_by(CompanyYearCore.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    data = [_serialize_row(r._asdict()) for r in rows]
    return jsonify({"total": total, "rows": data})


@unified_api_bp.route("/filings/export", methods=["GET"])
def export_unified_filings():
    """Export unified filings to CSV for download."""
    with db_session_scope() as session:
        rows = _base_query(session).all()
        data = [_serialize_row(r._asdict()) for r in rows]

    if not data:
        return jsonify({"error": "No filings available to export"}), 404

    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="unified_filings.csv",
    )


