"""
PATH: backend/app/services/rolling_window.py
PURPOSE:
  - Analyze R&D-return relationships across rolling windows
  - Build quintile portfolios based on R&D intensity
  - Compute forward returns for each quintile
  
METHODOLOGY NOTE:
  - Uses FY(T-1) data to form portfolios at start of year T
  - R&D intensity capped at 100% (200% for biotech/healthcare) to prevent outliers
  - Minimum revenue filter ($100M) to exclude pre-revenue companies
  - Zero-R&D companies included in Q1 (lowest R&D intensity)
  
LOOK-AHEAD BIAS CONSIDERATIONS:
  - Fiscal year-end data (FY T-1) is not available until the 10-K filing
  - Most 10-K filings occur within 60-90 days after fiscal year-end
  - For calendar-year companies, FY 2009 data is filed by March 2010
  - CALENDAR year returns (Jan-Dec) can have slight look-ahead bias when using FY(T-1) data
    because FY(T-1) is not fully public on Jan 1 of year T for many firms.
  - This service defaults to July-June returns (Fama-French convention) via `JulyJuneReturn`
    when `use_july_june=True` (default). This is the publication-grade, bias-minimized path.

KNOWN LIMITATIONS:
  1. Survivorship bias: Uses current S&P 500 constituents (unless historical data loaded)
  2. Filing date timing: ~3 month lag not perfectly handled with annual data
  3. Overlapping windows: Rolling windows are not independent observations
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid
from dataclasses import dataclass
import numpy as np
from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FMPIncomeStatement, FMPAnnualReturn, ResearchCohort,
    RollingWindowResult, FactorPremium, SP500Company,
    JulyJuneReturn
)
from app.services.return_calculator import JulyJuneReturnCalculator
from app.services.delisting_utils import delisting_key_year, bounds_for_return_year
from app.services.sanity_checks import (
    cap_rd_intensity,
    MIN_REVENUE_THRESHOLD,
    MAX_RD_INTENSITY_ABSOLUTE,
    HIGH_RD_SECTORS
)
from app.core.logging import get_logger
from app.core.formulas import validate_formula_output

logger = get_logger(__name__)


@dataclass
class QuintileResult:
    """Result for a single quintile in a window."""
    quintile: int
    n_companies: int
    symbols: List[str]
    avg_rd_intensity: float
    median_rd_intensity: float
    avg_return: float
    median_return: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float  # Maximum drawdown in percent (e.g., -25.0 means -25%)


class RollingWindowAnalyzer:
    """
    Analyze R&D-return relationships across rolling windows.
    
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
    
    async def calculate_quintile_stats(
        self, 
        quintile: int,
        companies: List[Dict],
        window_length: int,
        window_years: List[int]
    ) -> QuintileResult:
        """
        Calculate statistics for a quintile using PROPER TIME-SERIES methodology.
        
        Survivorship Correction:
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        - Uses time-varying risk-free rate from database.
        """
        if not companies:
            return QuintileResult(
                quintile=quintile,
                n_companies=0,
                symbols=[],
                avg_rd_intensity=0,
                median_rd_intensity=0,
                avg_return=0,
                median_return=0,
                total_return=0,
                annualized_return=0,
                volatility=0,
                sharpe_ratio=0
            )
        
        symbols = [c["symbol"] for c in companies]
        rd_intensities = [c["rd_intensity"] for c in companies]
        
        def safe_float(val):
            """Convert NaN/Inf to 0."""
            if val is None or np.isnan(val) or np.isinf(val):
                return 0.0
            return float(val)
        
        # Calculate equal-weighted portfolio return for each year in window
        portfolio_returns = []
        
        for year in window_years:
            year_returns = []
            rf_rate = await self.get_risk_free_rate(year)
            
            for c in companies:
                symbol = c["symbol"]
                
                # Normal return
                if "returns" in c and year in c["returns"]:
                    ret = c["returns"][year]
                    if ret is not None and not np.isnan(ret):
                        year_returns.append(ret)
            
            if year_returns:
                portfolio_returns.append(np.mean(year_returns))
            else:
                # Fallback to RF if no companies left (unlikely)
                portfolio_returns.append(rf_rate)
        
        if not portfolio_returns:
            return QuintileResult(
                quintile=quintile, n_companies=len(companies), symbols=symbols,
                avg_rd_intensity=safe_float(np.mean(rd_intensities)),
                median_rd_intensity=safe_float(np.median(rd_intensities)),
                avg_return=0, median_return=0, total_return=0, annualized_return=0,
                volatility=0, sharpe_ratio=0, max_drawdown=0
            )
            
        # Time-series statistics
        mean_return = float(np.mean(portfolio_returns))
        
        compound_product = 1.0
        for r in portfolio_returns:
            compound_product *= (1 + r)
        total_return = compound_product - 1
        
        n_periods = len(portfolio_returns)
        annualized_return = (compound_product ** (1 / n_periods) - 1) if n_periods > 0 else 0
        
        volatility = float(np.std(portfolio_returns, ddof=1)) if len(portfolio_returns) > 1 else 0
        
        # Sharpe ratio with time-varying RF
        avg_rf = np.mean([await self.get_risk_free_rate(y) for y in window_years])
        excess_return = annualized_return - avg_rf
        sharpe = excess_return / volatility if volatility > 0 else 0
        
        # Max drawdown calculation
        cumulative = np.cumprod([1 + r for r in portfolio_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else 0.0
        
        return QuintileResult(
            quintile=quintile,
            n_companies=len(companies),
            symbols=symbols,
            avg_rd_intensity=safe_float(np.mean(rd_intensities)),
            median_rd_intensity=safe_float(np.median(rd_intensities)),
            avg_return=mean_return * 100,
            median_return=safe_float(np.median(portfolio_returns)) * 100,
            total_return=total_return * 100,
            annualized_return=annualized_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown * 100  # Store as percent
        )
    
    async def compute_quintile_returns(
        self,
        window_type: str,
        start_year: int,
        end_year: int
    ) -> List[QuintileResult]:
        """
        Compute quintile returns for a specific window.
        """
        window_length = self.WINDOW_LENGTHS.get(window_type, 5)
        window_years = list(range(start_year, end_year + 1))
        
        # Get eligible companies
        companies = await self.get_eligible_companies(window_type, start_year, end_year)
        
        if len(companies) < 10:
            logger.warning(f"Insufficient companies for {window_type} window {start_year}-{end_year}: {len(companies)}")
            return []
        
        # Assign to quintiles
        quintiles = self.assign_quintiles(companies)
        
        # Calculate stats for each quintile (ASYNCHRONOUSLY)
        results = []
        for q in range(1, 6):
            stats = await self.calculate_quintile_stats(q, quintiles[q], window_length, window_years)
            results.append(stats)
        
        return results
    
    async def compute_all_rolling_windows(
        self,
        window_type: str,
        save_results: bool = True
    ) -> List[Dict]:
        """
        Generate all possible rolling windows for a given type.
        
        - 5yr: 1995-2000, 1996-2001, ... 2020-2025
        - 10yr: 1995-2005, 1996-2006, ... 2015-2025
        - 20yr: 1995-2015, 1996-2016, ... 2005-2025
        """
        window_length = self.WINDOW_LENGTHS.get(window_type, 5)
        
        # Determine available year range from data
        year_result = await self.session.execute(
            select(
                func.min(FMPIncomeStatement.fiscal_year),
                func.max(FMPIncomeStatement.fiscal_year)
            )
        )
        min_year, max_year = year_result.fetchone()
        
        if not min_year or not max_year:
            return []
        
        # Generate all windows
        all_results = []

        # Versioning metadata for stored results (Dec 2025)
        return_convention = "july_june" if self.use_july_june else "calendar"

        # Preload existing rows so recomputation is idempotent and does not duplicate rows.
        existing_by_key: Dict[Tuple[int, int, int], RollingWindowResult] = {}
        if save_results:
            existing_result = await self.session.execute(
                select(RollingWindowResult)
                .where(
                    RollingWindowResult.window_type == window_type,
                    RollingWindowResult.return_convention == return_convention,
                    RollingWindowResult.data_tier == self.data_tier,
                )
            )
            for row in existing_result.scalars().all():
                existing_by_key[(row.start_year, row.end_year, row.quintile)] = row
        
        for start_year in range(min_year, max_year - window_length + 2):
            end_year = start_year + window_length - 1
            
            if end_year > max_year:
                break
            
            logger.info(f"Computing {window_type} window: {start_year}-{end_year}")
            
            quintile_results = await self.compute_quintile_returns(
                window_type, start_year, end_year
            )
            
            if not quintile_results:
                continue
            
            window_result = {
                "window_type": window_type,
                "start_year": start_year,
                "end_year": end_year,
                "quintiles": [
                    {
                        "quintile": r.quintile,
                        "n_companies": r.n_companies,
                        "avg_rd_intensity": round(r.avg_rd_intensity, 2),
                        "avg_return": round(r.avg_return, 2),
                        "total_return": round(r.total_return, 2),
                        "volatility": round(r.volatility, 2),
                        "sharpe_ratio": round(r.sharpe_ratio, 3)
                    }
                    for r in quintile_results
                ],
                "rd_premium": round(quintile_results[4].avg_return - quintile_results[0].avg_return, 2)
                    if len(quintile_results) == 5 else 0
            }
            
            all_results.append(window_result)
            
            # Save to database
            if save_results:
                for r in quintile_results:
                    natural_key = (start_year, end_year, r.quintile)
                    existing = existing_by_key.get(natural_key)

                    if existing:
                        # Update existing row (idempotent recomputation)
                        existing.return_convention = return_convention
                        existing.data_tier = self.data_tier
                        existing.computation_run_id = self.computation_run_id

                        existing.n_companies = r.n_companies
                        existing.avg_rd_intensity = r.avg_rd_intensity
                        existing.median_rd_intensity = r.median_rd_intensity
                        existing.avg_return = r.avg_return
                        existing.median_return = r.median_return
                        existing.total_return = r.total_return
                        existing.annualized_return = r.annualized_return
                        existing.volatility = r.volatility
                        existing.sharpe_ratio = r.sharpe_ratio
                        existing.max_drawdown = r.max_drawdown
                    else:
                        db_result = RollingWindowResult(
                            window_type=window_type,
                            start_year=start_year,
                            end_year=end_year,
                            quintile=r.quintile,
                            # Versioning metadata (Dec 2025)
                            return_convention=return_convention,
                            data_tier=self.data_tier,
                            computation_run_id=self.computation_run_id,
                            # Portfolio statistics
                            n_companies=r.n_companies,
                            avg_rd_intensity=r.avg_rd_intensity,
                            median_rd_intensity=r.median_rd_intensity,
                            avg_return=r.avg_return,
                            median_return=r.median_return,
                            total_return=r.total_return,
                            annualized_return=r.annualized_return,
                            volatility=r.volatility,
                            sharpe_ratio=r.sharpe_ratio,
                            max_drawdown=r.max_drawdown,
                        )
                        self.session.add(db_result)
                        existing_by_key[natural_key] = db_result
        
        if save_results:
            await self.session.commit()
        
        return all_results
    
    async def compute_annual_factor_premiums(
        self,
        save_results: bool = True
    ) -> List[Dict]:
        """
        Compute R&D factor premium for each year.
        
        Premium = Q5 (High R&D) return - Q1 (Low R&D) return
        
        PUBLICATION FIX (Dec 2025):
        - Uses July-June returns (controlled by self.use_july_june)
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        """
        from app.db.models import SP500HistoricalConstituent
        from sqlalchemy import or_
        from datetime import date
        
        # Get year range
        return_convention = "july_june" if self.use_july_june else "calendar"

        existing_premiums_by_year: Dict[int, FactorPremium] = {}
        if save_results:
            existing_premiums_result = await self.session.execute(
                select(FactorPremium)
                .where(
                    FactorPremium.return_convention == return_convention,
                    FactorPremium.data_tier == self.data_tier,
                )
            )
            for row in existing_premiums_result.scalars().all():
                existing_premiums_by_year[row.year] = row

        if self.use_july_june:
            year_result = await self.session.execute(
                select(
                    func.min(JulyJuneReturn.formation_year),
                    func.max(JulyJuneReturn.formation_year),
                )
                .where(JulyJuneReturn.data_tier == self.data_tier)
            )
        else:
            year_result = await self.session.execute(
                select(
                    func.min(FMPAnnualReturn.year),
                    func.max(FMPAnnualReturn.year),
                )
            )
        min_year, max_year = year_result.fetchone()
        
        if not min_year or not max_year:
            return []
        
        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        all_premiums = []
        
        # For July-June: formation_year is the FY data year
        # Returns are July(formation_year+1) to June(formation_year+2)
        for formation_year in range(min_year, max_year + 1):
            return_year = formation_year + 1  # For labeling purposes
            
            # Get R&D intensities from formation year
            if self.use_july_june and membership_available:
                formation_date = date(int(return_year), 7, 1)
                rd_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.rd_expenses,
                        FMPIncomeStatement.revenue
                    )
                    .join(SP500HistoricalConstituent, SP500HistoricalConstituent.symbol == FMPIncomeStatement.symbol)
                    .where(
                        SP500HistoricalConstituent.added_date <= formation_date,
                        or_(
                            SP500HistoricalConstituent.removed_date == None,
                            SP500HistoricalConstituent.removed_date >= formation_date,
                        ),
                    )
                    .where(FMPIncomeStatement.fiscal_year == formation_year)
                    .where(FMPIncomeStatement.period == "FY")
                    .where(FMPIncomeStatement.rd_expenses >= 0)
                    .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
                )
            else:
                rd_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.rd_expenses,
                        FMPIncomeStatement.revenue
                    )
                    .where(FMPIncomeStatement.fiscal_year == formation_year)
                    .where(FMPIncomeStatement.period == "FY")
                    .where(FMPIncomeStatement.rd_expenses >= 0)
                    .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
                )
            rd_data = {
                r.symbol: r.rd_expenses / r.revenue * 100
                for r in rd_result.fetchall()
            }
            
            # Get returns (July-June or calendar)
            if self.use_july_june:
                return_result = await self.session.execute(
                    select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                    .where(JulyJuneReturn.formation_year == formation_year)
                    .where(JulyJuneReturn.annualized_return.isnot(None))
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
                returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
            else:
                return_result = await self.session.execute(
                    select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                    .where(FMPAnnualReturn.year == return_year)
                    .where(FMPAnnualReturn.annual_return.isnot(None))
                )
                returns = {r.symbol: r.annual_return for r in return_result.fetchall()}
            
            # Combine and assign quintiles
            combined = []
            for s, rd in rd_data.items():
                if s in returns and returns[s] is not None:
                    ret = returns[s]
                else:
                    continue  # No return data
                
                combined.append({"symbol": s, "rd_intensity": rd, "return": ret})
            
            if len(combined) < 25:
                continue
            
            # Sort and assign quintiles
            sorted_companies = sorted(combined, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5
            
            quintile_returns = {i: [] for i in range(1, 6)}
            quintile_ns = {i: 0 for i in range(1, 6)}
            
            for i, c in enumerate(sorted_companies):
                q = min(5, i // quintile_size + 1)
                quintile_returns[q].append(c["return"])
                quintile_ns[q] += 1
            
            q_means = {q: np.mean(rets) if rets else 0 for q, rets in quintile_returns.items()}
            
            rd_premium = q_means[5] - q_means[1]
            
            premium_data = {
                "year": return_year,
                "formation_year": formation_year,
                "rd_premium": round(rd_premium * 100, 2),  # Convert to percentage
                "q1_return": round(q_means[1] * 100, 2),
                "q2_return": round(q_means[2] * 100, 2),
                "q3_return": round(q_means[3] * 100, 2),
                "q4_return": round(q_means[4] * 100, 2),
                "q5_return": round(q_means[5] * 100, 2),
                "q1_n": quintile_ns[1],
                "q2_n": quintile_ns[2],
                "q3_n": quintile_ns[3],
                "q4_n": quintile_ns[4],
                "q5_n": quintile_ns[5],
                "return_type": "july_june" if self.use_july_june else "calendar"
            }
            
            all_premiums.append(premium_data)
            
            if save_results:
                existing = existing_premiums_by_year.get(return_year)
                if existing:
                    existing.return_convention = return_convention
                    existing.data_tier = self.data_tier

                    existing.rd_premium = rd_premium * 100
                    existing.q1_return = q_means[1] * 100
                    existing.q2_return = q_means[2] * 100
                    existing.q3_return = q_means[3] * 100
                    existing.q4_return = q_means[4] * 100
                    existing.q5_return = q_means[5] * 100

                    existing.q1_n = quintile_ns[1]
                    existing.q2_n = quintile_ns[2]
                    existing.q3_n = quintile_ns[3]
                    existing.q4_n = quintile_ns[4]
                    existing.q5_n = quintile_ns[5]
                else:
                    db_premium = FactorPremium(
                        year=return_year,
                        return_convention=return_convention,
                        data_tier=self.data_tier,
                        rd_premium=rd_premium * 100,  # Store as percentage
                        q1_return=q_means[1] * 100,
                        q2_return=q_means[2] * 100,
                        q3_return=q_means[3] * 100,
                        q4_return=q_means[4] * 100,
                        q5_return=q_means[5] * 100,
                        q1_n=quintile_ns[1],
                        q2_n=quintile_ns[2],
                        q3_n=quintile_ns[3],
                        q4_n=quintile_ns[4],
                        q5_n=quintile_ns[5],
                    )
                    self.session.add(db_premium)
                    existing_premiums_by_year[return_year] = db_premium
        
        if save_results:
            await self.session.commit()
        
        logger.info(f"Computed factor premiums for {len(all_premiums)} years (use_july_june={self.use_july_june})")
        
        return all_premiums
    
    async def get_stored_window_results(
        self,
        window_type: str
    ) -> List[Dict]:
        """Get pre-computed window results from database."""
        return_convention = "july_june" if self.use_july_june else "calendar"

        result = await self.session.execute(
            select(RollingWindowResult)
            .where(
                RollingWindowResult.window_type == window_type,
                RollingWindowResult.return_convention == return_convention,
                RollingWindowResult.data_tier == self.data_tier,
            )
            .order_by(RollingWindowResult.start_year, RollingWindowResult.quintile)
        )
        rows = result.scalars().all()
        
        # Group by window
        windows = {}
        for r in rows:
            key = (r.start_year, r.end_year)
            if key not in windows:
                windows[key] = {
                    "window_type": r.window_type,
                    "start_year": r.start_year,
                    "end_year": r.end_year,
                    "quintiles": []
                }
            windows[key]["quintiles"].append({
                "quintile": r.quintile,
                "n_companies": r.n_companies,
                "avg_rd_intensity": r.avg_rd_intensity,
                "median_rd_intensity": r.median_rd_intensity,
                "avg_return": r.avg_return,
                "median_return": r.median_return,
                "total_return": r.total_return,
                "annualized_return": r.annualized_return,
                "volatility": r.volatility,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
            })
        
        # Calculate premium for each window
        results = []
        for key, window in sorted(windows.items()):
            quintiles = window["quintiles"]
            q1 = next((q for q in quintiles if q["quintile"] == 1), None)
            q5 = next((q for q in quintiles if q["quintile"] == 5), None)
            window["rd_premium"] = round((q5["avg_return"] or 0) - (q1["avg_return"] or 0), 2) if q1 and q5 else 0
            results.append(window)
        
        return results

    async def aggregate_windows(self, window_type: str) -> List[Dict]:
        """
        Aggregate pre-computed rolling-window results across all windows for a given horizon.
        
        This is a convenience method used by multiple API endpoints (e.g., export tables and
        net-of-cost analysis). It **does not recompute** windows; it summarizes stored results
        from `RollingWindowResult`.
        
        Returns:
            List[Dict] with one row per quintile containing average metrics across windows.
        """
        windows = await self.get_stored_window_results(window_type)
        if not windows:
            return []
        
        # Collect per-quintile metrics across windows
        per_q: Dict[int, Dict[str, List[float]]] = {
            q: {
                "n_companies": [],
                "avg_rd_intensity": [],
                "median_rd_intensity": [],
                "avg_return": [],
                "median_return": [],
                "total_return": [],
                "annualized_return": [],
                "volatility": [],
                "sharpe_ratio": [],
                "max_drawdown": [],
            }
            for q in range(1, 6)
        }
        
        for w in windows:
            for q in w.get("quintiles", []):
                qn = int(q.get("quintile", 0) or 0)
                if qn not in per_q:
                    continue
                
                # Note: stored values are already in *percent units* for returns/volatility/intensity.
                per_q[qn]["n_companies"].append(float(q.get("n_companies") or 0))
                if q.get("avg_rd_intensity") is not None:
                    per_q[qn]["avg_rd_intensity"].append(float(q["avg_rd_intensity"]))
                if q.get("median_rd_intensity") is not None:
                    per_q[qn]["median_rd_intensity"].append(float(q["median_rd_intensity"]))
                if q.get("avg_return") is not None:
                    per_q[qn]["avg_return"].append(float(q["avg_return"]))
                if q.get("median_return") is not None:
                    per_q[qn]["median_return"].append(float(q["median_return"]))
                if q.get("total_return") is not None:
                    per_q[qn]["total_return"].append(float(q["total_return"]))
                if q.get("annualized_return") is not None:
                    per_q[qn]["annualized_return"].append(float(q["annualized_return"]))
                if q.get("volatility") is not None:
                    per_q[qn]["volatility"].append(float(q["volatility"]))
                if q.get("sharpe_ratio") is not None:
                    per_q[qn]["sharpe_ratio"].append(float(q["sharpe_ratio"]))
                if q.get("max_drawdown") is not None:
                    per_q[qn]["max_drawdown"].append(float(q["max_drawdown"]))
        
        def mean_or_none(vals: List[float]) -> float | None:
            return float(np.mean(vals)) if vals else None
        
        n_windows = len(windows)
        aggregated: List[Dict] = []
        for qn in range(1, 6):
            aggregated.append({
                "quintile": qn,
                "label": f"Q{qn}",
                "n_windows": n_windows,
                "n_companies": int(round(mean_or_none(per_q[qn]["n_companies"]) or 0)),
                "avg_rd_intensity": mean_or_none(per_q[qn]["avg_rd_intensity"]),
                "median_rd_intensity": mean_or_none(per_q[qn]["median_rd_intensity"]),
                "avg_return": mean_or_none(per_q[qn]["avg_return"]),
                "median_return": mean_or_none(per_q[qn]["median_return"]),
                "total_return": mean_or_none(per_q[qn]["total_return"]),
                "annualized_return": mean_or_none(per_q[qn]["annualized_return"]),
                "volatility": mean_or_none(per_q[qn]["volatility"]),
                "sharpe_ratio": mean_or_none(per_q[qn]["sharpe_ratio"]),
                "max_drawdown": mean_or_none(per_q[qn]["max_drawdown"]),
            })
        
        return aggregated
    
    def calculate_weighted_return(
        self,
        companies: List[Dict],
        weighting: str = "equal"
    ) -> float:
        """
        Calculate portfolio return with specified weighting scheme.
        
        Args:
            companies: List of dicts with 'return' and optionally 'market_cap' keys
            weighting: 'equal' or 'value' (market cap weighted)
            
        Returns:
            Weighted portfolio return
        """
        if not companies:
            return 0.0
        
        returns = [c.get("return", 0) or 0 for c in companies]
        
        if weighting == "value":
            market_caps = [c.get("market_cap", 1) or 1 for c in companies]
            total_cap = sum(market_caps)
            if total_cap > 0:
                weights = [cap / total_cap for cap in market_caps]
                return float(np.average(returns, weights=weights))
        
        # Default: equal weight
        return float(np.mean(returns))
    
    async def compute_sector_neutral_premium(
        self,
        year: int
    ) -> Dict:
        """
        Compute sector-neutral R&D premium.
        
        Within each sector:
        1. Form quintiles based on R&D intensity
        2. Compute Q5 - Q1 premium
        3. Average across sectors (equal-weighted)
        
        This controls for sector effects and isolates firm-level R&D premium.
        
        PUBLICATION FIX (Dec 2025):
        - Uses July-June returns (controlled by self.use_july_june)
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        
        Args:
            year: Year for which to compute premium (return year for calendar, formation_year+1 for July-June)
            
        Returns:
            Dict with sector-neutral premium and breakdown by sector
        """
        from app.core.sectors import normalize_sector, GICS_SECTORS
        
        formation_year = year - 1  # FY data from year-1
        
        # Get R&D data with sector info from formation year
        rd_result = await self.session.execute(
            select(
                FMPIncomeStatement.symbol,
                FMPIncomeStatement.rd_expenses,
                FMPIncomeStatement.revenue,
                SP500Company.sector
            )
            .outerjoin(SP500Company, FMPIncomeStatement.symbol == SP500Company.symbol)
            .where(FMPIncomeStatement.fiscal_year == formation_year)
            .where(FMPIncomeStatement.period == "FY")
            .where(FMPIncomeStatement.rd_expenses >= 0)
            .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
        )
        
        # Group companies by normalized sector
        sector_data = {}
        for r in rd_result.fetchall():
            normalized_sector = normalize_sector(r.sector) if r.sector else "Unknown"
            if normalized_sector not in sector_data:
                sector_data[normalized_sector] = []
            
            rd_intensity = r.rd_expenses / r.revenue * 100
            sector_data[normalized_sector].append({
                "symbol": r.symbol,
                "rd_intensity": cap_rd_intensity(rd_intensity, r.sector),
            })
        
        # Get returns (July-June or calendar)
        if self.use_july_june:
            return_result = await self.session.execute(
                select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                .where(JulyJuneReturn.formation_year == formation_year)
                .where(JulyJuneReturn.annualized_return.isnot(None))
                .where(JulyJuneReturn.data_tier == self.data_tier)
            )
            returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
        else:
            return_result = await self.session.execute(
                select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                .where(FMPAnnualReturn.year == year)
                .where(FMPAnnualReturn.annual_return.isnot(None))
            )
            returns = {r.symbol: r.annual_return for r in return_result.fetchall()}
        
        # Compute within-sector quintile premiums
        sector_premiums = {}
        
        for sector, companies in sector_data.items():
            # Add returns
            companies_with_returns = []
            for c in companies:
                symbol = c["symbol"]
                if symbol in returns and returns[symbol] is not None:
                    ret = returns[symbol]
                else:
                    continue
                companies_with_returns.append({**c, "return": ret})
            
            if len(companies_with_returns) < 5:
                continue  # Need at least 5 companies to form quintiles
            
            # Sort by R&D intensity within sector
            sorted_companies = sorted(companies_with_returns, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5
            
            # Get Q1 and Q5 returns
            q1_companies = sorted_companies[:quintile_size]
            q5_companies = sorted_companies[-quintile_size:] if quintile_size > 0 else sorted_companies
            
            if q1_companies and q5_companies:
                q1_return = np.mean([c["return"] for c in q1_companies])
                q5_return = np.mean([c["return"] for c in q5_companies])
                premium = q5_return - q1_return
                
                sector_premiums[sector] = {
                    "premium": float(premium) * 100,  # Convert to percentage
                    "q1_return": float(q1_return) * 100,
                    "q5_return": float(q5_return) * 100,
                    "n_companies": n,
                    "q1_n": len(q1_companies),
                    "q5_n": len(q5_companies)
                }
        
        if not sector_premiums:
            return {"error": "Insufficient data for sector-neutral analysis", "year": year}
        
        # Equal-weighted average across sectors
        sector_neutral_premium = np.mean([s["premium"] for s in sector_premiums.values()])
        
        return {
            "year": year,
            "formation_year": formation_year,
            "sector_neutral_premium": float(sector_neutral_premium),
            "n_sectors": len(sector_premiums),
            "sector_breakdown": sector_premiums,
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)"
            }
        }

    async def compute_ew_vs_vw_premium(
        self,
        start_year: int,
        end_year: int
    ) -> Dict:
        """
        Compute REAL equal-weighted vs value-weighted R&D premium comparison.
        
        PUBLICATION FIX (Dec 2025):
        - Actually recomputes quintile returns under both weighting schemes
        - Uses market cap (approximated by revenue * 10) for VW
        - Integrates July-June returns and delisting returns
        
        Args:
            start_year: First year to include
            end_year: Last year to include
            
        Returns:
            Dict with EW and VW premium statistics
        """
        ew_premiums = []
        vw_premiums = []
        
        for year in range(start_year, end_year + 1):
            formation_year = year - 1
            
            # Get R&D data with revenue (as market cap proxy)
            rd_result = await self.session.execute(
                select(
                    FMPIncomeStatement.symbol,
                    FMPIncomeStatement.rd_expenses,
                    FMPIncomeStatement.revenue
                )
                .where(FMPIncomeStatement.fiscal_year == formation_year)
                .where(FMPIncomeStatement.period == "FY")
                .where(FMPIncomeStatement.rd_expenses > 0)
                .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
            )
            
            companies = []
            for r in rd_result.fetchall():
                rd_intensity = (r.rd_expenses / r.revenue * 100) if r.revenue > 0 else 0
                companies.append({
                    "symbol": r.symbol,
                    "rd_intensity": min(rd_intensity, MAX_RD_INTENSITY_ABSOLUTE),
                    "market_cap_proxy": r.revenue * 10  # Simple proxy
                })
            
            if len(companies) < 25:  # Need at least 5 per quintile
                continue
            
            # Get returns
            if self.use_july_june:
                return_result = await self.session.execute(
                    select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                    .where(JulyJuneReturn.formation_year == formation_year)
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
                returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
            else:
                return_result = await self.session.execute(
                    select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                    .where(FMPAnnualReturn.year == year)
                )
                returns = {r.symbol: r.annual_return for r in return_result.fetchall()}
            
            # Add returns (including delisting)
            for c in companies:
                symbol = c["symbol"]
                if symbol in returns and returns[symbol] is not None:
                    c["return"] = returns[symbol]
                else:
                    c["return"] = None
            
            # Filter to companies with returns
            companies = [c for c in companies if c["return"] is not None]
            
            if len(companies) < 25:
                continue
            
            # Sort by R&D intensity and form quintiles
            sorted_companies = sorted(companies, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5
            
            q1 = sorted_companies[:quintile_size]
            q5 = sorted_companies[-quintile_size:]
            
            if not q1 or not q5:
                continue
            
            # Equal-weighted returns
            q1_ew = np.mean([c["return"] for c in q1])
            q5_ew = np.mean([c["return"] for c in q5])
            ew_premium = (q5_ew - q1_ew) * 100  # Convert to percentage
            ew_premiums.append(ew_premium)
            
            # Value-weighted returns
            q1_caps = [c["market_cap_proxy"] for c in q1]
            q5_caps = [c["market_cap_proxy"] for c in q5]
            q1_rets = [c["return"] for c in q1]
            q5_rets = [c["return"] for c in q5]
            
            q1_vw = np.average(q1_rets, weights=q1_caps) if sum(q1_caps) > 0 else 0
            q5_vw = np.average(q5_rets, weights=q5_caps) if sum(q5_caps) > 0 else 0
            vw_premium = (q5_vw - q1_vw) * 100
            vw_premiums.append(vw_premium)
        
        if len(ew_premiums) < 5:
            return {"error": "Insufficient data for EW vs VW comparison"}
        
        # Compute statistics
        ew_mean = float(np.mean(ew_premiums))
        vw_mean = float(np.mean(vw_premiums))
        ew_std = float(np.std(ew_premiums, ddof=1))
        vw_std = float(np.std(vw_premiums, ddof=1))
        n = len(ew_premiums)
        
        ew_t = ew_mean / (ew_std / np.sqrt(n)) if ew_std > 0 else 0
        vw_t = vw_mean / (vw_std / np.sqrt(n)) if vw_std > 0 else 0
        
        from scipy import stats as sp_stats
        ew_p = float(2 * (1 - sp_stats.t.cdf(abs(ew_t), df=n-1))) if n > 1 else 1.0
        vw_p = float(2 * (1 - sp_stats.t.cdf(abs(vw_t), df=n-1))) if n > 1 else 1.0
        
        return {
            "period": f"{start_year}-{end_year}",
            "n_years": n,
            "equal_weighted": {
                "mean_premium_pct": round(ew_mean, 2),
                "std_dev": round(ew_std, 2),
                "t_statistic": round(ew_t, 2),
                "p_value": round(ew_p, 4),
                "significant_005": bool(ew_p < 0.05)
            },
            "value_weighted": {
                "mean_premium_pct": round(vw_mean, 2),
                "std_dev": round(vw_std, 2),
                "t_statistic": round(vw_t, 2),
                "p_value": round(vw_p, 4),
                "significant_005": bool(vw_p < 0.05)
            },
            "ew_minus_vw_spread": round(ew_mean - vw_mean, 2),
            "interpretation": (
                "EW premium > VW suggests small-cap contribution. "
                f"Both schemes show {'significant' if ew_p < 0.05 and vw_p < 0.05 else 'mixed'} results."
            ),
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "market_cap_proxy": "Revenue × 10",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)"
            }
        }

    async def compute_rd_cap_sensitivity(
        self,
        start_year: int,
        end_year: int,
        rd_caps: List[float] = None
    ) -> Dict:
        """
        Compute R&D premium sensitivity to different R&D intensity caps.
        
        PUBLICATION FIX (Dec 2025):
        - Actually recomputes premiums under each cap scenario
        - Not heuristic-based multipliers
        
        Args:
            start_year: First year
            end_year: Last year
            rd_caps: List of R&D intensity caps (%) to test. Default: [50, 100, 200, 500]
            
        Returns:
            Dict with premium under each cap scenario
        """
        if rd_caps is None:
            rd_caps = [50.0, 100.0, 200.0, 500.0]
        
        results = {}
        
        for cap in rd_caps:
            premiums = []
            
            for year in range(start_year, end_year + 1):
                formation_year = year - 1
                
                # Get R&D data
                rd_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.rd_expenses,
                        FMPIncomeStatement.revenue
                    )
                    .where(FMPIncomeStatement.fiscal_year == formation_year)
                    .where(FMPIncomeStatement.period == "FY")
                    .where(FMPIncomeStatement.rd_expenses > 0)
                    .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
                )
                
                companies = []
                for r in rd_result.fetchall():
                    rd_intensity = (r.rd_expenses / r.revenue * 100) if r.revenue > 0 else 0
                    # Apply cap
                    capped_intensity = min(rd_intensity, cap)
                    companies.append({
                        "symbol": r.symbol,
                        "rd_intensity": capped_intensity
                    })
                
                if len(companies) < 25:
                    continue
                
                # Get returns
                if self.use_july_june:
                    return_result = await self.session.execute(
                        select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                        .where(JulyJuneReturn.formation_year == formation_year)
                        .where(JulyJuneReturn.data_tier == self.data_tier)
                    )
                    returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
                else:
                    return_result = await self.session.execute(
                        select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                        .where(FMPAnnualReturn.year == year)
                    )
                    returns = {r.symbol: r.annual_return for r in return_result.fetchall()}
                
                # Add returns (including delisting)
                for c in companies:
                    symbol = c["symbol"]
                    if symbol in returns and returns[symbol] is not None:
                        c["return"] = returns[symbol]
                    else:
                        c["return"] = None
                
                # Filter to companies with returns
                companies = [c for c in companies if c["return"] is not None]
                
                if len(companies) < 25:
                    continue
                
                # Sort by R&D intensity and form quintiles
                sorted_companies = sorted(companies, key=lambda x: x["rd_intensity"])
                n = len(sorted_companies)
                quintile_size = n // 5
                
                q1 = sorted_companies[:quintile_size]
                q5 = sorted_companies[-quintile_size:]
                
                if q1 and q5:
                    q1_ret = np.mean([c["return"] for c in q1])
                    q5_ret = np.mean([c["return"] for c in q5])
                    premium = (q5_ret - q1_ret) * 100
                    premiums.append(premium)
            
            if len(premiums) >= 5:
                mean_prem = float(np.mean(premiums))
                std_prem = float(np.std(premiums, ddof=1))
                n = len(premiums)
                t_stat = mean_prem / (std_prem / np.sqrt(n)) if std_prem > 0 else 0
                
                from scipy import stats as sp_stats
                p_value = float(2 * (1 - sp_stats.t.cdf(abs(t_stat), df=n-1))) if n > 1 else 1.0
                
                results[f"cap_{int(cap)}pct"] = {
                    "rd_cap_pct": cap,
                    "mean_premium_pct": round(mean_prem, 2),
                    "std_dev": round(std_prem, 2),
                    "t_statistic": round(t_stat, 2),
                    "p_value": round(p_value, 4),
                    "significant_005": bool(p_value < 0.05),
                    "n_years": n
                }
        
        # Determine robustness
        all_significant = all(r["significant_005"] for r in results.values())
        all_positive = all(r["mean_premium_pct"] > 0 for r in results.values())
        
        return {
            "period": f"{start_year}-{end_year}",
            "scenarios": results,
            "robustness_verdict": "ROBUST" if all_significant and all_positive else "SENSITIVE",
            "interpretation": (
                "Premium is robust if significant and positive under all cap scenarios. "
                f"Results: {'All scenarios significant' if all_significant else 'Some scenarios not significant'}."
            ),
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)",
                "note": "Each scenario recomputes quintiles with the specified R&D cap"
            }
        }

