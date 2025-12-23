"""
PATH: backend/app/services/cohort_classifier.py
PURPOSE:
  - Classify 500 companies into rolling window cohorts
  - Determine eligibility for 5/10/20-year analysis windows
  - Compute data quality scores
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    SP500Company, FMPIncomeStatement, FMPAnnualReturn, 
    ResearchCohort
)

logger = logging.getLogger(__name__)


class CohortClassifier:
    """
    Classifies companies into research cohorts based on data availability.
    
    Window Requirements:
    - 5-year window: At least 5 consecutive years of R&D and return data
    - 10-year window: At least 10 consecutive years
    - 20-year window: At least 20 consecutive years
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_company_data_coverage(self, symbol: str) -> Dict:
        """
        Analyze data coverage for a single company.
        
        Returns:
            {
                "symbol": str,
                "years_with_income": int,
                "years_with_rd": int,
                "years_with_returns": int,
                "first_year": int,
                "last_year": int,
                "consecutive_windows": {5: bool, 10: bool, 20: bool},
                "avg_rd_intensity": float,
                "total_rd_spend": float
            }
        """
        # Get income statement years with R&D data
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
        
        # Get return years
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
        
        # Calculate R&D metrics
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
        
        # Find years with BOTH R&D data AND return data
        complete_years = sorted(set(years_with_rd) & return_years)
        
        # Check for consecutive windows
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
        """
        Check if there are consecutive year runs of 5, 10, and 20 years.
        """
        if not years:
            return {5: False, 10: False, 20: False}
        
        # Find longest consecutive run
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
        """Classify R&D profile based on intensity."""
        if avg_rd_intensity >= 10:
            return "High"
        elif avg_rd_intensity >= 3:
            return "Medium"
        else:
            return "Low"
    
    def _calculate_quality_score(self, coverage: Dict) -> float:
        """
        Calculate data quality score (0-100) based on:
        - Years of data coverage
        - R&D data completeness
        - Return data availability
        """
        score = 0
        
        # Years with income data (max 30 points)
        score += min(coverage["years_with_income"] * 1.0, 30)
        
        # Years with R&D data (max 30 points)
        score += min(coverage["years_with_rd"] * 1.0, 30)
        
        # Complete years (R&D + returns) (max 30 points)
        score += min(coverage.get("complete_years", 0) * 1.5, 30)
        
        # Window eligibility bonus (max 10 points)
        windows = coverage["consecutive_windows"]
        if windows.get(20):
            score += 10
        elif windows.get(10):
            score += 6
        elif windows.get(5):
            score += 3
        
        return min(score, 100)
    
    async def classify_all_companies(self) -> Dict:
        """
        Classify companies into research cohorts and populate research_cohort table.
        
        Survivorship-Bias-Free: Uses historical S&P 500 constituents if available.
        
        Returns summary statistics.
        """
        from app.db.models import SP500HistoricalConstituent, Company
        
        # 1. Get all symbols that have ever been in S&P 500 (survivorship-bias-free)
        # or fall back to current list
        hist_result = await self.session.execute(
            select(func.distinct(SP500HistoricalConstituent.symbol))
        )
        hist_symbols = [r[0] for r in hist_result.fetchall()]
        
        if hist_symbols:
            logger.info(f"Using {len(hist_symbols)} historical S&P 500 constituents for analysis")
            # Get company details for these symbols
            result = await self.session.execute(
                select(Company).where(Company.ticker.in_(hist_symbols))
            )
            companies = result.scalars().all()
            
            # Add current S&P 500 as well just in case they aren't in historical table yet
            curr_result = await self.session.execute(select(SP500Company))
            curr_companies = curr_result.scalars().all()
            
            # Union of both lists (by ticker)
            seen_tickers = {c.ticker for c in companies}
            for cc in curr_companies:
                if cc.symbol not in seen_tickers:
                    # Create dummy company-like object for classification
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
            result = await self.session.execute(
                select(SP500Company)
            )
            companies = result.scalars().all()
        
        logger.info(f"Classifying {len(companies)} total companies")
        
        cohort_5yr = []
        cohort_10yr = []
        cohort_20yr = []
        excluded = []
        
        for company in companies:
            coverage = await self.get_company_data_coverage(company.symbol)
            
            # Calculate profile and quality
            rd_profile = self._calculate_rd_profile(coverage["avg_rd_intensity"])
            quality_score = self._calculate_quality_score(coverage)
            
            # Create or update cohort record
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
            
            # Upsert
            await self.session.merge(cohort_record)
            
            # Categorize
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
    
    async def get_cohort_by_window(self, window_type: str) -> List[Dict]:
        """
        Get companies eligible for a specific window type.
        
        Args:
            window_type: "5yr", "10yr", or "20yr"
        """
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
        
        # Sector breakdown
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
        
        # R&D profile breakdown
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


# Import Integer for type casting
from sqlalchemy import Integer


async def classify_cohort_windows(session: AsyncSession) -> Dict:
    """
    Convenience function to classify 500 companies into rolling window cohorts.
    """
    classifier = CohortClassifier(session)
    return await classifier.classify_all_companies()

