"""
PATH: backend/app/services/rolling_window/_base.py
PURPOSE: Base class for RollingWindowAnalyzer with initialization and core methods
WHY: Foundation methods (init, risk-free rate, eligible companies, quintile assignment)
     that all other mixins depend on
FLOW:
  ┌────────────┐   ┌──────────────────────┐   ┌───────────────┐
  │ DB session │ → │ get_eligible_companies│ → │ assign_quintiles│
  └────────────┘   └──────────────────────┘   └───────────────┘
"""

import uuid
from typing import Dict, List

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FMPIncomeStatement, FMPAnnualReturn, SP500Company, JulyJuneReturn
)
from app.services.return_calculator import JulyJuneReturnCalculator
from app.services.sanity_checks import cap_rd_intensity, MIN_REVENUE_THRESHOLD
from app.core.logging import get_logger

logger = get_logger(__name__)


class RollingWindowBase:
    """
    Base class for RollingWindowAnalyzer with core methods.

    Methodology:
    1. At start of each window, rank companies by R&D intensity (from FY T-1)
    2. Assign to quintiles (Q1=Low R&D, Q5=High R&D)
    3. Calculate forward returns over the window period
    4. Compare quintile performance

    REBALANCING ASSUMPTION:
    This implementation uses ANNUAL EQUAL-WEIGHT REBALANCING, not buy-and-hold.
    Each year within a window, we compute the equal-weighted portfolio return
    (mean of individual company returns), then compound these annual returns.
    This is equivalent to rebalancing to equal weights each year.

    For true buy-and-hold, we would need to track drifting weights based on
    cumulative returns. The annual rebalancing approach is standard in factor
    research (e.g., Fama-French) and helps maintain exposure to the factor.
    """

    WINDOW_LENGTHS = {
        "5yr": 5,
        "10yr": 10,
        "20yr": 20
    }

    def __init__(self, session: AsyncSession, use_july_june: bool = True, data_tier: str = "tier1"):
        """
        Initialize rolling window analyzer.

        Args:
            session: Database session
            use_july_june: If True, use July-June returns (Fama-French convention)
                          to eliminate look-ahead bias. Default is True for
                          research-grade analysis.
            data_tier: 'tier1' (FMP daily) or 'tier2' (CRSP monthly). Default is 'tier1'.
        """
        self.session = session
        self.default_risk_free_rate = 0.02  # 2% fallback if no historical data
        self.use_july_june = use_july_june
        self.data_tier = data_tier
        self._july_june_calculator = None
        self._risk_free_cache = {}  # Cache for historical RF rates
        # Versioning / reproducibility (Dec 2025)
        # A single analyzer instance corresponds to one computation "run".
        self.computation_run_id = str(uuid.uuid4())

    @property
    def july_june_calculator(self) -> JulyJuneReturnCalculator:
        """Lazy initialization of July-June return calculator."""
        if self._july_june_calculator is None:
            self._july_june_calculator = JulyJuneReturnCalculator(self.session)
        return self._july_june_calculator

    async def get_risk_free_rate(self, year: int) -> float:
        """
        Get risk-free rate for a specific year.

        Uses historical data from RiskFreeRate table if available,
        otherwise falls back to default rate.

        Args:
            year: Calendar year

        Returns:
            Annual risk-free rate as decimal (e.g., 0.02 for 2%)
        """
        if year in self._risk_free_cache:
            return self._risk_free_cache[year]

        from app.db.models import RiskFreeRate
        from datetime import date

        # Try to get average RF rate for the year
        result = await self.session.execute(
            select(func.avg(RiskFreeRate.rate_annual_pct))
            .where(
                RiskFreeRate.date >= date(year, 1, 1),
                RiskFreeRate.date <= date(year, 12, 31)
            )
        )
        avg_rate = result.scalar_one_or_none()

        if avg_rate is not None:
            rate = avg_rate / 100  # Convert from percentage to decimal
            self._risk_free_cache[year] = rate
            return rate

        # Fallback to default
        return self.default_risk_free_rate

    async def get_eligible_companies(
        self,
        window_type: str,
        start_year: int,
        end_year: int
    ) -> List[Dict]:
        """
        Get companies with complete data for the specified window.

        Survivorship-Bias-Free: Filters by historical S&P 500 constituents for the start year.
        """
        from app.db.models import SP500HistoricalConstituent
        from datetime import date

        # 1. Determine constituents at start of window (Year T)
        # CRITICAL for survivorship-bias-free research
        # For July–June convention, portfolios are formed on July 1 of start_year.
        # For calendar-year convention, we use Jan 1 of start_year.
        formation_date = date(start_year, 7, 1) if self.use_july_june else date(start_year, 1, 1)
        hist_result = await self.session.execute(
            select(SP500HistoricalConstituent.symbol)
            .where(
                SP500HistoricalConstituent.added_date <= formation_date,
                (SP500HistoricalConstituent.removed_date == None) | (SP500HistoricalConstituent.removed_date >= formation_date)
            )
        )
        constituents = {r[0] for r in hist_result.fetchall()}

        # 2. Get R&D data from formation year (Year T-1)
        formation_year = start_year - 1

        rd_query = select(
                FMPIncomeStatement.symbol,
                FMPIncomeStatement.rd_expenses,
            FMPIncomeStatement.revenue,
            SP500Company.sector
        ).outerjoin(SP500Company, FMPIncomeStatement.symbol == SP500Company.symbol) \
         .where(FMPIncomeStatement.fiscal_year == formation_year) \
         .where(FMPIncomeStatement.period == "FY") \
         .where(FMPIncomeStatement.rd_expenses >= 0) \
            .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)

        if constituents:
            logger.info(f"Filtering by {len(constituents)} point-in-time constituents for {start_year} (formation_date={formation_date})")
            rd_query = rd_query.where(FMPIncomeStatement.symbol.in_(constituents))
        else:
            logger.info(f"No historical constituents found for {start_year}, using all available")

        rd_result = await self.session.execute(rd_query)

        rd_data = {}
        for r in rd_result.fetchall():
            raw_intensity = r.rd_expenses / r.revenue * 100
            capped_intensity = cap_rd_intensity(raw_intensity, sector=r.sector)
            rd_data[r.symbol] = {
                "rd_intensity": capped_intensity,
                "sector": r.sector
            }

        # 3. Get return data for all years in window
        years_needed = list(range(start_year, end_year + 1))
        eligible_companies = []

        for symbol, info in rd_data.items():
            if self.use_july_june:
                # formation_year maps to returns July(formation_year) to June(formation_year+1)
                # For window starting in start_year, first return is for formation_year = start_year-1
                ret_result = await self.session.execute(
                    select(JulyJuneReturn.formation_year, JulyJuneReturn.annualized_return)
                    .where(JulyJuneReturn.symbol == symbol)
                    .where(JulyJuneReturn.formation_year.in_([y - 1 for y in years_needed]))
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
                returns = {r.formation_year + 1: r.annualized_return for r in ret_result.fetchall()}
            else:
                ret_result = await self.session.execute(
                select(FMPAnnualReturn.year, FMPAnnualReturn.annual_return)
                .where(FMPAnnualReturn.symbol == symbol)
                .where(FMPAnnualReturn.year.in_(years_needed))
            )
                returns = {r.year: r.annual_return for r in ret_result.fetchall()}

            # Allow companies that delist during the window (Survivorship handling)
            # If we have at least 1 year of returns, we include it
            if returns:
                avg_return = np.mean([r for r in returns.values() if r is not None])
                eligible_companies.append({
                    "symbol": symbol,
                    "rd_intensity": info["rd_intensity"],
                    "returns": returns,
                    "avg_annual_return": avg_return,
                    "return_type": "july_june" if self.use_july_june else "calendar"
                })

        return eligible_companies

    def assign_quintiles(self, companies: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Assign companies to quintiles based on R&D intensity.

        Q1 = Lowest R&D intensity (bottom 20%)
        Q5 = Highest R&D intensity (top 20%)
        """
        if not companies:
            return {i: [] for i in range(1, 6)}

        # Sort by R&D intensity
        sorted_companies = sorted(companies, key=lambda x: x["rd_intensity"])

        n = len(sorted_companies)
        quintile_size = n // 5

        quintiles = {}
        for q in range(1, 6):
            start_idx = (q - 1) * quintile_size
            if q == 5:
                # Last quintile gets remaining companies
                end_idx = n
            else:
                end_idx = q * quintile_size

            quintiles[q] = sorted_companies[start_idx:end_idx]
            for company in quintiles[q]:
                company["quintile"] = q

        return quintiles
