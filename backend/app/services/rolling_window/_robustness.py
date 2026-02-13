# EXEMPTION: 316 lines — Robustness mixin with sector-neutral and EW-vs-VW methods sharing data queries
"""
PATH: backend/app/services/rolling_window/_robustness.py
PURPOSE: Robustness checks — sector-neutral premium and EW vs VW comparison
WHY: Publication-grade robustness tests that isolate R&D premium from
     sector effects and weighting-scheme sensitivity
FLOW:
  ┌──────────────────────┐   ┌─────────────────────┐
  │ sector_neutral       │   │ ew_vs_vw_premium    │
  │ (within-sector Q5-Q1)│   │ (equal vs value wt) │
  └──────────────────────┘   └─────────────────────┘
"""

from typing import Dict, List

import numpy as np
from sqlalchemy import select

from app.db.models import (
    FMPIncomeStatement, FMPAnnualReturn, SP500Company, JulyJuneReturn
)
from app.services.sanity_checks import (
    cap_rd_intensity, MIN_REVENUE_THRESHOLD, MAX_RD_INTENSITY_ABSOLUTE
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class RobustnessMixin:
    """Mixin: sector-neutral premium and equal-weighted vs value-weighted comparison."""

    async def compute_sector_neutral_premium(
        self,
        year: int
    ) -> Dict:
        """
        Compute sector-neutral R&D premium.

        Within each sector:
        1. Form quintiles based on R&D intensity
        2. Compute Q5 - Q1 premium
        3. Average across sectors (equal-weighted)

        This controls for sector effects and isolates firm-level R&D premium.

        PUBLICATION FIX (Dec 2025):
        - Uses July-June returns (controlled by self.use_july_june)
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).

        Args:
            year: Year for which to compute premium (return year for calendar, formation_year+1 for July-June)

        Returns:
            Dict with sector-neutral premium and breakdown by sector
        """
        from app.core.sectors import normalize_sector, GICS_SECTORS

        formation_year = year - 1  # FY data from year-1

        # Get R&D data with sector info from formation year
        rd_result = await self.session.execute(
            select(
                FMPIncomeStatement.symbol,
                FMPIncomeStatement.rd_expenses,
                FMPIncomeStatement.revenue,
                SP500Company.sector
            )
            .outerjoin(SP500Company, FMPIncomeStatement.symbol == SP500Company.symbol)
            .where(FMPIncomeStatement.fiscal_year == formation_year)
            .where(FMPIncomeStatement.period == "FY")
            .where(FMPIncomeStatement.rd_expenses >= 0)
            .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
        )

        # Group companies by normalized sector
        sector_data = {}
        for r in rd_result.fetchall():
            normalized_sector = normalize_sector(r.sector) if r.sector else "Unknown"
            if normalized_sector not in sector_data:
                sector_data[normalized_sector] = []

            rd_intensity = r.rd_expenses / r.revenue * 100
            sector_data[normalized_sector].append({
                "symbol": r.symbol,
                "rd_intensity": cap_rd_intensity(rd_intensity, r.sector),
            })

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
                .where(FMPAnnualReturn.year == year)
                .where(FMPAnnualReturn.annual_return.isnot(None))
            )
            returns = {r.symbol: r.annual_return for r in return_result.fetchall()}

        # Compute within-sector quintile premiums
        sector_premiums = {}

        for sector, companies in sector_data.items():
            # Add returns
            companies_with_returns = []
            for c in companies:
                symbol = c["symbol"]
                if symbol in returns and returns[symbol] is not None:
                    ret = returns[symbol]
                else:
                    continue
                companies_with_returns.append({**c, "return": ret})

            if len(companies_with_returns) < 5:
                continue  # Need at least 5 companies to form quintiles

            # Sort by R&D intensity within sector
            sorted_companies = sorted(companies_with_returns, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5

            # Get Q1 and Q5 returns
            q1_companies = sorted_companies[:quintile_size]
            q5_companies = sorted_companies[-quintile_size:] if quintile_size > 0 else sorted_companies

            if q1_companies and q5_companies:
                q1_return = np.mean([c["return"] for c in q1_companies])
                q5_return = np.mean([c["return"] for c in q5_companies])
                premium = q5_return - q1_return

                sector_premiums[sector] = {
                    "premium": float(premium) * 100,  # Convert to percentage
                    "q1_return": float(q1_return) * 100,
                    "q5_return": float(q5_return) * 100,
                    "n_companies": n,
                    "q1_n": len(q1_companies),
                    "q5_n": len(q5_companies)
                }

        if not sector_premiums:
            return {"error": "Insufficient data for sector-neutral analysis", "year": year}

        # Equal-weighted average across sectors
        sector_neutral_premium = np.mean([s["premium"] for s in sector_premiums.values()])

        return {
            "year": year,
            "formation_year": formation_year,
            "sector_neutral_premium": float(sector_neutral_premium),
            "n_sectors": len(sector_premiums),
            "sector_breakdown": sector_premiums,
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)"
            }
        }

    async def compute_ew_vs_vw_premium(
        self,
        start_year: int,
        end_year: int
    ) -> Dict:
        """
        Compute REAL equal-weighted vs value-weighted R&D premium comparison.

        PUBLICATION FIX (Dec 2025):
        - Actually recomputes quintile returns under both weighting schemes
        - Uses market cap (approximated by revenue * 10) for VW
        - Integrates July-June returns and delisting returns

        Args:
            start_year: First year to include
            end_year: Last year to include

        Returns:
            Dict with EW and VW premium statistics
        """
        ew_premiums = []
        vw_premiums = []

        for year in range(start_year, end_year + 1):
            formation_year = year - 1

            # Get R&D data with revenue (as market cap proxy)
            rd_result = await self.session.execute(
                select(
                    FMPIncomeStatement.symbol,
                    FMPIncomeStatement.rd_expenses,
                    FMPIncomeStatement.revenue
                )
                .where(FMPIncomeStatement.fiscal_year == formation_year)
                .where(FMPIncomeStatement.period == "FY")
                .where(FMPIncomeStatement.rd_expenses > 0)
                .where(FMPIncomeStatement.revenue >= MIN_REVENUE_THRESHOLD)
            )

            companies = []
            for r in rd_result.fetchall():
                rd_intensity = (r.rd_expenses / r.revenue * 100) if r.revenue > 0 else 0
                companies.append({
                    "symbol": r.symbol,
                    "rd_intensity": min(rd_intensity, MAX_RD_INTENSITY_ABSOLUTE),
                    "market_cap_proxy": r.revenue * 10  # Simple proxy
                })

            if len(companies) < 25:  # Need at least 5 per quintile
                continue

            # Get returns
            if self.use_july_june:
                return_result = await self.session.execute(
                    select(JulyJuneReturn.symbol, JulyJuneReturn.annualized_return)
                    .where(JulyJuneReturn.formation_year == formation_year)
                    .where(JulyJuneReturn.data_tier == self.data_tier)
                )
                returns = {r.symbol: r.annualized_return for r in return_result.fetchall()}
            else:
                return_result = await self.session.execute(
                    select(FMPAnnualReturn.symbol, FMPAnnualReturn.annual_return)
                    .where(FMPAnnualReturn.year == year)
                )
                returns = {r.symbol: r.annual_return for r in return_result.fetchall()}

            # Add returns (including delisting)
            for c in companies:
                symbol = c["symbol"]
                if symbol in returns and returns[symbol] is not None:
                    c["return"] = returns[symbol]
                else:
                    c["return"] = None

            # Filter to companies with returns
            companies = [c for c in companies if c["return"] is not None]

            if len(companies) < 25:
                continue

            # Sort by R&D intensity and form quintiles
            sorted_companies = sorted(companies, key=lambda x: x["rd_intensity"])
            n = len(sorted_companies)
            quintile_size = n // 5

            q1 = sorted_companies[:quintile_size]
            q5 = sorted_companies[-quintile_size:]

            if not q1 or not q5:
                continue

            # Equal-weighted returns
            q1_ew = np.mean([c["return"] for c in q1])
            q5_ew = np.mean([c["return"] for c in q5])
            ew_premium = (q5_ew - q1_ew) * 100  # Convert to percentage
            ew_premiums.append(ew_premium)

            # Value-weighted returns
            q1_caps = [c["market_cap_proxy"] for c in q1]
            q5_caps = [c["market_cap_proxy"] for c in q5]
            q1_rets = [c["return"] for c in q1]
            q5_rets = [c["return"] for c in q5]

            q1_vw = np.average(q1_rets, weights=q1_caps) if sum(q1_caps) > 0 else 0
            q5_vw = np.average(q5_rets, weights=q5_caps) if sum(q5_caps) > 0 else 0
            vw_premium = (q5_vw - q1_vw) * 100
            vw_premiums.append(vw_premium)

        if len(ew_premiums) < 5:
            return {"error": "Insufficient data for EW vs VW comparison"}

        # Compute statistics
        ew_mean = float(np.mean(ew_premiums))
        vw_mean = float(np.mean(vw_premiums))
        ew_std = float(np.std(ew_premiums, ddof=1))
        vw_std = float(np.std(vw_premiums, ddof=1))
        n = len(ew_premiums)

        ew_t = ew_mean / (ew_std / np.sqrt(n)) if ew_std > 0 else 0
        vw_t = vw_mean / (vw_std / np.sqrt(n)) if vw_std > 0 else 0

        from scipy import stats as sp_stats
        ew_p = float(2 * (1 - sp_stats.t.cdf(abs(ew_t), df=n-1))) if n > 1 else 1.0
        vw_p = float(2 * (1 - sp_stats.t.cdf(abs(vw_t), df=n-1))) if n > 1 else 1.0

        return {
            "period": f"{start_year}-{end_year}",
            "n_years": n,
            "equal_weighted": {
                "mean_premium_pct": round(ew_mean, 2),
                "std_dev": round(ew_std, 2),
                "t_statistic": round(ew_t, 2),
                "p_value": round(ew_p, 4),
                "significant_005": bool(ew_p < 0.05)
            },
            "value_weighted": {
                "mean_premium_pct": round(vw_mean, 2),
                "std_dev": round(vw_std, 2),
                "t_statistic": round(vw_t, 2),
                "p_value": round(vw_p, 4),
                "significant_005": bool(vw_p < 0.05)
            },
            "ew_minus_vw_spread": round(ew_mean - vw_mean, 2),
            "interpretation": (
                "EW premium > VW suggests small-cap contribution. "
                f"Both schemes show {'significant' if ew_p < 0.05 and vw_p < 0.05 else 'mixed'} results."
            ),
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "market_cap_proxy": "Revenue × 10",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)"
            }
        }
