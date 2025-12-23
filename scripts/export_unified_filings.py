# PATH: scripts/export_unified_filings.py
# PURPOSE:
#   - Export the unified filings reference table to CSV (and optional Parquet).
#
# ROLE IN ARCHITECTURE:
#   - Ops/analysis helper to quickly inspect what filings exist in DB.
#
# MAIN EXPORTS:
#   - export_unified_filings(): writes data/exports/unified_filings.csv
#   - CLI entrypoint (python scripts/export_unified_filings.py)
#
# NON-RESPONSIBILITIES:
#   - Does NOT mutate core tables.
#   - Does NOT fetch/crawl or compute factors.
#
# NOTES FOR FUTURE AI:
#   - If manifest status is stored in DB later, include it here.
#   - Keep export size reasonable; paginate if the dataset grows.

# Setup path - must be first
import _setup_path  # noqa: F401

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from src.api.blueprints.unified_api import _base_query, _serialize_row  # reuse logic
from src.db.connection import db_session_scope
from src.logging.logger import get_logger

logger = get_logger(__name__)


def export_unified_filings(output_dir: Path, parquet: bool = False) -> Path:
    """Export unified_filings join to CSV (and optionally Parquet)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "unified_filings.csv"
    parquet_path = output_dir / "unified_filings.parquet"

    with db_session_scope() as session:
        rows = _base_query(session).all()
        data = [_serialize_row(r._asdict()) for r in rows]

    if not data:
        raise RuntimeError("No unified filings found to export.")

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    logger.info(f"Wrote CSV: {csv_path} ({csv_path.stat().st_size/1e6:.2f} MB)")

    if parquet:
        df.to_parquet(parquet_path, index=False)
        logger.info(f"Wrote Parquet: {parquet_path} ({parquet_path.stat().st_size/1e6:.2f} MB)")

    return csv_path


def main():
    """CLI entrypoint to export unified filings."""
    parser = argparse.ArgumentParser(description="Export unified filings to CSV/Parquet.")
    parser.add_argument("--out", type=Path, default=Path("data/exports"), help="Output directory.")
    parser.add_argument("--parquet", action="store_true", help="Also write Parquet.")
    args = parser.parse_args()

    export_unified_filings(args.out, parquet=args.parquet)


if __name__ == "__main__":
    main()


