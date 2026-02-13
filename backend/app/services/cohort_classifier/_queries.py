# Query mixin: cohort retrieval and summary statistics.
import logging
from typing import Dict, List
from sqlalchemy import select, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchCohort

logger = logging.getLogger(__name__)


class QueryMixin:
    """Mixin providing cohort query and summary methods."""

    session: AsyncSession

    async def get_cohort_by_window(self, window_type: str) -> List[Dict]:
        """Get companies eligible for a specific window type: '5yr', '10yr', or '20yr'."""
        column_map = {
            "5yr": ResearchCohort.has_5yr_window,
            "10yr": ResearchCohort.has_10yr_window,
            "20yr": ResearchCohort.has_20yr_window
        }
        if window_type not in column_map:
            raise ValueError(f"Invalid window type: {window_type}")
        result = await self.session.execute(
            select(ResearchCohort)
            .where(column_map[window_type] == True)
            .order_by(ResearchCohort.avg_rd_intensity.desc())
        )
        companies = result.scalars().all()
        return [
            {
                "symbol": c.symbol,
                "name": c.name,
                "sector": c.sector,
                "years_with_data": c.years_with_data,
                "years_with_rd": c.years_with_rd,
                "first_year": c.first_year,
                "last_year": c.last_year,
                "avg_rd_intensity": c.avg_rd_intensity,
                "rd_profile": c.rd_profile,
                "data_quality_score": c.data_quality_score
            }
            for c in companies
        ]

    async def get_cohort_summary(self) -> Dict:
        """Get summary statistics for the research cohort."""
        result = await self.session.execute(
            select(
                func.count(ResearchCohort.symbol).label("total"),
                func.sum(func.cast(ResearchCohort.has_5yr_window, Integer)).label("n_5yr"),
                func.sum(func.cast(ResearchCohort.has_10yr_window, Integer)).label("n_10yr"),
                func.sum(func.cast(ResearchCohort.has_20yr_window, Integer)).label("n_20yr"),
                func.avg(ResearchCohort.avg_rd_intensity).label("avg_rd_intensity"),
                func.avg(ResearchCohort.data_quality_score).label("avg_quality")
            )
        )
        row = result.fetchone()
        sector_result = await self.session.execute(
            select(
                ResearchCohort.sector,
                func.count(ResearchCohort.symbol).label("count"),
                func.sum(func.cast(ResearchCohort.has_5yr_window, Integer)).label("n_5yr"),
                func.sum(func.cast(ResearchCohort.has_10yr_window, Integer)).label("n_10yr"),
                func.sum(func.cast(ResearchCohort.has_20yr_window, Integer)).label("n_20yr")
            )
            .group_by(ResearchCohort.sector)
            .order_by(func.count(ResearchCohort.symbol).desc())
        )
        sectors = [
            {
                "sector": r.sector,
                "total": r.count,
                "n_5yr": r.n_5yr or 0,
                "n_10yr": r.n_10yr or 0,
                "n_20yr": r.n_20yr or 0
            }
            for r in sector_result.fetchall()
        ]
        profile_result = await self.session.execute(
            select(
                ResearchCohort.rd_profile,
                func.count(ResearchCohort.symbol).label("count")
            )
            .group_by(ResearchCohort.rd_profile)
        )
        profiles = {r.rd_profile: r.count for r in profile_result.fetchall()}
        return {
            "total_companies": row.total or 0,
            "eligible_5yr": row.n_5yr or 0,
            "eligible_10yr": row.n_10yr or 0,
            "eligible_20yr": row.n_20yr or 0,
            "avg_rd_intensity": round(row.avg_rd_intensity or 0, 2),
            "avg_quality_score": round(row.avg_quality or 0, 1),
            "by_sector": sectors,
            "by_rd_profile": profiles
        }
