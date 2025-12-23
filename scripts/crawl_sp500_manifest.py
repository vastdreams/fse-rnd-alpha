#!/usr/bin/env python
"""
PATH: scripts/crawl_sp500_manifest.py
PURPOSE:
  - Drive SEC crawling from the S&P 500 manifest (JSONL).
ROLE IN ARCHITECTURE:
  - Ingestion runner: batch-crawls filings for a list of tickers/CIKs.
MAIN EXPORTS:
  - CLI script (no imports expected).
NON-RESPONSIBILITIES:
  - Does not compute R&D factors (use compute_rd_factors.py separately).
NOTES FOR FUTURE AI:
  - Manifest format: JSONL with keys ticker, name, cik (optional), status, years_requested.
  - Resumable: you can filter on status != "done" to continue.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.sec_crawler import crawl_company_filings


def load_manifest(path: Path) -> List[Dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def main(manifest_path: str, start: int, limit: int, years: int, skip_done: bool):
    manifest_file = Path(manifest_path)
    rows = load_manifest(manifest_file)
    if skip_done:
        rows = [r for r in rows if r.get("status") != "done"]
    batch = rows[start : start + limit]
    print(f"Loaded {len(rows)} manifest rows; processing batch {start}:{start+limit} ({len(batch)} rows)")

    updated = False
    for entry in batch:
        ticker = entry.get("ticker")
        cik = entry.get("cik") or ""
        cik_clean = cik.lstrip("0") if cik else None
        target_id = cik_clean if cik_clean else ticker
        if not target_id or not ticker:
            print(f"Skipping entry with missing ticker/CIK: {entry}")
            continue
        try:
            filings = crawl_company_filings(target_id, ticker, years=years)
            print(f"{ticker}: fetched {len(filings)} filings")
            entry["status"] = "done"
            updated = True
        except Exception as e:
            print(f"{ticker}: error {e}")
            entry["status"] = "error"
            updated = True

    # Persist updated manifest even if no change (keeps run deterministic)
    if updated:
        tmp_path = manifest_file.with_suffix(".jsonl.tmp")
        with tmp_path.open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        tmp_path.replace(manifest_file)
        print(f"Updated manifest written to {manifest_file}")
    else:
        print("No manifest changes to write.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch-crawl SEC filings from manifest.")
    parser.add_argument("--manifest", default="data/reference/sp500_manifest_seed.jsonl")
    parser.add_argument("--start", type=int, default=0, help="Start index in manifest")
    parser.add_argument("--limit", type=int, default=25, help="Max rows to process")
    parser.add_argument("--years", type=int, default=20, help="Lookback years per ticker")
    parser.add_argument("--skip-done", action="store_true", help="Skip rows with status=done")
    args = parser.parse_args()
    main(args.manifest, args.start, args.limit, args.years, args.skip_done)

