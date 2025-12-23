# PATH: src/backtesting/publication_grade/portfolio_engine.py
# PURPOSE:
#   - Build portfolio return TIME SERIES (not cross-sectional stats)
#   - Annual rebalancing with proper formation timing
#   - Handle zero vs missing R&D correctly
#
# ROLE IN ARCHITECTURE:
#   - Core computation engine for publication-grade backtests
#
# METHODOLOGY:
#   1. Form portfolios at July 1 each year using FY(t-1) accounting data
#   2. Hold for 12 months (July t to June t+1)
#   3. Compute equal-weighted portfolio return for each quintile
#   4. Build TIME SERIES of quintile returns
#   5. Compute Q5-Q1 factor return series
#
# NOTES FOR FUTURE AI:
#   - All returns in DECIMAL form (0.10 = 10%)
#   - Never average across companies first - build portfolio series
#   - Formation timing follows Fama-French convention

import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from .schemas import (
    FormationPeriod,
    FormationTiming,
    RDTreatment,
    CompanyFactorData,
    PortfolioReturn,
    QuintileTimeSeries,
    FactorPremiumSeries
)

logger = logging.getLogger(__name__)


# Configuration constants
MIN_REVENUE_THRESHOLD = 1_000_000  # $1M minimum revenue
WINSORIZE_PERCENTILE = 0.01       # 1%/99% winsorization


class PortfolioEngine:
    """
    Publication-grade portfolio construction engine.
    
    Key methodological choices:
    1. July formation (Fama-French convention) to avoid look-ahead bias
    2. Include R&D = 0 as valid observation (not the same as missing)
    3. Annual rebalancing (sort EACH year, not once per window)
    4. Equal-weighted portfolios (standard for factor research)
    5. Build time series of portfolio returns (not cross-sectional averages)
    """
    
    def __init__(
        self,
        formation_timing: FormationTiming = FormationTiming.JULY,
        rd_treatment: RDTreatment = RDTreatment.INCLUDE_ZERO,
        num_quintiles: int = 5,
        winsorize: bool = True
    ):
        self.formation_timing = formation_timing
        self.rd_treatment = rd_treatment
        self.num_quintiles = num_quintiles
        self.winsorize = winsorize
    
    def generate_formation_periods(
        self,
        start_year: int,
        end_year: int
    ) -> List[FormationPeriod]:
        """
        Generate formation periods with proper timing.
        
        Example for start_year=2000, end_year=2020:
        - Formation 1: July 1, 2000 using FY1999 data, hold to June 30, 2001
        - Formation 2: July 1, 2001 using FY2000 data, hold to June 30, 2002
        - ...
        - Formation 21: July 1, 2020 using FY2019 data, hold to June 30, 2021
        """
        periods = []
        
        for year in range(start_year, end_year + 1):
            if self.formation_timing == FormationTiming.JULY:
                formation_date = date(year, 7, 1)
                holding_end = date(year + 1, 6, 30)
            elif self.formation_timing == FormationTiming.JUNE_END:
                formation_date = date(year, 6, 30)
                holding_end = date(year + 1, 6, 29)
            else:  # JANUARY (not recommended)
                formation_date = date(year, 1, 1)
                holding_end = date(year, 12, 31)
            
            # Use PRIOR fiscal year's data (FY t-1 for July t formation)
            fiscal_year_used = year - 1
            
            period = FormationPeriod(
                formation_date=formation_date,
                fiscal_year_used=fiscal_year_used,
                holding_start=formation_date,
                holding_end=holding_end
            )
            periods.append(period)
        
        return periods
    
    def get_factor_data_for_period(
        self,
        period: FormationPeriod,
        session  # SQLAlchemy session
    ) -> List[CompanyFactorData]:
        """
        Get R&D intensity data for portfolio formation.
        
        CRITICAL: Uses fiscal_year_used (prior year) to avoid look-ahead bias.
        Only uses filings with filing_date <= formation_date.
        """
        from src.models.orm.company_year_core import CompanyYearCore
        from src.models.orm.financials_core import FinancialsCore
        from src.models.orm.annual_report import AnnualReport
        
        companies_data = []
        
        # Query company years for the fiscal year we're using
        company_years = session.query(CompanyYearCore).filter(
            CompanyYearCore.fiscal_year == period.fiscal_year_used
        ).all()
        
        for cy in company_years:
            company = CompanyFactorData(
                ticker=cy.ticker,
                cik=cy.cik,
                fiscal_year=cy.fiscal_year
            )
            
            # Check filing date (if available) to enforce no look-ahead
            if cy.annual_report:
                report = cy.annual_report
                if hasattr(report, 'filing_date') and report.filing_date:
                    if report.filing_date > period.formation_date:
                        # Filing wasn't available at formation - skip
                        company.is_eligible = False
                        logger.debug(
                            f"Skipping {cy.ticker} FY{cy.fiscal_year}: "
                            f"filed {report.filing_date} > formation {period.formation_date}"
                        )
                        continue
                    company.filing_date = report.filing_date
            
            # Get financials
            if cy.financials_core:
                fc = cy.financials_core
                company.rd_expense = fc.rd_expense
                company.revenue = fc.revenue
                
                # Handle R&D zero vs missing
                if fc.rd_expense is None:
                    company.rd_is_missing = True
                    company.is_eligible = (self.rd_treatment != RDTreatment.EXCLUDE_ZERO)
                elif fc.rd_expense == 0:
                    company.rd_is_zero = True
                    company.rd_intensity = 0.0
                    # Zero R&D is valid if we include it
                    company.is_eligible = (self.rd_treatment == RDTreatment.INCLUDE_ZERO)
                elif fc.revenue and fc.revenue >= MIN_REVENUE_THRESHOLD:
                    company.rd_intensity = fc.rd_expense / fc.revenue
                    company.is_eligible = True
                else:
                    # Revenue too low or missing
                    company.is_eligible = False
            else:
                company.is_eligible = False
            
            companies_data.append(company)
        
        # Filter to eligible only
        eligible = [c for c in companies_data if c.is_eligible and c.rd_intensity is not None]
        
        # Winsorize if configured
        if self.winsorize and eligible:
            intensities = [c.rd_intensity for c in eligible]
            lower = np.percentile(intensities, WINSORIZE_PERCENTILE * 100)
            upper = np.percentile(intensities, (1 - WINSORIZE_PERCENTILE) * 100)
            
            for c in eligible:
                c.rd_intensity_winsorized = min(max(c.rd_intensity, lower), upper)
        else:
            for c in eligible:
                c.rd_intensity_winsorized = c.rd_intensity
        
        return eligible
    
    def assign_quintiles(
        self,
        companies: List[CompanyFactorData]
    ) -> Dict[int, List[CompanyFactorData]]:
        """
        Assign companies to quintiles based on R&D intensity.
        
        Q1 = Lowest R&D intensity (bottom 20%)
        Q5 = Highest R&D intensity (top 20%)
        
        Uses winsorized values if available.
        """
        if not companies:
            return {q: [] for q in range(1, self.num_quintiles + 1)}
        
        # Sort by factor value (winsorized if available)
        def get_intensity(c):
            return c.rd_intensity_winsorized if c.rd_intensity_winsorized is not None else c.rd_intensity
        
        sorted_companies = sorted(companies, key=get_intensity)
        
        n = len(sorted_companies)
        quintile_size = n // self.num_quintiles
        
        quintiles = {q: [] for q in range(1, self.num_quintiles + 1)}
        
        for i, company in enumerate(sorted_companies):
            # Determine quintile (1-indexed)
            q = min(i // quintile_size + 1, self.num_quintiles)
            quintiles[q].append(company)
        
        return quintiles
    
    def calculate_portfolio_return(
        self,
        tickers: List[str],
        period: FormationPeriod,
        session  # SQLAlchemy session
    ) -> Tuple[float, int]:
        """
        Calculate equal-weighted portfolio return for holding period.
        
        Returns:
            (portfolio_return, n_stocks_with_valid_returns)
        """
        from src.models.orm.price import Price
        
        returns = []
        
        for ticker in tickers:
            # Get price at start of holding period
            start_price_record = session.query(Price).filter(
                Price.ticker == ticker,
                Price.date >= period.holding_start,
                Price.date <= period.holding_start + timedelta(days=7)  # Allow 1 week
            ).order_by(Price.date).first()
            
            # Get price at end of holding period  
            end_price_record = session.query(Price).filter(
                Price.ticker == ticker,
                Price.date <= period.holding_end,
                Price.date >= period.holding_end - timedelta(days=7)
            ).order_by(Price.date.desc()).first()
            
            if start_price_record and end_price_record:
                start_price = start_price_record.adj_close
                end_price = end_price_record.adj_close
                
                if start_price and start_price > 0 and end_price:
                    ret = (end_price - start_price) / start_price
                    returns.append(ret)
        
        if not returns:
            return 0.0, 0
        
        # Equal-weighted portfolio return
        portfolio_return = sum(returns) / len(returns)
        
        return portfolio_return, len(returns)
    
    def build_quintile_time_series(
        self,
        start_year: int,
        end_year: int,
        session  # SQLAlchemy session
    ) -> Dict[int, QuintileTimeSeries]:
        """
        Build complete time series of quintile portfolio returns.
        
        This is the CORE function that produces publication-grade results.
        
        For each formation period:
        1. Get factor data using PRIOR year accounting
        2. Assign to quintiles
        3. Calculate equal-weighted portfolio return over holding period
        4. Store in time series
        
        The result is a TIME SERIES of portfolio returns (not cross-sectional averages).
        """
        logger.info(f"Building quintile time series for {start_year}-{end_year}")
        
        # Initialize time series for each quintile
        quintile_returns = {q: [] for q in range(1, self.num_quintiles + 1)}
        
        # Generate formation periods
        periods = self.generate_formation_periods(start_year, end_year)
        
        for period in periods:
            logger.info(f"Processing formation period: {period.formation_date}")
            
            # Get factor data for this formation
            companies = self.get_factor_data_for_period(period, session)
            
            if len(companies) < 25:  # Need at least 5 per quintile
                logger.warning(f"Insufficient companies ({len(companies)}) for {period.formation_date}")
                continue
            
            # Assign to quintiles
            quintiles = self.assign_quintiles(companies)
            
            # Calculate portfolio return for each quintile
            for q in range(1, self.num_quintiles + 1):
                q_companies = quintiles[q]
                
                if not q_companies:
                    continue
                
                tickers = [c.ticker for c in q_companies]
                
                # Calculate portfolio return over holding period
                portfolio_ret, n_valid = self.calculate_portfolio_return(
                    tickers, period, session
                )
                
                if n_valid >= 3:  # Need at least 3 stocks with returns
                    avg_factor = np.mean([
                        c.rd_intensity_winsorized or c.rd_intensity 
                        for c in q_companies
                    ])
                    
                    portfolio_return = PortfolioReturn(
                        period_start=period.holding_start,
                        period_end=period.holding_end,
                        quintile=q,
                        return_ew=portfolio_ret,
                        n_stocks=n_valid,
                        tickers=tickers[:10],  # Store sample
                        avg_factor_value=avg_factor
                    )
                    
                    quintile_returns[q].append(portfolio_return)
        
        # Convert to QuintileTimeSeries objects
        result = {}
        for q in range(1, self.num_quintiles + 1):
            result[q] = QuintileTimeSeries(
                quintile=q,
                returns=quintile_returns[q]
            )
            logger.info(
                f"Q{q}: {result[q].n_periods} periods, "
                f"mean return {result[q].mean_return()*100:.2f}%"
            )
        
        return result
    
    def build_factor_premium_series(
        self,
        quintile_series: Dict[int, QuintileTimeSeries]
    ) -> FactorPremiumSeries:
        """
        Build Q5 - Q1 factor return series.
        
        This is the "R&D factor" that we can:
        1. Test for significance (with HAC errors)
        2. Regress against FF factors to get alpha
        """
        q5 = quintile_series[5]
        q1 = quintile_series[1]
        
        # Align periods (only use periods where both Q5 and Q1 have returns)
        q5_by_period = {r.period_start: r.return_ew for r in q5.returns}
        q1_by_period = {r.period_start: r.return_ew for r in q1.returns}
        
        common_periods = sorted(set(q5_by_period.keys()) & set(q1_by_period.keys()))
        
        premiums = []
        q5_returns = []
        q1_returns = []
        
        for period in common_periods:
            q5_ret = q5_by_period[period]
            q1_ret = q1_by_period[period]
            
            premiums.append(q5_ret - q1_ret)
            q5_returns.append(q5_ret)
            q1_returns.append(q1_ret)
        
        return FactorPremiumSeries(
            periods=common_periods,
            premiums=premiums,
            q5_returns=q5_returns,
            q1_returns=q1_returns
        )


# Import at end to avoid circular imports
from datetime import timedelta

