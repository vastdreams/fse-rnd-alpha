#!/usr/bin/env python3
"""
PATH: scripts/recompute_all_concurrent.py
PURPOSE:
  - Recompute all rolling window analysis with fixed code
  - Runs 5yr, 10yr, 20yr windows CONCURRENTLY
  - Also recomputes factor premiums and runs ANOVAs

USAGE:
  cd /path/to/fse-rnd-alpha
  source venv/bin/activate
  python scripts/recompute_all_concurrent.py
"""

import sys
import os
import asyncio
import time

# Add backend directory to path for imports (so 'app' module works)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_dir)
sys.path.insert(0, project_root)
os.chdir(project_root)

from dotenv import load_dotenv
load_dotenv()


async def recompute_all():
    """Run all recomputation tasks concurrently."""
    
    # Import after path setup
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Get database URL and convert to async
    database_url = os.environ.get(
        "DATABASE_URL", 
        "postgresql+psycopg2://postgres:postgres@localhost:5432/rd_alpha"
    )
    # Convert to asyncpg
    if "psycopg2" in database_url:
        database_url = database_url.replace("psycopg2", "asyncpg")
    elif "+psycopg" in database_url:
        database_url = database_url.replace("+psycopg", "+asyncpg")
    elif "postgresql://" in database_url and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"🔌 Connecting to database...")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    start_time = time.time()
    
    async with async_session() as session:
        # Import services (backend is in PYTHONPATH)
        from app.services.cohort_classifier import CohortClassifier
        from app.services.rolling_window import RollingWindowAnalyzer
        from app.services.statistics import StatisticalAnalyzer
        
        # Step 1: Classify cohort first (dependency for windows)
        print("\n📊 Step 1: Classifying research cohort...")
        classifier = CohortClassifier(session)
        cohort_result = await classifier.classify_all_companies()
        print(f"   ✅ Cohort classified: {cohort_result}")
        
        # Step 2: Compute rolling windows CONCURRENTLY
        print("\n📈 Step 2: Computing rolling windows (CONCURRENT)...")
        analyzer = RollingWindowAnalyzer(session)
        
        async def compute_window(window_type: str):
            print(f"   🔄 Starting {window_type} windows...")
            result = await analyzer.compute_all_rolling_windows(window_type, save_results=True)
            print(f"   ✅ {window_type}: {len(result)} windows computed")
            return window_type, result
        
        # Run all three window computations concurrently
        window_tasks = [
            compute_window("5yr"),
            compute_window("10yr"),
            compute_window("20yr"),
        ]
        window_results = await asyncio.gather(*window_tasks)
        
        for wtype, results in window_results:
            print(f"   📊 {wtype}: {len(results)} windows")
        
        # Step 3: Compute factor premiums
        print("\n💰 Step 3: Computing annual factor premiums...")
        premium_results = await analyzer.compute_annual_factor_premiums(save_results=True)
        print(f"   ✅ Factor premiums: {len(premium_results)} years")
        
        # Step 4: Run ANOVAs CONCURRENTLY
        print("\n📉 Step 4: Running ANOVA tests (CONCURRENT)...")
        stats_analyzer = StatisticalAnalyzer(session)
        
        async def run_anova(window_type: str):
            print(f"   🔄 Starting ANOVA for {window_type}...")
            result = await stats_analyzer.run_all_anovas(window_type)
            print(f"   ✅ {window_type} ANOVA: {len(result)} tests")
            return window_type, result
        
        anova_tasks = [
            run_anova("5yr"),
            run_anova("10yr"),
            run_anova("20yr"),
        ]
        anova_results = await asyncio.gather(*anova_tasks)
        
        # Commit all changes
        await session.commit()
    
    await engine.dispose()
    
    elapsed = time.time() - start_time
    print(f"\n✅ All recomputation complete in {elapsed:.1f}s")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for wtype, results in window_results:
        print(f"  {wtype} windows: {len(results)}")
    print(f"  Factor premiums: {len(premium_results)} years")
    for wtype, results in anova_results:
        print(f"  {wtype} ANOVAs: {len(results)}")
    print("="*60)


if __name__ == "__main__":
    print("🚀 Starting concurrent recomputation of rolling window analysis...")
    print("   This will update all quintile statistics with the fixed code.")
    print("")
    
    asyncio.run(recompute_all())

