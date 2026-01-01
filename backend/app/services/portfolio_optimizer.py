"""
Portfolio Optimizer Service for R&D ETF Construction

Selects top R&D companies, calculates portfolio returns,
and compares against benchmarks.

Now supports multiple selection methods:
- quality_adjusted: Legacy R&D intensity * quality score
- highest_rd: Pure R&D intensity ranking  
- balanced: Sector-diversified selection
- rd_alpha: NEW - Research-based sector-agnostic scoring (recommended)
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import numpy as np
from sqlalchemy import select, func, desc, and_, case, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ResearchCohort, FMPIncomeStatement, 
    FMPAnnualReturn, FMPDailyPrice, SP500Company, RollingWindowResult, JulyJuneReturn
)
from app.services.sanity_checks import (
    cap_rd_intensity, 
    MIN_REVENUE_THRESHOLD,
    MAX_RD_INTENSITY_ABSOLUTE,
    HIGH_RD_SECTORS
)

logger = logging.getLogger(__name__)

async def _get_baseline_rd_premium_pct(
    session: AsyncSession,
    *,
    window_type: str,
    return_convention: str,
    data_tier: str = "tier1",
) -> float:
    """
    Get the baseline Q5-Q1 premium (percentage points) from stored rolling-window aggregates.
    
    IMPORTANT:
      - This reads pre-computed `RollingWindowResult` rows (publication pipeline output).
      - It is used to power portfolio “projection”/“forecast” UI features without hardcoding numbers.
    
    Args:
        session: DB session
        window_type: "5yr" / "10yr" / "20yr"
        return_convention: "july_june" or "calendar"
        data_tier: "tier1" or "tier2"
    
    Returns:
        Premium in percentage points (e.g., 7.11 means +7.11% per year).
        Returns 0.0 if inputs are unavailable.
    """
    result = await session.execute(
        select(RollingWindowResult.quintile, func.avg(RollingWindowResult.avg_return))
        .where(
            RollingWindowResult.window_type == window_type,
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == data_tier,
            RollingWindowResult.quintile.in_([1, 5]),
            RollingWindowResult.avg_return.isnot(None),
        )
        .group_by(RollingWindowResult.quintile)
    )
    rows = result.fetchall()
    by_q = {int(q): float(avg) for q, avg in rows if q is not None and avg is not None}
    if 1 not in by_q or 5 not in by_q:
        return 0.0
    return float(by_q[5] - by_q[1])

# Minimum revenue for inclusion (filter out pre-revenue companies with extreme ratios)
MIN_REVENUE = MIN_REVENUE_THRESHOLD  # $100M

# Maximum R&D intensity cap (prevents outliers like 4800%)
MAX_RD_INTENSITY = MAX_RD_INTENSITY_ABSOLUTE  # 100%


@dataclass
class PortfolioHolding:
    """Single holding in the portfolio."""
    symbol: str
    name: str
    sector: str
    weight: float
    rd_intensity: float
    quality_score: float


@dataclass
class PortfolioPerformance:
    """Performance metrics for a portfolio."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    years: int


class PortfolioOptimizer:
    """
    Optimizes R&D-focused portfolio construction.
    
    PUBLICATION FIX (Dec 2025):
    - Supports July-June returns (Fama-French convention) via use_july_june flag
    - Integrates delisting returns for survivorship bias correction
    - Uses standardized risk-free rate from RiskFreeRate table
    """
    
    # Default risk-free rate when database has no data
    DEFAULT_RISK_FREE_RATE = 0.02  # 2% annual
    
    def __init__(self, session: AsyncSession, use_july_june: bool = True):
        """
        Initialize portfolio optimizer.
        
        Args:
            session: Database session
            use_july_june: If True (default), use July-June returns (Fama-French convention)
                          to eliminate look-ahead bias. Set False for calendar year returns.
        """
        self.session = session
        self.use_july_june = use_july_june
        self._rf_cache = {}  # Cache for risk-free rates

    async def get_risk_free_rate(self, year: int) -> float:
        """
        Get risk-free rate for a specific year from database.
        
        Uses RiskFreeRate table if available, otherwise falls back to default.
        This standardizes RF usage across research and ETF metrics.
        
        Args:
            year: Calendar year
            
        Returns:
            Annual risk-free rate as decimal (e.g., 0.02 for 2%)
        """
        if year in self._rf_cache:
            return self._rf_cache[year]
        
        from app.db.models import RiskFreeRate
        from datetime import date
        
        # Get average RF rate for the year
        result = await self.session.execute(
            select(func.avg(RiskFreeRate.rate_annual_pct))
            .where(
                RiskFreeRate.date >= date(year, 1, 1),
                RiskFreeRate.date <= date(year, 12, 31)
            )
        )
        avg_rate = result.scalar()
        
        if avg_rate is not None:
            rate = avg_rate / 100  # Convert from percentage (e.g., 2.0) to decimal (e.g., 0.02)
            self._rf_cache[year] = rate
            return rate
        
        # Fallback to default
        return self.DEFAULT_RISK_FREE_RATE
    
    async def select_top_rd_companies(
        self,
        n: int = 20,
        method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None,
        min_years: int = 5
    ) -> List[PortfolioHolding]:
        """
        Select top N R&D companies for portfolio.
        
        Methods:
        - "quality_adjusted": Combines R&D intensity with data quality
        - "highest_rd": Pure R&D intensity ranking
        - "balanced": Diversified across sectors
        - "rd_alpha": NEW - Research-based sector-agnostic scoring (recommended)
        """
        # Use new R&D Alpha scorer for rd_alpha method
        if method == "rd_alpha":
            holdings, _ = await self._select_with_rd_alpha_scorer(n=n, as_of_year=None)
            return holdings
        
        query = select(ResearchCohort).where(
            ResearchCohort.years_with_data >= min_years,
            ResearchCohort.avg_rd_intensity > 0
        )
        
        if sectors:
            query = query.where(ResearchCohort.sector.in_(sectors))
        
        if method == "quality_adjusted":
            # Score = rd_intensity * data_quality_score / 100
            query = query.order_by(
                desc(ResearchCohort.avg_rd_intensity * ResearchCohort.data_quality_score / 100.0)
            )
        elif method == "highest_rd":
            query = query.order_by(desc(ResearchCohort.avg_rd_intensity))
        elif method == "balanced":
            # Will need post-processing for sector balance
            query = query.order_by(desc(ResearchCohort.avg_rd_intensity))
        
        query = query.limit(n * 2 if method == "balanced" else n)
        
        result = await self.session.execute(query)
        companies = result.scalars().all()
        
        if method == "balanced":
            companies = self._balance_by_sector(companies, n)
        else:
            companies = companies[:n]
        
        # Calculate weights (equal weight or market-cap weight)
        total_companies = len(companies)
        holdings = []
        
        for c in companies:
            holdings.append(PortfolioHolding(
                symbol=c.symbol,
                name=c.name or c.symbol,
                sector=c.sector or "Unknown",
                weight=1.0 / total_companies,  # Equal weight
                rd_intensity=float(c.avg_rd_intensity or 0),
                quality_score=float(c.data_quality_score or 0)
            ))
        
        return holdings
    
    async def _select_with_rd_alpha_scorer(
        self,
        n: int = 20,
        as_of_year: Optional[int] = None
    ) -> Tuple[List[PortfolioHolding], Optional[Dict]]:
        """
        Select companies using the new R&D Alpha scoring engine.
        
        This method:
        - Uses sector-agnostic weighting to prevent tech/biotech overconcentration
        - Applies the research-based selection formula
        - Integrates findings from Papers 1-4
        - Returns eligibility metadata for transparency
        
        Returns:
            Tuple of (holdings list, eligibility metadata dict or None)
        """
        from app.services.rd_alpha_scorer import RDAlphaScorer
        
        scorer = RDAlphaScorer(self.session)
        
        # Calculate scores (returns tuple with eligibility result)
        all_scores, eligibility_result = await scorer.calculate_alpha_scores(
            universe="sp500",
            as_of_year=as_of_year
        )
        
        # Apply sector constraints
        selected, _ = await scorer.apply_sector_constraints(all_scores, n_holdings=n)
        
        # Convert to PortfolioHolding format
        holdings = []
        for score in selected:
            holdings.append(PortfolioHolding(
                symbol=score.symbol,
                name=score.name,
                sector=score.sector,
                weight=score.weight,
                rd_intensity=score.rd_intensity,
                quality_score=score.quality_score
            ))
        
        # Build eligibility metadata for API response
        eligibility_meta = None
        if eligibility_result:
            eligibility_meta = eligibility_result.to_meta_dict()
            eligibility_meta["warnings"] = eligibility_result.warnings
        
        return holdings, eligibility_meta
    
    async def select_top_rd_companies_for_year(
        self,
        as_of_year: int,
        n: int = 20,
        method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None
    ) -> List[PortfolioHolding]:
        """
        Select top N R&D companies based on their R&D intensity in a SPECIFIC YEAR.
        
        This provides point-in-time holdings, selecting companies that were
        the top R&D spenders at that particular point in history.
        
        IMPORTANT: Uses FY(as_of_year - 1) data to avoid look-ahead bias.
        At the start of year T, only FY(T-1) data is available.
        
        Filters applied:
        - Minimum revenue: $100M (prevents extreme ratios from pre-revenue companies)
        - R&D intensity capped at 100% (prevents outliers)
        """
        # Allow point-in-time selection using the R&D Alpha scoring engine
        # (sector-constrained, research-based scoring; uses only information available as-of as_of_year)
        if method == "rd_alpha":
            holdings, _ = await self._select_with_rd_alpha_scorer(n=n, as_of_year=as_of_year)
            return holdings

        # Use PRIOR year's financial data to avoid look-ahead bias
        # At the start of 2020, we would only have FY2019 data available
        data_year = as_of_year - 1
        
        # Subquery to get R&D intensity for each company
        # R&D Intensity = R&D Expense / Revenue * 100, capped at MAX_RD_INTENSITY
        raw_intensity = FMPIncomeStatement.rd_expenses / FMPIncomeStatement.revenue * 100
        
        subq = (
            select(
                FMPIncomeStatement.symbol,
                # Cap R&D intensity at MAX_RD_INTENSITY to prevent outliers
                case(
                    (raw_intensity > MAX_RD_INTENSITY, MAX_RD_INTENSITY),
                    else_=raw_intensity
                ).label("rd_intensity"),
                FMPIncomeStatement.revenue
            )
            .where(
                FMPIncomeStatement.fiscal_year == data_year,
                # Minimum revenue filter to prevent extreme ratios
                FMPIncomeStatement.revenue >= MIN_REVENUE,
                FMPIncomeStatement.rd_expenses > 0
            )
        ).subquery()
        
        # Join with SP500Company for company details
        query = (
            select(
                subq.c.symbol,
                subq.c.rd_intensity,
                subq.c.revenue,
                SP500Company.name,
                SP500Company.sector
            )
            .join(SP500Company, SP500Company.symbol == subq.c.symbol)
        )
        
        if sectors:
            query = query.where(SP500Company.sector.in_(sectors))
        
        # Order by R&D intensity (already capped)
        query = query.order_by(desc(subq.c.rd_intensity)).limit(n)
        
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        if not rows:
            # Fallback to ResearchCohort if no FMPIncomeStatement data
            logger.warning(f"No income statement data for year {data_year}, using ResearchCohort fallback")
            return await self.select_top_rd_companies(n=n, method=method, sectors=sectors)
        
        # Calculate weights (equal weight)
        total_companies = len(rows)
        holdings = []
        
        for row in rows:
            # Apply sector-specific cap (higher for biotech/pharma)
            sector = row.sector or "Unknown"
            intensity = float(row.rd_intensity or 0)
            capped_intensity = cap_rd_intensity(intensity, sector)
            
            holdings.append(PortfolioHolding(
                symbol=row.symbol,
                name=row.name or row.symbol,
                sector=sector,
                weight=1.0 / total_companies,
                rd_intensity=capped_intensity,
                quality_score=80.0  # Default quality score for historical selection
            ))
        
        logger.info(f"Selected {len(holdings)} holdings for year {as_of_year} using FY{data_year} data")
        return holdings
    
    async def get_forecast_vs_actual(
        self,
        as_of_year: int,
        n_holdings: int = 20,
        method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None
    ) -> Dict:
        """
        Compare forecasted returns (based on R&D premium) vs actual returns.
        
        If as_of_year is in the past, we can compare what we would have
        forecasted vs what actually happened.
        """
        current_year = datetime.now().year
        
        # Get holdings for that year
        holdings = await self.select_top_rd_companies_for_year(
            as_of_year=as_of_year,
            n=n_holdings,
            method=method,
            sectors=sectors
        )
        
        symbols = [h.symbol for h in holdings]
        weights = [h.weight for h in holdings]
        
        # Baseline premium (publication-grade): derived from stored rolling-window results.
        return_convention = "july_june" if self.use_july_june else "calendar"
        premium_pct = await _get_baseline_rd_premium_pct(
            self.session,
            window_type="5yr",
            return_convention=return_convention,
            data_tier="tier1",
        )
        premium = premium_pct / 100.0  # pct points -> decimal
        
        # Benchmark return for the period (align to return convention).
        if self.use_july_june:
            formation_year = as_of_year - 1
            bench_result = await self.session.execute(
                select(func.avg(JulyJuneReturn.annualized_return))
                .where(
                    JulyJuneReturn.formation_year == formation_year,
                    JulyJuneReturn.data_tier == "tier1",
                    JulyJuneReturn.annualized_return.isnot(None),
                )
            )
            bench_raw = bench_result.scalar()
            benchmark_return = float(bench_raw) if bench_raw is not None else 0.08
        else:
            bench_result = await self.session.execute(
                select(func.avg(FMPAnnualReturn.annual_return))
                .where(FMPAnnualReturn.year == as_of_year)
            )
            bench_raw = bench_result.scalar()
            benchmark_return = float(bench_raw) if bench_raw is not None else 0.08
        
        # Projection (NOT a prediction): benchmark + baseline premium.
        forecast_return = benchmark_return + premium
        
        # Calculate actual portfolio return for that period
        actual_return = 0.0
        valid_w = 0.0
        for symbol, weight in zip(symbols, weights):
            if self.use_july_june:
                formation_year = as_of_year - 1
                result = await self.session.execute(
                    select(JulyJuneReturn.annualized_return)
                    .where(
                        JulyJuneReturn.symbol == symbol,
                        JulyJuneReturn.formation_year == formation_year,
                        JulyJuneReturn.data_tier == "tier1",
                    )
                )
                r = result.scalar()
            else:
                result = await self.session.execute(
                    select(FMPAnnualReturn.annual_return)
                    .where(
                        FMPAnnualReturn.symbol == symbol,
                        FMPAnnualReturn.year == as_of_year
                    )
                )
                r = result.scalar()
            if r is not None:
                actual_return += float(r) * weight
                valid_w += weight
        
        if valid_w > 0:
            actual_return = actual_return / valid_w
        
        # Calculate if forecast was accurate
        is_historical = as_of_year < current_year
        forecast_error = (actual_return - forecast_return) if is_historical else None
        
        return {
            "year": as_of_year,
            "is_historical": is_historical,
            "forecast_return": round(forecast_return * 100, 2),
            "actual_return": round(actual_return * 100, 2) if is_historical else None,
            "benchmark_return": round(benchmark_return * 100, 2),
            "forecast_premium": round(premium * 100, 2),
            "forecast_error": round(forecast_error * 100, 2) if forecast_error is not None else None,
            "holdings_count": len(holdings),
            "avg_rd_intensity": round(sum(h.rd_intensity for h in holdings) / len(holdings), 2) if holdings else 0,
            "top_holdings": [
                {"symbol": h.symbol, "sector": h.sector, "rd_intensity": round(h.rd_intensity, 1)}
                for h in holdings[:5]
            ]
        }
    
    def _balance_by_sector(
        self, 
        companies: List[ResearchCohort], 
        n: int
    ) -> List[ResearchCohort]:
        """Select top companies while ensuring sector diversity."""
        sector_counts: Dict[str, int] = {}
        max_per_sector = max(2, n // 5)  # At least 5 sectors represented
        selected = []
        
        for c in companies:
            sector = c.sector or "Unknown"
            if sector_counts.get(sector, 0) < max_per_sector:
                selected.append(c)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if len(selected) >= n:
                break
        
        return selected
    
    async def get_available_windows(self) -> List[Dict]:
        """Get list of available time windows for analysis."""
        windows = []
        current_year = datetime.now().year
        
        # Generate 5-year windows
        for start in range(1995, current_year - 4):
            windows.append({
                "window_id": f"5yr_{start}_{start+4}",
                "window_type": "5yr",
                "start_year": start,
                "end_year": start + 4,
                "label": f"{start}-{start+4}"
            })
        
        # Generate 10-year windows
        for start in range(1995, current_year - 9):
            windows.append({
                "window_id": f"10yr_{start}_{start+9}",
                "window_type": "10yr",
                "start_year": start,
                "end_year": start + 9,
                "label": f"{start}-{start+9}"
            })
        
        return windows
    
    async def calculate_portfolio_returns(
        self,
        symbols: List[str],
        weights: List[float],
        start_year: int,
        end_year: int
    ) -> PortfolioPerformance:
        """
        Calculate portfolio performance over a period.
        
        PUBLICATION FIX (Dec 2025):
        - Now supports July-June returns (Fama-French convention) via self.use_july_june
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        """
        from app.db.models import JulyJuneReturn
        
        annual_returns = []
        
        for year in range(start_year, end_year + 1):
            year_return = 0.0
            valid_weights = 0.0
            
            for symbol, weight in zip(symbols, weights):
                ret = None
                
                if self.use_july_june:
                    # July-June returns: formation_year is year-1
                    formation_year = year - 1
                    result = await self.session.execute(
                        select(JulyJuneReturn.annualized_return)
                        .where(
                            JulyJuneReturn.symbol == symbol,
                            JulyJuneReturn.formation_year == formation_year,
                            JulyJuneReturn.data_tier == "tier1",
                        )
                    )
                    ret = result.scalar()
                else:
                    # Calendar year returns
                    result = await self.session.execute(
                        select(FMPAnnualReturn.annual_return)
                        .where(
                            FMPAnnualReturn.symbol == symbol,
                            FMPAnnualReturn.year == year
                        )
                    )
                    ret = result.scalar()
                
                if ret is not None:
                    year_return += float(ret) * weight
                    valid_weights += weight
            
            # Normalize for missing stocks
            if valid_weights > 0:
                year_return = year_return / valid_weights
                annual_returns.append(float(year_return))
        
        if not annual_returns:
            return PortfolioPerformance(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0, years=0
            )
        
        # Calculate metrics with time-varying risk-free rate from database
        # PUBLICATION FIX (Dec 2025): Use standardized RF from RiskFreeRate table
        rf_rates = []
        for year in range(start_year, end_year + 1):
            rf = await self.get_risk_free_rate(year)
            rf_rates.append(rf)
        avg_rf = float(np.mean(rf_rates)) if rf_rates else self.DEFAULT_RISK_FREE_RATE
        
        total_return = float(np.prod([1 + r for r in annual_returns]) - 1)
        annualized_return = float(np.mean(annual_returns))
        volatility = float(np.std(annual_returns, ddof=1)) if len(annual_returns) > 1 else 0
        
        # Sharpe Ratio = (Return - Risk-Free Rate) / Volatility
        # Note: annualized_return and volatility are in decimal form (0.10 = 10%)
        excess_return = annualized_return - avg_rf
        sharpe_ratio = float(excess_return / volatility) if volatility > 0 else 0
        
        # Calculate max drawdown
        cumulative = np.cumprod([1 + r for r in annual_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns))
        
        return PortfolioPerformance(
            total_return=round(total_return * 100, 2),
            annualized_return=round(annualized_return * 100, 2),
            volatility=round(volatility * 100, 2),
            sharpe_ratio=round(sharpe_ratio, 3),
            max_drawdown=round(max_drawdown * 100, 2),
            years=len(annual_returns)
        )
    
    async def calculate_benchmark_returns(
        self,
        benchmark_type: str,
        start_year: int,
        end_year: int
    ) -> PortfolioPerformance:
        """
        Calculate benchmark performance.
        
        Types:
        - "sp500": S&P 500 proxy (equal weight of all companies)
        - "equal_weight": Equal weight S&P 500
        - "sector_matched": Match sector weights to portfolio
        """
        # Get all companies with return data
        result = await self.session.execute(
            select(FMPAnnualReturn.symbol).distinct()
        )
        all_symbols = [r[0] for r in result.fetchall()]
        
        if not all_symbols:
            return PortfolioPerformance(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, max_drawdown=0, years=0
            )
        
        # Equal weight for all benchmarks (simplified)
        weights = [1.0 / len(all_symbols)] * len(all_symbols)
        
        return await self.calculate_portfolio_returns(
            all_symbols, weights, start_year, end_year
        )
    
    async def backtest_rd_etf(
        self,
        start_year: int,
        end_year: int,
        n_holdings: int = 20,
        selection_method: str = "quality_adjusted",
        sectors: Optional[List[str]] = None,
        use_point_in_time: bool = True
    ) -> Dict:
        """
        Run full backtest of R&D ETF strategy.
        
        Returns:
        - Portfolio performance
        - Benchmark comparisons
        - Holdings (start year + year-by-year)
        - Year-by-year returns
        """
        years = list(range(start_year, end_year + 1))

        # ---------------------------------------------------------------------
        # 1) Annual reconstitution (point-in-time): select holdings each year
        # ---------------------------------------------------------------------
        holdings_by_year: Dict[int, List[PortfolioHolding]] = {}
        universe_portfolio_symbols: set[str] = set()

        for year in years:
            if use_point_in_time:
                year_holdings = await self.select_top_rd_companies_for_year(
                    as_of_year=year,
                    n=n_holdings,
                    method=selection_method,
                    sectors=sectors,
                )
            else:
                year_holdings = await self.select_top_rd_companies(
                    n=n_holdings,
                    method=selection_method,
                    sectors=sectors,
                    min_years=5,
                )

            holdings_by_year[int(year)] = year_holdings
            for h in year_holdings:
                universe_portfolio_symbols.add(str(h.symbol))

        # Keep the start-year holdings as a convenient headline list (backward compatible)
        start_holdings = holdings_by_year.get(int(start_year), [])
        
        # Benchmark universe (S&P 500 proxy): the research cohort symbols (tier-consistent)
        bench_result = await self.session.execute(select(ResearchCohort.symbol))
        benchmark_symbols = [r[0] for r in bench_result.fetchall() if r and r[0]]
        if not benchmark_symbols:
            benchmark_symbols = list({*universe_portfolio_symbols})

        # Prefetch returns for performance-consistent yearly series
        from app.db.models import JulyJuneReturn

        # S&P 500 comparison series:
        # - Use SPY (cap-weighted, total-return proxy via split-adjusted close + dividends)
        #   to avoid relying on any “constituents API” and to keep the benchmark investable
        #   for practitioner readers.
        sp500_proxy_symbol = "SPY"

        universe_symbols = sorted({*universe_portfolio_symbols, *benchmark_symbols, sp500_proxy_symbol})

        # Return series (one query for the whole universe + period)
        returns_map: Dict[Tuple[str, int], float] = {}
        if self.use_july_june:
            formation_years = [y - 1 for y in years]
            ret_result = await self.session.execute(
                select(JulyJuneReturn.symbol, JulyJuneReturn.formation_year, JulyJuneReturn.annualized_return)
                .where(
                    JulyJuneReturn.symbol.in_(universe_symbols),
                    JulyJuneReturn.formation_year.in_(formation_years),
                    JulyJuneReturn.data_tier == "tier1",
                    JulyJuneReturn.annualized_return.isnot(None),
                )
            )
            for sym, formation_year, ret in ret_result.fetchall():
                if sym is None or formation_year is None or ret is None:
                    continue
                returns_map[(str(sym), int(formation_year) + 1)] = float(ret)
        else:
            ret_result = await self.session.execute(
                select(FMPAnnualReturn.symbol, FMPAnnualReturn.year, FMPAnnualReturn.annual_return)
                .where(
                    FMPAnnualReturn.symbol.in_(universe_symbols),
                    FMPAnnualReturn.year.in_(years),
                    FMPAnnualReturn.annual_return.isnot(None),
                )
            )
            for sym, year, ret in ret_result.fetchall():
                if sym is None or year is None or ret is None:
                    continue
                returns_map[(str(sym), int(year))] = float(ret)

        portfolio_annual_returns: List[float] = []
        portfolio_years: List[int] = []
        benchmark_annual_returns: List[float] = []
        benchmark_years: List[int] = []
        
        # S&P 500 proxy returns (SPY) aligned to the same return convention and return pipeline.
        # NOTE: This is a *proxy*, not the SPXTR index.
        sp500_returns_map: Dict[int, float] = {}
        for year in years:
            spy_ret = returns_map.get((sp500_proxy_symbol, year))
            if spy_ret is not None:
                sp500_returns_map[int(year)] = float(spy_ret)
        
        sp500_annual_returns: List[float] = []

        yearly_data: List[Dict[str, float]] = []

        # Turnover diagnostics (based on weight changes between annual reconstitutions)
        turnover_by_year: List[Dict[str, float]] = []

        # Optional net-of-cost series driven by realized turnover (simple approximation)
        from app.services.transaction_costs import TransactionCostEstimator
        cost_estimator = TransactionCostEstimator(universe="sp500", cost_model="moderate")
        portfolio_cost_template = cost_estimator.estimate_portfolio_cost(n_holdings=n_holdings, rebalancing_frequency="annual")
        round_trip_cost_per_full_turnover = float(portfolio_cost_template.round_trip_total)  # cost for 100% turnover
        benchmark_cost = 0.0003  # 3bp proxy for benchmark implementation
        portfolio_annual_returns_net: List[float] = []
        benchmark_annual_returns_net: List[float] = []

        prev_weights: Dict[str, float] = {}

        for year in years:
            # Holdings + weights for this year
            year_holdings = holdings_by_year.get(int(year), [])
            symbols = [h.symbol for h in year_holdings]
            weights = [float(h.weight) for h in year_holdings]
            curr_weights = {str(sym): float(w) for sym, w in zip(symbols, weights)}

            # Turnover: 0.5 * sum |w_t - w_{t-1}| (union of names)
            if prev_weights:
                keys = set(prev_weights.keys()) | set(curr_weights.keys())
                gross_turnover = 0.5 * sum(abs(curr_weights.get(k, 0.0) - prev_weights.get(k, 0.0)) for k in keys)
                n_added = len([k for k in curr_weights.keys() if k not in prev_weights])
                n_removed = len([k for k in prev_weights.keys() if k not in curr_weights])
            else:
                gross_turnover = 0.0
                n_added = len(curr_weights)
                n_removed = 0

            turnover_by_year.append(
                {
                    "year": int(year),
                    "turnover": round(float(gross_turnover), 4),
                    "turnover_pct": round(float(gross_turnover) * 100, 1),
                    "n_added": float(n_added),
                    "n_removed": float(n_removed),
                }
            )

            # Portfolio return (weighted; renormalize for missing returns)
            port_return = 0.0
            valid_w = 0.0
            for sym, w in zip(symbols, weights):
                ret = returns_map.get((sym, year))
                if ret is None:
                    continue
                port_return += float(ret) * float(w)
                valid_w += float(w)
            
            if valid_w > 0:
                port_return = port_return / valid_w
                portfolio_annual_returns.append(float(port_return))
                portfolio_years.append(int(year))
            else:
                port_return = 0.0

            # Benchmark return (equal-weight mean across benchmark universe)
            bench_vals: List[float] = []
            for sym in benchmark_symbols:
                ret = returns_map.get((sym, year))
                if ret is None:
                    continue
                bench_vals.append(float(ret))

            bench_return = float(np.mean(bench_vals)) if bench_vals else 0.0
            benchmark_annual_returns.append(float(bench_return))
            benchmark_years.append(int(year))

            # Net-of-cost approximation: cost scales with realized turnover (excluding initial build cost)
            annual_cost = round_trip_cost_per_full_turnover * float(gross_turnover)
            port_return_net = float(port_return) - float(annual_cost)
            bench_return_net = float(bench_return) - float(benchmark_cost)
            portfolio_annual_returns_net.append(port_return_net)
            benchmark_annual_returns_net.append(bench_return_net)

            # S&P 500 market return for this year
            sp500_return = sp500_returns_map.get(year, None)
            if sp500_return is not None:
                sp500_annual_returns.append(float(sp500_return))
            
            yearly_data.append(
                {
                    "year": int(year),
                    "portfolio_return": round(port_return * 100, 2),
                    "benchmark_return": round(bench_return * 100, 2),
                    "sp500_return": round(sp500_return * 100, 2) if sp500_return is not None else None,
                    "excess_return": round((port_return - bench_return) * 100, 2),
                    "excess_vs_sp500": round((port_return - sp500_return) * 100, 2) if sp500_return is not None else None,
                    "turnover_pct": round(float(gross_turnover) * 100, 1),
                    "portfolio_return_net": round(port_return_net * 100, 2),
                    "benchmark_return_net": round(bench_return_net * 100, 2),
                    "excess_return_net": round((port_return_net - bench_return_net) * 100, 2),
                }
            )

            prev_weights = curr_weights

        async def _perf_from_series(annual_returns: List[float], years_used: List[int]) -> Dict[str, float]:
            if not annual_returns:
                return {
                    "total_return": 0.0,
                    "annualized_return": 0.0,
                    "volatility": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                }

            total_return = float(np.prod([1 + r for r in annual_returns]) - 1)
            n_years = len(annual_returns)
            annualized_return = float((1 + total_return) ** (1 / n_years) - 1) if n_years > 0 else 0.0
            volatility = float(np.std(annual_returns)) if n_years > 1 else 0.0

            rf_rates = [await self.get_risk_free_rate(int(y)) for y in years_used] if years_used else []
            avg_rf = float(np.mean(rf_rates)) if rf_rates else self.DEFAULT_RISK_FREE_RATE
            excess = annualized_return - avg_rf
            sharpe = float(excess / volatility) if volatility > 0 else 0.0

            cumulative = np.cumprod([1 + r for r in annual_returns])
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = cumulative / running_max - 1
            max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else 0.0

            return {
                "total_return": round(total_return * 100, 2),
                "annualized_return": round(annualized_return * 100, 2),
                "volatility": round(volatility * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "max_drawdown": round(max_drawdown * 100, 2),
            }

        portfolio_perf = await _perf_from_series(portfolio_annual_returns, portfolio_years)
        benchmark_perf = await _perf_from_series(benchmark_annual_returns, benchmark_years)
        sp500_perf = await _perf_from_series(sp500_annual_returns, [y for y in years if y in sp500_returns_map])
        portfolio_perf_net = await _perf_from_series(portfolio_annual_returns_net, portfolio_years)
        benchmark_perf_net = await _perf_from_series(benchmark_annual_returns_net, benchmark_years)

        # Turnover summary
        turnover_vals = [float(t.get("turnover", 0.0)) for t in turnover_by_year[1:]]  # exclude first year
        avg_turnover = float(np.mean(turnover_vals)) if turnover_vals else 0.0
        max_turnover = float(np.max(turnover_vals)) if turnover_vals else 0.0
        
        return {
            "period": f"{start_year}-{end_year}",
            "meta": {
                "return_convention": "july_june" if self.use_july_june else "calendar",
                "benchmark_universe": "research_cohort_equal_weight",
                "sp500_proxy": "SPY_total_return_proxy_close_plus_dividends",
                "selection_method": selection_method,
                "n_holdings": int(n_holdings),
                "use_point_in_time": bool(use_point_in_time),
                "reconstitution": "annual",
            },
            "holdings": [
                {
                    "symbol": h.symbol,
                    "name": h.name,
                    "sector": h.sector,
                    "weight": round(h.weight * 100, 2),
                    "rd_intensity": round(h.rd_intensity, 2),
                }
                for h in start_holdings
            ],
            "holdings_by_year": {
                int(y): [
                    {
                        "symbol": h.symbol,
                        "name": h.name,
                        "sector": h.sector,
                        "weight": round(float(h.weight) * 100, 2),
                        "rd_intensity": round(float(h.rd_intensity), 2),
                    }
                    for h in holdings_by_year.get(int(y), [])
                ]
                for y in years
            },
            "portfolio_performance": portfolio_perf,
            "benchmark_performance": benchmark_perf,
            "sp500_performance": sp500_perf,
            "excess_return": round(float(portfolio_perf.get("annualized_return", 0.0)) - float(benchmark_perf.get("annualized_return", 0.0)), 2),
            "excess_vs_sp500": round(float(portfolio_perf.get("annualized_return", 0.0)) - float(sp500_perf.get("annualized_return", 0.0)), 2) if sp500_perf.get("annualized_return") else None,
            "portfolio_performance_net": portfolio_perf_net,
            "benchmark_performance_net": benchmark_perf_net,
            "excess_return_net": round(float(portfolio_perf_net.get("annualized_return", 0.0)) - float(benchmark_perf_net.get("annualized_return", 0.0)), 2),
            "turnover": {
                "avg_turnover_pct": round(avg_turnover * 100, 1),
                "max_turnover_pct": round(max_turnover * 100, 1),
                "by_year": turnover_by_year,
                "note": "Turnover is computed as 0.5 * sum |w_t - w_{t-1}|. First year turnover reflects initial formation and is excluded from averages.",
            },
            "cost_assumptions": {
                "cost_model": f"sp500_{cost_estimator.cost_model}",
                "round_trip_cost_per_100pct_turnover_pct": round(round_trip_cost_per_full_turnover * 100, 3),
                "benchmark_cost_pct": round(benchmark_cost * 100, 3),
                "note": "Net-of-cost series is a simple approximation: annual trading cost is proportional to realized turnover using literature-calibrated cost parameters.",
            },
            "yearly_data": yearly_data,
        }
    
    async def get_sector_allocation(
        self, 
        holdings: List[PortfolioHolding]
    ) -> List[Dict]:
        """Get sector allocation of portfolio."""
        sector_weights: Dict[str, float] = {}
        
        for h in holdings:
            sector_weights[h.sector] = sector_weights.get(h.sector, 0) + h.weight
        
        return [
            {"sector": s, "weight": round(w * 100, 2)}
            for s, w in sorted(sector_weights.items(), key=lambda x: -x[1])
        ]

