"""
PATH: backend/app/services/rd_alpha_scorer/scoring_mixin.py
PURPOSE: Mixin providing per-company scoring logic (R&D intensity, momentum, volatility, quality).
WHY: Isolates the per-company scoring formula from the top-level orchestrator and sector constraints.
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MomentumCache, VolatilityCache
from app.services.rd_alpha_scorer.data_classes import (
    RDAlphaScore,
    SP500_SECTOR_WEIGHTS,
    SECTOR_RD_CAPS,
)

logger = logging.getLogger(__name__)


class ScoringMixin:
    """
    Mixin that provides per-company scoring methods.

    Expects the consumer class to define:
        self.session: AsyncSession
        self.momentum_calculator: MomentumCalculator  (lazy property)
        self.volatility_calculator: VolatilityCalculator  (lazy property)
        MIN_MOMENTUM_FACTOR, MAX_MOMENTUM_FACTOR, DEFAULT_VOLATILITY, VOLATILITY_FLOOR: class attrs
    """

    async def _calculate_company_score(
        self,
        company,
        high_rd_sector_weights: Dict[str, float],
        as_of_year: Optional[int] = None,
        pit_financials: Optional[Dict] = None,
    ) -> Optional[RDAlphaScore]:
        """
        Calculate score for a single company.

        Args:
            company: ResearchCohort record with company metadata
            high_rd_sector_weights: Sector representation in eligible universe
            as_of_year: Year for point-in-time scoring
            pit_financials: Point-in-time FY(T-1) financials dict with:
                - rd_intensity_pct: R&D/Revenue * 100
                - revenue: FY(T-1) revenue
                - rd_expenses: FY(T-1) R&D expenses
                - fiscal_year: The fiscal year used
        """
        sector = company.sector or "Unknown"

        # 1. R&D Intensity (capped by sector)
        # POINT-IN-TIME: Use FY(T-1) financials when available, else cohort average
        if pit_financials:
            rd_intensity = float(pit_financials["rd_intensity_pct"])
            data_source = "point_in_time"
            fiscal_year_used = pit_financials.get("fiscal_year")
            latest_revenue = pit_financials.get("revenue", 0.0)
            latest_rd_expense = pit_financials.get("rd_expenses", 0.0)
        else:
            rd_intensity = float(company.avg_rd_intensity) if company.avg_rd_intensity else 0.0
            data_source = "cohort_avg"
            fiscal_year_used = None
            latest_revenue = 0.0
            latest_rd_expense = 0.0

        sector_cap = SECTOR_RD_CAPS.get(sector, SECTOR_RD_CAPS["default"])
        rd_intensity_capped = min(rd_intensity / 100.0, sector_cap)  # Convert from % to ratio

        if rd_intensity_capped <= 0:
            return None

        # 2. Sector Adjustment Factor
        # Penalizes sectors that are overrepresented in high-R&D universe
        sp500_weight = SP500_SECTOR_WEIGHTS.get(sector, 0.05)  # Default 5%
        high_rd_weight = high_rd_sector_weights.get(sector, 0.10)  # Default 10%

        # Adjustment: sectors overrepresented get lower adjustment
        # Tech is ~30% of S&P but ~50% of high-R&D, so adjustment = 0.30/0.50 = 0.6
        sector_adjustment = min(sp500_weight / max(high_rd_weight, 0.01), 2.0)

        # 3. Momentum Factor (from Paper 3 - Pricing Factor research)
        # Uses real 3-year excess returns vs benchmark (already point-in-time)
        momentum_factor = await self._get_real_momentum(
            company.symbol,
            as_of_year or datetime.now().year
        )

        # 4. Quality Score (existing metric)
        quality_score = float(company.data_quality_score or 50) / 100.0

        # 5. Volatility (from Paper 4 - Value Creation research)
        # Uses real 3-year historical volatility from daily prices (already point-in-time)
        volatility = await self._get_real_volatility(
            company.symbol,
            as_of_year or datetime.now().year
        )

        # Calculate raw score
        raw_score = (
            rd_intensity_capped *
            sector_adjustment *
            momentum_factor *
            quality_score
        ) / volatility

        return RDAlphaScore(
            symbol=company.symbol,
            name=company.name or company.symbol,
            sector=sector,
            industry=None,
            rd_intensity=rd_intensity,
            rd_intensity_capped=rd_intensity_capped * 100,  # Back to percentage for display
            sector_adjustment=sector_adjustment,
            momentum_factor=momentum_factor,
            quality_score=quality_score,
            volatility=volatility,
            raw_score=raw_score,
            final_score=raw_score,  # Will be adjusted in apply_sector_constraints
            weight=0.0,
            selection_rank=0,
            years_of_data=company.years_with_data or 0,
            latest_revenue=latest_revenue,
            latest_rd_expense=latest_rd_expense,
            fiscal_year_used=fiscal_year_used,
            data_source=data_source,
        )

    async def _get_real_momentum(
        self,
        symbol: str,
        as_of_year: int
    ) -> float:
        """
        Get real momentum factor from cached or computed data.

        Uses 3-year prior excess returns vs benchmark (Paper 3 research).
        Falls back to neutral (1.0) if no data available.
        """
        try:
            # Try to get from cache first
            cached = await self.session.execute(
                select(MomentumCache.momentum_factor)
                .where(
                    MomentumCache.symbol == symbol,
                    MomentumCache.as_of_year == as_of_year
                )
            )
            result = cached.scalar_one_or_none()

            if result is not None:
                return max(self.MIN_MOMENTUM_FACTOR, min(self.MAX_MOMENTUM_FACTOR, result))

            # Compute on-the-fly if not cached
            momentum = await self.momentum_calculator.compute_momentum(symbol, as_of_year)
            if momentum:
                return momentum.momentum_factor

        except Exception as e:
            logger.debug(f"Error getting momentum for {symbol}: {e}")

        # Return neutral if no data
        return 1.0

    async def _get_real_volatility(
        self,
        symbol: str,
        as_of_year: int
    ) -> float:
        """
        Get real volatility from cached or computed data.

        Uses 3-year trailing daily returns (Paper 4 research).
        Falls back to default (0.25) if no data available.
        """
        try:
            # Try to get from cache first
            cached = await self.session.execute(
                select(VolatilityCache.volatility_3yr)
                .where(
                    VolatilityCache.symbol == symbol,
                    VolatilityCache.as_of_year == as_of_year
                )
            )
            result = cached.scalar_one_or_none()

            if result is not None:
                return max(self.VOLATILITY_FLOOR, result)

            # Compute on-the-fly if not cached
            vol = await self.volatility_calculator.compute_volatility(symbol, as_of_year)
            if vol:
                return vol.volatility_3yr

        except Exception as e:
            logger.debug(f"Error getting volatility for {symbol}: {e}")

        # Return default if no data
        return self.DEFAULT_VOLATILITY
