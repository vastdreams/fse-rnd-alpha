# EXEMPTION: 479 lines — Single large Fama-MacBeth method with complex cross-sectional regression pipeline
"""
PATH: backend/app/services/statistics/fama_macbeth_monthly.py
PURPOSE: Monthly Fama-MacBeth cross-sectional regressions (publication-grade).
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional, Any
import numpy as np
from scipy import stats
from sqlalchemy import select, func

from app.core.logging import get_logger

logger = get_logger(__name__)


class FamaMacBethMonthlyMixin:
    """Mixin providing monthly Fama-MacBeth regression."""

    async def run_fama_macbeth_monthly_with_controls(
        self,
        start_return_year: int = 1996,
        end_return_year: int = 2025,
        nw_lags: int = 12,
        winsor_p: float = 0.01,
        data_tier: str = "tier1",
    ) -> Dict[str, Any]:
        """
        Monthly Fama–MacBeth (1973) cross-sectional regressions with controls.

        PUBLICATION-GRADE (Jan 2026):
        ─────────────────────────────
        This is the PRIMARY inferential test for whether R&D intensity predicts
        returns after controlling for firm size and book-to-market.

        Methodology (pre-specified, not data-mined):
        1. **Monthly cross-sectional regression** (Stage 1):
           For each month t in [Jul Y, Jun Y+1], regress:
               Return_i,t = α_t + β1_t*RD_i + β2_t*logME_i + β3_t*BM_i + ε_i,t
           where RD, logME, and BM are fixed at formation (June Y) for the
           entire July(Y)-June(Y+1) period (annual signal, monthly returns).

        2. **Time-series inference** (Stage 2):
           Compute mean of each coefficient across months.
           FM t-stat = mean(β) / (std(β) / sqrt(T)).
           NW(12) t-stat uses Newey-West HAC standard errors.

        Signal timing (Fama-French convention):
        - FY(T) financials → characteristics at June(T+1) formation
        - Returns measured monthly Jul(T+1) through Jun(T+2)

        Controls:
        - **Size**: log(market_cap), where market_cap = shares_out × June_end_close
        - **Book-to-market**: total_equity / market_cap (with null guards)

        Args:
            start_return_year: First July start year (e.g. 1996 means Jul1996-Jun1997).
            end_return_year: Last July start year (e.g. 2024 means Jul2024-Jun2025).
            nw_lags: Newey-West lag truncation (default 12 for monthly data).
            winsor_p: Winsorization percentile (0.01 = 1%/99%).
            data_tier: 'tier1' (FMP).

        Returns:
            Dict with n_months, coefficient estimates, t-stats, p-values, latex_table.
        """
        from datetime import date as _date
        from sqlalchemy import text
        import pandas as pd
        import statsmodels.api as sm
        from app.db.models import SP500HistoricalConstituent

        if data_tier != "tier1":
            return {"error": f"Monthly FM currently supports tier1 only. Got {data_tier!r}"}

        # Check if membership spans are available for point-in-time gating
        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        all_month_data: list[dict] = []

        for return_year in range(int(start_return_year), int(end_return_year) + 1):
            formation_year = return_year - 1
            formation_date = _date(return_year, 7, 1)
            june_formation_end = _date(return_year, 6, 30)

            # Query: Get RD intensity, market cap (shares_out × June close), B/M
            # Then monthly returns for Jul(Y)-Jun(Y+1)
            if membership_available:
                q = text("""
                    WITH members AS (
                        SELECT DISTINCT symbol
                        FROM sp500_historical_constituents
                        WHERE added_date <= :formation_date
                          AND (removed_date IS NULL OR removed_date >= :formation_date)
                    ),
                    fundamentals AS (
                        SELECT
                            inc.symbol,
                            CASE WHEN inc.revenue > 100000000
                                 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                 ELSE NULL END AS rd_intensity,
                            bs.total_equity
                        FROM fmp_income_statements inc
                        JOIN members m ON m.symbol = inc.symbol
                        LEFT JOIN fmp_balance_sheets bs
                          ON bs.symbol = inc.symbol AND bs.fiscal_year = inc.fiscal_year AND bs.period = 'FY'
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.revenue >= 100000000
                          AND inc.rd_expenses >= 0
                    ),
                    june_prices AS (
                        SELECT DISTINCT ON (symbol) symbol, close AS june_close
                        FROM fmp_daily_prices
                        WHERE date <= :june_end AND date >= :june_start
                        ORDER BY symbol, date DESC
                    ),
                    shares AS (
                        SELECT symbol, shares_out
                        FROM fmp_income_statements
                        WHERE fiscal_year = :formation_year AND period = 'FY'
                    ),
                    market_caps AS (
                        SELECT
                            jp.symbol,
                            jp.june_close,
                            s.shares_out,
                            (jp.june_close * s.shares_out) AS market_cap
                        FROM june_prices jp
                        JOIN shares s ON s.symbol = jp.symbol
                        WHERE s.shares_out > 0 AND jp.june_close > 0
                    ),
                    characteristics AS (
                        SELECT
                            f.symbol,
                            f.rd_intensity,
                            mc.market_cap,
                            LN(mc.market_cap) AS log_me,
                            CASE WHEN mc.market_cap > 0 THEN f.total_equity / mc.market_cap ELSE NULL END AS bm
                        FROM fundamentals f
                        JOIN market_caps mc ON mc.symbol = f.symbol
                        WHERE f.rd_intensity IS NOT NULL
                    ),
                    daily AS (
                        SELECT
                            p.symbol,
                            p.date,
                            p.close AS price,
                            COALESCE(d.adj_dividend, d.dividend, 0.0) AS dividend,
                            LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_price
                        FROM fmp_daily_prices p
                        JOIN characteristics c ON c.symbol = p.symbol
                        LEFT JOIN fmp_dividends d ON d.symbol = p.symbol AND d.date = p.date
                        WHERE p.date >= :window_start AND p.date <= :window_end
                          AND p.close IS NOT NULL AND p.close > 0
                    ),
                    daily_ret AS (
                        SELECT
                            symbol,
                            date,
                            date_trunc('month', date)::date AS month,
                            CASE WHEN prev_price > 0 THEN ((price + dividend) / prev_price) - 1 ELSE NULL END AS ret
                        FROM daily
                    ),
                    monthly_ret AS (
                        SELECT
                            symbol,
                            month,
                            (EXP(SUM(LN(1 + ret))) - 1) * 100 AS return_pct
                        FROM daily_ret
                        WHERE ret IS NOT NULL AND (1 + ret) > 0
                          AND month >= :month_start AND month <= :month_end
                        GROUP BY symbol, month
                    )
                    SELECT
                        mr.month,
                        mr.symbol,
                        mr.return_pct,
                        c.rd_intensity,
                        c.log_me,
                        c.bm
                    FROM monthly_ret mr
                    JOIN characteristics c ON c.symbol = mr.symbol
                    WHERE mr.return_pct IS NOT NULL
                      AND c.rd_intensity IS NOT NULL
                      AND c.log_me IS NOT NULL
                      AND c.bm IS NOT NULL
                    ORDER BY mr.month, mr.symbol
                """)
            else:
                # Fallback without membership gating
                q = text("""
                    WITH fundamentals AS (
                        SELECT
                            inc.symbol,
                            CASE WHEN inc.revenue > 100000000
                                 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                 ELSE NULL END AS rd_intensity,
                            bs.total_equity
                        FROM fmp_income_statements inc
                        LEFT JOIN fmp_balance_sheets bs
                          ON bs.symbol = inc.symbol AND bs.fiscal_year = inc.fiscal_year AND bs.period = 'FY'
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.revenue >= 100000000
                          AND inc.rd_expenses >= 0
                    ),
                    june_prices AS (
                        SELECT DISTINCT ON (symbol) symbol, close AS june_close
                        FROM fmp_daily_prices
                        WHERE date <= :june_end AND date >= :june_start
                        ORDER BY symbol, date DESC
                    ),
                    shares AS (
                        SELECT symbol, shares_out
                        FROM fmp_income_statements
                        WHERE fiscal_year = :formation_year AND period = 'FY'
                    ),
                    market_caps AS (
                        SELECT
                            jp.symbol,
                            jp.june_close,
                            s.shares_out,
                            (jp.june_close * s.shares_out) AS market_cap
                        FROM june_prices jp
                        JOIN shares s ON s.symbol = jp.symbol
                        WHERE s.shares_out > 0 AND jp.june_close > 0
                    ),
                    characteristics AS (
                        SELECT
                            f.symbol,
                            f.rd_intensity,
                            mc.market_cap,
                            LN(mc.market_cap) AS log_me,
                            CASE WHEN mc.market_cap > 0 THEN f.total_equity / mc.market_cap ELSE NULL END AS bm
                        FROM fundamentals f
                        JOIN market_caps mc ON mc.symbol = f.symbol
                        WHERE f.rd_intensity IS NOT NULL
                    ),
                    daily AS (
                        SELECT
                            p.symbol,
                            p.date,
                            p.close AS price,
                            COALESCE(d.adj_dividend, d.dividend, 0.0) AS dividend,
                            LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_price
                        FROM fmp_daily_prices p
                        JOIN characteristics c ON c.symbol = p.symbol
                        LEFT JOIN fmp_dividends d ON d.symbol = p.symbol AND d.date = p.date
                        WHERE p.date >= :window_start AND p.date <= :window_end
                          AND p.close IS NOT NULL AND p.close > 0
                    ),
                    daily_ret AS (
                        SELECT
                            symbol,
                            date,
                            date_trunc('month', date)::date AS month,
                            CASE WHEN prev_price > 0 THEN ((price + dividend) / prev_price) - 1 ELSE NULL END AS ret
                        FROM daily
                    ),
                    monthly_ret AS (
                        SELECT
                            symbol,
                            month,
                            (EXP(SUM(LN(1 + ret))) - 1) * 100 AS return_pct
                        FROM daily_ret
                        WHERE ret IS NOT NULL AND (1 + ret) > 0
                          AND month >= :month_start AND month <= :month_end
                        GROUP BY symbol, month
                    )
                    SELECT
                        mr.month,
                        mr.symbol,
                        mr.return_pct,
                        c.rd_intensity,
                        c.log_me,
                        c.bm
                    FROM monthly_ret mr
                    JOIN characteristics c ON c.symbol = mr.symbol
                    WHERE mr.return_pct IS NOT NULL
                      AND c.rd_intensity IS NOT NULL
                      AND c.log_me IS NOT NULL
                      AND c.bm IS NOT NULL
                    ORDER BY mr.month, mr.symbol
                """)

            params = {
                "formation_year": formation_year,
                "formation_date": formation_date,
                "june_start": _date(return_year, 6, 1),
                "june_end": june_formation_end,
                "window_start": _date(return_year, 6, 1),
                "window_end": _date(return_year + 1, 6, 30),
                "month_start": _date(return_year, 7, 1),
                "month_end": _date(return_year + 1, 6, 1),
            }

            result = await self.session.execute(q, params)
            rows = result.fetchall()

            for month, symbol, return_pct, rd_intensity, log_me, bm in rows:
                if month is None or return_pct is None:
                    continue
                all_month_data.append({
                    "month": month,
                    "symbol": symbol,
                    "return_pct": float(return_pct),
                    "rd_intensity": float(rd_intensity),
                    "log_me": float(log_me),
                    "bm": float(bm),
                })

        if len(all_month_data) < 1000:
            return {"error": f"Insufficient data for monthly FM ({len(all_month_data)} obs)"}

        df = pd.DataFrame(all_month_data)

        # Winsorize returns per month
        def winsorize_group(g):
            lo = g["return_pct"].quantile(winsor_p)
            hi = g["return_pct"].quantile(1 - winsor_p)
            g["return_pct"] = g["return_pct"].clip(lo, hi)
            return g

        df = df.groupby("month", group_keys=False).apply(winsorize_group)

        # Stage 1: Run OLS per month
        months_sorted = sorted(df["month"].unique())
        coef_series: list[dict] = []

        for m in months_sorted:
            mdf = df[df["month"] == m].copy()
            if len(mdf) < 20:
                continue

            y = mdf["return_pct"]
            X = sm.add_constant(mdf[["rd_intensity", "log_me", "bm"]])

            try:
                model = sm.OLS(y, X).fit()
                coef_series.append({
                    "month": m,
                    "n_obs": len(mdf),
                    "const": model.params.get("const", np.nan),
                    "rd_intensity": model.params.get("rd_intensity", np.nan),
                    "log_me": model.params.get("log_me", np.nan),
                    "bm": model.params.get("bm", np.nan),
                    "r_squared": model.rsquared,
                })
            except Exception:
                continue

        if len(coef_series) < 36:
            return {"error": f"Insufficient monthly regressions ({len(coef_series)})"}

        coef_df = pd.DataFrame(coef_series)
        n_months = len(coef_df)

        # Stage 2: Compute FM and NW statistics
        def compute_fm_stats(series: pd.Series) -> Dict[str, Any]:
            arr = series.dropna().values
            n = len(arr)
            if n < 10:
                return {"coefficient": None, "t_stat_fm": None, "p_value_fm": None,
                        "t_stat_hac": None, "p_value_hac": None, "significant_005": False, "significant_001": False}

            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=1))
            se_fm = std_val / np.sqrt(n)
            t_fm = mean_val / se_fm if se_fm > 0 else 0
            p_fm = float(2 * (1 - stats.t.cdf(abs(t_fm), df=n - 1)))

            # Newey-West HAC
            hac_var = std_val ** 2 / n
            for lag in range(1, min(nw_lags + 1, n - 1)):
                weight = 1 - lag / (nw_lags + 1)
                autocov = np.cov(arr[:-lag], arr[lag:])[0, 1]
                hac_var += 2 * weight * autocov / n
            hac_se = np.sqrt(max(0, hac_var))
            t_hac = mean_val / hac_se if hac_se > 0 else 0
            p_hac = float(2 * (1 - stats.t.cdf(abs(t_hac), df=n - 1)))

            return {
                "coefficient": round(mean_val, 5),
                "std_dev": round(std_val, 5),
                "t_stat_fm": round(t_fm, 3),
                "p_value_fm": round(p_fm, 4),
                "t_stat_hac": round(t_hac, 3),
                "p_value_hac": round(p_hac, 4),
                "significant_005": bool(p_hac < 0.05),
                "significant_001": bool(p_hac < 0.01),
            }

        rd_stats = compute_fm_stats(coef_df["rd_intensity"])
        size_stats = compute_fm_stats(coef_df["log_me"])
        bm_stats = compute_fm_stats(coef_df["bm"])
        alpha_stats = compute_fm_stats(coef_df["const"])

        avg_n_firms = int(coef_df["n_obs"].mean())
        avg_rsq = round(coef_df["r_squared"].mean(), 4)
        first_month = str(months_sorted[0])
        last_month = str(months_sorted[-1])

        # LaTeX table
        def sig_stars(p):
            if p is None:
                return ""
            if p < 0.01:
                return "***"
            if p < 0.05:
                return "**"
            if p < 0.10:
                return "*"
            return ""

        latex_table = f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Fama-MacBeth Cross-Sectional Regressions (Monthly)}}
\\label{{tab:fama_macbeth_monthly}}
\\begin{{tabular}}{{lcccc}}
\\toprule
Variable & Coefficient & t-stat (FM) & t-stat (NW) & \\\\
\\midrule
Intercept & {alpha_stats.get('coefficient', 'N/A')} & {alpha_stats.get('t_stat_fm', 'N/A')} & {alpha_stats.get('t_stat_hac', 'N/A')} & {sig_stars(alpha_stats.get('p_value_hac'))} \\\\
R\\&D Intensity & {rd_stats.get('coefficient', 'N/A')} & {rd_stats.get('t_stat_fm', 'N/A')} & {rd_stats.get('t_stat_hac', 'N/A')} & {sig_stars(rd_stats.get('p_value_hac'))} \\\\
Log(Market Cap) & {size_stats.get('coefficient', 'N/A')} & {size_stats.get('t_stat_fm', 'N/A')} & {size_stats.get('t_stat_hac', 'N/A')} & {sig_stars(size_stats.get('p_value_hac'))} \\\\
Book-to-Market & {bm_stats.get('coefficient', 'N/A')} & {bm_stats.get('t_stat_fm', 'N/A')} & {bm_stats.get('t_stat_hac', 'N/A')} & {sig_stars(bm_stats.get('p_value_hac'))} \\\\
\\midrule
N (months) & \\multicolumn{{4}}{{c}}{{{n_months}}} \\\\
Avg firms/month & \\multicolumn{{4}}{{c}}{{{avg_n_firms}}} \\\\
Avg R$^2$ & \\multicolumn{{4}}{{c}}{{{avg_rsq}}} \\\\
\\bottomrule
\\multicolumn{{5}}{{l}}{{\\footnotesize *** p < 0.01, ** p < 0.05, * p < 0.10. NW = Newey-West HAC (lag={nw_lags}).}} \\\\
\\end{{tabular}}
\\end{{table}}
"""

        rd_sig = "significantly" if rd_stats.get("significant_005") else "not significantly"
        rd_dir = "positive" if (rd_stats.get("coefficient") or 0) > 0 else "negative"

        interpretation = (
            f"Across {n_months} monthly cross-sections ({first_month} to {last_month}), "
            f"R&D intensity is {rd_sig} associated with next-month returns "
            f"(coefficient = {rd_stats.get('coefficient')}, t = {rd_stats.get('t_stat_hac')} with NW adjustment, "
            f"p = {rd_stats.get('p_value_hac')}). "
            f"This {rd_dir} relationship holds after controlling for firm size (log market cap) and book-to-market."
        )

        return {
            "methodology": "Fama-MacBeth (1973) Monthly Cross-Sectional Regressions",
            "frequency": "monthly",
            "return_convention": "July-June (Fama-French)",
            "signal_timing": "FY(T) characteristics -> monthly returns Jul(T+1)-Jun(T+2)",
            "winsorization": f"{winsor_p*100:.0f}%/{(1-winsor_p)*100:.0f}%",
            "nw_lags": nw_lags,
            "n_months": n_months,
            "month_range": f"{first_month} to {last_month}",
            "avg_n_firms_per_month": avg_n_firms,
            "avg_r_squared": avg_rsq,
            "total_firm_months": len(df),

            # Coefficient results
            "intercept": alpha_stats,
            "rd_intensity": rd_stats,
            "log_market_cap": size_stats,
            "book_to_market": bm_stats,

            # Key finding
            "rd_predicts_returns": rd_stats.get("significant_005", False),
            "rd_predicts_returns_001": rd_stats.get("significant_001", False),

            # For publication
            "latex_table": latex_table,
            "interpretation": interpretation,
        }

