"""Generate research-grade reports with methods, results, limitations."""
from typing import Dict, List
from datetime import datetime
from src.db.connection import db_session_scope
from src.models.orm.backtest_run import BacktestRun
from src.models.orm.backtest import BacktestResult
from src.models.orm.company_year_core import CompanyYearCore
from src.backtesting.time_segmentation import define_time_segments, segment_backtest_results, calculate_segment_statistics
from src.backtesting.regression_analysis import calculate_factor_loading, calculate_risk_adjusted_returns
from src.backtesting.cross_sectional import analyze_by_industry, compare_factor_performance
from src.backtesting.portfolio_attribution import calculate_factor_correlations
from src.logging.logger import get_logger

logger = get_logger(__name__)


def generate_research_report(backtest_run_id: int) -> Dict[str, str]:
    """Generate comprehensive research report."""
    with db_session_scope() as session:
        run = session.query(BacktestRun).filter_by(id=backtest_run_id).first()
        if not run:
            return {}
        
        results = session.query(BacktestResult).filter_by(backtest_run_id=backtest_run_id).all()
        results_data = [{
            "formation_year": r.formation_year,
            "bucket": r.bucket,
            "mean_ret": r.mean_ret,
            "t_stat": r.t_stat,
            "n": r.n,
            "sharpe_ratio": r.sharpe_ratio,
        } for r in results]
    
    # Methods section
    methods = generate_methods_section(run, results_data)
    
    # Results section
    results_text = generate_results_section(run, results_data)
    
    # Limitations section
    limitations = generate_limitations_section(run, results_data)
    
    # Summary
    summary = generate_summary(run, results_data)
    
    return {
        "title": f"R&D Factor Analysis: {run.factor_id}",
        "summary": summary,
        "methods": methods,
        "results": results_text,
        "limitations": limitations,
        "generated_at": datetime.now().isoformat(),
    }


def generate_methods_section(run: BacktestRun, results: List[Dict]) -> str:
    """Generate methods section."""
    methods = f"""
## Methods

### Factor Definition
The analysis uses the {run.factor_id} factor, which combines:
- R&D intensity (R&D expense / Revenue) from XBRL financial data
- R&D narrative tone score from annual report text analysis using GPT-4

### Data Sources
- **Financial Data**: SEC XBRL CompanyFacts API
- **Text Data**: SEC 10-K annual reports (2020-2023)
- **Price Data**: Historical stock prices for return calculation
- **Universe**: {run.universe} companies

### Portfolio Construction
- **Formation Schedule**: {run.formation_schedule}
- **Holding Period**: {run.holding_period_years} year(s)
- **Bucket Assignment**: Companies ranked by factor value and assigned to deciles
- **Portfolio**: Long-only top decile portfolio with equal weighting

### Return Calculation
Returns calculated as holding period returns using adjusted closing prices:
- Formation date: Fiscal year-end
- Holding period: {run.holding_period_years} year(s)
- Return = (End Price - Start Price) / Start Price

### Statistical Analysis
- Mean returns calculated for each decile
- t-statistics for significance testing
- Sharpe ratios for risk-adjusted performance
- Time-segmented analysis for robustness
"""
    return methods.strip()


def generate_results_section(run: BacktestRun, results: List[Dict]) -> str:
    """Generate results section."""
    if not results:
        return "No results available."
    
    # Aggregate by bucket
    bucket_stats = {}
    for r in results:
        bucket = r.get("bucket", "unknown")
        if bucket not in bucket_stats:
            bucket_stats[bucket] = []
        bucket_stats[bucket].append(r.get("mean_ret", 0))
    
    # Top decile results
    top_decile = [r for r in results if r.get("bucket") == "decile_10"]
    if top_decile:
        mean_return = sum(r.get("mean_ret", 0) for r in top_decile) / len(top_decile)
        avg_t_stat = sum(r.get("t_stat", 0) or 0 for r in top_decile) / len(top_decile)
        avg_sharpe = sum(r.get("sharpe_ratio", 0) or 0 for r in top_decile) / len(top_decile)
    else:
        mean_return = 0
        avg_t_stat = 0
        avg_sharpe = 0
    
    # Time segmentation
    segments = define_time_segments(run.start_year, run.end_year)
    segmented = segment_backtest_results(results, segments)
    segment_stats = calculate_segment_statistics(segmented)
    
    results_text = f"""
## Results

### Overall Performance
The top decile (highest R&D factor) portfolio achieved:
- **Mean Annual Return**: {mean_return:.2%}
- **Average t-statistic**: {avg_t_stat:.2f}
- **Average Sharpe Ratio**: {avg_sharpe:.2f}
- **Number of Formation Periods**: {len(set(r.get('formation_year', 0) for r in results))}

### Time-Segmented Performance
"""
    
    for segment_name, stats in segment_stats.items():
        results_text += f"""
**{segment_name}**:
- Mean Return: {stats['mean_return']:.2%}
- Observations: {stats['n_observations']}
- Min/Max: {stats['min_return']:.2%} / {stats['max_return']:.2%}
"""
    
    results_text += f"""
### Decile Analysis
Performance across deciles shows a {('positive' if mean_return > 0 else 'negative')} relationship between R&D factor and returns.

### Statistical Significance
The t-statistic of {avg_t_stat:.2f} suggests {'statistically significant' if abs(avg_t_stat) > 1.96 else 'not statistically significant'} results at the 5% level.
"""
    
    return results_text.strip()


def generate_limitations_section(run: BacktestRun, results: List[Dict]) -> str:
    """Generate limitations section."""
    limitations = f"""
## Limitations

### Data Limitations
1. **Sample Size**: Analysis limited to {run.universe} companies over {run.start_year}-{run.end_year} period
2. **Coverage**: Not all companies have complete data for all years
3. **Text Extraction**: GPT-based extraction may miss some R&D mentions or misclassify tone

### Methodology Limitations
1. **Look-ahead Bias**: Uses fiscal year-end data, which may not be available at formation date
2. **Survivorship Bias**: Only includes companies with complete data
3. **Transaction Costs**: Returns do not account for trading costs or bid-ask spreads
4. **Rebalancing**: Assumes perfect rebalancing at formation dates

### Factor Limitations
1. **R&D Intensity**: May not capture R&D quality or effectiveness
2. **Tone Score**: Subjective measure that may vary by industry
3. **Combined Factor**: Simple weighted combination may not be optimal

### Time Period Limitations
- Analysis period ({run.start_year}-{run.end_year}) may not be representative of all market conditions
- Results may be influenced by specific market regimes (e.g., COVID-19 pandemic)

### Recommendations for Future Research
1. Expand universe to S&P 500 or Russell 3000
2. Extend time period to 20+ years for robustness
3. Test alternative factor combinations and weighting schemes
4. Include transaction costs and market impact in return calculations
5. Conduct industry-neutral analysis to control for sector effects
"""
    return limitations.strip()


def generate_summary(run: BacktestRun, results: List[Dict]) -> str:
    """Generate executive summary."""
    top_decile = [r for r in results if r.get("bucket") == "decile_10"]
    if top_decile:
        mean_return = sum(r.get("mean_ret", 0) for r in top_decile) / len(top_decile)
    else:
        mean_return = 0
    
    summary = f"""
## Executive Summary

This analysis examines the relationship between R&D factors (intensity and narrative) and stock returns from {run.start_year} to {run.end_year}.

**Key Findings**:
- Top decile R&D factor portfolio achieved {mean_return:.2%} mean annual return
- Analysis covers {len(set(r.get('formation_year', 0) for r in results))} formation periods
- Results {'support' if mean_return > 0 else 'do not support'} the hypothesis that high R&D investment is associated with superior returns

**Methodology**: Equal-weighted long-only portfolios formed annually based on R&D factor rankings.

**Data**: SEC XBRL financial data and 10-K annual report text analysis using GPT-4.
"""
    return summary.strip()

