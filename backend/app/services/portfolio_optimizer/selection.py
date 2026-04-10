"""
PATH: research/backend/app/services/portfolio_optimizer/selection.py
PURPOSE: Company selection logic for R&D-focused portfolio construction
WHY: Isolates the multiple selection strategies (quality_adjusted, highest_rd, balanced, rd_alpha)
DEPENDENCIES:
  - app.db.models: ORM models for company/financial data
  - app.services.sanity_checks: R&D intensity capping
  - .models: shared dataclasses and constants
"""

import logging
from typing import List, Dict, Optional, Tuple

from sqlalchemy import select, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ResearchCohort, FMPIncomeStatement, SP500Company,
)
from app.services.sanity_checks import cap_rd_intensity

from .models import PortfolioHolding, MIN_REVENUE, MAX_RD_INTENSITY

logger = logging.getLogger(__name__)


class SelectionMixin:
    """
    Mixin providing company selection methods for PortfolioOptimizer.

    Expects the composing class to set:
      - self.session: AsyncSession
    """

    session: AsyncSession  # set by PortfolioOptimizer.__init__

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
        - "rd_alpha": Research-based sector-agnostic scoring (recommended)
        - "pnl_efficiency": PNL operating efficiency scoring
        """
        if method == "rd_alpha":
            holdings, _ = await self._select_with_rd_alpha_scorer(n=n, as_of_year=None)
            return holdings

        if method == "pnl_efficiency":
            holdings, _ = await self._select_with_pnl_efficiency_scorer(n=n, as_of_year=None)
            return holdings

        query = select(ResearchCohort).where(
            ResearchCohort.years_with_data >= min_years,
            ResearchCohort.avg_rd_intensity > 0
        )

        if sectors:
            query = query.where(ResearchCohort.sector.in_(sectors))

        if method == "quality_adjusted":
            query = query.order_by(
                desc(ResearchCohort.avg_rd_intensity * ResearchCohort.data_quality_score / 100.0)
            )
        elif method == "highest_rd":
            query = query.order_by(desc(ResearchCohort.avg_rd_intensity))
        elif method == "balanced":
            query = query.order_by(desc(ResearchCohort.avg_rd_intensity))

        query = query.limit(n * 2 if method == "balanced" else n)

        result = await self.session.execute(query)
        companies = result.scalars().all()

        if method == "balanced":
            companies = self._balance_by_sector(companies, n)
        else:
            companies = companies[:n]

        total_companies = len(companies)
        holdings = []

        for c in companies:
            holdings.append(PortfolioHolding(
                symbol=c.symbol,
                name=c.name or c.symbol,
                sector=c.sector or "Unknown",
                weight=1.0 / total_companies,
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
        Select companies using the R&D Alpha scoring engine.

        Uses sector-agnostic weighting to prevent tech/biotech overconcentration,
        applies research-based selection formula, and integrates findings from Papers 1-4.

        Returns:
            Tuple of (holdings list, eligibility metadata dict or None)
        """
        from app.services.rd_alpha_scorer import RDAlphaScorer

        scorer = RDAlphaScorer(self.session)

        all_scores, eligibility_result = await scorer.calculate_alpha_scores(
            universe="sp500",
            as_of_year=as_of_year
        )

        selected, _ = await scorer.apply_sector_constraints(all_scores, n_holdings=n)

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

        Provides point-in-time holdings, selecting companies that were
        the top R&D spenders at that particular point in history.

        IMPORTANT: Uses FY(as_of_year - 1) data to avoid look-ahead bias.

        Filters applied:
        - Minimum revenue: $100M (prevents extreme ratios from pre-revenue companies)
        - R&D intensity capped at 100% (prevents outliers)
        """
        if method == "rd_alpha":
            holdings, _ = await self._select_with_rd_alpha_scorer(n=n, as_of_year=as_of_year)
            return holdings

        if method == "pnl_efficiency":
            holdings, _ = await self._select_with_pnl_efficiency_scorer(n=n, as_of_year=as_of_year)
            return holdings

        # Use PRIOR year's financial data to avoid look-ahead bias
        data_year = as_of_year - 1

        raw_intensity = FMPIncomeStatement.rd_expenses / FMPIncomeStatement.revenue * 100

        subq = (
            select(
                FMPIncomeStatement.symbol,
                case(
                    (raw_intensity > MAX_RD_INTENSITY, MAX_RD_INTENSITY),
                    else_=raw_intensity
                ).label("rd_intensity"),
                FMPIncomeStatement.revenue
            )
            .where(
                FMPIncomeStatement.fiscal_year == data_year,
                FMPIncomeStatement.revenue >= MIN_REVENUE,
                FMPIncomeStatement.rd_expenses > 0
            )
        ).subquery()

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

        query = query.order_by(desc(subq.c.rd_intensity)).limit(n)

        result = await self.session.execute(query)
        rows = result.fetchall()

        if not rows:
            logger.warning(f"No income statement data for year {data_year}, using ResearchCohort fallback")
            return await self.select_top_rd_companies(n=n, method=method, sectors=sectors)

        total_companies = len(rows)
        holdings = []

        for row in rows:
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


    async def _select_with_pnl_efficiency_scorer(
        self,
        n: int = 20,
        as_of_year: Optional[int] = None,
    ) -> Tuple[List[PortfolioHolding], Optional[Dict]]:
        """Select companies using PNL Efficiency scoring engine."""
        from app.services.pnl_efficiency_scorer import PnlEfficiencyScorer

        scorer = PnlEfficiencyScorer(self.session)
        all_scores = await scorer.calculate_scores(as_of_year=as_of_year)
        selected = await scorer.apply_sector_constraints(all_scores, n_holdings=n)

        holdings = []
        for score in selected:
            holdings.append(PortfolioHolding(
                symbol=score.symbol,
                name=score.name,
                sector=score.sector,
                weight=score.weight,
                rd_intensity=0.0,
                quality_score=score.sector_percentile,
            ))

        return holdings, None

    def _balance_by_sector(
        self,
        companies: List[ResearchCohort],
        n: int
    ) -> List[ResearchCohort]:
        """Select top companies while ensuring sector diversity."""
        sector_counts: Dict[str, int] = {}
        max_per_sector = max(2, n // 5)
        selected = []

        for c in companies:
            sector = c.sector or "Unknown"
            if sector_counts.get(sector, 0) < max_per_sector:
                selected.append(c)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if len(selected) >= n:
                break

        return selected
