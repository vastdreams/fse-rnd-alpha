from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"

    ticker = Column(String, unique=True, index=True, nullable=False)
    cik = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    country = Column(String, default="US", nullable=True)
    
    # Relationships
    company_years = relationship("CompanyYearCore", back_populates="company")
