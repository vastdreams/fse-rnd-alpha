from sqlalchemy import Column, String, Date, Float, Index
from .base_model import BaseModel


class Price(BaseModel):
    """Daily and monthly price data."""
    __tablename__ = "prices"

    ticker = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    adj_close = Column(Float, nullable=True)
    tri = Column(Float, nullable=True)  # Total Return Index
    volume = Column(Float, nullable=True)
    frequency = Column(String, default="daily", nullable=True)  # daily, monthly
    
    __table_args__ = (
        Index("idx_ticker_date", "ticker", "date"),
        {"comment": "Price and total return index data"}
    )
