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


async def _run_tier1(
    start_formation_year: int,
    end_formation_year: int,
    *,
    price_mode: str,
    symbols: list[str] | None,
) -> int:
    """
    Compute and store July–June returns using FMP daily prices (Tier-1).
    """
    from app.services.return_calculator import JulyJuneReturnCalculator
    
    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            calculator = JulyJuneReturnCalculator(session, data_tier="tier1", price_mode=price_mode)
            results = await calculator.compute_all_july_june_returns(
                start_formation_year=start_formation_year,
                end_formation_year=end_formation_year,
                symbols=symbols,
            )
            # Return-definition audit (publication readiness): how often do we fall back to close?
            total_adj_days = 0
            total_fallback_days = 0
            total_records = 0
            for _, by_year in results.items():
                for _, r in by_year.items():
                    total_records += 1
                    total_adj_days += int(getattr(r, "adj_close_days", 0))
                    total_fallback_days += int(getattr(r, "close_fallback_days", 0))

            denom = total_adj_days + total_fallback_days
            fallback_share = (total_fallback_days / denom) if denom > 0 else 0.0
            logger.info(
                "Tier-1 return definition audit",
                extra={
                    "price_mode": price_mode,
                    "records": total_records,
                    "adj_close_days": total_adj_days,
                    "close_fallback_days": total_fallback_days,
                    "close_fallback_share": round(fallback_share, 6),
                },
            )
            saved = await calculator.save_july_june_returns(results)
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
        default=1994,
        help="First formation year (FY year) to compute (default: 1994).",
    )
    parser.add_argument(
        "--end-formation-year",
        type=int,
        default=2023,
        help="Last formation year (FY year) to compute (default: 2023).",
    )
    parser.add_argument(
        "--data-tier",
        choices=["tier1", "tier2"],
        default="tier1",
        help="Data tier to use: tier1 (FMP daily) or tier2 (CRSP monthly). Default: tier1.",
    )
    parser.add_argument(
        "--price-mode",
        choices=["adj_close_only", "adj_close_fallback_close"],
        default="adj_close_only",
        help=(
            "Tier-1 price construction policy. "
            "adj_close_only is publication-grade (no silent fallback); "
            "adj_close_fallback_close is a coverage-oriented sensitivity mode."
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
            )
        )
        print(f"Saved {saved} Tier-1 (FMP) July–June return records to `july_june_returns`.")
    else:
        saved = asyncio.run(_run_tier2(args.start_formation_year, args.end_formation_year))
        print(f"Saved {saved} Tier-2 (CRSP) July–June return records to `july_june_returns`.")


if __name__ == "__main__":
    main()
