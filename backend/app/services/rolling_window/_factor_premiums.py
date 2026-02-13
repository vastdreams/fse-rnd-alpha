"""
PATH: backend/app/services/rolling_window/_factor_premiums.py
PURPOSE: Compute annual R&D factor premiums (Q5 - Q1)
WHY: Isolates the year-by-year factor premium computation, the core
     quantitative result of the research
FLOW:
  ┌──────────────┐   ┌────────────────────┐   ┌──────────────────┐
  │ R&D data     │ → │ Quintile formation │ → │ Q5-Q1 premium    │
  │ (FY T-1)     │   │ + return matching  │   │ per year → DB    │
  └──────────────┘   └────────────────────┘   └──────────────────┘
"""

from typing import Dict, List

import numpy as np
from sqlalchemy import select, func

from app.db.models import (
    FMPIncomeStatement, FMPAnnualReturn, JulyJuneReturn, FactorPremium
)
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD
from app.core.logging import get_logger

logger = get_logger(__name__)


class FactorPremiumsMixin:
    """Mixin: annual R&D factor premium computation."""

    async def compute_annual_factor_premiums(
        self,
        save_results: bool = True
    ) -> List[Dict]:
        """
        Compute R&D factor premium for each year.

        Premium = Q5 (High R&D) return - Q1 (Low R&D) return

        PUBLICATION FIX (Dec 2025):
        - Uses July-June returns (controlled by self.use_july_june)
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        """
        from app.db.models import SP500HistoricalConstituent
        from sqlalchemy import or_
        from datetime import date

        # Get year range
        return_convention = "july_june" if self.use_july_june else "calendar"

        existing_premiums_by_year: Dict[int, FactorPremium] = {}
        if save_results:
            existing_premiums_result = await self.session.execute(
                select(FactorPremium)
                .where(
                    FactorPremium.return_convention == return_convention,
                    FactorPremium.data_tier == self.data_tier,
                )
            )
            for row in existing_premiums_result.scalars().all():
                existing_premiums_by_year[row.year] = row

        if self.use_july_june:
            year_result = await self.session.execute(
                select(
                    func.min(JulyJuneReturn.formation_year),
                    func.max(JulyJuneReturn.formation_year),
                )
                .where(JulyJuneReturn.data_tier == self.data_tier)
            )
        else:
            year_result = await self.session.execute(
                select(
                    func.min(FMPAnnualReturn.year),
                    func.max(FMPAnnualReturn.year),
                )
            )
        min_year, max_year = year_result.fetchone()

        if not min_year or not max_year:
            return []

        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        all_premiums = []

        # For July-June: formation_year is the FY data year
        # Returns are July(formation_year+1) to June(formation_year+2)
        for formation_year in range(min_year, max_year + 1):
            return_year = formation_year + 1  # For labeling purposes

            # Get R&D intensities from formation year
            if self.use_july_june and membership_available:
                formation_date = date(int(return_year), 7, 1)
                rd_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.rd_expenses,
                        FMPIncomeStatement.revenue
                    )
                    .join(SP500HistoricalConstituent, SP500HistoricalConstituent.symbol == FMPIncomeStatement.symbol)
                    .where(
                        SP500HistoricalConstituent.added_date <= formation_date,
                        or_(
                            SP500HistoricalConstituent.removed_date == None,
                            SP500HistoricalConstituent.removed_date >= formation_date,
                        ),
                    )
                    .where(FMPIncomeStatement.fiscal_year == formation_year)
                    .where(FMPIncomeStatement.period == "FY")
                    .where(FMPIncomeStatement.rd_expenses >= 0)
                    .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
                )
            else:
                rd_result = await self.session.execute(
                    select(
                        FMPIncomeStatement.symbol,
                        FMPIncomeStatement.rd_expenses,
                        FMPIncomeStatement.revenue
                    )
                    .where(FMPIncomeStatement.fiscal_year == formation_year)
                    .where(FMPIncomeStatement.period == "FY")
                    .where(FMPIncomeStatement.rd_expenses >= 0)
                    .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
                )
            rd_data = {
                r.symbol: r.rd_expenses / r.revenue * 100
                for r in rd_result.fetchall()
            }

            # Get returns (July-June or calendar)
            if self.use_july_june:
                return_result = await self.session.execute(
                    select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                    .where(JulyJuneReturn.formation_year == formation_year)
                    .where(JulyJuneReturn.annualized_return.isnot(None))
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
                returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
            else:
                return_result = await self.session.execute(
                    select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                    .where(FMPAnnualReturn.year == return_year)
                    .where(FMPAnnualReturn.annual_return.isnot(None))
                )
                returns = {r.symbol: r.annual_return for r in return_result.fetchall()}

            # Combine and assign quintiles
            combined = []
            for s, rd in rd_data.items():
                if s in returns and returns[s] is not None:
                    ret = returns[s]
                else:
                    continue  # No return data

                combined.append({"symbol": s, "rd_intensity": rd, "return": ret})

            if len(combined) < 25:
                continue

            # Sort and assign quintiles
            sorted_companies = sorted(combined, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5

            quintile_returns = {i: [] for i in range(1, 6)}
            quintile_ns = {i: 0 for i in range(1, 6)}

            for i, c in enumerate(sorted_companies):
                q = min(5, i // quintile_size + 1)
                quintile_returns[q].append(c["return"])
                quintile_ns[q] += 1

            q_means = {q: np.mean(rets) if rets else 0 for q, rets in quintile_returns.items()}

            rd_premium = q_means[5] - q_means[1]

            premium_data = {
                "year": return_year,
                "formation_year": formation_year,
                "rd_premium": round(rd_premium * 100, 2),  # Convert to percentage
                "q1_return": round(q_means[1] * 100, 2),
                "q2_return": round(q_means[2] * 100, 2),
                "q3_return": round(q_means[3] * 100, 2),
                "q4_return": round(q_means[4] * 100, 2),
                "q5_return": round(q_means[5] * 100, 2),
                "q1_n": quintile_ns[1],
                "q2_n": quintile_ns[2],
                "q3_n": quintile_ns[3],
                "q4_n": quintile_ns[4],
                "q5_n": quintile_ns[5],
                "return_type": "july_june" if self.use_july_june else "calendar"
            }

            all_premiums.append(premium_data)

            if save_results:
                existing = existing_premiums_by_year.get(return_year)
                if existing:
                    existing.return_convention = return_convention
                    existing.data_tier = self.data_tier

                    existing.rd_premium = rd_premium * 100
                    existing.q1_return = q_means[1] * 100
                    existing.q2_return = q_means[2] * 100
                    existing.q3_return = q_means[3] * 100
                    existing.q4_return = q_means[4] * 100
                    existing.q5_return = q_means[5] * 100

                    existing.q1_n = quintile_ns[1]
                    existing.q2_n = quintile_ns[2]
                    existing.q3_n = quintile_ns[3]
                    existing.q4_n = quintile_ns[4]
                    existing.q5_n = quintile_ns[5]
                else:
                    db_premium = FactorPremium(
                        year=return_year,
                        return_convention=return_convention,
                        data_tier=self.data_tier,
                        rd_premium=rd_premium * 100,  # Store as percentage
                        q1_return=q_means[1] * 100,
                        q2_return=q_means[2] * 100,
                        q3_return=q_means[3] * 100,
                        q4_return=q_means[4] * 100,
                        q5_return=q_means[5] * 100,
                        q1_n=quintile_ns[1],
                        q2_n=quintile_ns[2],
                        q3_n=quintile_ns[3],
                        q4_n=quintile_ns[4],
                        q5_n=quintile_ns[5],
                    )
                    self.session.add(db_premium)
                    existing_premiums_by_year[return_year] = db_premium

        if save_results:
            await self.session.commit()

        logger.info(f"Computed factor premiums for {len(all_premiums)} years (use_july_june={self.use_july_june})")

        return all_premiums
