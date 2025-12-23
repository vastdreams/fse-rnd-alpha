"""Enhanced backtesting engine with time segmentation and advanced statistics."""
from typing import Dict, List
from datetime import datetime
from src.backtesting.engine import run_backtest, get_factor_values, get_prices
from src.backtesting.specs import BacktestSpec
from src.backtesting.time_segmentation import define_time_segments, segment_backtest_results, calculate_segment_statistics
from src.backtesting.regression_analysis import calculate_factor_loading, calculate_risk_adjusted_returns
from src.backtesting.returns_calculator import calculate_holding_period_return, calculate_portfolio_returns, calculate_portfolio_total_return
from src.backtesting.cross_sectional import analyze_by_industry, compare_factor_performance
from src.backtesting.portfolio_attribution import calculate_portfolio_exposures, calculate_factor_correlations
from src.backtesting.portfolio_construction import assign_buckets, build_long_only_portfolio
from src.db.connection import db_session_scope
from src.models.orm.backtest_run import BacktestRun
from src.logging.logger import get_logger

logger = get_logger(__name__)


def run_enhanced_backtest(spec: BacktestSpec) -> Dict:
    """Run enhanced backtest with time segmentation and advanced analysis."""
    logger.info(f"Running enhanced backtest: {spec.factor_id}")
    
    # Run base backtest
    backtest_run = run_backtest(spec)
    
    # Get results
    with db_session_scope() as session:
        results = session.query(BacktestResult).filter_by(
            backtest_run_id=backtest_run.id
        ).all()
        
        results_data = [{
            "formation_year": r.formation_year,
            "bucket": r.bucket,
            "mean_ret": r.mean_ret,
            "t_stat": r.t_stat,
            "n": r.n,
            "sharpe_ratio": r.sharpe_ratio,
        } for r in results]
    
    # Time segmentation
    segments = define_time_segments(spec.start_year, spec.end_year)
    segmented = segment_backtest_results(results_data, segments)
    segment_stats = calculate_segment_statistics(segmented)
    
    # Regression analysis (for top decile)
    top_decile_results = [r for r in results_data if r.get("bucket") == "decile_10"]
    
    # Factor correlations
    if spec.universe == ["pilot_top10"]:
        from src.ingestion.universe_builder import get_pilot_companies
        universe = [c["ticker"] for c in get_pilot_companies()]
    else:
        universe = spec.universe
    
    # Get factor values and returns for regression
    factor_values_list = []
    returns_list = []
    
    for formation_year in range(spec.start_year, spec.end_year + 1):
        factor_values = get_factor_values(spec.factor_id, formation_year, universe)
        if factor_values:
            # Get average return for top decile companies
            buckets = assign_buckets(factor_values, spec.num_buckets)
            top_tickers = [t for t, b in buckets.items() if b == 9]
            
            if top_tickers:
                # Calculate returns
                formation_date = datetime(formation_year, 12, 31)
                portfolio_returns = calculate_portfolio_returns(
                    {t: 1.0/len(top_tickers) for t in top_tickers},
                    formation_date,
                    spec.holding_period_years * 12
                )
                
                avg_return = sum(portfolio_returns.values()) / len(portfolio_returns) if portfolio_returns else 0
                avg_factor = sum(factor_values.get(t, 0) for t in top_tickers) / len(top_tickers)
                
                if avg_return != 0 and avg_factor != 0:
                    factor_values_list.append(avg_factor)
                    returns_list.append(avg_return)
    
    # Regression
    regression_results = {}
    if len(factor_values_list) > 1 and len(returns_list) > 1:
        regression_results = calculate_factor_loading(factor_values_list, returns_list)
    
    # Risk-adjusted returns
    risk_adj = calculate_risk_adjusted_returns(returns_list) if returns_list else {}
    
    # Cross-sectional analysis
    industry_stats = {}
    for formation_year in range(spec.start_year, spec.end_year + 1):
        year_results = [r for r in results_data if r.get("formation_year") == formation_year]
        if year_results:
            industry_stats[formation_year] = analyze_by_industry(year_results, formation_year)
    
    # Portfolio exposures
    portfolio_exposures = {}
    for formation_year in range(spec.start_year, spec.end_year + 1):
        factor_values = get_factor_values(spec.factor_id, formation_year, universe)
        if factor_values:
            buckets = assign_buckets(factor_values, spec.num_buckets)
            portfolio = build_long_only_portfolio(buckets, target_bucket=9)
            if portfolio:
                exposures = calculate_portfolio_exposures(portfolio, formation_year)
                portfolio_exposures[formation_year] = exposures
    
    # Factor correlations
    correlations = calculate_factor_correlations(spec.start_year, universe)
    
    return {
        "backtest_run_id": backtest_run.id,
        "base_results": results_data,
        "time_segments": {
            "segments": segments,
            "segmented_results": segmented,
            "segment_statistics": segment_stats,
        },
        "regression": regression_results,
        "risk_adjusted": risk_adj,
        "industry_analysis": industry_stats,
        "portfolio_exposures": portfolio_exposures,
        "factor_correlations": correlations.to_dict() if not correlations.empty else {},
    }

