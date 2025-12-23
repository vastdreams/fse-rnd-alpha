#!/usr/bin/env python3
"""
PATH: scripts/ingest_sp500_historical.py
PURPOSE:
  - Fetch historical S&P 500 constituents from FMP API
  - Cross-reference with current constituents to establish complete membership timeline
  - Populate sp500_historical_constituents table for survivorship bias correction

PUBLICATION FIX (Dec 2025):
  - No longer uses placeholder dates (1900-01-01)
  - Estimates add dates from first available data when not known
  - Tracks data source for each membership record
  - Creates consolidated membership spans for each symbol
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import SP500HistoricalConstituent, SP500Company, FMPIncomeStatement, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

HISTORICAL_URL = "https://financialmodelingprep.com/api/v3/historical/sp500_constituent"
CURRENT_CONSTITUENTS_URL = "https://financialmodelingprep.com/api/v3/sp500_constituent"

# Default start date for companies without known add date
# This is when our data coverage begins reliably
DEFAULT_START_DATE = date(1994, 1, 1)


async def fetch_historical_constituents(api_key: str) -> List[Dict]:
    """Fetch historical changes from FMP."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{HISTORICAL_URL}?apikey={api_key}")
        response.raise_for_status()
        return response.json()


async def fetch_current_constituents(api_key: str) -> List[Dict]:
    """Fetch current S&P 500 constituents from FMP."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{CURRENT_CONSTITUENTS_URL}?apikey={api_key}")
        response.raise_for_status()
        return response.json()


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
    1. Fetch historical changes (additions and removals) from FMP
    2. Fetch current constituents
    3. Build a timeline for each symbol:
       - If added via historical API: use that date
       - If removed via historical API: use that date
       - If in current constituents with no history: estimate from first data year
       - Track data source for transparency
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        logger.error("FMP_API_KEY environment variable not set")
        return

    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Fetch data from FMP
        changes = await fetch_historical_constituents(api_key)
        current_constituents = await fetch_current_constituents(api_key)
        
        logger.info(f"Fetched {len(changes)} historical changes and {len(current_constituents)} current constituents.")
        
        async with async_session() as session:
            # Build membership timeline
            # symbol -> list of (added_date, removed_date, source, reason, name)
            membership_events: Dict[str, List[Dict]] = defaultdict(list)
            
            # Process historical changes
            for change in changes:
                event_date_str = change.get("date")
                if not event_date_str:
                    continue
                    
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                
                # Company added
                if change.get("symbol"):
                    symbol = change["symbol"]
                    membership_events[symbol].append({
                        "type": "add",
                        "date": event_date,
                        "source": "fmp_historical",
                        "reason": change.get("reason"),
                        "name": change.get("name")
                    })
                
                # Company removed
                if change.get("removedTicker"):
                    symbol = change["removedTicker"]
                    membership_events[symbol].append({
                        "type": "remove",
                        "date": event_date,
                        "source": "fmp_historical",
                        "reason": change.get("reason"),
                        "name": change.get("removedName")
                    })
            
            # Current constituents (still in index)
            current_symbols = set()
            for constituent in current_constituents:
                symbol = constituent.get("symbol")
                if symbol:
                    current_symbols.add(symbol)
                    # If no add event in history, this is a long-standing member
                    if symbol not in membership_events or not any(e["type"] == "add" for e in membership_events[symbol]):
                        # Estimate add date from first data year
                        first_year = await get_first_data_year(session, symbol)
                        if first_year:
                            estimated_date = date(first_year, 1, 1)
                        else:
                            estimated_date = DEFAULT_START_DATE
                        
                        membership_events[symbol].append({
                            "type": "add",
                            "date": estimated_date,
                            "source": "estimated_from_data",
                            "reason": None,
                            "name": constituent.get("name")
                        })
            
            # Clear existing and rebuild
            await session.execute(text("TRUNCATE TABLE sp500_historical_constituents"))
            
            # Create consolidated membership records
            records_created = 0
            symbols_processed = set()
            
            for symbol, events in membership_events.items():
                symbols_processed.add(symbol)
                
                # Sort events by date
                events.sort(key=lambda e: e["date"])
                
                # Build membership spans
                current_add: Optional[Dict] = None
                
                for event in events:
                    if event["type"] == "add":
                        current_add = event
                    elif event["type"] == "remove" and current_add:
                        # Complete span: add -> remove
                        record = SP500HistoricalConstituent(
                            symbol=symbol,
                            added_date=current_add["date"],
                            removed_date=event["date"],
                            removal_reason=event.get("reason"),
                            company_name=current_add.get("name") or event.get("name"),
                            membership_source=current_add.get("source"),
                        )
                        session.add(record)
                        records_created += 1
                        current_add = None
                    elif event["type"] == "remove" and not current_add:
                        # Removal without known add - estimate add date
                        first_year = await get_first_data_year(session, symbol)
                        if first_year:
                            estimated_add = date(first_year, 1, 1)
                        else:
                            estimated_add = DEFAULT_START_DATE
                        
                        record = SP500HistoricalConstituent(
                            symbol=symbol,
                            added_date=estimated_add,
                            removed_date=event["date"],
                            removal_reason=event.get("reason"),
                            company_name=event.get("name"),
                            membership_source="estimated_from_data",
                        )
                        session.add(record)
                        records_created += 1
                
                # If still have an open add (currently in index)
                if current_add and symbol in current_symbols:
                    record = SP500HistoricalConstituent(
                        symbol=symbol,
                        added_date=current_add["date"],
                        removed_date=None,  # Still active
                        removal_reason=None,
                        company_name=current_add.get("name"),
                        membership_source=current_add.get("source"),
                    )
                    session.add(record)
                    records_created += 1
            
            await session.commit()
            
            # Log summary
            still_active = len([s for s, e in membership_events.items() 
                               if any(ev["type"] == "add" for ev in e) and s in current_symbols])
            historical_removals = len([s for s, e in membership_events.items() 
                                       if any(ev["type"] == "remove" for ev in e)])
            
            logger.info("=" * 60)
            logger.info("HISTORICAL CONSTITUENTS INGESTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total unique symbols processed: {len(symbols_processed)}")
            logger.info(f"Membership records created: {records_created}")
            logger.info(f"Currently active members: {still_active}")
            logger.info(f"Historical removals tracked: {historical_removals}")
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
        logger.info("=" * 60)
        
        if placeholder_count > 0:
            logger.warning(f"WARNING: {placeholder_count} records still have placeholder dates!")
    
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
