#!/usr/bin/env python3
"""
PATH: scripts/ingest_sp500_historical.py
PURPOSE:
  - Populate sp500_historical_constituents table for survivorship bias correction
  - PRIMARY: Uses FMP historical S&P 500 constituent changes endpoint (adds + removes)
  - FALLBACK: Uses Wikipedia-sourced CSV if FMP endpoint unavailable
  - Tracks data source for each membership record

PUBLICATION FIX (Jan 2026):
  - Now uses FMP /api/v3/historical/sp500_constituent for TRUE point-in-time membership
  - Tracks both additions AND removals (enables real survivorship-bias-free analysis)
  - Each (symbol, added_date, removed_date) span is a distinct record
  - Symbols can have multiple spans (added, removed, re-added patterns)
"""

import asyncio
import csv
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import SP500HistoricalConstituent, FMPIncomeStatement
from app.services.fmp_client import FMPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Path to the reference CSV (Wikipedia S&P 500 list with "Date added") - fallback only
REFERENCE_CSV_PATH = Path(__file__).parent.parent / "data" / "reference" / "sp500_constituents.csv"

# Default start date for companies without known add date
DEFAULT_START_DATE = date(1957, 3, 4)  # S&P 500 inception date


async def fetch_fmp_historical_constituents() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch historical S&P 500 constituent changes from FMP API.
    
    Returns:
        Tuple of (historical_changes, current_constituents)
        - historical_changes: List of add/remove events
        - current_constituents: List of current S&P 500 members
    """
    async with FMPClient() as client:
        # Get historical changes (adds + removes)
        historical = await client.get_historical_sp500_constituents()
        
        # Get current constituents (for current members without removal)
        current = await client.get_sp500_constituents()
        
        return historical, current


def build_membership_spans(
    historical_changes: List[Dict[str, Any]],
    current_constituents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build membership spans from historical changes and current constituents.
    
    FMP historical endpoint returns records like:
    {
        "date": "2024-03-18",
        "symbol": "SMCI",
        "addedSecurity": "Super Micro Computer",
        "removedTicker": "WHR",
        "removedSecurity": "Whirlpool Corporation",
        "reason": "Market capitalization change"
    }
    
    We need to build spans: (symbol, added_date, removed_date, company_name, reason)
    """
    # Track events by symbol: list of (date, event_type, name, reason)
    events_by_symbol: Dict[str, List[Tuple[date, str, str, str]]] = defaultdict(list)
    
    # Process historical changes
    for change in historical_changes:
        change_date_str = change.get("date", "")
        if not change_date_str:
            continue
            
        try:
            change_date = datetime.strptime(change_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        
        # Process addition
        added_symbol = change.get("symbol", "").strip().upper()
        if added_symbol:
            added_name = change.get("addedSecurity", "").strip()
            events_by_symbol[added_symbol].append((change_date, "add", added_name, None))
        
        # Process removal
        removed_symbol = change.get("removedTicker", "").strip().upper()
        if removed_symbol:
            removed_name = change.get("removedSecurity", "").strip()
            reason = change.get("reason", "").strip() or None
            events_by_symbol[removed_symbol].append((change_date, "remove", removed_name, reason))
    
    # Current constituents are "currently active" (no removal yet)
    current_symbols = set()
    current_info: Dict[str, Dict[str, str]] = {}
    for c in current_constituents:
        sym = c.get("symbol", "").strip().upper()
        if sym:
            current_symbols.add(sym)
            current_info[sym] = {
                "name": c.get("name", "") or c.get("companyName", ""),
                "sector": c.get("sector", ""),
                "subSector": c.get("subSector", ""),
            }
    
    # Build spans from events
    spans = []
    
    for symbol, events in events_by_symbol.items():
        # Sort events by date
        events.sort(key=lambda x: x[0])
        
        current_span_start: Optional[date] = None
        current_span_name: Optional[str] = None
        
        for event_date, event_type, name, reason in events:
            if event_type == "add":
                if current_span_start is None:
                    # Start a new span
                    current_span_start = event_date
                    current_span_name = name
                # else: already in index, might be duplicate data
            elif event_type == "remove":
                if current_span_start is not None:
                    # Close the span
                    spans.append({
                        "symbol": symbol,
                        "added_date": current_span_start,
                        "removed_date": event_date,
                        "company_name": current_span_name or name,
                        "removal_reason": reason,
                        "sector": current_info.get(symbol, {}).get("sector"),
                    })
                    current_span_start = None
                    current_span_name = None
                else:
                    # Removal without a prior add in our data - company was in index before our history starts
                    spans.append({
                        "symbol": symbol,
                        "added_date": DEFAULT_START_DATE,  # Assume was in since inception
                        "removed_date": event_date,
                        "company_name": name,
                        "removal_reason": reason,
                        "sector": None,
                    })
        
        # If span is still open and symbol is currently in index
        if current_span_start is not None:
            if symbol in current_symbols:
                # Still active - no removed_date
                spans.append({
                    "symbol": symbol,
                    "added_date": current_span_start,
                    "removed_date": None,
                    "company_name": current_span_name or current_info.get(symbol, {}).get("name"),
                    "removal_reason": None,
                    "sector": current_info.get(symbol, {}).get("sector"),
                })
            # If not in current list but no removal event, it might have been removed
            # We leave this span open but it's likely incomplete data
    
    # Add current constituents that have no events (long-standing members)
    symbols_with_events = set(events_by_symbol.keys())
    for sym in current_symbols:
        if sym not in symbols_with_events:
            # No historical events - was added before our history starts
            spans.append({
                "symbol": sym,
                "added_date": DEFAULT_START_DATE,
                "removed_date": None,  # Still active
                "company_name": current_info.get(sym, {}).get("name"),
                "removal_reason": None,
                "sector": current_info.get(sym, {}).get("sector"),
            })
    
    logger.info(f"Built {len(spans)} membership spans from {len(events_by_symbol)} symbols with events + {len(current_symbols - symbols_with_events)} long-standing members")
    return spans


def load_sp500_from_csv() -> List[Dict[str, Any]]:
    """
    Load S&P 500 constituents from the reference CSV file (fallback).
    
    CSV columns: Symbol, Security, GICS Sector, GICS Sub-Industry, 
                 Headquarters Location, Date added, CIK, Founded
    
    Returns list of dicts with symbol, name, sector, added_date.
    """
    if not REFERENCE_CSV_PATH.exists():
        logger.warning(f"Reference CSV not found: {REFERENCE_CSV_PATH}")
        return []
    
    constituents = []
    with open(REFERENCE_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row.get("Symbol", "").strip().upper()
            if not symbol:
                continue
            
            # Parse "Date added" (format: YYYY-MM-DD or empty)
            date_added_str = row.get("Date added", "").strip()
            added_date = None
            if date_added_str:
                try:
                    added_date = datetime.strptime(date_added_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            constituents.append({
                "symbol": symbol,
                "added_date": added_date or DEFAULT_START_DATE,
                "removed_date": None,  # CSV only has current constituents
                "company_name": row.get("Security", "").strip(),
                "sector": row.get("GICS Sector", "").strip(),
                "removal_reason": None,
            })
    
    logger.info(f"Loaded {len(constituents)} constituents from CSV (fallback)")
    return constituents


async def ingest_historical_sp500(use_fmp: bool = True):
    """
    Ingest historical S&P 500 constituents with proper point-in-time handling.
    
    Strategy:
    1. Try FMP historical API first (adds + removes)
    2. Fall back to Wikipedia CSV if FMP unavailable
    3. Track data source for transparency
    
    Args:
        use_fmp: If True, try FMP API first; if False, use CSV only
    """
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    spans = []
    data_source = "unknown"
    
    try:
        # Try FMP API first
        if use_fmp:
            logger.info("Fetching historical S&P 500 constituents from FMP API...")
            try:
                historical, current = await fetch_fmp_historical_constituents()
                
                if historical or current:
                    logger.info(f"FMP returned {len(historical)} historical changes, {len(current)} current constituents")
                    spans = build_membership_spans(historical, current)
                    data_source = "fmp_historical"
                else:
                    logger.warning("FMP returned no data, falling back to CSV")
            except Exception as e:
                logger.warning(f"FMP API failed: {e}, falling back to CSV")
        
        # Fallback to CSV
        if not spans:
            logger.info("Using Wikipedia CSV fallback...")
            spans = load_sp500_from_csv()
            data_source = "wikipedia_sp500_list"
        
        if not spans:
            raise ValueError("No S&P 500 constituent data available from any source")
        
        async with async_session() as session:
            # Clear existing and rebuild (atomic swap)
            await session.execute(text("TRUNCATE TABLE sp500_historical_constituents"))
            
            records_created = 0
            with_removal = 0
            without_removal = 0
            
            for span in spans:
                symbol = span["symbol"]
                if not symbol:
                    continue
                
                record = SP500HistoricalConstituent(
                    symbol=symbol,
                    added_date=span["added_date"],
                    removed_date=span.get("removed_date"),
                    removal_reason=span.get("removal_reason"),
                    company_name=span.get("company_name"),
                    sector=span.get("sector"),
                    membership_source=data_source,
                )
                session.add(record)
                records_created += 1
                
                if span.get("removed_date"):
                    with_removal += 1
                else:
                    without_removal += 1
            
            await session.commit()
            
            # Log summary
            logger.info("=" * 60)
            logger.info("HISTORICAL CONSTITUENTS INGESTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Data source: {data_source}")
            logger.info(f"Total membership spans created: {records_created}")
            logger.info(f"  - With removal date (historical): {with_removal}")
            logger.info(f"  - Without removal date (current): {without_removal}")
            logger.info("=" * 60)
            
            if data_source == "fmp_historical":
                logger.info("✓ TRUE POINT-IN-TIME MEMBERSHIP (FMP historical adds + removes)")
            else:
                logger.info("⚠ CURRENT CONSTITUENTS ONLY (no historical removals)")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"Error ingesting historical constituents: {e}")
        raise
    finally:
        await engine.dispose()


async def validate_membership_data():
    """Validate the ingested membership data for quality."""
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check for any remaining placeholder dates
        placeholder_check = await session.execute(
            text("SELECT COUNT(*) FROM sp500_historical_constituents WHERE added_date = '1900-01-01'")
        )
        placeholder_count = placeholder_check.scalar()
        
        # Check date range coverage
        date_range = await session.execute(
            text("""
                SELECT 
                    MIN(added_date) as earliest_add,
                    MAX(added_date) as latest_add,
                    MIN(removed_date) as earliest_remove,
                    MAX(removed_date) as latest_remove,
                    COUNT(*) as total_records,
                    COUNT(removed_date) as removal_count,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM sp500_historical_constituents
            """)
        )
        stats = date_range.fetchone()
        
        # Check membership source breakdown
        source_breakdown = await session.execute(
            text("""
                SELECT membership_source, COUNT(*) as cnt
                FROM sp500_historical_constituents
                GROUP BY membership_source
                ORDER BY cnt DESC
            """)
        )
        sources = source_breakdown.fetchall()
        
        # Check coverage by formation year (July 1 check)
        coverage_by_year = await session.execute(
            text("""
                WITH years AS (
                    SELECT generate_series(1995, 2025) as year
                )
                SELECT 
                    y.year,
                    COUNT(DISTINCT h.symbol) as n_constituents
                FROM years y
                LEFT JOIN sp500_historical_constituents h
                    ON h.added_date <= make_date(y.year, 7, 1)
                    AND (h.removed_date IS NULL OR h.removed_date >= make_date(y.year, 7, 1))
                GROUP BY y.year
                ORDER BY y.year
            """)
        )
        yearly_coverage = coverage_by_year.fetchall()
        
        logger.info("\n" + "=" * 60)
        logger.info("MEMBERSHIP DATA VALIDATION")
        logger.info("=" * 60)
        logger.info(f"Placeholder dates (1900-01-01): {placeholder_count}")
        logger.info(f"Earliest add date: {stats[0]}")
        logger.info(f"Latest add date: {stats[1]}")
        logger.info(f"Earliest removal: {stats[2]}")
        logger.info(f"Latest removal: {stats[3]}")
        logger.info(f"Total membership spans: {stats[4]}")
        logger.info(f"Spans with removal date: {stats[5]}")
        logger.info(f"Unique symbols: {stats[6]}")
        logger.info("")
        logger.info("Membership source breakdown:")
        for src, cnt in sources:
            logger.info(f"  {src or 'NULL'}: {cnt}")
        logger.info("")
        logger.info("Coverage by formation year (July 1):")
        for year, n in yearly_coverage:
            status = "✓" if n >= 450 else "⚠" if n >= 300 else "✗"
            logger.info(f"  {year}: {n:4d} constituents {status}")
        logger.info("=" * 60)
        
        if placeholder_count > 0:
            logger.warning(f"WARNING: {placeholder_count} records still have placeholder dates!")
        
        # Validate coverage targets
        valid_years = [(y, n) for y, n in yearly_coverage if n and n > 0]
        if valid_years:
            avg_coverage = sum(n for _, n in valid_years) / len(valid_years)
            if avg_coverage < 450:
                logger.warning(f"WARNING: Average yearly coverage ({avg_coverage:.1f}) is below target (450-550)")
            else:
                logger.info(f"Average yearly coverage: {avg_coverage:.1f} ✓")
    
    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest historical S&P 500 constituents")
    parser.add_argument("--validate", action="store_true", help="Validate existing data instead of ingesting")
    parser.add_argument("--csv-only", action="store_true", help="Use CSV fallback only (skip FMP API)")
    args = parser.parse_args()
    
    if args.validate:
        asyncio.run(validate_membership_data())
    else:
        asyncio.run(ingest_historical_sp500(use_fmp=not args.csv_only))
