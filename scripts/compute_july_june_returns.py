#!/usr/bin/env python3
"""
PATH: scripts/compute_july_june_returns.py
PURPOSE:
  - Compute and persist July–June returns (Fama-French convention) into `july_june_returns`.
  - Supports both Tier-1 (FMP daily prices) and Tier-2 (CRSP monthly returns).
  - This is a focused, reproducibility-friendly entrypoint used by the publication pipeline.
  
ROLE IN ARCHITECTURE:
  - Data preparation / bias-correction step (research-grade returns).

MAIN EXPORTS:
  - main(): CLI entrypoint.

NON-RESPONSIBILITIES:
  - Does NOT compute rolling windows, factor premiums, or ANOVAs (see `scripts/compute_research_metrics.py`).
  - Does NOT ingest price data (see ingestion scripts).

USAGE:
  # Tier-1 (FMP daily prices - default)
  python scripts/compute_july_june_returns.py --data-tier tier1
  
  # Tier-2 (CRSP monthly returns)
  python scripts/compute_july_june_returns.py --data-tier tier2

NOTES FOR FUTURE AI:
  - `formation_year` refers to the fiscal-year data used for sorting, not the return period year.
  - Return period is July(formation_year+1) to June(formation_year+2).
  - Defaults are chosen to cover the paper sample (FY 1994+ enables Jul 1995+).
  - Tier-2 requires CRSP data to be ingested first (see ingest_wrds_tier2.py).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Make `backend/app` importable as `app.*`
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def _compute_symbol_returns(
    symbol: str,
    start_formation_year: int,
    end_formation_year: int,
    price_mode: str,
    session: AsyncSession,
) -> tuple[str, dict, dict]:
    """
    Compute July-June returns for a single symbol (all years).
    Returns (symbol, year_results, audit_stats).
    """
    from app.services.return_calculator import JulyJuneReturnCalculator
    
    calculator = JulyJuneReturnCalculator(session, data_tier="tier1", price_mode=price_mode)
    year_results = {}
    audit = {"adj_close_days": 0, "close_fallback_days": 0, "dividend_days": 0, "records": 0}
    
    for year in range(start_formation_year, end_formation_year + 1):
        ret = await calculator.compute_july_june_return(symbol, year)
        if ret:
            year_results[year] = ret
            audit["adj_close_days"] += int(getattr(ret, "adj_close_days", 0))
            audit["close_fallback_days"] += int(getattr(ret, "close_fallback_days", 0))
            audit["dividend_days"] += int(getattr(ret, "dividend_days", 0))
            audit["records"] += 1
    
    return symbol, year_results, audit


async def _run_tier1(
    start_formation_year: int,
    end_formation_year: int,
    *,
    price_mode: str,
    symbols: list[str] | None,
    parallel_workers: int = 10,
) -> int:
    """
    Compute and store July–June returns using FMP daily prices (Tier-1).
    
    Optimized for large ticker sets with parallel processing.
    """
    from sqlalchemy import select, func
    from app.db.models import FMPDailyPrice
    from app.services.return_calculator import JulyJuneReturnCalculator
    
    engine = create_async_engine(settings.async_database_url, echo=False, pool_size=parallel_workers + 2)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # Get all symbols with daily price data if not specified
        if symbols is None:
            async with async_session() as session:
                result = await session.execute(select(func.distinct(FMPDailyPrice.symbol)))
                symbols = [r[0] for r in result.fetchall() if r[0]]
        
        logger.info(f"Computing July-June returns for {len(symbols)} symbols, years {start_formation_year}-{end_formation_year}")
        logger.info(f"Using {parallel_workers} parallel workers")
        
        # Process symbols in batches with bounded parallelism
        semaphore = asyncio.Semaphore(parallel_workers)
        all_results = {}
        total_audit = {"adj_close_days": 0, "close_fallback_days": 0, "dividend_days": 0, "records": 0}
        processed = 0
        
        async def process_symbol(sym: str):
            nonlocal processed
            async with semaphore:
                async with async_session() as session:
                    symbol, year_results, audit = await _compute_symbol_returns(
                        sym, start_formation_year, end_formation_year, price_mode, session
                    )
                    return symbol, year_results, audit
        
        # Process in chunks to manage memory and provide progress updates
        chunk_size = 100
        for chunk_start in range(0, len(symbols), chunk_size):
            chunk = symbols[chunk_start:chunk_start + chunk_size]
            tasks = [process_symbol(sym) for sym in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, Exception):
                    logger.warning(f"Error processing symbol: {res}")
                    continue
                symbol, year_results, audit = res
                if year_results:
                    all_results[symbol] = year_results
                total_audit["adj_close_days"] += audit["adj_close_days"]
                total_audit["close_fallback_days"] += audit["close_fallback_days"]
                total_audit["dividend_days"] += audit["dividend_days"]
                total_audit["records"] += audit["records"]
            
            processed += len(chunk)
            logger.info(f"Progress: {processed}/{len(symbols)} symbols ({total_audit['records']} records)")
        
        # Log audit summary
        denom = total_audit["adj_close_days"] + total_audit["close_fallback_days"]
        fallback_share = (total_audit["close_fallback_days"] / denom) if denom > 0 else 0.0
        logger.info(
            "Tier-1 return definition audit: "
            f"price_mode={price_mode}, records={total_audit['records']}, "
            f"adj_close_days={total_audit['adj_close_days']}, "
            f"close_fallback_days={total_audit['close_fallback_days']}, "
            f"fallback_share={round(fallback_share, 6)}, "
            f"dividend_days={total_audit['dividend_days']}"
        )
        
        # Save all results
        async with async_session() as session:
            calculator = JulyJuneReturnCalculator(session, data_tier="tier1", price_mode=price_mode)
            saved = await calculator.save_july_june_returns(all_results)
            await session.commit()
            return saved
    finally:
        await engine.dispose()


async def _run_tier2(start_formation_year: int, end_formation_year: int) -> int:
    """
    Compute and store July–June returns using CRSP monthly returns (Tier-2).
    """
    from app.services.tier2_return_calculator import Tier2JulyJuneCalculator
    
    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            calculator = Tier2JulyJuneCalculator(session)
            results = await calculator.compute_all_returns(
                start_year=start_formation_year,
                end_year=end_formation_year,
                save_results=True,
            )
            return len(results)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute July–June returns (Fama-French convention)")
    parser.add_argument(
        "--start-formation-year",
        type=int,
        default=1990,
        help="First formation year (FY year) to compute (default: 1990 for full history).",
    )
    parser.add_argument(
        "--end-formation-year",
        type=int,
        default=2023,
        help="Last formation year (FY year) to compute (default: 2023).",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=10,
        help="Number of parallel workers for Tier-1 computation (default: 10).",
    )
    parser.add_argument(
        "--data-tier",
        choices=["tier1", "tier2"],
        default="tier1",
        help="Data tier to use: tier1 (FMP daily) or tier2 (CRSP monthly). Default: tier1.",
    )
    parser.add_argument(
        "--price-mode",
        choices=[
            # Current (recommended) modes
            "total_return_dividends",
            "price_only",
            # Backwards-compatible aliases (kept for older docs/scripts)
            "adj_close_only",
            "adj_close_fallback_close",
        ],
        default="total_return_dividends",
        help=(
            "Tier-1 price construction policy. "
            "total_return_dividends is publication-grade (split-adjusted close + dividends → TSR proxy); "
            "price_only is a price-return sensitivity mode (no dividends). "
            "Legacy aliases adj_close_only/adj_close_fallback_close are accepted for backwards compatibility."
        ),
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Optional comma-separated ticker list (e.g., SPY,AAPL). Default: all symbols with Tier-1 price data.",
    )
    args = parser.parse_args()

    if args.end_formation_year < args.start_formation_year:
        raise SystemExit("end_formation_year must be >= start_formation_year")

    logger.info(f"Computing July-June returns for formation years {args.start_formation_year}-{args.end_formation_year}")
    logger.info(f"Data tier: {args.data_tier}")

    if args.data_tier == "tier1":
        symbols = None
        if isinstance(args.symbols, str) and args.symbols.strip():
            symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        saved = asyncio.run(
            _run_tier1(
                args.start_formation_year,
                args.end_formation_year,
                price_mode=args.price_mode,
                symbols=symbols,
                parallel_workers=args.parallel_workers,
            )
        )
        print(f"Saved {saved} Tier-1 (FMP) July–June return records to `july_june_returns`.")
    else:
        saved = asyncio.run(_run_tier2(args.start_formation_year, args.end_formation_year))
        print(f"Saved {saved} Tier-2 (CRSP) July–June return records to `july_june_returns`.")


if __name__ == "__main__":
    main()
