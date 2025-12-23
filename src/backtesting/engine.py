"""Main backtesting engine."""
import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime
from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_ratios import FinancialsRatios
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.price import Price
from src.models.orm.backtest_run import BacktestRun
from src.models.orm.backtest import BacktestResult
from src.backtesting.specs import BacktestSpec
from src.backtesting.portfolio_construction import assign_buckets, build_long_short_portfolio, build_long_only_portfolio
from src.backtesting.statistics import calculate_portfolio_return, calculate_statistics
from src.ingestion.universe_builder import get_pilot_companies
from src.logging.logger import get_logger

logger = get_logger(__name__)


def get_factor_values(
    factor_id: str,
    formation_year: int,
    universe: List[str]
) -> Dict[str, float]:
    """Get factor values for a given year and universe."""
    factor_values = {}
    
    with db_session_scope() as session:
        # Get company years for the formation year
        company_years = session.query(CompanyYearCore).filter_by(
            fiscal_year=formation_year
        ).all()
        
        for cy in company_years:
            if cy.ticker not in universe:
                continue
            
            if factor_id == "RND_v1_numeric":
                # Use R&D intensity from ratios
                if cy.financials_ratios and cy.financials_ratios.rd_intensity:
                    factor_values[cy.ticker] = cy.financials_ratios.rd_intensity
            
            elif factor_id == "RND_v1_text":
                # Use R&D tone score from text factors
                if cy.text_factor_rd and cy.text_factor_rd.rd_tone_score is not None:
                    factor_values[cy.ticker] = cy.text_factor_rd.rd_tone_score
            
            elif factor_id == "RND_v1_combined":
                # Combine numeric and text
                numeric_val = 0.0
                text_val = 0.0
                
                if cy.financials_ratios and cy.financials_ratios.rd_intensity:
                    numeric_val = cy.financials_ratios.rd_intensity
                
                if cy.text_factor_rd and cy.text_factor_rd.rd_tone_score is not None:
                    text_val = cy.text_factor_rd.rd_tone_score
                
                # Simple combination (can be improved)
                if numeric_val > 0 or text_val != 0:
                    factor_values[cy.ticker] = numeric_val * 0.6 + (text_val + 1) * 0.4  # Normalize text to 0-2
    
    return factor_values


def get_prices(
    tickers: List[str],
    start_date: datetime,
    end_date: datetime
) -> Dict[str, List[float]]:
    """Get price data for tickers over date range."""
    prices = {}
    
    with db_session_scope() as session:
        for ticker in tickers:
            price_records = session.query(Price).filter(
                Price.ticker == ticker,
                Price.date >= start_date,
                Price.date <= end_date
            ).order_by(Price.date).all()
            
            if price_records:
                prices[ticker] = [p.adj_close for p in price_records if p.adj_close]
    
    return prices


def run_backtest(spec: BacktestSpec) -> BacktestRun:
    """Run a backtest and store results."""
    logger.info(f"Running backtest: {spec.factor_id} from {spec.start_year} to {spec.end_year}")
    
    # Get universe
    if spec.universe == ["pilot_top10"]:
        universe = [c["ticker"] for c in get_pilot_companies()]
    else:
        universe = spec.universe
    
    # Create spec hash
    spec_dict = spec.to_dict()
    spec_hash = hashlib.sha256(json.dumps(spec_dict, sort_keys=True).encode()).hexdigest()[:16]
    
    # Check if already run
    with db_session_scope() as session:
        existing = session.query(BacktestRun).filter_by(spec_hash=spec_hash).first()
        if existing:
            logger.info(f"Backtest already exists: {spec_hash}")
            return existing
        
        # Create backtest run
        backtest_run = BacktestRun(
            spec_hash=spec_hash,
            factor_id=spec.factor_id,
            universe=",".join(universe),
            start_year=spec.start_year,
            end_year=spec.end_year,
            formation_schedule=spec.formation_schedule,
            holding_period_years=spec.holding_period_years,
            spec_json=spec_dict,
            status="running",
            started_at=datetime.now(),
        )
        session.add(backtest_run)
        session.commit()
        run_id = backtest_run.id
    
    # Run backtest for each formation year
    results = []
    
    for formation_year in range(spec.start_year, spec.end_year + 1):
        logger.info(f"Processing formation year: {formation_year}")
        
        # Get factor values
        factor_values = get_factor_values(spec.factor_id, formation_year, universe)
        
        if not factor_values:
            logger.warning(f"No factor values for {formation_year}")
            continue
        
        # Assign buckets
        buckets = assign_buckets(factor_values, spec.num_buckets)
        
        # Calculate returns for each bucket
        for bucket_num in range(spec.num_buckets):
            bucket_tickers = [t for t, b in buckets.items() if b == bucket_num]
            
            if not bucket_tickers:
                continue
            
            # Get prices (simplified - would need proper date handling)
            # For now, use a simple return calculation
            bucket_returns = []
            
            with db_session_scope() as session:
                for ticker in bucket_tickers:
                    # Get next year's company year for return calculation
                    next_year = session.query(CompanyYearCore).filter_by(
                        ticker=ticker,
                        fiscal_year=formation_year + spec.holding_period_years
                    ).first()
                    
                    if next_year and next_year.financials_core:
                        # Simple return proxy (would use actual prices in production)
                        # For now, use revenue growth as proxy
                        current_year = session.query(CompanyYearCore).filter_by(
                            ticker=ticker,
                            fiscal_year=formation_year
                        ).first()
                        
                        if current_year and current_year.financials_core and next_year.financials_core.revenue:
                            if current_year.financials_core.revenue and current_year.financials_core.revenue > 0:
                                ret = (next_year.financials_core.revenue - current_year.financials_core.revenue) / current_year.financials_core.revenue
                                bucket_returns.append(ret)
            
            if bucket_returns:
                stats = calculate_statistics(bucket_returns)
                
                # Store result
                with db_session_scope() as session:
                    result = BacktestResult(
                        backtest_run_id=run_id,
                        spec_hash=spec_hash,
                        formation_year=formation_year,
                        horizon_years=spec.holding_period_years,
                        bucket=f"decile_{bucket_num + 1}",
                        mean_ret=stats["mean"],
                        t_stat=stats.get("t_stat"),
                        n=stats["n"],
                        stderr=stats.get("stderr"),
                        sharpe_ratio=stats.get("sharpe"),
                    )
                    session.add(result)
                    session.commit()
                
                results.append(result)
    
    # Update backtest run status
    with db_session_scope() as session:
        backtest_run = session.query(BacktestRun).filter_by(id=run_id).first()
        if backtest_run:
            backtest_run.status = "completed"
            backtest_run.completed_at = datetime.now()
            session.commit()
    
    logger.info(f"Backtest completed: {len(results)} results")
    return backtest_run

