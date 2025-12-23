#!/usr/bin/env python3
"""
PATH: scripts/compute_research_metrics.py
PURPOSE:
  - Precompute all research metrics for R&D Alpha scoring
  - Computes July-June returns, momentum, and volatility
  - Populates cache tables for fast scoring

ROLE IN ARCHITECTURE:
  - Data preparation script for research-grade analysis
  - Run once to populate caches, then periodically to update

USAGE:
  python scripts/compute_research_metrics.py [--start-year 2000] [--end-year 2024]
  
  Options:
    --start-year: First year to compute (default: 2000)
    --end-year: Last year to compute (default: 2024)
    --returns-only: Only compute July-June returns
    --momentum-only: Only compute momentum
    --volatility-only: Only compute volatility

NOTES FOR FUTURE AI:
  - Run this script after ingesting new price data
  - Momentum needs 3 years of prior data (start at least 2003)
  - Volatility needs 3 years of daily prices
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, JulyJuneReturn, MomentumCache, VolatilityCache
from app.services.return_calculator import JulyJuneReturnCalculator
from app.services.momentum_service import MomentumCalculator
from app.services.volatility_service import VolatilityCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_tables(engine):
    """Create research metric tables if they don't exist."""
    async with engine.begin() as conn:
        # Create only the new tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created")


async def compute_july_june_returns(
    session: AsyncSession,
    start_year: int,
    end_year: int
) -> int:
    """
    Compute July-June returns for all symbols.
    
    Returns count of records saved.
    """
    logger.info(f"Computing July-June returns for {start_year}-{end_year}...")
    
    calculator = JulyJuneReturnCalculator(session)
    
    # Compute returns
    results = await calculator.compute_all_july_june_returns(
        start_formation_year=start_year,
        end_formation_year=end_year - 1  # Need next year's June for returns
    )
    
    # Count successful computations
    total_results = sum(len(years) for years in results.values())
    logger.info(f"Computed {total_results} July-June return records")
    
    # Save to database
    count = await calculator.save_july_june_returns(results)
    
    return count


async def compute_momentum(
    session: AsyncSession,
    start_year: int,
    end_year: int
) -> int:
    """
    Compute momentum for all symbols.
    
    Requires July-June returns to be computed first.
    """
    logger.info(f"Computing momentum for {start_year}-{end_year}...")
    
    # Start year must be at least 3 years after first July-June return year
    effective_start = max(start_year, start_year + 3)
    
    calculator = MomentumCalculator(session)
    
    # Compute momentum
    results = await calculator.precompute_all_momentum(
        start_year=effective_start,
        end_year=end_year,
        use_july_june=True
    )
    
    # Count successful computations
    total_results = sum(len(years) for years in results.values())
    logger.info(f"Computed {total_results} momentum records")
    
    # Save to database
    count = await calculator.save_momentum_cache(results)
    
    return count


async def compute_volatility(
    session: AsyncSession,
    start_year: int,
    end_year: int
) -> int:
    """
    Compute volatility for all symbols.
    
    Requires daily price data.
    """
    logger.info(f"Computing volatility for {start_year}-{end_year}...")
    
    # Start year must be at least 3 years after first price data
    effective_start = max(start_year, start_year + 3)
    
    calculator = VolatilityCalculator(session)
    
    # Compute volatility
    results = await calculator.precompute_all_volatility(
        start_year=effective_start,
        end_year=end_year
    )
    
    # Count successful computations
    total_results = sum(len(years) for years in results.values())
    logger.info(f"Computed {total_results} volatility records")
    
    # Save to database
    count = await calculator.save_volatility_cache(results)
    
    return count


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compute research metrics for R&D Alpha scoring"
    )
    parser.add_argument(
        "--start-year", type=int, default=2000,
        help="First year to compute (default: 2000)"
    )
    parser.add_argument(
        "--end-year", type=int, default=2024,
        help="Last year to compute (default: 2024)"
    )
    parser.add_argument(
        "--returns-only", action="store_true",
        help="Only compute July-June returns"
    )
    parser.add_argument(
        "--momentum-only", action="store_true",
        help="Only compute momentum"
    )
    parser.add_argument(
        "--volatility-only", action="store_true",
        help="Only compute volatility"
    )
    parser.add_argument(
        "--full-recompute", action="store_true",
        help="Run entire research pipeline including rolling windows and ANOVA"
    )
    parser.add_argument(
        "--database-url", type=str,
        default=settings.async_database_url,
        help="Database URL"
    )
    
    args = parser.parse_args()
    
    # Determine what to compute
    compute_all = not (args.returns_only or args.momentum_only or args.volatility_only)
    
    logger.info("=" * 60)
    logger.info("R&D Alpha Research Metrics Computation")
    logger.info("=" * 60)
    logger.info(f"Start year: {args.start_year}")
    logger.info(f"End year: {args.end_year}")
    logger.info(f"Database: {args.database_url.split('@')[-1]}")
    logger.info(f"Full recompute: {args.full_recompute}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    # Create database connection
    engine = create_async_engine(args.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Ensure tables exist
    await create_tables(engine)
    
    async with async_session() as session:
        # Step 0: Cohort Classification
        if args.full_recompute:
            logger.info("\n" + "=" * 40)
            logger.info("STEP 0: Cohort Classification (Survivorship-Bias-Free)")
            logger.info("=" * 40)
            from app.services.cohort_classifier import CohortClassifier
            classifier = CohortClassifier(session)
            await classifier.classify_all_companies()
            logger.info("Cohort classification complete")

        # Step 1: July-June Returns
        if compute_all or args.returns_only:
            logger.info("\n" + "=" * 40)
            logger.info("STEP 1: July-June Returns")
            logger.info("=" * 40)
            returns_count = await compute_july_june_returns(
                session, args.start_year, args.end_year
            )
            logger.info(f"Saved {returns_count} July-June return records")
        
        # Step 2: Momentum
        if compute_all or args.momentum_only:
            logger.info("\n" + "=" * 40)
            logger.info("STEP 2: Momentum (3-year excess returns)")
            logger.info("=" * 40)
            momentum_count = await compute_momentum(
                session, args.start_year, args.end_year
            )
            logger.info(f"Saved {momentum_count} momentum records")
        
        # Step 3: Volatility
        if compute_all or args.volatility_only:
            logger.info("\n" + "=" * 40)
            logger.info("STEP 3: Volatility (3-year daily std dev)")
            logger.info("=" * 40)
            volatility_count = await compute_volatility(
                session, args.start_year, args.end_year
            )
            logger.info(f"Saved {volatility_count} volatility records")

        # Step 4: Rolling Window Analysis
        if args.full_recompute:
            logger.info("\n" + "=" * 40)
            logger.info("STEP 4: Rolling Window Analysis")
            logger.info("=" * 40)
            from app.services.rolling_window import RollingWindowAnalyzer
            # use_july_june=True is default for research-grade
            analyzer = RollingWindowAnalyzer(session, use_july_june=True)
            for window_type in ["5yr", "10yr", "20yr"]:
                logger.info(f"Computing {window_type} rolling windows...")
                await analyzer.compute_all_rolling_windows(window_type, save_results=True)
            
            logger.info("\n" + "=" * 40)
            logger.info("STEP 5: Statistical Analysis (ANOVA/t-tests)")
            logger.info("=" * 40)
            from app.services.statistics import StatisticalAnalyzer
            stats_analyzer = StatisticalAnalyzer(session)
            for window_type in ["5yr", "10yr", "20yr"]:
                logger.info(f"Running aggregate statistics for {window_type}...")
                await stats_analyzer.run_all_anovas(window_type)
            
            logger.info("Full research pipeline complete.")
    
    # Cleanup
    await engine.dispose()
    
    elapsed = datetime.now() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("COMPUTATION COMPLETE")
    logger.info(f"Total time: {elapsed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

