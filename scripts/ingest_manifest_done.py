# PATH: scripts/ingest_manifest_done.py
# PURPOSE:
#   - Read the S&P 500 crawl manifest, locate downloaded filings marked as "done",
#     and upsert Company, CompanyYearCore, and AnnualReport rows pointing to the
#     downloaded files.
#
# ROLE IN ARCHITECTURE:
#   - Data ingestion / ETL helper that bridges disk outputs from the crawler into
#     the relational DB so downstream factor computations can run.
#
# MAIN EXPORTS:
#   - ingest_manifest_done(): upsert records for all manifest rows with status == "done".
#   - main(): CLI entrypoint; optionally triggers R&D factor computation.
#
# NON-RESPONSIBILITIES:
#   - Does NOT crawl or download filings.
#   - Does NOT perform text chunking or factor extraction beyond invoking the
#     compute_rd_factors helper.
#   - Does NOT validate XBRL or financial ratios.
#
# NOTES FOR FUTURE AI:
#   - If you add new file formats, extend _PREFERRED_EXTS and file_format mapping.
#   - If accession IDs become available in the manifest, store them instead of
#     deriving from filenames.
#   - Consider batching DB commits for speed if this grows, but keep per-file
#     commits for safety unless you add transactional retry logic.

# Setup path - must be first
import _setup_path  # noqa: F401

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from scripts.compute_rd_factors import compute_all_rd_factors
from src.db.connection import db_session_scope
from src.logging.logger import get_logger
from src.models.orm.annual_report import AnnualReport
from src.models.orm.company import Company
from src.models.orm.company_year_core import CompanyYearCore

logger = get_logger(__name__)

_PREFERRED_EXTS = [".txt", ".html", ".htm", ".pdf"]


def _load_manifest(manifest_path: Path) -> List[Dict]:
    """Load manifest rows from JSONL."""
    rows: List[Dict] = []
    with manifest_path.open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sha256(path: Path) -> str:
    """Compute SHA256 for a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _select_filing_file(year_dir: Path) -> Optional[Path]:
    """Pick the best filing file in a year directory based on preferred extensions."""
    if not year_dir.is_dir():
        return None
    files = list(year_dir.iterdir())
    for ext in _PREFERRED_EXTS:
        for file in files:
            if file.is_file() and file.suffix.lower() == ext:
                return file
    # Fallback to any file if no preferred ext found
    for file in files:
        if file.is_file():
            return file
    return None


def _ensure_company(session: Session, ticker: str, cik: str, name: str) -> Company:
    """Get or create Company."""
    company = session.query(Company).filter_by(ticker=ticker).first()
    if company:
        # Keep existing metadata; update name/cik if missing
        if not company.name:
            company.name = name
        if not company.cik:
            company.cik = cik
        return company
    company = Company(ticker=ticker, cik=cik, name=name)
    session.add(company)
    session.flush()
    return company


def _upsert_company_year(
    session: Session,
    company: Company,
    ticker: str,
    cik: str,
    fiscal_year: int,
    report_path: str,
    report_hash: str,
    sec_accession_id: Optional[str],
) -> CompanyYearCore:
    """Upsert CompanyYearCore for a given year."""
    cy = (
        session.query(CompanyYearCore)
        .filter_by(company_id=company.id, fiscal_year=fiscal_year)
        .first()
    )
    if not cy:
        cy = CompanyYearCore(
            company_id=company.id,
            ticker=ticker,
            cik=cik,
            fiscal_year=fiscal_year,
            sec_accession_id=sec_accession_id,
            report_path=report_path,
            report_hash=report_hash,
        )
        session.add(cy)
        session.flush()
        return cy

    cy.sec_accession_id = sec_accession_id or cy.sec_accession_id
    cy.report_path = report_path
    cy.report_hash = report_hash
    session.flush()
    return cy


def _upsert_annual_report(
    session: Session,
    company_year: CompanyYearCore,
    cik: str,
    fiscal_year: int,
    filing_path: str,
    file_hash: str,
    file_size: int,
    file_format: str,
):
    """Upsert AnnualReport tied to a company year."""
    ar = (
        session.query(AnnualReport)
        .filter_by(company_year_id=company_year.id)
        .first()
    )
    if not ar:
        ar = AnnualReport(
            company_year_id=company_year.id,
            cik=cik,
            fiscal_year=fiscal_year,
            file_path=filing_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            file_format=file_format,
            extraction_status="pending",
        )
        session.add(ar)
    else:
        ar.cik = cik
        ar.fiscal_year = fiscal_year
        ar.file_path = filing_path
        ar.file_hash = file_hash
        ar.file_size_bytes = file_size
        ar.file_format = file_format
        if not ar.extraction_status:
            ar.extraction_status = "pending"
    session.flush()


def _find_company_dirs(base_raw_dir: Path, cik: str) -> List[Path]:
    """Return possible company directories (with and without leading zeros)."""
    candidates = []
    cik_clean = cik.lstrip("0") or cik
    for val in {cik, cik_clean}:
        if val:
            candidate = base_raw_dir / val
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _ingest_entry(
    session: Session,
    entry: Dict,
    base_raw_dir: Path,
) -> List[int]:
    """Ingest a single manifest entry; returns company_year_ids processed."""
    ticker = entry.get("ticker")
    cik = entry.get("cik")
    name = entry.get("name", ticker)
    if not ticker or not cik:
        logger.warning({"event_type": "validation", "msg": "missing ticker/cik", "entry": entry})
        return []

    processed_ids: List[int] = []
    company_dirs = _find_company_dirs(base_raw_dir, cik)
    if not company_dirs:
        logger.warning({"event_type": "missing_files", "ticker": ticker, "cik": cik})
        return processed_ids

    company = _ensure_company(session, ticker=ticker, cik=cik, name=name)

    for company_dir in company_dirs:
        for year_dir in sorted(company_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            try:
                fiscal_year = int(year_dir.name)
            except ValueError:
                continue
            filing = _select_filing_file(year_dir)
            if not filing:
                logger.warning({"event_type": "missing_filing_file", "ticker": ticker, "year": fiscal_year})
                continue

            file_hash = _sha256(filing)
            file_size = filing.stat().st_size
            file_format = filing.suffix.lower().lstrip(".") or "html"
            sec_accession_id = filing.stem  # best-effort placeholder

            cy = _upsert_company_year(
                session=session,
                company=company,
                ticker=ticker,
                cik=cik,
                fiscal_year=fiscal_year,
                report_path=str(filing),
                report_hash=file_hash,
                sec_accession_id=sec_accession_id,
            )
            _upsert_annual_report(
                session=session,
                company_year=cy,
                cik=cik,
                fiscal_year=fiscal_year,
                filing_path=str(filing),
                file_hash=file_hash,
                file_size=file_size,
                file_format=file_format,
            )
            processed_ids.append(cy.id)

    return processed_ids


def ingest_manifest_done(
    manifest_path: Path,
    base_raw_dir: Path,
    limit: Optional[int] = None,
) -> List[int]:
    """Ingest all manifest rows with status == done; return company_year_ids."""
    rows = _load_manifest(manifest_path)
    done_rows = [r for r in rows if r.get("status") == "done"]
    if limit:
        done_rows = done_rows[:limit]

    processed: List[int] = []
    with db_session_scope() as session:
        for row in done_rows:
            ids = _ingest_entry(session, row, base_raw_dir)
            if ids:
                session.commit()
                processed.extend(ids)
            else:
                session.rollback()
    return processed


def main():
    """CLI: ingest manifest rows marked done, then optionally compute RD factors."""
    parser = argparse.ArgumentParser(description="Ingest manifest (status=done) into DB and run RD factors.")
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=Path("data/reference/sp500_manifest_seed.jsonl"),
        help="Path to manifest JSONL",
    )
    parser.add_argument(
        "--base-raw-dir",
        type=Path,
        default=Path("data/raw/annual_reports"),
        help="Base directory where filings were downloaded",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of done rows to ingest",
    )
    parser.add_argument(
        "--skip-compute",
        action="store_true",
        help="Skip compute_rd_factors step",
    )
    parser.add_argument(
        "--no-force",
        action="store_true",
        help="Do not force recompute (default is force=True)",
    )
    args = parser.parse_args()

    processed_ids = ingest_manifest_done(args.manifest_path, args.base_raw_dir, args.limit)
    logger.info({"event_type": "ingest_complete", "processed_company_year_ids": processed_ids})

    if args.skip_compute:
        logger.info("Skipping compute_rd_factors as requested.")
        return

    if not processed_ids:
        logger.warning("No company_year_ids processed; skipping compute_rd_factors.")
        return

    compute_all_rd_factors(
        use_v2=True,
        force_recompute=not args.no_force,
        company_year_ids=processed_ids,
    )


if __name__ == "__main__":
    main()


