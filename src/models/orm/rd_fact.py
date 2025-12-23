from sqlalchemy import Column, String, Integer, Float
from .base_model import BaseModel


class RDFact(BaseModel):
    __tablename__ = "rd_facts"

    ticker = Column(String, index=True, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    rd_expense = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
