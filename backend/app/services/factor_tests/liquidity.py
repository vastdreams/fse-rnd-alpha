"""
PATH: backend/app/services/factor_tests/liquidity.py
PURPOSE: Liquidity moderation test for the characteristic premium (HML_RD = Q5 - Q1)
WHY: Direct, publication-grade proxy for information frictions (Ahmed, Bu, Ye 2025)

METHOD (Tier-1, July-June aligned):
  - Compute pre-formation liquidity over Jul(Y)-Jun(Y+1) for formation_year = Y
  - Bucket stocks into terciles by liquidity within each formation year
  - Within each tercile, compute internal RD quintiles and the Q5-Q1 premium by year
  - Aggregate across years and report mean premium + Newey-West t-stat
"""

from typing import Dict, Any

import numpy as np
import pandas as pd
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.factor_tests.utils import safe_qcut

# ---------------------------------------------------------------------------
# SQL: Fetch company-level data with liquidity proxies (Amihud + dollar volume)
# ---------------------------------------------------------------------------
_LIQUIDITY_SQL = """
    WITH years AS (
        SELECT generate_series(:start_y, :end_y - 1) AS formation_year
    ),
    members AS (
        SELECT y.formation_year, c.symbol
        FROM years y
        JOIN sp500_historical_constituents c
          ON c.added_date <= make_date(y.formation_year + 1, 7, 1)
         AND (c.removed_date IS NULL OR c.removed_date >= make_date(y.formation_year + 1, 7, 1))
    ),
    fundamentals AS (
        SELECT
            inc.symbol,
            inc.fiscal_year AS formation_year,
            CASE
                WHEN inc.revenue >= 100000000 AND inc.revenue IS NOT NULL AND inc.rd_expenses IS NOT NULL
                THEN (inc.rd_expenses::float / NULLIF(inc.revenue, 0) * 100.0)
                ELSE NULL
            END AS rd_intensity
        FROM fmp_income_statements inc
        WHERE inc.period = 'FY'
          AND inc.fiscal_year >= :start_y
          AND inc.fiscal_year < :end_y
    ),
    returns AS (
        SELECT
            r.symbol,
            r.formation_year,
            (r.annualized_return * 100.0) AS return_pct
        FROM july_june_returns r
        WHERE r.data_tier = :data_tier
          AND r.formation_year >= :start_y
          AND r.formation_year < :end_y
          AND r.annualized_return IS NOT NULL
    ),
    daily AS (
        SELECT
            p.symbol,
            p.date,
            p.close,
            p.volume,
            LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_close,
            (
              EXTRACT(YEAR FROM p.date)::int
              - CASE WHEN EXTRACT(MONTH FROM p.date)::int < 7 THEN 1 ELSE 0 END
            ) AS formation_year
        FROM fmp_daily_prices p
        WHERE p.date >= make_date(:start_y, 7, 1)
          AND p.date <= make_date(:end_y, 6, 30)
          AND p.symbol IN (SELECT DISTINCT symbol FROM sp500_historical_constituents)
    ),
    liquidity AS (
        SELECT
            d.symbol,
            d.formation_year,
            COUNT(*) FILTER (
                WHERE d.close IS NOT NULL AND d.volume IS NOT NULL AND d.volume > 0
            ) AS trading_days,
            AVG(
                CASE
                    WHEN d.prev_close IS NULL OR d.prev_close = 0 THEN NULL
                    WHEN d.close IS NULL OR d.volume IS NULL OR d.volume <= 0 THEN NULL
                    ELSE ABS((d.close / d.prev_close) - 1.0) / NULLIF((d.close * d.volume)::float, 0)
                END
            ) AS amihud_illiq,
            AVG(
                CASE
                    WHEN d.close IS NULL OR d.volume IS NULL OR d.volume <= 0 THEN NULL
                    ELSE (d.close * d.volume)::float
                END
            ) AS avg_dollar_volume
        FROM daily d
        WHERE d.formation_year >= :start_y
          AND d.formation_year < :end_y
        GROUP BY d.symbol, d.formation_year
    )
    SELECT
        m.formation_year,
        m.symbol,
        f.rd_intensity,
        r.return_pct,
        l.trading_days,
        l.amihud_illiq,
        l.avg_dollar_volume
    FROM members m
    JOIN fundamentals f
      ON f.symbol = m.symbol AND f.formation_year = m.formation_year
    JOIN returns r
      ON r.symbol = m.symbol AND r.formation_year = m.formation_year
    JOIN liquidity l
      ON l.symbol = m.symbol AND l.formation_year = m.formation_year
    WHERE f.rd_intensity IS NOT NULL
      AND l.trading_days >= 150
      AND l.amihud_illiq IS NOT NULL
      AND l.avg_dollar_volume IS NOT NULL
"""


class LiquidityModerationAnalyzer:
    """
    Liquidity moderation test for the characteristic premium (HML_RD = Q5 - Q1).

    Two panels:
      (A) Amihud (2002) illiquidity using daily close returns and dollar volume
      (B) Dollar volume proxy (avg close x volume), inverted so higher = more illiquid
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_liquidity_moderation_tests(
        self,
        *,
        start_formation_year: int,
        end_formation_year: int,
        data_tier: str = "tier1",
    ) -> Dict[str, Any]:
        from app.services.statistics import StatisticalAnalyzer

        if end_formation_year <= start_formation_year:
            return {"error": "end_formation_year must be > start_formation_year"}

        result = await self.session.execute(
            text(_LIQUIDITY_SQL),
            {
                "start_y": int(start_formation_year),
                "end_y": int(end_formation_year),
                "data_tier": str(data_tier),
            },
        )
        rows = result.fetchall()
        if not rows:
            return {"error": "No rows available for liquidity moderation (check daily prices + membership + returns)."}

        df = pd.DataFrame(
            rows,
            columns=[
                "formation_year", "symbol", "rd_intensity", "return_pct",
                "trading_days", "amihud_illiq", "avg_dollar_volume",
            ],
        )

        # Liquidity terciles
        df["amihud_bucket"] = df.groupby("formation_year")["amihud_illiq"].transform(
            lambda s: safe_qcut(s, 3, ["Liquid", "Medium", "Illiquid"])
        )
        # Dollar volume: invert so "Illiquid" means lower dollar volume
        df["dvol_bucket"] = df.groupby("formation_year")["avg_dollar_volume"].transform(
            lambda s: safe_qcut((-s), 3, ["Liquid", "Medium", "Illiquid"])
        )

        def _assign_rd_quintiles(sub: "pd.DataFrame") -> "pd.DataFrame":
            sub = sub.copy()
            sub["rd_quintile"] = safe_qcut(sub["rd_intensity"], 5, [1, 2, 3, 4, 5])
            return sub

        def _yearly_premiums(bucket_col: str) -> "pd.DataFrame":
            out: list[dict[str, Any]] = []
            for (y, b), sub in df.groupby(["formation_year", bucket_col]):
                if sub.empty or len(sub) < 25:
                    continue
                sub2 = _assign_rd_quintiles(sub)
                q5 = sub2[sub2["rd_quintile"] == 5]["return_pct"].mean()
                q1 = sub2[sub2["rd_quintile"] == 1]["return_pct"].mean()
                if np.isnan(q5) or np.isnan(q1):
                    continue
                out.append({
                    "formation_year": int(y),
                    "bucket": str(b),
                    "premium": float(q5 - q1),
                    "n_firms": int(len(sub2)),
                })
            return pd.DataFrame(out)

        amihud_yearly = _yearly_premiums("amihud_bucket")
        dvol_yearly = _yearly_premiums("dvol_bucket")

        if amihud_yearly.empty or dvol_yearly.empty:
            return {"error": "Insufficient yearly bucket data for liquidity moderation."}

        stats_analyzer = StatisticalAnalyzer(self.session, use_july_june=True, data_tier=data_tier)

        def _summarize(yearly: "pd.DataFrame") -> Dict[str, Any]:
            buckets: dict[str, Any] = {}
            for name in ["Liquid", "Medium", "Illiquid"]:
                s = yearly[yearly["bucket"] == name].sort_values("formation_year")
                series = s["premium"].tolist()
                hac = stats_analyzer.compute_hac_ttest(series, hypothesis_value=0.0, lags=1)
                buckets[name] = {
                    "mean_premium_pct": round(float(hac.mean), 2),
                    "nw_t_stat": round(float(hac.t_statistic_hac), 2),
                    "nw_p_value": float(hac.p_value_hac),
                    "n_years": int(len(series)),
                    "avg_firms_per_year": round(float(s["n_firms"].mean()), 1) if len(s) else None,
                }

            pivot = yearly.pivot_table(index="formation_year", columns="bucket", values="premium", aggfunc="mean")
            if "Illiquid" in pivot.columns and "Liquid" in pivot.columns:
                spread_series = (pivot["Illiquid"] - pivot["Liquid"]).dropna().tolist()
                hac_spread = stats_analyzer.compute_hac_ttest(spread_series, hypothesis_value=0.0, lags=1)
                buckets["Illiquid_minus_Liquid"] = {
                    "mean_premium_pct": round(float(hac_spread.mean), 2),
                    "nw_t_stat": round(float(hac_spread.t_statistic_hac), 2),
                    "nw_p_value": float(hac_spread.p_value_hac),
                    "n_years": int(len(spread_series)),
                }

            return {
                "buckets": buckets,
                "yearly": [
                    {
                        "formation_year": int(r["formation_year"]),
                        "return_start_year": int(r["formation_year"]) + 1,
                        "bucket": str(r["bucket"]),
                        "premium_pct": round(float(r["premium"]), 2),
                        "n_firms": int(r["n_firms"]),
                    }
                    for _, r in yearly.sort_values(["formation_year", "bucket"]).iterrows()
                ],
            }

        return {
            "meta": {
                "start_formation_year": int(start_formation_year),
                "end_formation_year": int(end_formation_year - 1),
                "return_convention": "july_june",
                "data_tier": str(data_tier),
                "liquidity_window": "Jul(Y)-Jun(Y+1) (pre-formation)",
                "premium_definition": "Within-bucket Q5-Q1 using July-June annualized returns (percent)",
                "nw_lags": 1,
                "trading_days_min": 150,
            },
            "amihud": {
                "proxy": "Amihud (2002) ILLIQ = mean(|r_d| / dollar_volume_d) using daily close and dollar volume",
                **_summarize(amihud_yearly),
            },
            "dollar_volume": {
                "proxy": "Average daily dollar volume (close x volume), inverted for 'Illiquid' bucket",
                **_summarize(dvol_yearly),
            },
            "note": (
                "This is a descriptive conditional-sort diagnostic (not primary inference). "
                "Motivated by evidence that the R&D premium strengthens with illiquidity."
            ),
        }
