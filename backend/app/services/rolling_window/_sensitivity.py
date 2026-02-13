"""
PATH: backend/app/services/rolling_window/_sensitivity.py
PURPOSE: R&D intensity cap sensitivity analysis
WHY: Tests whether the R&D premium is robust to different outlier-cap thresholds
FLOW:
  ┌──────────────────┐   ┌──────────────────────┐   ┌───────────────────┐
  │ rd_caps list     │ → │ Recompute quintiles  │ → │ Premium + t-stat  │
  │ [50,100,200,500] │   │ under each cap       │   │ per scenario      │
  └──────────────────┘   └──────────────────────┘   └───────────────────┘
"""

from typing import Dict, List

import numpy as np
from sqlalchemy import select

from app.db.models import FMPIncomeStatement, FMPAnnualReturn, JulyJuneReturn
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD
from app.core.logging import get_logger

logger = get_logger(__name__)


class SensitivityMixin:
    """Mixin: R&D intensity cap sensitivity analysis."""

    async def compute_rd_cap_sensitivity(
        self,
        start_year: int,
        end_year: int,
        rd_caps: List[float] = None
    ) -> Dict:
        """
        Compute R&D premium sensitivity to different R&D intensity caps.

        PUBLICATION FIX (Dec 2025):
        - Actually recomputes premiums under each cap scenario
        - Not heuristic-based multipliers

        Args:
            start_year: First year
            end_year: Last year
            rd_caps: List of R&D intensity caps (%) to test. Default: [50, 100, 200, 500]

        Returns:
            Dict with premium under each cap scenario
        """
        if rd_caps is None:
            rd_caps = [50.0, 100.0, 200.0, 500.0]

        results = {}

        for cap in rd_caps:
            premiums = []

            for year in range(start_year, end_year + 1):
                formation_year = year - 1

                # Get R&D data
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
                    # Apply cap
                    capped_intensity = min(rd_intensity, cap)
                    companies.append({
                        "symbol": r.symbol,
                        "rd_intensity": capped_intensity
                    })

                if len(companies) < 25:
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

                if q1 and q5:
                    q1_ret = np.mean([c["return"] for c in q1])
                    q5_ret = np.mean([c["return"] for c in q5])
                    premium = (q5_ret - q1_ret) * 100
                    premiums.append(premium)

            if len(premiums) >= 5:
                mean_prem = float(np.mean(premiums))
                std_prem = float(np.std(premiums, ddof=1))
                n = len(premiums)
                t_stat = mean_prem / (std_prem / np.sqrt(n)) if std_prem > 0 else 0

                from scipy import stats as sp_stats
                p_value = float(2 * (1 - sp_stats.t.cdf(abs(t_stat), df=n-1))) if n > 1 else 1.0

                results[f"cap_{int(cap)}pct"] = {
                    "rd_cap_pct": cap,
                    "mean_premium_pct": round(mean_prem, 2),
                    "std_dev": round(std_prem, 2),
                    "t_statistic": round(t_stat, 2),
                    "p_value": round(p_value, 4),
                    "significant_005": bool(p_value < 0.05),
                    "n_years": n
                }

        # Determine robustness
        all_significant = all(r["significant_005"] for r in results.values())
        all_positive = all(r["mean_premium_pct"] > 0 for r in results.values())

        return {
            "period": f"{start_year}-{end_year}",
            "scenarios": results,
            "robustness_verdict": "ROBUST" if all_significant and all_positive else "SENSITIVE",
            "interpretation": (
                "Premium is robust if significant and positive under all cap scenarios. "
                f"Results: {'All scenarios significant' if all_significant else 'Some scenarios not significant'}."
            ),
            "methodology": {
                "return_type": "July-June (Fama-French convention)" if self.use_july_june else "Calendar year",
                "survivorship_correction": "Handled in upstream return computation (cash-after-exit assumption)",
                "note": "Each scenario recomputes quintiles with the specified R&D cap"
            }
        }
