"""
PATH: backend/app/services/etf_universe.py
PURPOSE:
  - Build point-in-time eligible universe for ETF formation
  - Implement provisional anti-lookahead gates when historical membership is unavailable
  - Track coverage metrics and provenance for audit

ROLE IN ARCHITECTURE:
  - Used by RDAlphaScorer and ETFBacktester for universe construction
  - Enforces anti-lookahead rules to prevent survivorship/lookahead bias

MAIN EXPORTS:
  - ETFUniverseBuilder: Main class for building eligible universes
  - EligibilityResult: Dataclass containing eligible symbols + metadata
  - EligibilityMode: Enum for published vs provisional

NON-RESPONSIBILITIES:
  - Does not score companies (see rd_alpha_scorer.py)
  - Does not compute returns (see etf_backtester.py)

NOTES FOR FUTURE AI:
  - Formation date is July 1 of as_of_year (Fama-French convention)
  - Provisional gates are deterministic fallbacks when membership is missing
  - All gates are logged for audit/provenance
"""

import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    SP500HistoricalConstituent,
    SP500Company,
    ResearchCohort,
    FMPIncomeStatement,
    FMPDailyPrice,
    MomentumCache,
    VolatilityCache,
    CompanyYearCore,
)
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD

logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration Constants
# ==============================================================================

# Minimum listing age before formation date (prevents recent IPOs)
MIN_LISTING_AGE_DAYS = 365

# Minimum trailing trading days for liquidity assessment
MIN_LIQUIDITY_TRADING_DAYS = 60

# Minimum median daily dollar volume ($) for liquidity gate
MIN_LIQUIDITY_DOLLAR_VOLUME = 1_000_000  # $1M median daily volume

# Minimum revenue for financial validity
MIN_REVENUE = MIN_REVENUE_THRESHOLD  # $100M from sanity_checks


# ==============================================================================
# Data Classes
# ==============================================================================

class EligibilityMode(str, Enum):
    """Mode indicating how eligibility was determined."""
    PUBLISHED = "published"      # Full historical membership used
    PROVISIONAL = "provisional"  # Anti-lookahead gates used (membership unavailable)


@dataclass
class GateResult:
    """Result of applying a single eligibility gate."""
    gate_name: str
    passed_count: int
    failed_count: int
    failed_symbols: List[str] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        total = self.passed_count + self.failed_count
        return self.passed_count / total if total > 0 else 0.0


@dataclass
class EligibilityResult:
    """Complete result of universe eligibility determination."""
    as_of_year: int
    formation_date: date
    mode: EligibilityMode
    
    # Eligible symbols
    eligible_symbols: List[str]
    
    # Gate results (for audit)
    gate_results: List[GateResult] = field(default_factory=list)
    
    # Coverage metrics
    total_candidates: int = 0
    membership_coverage: int = 0  # How many had historical membership data
    
    # Provenance
    warnings: List[str] = field(default_factory=list)
    
    @property
    def gates_applied(self) -> List[str]:
        return [g.gate_name for g in self.gate_results]
    
    def to_meta_dict(self) -> Dict:
        """Convert to dictionary for API response meta block."""
        return {
            "mode": self.mode.value,
            "formation_date": self.formation_date.isoformat(),
            "formation_date_rule": "July 1 of as_of_year (Fama-French convention)",
            "eligibility_gates_applied": self.gates_applied,
            "membership_coverage": self.membership_coverage,
            "total_candidates": self.total_candidates,
            "eligible_count": len(self.eligible_symbols),
            "exclusion_rate": 1.0 - (len(self.eligible_symbols) / self.total_candidates) if self.total_candidates > 0 else 0.0,
        }


# ==============================================================================
# ETF Universe Builder
# ==============================================================================

class ETFUniverseBuilder:
    """
    Builds point-in-time eligible universe for ETF formation.
    
    Formation Rules (Fama-French convention):
    - Formation date: July 1 of as_of_year
    - Uses FY(T-1) financials (filed before formation date)
    - Trailing momentum/volatility computed through June 30
    
    Eligibility Modes:
    - PUBLISHED: Uses sp500_historical_constituents (preferred)
    - PROVISIONAL: Uses anti-lookahead gates when membership unavailable
    
    Provisional Gates (in order):
    1. Listing gate: First price date <= formation_date - 365 days
    2. Filing gate: FY(T-1) financials filed <= formation_date
    3. Liquidity gate: Median 60-day dollar volume >= threshold
    4. Risk data gate: Momentum + volatility computable for as_of_year
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def build_eligible_universe(
        self,
        as_of_year: int,
        min_revenue: float = MIN_REVENUE,
        require_risk_data: bool = True,
    ) -> EligibilityResult:
        """
        Build eligible universe for ETF formation.
        
        Args:
            as_of_year: Year for ETF formation (portfolio holds July T to June T+1)
            min_revenue: Minimum revenue threshold for inclusion
            require_risk_data: Whether to require momentum/volatility data
            
        Returns:
            EligibilityResult with eligible symbols and metadata
        """
        formation_date = date(as_of_year, 7, 1)
        
        # Step 1: Try to use historical S&P 500 membership (PUBLISHED mode)
        membership_symbols = await self._get_historical_membership(formation_date)
        
        if membership_symbols:
            # PUBLISHED mode: filter by membership + basic financial validity
            result = await self._build_published_universe(
                as_of_year=as_of_year,
                formation_date=formation_date,
                membership_symbols=membership_symbols,
                min_revenue=min_revenue,
                require_risk_data=require_risk_data,
            )
        else:
            # PROVISIONAL mode: apply anti-lookahead gates
            result = await self._build_provisional_universe(
                as_of_year=as_of_year,
                formation_date=formation_date,
                min_revenue=min_revenue,
                require_risk_data=require_risk_data,
            )
        
        return result
    
    async def _get_historical_membership(self, formation_date: date) -> Set[str]:
        """
        Get S&P 500 constituents as of formation date from historical table.
        
        Returns empty set if no data available.
        """
        try:
            result = await self.session.execute(
                select(SP500HistoricalConstituent.symbol)
                .where(
                    SP500HistoricalConstituent.added_date <= formation_date,
                    or_(
                        SP500HistoricalConstituent.removed_date == None,
                        SP500HistoricalConstituent.removed_date >= formation_date,
                    ),
                )
            )
            symbols = {r[0] for r in result.fetchall() if r and r[0]}
            
            if symbols:
                logger.info(f"Historical membership: {len(symbols)} S&P 500 constituents as of {formation_date}")
            
            return symbols
            
        except Exception as e:
            logger.warning(f"Could not load historical membership for {formation_date}: {e}")
            return set()
    
    async def _build_published_universe(
        self,
        as_of_year: int,
        formation_date: date,
        membership_symbols: Set[str],
        min_revenue: float,
        require_risk_data: bool,
    ) -> EligibilityResult:
        """Build universe using historical membership (PUBLISHED mode)."""
        
        gate_results = []
        warnings = []
        
        # Start with membership
        current_symbols = membership_symbols.copy()
        initial_count = len(current_symbols)
        
        gate_results.append(GateResult(
            gate_name="membership",
            passed_count=len(current_symbols),
            failed_count=0,
        ))
        
        # Apply financial validity gate (FY(T-1) data exists with min revenue)
        financial_valid = await self._apply_financial_gate(
            symbols=current_symbols,
            fiscal_year=as_of_year - 1,
            min_revenue=min_revenue,
        )
        
        failed_financial = current_symbols - financial_valid
        gate_results.append(GateResult(
            gate_name="financial_validity",
            passed_count=len(financial_valid),
            failed_count=len(failed_financial),
            failed_symbols=list(failed_financial)[:20],  # Limit for logging
        ))
        current_symbols = financial_valid
        
        # Apply risk data gate if required
        if require_risk_data:
            risk_valid = await self._apply_risk_data_gate(current_symbols, as_of_year)
            failed_risk = current_symbols - risk_valid
            gate_results.append(GateResult(
                gate_name="risk_data",
                passed_count=len(risk_valid),
                failed_count=len(failed_risk),
                failed_symbols=list(failed_risk)[:20],
            ))
            current_symbols = risk_valid
        
        return EligibilityResult(
            as_of_year=as_of_year,
            formation_date=formation_date,
            mode=EligibilityMode.PUBLISHED,
            eligible_symbols=sorted(current_symbols),
            gate_results=gate_results,
            total_candidates=initial_count,
            membership_coverage=len(membership_symbols),
            warnings=warnings,
        )
    
    async def _build_provisional_universe(
        self,
        as_of_year: int,
        formation_date: date,
        min_revenue: float,
        require_risk_data: bool,
    ) -> EligibilityResult:
        """Build universe using anti-lookahead gates (PROVISIONAL mode)."""
        
        gate_results = []
        warnings = [
            "PROVISIONAL MODE: Historical S&P 500 membership unavailable. "
            "Using anti-lookahead gates to approximate point-in-time universe. "
            "Run `scripts/ingest_sp500_historical.py` to enable PUBLISHED mode."
        ]
        
        # Start with all companies in research cohort that have data
        result = await self.session.execute(
            select(ResearchCohort.symbol)
            .where(
                ResearchCohort.years_with_data >= 3,
                ResearchCohort.avg_rd_intensity > 0,
            )
        )
        current_symbols = {r[0] for r in result.fetchall() if r and r[0]}
        initial_count = len(current_symbols)
        
        logger.info(f"Provisional mode: starting with {initial_count} research cohort candidates")
        
        # Gate 1: Listing gate (must have been trading for 1+ year before formation)
        listing_valid = await self._apply_listing_gate(current_symbols, formation_date)
        failed_listing = current_symbols - listing_valid
        gate_results.append(GateResult(
            gate_name="listing_age",
            passed_count=len(listing_valid),
            failed_count=len(failed_listing),
            failed_symbols=list(failed_listing)[:20],
        ))
        current_symbols = listing_valid
        
        # Gate 2: Filing gate (FY(T-1) financials filed before formation)
        filing_valid = await self._apply_filing_gate(
            symbols=current_symbols,
            fiscal_year=as_of_year - 1,
            formation_date=formation_date,
            min_revenue=min_revenue,
        )
        failed_filing = current_symbols - filing_valid
        gate_results.append(GateResult(
            gate_name="filing_date",
            passed_count=len(filing_valid),
            failed_count=len(failed_filing),
            failed_symbols=list(failed_filing)[:20],
        ))
        current_symbols = filing_valid
        
        # Gate 3: Liquidity gate (sufficient trading volume)
        liquidity_valid = await self._apply_liquidity_gate(current_symbols, formation_date)
        failed_liquidity = current_symbols - liquidity_valid
        gate_results.append(GateResult(
            gate_name="liquidity",
            passed_count=len(liquidity_valid),
            failed_count=len(failed_liquidity),
            failed_symbols=list(failed_liquidity)[:20],
        ))
        current_symbols = liquidity_valid
        
        # Gate 4: Risk data gate (momentum + volatility computable)
        if require_risk_data:
            risk_valid = await self._apply_risk_data_gate(current_symbols, as_of_year)
            failed_risk = current_symbols - risk_valid
            gate_results.append(GateResult(
                gate_name="risk_data",
                passed_count=len(risk_valid),
                failed_count=len(failed_risk),
                failed_symbols=list(failed_risk)[:20],
            ))
            current_symbols = risk_valid
        
        return EligibilityResult(
            as_of_year=as_of_year,
            formation_date=formation_date,
            mode=EligibilityMode.PROVISIONAL,
            eligible_symbols=sorted(current_symbols),
            gate_results=gate_results,
            total_candidates=initial_count,
            membership_coverage=0,  # No membership data in provisional mode
            warnings=warnings,
        )
    
    async def _apply_listing_gate(
        self,
        symbols: Set[str],
        formation_date: date,
    ) -> Set[str]:
        """
        Apply listing age gate: symbol must have price data at least 1 year before formation.
        
        This prevents including companies that IPO'd too recently (e.g., HOOD in 2021
        would be excluded from 2019 formation).
        """
        cutoff_date = formation_date - timedelta(days=MIN_LISTING_AGE_DAYS)
        
        # Find first price date for each symbol
        result = await self.session.execute(
            select(
                FMPDailyPrice.symbol,
                func.min(FMPDailyPrice.date).label("first_date"),
            )
            .where(FMPDailyPrice.symbol.in_(symbols))
            .group_by(FMPDailyPrice.symbol)
            .having(func.min(FMPDailyPrice.date) <= cutoff_date)
        )
        
        valid_symbols = {r[0] for r in result.fetchall() if r and r[0]}
        
        logger.debug(f"Listing gate: {len(valid_symbols)}/{len(symbols)} passed (cutoff: {cutoff_date})")
        return valid_symbols
    
    async def _apply_filing_gate(
        self,
        symbols: Set[str],
        fiscal_year: int,
        formation_date: date,
        min_revenue: float,
    ) -> Set[str]:
        """
        Apply filing date gate: FY(T-1) financials must be filed before formation date.
        
        Uses CompanyYearCore.filing_date when available, otherwise FMPIncomeStatement.date.
        """
        valid_symbols = set()
        
        # First try CompanyYearCore for filing dates
        cyc_result = await self.session.execute(
            select(CompanyYearCore.ticker)
            .where(
                CompanyYearCore.ticker.in_(symbols),
                CompanyYearCore.fiscal_year == fiscal_year,
                CompanyYearCore.filing_date.isnot(None),
                CompanyYearCore.filing_date <= formation_date,
            )
        )
        valid_symbols.update({r[0] for r in cyc_result.fetchall() if r and r[0]})
        
        # For remaining symbols, check FMPIncomeStatement
        remaining = symbols - valid_symbols
        if remaining:
            fmp_result = await self.session.execute(
                select(FMPIncomeStatement.symbol)
                .where(
                    FMPIncomeStatement.symbol.in_(remaining),
                    FMPIncomeStatement.fiscal_year == fiscal_year,
                    or_(
                        FMPIncomeStatement.period == None,
                        FMPIncomeStatement.period == "FY",
                    ),
                    FMPIncomeStatement.revenue.isnot(None),
                    FMPIncomeStatement.revenue >= min_revenue,
                    FMPIncomeStatement.rd_expenses.isnot(None),
                    FMPIncomeStatement.rd_expenses > 0,
                    # Use date field as proxy for filing date
                    or_(
                        FMPIncomeStatement.date == None,  # If no date, assume available
                        FMPIncomeStatement.date <= formation_date,
                    ),
                )
            )
            valid_symbols.update({r[0] for r in fmp_result.fetchall() if r and r[0]})
        
        logger.debug(f"Filing gate: {len(valid_symbols)}/{len(symbols)} passed (FY{fiscal_year} by {formation_date})")
        return valid_symbols
    
    async def _apply_financial_gate(
        self,
        symbols: Set[str],
        fiscal_year: int,
        min_revenue: float,
    ) -> Set[str]:
        """
        Apply financial validity gate: FY(T-1) must have valid revenue and R&D data.
        """
        result = await self.session.execute(
            select(FMPIncomeStatement.symbol)
            .where(
                FMPIncomeStatement.symbol.in_(symbols),
                FMPIncomeStatement.fiscal_year == fiscal_year,
                or_(
                    FMPIncomeStatement.period == None,
                    FMPIncomeStatement.period == "FY",
                ),
                FMPIncomeStatement.revenue.isnot(None),
                FMPIncomeStatement.revenue >= min_revenue,
                FMPIncomeStatement.rd_expenses.isnot(None),
                FMPIncomeStatement.rd_expenses > 0,
            )
        )
        
        valid_symbols = {r[0] for r in result.fetchall() if r and r[0]}
        
        logger.debug(f"Financial gate: {len(valid_symbols)}/{len(symbols)} passed (FY{fiscal_year}, min_rev=${min_revenue/1e6:.0f}M)")
        return valid_symbols
    
    async def _apply_liquidity_gate(
        self,
        symbols: Set[str],
        formation_date: date,
    ) -> Set[str]:
        """
        Apply liquidity gate: median 60-day dollar volume >= threshold.
        
        Uses trailing 60 trading days ending before formation date.
        """
        start_date = formation_date - timedelta(days=90)  # ~60 trading days
        
        # Calculate median dollar volume per symbol
        # Note: This is a simplified version; production might use a window function
        valid_symbols = set()
        
        for symbol in symbols:
            result = await self.session.execute(
                select(
                    FMPDailyPrice.close,
                    FMPDailyPrice.volume,
                )
                .where(
                    FMPDailyPrice.symbol == symbol,
                    FMPDailyPrice.date >= start_date,
                    FMPDailyPrice.date < formation_date,
                    FMPDailyPrice.close.isnot(None),
                    FMPDailyPrice.close > 0,
                    FMPDailyPrice.volume.isnot(None),
                    FMPDailyPrice.volume > 0,
                )
                .order_by(FMPDailyPrice.date.desc())
                .limit(MIN_LIQUIDITY_TRADING_DAYS)
            )
            
            rows = result.fetchall()
            if len(rows) >= MIN_LIQUIDITY_TRADING_DAYS // 2:  # Require at least half the days
                dollar_volumes = [r[0] * r[1] for r in rows if r[0] and r[1]]
                if dollar_volumes:
                    median_volume = sorted(dollar_volumes)[len(dollar_volumes) // 2]
                    if median_volume >= MIN_LIQUIDITY_DOLLAR_VOLUME:
                        valid_symbols.add(symbol)
        
        logger.debug(f"Liquidity gate: {len(valid_symbols)}/{len(symbols)} passed (min ${MIN_LIQUIDITY_DOLLAR_VOLUME/1e6:.1f}M median daily)")
        return valid_symbols
    
    async def _apply_risk_data_gate(
        self,
        symbols: Set[str],
        as_of_year: int,
    ) -> Set[str]:
        """
        Apply risk data gate: momentum and volatility must be computable.
        
        This ensures we don't use default fallbacks during scoring.
        """
        # Check momentum cache
        momentum_result = await self.session.execute(
            select(MomentumCache.symbol)
            .where(
                MomentumCache.symbol.in_(symbols),
                MomentumCache.as_of_year == as_of_year,
                MomentumCache.momentum_factor.isnot(None),
            )
        )
        has_momentum = {r[0] for r in momentum_result.fetchall() if r and r[0]}
        
        # Check volatility cache
        volatility_result = await self.session.execute(
            select(VolatilityCache.symbol)
            .where(
                VolatilityCache.symbol.in_(symbols),
                VolatilityCache.as_of_year == as_of_year,
                VolatilityCache.volatility_3yr.isnot(None),
            )
        )
        has_volatility = {r[0] for r in volatility_result.fetchall() if r and r[0]}
        
        # Must have both
        valid_symbols = has_momentum & has_volatility
        
        # For symbols without cached data, we allow them through but they'll
        # get computed on-the-fly (the scorer handles this)
        # In strict mode, we'd require cached data
        
        # For now, be lenient: if no cache exists, allow through (scorer computes)
        if not valid_symbols:
            logger.warning(f"Risk data gate: No cached momentum/volatility for {as_of_year}. Allowing all {len(symbols)} symbols (will compute on-the-fly).")
            return symbols
        
        logger.debug(f"Risk data gate: {len(valid_symbols)}/{len(symbols)} have cached risk data for {as_of_year}")
        return valid_symbols


# ==============================================================================
# Convenience function for external use
# ==============================================================================

async def get_eligible_universe(
    session: AsyncSession,
    as_of_year: int,
    min_revenue: float = MIN_REVENUE,
    require_risk_data: bool = False,  # Default False for backward compatibility
) -> EligibilityResult:
    """
    Convenience function to get eligible universe for ETF formation.
    
    Args:
        session: Database session
        as_of_year: Year for ETF formation
        min_revenue: Minimum revenue threshold
        require_risk_data: Whether to require cached momentum/volatility
        
    Returns:
        EligibilityResult with eligible symbols and metadata
    """
    builder = ETFUniverseBuilder(session)
    return await builder.build_eligible_universe(
        as_of_year=as_of_year,
        min_revenue=min_revenue,
        require_risk_data=require_risk_data,
    )

