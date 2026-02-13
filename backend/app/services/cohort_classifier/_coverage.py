# Coverage analysis mixin: data availability checks per company.
import logging
from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FMPIncomeStatement, FMPAnnualReturn

logger = logging.getLogger(__name__)


class CoverageAnalysisMixin:
    """Mixin providing per-company data coverage analysis and quality scoring."""

    session: AsyncSession

    async def get_company_data_coverage(self, symbol: str) -> Dict:
        """Analyze data coverage for a single company.
        Returns years with income/R&D/returns, consecutive windows, avg_rd_intensity, total_rd_spend.
        """
        income_result = await self.session.execute(
            select(
                FMPIncomeStatement.fiscal_year,
                FMPIncomeStatement.rd_expenses,
                FMPIncomeStatement.revenue
            )
            .where(FMPIncomeStatement.symbol == symbol)
            .where(FMPIncomeStatement.period == "FY")
            .order_by(FMPIncomeStatement.fiscal_year)
        )
        income_rows = income_result.fetchall()
        return_result = await self.session.execute(
            select(FMPAnnualReturn.year)
            .where(FMPAnnualReturn.symbol == symbol)
            .order_by(FMPAnnualReturn.year)
        )
        return_years = set(r.year for r in return_result.fetchall())
        if not income_rows:
            return {
                "symbol": symbol,
                "years_with_income": 0,
                "years_with_rd": 0,
                "years_with_returns": len(return_years),
                "first_year": None,
                "last_year": None,
                "consecutive_windows": {5: False, 10: False, 20: False},
                "avg_rd_intensity": 0,
                "total_rd_spend": 0
            }
        years_with_rd = []
        rd_intensities = []
        total_rd = 0
        for row in income_rows:
            if row.rd_expenses and row.rd_expenses > 0:
                years_with_rd.append(row.fiscal_year)
                total_rd += row.rd_expenses
                if row.revenue and row.revenue > 0:
                    rd_intensities.append(row.rd_expenses / row.revenue * 100)
        all_years = [r.fiscal_year for r in income_rows]
        first_year = min(all_years) if all_years else None
        last_year = max(all_years) if all_years else None
        complete_years = sorted(set(years_with_rd) & return_years)
        consecutive_windows = self._check_consecutive_windows(complete_years)
        avg_rd_intensity = sum(rd_intensities) / len(rd_intensities) if rd_intensities else 0
        return {
            "symbol": symbol,
            "years_with_income": len(all_years),
            "years_with_rd": len(years_with_rd),
            "years_with_returns": len(return_years),
            "complete_years": len(complete_years),
            "first_year": first_year,
            "last_year": last_year,
            "consecutive_windows": consecutive_windows,
            "avg_rd_intensity": avg_rd_intensity,
            "total_rd_spend": total_rd
        }

    def _check_consecutive_windows(self, years: List[int]) -> Dict[int, bool]:
        """Check if there are consecutive year runs of 5, 10, and 20 years."""
        if not years:
            return {5: False, 10: False, 20: False}
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(years)):
            if years[i] == years[i-1] + 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        return {
            5: max_consecutive >= 5,
            10: max_consecutive >= 10,
            20: max_consecutive >= 20
        }

    def _calculate_rd_profile(self, avg_rd_intensity: float) -> str:
        """Classify R&D profile based on intensity: High (>=10%), Medium (>=3%), Low."""
        if avg_rd_intensity >= 10:
            return "High"
        elif avg_rd_intensity >= 3:
            return "Medium"
        else:
            return "Low"

    def _calculate_quality_score(self, coverage: Dict) -> float:
        """Calculate data quality score (0-100) based on coverage and window eligibility."""
        score = 0
        score += min(coverage["years_with_income"] * 1.0, 30)
        score += min(coverage["years_with_rd"] * 1.0, 30)
        score += min(coverage.get("complete_years", 0) * 1.5, 30)
        windows = coverage["consecutive_windows"]
        if windows.get(20):
            score += 10
        elif windows.get(10):
            score += 6
        elif windows.get(5):
            score += 3
        return min(score, 100)
