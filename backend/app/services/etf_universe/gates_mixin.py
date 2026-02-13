"""
PATH: backend/app/services/etf_universe/gates_mixin.py
PURPOSE: Eligibility gate methods for ETF universe filtering
WHY: Isolates each anti-lookahead gate into testable units
FLOW:
  ┌────────────────┐    ┌───────────────┐    ┌──────────────┐
  │ Set[str] syms  │ →  │ Gate logic    │ →  │ Set[str] ok  │
  └────────────────┘    └───────────────┘    └──────────────┘
DEPENDENCIES:
  - sqlalchemy: async DB queries
  - app.db.models: ORM models for financial data
RELATED:
  - builder.py: uses this mixin in ETFUniverseBuilder
"""

import logging
from typing import Set
from datetime import date, timedelta

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FMPIncomeStatement,
    FMPDailyPrice,
    MomentumCache,
    VolatilityCache,
    CompanyYearCore,
)
from app.services.etf_universe.data_classes import (
    MIN_LISTING_AGE_DAYS,
    MIN_LIQUIDITY_TRADING_DAYS,
    MIN_LIQUIDITY_DOLLAR_VOLUME,
)

logger = logging.getLogger(__name__)


class ETFUniverseGatesMixin:
    """
    Mixin providing eligibility gate methods for ETFUniverseBuilder.

    Each gate takes a set of candidate symbols and returns the subset
    that passes the gate's criteria.

    Gates (in provisional-mode order):
    1. Listing gate: First price date <= formation_date - 365 days
    2. Filing gate: FY(T-1) financials filed <= formation_date
    3. Financial gate: FY(T-1) has valid revenue and R&D data
    4. Liquidity gate: Median 60-day dollar volume >= threshold
    5. Risk data gate: Momentum + volatility computable for as_of_year
    """

    session: AsyncSession  # provided by the concrete class

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
