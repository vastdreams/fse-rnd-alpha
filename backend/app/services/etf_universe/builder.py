# EXEMPTION: 318 lines — ETF universe construction pipeline with tightly-coupled eligibility logic
"""
PATH: backend/app/services/etf_universe/builder.py
PURPOSE: ETFUniverseBuilder class — builds point-in-time eligible universe for ETF formation
WHY: Main entry point for universe construction, delegates gate logic to mixin
FLOW:
  ┌──────────────┐    ┌────────────────────┐    ┌───────────────────┐
  │ as_of_year   │ →  │ ETFUniverseBuilder │ →  │ EligibilityResult │
  └──────────────┘    └────────────────────┘    └───────────────────┘
DEPENDENCIES:
  - gates_mixin: anti-lookahead gate methods
  - data_classes: EligibilityMode, GateResult, EligibilityResult, MIN_REVENUE
RELATED:
  - gates_mixin.py: provides _apply_*_gate methods
  - data_classes.py: provides result types and constants
"""

import logging
from typing import Set
from datetime import date

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    SP500HistoricalConstituent,
    ResearchCohort,
)
from app.services.etf_universe.data_classes import (
    EligibilityMode,
    EligibilityResult,
    GateResult,
    MIN_REVENUE,
)
from app.services.etf_universe.gates_mixin import ETFUniverseGatesMixin

logger = logging.getLogger(__name__)


# ==============================================================================
# ETF Universe Builder
# ==============================================================================

class ETFUniverseBuilder(ETFUniverseGatesMixin):
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
