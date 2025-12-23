# PATH: src/models/orm/financials_core.py
# PURPOSE:
#   - ORM model for core financial statement data
#   - Income statement, balance sheet, and cash flow items
#
# ROLE IN ARCHITECTURE:
#   - Data layer model, linked to CompanyYearCore
#
# NOTES FOR FUTURE AI:
#   - rd_expense can be NULL (not reported) or 0 (explicitly zero)
#   - Treat these differently: NULL = missing, 0 = valid observation
#   - All monetary values in USD

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.models.orm.base_model import BaseModel


class FinancialsCore(BaseModel):
    """
    Core financial statement data.
    
    IMPORTANT: R&D expense handling:
    - rd_expense = NULL: Not reported in filings (missing data)
    - rd_expense = 0: Explicitly reported as zero (valid observation)
    - rd_is_estimated: True if value was imputed/estimated
    
    For publication-grade research, these must be treated differently:
    - Missing: exclude from analysis or impute
    - Zero: include in lowest quintile
    """
    __tablename__ = "financials_core"
    
    company_year_id = Column(Integer, ForeignKey("company_year_core.id"), nullable=False, unique=True)
    
    # Income Statement
    revenue = Column(Float)
    cost_of_revenue = Column(Float)
    gross_profit = Column(Float)
    
    # R&D with proper handling
    rd_expense = Column(Float)  # NULL = missing, 0 = zero
    rd_is_estimated = Column(Boolean, default=False)  # True if imputed
    rd_source = Column(String)  # "10k_line_item", "notes", "estimated"
    
    sga_expense = Column(Float)
    operating_income = Column(Float)
    ebit = Column(Float)
    interest_expense = Column(Float)
    pretax_income = Column(Float)
    income_tax = Column(Float)
    net_income = Column(Float)
    eps_basic = Column(Float)
    eps_diluted = Column(Float)
    
    # Balance Sheet
    total_assets = Column(Float)
    current_assets = Column(Float)
    cash_and_equivalents = Column(Float)
    accounts_receivable = Column(Float)
    inventory = Column(Float)
    property_plant_equipment = Column(Float)
    goodwill = Column(Float)
    intangible_assets = Column(Float)
    total_liabilities = Column(Float)
    current_liabilities = Column(Float)
    accounts_payable = Column(Float)
    short_term_debt = Column(Float)
    long_term_debt = Column(Float)
    total_debt = Column(Float)
    shareholders_equity = Column(Float)
    retained_earnings = Column(Float)
    
    # Cash Flow
    operating_cash_flow = Column(Float)
    capital_expenditures = Column(Float)
    investing_cash_flow = Column(Float)
    financing_cash_flow = Column(Float)
    dividends_paid = Column(Float)
    stock_repurchased = Column(Float)
    free_cash_flow = Column(Float)
    
    # Relationship
    company_year = relationship("CompanyYearCore", back_populates="financials_core")
    
    @property
    def rd_intensity(self) -> float:
        """
        Calculate R&D intensity (R&D / Revenue).
        
        Returns:
            R&D intensity as decimal (0.10 = 10%), or None if not calculable.
        """
        if self.rd_expense is None:
            return None  # Missing data
        if self.revenue is None or self.revenue <= 0:
            return None  # Can't calculate
        return self.rd_expense / self.revenue
    
    @property
    def rd_is_missing(self) -> bool:
        """Check if R&D data is missing (not reported)."""
        return self.rd_expense is None
    
    @property
    def rd_is_zero(self) -> bool:
        """Check if R&D is explicitly zero."""
        return self.rd_expense is not None and self.rd_expense == 0
