"""Proper price-based return calculations."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from src.db.connection import db_session_scope
from src.models.orm.price import Price
from src.logging.logger import get_logger

logger = get_logger(__name__)


def calculate_holding_period_return(
    ticker: str,
    formation_date: datetime,
    holding_period_months: int = 12
) -> Optional[float]:
    """Calculate holding period return using actual prices."""
    with db_session_scope() as session:
        # Get price at formation
        formation_price = session.query(Price).filter(
            Price.ticker == ticker,
            Price.date >= formation_date,
        ).order_by(Price.date).first()
        
        if not formation_price or not formation_price.adj_close:
            return None
        
        # Get price at end of holding period
        end_date = formation_date + timedelta(days=holding_period_months * 30)
        end_price = session.query(Price).filter(
            Price.ticker == ticker,
            Price.date <= end_date,
        ).order_by(Price.date.desc()).first()
        
        if not end_price or not end_price.adj_close:
            return None
        
        # Calculate return
        start_price = formation_price.adj_close
        end_price_val = end_price.adj_close
        
        if start_price > 0:
            return (end_price_val - start_price) / start_price
        
    return None


def calculate_portfolio_returns(
    portfolio: Dict[str, float],
    formation_date: datetime,
    holding_period_months: int = 12
) -> Dict[str, float]:
    """Calculate returns for all tickers in portfolio."""
    returns = {}
    
    for ticker, weight in portfolio.items():
        ret = calculate_holding_period_return(ticker, formation_date, holding_period_months)
        if ret is not None:
            returns[ticker] = ret
    
    return returns


def calculate_portfolio_total_return(
    portfolio: Dict[str, float],
    returns: Dict[str, float]
) -> float:
    """Calculate weighted portfolio return."""
    total_return = 0.0
    
    for ticker, weight in portfolio.items():
        if ticker in returns:
            total_return += weight * returns[ticker]
    
    return total_return


def get_price_series(
    ticker: str,
    start_date: datetime,
    end_date: datetime
) -> pd.Series:
    """Get price time series for a ticker."""
    with db_session_scope() as session:
        prices = session.query(Price).filter(
            Price.ticker == ticker,
            Price.date >= start_date,
            Price.date <= end_date,
        ).order_by(Price.date).all()
        
        if prices:
            return pd.Series(
                [p.adj_close for p in prices],
                index=[p.date for p in prices]
            )
    
    return pd.Series()


def calculate_cumulative_returns(
    returns: Dict[str, float],
    rebalance_dates: List[datetime]
) -> pd.Series:
    """Calculate cumulative returns over time."""
    cumulative = pd.Series([1.0], index=[rebalance_dates[0] if rebalance_dates else datetime.now()])
    
    for i, date in enumerate(rebalance_dates[1:], 1):
        if i <= len(returns):
            prev_value = cumulative.iloc[-1]
            period_return = list(returns.values())[i-1] if i-1 < len(returns) else 0
            cumulative.loc[date] = prev_value * (1 + period_return)
    
    return cumulative

