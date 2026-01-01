#!/usr/bin/env python3
"""
PATH: scripts/ingest_sp500_historical.py
PURPOSE:
  - Populate sp500_historical_constituents table for survivorship bias correction
  - Uses Wikipedia-sourced S&P 500 list CSV with official "Date added" information
  - Fallback: estimates add dates from first available financial data when not known

PUBLICATION FIX (Jan 2026):
  - Primary source: data/reference/sp500_constituents.csv (Wikipedia S&P 500 list)
  - Uses official S&P "Date added" from Wikipedia for genuine point-in-time membership
  - No longer relies on FMP historical API (requires higher subscription tier)
  - Tracks data source for each membership record
"""

import asyncio
import csv
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import SP500HistoricalConstituent, FMPIncomeStatement

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Path to the reference CSV (Wikipedia S&P 500 list with "Date added")
REFERENCE_CSV_PATH = Path(__file__).parent.parent / "data" / "reference" / "sp500_constituents.csv"

# Default start date for companies without known add date
# This is when our data coverage begins reliably
DEFAULT_START_DATE = date(1994, 1, 1)


def load_sp500_from_csv() -> List[Dict[str, Any]]:
    """
    Load S&P 500 constituents from the reference CSV file.
    
    CSV columns: Symbol, Security, GICS Sector, GICS Sub-Industry, 
                 Headquarters Location, Date added, CIK, Founded
    
    Returns list of dicts with symbol, name, sector, added_date.
    """
    if not REFERENCE_CSV_PATH.exists():
        raise FileNotFoundError(f"Reference CSV not found: {REFERENCE_CSV_PATH}")
    
    constituents = []
    with open(REFERENCE_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row.get("Symbol", "").strip()
            if not symbol:
                continue
            
            # Parse "Date added" (format: YYYY-MM-DD or empty)
            date_added_str = row.get("Date added", "").strip()
            added_date = None
            if date_added_str:
                try:
                    added_date = datetime.strptime(date_added_str, "%Y-%m-%d").date()
                except ValueError:
                    # Try other formats or skip
                    pass
            
            constituents.append({
                "symbol": symbol,
                "name": row.get("Security", "").strip(),
                "sector": row.get("GICS Sector", "").strip(),
                "added_date": added_date,
                "cik": row.get("CIK", "").strip(),
            })
    
    logger.info(f"Loaded {len(constituents)} constituents from CSV")
    return constituents


async def get_first_data_year(session: AsyncSession, symbol: str) -> Optional[int]:
    """Get the first year we have financial data for a symbol."""
    result = await session.execute(
        select(func.min(FMPIncomeStatement.fiscal_year))
        .where(FMPIncomeStatement.symbol == symbol)
    )
    return result.scalar_one_or_none()


async def ingest_historical_sp500():
    """
    Ingest historical S&P 500 constituents with proper point-in-time handling.
    
    Strategy:
    1. Load current constituents from Wikipedia-sourced CSV (with official "Date added")
    2. For each constituent:
       - Use the official S&P "Date added" if available
       - Otherwise estimate from first year of financial data
       - All current constituents have removed_date = NULL (still active)
    3. Track data source for transparency
    
    NOTE: This provides genuine point-in-time membership for current constituents.
    Historical removals are not tracked (would require FMP premium tier or CRSP data).
    """
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Load from CSV
        constituents = load_sp500_from_csv()
        
        async with async_session() as session:
            # Clear existing and rebuild
            await session.execute(text("TRUNCATE TABLE sp500_historical_constituents"))
            
            records_created = 0
            with_official_date = 0
            with_estimated_date = 0
            
            for constituent in constituents:
                symbol = constituent["symbol"]
                added_date = constituent["added_date"]
                source = "wikipedia_sp500_list"
                
                # If no official date, estimate from first data year
                if added_date is None:
                    first_year = await get_first_data_year(session, symbol)
                    if first_year:
                        added_date = date(first_year, 1, 1)
                        source = "estimated_from_data"
                    else:
                        added_date = DEFAULT_START_DATE
                        source = "default_fallback"
                    with_estimated_date += 1
                else:
                    with_official_date += 1
                
                # Create membership record (currently active = removed_date is NULL)
                record = SP500HistoricalConstituent(
                    symbol=symbol,
                    added_date=added_date,
                    removed_date=None,  # Still active in index
                    removal_reason=None,
                    company_name=constituent.get("name"),
                    sector=constituent.get("sector"),
                    membership_source=source,
                )
                session.add(record)
                records_created += 1
            
            await session.commit()
            
            # Log summary
            logger.info("=" * 60)
            logger.info("HISTORICAL CONSTITUENTS INGESTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total records created: {records_created}")
            logger.info(f"With official S&P 'Date added': {with_official_date}")
            logger.info(f"With estimated add date: {with_estimated_date}")
            logger.info(f"Source: {REFERENCE_CSV_PATH}")
            logger.info("=" * 60)
            logger.info("NOTE: All records are current constituents (removed_date = NULL).")
            logger.info("Historical removals require FMP premium tier or CRSP data.")
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
                    COUNT(removed_date) as removal_count
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
                    SELECT generate_series(2000, 2024) as year
                )
                SELECT 
                    y.year,
                    COUNT(h.symbol) as n_constituents
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
        logger.info(f"Total records: {stats[4]}")
        logger.info(f"Records with removal date: {stats[5]}")
        logger.info("")
        logger.info("Membership source breakdown:")
        for src, cnt in sources:
            logger.info(f"  {src or 'NULL'}: {cnt}")
        logger.info("")
        logger.info("Coverage by formation year (July 1):")
        for year, n in yearly_coverage:
            logger.info(f"  {year}: {n} constituents")
        logger.info("=" * 60)
        
        if placeholder_count > 0:
            logger.warning(f"WARNING: {placeholder_count} records still have placeholder dates!")
        
        # Validate coverage targets
        avg_coverage = sum(n for _, n in yearly_coverage if n) / len(yearly_coverage) if yearly_coverage else 0
        if avg_coverage < 450:
            logger.warning(f"WARNING: Average yearly coverage ({avg_coverage:.1f}) is below target (450-550)")
        else:
            logger.info(f"Average yearly coverage: {avg_coverage:.1f} ✓")
    
    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest historical S&P 500 constituents")
    parser.add_argument("--validate", action="store_true", help="Validate existing data instead of ingesting")
    args = parser.parse_args()
    
    if args.validate:
        asyncio.run(validate_membership_data())
    else:
        asyncio.run(ingest_historical_sp500())
