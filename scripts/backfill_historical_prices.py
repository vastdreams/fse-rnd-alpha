#!/usr/bin/env python3
"""
PATH: scripts/backfill_historical_prices.py
PURPOSE:
  - Backfill daily prices for ALL historical S&P 500 tickers (not just current constituents)
  - Uses concurrent fetching with rate limiting for FMP Ultimate tier (3000 calls/min)
  - Bulk upserts for maximum throughput

USAGE:
  python scripts/backfill_historical_prices.py                    # Backfill all missing
  python scripts/backfill_historical_prices.py --from-year 1995   # Start from specific year
  python scripts/backfill_historical_prices.py --symbols AAPL,MSFT  # Specific symbols only
"""

import asyncio
import logging
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Union
import aiohttp

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FMP API configuration
FMP_BASE_URL = "https://financialmodelingprep.com"
MAX_CONCURRENT_REQUESTS = 50  # Conservative for 3000 calls/min
BATCH_SIZE = 50  # Symbols per batch for progress logging
DEFAULT_START_DATE = "1990-01-01"


class FMPBulkPriceIngestor:
    """
    Bulk ingestion of historical prices from FMP API.
    
    Designed for:
    - High concurrency (FMP Ultimate: 3000 calls/min)
    - Bulk database inserts (psycopg2 execute_values)
    - Progress tracking for long-running backfills
    """
    
    def __init__(self, api_key: str, db_url: str, max_concurrent: int = MAX_CONCURRENT_REQUESTS):
        self.api_key = api_key
        self.db_url = db_url
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None
        self.call_count = 0
        self.rate_limit_start = datetime.now()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _get(self, endpoint: str, params: Dict = None) -> Any:
        """Make GET request with rate limiting."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        url = f"{FMP_BASE_URL}{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key
        
        async with self.semaphore:
            self.call_count += 1
            
            # Basic rate limiting check
            elapsed = (datetime.now() - self.rate_limit_start).total_seconds()
            if elapsed < 60 and self.call_count > 2900:
                # Approaching limit, pause briefly
                await asyncio.sleep(1)
            elif elapsed >= 60:
                # Reset counter
                self.call_count = 0
                self.rate_limit_start = datetime.now()
            
            for attempt in range(3):
                try:
                    async with self.session.get(url, params=params, timeout=60) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            logger.warning(f"Rate limited, waiting {2 ** attempt}s...")
                            await asyncio.sleep(2 ** attempt)
                        else:
                            logger.debug(f"API error {response.status}: {endpoint}")
                            return None
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout for {endpoint}, attempt {attempt + 1}")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Request error: {e}")
                    return None
            
            return None
    
    async def get_historical_prices(self, symbol: str, from_date: str = DEFAULT_START_DATE) -> List[Dict]:
        """Fetch full historical prices for a symbol."""
        params = {"symbol": symbol, "from": from_date}
        data = await self._get("/stable/historical-price-eod/full", params)
        return data if isinstance(data, list) else []
    
    async def get_dividends(self, symbol: str) -> List[Dict]:
        """Fetch dividend history for a symbol."""
        data = await self._get("/stable/dividends", {"symbol": symbol})
        return data if isinstance(data, list) else []


async def get_all_historical_symbols(session: AsyncSession) -> Set[str]:
    """Get all unique symbols from sp500_historical_constituents."""
    result = await session.execute(
        text("SELECT DISTINCT symbol FROM sp500_historical_constituents WHERE symbol IS NOT NULL")
    )
    return {row[0].upper() for row in result.fetchall() if row[0]}


async def get_symbols_with_prices(session: AsyncSession) -> Set[str]:
    """Get symbols that already have price data."""
    result = await session.execute(
        text("SELECT DISTINCT symbol FROM fmp_daily_prices WHERE symbol IS NOT NULL")
    )
    return {row[0].upper() for row in result.fetchall() if row[0]}


async def get_symbols_with_dividends(session: AsyncSession) -> Set[str]:
    """Get symbols that already have dividend data."""
    result = await session.execute(
        text("SELECT DISTINCT symbol FROM fmp_dividends WHERE symbol IS NOT NULL")
    )
    return {row[0].upper() for row in result.fetchall() if row[0]}


async def upsert_prices_bulk(session: AsyncSession, prices: List[Dict], symbol: str) -> int:
    """Bulk upsert price records for a symbol."""
    if not prices:
        return 0
    
    values = []
    for p in prices:
        try:
            price_date_raw = p.get("date")
            if not price_date_raw:
                continue
            
            # Convert string date to date object if needed
            if isinstance(price_date_raw, str):
                price_date = datetime.strptime(price_date_raw, "%Y-%m-%d").date()
            else:
                price_date = price_date_raw
            
            values.append({
                "symbol": symbol,
                "date": price_date,
                "open": p.get("open"),
                "high": p.get("high"),
                "low": p.get("low"),
                "close": p.get("close"),
                "adj_close": p.get("adjClose"),
                "volume": p.get("volume"),
                "change_pct": p.get("changePercent"),
                "vwap": p.get("vwap"),
            })
        except Exception:
            continue
    
    if not values:
        return 0
    
    # Batch insert using raw SQL for performance
    insert_sql = text("""
        INSERT INTO fmp_daily_prices (symbol, date, open, high, low, close, adj_close, volume, change_pct, vwap)
        VALUES (:symbol, :date, :open, :high, :low, :close, :adj_close, :volume, :change_pct, :vwap)
        ON CONFLICT (symbol, date) DO UPDATE SET
            close = EXCLUDED.close,
            adj_close = EXCLUDED.adj_close,
            volume = EXCLUDED.volume
    """)
    
    for v in values:
        await session.execute(insert_sql, v)
    
    return len(values)


def _parse_date(date_raw: Any) -> Optional[date]:
    """Parse date from string or date object."""
    if not date_raw:
        return None
    if isinstance(date_raw, str):
        try:
            return datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    return date_raw


async def upsert_dividends_bulk(session: AsyncSession, dividends: List[Dict], symbol: str) -> int:
    """Bulk upsert dividend records for a symbol."""
    if not dividends:
        return 0
    
    values = []
    for d in dividends:
        try:
            div_date = _parse_date(d.get("date"))
            if not div_date:
                continue
            
            values.append({
                "symbol": symbol,
                "date": div_date,
                "dividend": d.get("dividend"),
                "adj_dividend": d.get("adjDividend"),
                "record_date": _parse_date(d.get("recordDate")),
                "payment_date": _parse_date(d.get("paymentDate")),
                "declaration_date": _parse_date(d.get("declarationDate")),
            })
        except Exception:
            continue
    
    if not values:
        return 0
    
    insert_sql = text("""
        INSERT INTO fmp_dividends (symbol, date, dividend, adj_dividend, record_date, payment_date, declaration_date)
        VALUES (:symbol, :date, :dividend, :adj_dividend, :record_date, :payment_date, :declaration_date)
        ON CONFLICT (symbol, date) DO UPDATE SET
            dividend = EXCLUDED.dividend,
            adj_dividend = EXCLUDED.adj_dividend
    """)
    
    for v in values:
        await session.execute(insert_sql, v)
    
    return len(values)


async def backfill_prices_for_symbols(
    symbols: List[str],
    from_date: str = DEFAULT_START_DATE,
    include_dividends: bool = True,
):
    """
    Backfill prices (and optionally dividends) for a list of symbols.
    """
    api_key = settings.FMP_API_KEY
    if not api_key:
        raise ValueError("FMP_API_KEY not configured")
    
    engine = create_async_engine(settings.async_database_url)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    total_prices = 0
    total_dividends = 0
    errors = []
    
    try:
        async with FMPBulkPriceIngestor(api_key, str(settings.DATABASE_URL)) as ingestor:
            # Process in batches for progress logging
            for batch_start in range(0, len(symbols), BATCH_SIZE):
                batch = symbols[batch_start:batch_start + BATCH_SIZE]
                
                # Fetch prices for batch concurrently
                price_tasks = [ingestor.get_historical_prices(s, from_date) for s in batch]
                price_results = await asyncio.gather(*price_tasks, return_exceptions=True)
                
                # Fetch dividends if requested
                if include_dividends:
                    div_tasks = [ingestor.get_dividends(s) for s in batch]
                    div_results = await asyncio.gather(*div_tasks, return_exceptions=True)
                else:
                    div_results = [[] for _ in batch]
                
                # Store results
                async with async_session_maker() as session:
                    for symbol, prices, dividends in zip(batch, price_results, div_results):
                        try:
                            if isinstance(prices, Exception):
                                errors.append((symbol, str(prices)))
                                continue
                            
                            if prices:
                                n_prices = await upsert_prices_bulk(session, prices, symbol)
                                total_prices += n_prices
                            
                            if include_dividends and dividends and not isinstance(dividends, Exception):
                                n_divs = await upsert_dividends_bulk(session, dividends, symbol)
                                total_dividends += n_divs
                        
                        except Exception as e:
                            errors.append((symbol, str(e)))
                    
                    await session.commit()
                
                # Progress log
                progress = min(batch_start + BATCH_SIZE, len(symbols))
                logger.info(f"Progress: {progress}/{len(symbols)} symbols, {total_prices} prices, {total_dividends} dividends")
        
        return {
            "symbols_processed": len(symbols),
            "total_prices": total_prices,
            "total_dividends": total_dividends,
            "errors": errors[:20],  # Limit error list
            "error_count": len(errors),
        }
    
    finally:
        await engine.dispose()


async def main(
    from_year: int = 1990,
    symbols: Optional[List[str]] = None,
    skip_existing: bool = True,
    include_dividends: bool = True,
):
    """
    Main backfill function.
    
    Args:
        from_year: Start year for price history
        symbols: Optional list of symbols (None = all historical S&P 500)
        skip_existing: If True, skip symbols that already have price data
        include_dividends: If True, also backfill dividend data
    """
    engine = create_async_engine(settings.async_database_url)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session_maker() as session:
            # Get target symbols
            if symbols:
                target_symbols = set(s.upper() for s in symbols)
            else:
                target_symbols = await get_all_historical_symbols(session)
            
            logger.info(f"Found {len(target_symbols)} historical S&P 500 symbols")
            
            # Skip existing if requested
            if skip_existing:
                existing_prices = await get_symbols_with_prices(session)
                target_symbols = target_symbols - existing_prices
                logger.info(f"After skipping existing: {len(target_symbols)} symbols need prices")
        
        if not target_symbols:
            logger.info("No symbols need backfilling")
            return {"symbols_processed": 0}
        
        # Convert to list and sort for reproducibility
        symbols_list = sorted(target_symbols)
        
        from_date = f"{from_year}-01-01"
        logger.info(f"Backfilling prices from {from_date} for {len(symbols_list)} symbols...")
        
        result = await backfill_prices_for_symbols(
            symbols_list,
            from_date=from_date,
            include_dividends=include_dividends,
        )
        
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Symbols processed: {result['symbols_processed']}")
        logger.info(f"Total price records: {result['total_prices']}")
        logger.info(f"Total dividend records: {result['total_dividends']}")
        logger.info(f"Errors: {result['error_count']}")
        if result['errors']:
            logger.info("Sample errors:")
            for sym, err in result['errors'][:5]:
                logger.info(f"  {sym}: {err}")
        logger.info("=" * 60)
        
        return result
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill historical prices for S&P 500 constituents")
    parser.add_argument("--from-year", type=int, default=1990, help="Start year for price history")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols (default: all historical)")
    parser.add_argument("--force", action="store_true", help="Don't skip symbols with existing data")
    parser.add_argument("--no-dividends", action="store_true", help="Skip dividend backfill")
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    
    asyncio.run(main(
        from_year=args.from_year,
        symbols=symbols,
        skip_existing=not args.force,
        include_dividends=not args.no_dividends,
    ))

