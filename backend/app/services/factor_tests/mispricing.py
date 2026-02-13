"""
PATH: backend/app/services/factor_tests/mispricing.py
PURPOSE: Tests whether R&D premium is due to Mispricing (behavioral) vs Risk (rational)
WHY: Publication-grade conditional-sort diagnostics for arbitrage cost proxies

FLOW:
  ┌───────────────┐    ┌───────────────┐    ┌────────────────┐
  │ SQL: company   │ -> │ Conditional   │ -> │ Interpret as   │
  │ data per year  │    │ sorting by    │    │ mispricing or  │
  │                │    │ proxy buckets │    │ risk evidence  │
  └───────────────┘    └───────────────┘    └────────────────┘
"""

from typing import Dict, Any

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.factor_tests.utils import safe_qcut
from app.services.factor_tests.mispricing_analysis import (
    conditional_rd_premium,
    interpret_mispricing_results,
    generate_mispricing_latex,
)

# ---------------------------------------------------------------------------
# SQL: July-June returns with optional SP500 membership filter.
# Placeholders {members_cte} and {members_join} filled at runtime.
# ---------------------------------------------------------------------------
_MISPRICING_SQL_JULY_JUNE = """
    WITH {members_cte}
    company_data AS (
        SELECT
            inc.symbol,
            inc.revenue,
            CASE
                WHEN inc.revenue > 100000000
                THEN (inc.rd_expenses::float / inc.revenue * 100)
                ELSE NULL
            END as rd_intensity,
            LOG(NULLIF(inc.revenue, 0)) as log_size,
            (
                SELECT COUNT(*) FROM fmp_income_statements i2
                WHERE i2.symbol = inc.symbol
                AND i2.fiscal_year <= inc.fiscal_year
            ) as years_tracked,
            (
                SELECT COUNT(*) FROM sp500_companies sp
                WHERE sp.sector = (
                    SELECT sector FROM sp500_companies WHERE symbol = inc.symbol LIMIT 1
                )
            ) as sector_size
        FROM fmp_income_statements inc
        {members_join}
        WHERE inc.fiscal_year = :prior_year
          AND inc.period = 'FY'
          AND inc.revenue >= 100000000
    ),
    returns AS (
        SELECT symbol, annualized_return * 100 as return_pct
        FROM july_june_returns
        WHERE formation_year = :prior_year
              AND data_tier = :data_tier
    ),
    volatility AS (
        SELECT symbol, volatility as vol
        FROM july_june_returns
        WHERE formation_year = :prior_year
              AND data_tier = :data_tier
    )
    SELECT
        cd.symbol,
        cd.rd_intensity,
        cd.log_size,
        cd.years_tracked,
        cd.sector_size,
        r.return_pct,
        v.vol
    FROM company_data cd
    LEFT JOIN returns r ON cd.symbol = r.symbol
    LEFT JOIN volatility v ON cd.symbol = v.symbol
    WHERE cd.rd_intensity IS NOT NULL
"""

_MISPRICING_SQL_CALENDAR = """
    WITH company_data AS (
        SELECT
            inc.symbol,
            inc.revenue,
            CASE
                WHEN inc.revenue > 100000000
                THEN (inc.rd_expenses::float / inc.revenue * 100)
                ELSE NULL
            END as rd_intensity,
            LOG(NULLIF(inc.revenue, 0)) as log_size,
            (
                SELECT COUNT(*) FROM fmp_income_statements i2
                WHERE i2.symbol = inc.symbol
                AND i2.fiscal_year <= inc.fiscal_year
            ) as years_tracked,
            (
                SELECT COUNT(*) FROM sp500_companies sp
                WHERE sp.sector = (
                    SELECT sector FROM sp500_companies WHERE symbol = inc.symbol LIMIT 1
                )
            ) as sector_size
        FROM fmp_income_statements inc
        WHERE inc.fiscal_year = :prior_year
          AND inc.period = 'FY'
          AND inc.revenue >= 100000000
    ),
    returns AS (
        SELECT symbol, annual_return * 100 as return_pct
        FROM fmp_annual_returns
        WHERE year = :return_year
    ),
    volatility AS (
        SELECT symbol, volatility as vol
        FROM fmp_annual_returns
        WHERE year = :prior_year
    )
    SELECT
        cd.symbol,
        cd.rd_intensity,
        cd.log_size,
        cd.years_tracked,
        cd.sector_size,
        r.return_pct,
        v.vol
    FROM company_data cd
    LEFT JOIN returns r ON cd.symbol = r.symbol
    LEFT JOIN volatility v ON cd.symbol = v.symbol
    WHERE cd.rd_intensity IS NOT NULL
"""

_MEMBERS_CTE = """
    members AS (
        SELECT DISTINCT symbol
        FROM sp500_historical_constituents
        WHERE added_date <= :formation_date
          AND (removed_date IS NULL OR removed_date >= :formation_date)
    ),"""

_MEMBERS_JOIN = "JOIN members m ON m.symbol = inc.symbol"


class MispricingAnalyzer:
    """
    Tests whether R&D premium is due to Mispricing (behavioral) vs Risk (rational).

    Mispricing Hypothesis:
    - Premium is higher where arbitrage is costly (illiquid, small, high idiosyncratic vol)
    - Premium is higher where investors are less sophisticated (low inst. ownership)

    Risk Hypothesis:
    - Premium is compensation for innovation risk
    - Premium should persist regardless of arbitrage costs
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_mispricing_tests(
        self,
        start_year: int = 1995,
        end_year: int = 2024,
        use_july_june: bool = True,
        data_tier: str = "tier1",
    ) -> Dict[str, Any]:
        """
        Run comprehensive mispricing vs risk tests.

        PUBLICATION FIX (Dec 2025):
        - Now uses July-June returns by default (Fama-French convention)
        - Eliminates look-ahead bias in return calculations
        """
        import pandas as pd
        from datetime import date
        from app.db.models import SP500HistoricalConstituent

        all_data = []

        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        for year in range(start_year, end_year):
            return_year = year + 1
            params: dict[str, Any] = {"prior_year": year, "return_year": year + 1, "data_tier": data_tier}

            if use_july_june:
                if membership_available:
                    sql = _MISPRICING_SQL_JULY_JUNE.format(members_cte=_MEMBERS_CTE, members_join=_MEMBERS_JOIN)
                    params["formation_date"] = date(int(return_year), 7, 1)
                else:
                    sql = _MISPRICING_SQL_JULY_JUNE.format(members_cte="", members_join="")
            else:
                sql = _MISPRICING_SQL_CALENDAR

            result = await self.session.execute(text(sql), params)
            rows = result.fetchall()

            for row in rows:
                return_pct = float(row[5]) if row[5] is not None else None
                if return_pct is None:
                    continue
                all_data.append({
                    "year": year,
                    "symbol": row[0],
                    "rd_intensity": float(row[1]) if row[1] else 0,
                    "log_size": float(row[2]) if row[2] else 0,
                    "years_tracked": int(row[3]) if row[3] else 0,
                    "sector_size": int(row[4]) if row[4] else 0,
                    "return_pct": float(return_pct),
                    "volatility": float(row[6]) if row[6] else 0.3,
                })

        if len(all_data) < 100:
            return {"error": "Insufficient data for mispricing tests"}

        df = pd.DataFrame(all_data)

        # Build proxy buckets within each year
        df["size_tercile"] = df.groupby("year")["log_size"].transform(
            lambda s: safe_qcut(s, 3, ["Small", "Medium", "Large"])
        )
        df["vol_tercile"] = df.groupby("year")["volatility"].transform(
            lambda s: safe_qcut(s, 3, ["Low", "Medium", "High"])
        )
        df["coverage_tercile"] = df.groupby("year")["years_tracked"].transform(
            lambda s: safe_qcut(s, 3, ["Low", "Medium", "High"])
        )

        test_results: Dict[str, Any] = {}

        test_results["by_size"] = {
            size: conditional_rd_premium(df, "size_tercile", size)
            for size in ["Small", "Medium", "Large"]
        }
        test_results["by_volatility"] = {
            vol: conditional_rd_premium(df, "vol_tercile", vol)
            for vol in ["Low", "Medium", "High"]
        }
        test_results["by_coverage"] = {
            cov: conditional_rd_premium(df, "coverage_tercile", cov)
            for cov in ["Low", "Medium", "High"]
        }

        interpretation = interpret_mispricing_results(test_results)

        return {
            "tests": test_results,
            "total_observations": len(df),
            "n_years": int(df["year"].nunique()),
            "mispricing_evidence_count": interpretation["mispricing_evidence_count"],
            "interpretation": {
                "likely_explanation": interpretation["likely_explanation"],
                "confidence": interpretation["confidence"],
                "explanation": interpretation["explanation"],
            },
            "proxy_notes": {
                "coverage": "Coverage is proxied by years_tracked (count of historical income statement years), not analyst coverage.",
            },
            "latex_summary": generate_mispricing_latex(test_results),
        }
