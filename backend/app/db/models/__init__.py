"""
PATH: backend/app/db/models/__init__.py
PURPOSE: Re-export ALL model classes for backward compatibility.
WHY: Every existing `from app.db.models import X` must continue to work unchanged.
"""

# --- Company domain ---
from app.db.models.company import Company, CompanyYearCore, AnnualReport

# --- Financial domain ---
from app.db.models.financial import FinancialsCore, FinancialsRatios, TextFactorRD, Price

# --- FMP vendor data ---
from app.db.models.fmp import (
    SP500Company,
    FMPIncomeStatement,
    FMPBalanceSheet,
    FMPCashFlow,
    FMPDailyPrice,
    FMPDividend,
    FMPAnnualReturn,
)

# --- Research analysis ---
from app.db.models.research import (
    ResearchCohort,
    RollingWindowResult,
    AnovaResult,
    FactorPremium,
    ComputationRun,
    PublicationSnapshot,
)

# --- ETF & market forecasts ---
from app.db.models.etf import ETFSelectionHistory, MarketForecast

# --- Research metrics ---
from app.db.models.metrics import (
    JulyJuneReturn,
    MomentumCache,
    VolatilityCache,
    RiskFreeRate,
    SP500HistoricalConstituent,
    DelistingReturn,
    FamaFrenchFactor,
)

# --- Tier-2 CRSP/Compustat stubs ---
from app.db.models.tier2 import (
    CRSPMonthlyStock,
    CRSPCompustatLink,
    CompustatAnnual,
    CRSPS500Constituent,
)

__all__ = [
    # Company
    "Company",
    "CompanyYearCore",
    "AnnualReport",
    # Financial
    "FinancialsCore",
    "FinancialsRatios",
    "TextFactorRD",
    "Price",
    # FMP
    "SP500Company",
    "FMPIncomeStatement",
    "FMPBalanceSheet",
    "FMPCashFlow",
    "FMPDailyPrice",
    "FMPDividend",
    "FMPAnnualReturn",
    # Research
    "ResearchCohort",
    "RollingWindowResult",
    "AnovaResult",
    "FactorPremium",
    "ComputationRun",
    "PublicationSnapshot",
    # ETF
    "ETFSelectionHistory",
    "MarketForecast",
    # Metrics
    "JulyJuneReturn",
    "MomentumCache",
    "VolatilityCache",
    "RiskFreeRate",
    "SP500HistoricalConstituent",
    "DelistingReturn",
    "FamaFrenchFactor",
    # Tier 2
    "CRSPMonthlyStock",
    "CRSPCompustatLink",
    "CompustatAnnual",
    "CRSPS500Constituent",
]
