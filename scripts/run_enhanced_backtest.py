"""Run enhanced backtest with full research-grade analysis."""
# Setup path - must be first
import _setup_path  # noqa: F401

from src.backtesting.enhanced_engine import run_enhanced_backtest
from src.backtesting.specs import BacktestSpec
from src.research.report_generator import generate_research_report
import json
from src.logging.logger import get_logger

logger = get_logger(__name__)


def main():
    """Run enhanced backtest and generate report."""
    # Define backtest spec
    spec = BacktestSpec(
        factor_id="RND_v1_combined",
        universe=["pilot_top10"],
        start_year=2020,
        end_year=2023,
        formation_schedule="annual",
        holding_period_years=1,
        num_buckets=10,
    )
    
    logger.info("Running enhanced backtest...")
    results = run_enhanced_backtest(spec)
    
    logger.info("Generating research report...")
    report = generate_research_report(results["backtest_run_id"])
    
    # Save results
    output_file = f"research_report_{results['backtest_run_id']}.json"
    with open(output_file, "w") as f:
        json.dump({
            "results": results,
            "report": report,
        }, f, indent=2, default=str)
    
    logger.info(f"Results saved to {output_file}")
    
    # Print report
    print("\n" + "="*80)
    print(report.get("title", "Research Report"))
    print("="*80)
    print("\n" + report.get("summary", ""))
    print("\n" + report.get("methods", ""))
    print("\n" + report.get("results", ""))
    print("\n" + report.get("limitations", ""))


if __name__ == "__main__":
    main()

