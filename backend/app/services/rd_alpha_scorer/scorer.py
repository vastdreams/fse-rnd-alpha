"""
PATH: backend/app/services/rd_alpha_scorer/scorer.py
PURPOSE: Main RDAlphaScorer class composing ScoringMixin + ConstraintsMixin.
WHY: Keeps the top-level orchestrator (calculate_alpha_scores) small while mixins handle concerns.

ROLE IN ARCHITECTURE:
  - Core scoring service for ETF portfolio construction
  - Used by portfolio_optimizer.py and portfolio API endpoints
  - Works with etf_universe.py for point-in-time eligibility

POINT-IN-TIME RULES (Dec 2025 Update):
  - For backtests, use FY(T-1) financials for R&D intensity (not avg_rd_intensity)
  - Formation date is July 1 of as_of_year (Fama-French convention)
  - ETFUniverseBuilder handles eligibility gates; scorer only scores eligible symbols
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchCohort, FMPIncomeStatement
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE
from app.services.momentum_service import MomentumCalculator
from app.services.volatility_service import VolatilityCalculator
from app.services.etf_universe import ETFUniverseBuilder, EligibilityResult
from app.core.logging import get_logger
from app.core.formulas import validate_formula_output

from app.services.rd_alpha_scorer.data_classes import RDAlphaScore
from app.services.rd_alpha_scorer.scoring_mixin import ScoringMixin
from app.services.rd_alpha_scorer.constraints_mixin import ConstraintsMixin

logger = get_logger(__name__)


class RDAlphaScorer(ScoringMixin, ConstraintsMixin):
    """
    Research-based scoring engine for R&D Alpha ETF selection.

    Formula:
    R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility

    Where:
    - RD_Intensity = min(R&D/Revenue, Sector_Cap)
    - Sector_Adj = SP500_Sector_Weight / HighRD_Sector_Weight
    - Momentum = 1 + (Prior_3yr_Excess_Return × 0.1)
    - Quality = Data_Quality_Score / 100
    - Volatility = Historical_3yr_StdDev (floored at 0.10)
    """

    # Portfolio constraints
    MAX_SECTOR_WEIGHT = 0.25       # No sector > 25%
    MIN_SECTOR_WEIGHT = 0.02       # At least 2% per included sector
    MIN_COMPANIES_PER_SECTOR = 1   # At least 1 company per included sector
    DEFAULT_VOLATILITY = 0.25      # Default if no volatility data
    VOLATILITY_FLOOR = 0.10       # Minimum volatility to prevent extreme scores

    # Momentum bounds (from Paper 3)
    MIN_MOMENTUM_FACTOR = 0.5
    MAX_MOMENTUM_FACTOR = 2.0

    def __init__(self, session: AsyncSession):
        self.session = session
        self._momentum_calculator: Optional[MomentumCalculator] = None
        self._volatility_calculator: Optional[VolatilityCalculator] = None

    @property
    def momentum_calculator(self) -> MomentumCalculator:
        """Lazy initialization of momentum calculator."""
        if self._momentum_calculator is None:
            self._momentum_calculator = MomentumCalculator(self.session)
        return self._momentum_calculator

    @property
    def volatility_calculator(self) -> VolatilityCalculator:
        """Lazy initialization of volatility calculator."""
        if self._volatility_calculator is None:
            self._volatility_calculator = VolatilityCalculator(self.session)
        return self._volatility_calculator

    async def calculate_alpha_scores(
        self,
        universe: str = "sp500",
        as_of_year: Optional[int] = None,
        min_years_data: int = 3,
        min_revenue: float = MIN_REVENUE_THRESHOLD,
        strict_point_in_time: bool = False,
        eligible_symbols: Optional[List[str]] = None,
    ) -> Tuple[List[RDAlphaScore], Optional[EligibilityResult]]:
        """
        Calculate R&D Alpha scores for all eligible companies.

        Args:
            universe: "sp500", "russell1000", or "russell3000"
            as_of_year: Point-in-time year for selection (None = latest)
            min_years_data: Minimum years of R&D data required
            min_revenue: Minimum revenue threshold
            strict_point_in_time: If True, fail if point-in-time data unavailable
            eligible_symbols: Pre-computed eligible symbols (bypasses universe builder)

        Returns:
            Tuple of (List of RDAlphaScore objects sorted by final_score, EligibilityResult or None)

        POINT-IN-TIME RULES (Dec 2025):
            When as_of_year is provided:
            - Uses ETFUniverseBuilder for eligibility (anti-lookahead gates)
            - R&D intensity computed from FY(T-1) financials, not avg_rd_intensity
            - Momentum/volatility computed point-in-time (already correct)
        """
        start_time = time.perf_counter()

        logger.log_step(
            "Calculate R&D Alpha Scores",
            step_number=1,
            total_steps=4,
            data={"universe": universe, "as_of_year": as_of_year, "strict_pit": strict_point_in_time}
        )

        eligibility_result: Optional[EligibilityResult] = None
        point_in_time_financials: Dict[str, Dict] = {}

        # -------------------------------------------------------------------------
        # Step 1: Determine eligible universe
        # -------------------------------------------------------------------------
        if as_of_year is not None and eligible_symbols is None:
            universe_builder = ETFUniverseBuilder(self.session)
            eligibility_result = await universe_builder.build_eligible_universe(
                as_of_year=as_of_year,
                min_revenue=min_revenue,
                require_risk_data=False,
            )

            if not eligibility_result.eligible_symbols:
                logger.warning(f"No eligible symbols for {as_of_year}")
                return [], eligibility_result

            logger.log_step(
                f"Universe eligibility determined: {eligibility_result.mode.value}",
                step_number=2,
                total_steps=4,
                data={
                    "mode": eligibility_result.mode.value,
                    "eligible_count": len(eligibility_result.eligible_symbols),
                    "gates": eligibility_result.gates_applied,
                }
            )

            eligible_symbols = eligibility_result.eligible_symbols

        # -------------------------------------------------------------------------
        # Step 2: Get point-in-time FY(T-1) financials for R&D intensity
        # -------------------------------------------------------------------------
        if as_of_year is not None:
            data_year = as_of_year - 1

            if eligible_symbols:
                fin_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.revenue,
                        FMPIncomeStatement.rd_expenses,
                    ).where(
                        FMPIncomeStatement.symbol.in_(eligible_symbols),
                        FMPIncomeStatement.fiscal_year == data_year,
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

                for row in fin_result.fetchall():
                    symbol, revenue, rd_expenses = row
                    if symbol and revenue and rd_expenses and revenue > 0:
                        rd_intensity_pct = (rd_expenses / revenue) * 100.0
                        rd_intensity_pct = min(rd_intensity_pct, MAX_RD_INTENSITY_ABSOLUTE)
                        point_in_time_financials[symbol] = {
                            "rd_intensity_pct": rd_intensity_pct,
                            "revenue": float(revenue),
                            "rd_expenses": float(rd_expenses),
                            "fiscal_year": data_year,
                        }

                logger.info(f"Point-in-time FY{data_year} financials: {len(point_in_time_financials)}/{len(eligible_symbols)} symbols")

                eligible_symbols = [s for s in eligible_symbols if s in point_in_time_financials]

        # -------------------------------------------------------------------------
        # Step 3: Get company metadata from research cohort
        # -------------------------------------------------------------------------
        query = select(ResearchCohort).where(
            ResearchCohort.years_with_data >= min_years_data,
            ResearchCohort.avg_rd_intensity > 0
        )

        if eligible_symbols:
            query = query.where(ResearchCohort.symbol.in_(eligible_symbols))

        result = await self.session.execute(query)
        cohort_companies = result.scalars().all()

        logger.log_db_query(
            operation="SELECT",
            table="research_cohort",
            rows_affected=len(cohort_companies),
            duration_ms=(time.perf_counter() - start_time) * 1000
        )

        # Calculate sector representation in eligible universe
        sector_counts: Dict[str, int] = {}
        for c in cohort_companies:
            sector = c.sector or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        total_companies = len(cohort_companies)
        high_rd_sector_weights = {
            s: count / total_companies
            for s, count in sector_counts.items()
        } if total_companies > 0 else {}

        # -------------------------------------------------------------------------
        # Step 4: Calculate scores
        # -------------------------------------------------------------------------
        scores: List[RDAlphaScore] = []

        for company in cohort_companies:
            pit_fin = point_in_time_financials.get(company.symbol) if as_of_year else None

            score = await self._calculate_company_score(
                company=company,
                high_rd_sector_weights=high_rd_sector_weights,
                as_of_year=as_of_year,
                pit_financials=pit_fin,
            )
            if score:
                scores.append(score)

        # Sort by final score descending
        scores.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks
        for i, score in enumerate(scores):
            score.selection_rank = i + 1

        logger.log_step(
            "Scores calculated and ranked",
            step_number=4,
            total_steps=4,
            data={
                "total_scored": len(scores),
                "top_score": scores[0].final_score if scores else 0,
                "sectors_represented": len(set(s.sector for s in scores)),
                "point_in_time_coverage": len(point_in_time_financials) if as_of_year else None,
            },
            duration_ms=(time.perf_counter() - start_time) * 1000
        )

        return scores, eligibility_result
