# Classification mixin: batch classification of companies into research cohorts.
import logging
from typing import Dict
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SP500Company, ResearchCohort

logger = logging.getLogger(__name__)


class ClassificationMixin:
    """Mixin providing batch classification of companies into rolling window cohorts."""

    session: AsyncSession

    async def classify_all_companies(self) -> Dict:
        """Classify companies into research cohorts and populate research_cohort table.
        Survivorship-bias-free: uses historical S&P 500 constituents if available.
        """
        from app.db.models import SP500HistoricalConstituent, Company

        hist_result = await self.session.execute(
            select(func.distinct(SP500HistoricalConstituent.symbol))
        )
        hist_symbols = [r[0] for r in hist_result.fetchall()]

        if hist_symbols:
            logger.info(f"Using {len(hist_symbols)} historical S&P 500 constituents for analysis")
            result = await self.session.execute(
                select(Company).where(Company.ticker.in_(hist_symbols))
            )
            companies = result.scalars().all()
            curr_result = await self.session.execute(select(SP500Company))
            curr_companies = curr_result.scalars().all()
            seen_tickers = {c.ticker for c in companies}
            for cc in curr_companies:
                if cc.symbol not in seen_tickers:
                    class MockCompany:
                        def __init__(self, ticker, name, sector, sub_sector):
                            self.symbol = ticker
                            self.name = name
                            self.sector = sector
                            self.sub_sector = sub_sector
                    companies.append(MockCompany(cc.symbol, cc.name, cc.sector, cc.sub_sector))
                    seen_tickers.add(cc.symbol)
        else:
            logger.info("Historical constituents table empty, falling back to current S&P 500")
            result = await self.session.execute(select(SP500Company))
            companies = result.scalars().all()

        logger.info(f"Classifying {len(companies)} total companies")
        cohort_5yr = []
        cohort_10yr = []
        cohort_20yr = []
        excluded = []

        for company in companies:
            coverage = await self.get_company_data_coverage(company.symbol)
            rd_profile = self._calculate_rd_profile(coverage["avg_rd_intensity"])
            quality_score = self._calculate_quality_score(coverage)
            cohort_record = ResearchCohort(
                symbol=company.symbol,
                name=company.name,
                sector=company.sector,
                industry=company.sub_sector,
                years_with_data=coverage["years_with_income"],
                years_with_rd=coverage["years_with_rd"],
                first_year=coverage["first_year"],
                last_year=coverage["last_year"],
                has_5yr_window=coverage["consecutive_windows"][5],
                has_10yr_window=coverage["consecutive_windows"][10],
                has_20yr_window=coverage["consecutive_windows"][20],
                avg_rd_intensity=coverage["avg_rd_intensity"],
                total_rd_spend=coverage["total_rd_spend"],
                rd_profile=rd_profile,
                data_quality_score=quality_score,
                has_price_data=coverage["years_with_returns"] > 0,
                has_return_data=coverage["years_with_returns"] > 0,
                updated_at=datetime.utcnow()
            )
            await self.session.merge(cohort_record)
            if coverage["consecutive_windows"][20]:
                cohort_20yr.append(company.symbol)
            if coverage["consecutive_windows"][10]:
                cohort_10yr.append(company.symbol)
            if coverage["consecutive_windows"][5]:
                cohort_5yr.append(company.symbol)
            if not coverage["consecutive_windows"][5]:
                excluded.append(company.symbol)

        await self.session.commit()
        summary = {
            "total_companies": len(companies),
            "cohort_5yr": len(cohort_5yr),
            "cohort_10yr": len(cohort_10yr),
            "cohort_20yr": len(cohort_20yr),
            "excluded": len(excluded),
            "symbols_5yr": cohort_5yr,
            "symbols_10yr": cohort_10yr,
            "symbols_20yr": cohort_20yr,
            "symbols_excluded": excluded
        }
        logger.info(f"Classification complete: 5yr={len(cohort_5yr)}, 10yr={len(cohort_10yr)}, 20yr={len(cohort_20yr)}")
        return summary
