"""
PATH: scripts/reproduce_all_tables.py
PURPOSE:
  - End-to-end reproducibility script for all research tables
  - Validates computed results against canonical values
  - Generates publication-ready output

ROLE IN ARCHITECTURE:
  - Reproducibility layer for academic standards
  - Can be run independently to verify all results

USAGE:
  python scripts/reproduce_all_tables.py [--output-dir ./tables]
"""

import asyncio
import argparse
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Database connection
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# ==============================================================================
# Configuration
# ==============================================================================

CANONICAL_VALUES = {
    "5yr": {"premium": 7.11, "eta_squared": 0.225, "cohens_d": 0.894},
    "10yr": {"premium": 4.78, "eta_squared": 0.319, "cohens_d": 1.132},
    "20yr": {"premium": 2.62, "eta_squared": 0.458, "cohens_d": 1.446},
}

TOLERANCE = 0.01  # 1% tolerance for validation


# ==============================================================================
# Table Generation Functions
# ==============================================================================

async def generate_table_1_quintile_performance(session) -> Dict:
    """
    Table 1: Quintile Portfolio Performance by Horizon
    
    Columns: Quintile, Avg R&D%, Mean Return (5yr/10yr/20yr), Sharpe Ratio
    """
    from app.services.rolling_window import RollingWindowAnalyzer
    
    analyzer = RollingWindowAnalyzer(session)
    
    results = {}
    for window_type in ["5yr", "10yr", "20yr"]:
        windows = await analyzer.get_stored_window_results(window_type)
        
        # Aggregate across all windows
        quintile_data = {i: {"returns": [], "rd_intensity": []} for i in range(1, 6)}
        
        for w in windows:
            for q in w.get("quintiles", []):
                quintile = q["quintile"]
                if q.get("avg_return"):
                    quintile_data[quintile]["returns"].append(q["avg_return"])
                if q.get("avg_rd_intensity"):
                    quintile_data[quintile]["rd_intensity"].append(q["avg_rd_intensity"])
        
        results[window_type] = {
            f"Q{i}": {
                "mean_return": sum(quintile_data[i]["returns"]) / len(quintile_data[i]["returns"]) if quintile_data[i]["returns"] else 0,
                "avg_rd_intensity": sum(quintile_data[i]["rd_intensity"]) / len(quintile_data[i]["rd_intensity"]) if quintile_data[i]["rd_intensity"] else 0,
            }
            for i in range(1, 6)
        }
    
    return {"table_1_quintile_performance": results}


async def generate_table_2_anova(session) -> Dict:
    """
    Table 2: ANOVA Results
    
    Columns: Horizon, F-statistic, p-value, eta-squared, omega-squared
    """
    from app.services.statistics import StatisticalAnalyzer
    
    analyzer = StatisticalAnalyzer(session)
    
    results = {}
    for window_type in ["5yr", "10yr", "20yr"]:
        anova = await analyzer.compute_aggregate_anova(window_type)
        if "anova" in anova:
            results[window_type] = {
                "f_statistic": anova["anova"].get("f_statistic"),
                "p_value": anova["anova"].get("p_value"),
                "eta_squared": anova["anova"].get("eta_squared"),
                "omega_squared": anova["anova"].get("omega_squared"),
            }
    
    return {"table_2_anova": results}


async def generate_table_3_ttest(session) -> Dict:
    """
    Table 3: T-Test Results (Q5 vs Q1)
    
    Columns: Horizon, Mean Diff, t-stat, p-value, Cohen's d
    """
    from app.services.statistics import StatisticalAnalyzer
    
    analyzer = StatisticalAnalyzer(session)
    
    results = {}
    for window_type in ["5yr", "10yr", "20yr"]:
        anova = await analyzer.compute_aggregate_anova(window_type)
        if "ttest_high_vs_low" in anova:
            ttest = anova["ttest_high_vs_low"]
            results[window_type] = {
                "mean_difference": ttest.get("mean_difference"),
                "t_statistic": ttest.get("t_statistic"),
                "p_value": ttest.get("p_value"),
                "cohens_d": ttest.get("cohens_d"),
            }
    
    return {"table_3_ttest": results}


async def generate_table_4_annual_hml(session) -> Dict:
    """
    Table 4: Annual HML Premium Series (Non-Overlapping)
    
    Preferred approach for inference
    """
    from app.services.statistics import StatisticalAnalyzer
    
    analyzer = StatisticalAnalyzer(session)
    result = await analyzer.compute_annual_hml_premium()
    
    return {"table_4_annual_hml": result}


async def generate_table_5_sector_breakdown(session) -> Dict:
    """
    Table 5: Sector Distribution by Quintile
    """
    from sqlalchemy import select, func
    from app.db.models import ResearchCohort
    
    result = await session.execute(
        select(
            ResearchCohort.sector,
            func.count().label("n_companies"),
            func.avg(ResearchCohort.avg_rd_intensity).label("avg_rd")
        )
        .where(ResearchCohort.sector.isnot(None))
        .group_by(ResearchCohort.sector)
        .order_by(func.avg(ResearchCohort.avg_rd_intensity).desc())
    )
    
    sectors = [
        {"sector": r[0], "n_companies": r[1], "avg_rd_intensity": float(r[2] or 0)}
        for r in result.fetchall()
    ]
    
    return {"table_5_sector_breakdown": sectors}


def validate_results(results: Dict) -> Dict[str, bool]:
    """
    Validate computed results against canonical values.
    """
    validations = {}
    
    if "table_3_ttest" in results:
        for horizon, canonical in CANONICAL_VALUES.items():
            if horizon in results["table_3_ttest"]:
                computed = results["table_3_ttest"][horizon]
                if computed.get("mean_difference"):
                    diff = abs(computed["mean_difference"] - canonical["premium"])
                    validations[f"{horizon}_premium"] = diff <= TOLERANCE * canonical["premium"]
    
    return validations


# ==============================================================================
# Main Execution
# ==============================================================================

async def main(output_dir: Path):
    """Generate all tables and save to output directory."""
    
    # Database connection (publication reproducibility):
    # - Uses the same DATABASE_URL/.env config as the FastAPI backend.
    DATABASE_URL = settings.async_database_url
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_session() as session:
        all_results = {}
        
        print("Generating Table 1: Quintile Performance...")
        all_results.update(await generate_table_1_quintile_performance(session))
        
        print("Generating Table 2: ANOVA Results...")
        all_results.update(await generate_table_2_anova(session))
        
        print("Generating Table 3: T-Test Results...")
        all_results.update(await generate_table_3_ttest(session))
        
        print("Generating Table 4: Annual HML Premium...")
        all_results.update(await generate_table_4_annual_hml(session))
        
        print("Generating Table 5: Sector Breakdown...")
        all_results.update(await generate_table_5_sector_breakdown(session))
        
        # Validate
        print("\nValidating results against canonical values...")
        validations = validate_results(all_results)
        all_results["_validations"] = validations
        all_results["_generated_at"] = datetime.utcnow().isoformat()
        
        # Save JSON
        json_path = output_dir / "all_tables.json"
        with open(json_path, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"Saved: {json_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        for key, passed in validations.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{key}: {status}")
        
        return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate reproducibility tables")
    parser.add_argument("--output-dir", type=Path, default=Path("./tables"))
    args = parser.parse_args()
    
    asyncio.run(main(args.output_dir))

