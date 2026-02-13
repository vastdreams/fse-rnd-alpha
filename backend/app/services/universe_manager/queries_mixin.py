"""
PATH: backend/app/services/universe_manager/queries_mixin.py
PURPOSE: Private DB query helpers for counting and listing universe members
WHY: Isolates raw SQL queries from business logic in manager.py
FLOW:
  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐
  │ AsyncSession │ →  │ Query helper │ →  │ int / List[str]   │
  └──────────────┘    └──────────────┘    └───────────────────┘
DEPENDENCIES:
  - sqlalchemy: async DB queries
  - app.db.models: ORM models
RELATED:
  - manager.py: uses this mixin for data access
"""

import logging
from typing import List, Dict

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SP500Company, ResearchCohort, FMPIncomeStatement

logger = logging.getLogger(__name__)


class UniverseQueriesMixin:
    """
    Mixin providing private DB query methods for UniverseManager.

    Requires self.session: AsyncSession from the concrete class.
    """

    session: AsyncSession  # provided by the concrete class

    async def _count_sp500_companies(self) -> int:
        """Count S&P 500 companies in database."""
        result = await self.session.execute(
            select(func.count(SP500Company.symbol))
        )
        return result.scalar() or 0

    async def _count_sp500_with_rd(self) -> int:
        """Count S&P 500 companies with R&D data."""
        result = await self.session.execute(
            select(func.count(distinct(ResearchCohort.symbol))).where(
                ResearchCohort.avg_rd_intensity > 0
            )
        )
        return result.scalar() or 0

    async def _count_all_companies(self) -> int:
        """Count all companies with financial data."""
        result = await self.session.execute(
            select(func.count(distinct(FMPIncomeStatement.symbol)))
        )
        return result.scalar() or 0

    async def _count_all_with_rd(self) -> int:
        """Count all companies with R&D data."""
        result = await self.session.execute(
            select(func.count(distinct(FMPIncomeStatement.symbol))).where(
                FMPIncomeStatement.rd_expenses > 0
            )
        )
        return result.scalar() or 0

    async def _get_sp500_symbols(self, with_rd_only: bool) -> List[str]:
        """Get S&P 500 company symbols."""
        if with_rd_only:
            # Join with research cohort
            result = await self.session.execute(
                select(ResearchCohort.symbol).where(
                    ResearchCohort.avg_rd_intensity > 0
                )
            )
        else:
            result = await self.session.execute(
                select(SP500Company.symbol)
            )
        return [row[0] for row in result.fetchall()]

    async def _get_all_symbols(self, with_rd_only: bool) -> List[str]:
        """Get all company symbols."""
        if with_rd_only:
            result = await self.session.execute(
                select(distinct(FMPIncomeStatement.symbol)).where(
                    FMPIncomeStatement.rd_expenses > 0
                )
            )
        else:
            result = await self.session.execute(
                select(distinct(FMPIncomeStatement.symbol))
            )
        return [row[0] for row in result.fetchall()]

    async def _get_sp500_sector_counts(self) -> Dict[str, Dict[str, int]]:
        """Get sector counts for S&P 500."""
        # Total by sector
        total_result = await self.session.execute(
            select(
                SP500Company.sector,
                func.count(SP500Company.symbol)
            ).group_by(SP500Company.sector)
        )
        totals = {row[0]: {"total": row[1], "with_rd": 0} for row in total_result.fetchall()}
        
        # With R&D data
        rd_result = await self.session.execute(
            select(
                ResearchCohort.sector,
                func.count(ResearchCohort.symbol)
            ).where(
                ResearchCohort.avg_rd_intensity > 0
            ).group_by(ResearchCohort.sector)
        )
        
        for row in rd_result.fetchall():
            sector = row[0]
            if sector in totals:
                totals[sector]["with_rd"] = row[1]
            else:
                totals[sector] = {"total": row[1], "with_rd": row[1]}
        
        return totals

    async def _get_all_sector_counts(self) -> Dict[str, Dict[str, int]]:
        """Get sector counts for all companies."""
        # Use research cohort for consistent sector data
        result = await self.session.execute(
            select(
                ResearchCohort.sector,
                func.count(ResearchCohort.symbol)
            ).group_by(ResearchCohort.sector)
        )
        
        return {
            row[0]: {"total": row[1], "with_rd": row[1]} 
            for row in result.fetchall()
        }
