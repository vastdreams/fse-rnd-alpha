#!/usr/bin/env python3
"""
PATH: scripts/run_delisting_sensitivity.py
PURPOSE:
  - Run sensitivity analysis on R&D premium with different delisting return assumptions
  - Generates publication-ready sensitivity table
  - Tests robustness of results to delisting return methodology

PUBLICATION REQUIREMENT:
  Reviewers will want to see how sensitive results are to delisting assumptions.
  This script produces a table showing premium estimates under different scenarios.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

from app.core.config import settings
from app.db.models import DelistingReturn
from app.services.statistics import StatisticalAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Sensitivity scenarios
SCENARIOS = {
    "baseline": {
        "name": "Baseline (Price-based + Heuristic)",
        "adjustment": 0.0,  # No adjustment - use current values
        "description": "Current methodology with price-based estimation"
    },
    "optimistic": {
        "name": "Optimistic",
        "adjustment": 0.10,  # Add 10% to all delisting returns
        "description": "Assumes distress is less severe than estimated"
    },
    "pessimistic": {
        "name": "Pessimistic", 
        "adjustment": -0.10,  # Subtract 10% from all delisting returns
        "description": "Assumes distress is more severe than estimated"
    },
    "crsp_proxy": {
        "name": "CRSP Proxy",
        "adjustment": -0.05,  # Standard CRSP adjustment
        "description": "Approximate CRSP-style delisting return treatment"
    },
    "no_delisting": {
        "name": "Assume 0% Delisting Return",
        "adjustment": "set_zero",  # Special mode handled explicitly
        "description": "Assume delistings have 0% return (upper bound vs distress penalties)"
    }
}


async def run_scenario_analysis():
    """
    Run annual HML premium analysis under different delisting-return scenarios.

    Publication intent:
      - Sensitivity should be reported on the PRIMARY inference object:
        annual non-overlapping HML (Q5-Q1) premium series.
      - We compute the annual HML premium under each delisting assumption and compare
        mean premiums and t-stats.

    Safety:
      - We do NOT persist scenario modifications. We run each scenario, then roll back.
    """
    
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    results = {}
    
    async with async_session() as session:
        # Get baseline delisting returns
        baseline_result = await session.execute(
            select(DelistingReturn)
        )
        baseline_returns = {dr.symbol: dr.delist_return for dr in baseline_result.scalars().all()}
        
        logger.info(f"Found {len(baseline_returns)} delisting return records")
        
        baseline_mean = None
        
        for scenario_key, scenario in SCENARIOS.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Running scenario: {scenario['name']}")
            logger.info(f"{'='*60}")
            
            try:
                # Modify delisting returns for this scenario (in-transaction, no commit).
                if scenario_key != "baseline":
                    if scenario["adjustment"] == "set_zero":
                        await session.execute(update(DelistingReturn).values(delist_return=0.0))
                    else:
                        delta = float(scenario["adjustment"])
                        for symbol, baseline in baseline_returns.items():
                            adjusted = baseline + delta
                            # Cap at -1 (total loss) and +1 (double)
                            adjusted = max(-1.0, min(1.0, adjusted))
                            await session.execute(
                                update(DelistingReturn)
                                .where(DelistingReturn.symbol == symbol)
                                .values(delist_return=adjusted)
                            )
                
                # Compute annual HML premium (primary result)
                stats = StatisticalAnalyzer(session)
                annual = await stats.compute_annual_hml_premium(use_july_june=True)
                
                if "error" in annual:
                    results[scenario_key] = {
                        "name": scenario["name"],
                        "description": scenario["description"],
                        "error": annual,
                    }
                else:
                    mean_premium = float(annual["mean_premium"])
                    if scenario_key == "baseline":
                        baseline_mean = mean_premium
                    
                    results[scenario_key] = {
                        "name": scenario["name"],
                        "description": scenario["description"],
                        "annual_hml": {
                            "n_years": annual["n_years"],
                            "mean_premium_pct": mean_premium,
                            "t_statistic": annual["hac_adjusted"]["t_statistic"],
                            "p_value": annual["hac_adjusted"]["p_value"],
                            "significant_005": annual["hac_adjusted"]["significant"],
                        },
                    }
                    
                    if baseline_mean is not None and scenario_key != "baseline":
                        results[scenario_key]["annual_hml"]["delta_vs_baseline_pct"] = round(
                            mean_premium - baseline_mean, 4
                        )
            finally:
                # Roll back scenario modifications (never persist)
                await session.rollback()
    
    await engine.dispose()
    
    return results


def print_sensitivity_table(results: Dict):
    """Print publication-ready sensitivity table."""
    
    logger.info("\n" + "=" * 80)
    logger.info("DELISTING RETURN SENSITIVITY ANALYSIS")
    logger.info("=" * 80)
    
    print("\nTable: Annual HML Premium Sensitivity to Delisting Return Assumptions (Primary Result)")
    print("-" * 100)
    print(f"{'Scenario':<30} {'Mean Premium':>14} {'Δ vs Baseline':>16} {'t-stat':>10} {'p-value':>10}")
    print("-" * 100)

    for _, data in results.items():
        if "annual_hml" not in data:
            row = f"{data.get('name', 'Unknown'):<30} {'N/A':>14} {'N/A':>16} {'N/A':>10} {'N/A':>10}"
            print(row)
            continue

        annual = data["annual_hml"]
        delta = annual.get("delta_vs_baseline_pct")
        row = (
            f"{data['name']:<30}"
            f"{annual['mean_premium_pct']:>13.2f}%"
            f"{(f'{delta:+.2f}%' if delta is not None else 'N/A'):>16}"
            f"{annual['t_statistic']:>10.2f}"
            f"{annual['p_value']:>10.4f}"
        )
        print(row)

    print("-" * 100)
    print("Note: Mean premium is computed from the annual non-overlapping HML series (Q5-Q1).")
    print("=" * 80)


async def main():
    """Main entry point."""
    logger.info("Starting delisting return sensitivity analysis...")
    
    results = await run_scenario_analysis()
    
    # Save results to JSON
    output_path = Path("./publication_tables/delisting_sensitivity.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {output_path}")
    
    # Print table
    print_sensitivity_table(results)


if __name__ == "__main__":
    asyncio.run(main())

