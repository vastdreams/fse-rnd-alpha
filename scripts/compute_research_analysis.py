#!/usr/bin/env python3
"""
PATH: scripts/compute_research_analysis.py
PURPOSE:
  - Run full 500-company research analysis
  - Classify cohort, compute rolling windows, factor premiums, ANOVAs

USAGE:
  python scripts/compute_research_analysis.py
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.session import Base
from app.db.models import (
    ResearchCohort, RollingWindowResult, AnovaResult, FactorPremium
)
from app.services.cohort_classifier import CohortClassifier
from app.services.rolling_window import RollingWindowAnalyzer
from app.services.statistics import StatisticalAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_full_analysis():
    """Run complete research analysis pipeline."""
    
    # Database connection
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:rd_alpha_secure_2024@localhost:5432/rd_alpha"
    )
    
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create tables if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Starting Research Analysis Pipeline")
        logger.info("=" * 60)
        
        # Step 1: Classify cohort
        logger.info("\n[STEP 1/5] Classifying 500-company cohort...")
        classifier = CohortClassifier(session)
        cohort_result = await classifier.classify_all_companies()
        logger.info(f"  - Total companies: {cohort_result['total_companies']}")
        logger.info(f"  - 5-year eligible: {cohort_result['cohort_5yr']}")
        logger.info(f"  - 10-year eligible: {cohort_result['cohort_10yr']}")
        logger.info(f"  - 20-year eligible: {cohort_result['cohort_20yr']}")
        
        # Step 2: Compute rolling windows
        logger.info("\n[STEP 2/5] Computing rolling windows...")
        analyzer = RollingWindowAnalyzer(session)
        
        for window_type in ["5yr", "10yr", "20yr"]:
            logger.info(f"  - Computing {window_type} windows...")
            results = await analyzer.compute_all_rolling_windows(window_type, save_results=True)
            logger.info(f"    Computed {len(results)} windows")
        
        # Step 3: Compute factor premiums
        logger.info("\n[STEP 3/5] Computing annual factor premiums...")
        premiums = await analyzer.compute_annual_factor_premiums(save_results=True)
        logger.info(f"  - Computed premiums for {len(premiums)} years")
        
        if premiums:
            avg_premium = sum(p["rd_premium"] for p in premiums) / len(premiums)
            positive_years = sum(1 for p in premiums if p["rd_premium"] > 0)
            logger.info(f"  - Average R&D premium: {avg_premium:.2f}%")
            logger.info(f"  - Positive premium years: {positive_years}/{len(premiums)}")
        
        # Step 4: Run ANOVA tests
        logger.info("\n[STEP 4/5] Running ANOVA tests...")
        stats_analyzer = StatisticalAnalyzer(session)
        
        for window_type in ["5yr", "10yr", "20yr"]:
            logger.info(f"  - Running ANOVAs for {window_type} windows...")
            anova_results = await stats_analyzer.run_all_anovas(window_type)
            significant = sum(1 for r in anova_results if r.get("significant"))
            logger.info(f"    {len(anova_results)} tests, {significant} significant (p<0.05)")
        
        # Step 5: Generate publication statistics
        logger.info("\n[STEP 5/5] Generating publication statistics...")
        pub_stats = await stats_analyzer.get_publication_statistics()
        
        logger.info("\n" + "=" * 60)
        logger.info("PUBLICATION SUMMARY")
        logger.info("=" * 60)
        
        for window_type in ["5yr", "10yr", "20yr"]:
            if window_type in pub_stats:
                ws = pub_stats[window_type]
                anova = ws.get("anova", {})
                ttest = ws.get("ttest_high_vs_low", {})
                
                logger.info(f"\n{window_type.upper()} WINDOW:")
                logger.info(f"  ANOVA F-statistic: {anova.get('f_statistic', 'N/A')}")
                logger.info(f"  ANOVA p-value: {anova.get('p_value', 'N/A')}")
                logger.info(f"  Effect size (η²): {anova.get('eta_squared', 'N/A')}")
                logger.info(f"  High-Low Difference: {ttest.get('mean_difference', 'N/A')}%")
                logger.info(f"  Significant: {'Yes' if anova.get('significant_005') else 'No'}")
        
        if "rd_factor_premium" in pub_stats:
            rdp = pub_stats["rd_factor_premium"]
            logger.info(f"\nR&D FACTOR PREMIUM:")
            logger.info(f"  Mean: {rdp.get('mean', 'N/A')}%")
            logger.info(f"  Std Dev: {rdp.get('std', 'N/A')}%")
            logger.info(f"  T-statistic: {rdp.get('t_statistic', 'N/A')}")
            logger.info(f"  p-value: {rdp.get('p_value', 'N/A')}")
            logger.info(f"  Significant: {'Yes' if rdp.get('significant') else 'No'}")
        
        elapsed = datetime.now() - start_time
        logger.info(f"\nAnalysis completed in {elapsed.total_seconds():.1f} seconds")
        logger.info("=" * 60)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_full_analysis())

