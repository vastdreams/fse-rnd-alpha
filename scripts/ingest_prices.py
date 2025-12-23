"""Ingest price data using yfinance."""
# Setup path - must be first
import _setup_path  # noqa: F401

import yfinance as yf
from datetime import datetime, timedelta
from src.ingestion.universe_builder import get_pilot_companies
from src.db.connection import db_session_scope
from src.models.orm.price import Price
from src.logging.logger import get_logger

logger = get_logger(__name__)


def ingest_prices():
    """Ingest price data for all pilot companies."""
    companies = get_pilot_companies()
    logger.info(f"Ingesting prices for {len(companies)} companies")
    
    # Get last 5 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    
    with db_session_scope() as session:
        for company_data in companies:
            ticker = company_data["ticker"]
            logger.info(f"Fetching prices for {ticker}")
            
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                
                for date, row in hist.iterrows():
                    # Check if already exists
                    existing = session.query(Price).filter_by(
                        ticker=ticker,
                        date=date.date()
                    ).first()
                    
                    if existing:
                        continue
                    
                    price = Price(
                        ticker=ticker,
                        date=date.date(),
                        adj_close=float(row["Close"]),
                        volume=float(row["Volume"]) if "Volume" in row else None,
                        frequency="daily",
                    )
                    session.add(price)
                
                session.commit()
                logger.info(f"Stored prices for {ticker}: {len(hist)} records")
                
            except Exception as e:
                logger.error(f"Error fetching prices for {ticker}: {e}")
                continue


if __name__ == "__main__":
    ingest_prices()

