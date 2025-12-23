# PATH: src/backtesting/publication_grade/run_backtest.py
# PURPOSE:
#   - Run complete publication-grade backtest
#   - Generate all statistics with proper inference
#   - Export results for paper auto-generation
#
# ROLE IN ARCHITECTURE:
#   - Entry point for publication-grade analysis
#
# USAGE:
#   python -m src.backtesting.publication_grade.run_backtest --start-year 2000 --end-year 2023

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.db.connection import db_session_scope
from src.logging.logger import get_logger

from .schemas import (
    FormationTiming,
    RDTreatment,
    BacktestOutput
)
from .portfolio_engine import PortfolioEngine
from .inference import NeweyWestInference
from .factor_returns import FactorReturnSeries

logger = get_logger(__name__)


def run_publication_grade_backtest(
    start_year: int = 2000,
    end_year: int = 2023,
    formation_timing: FormationTiming = FormationTiming.JULY,
    rd_treatment: RDTreatment = RDTreatment.INCLUDE_ZERO,
    output_dir: str = "results"
) -> BacktestOutput:
    """
    Run complete publication-grade backtest.
    
    This function:
    1. Builds portfolio return TIME SERIES (not cross-sectional averages)
    2. Uses proper formation timing (July convention)
    3. Includes R&D = 0 as valid observation
    4. Computes statistics with HAC (Newey-West) standard errors
    5. Generates factor premium series for regression
    6. Exports all results for paper auto-generation
    
    Args:
        start_year: First formation year
        end_year: Last formation year
        formation_timing: When to form portfolios each year
        rd_treatment: How to handle zero vs missing R&D
        output_dir: Directory for output files
        
    Returns:
        BacktestOutput with all results
    """
    logger.info("=" * 80)
    logger.info("PUBLICATION-GRADE BACKTEST")
    logger.info("=" * 80)
    logger.info(f"Period: {start_year} - {end_year}")
    logger.info(f"Formation timing: {formation_timing.value}")
    logger.info(f"R&D treatment: {rd_treatment.value}")
    
    # Initialize components
    engine = PortfolioEngine(
        formation_timing=formation_timing,
        rd_treatment=rd_treatment,
        num_quintiles=5,
        winsorize=True
    )
    
    inference = NeweyWestInference(risk_free_rate=0.02)  # 2% RF rate
    
    # Build quintile time series
    logger.info("\n1. Building quintile portfolio time series...")
    
    with db_session_scope() as session:
        quintile_series = engine.build_quintile_time_series(
            start_year=start_year,
            end_year=end_year,
            session=session
        )
    
    # Compute inference for each quintile
    logger.info("\n2. Computing inference with Newey-West HAC errors...")
    
    quintile_inference = {}
    for q in range(1, 6):
        if quintile_series[q].n_periods > 0:
            inf = inference.compute_quintile_inference(quintile_series[q])
            quintile_inference[q] = inf
            logger.info(
                f"Q{q}: mean={inf.mean_return*100:.2f}%, "
                f"t={inf.t_statistic:.2f}, p={inf.p_value:.4f}, "
                f"n={inf.n_observations}, lags={inf.n_lags_used}"
            )
    
    # Build factor premium series (Q5 - Q1)
    logger.info("\n3. Building R&D factor premium series...")
    
    factor_premium = engine.build_factor_premium_series(quintile_series)
    premium_inference = inference.compute_premium_inference(factor_premium)
    
    logger.info(
        f"R&D Premium: mean={premium_inference.mean_return*100:.2f}%, "
        f"t={premium_inference.t_statistic:.2f}, p={premium_inference.p_value:.4f}"
    )
    
    # Factor regression (if we have data)
    logger.info("\n4. Factor regression analysis...")
    
    factor_analysis = FactorReturnSeries(factor_premium)
    factor_regression = factor_analysis.run_factor_regression(use_hac=True)
    
    # Build output
    run_timestamp = datetime.now().isoformat()
    
    output = BacktestOutput(
        run_timestamp=run_timestamp,
        data_version="1.0",
        formation_timing=formation_timing,
        rd_treatment=rd_treatment,
        rebalance_frequency="annual",
        quintile_series=quintile_series,
        factor_premium_series=factor_premium,
        quintile_inference=quintile_inference,
        premium_inference=premium_inference,
        factor_regression=factor_regression
    )
    
    # Export results
    logger.info("\n5. Exporting results...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Paper numbers (for auto-generation)
    paper_numbers = output.to_paper_numbers()
    numbers_file = output_path / f"paper_numbers_{run_timestamp[:10]}.json"
    with open(numbers_file, "w") as f:
        json.dump(paper_numbers, f, indent=2)
    logger.info(f"Paper numbers saved to: {numbers_file}")
    
    # Full results
    results_file = output_path / f"backtest_results_{run_timestamp[:10]}.json"
    
    # Serialize (convert dataclasses to dicts)
    results_dict = {
        "metadata": {
            "run_timestamp": run_timestamp,
            "data_version": output.data_version,
            "formation_timing": formation_timing.value,
            "rd_treatment": rd_treatment.value,
            "start_year": start_year,
            "end_year": end_year,
        },
        "quintile_summary": {
            q: {
                "n_periods": qs.n_periods,
                "mean_return": qs.mean_return(),
                "geometric_mean": qs.geometric_mean_return(),
                "volatility": qs.volatility(),
            }
            for q, qs in quintile_series.items()
        },
        "inference": {
            q: {
                "mean_return": inf.mean_return,
                "t_statistic": inf.t_statistic,
                "p_value": inf.p_value,
                "standard_error": inf.standard_error,
                "n_lags": inf.n_lags_used,
            }
            for q, inf in quintile_inference.items()
        },
        "factor_premium": {
            "mean": premium_inference.mean_return,
            "t_statistic": premium_inference.t_statistic,
            "p_value": premium_inference.p_value,
            "sharpe": premium_inference.sharpe_ratio,
        },
        "factor_regression": factor_regression,
    }
    
    with open(results_file, "w") as f:
        json.dump(results_dict, f, indent=2, default=str)
    logger.info(f"Full results saved to: {results_file}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY (for paper)")
    logger.info("=" * 80)
    for key, value in paper_numbers.items():
        logger.info(f"  {key}: {value}")
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Run publication-grade R&D backtest")
    parser.add_argument("--start-year", type=int, default=2000, help="First formation year")
    parser.add_argument("--end-year", type=int, default=2023, help="Last formation year")
    parser.add_argument(
        "--formation", 
        choices=["july", "june_end", "january"],
        default="july",
        help="Portfolio formation timing"
    )
    parser.add_argument(
        "--rd-treatment",
        choices=["include_zero", "exclude_zero", "separate_bucket"],
        default="include_zero",
        help="How to handle zero R&D"
    )
    parser.add_argument("--output-dir", default="results", help="Output directory")
    
    args = parser.parse_args()
    
    # Map string args to enums
    formation_map = {
        "july": FormationTiming.JULY,
        "june_end": FormationTiming.JUNE_END,
        "january": FormationTiming.JANUARY,
    }
    
    rd_map = {
        "include_zero": RDTreatment.INCLUDE_ZERO,
        "exclude_zero": RDTreatment.EXCLUDE_ZERO,
        "separate_bucket": RDTreatment.SEPARATE_BUCKET,
    }
    
    run_publication_grade_backtest(
        start_year=args.start_year,
        end_year=args.end_year,
        formation_timing=formation_map[args.formation],
        rd_treatment=rd_map[args.rd_treatment],
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()

