"""Cross-sectional analysis by industry, market cap, etc."""
from typing import List, Dict
import pandas as pd
from src.db.connection import db_session_scope
from src.models.orm.company_year_core import CompanyYearCore
from src.logging.logger import get_logger

logger = get_logger(__name__)


def analyze_by_industry(
    results: List[Dict],
    formation_year: int
) -> Dict[str, Dict]:
    """Analyze backtest results by industry."""
    with db_session_scope() as session:
        # Get industry for each company
        company_years = session.query(CompanyYearCore).filter_by(
            fiscal_year=formation_year
        ).all()
        
        industry_map = {cy.ticker: cy.industry for cy in company_years if cy.industry}
    
    # Group results by industry
    industry_results = {}
    
    for result in results:
        # Extract ticker from result (would need to store this in results)
        # For now, aggregate by bucket
        bucket = result.get("bucket", "unknown")
        industry = "Unknown"
        
        if bucket not in industry_results:
            industry_results[bucket] = {}
        
        if industry not in industry_results[bucket]:
            industry_results[bucket][industry] = []
        
        industry_results[bucket][industry].append(result.get("mean_ret", 0))
    
    # Calculate statistics by industry
    industry_stats = {}
    for bucket, industries in industry_results.items():
        industry_stats[bucket] = {}
        for industry, returns in industries.items():
            if returns:
                industry_stats[bucket][industry] = {
                    "mean": sum(returns) / len(returns),
                    "n": len(returns),
                    "std": pd.Series(returns).std() if len(returns) > 1 else 0,
                }
    
    return industry_stats


def analyze_by_market_cap(
    results: List[Dict],
    formation_year: int
) -> Dict[str, Dict]:
    """Analyze backtest results by market cap (simplified)."""
    # Would need market cap data - for now return placeholder
    return {
        "large_cap": {"mean": 0.0, "n": 0},
        "mid_cap": {"mean": 0.0, "n": 0},
        "small_cap": {"mean": 0.0, "n": 0},
    }


def compare_factor_performance(
    factor_results: Dict[str, List[Dict]]
) -> pd.DataFrame:
    """Compare performance across different factors."""
    comparison = []
    
    for factor_name, results in factor_results.items():
        if results:
            returns = [r.get("mean_ret", 0) for r in results]
            comparison.append({
                "factor": factor_name,
                "mean_return": sum(returns) / len(returns) if returns else 0,
                "std": pd.Series(returns).std() if len(returns) > 1 else 0,
                "n": len(returns),
            })
    
    return pd.DataFrame(comparison)

