#!/usr/bin/env python
"""
PATH: scripts/crawl_research_cohort.py
PURPOSE:
  - Concurrent crawl of SEC filings for the 50-company research cohort.
  - Designed for EC2 deployment with 8 concurrent workers.

ROLE IN ARCHITECTURE:
  - Ingestion runner for research publication data.

MAIN EXPORTS:
  - CLI script for batch crawling.

NON-RESPONSIBILITIES:
  - Does not compute factors (use separate scripts after crawl).

NOTES FOR FUTURE AI:
  - Uses ThreadPoolExecutor for concurrent HTTP requests.
  - Respects SEC rate limits (10 req/sec) with per-worker delays.
  - Stores results in PostgreSQL and downloads reports to data/raw/.
"""

import argparse
import sys
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import threading

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Thread-local storage for worker IDs
local_data = threading.local()
worker_counter = 0
worker_lock = threading.Lock()


def get_worker_id():
    """Get or assign a unique worker ID for this thread."""
    global worker_counter
    if not hasattr(local_data, 'worker_id'):
        with worker_lock:
            local_data.worker_id = worker_counter
            worker_counter += 1
    return local_data.worker_id


# Research cohort: 50 companies selected for R&D analysis
RESEARCH_COHORT = [
    # Technology - High R&D
    ("NVDA", "Nvidia"),
    ("MSFT", "Microsoft Corporation"),
    ("ORCL", "Oracle Corporation"),
    ("ADSK", "Autodesk"),
    ("FTNT", "Fortinet"),
    ("EPAM", "EPAM Systems"),
    # Technology - Medium/Low R&D
    ("CSCO", "Cisco"),
    ("IBM", "IBM"),
    ("EA", "Electronic Arts"),
    ("CTSH", "Cognizant"),
    ("DELL", "Dell Technologies"),
    
    # Healthcare - High R&D
    ("AMGN", "Amgen"),
    ("JNJ", "Johnson & Johnson"),
    ("MRNA", "Moderna"),
    ("ISRG", "Intuitive Surgical"),
    # Healthcare - Medium/Low R&D
    ("HOLX", "Hologic"),
    ("COO", "Cooper Companies"),
    ("CI", "Cigna"),
    ("ELV", "Elevance Health"),
    
    # Industrial - Medium R&D
    ("DE", "Deere & Company"),
    ("CAT", "Caterpillar Inc."),
    ("EMR", "Emerson Electric"),
    ("ETN", "Eaton Corporation"),
    ("IEX", "IDEX Corporation"),
    ("AME", "Ametek"),
    ("GLW", "Corning Inc."),
    ("DD", "DuPont"),
    # Industrial - Low R&D
    ("APH", "Amphenol"),
    ("ECL", "Ecolab"),
    ("FDX", "FedEx"),
    ("CTAS", "Cintas"),
    ("JBHT", "J.B. Hunt"),
    
    # Consumer
    ("AAPL", "Apple Inc."),
    ("COST", "Costco"),
    ("KO", "Coca-Cola Company"),
    ("CL", "Colgate-Palmolive"),
    ("CLX", "Clorox"),
    ("KHC", "Kraft Heinz"),
    ("CPB", "Campbell Soup"),
    ("CMG", "Chipotle Mexican Grill"),
    ("DPZ", "Dominos Pizza"),
    
    # Financial
    ("AXP", "American Express"),
    ("CME", "CME Group"),
    ("MSCI", "MSCI Inc."),
    ("COIN", "Coinbase"),
    ("CINF", "Cincinnati Financial"),
    ("AJG", "Arthur J. Gallagher"),
    
    # Energy
    ("COP", "ConocoPhillips"),
    ("EOG", "EOG Resources"),
    ("ED", "Consolidated Edison"),
]


def crawl_single_company(ticker: str, name: str, years: int) -> Tuple[str, bool, str]:
    """
    Crawl a single company's filings.
    
    Args:
        ticker: Company ticker symbol
        name: Company name
        years: Number of years to fetch
        
    Returns:
        Tuple of (ticker, success, message)
    """
    worker_id = get_worker_id()
    
    # Import here to avoid circular imports
    from src.ingestion.sec_crawler import crawl_company_filings
    
    try:
        # Stagger workers to respect rate limits
        time.sleep(worker_id * 0.15)
        
        print(f"[Worker {worker_id}] Starting {ticker} ({name})...")
        start_time = time.time()
        
        filings = crawl_company_filings(ticker, ticker, years=years)
        
        elapsed = time.time() - start_time
        msg = f"[Worker {worker_id}] {ticker}: {len(filings)} filings in {elapsed:.1f}s"
        print(msg)
        
        return (ticker, True, msg)
        
    except Exception as e:
        msg = f"[Worker {worker_id}] {ticker}: ERROR - {str(e)[:100]}"
        print(msg)
        return (ticker, False, msg)


def run_concurrent_crawl(years: int, max_workers: int, dry_run: bool = False):
    """
    Run concurrent crawl for all research cohort companies.
    
    Args:
        years: Number of years to fetch per company
        max_workers: Number of concurrent workers
        dry_run: If True, just print what would be done
    """
    companies = RESEARCH_COHORT
    total = len(companies)
    
    print(f"\n{'='*60}")
    print(f"RESEARCH COHORT CONCURRENT CRAWL")
    print(f"{'='*60}")
    print(f"Companies: {total}")
    print(f"Years per company: {years}")
    print(f"Total company-years: {total * years}")
    print(f"Concurrent workers: {max_workers}")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("DRY RUN - Would crawl:")
        for ticker, name in companies:
            print(f"  - {ticker}: {name} ({years} years)")
        return
    
    start_time = time.time()
    results = {"success": [], "failed": []}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ticker = {
            executor.submit(crawl_single_company, ticker, name, years): ticker
            for ticker, name in companies
        }
        
        # Process completions
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                t, success, msg = future.result()
                if success:
                    results["success"].append(t)
                else:
                    results["failed"].append(t)
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                results["failed"].append(ticker)
            
            # Progress update
            pct = (completed / total) * 100
            print(f"Progress: {completed}/{total} ({pct:.1f}%)")
    
    elapsed = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print(f"CRAWL COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"Success: {len(results['success'])}/{total}")
    print(f"Failed: {len(results['failed'])}/{total}")
    
    if results["failed"]:
        print(f"\nFailed tickers: {', '.join(results['failed'])}")
    
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Concurrent crawl of research cohort (50 companies)"
    )
    parser.add_argument(
        "--years", 
        type=int, 
        default=20, 
        help="Years of history to fetch (default: 20)"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=8, 
        help="Number of concurrent workers (default: 8)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing"
    )
    
    args = parser.parse_args()
    
    run_concurrent_crawl(
        years=args.years,
        max_workers=args.workers,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

