# EXEMPTION: 324 lines — Complex monthly spanning test with SQL-heavy data assembly
"""
PATH: backend/app/services/factor_tests/spanning_monthly.py
PURPOSE: Mixin for monthly-frequency factor spanning tests
WHY: Monthly tests increase power for small annual samples (reviewer-friendly)
NOTE: File exceeds 300 lines due to large SQL queries that cannot be meaningfully split
"""

from typing import Dict, Any, Optional
from datetime import date as _date

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FamaFrenchFactor, SP500HistoricalConstituent
from app.services.factor_tests.models import SpanningTestResult

# ---------------------------------------------------------------------------
# SQL template for building monthly HML_RD returns within each July-June year.
# The {members_cte} and {members_join} placeholders are filled at runtime
# depending on whether SP500 membership data is available.
# ---------------------------------------------------------------------------
_MONTHLY_HML_SQL = """
    WITH {members_cte}
    rd_data AS (
        SELECT
            inc.symbol,
            CASE
                WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                ELSE NULL
            END AS rd_intensity
        FROM fmp_income_statements inc
        {members_join}
        WHERE inc.fiscal_year = :formation_year
          AND inc.period = 'FY'
          AND inc.rd_expenses >= 0
          AND inc.revenue >= 100000000
    ),
    ranked AS (
        SELECT
            rd.symbol,
            rd.rd_intensity,
            NTILE(5) OVER (ORDER BY rd.rd_intensity) AS quintile
        FROM rd_data rd
        WHERE rd.rd_intensity IS NOT NULL
    ),
    daily AS (
        SELECT
            p.symbol,
            p.date,
            p.close AS price,
            COALESCE(d.adj_dividend, d.dividend, 0.0) AS dividend,
            LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_price
        FROM fmp_daily_prices p
        JOIN ranked r ON r.symbol = p.symbol
        LEFT JOIN fmp_dividends d
          ON d.symbol = p.symbol
         AND d.date = p.date
        WHERE p.date >= :price_start
          AND p.date <= :price_end
          AND p.close IS NOT NULL
          AND p.close > 0
    ),
    daily_ret AS (
        SELECT
            symbol,
            date_trunc('month', date)::date AS month,
            CASE
                WHEN prev_price IS NOT NULL AND prev_price > 0
                THEN ((price + dividend) / prev_price) - 1
                ELSE NULL
            END AS ret
        FROM daily
    ),
    monthly_ret AS (
        SELECT
            symbol,
            month,
            (EXP(SUM(LN(1 + ret))) - 1) AS ret
        FROM daily_ret
        WHERE ret IS NOT NULL
          AND (1 + ret) > 0
          AND month >= :window_start_month
          AND month <= :window_end_month
        GROUP BY symbol, month
    ),
    joined AS (
        SELECT
            mr.month,
            r.quintile,
            mr.ret
        FROM monthly_ret mr
        JOIN ranked r ON r.symbol = mr.symbol
        WHERE r.quintile IN (1, 5)
          AND mr.ret IS NOT NULL
    )
    SELECT
        month,
        AVG(CASE WHEN quintile = 1 THEN ret END) AS q1,
        AVG(CASE WHEN quintile = 5 THEN ret END) AS q5,
        AVG(CASE WHEN quintile = 5 THEN ret END) - AVG(CASE WHEN quintile = 1 THEN ret END) AS hml,
        COUNT(CASE WHEN quintile = 1 THEN 1 END) AS n_q1,
        COUNT(CASE WHEN quintile = 5 THEN 1 END) AS n_q5
    FROM joined
    GROUP BY month
    ORDER BY month
"""

_MEMBERS_CTE = """
    members AS (
        SELECT DISTINCT symbol
        FROM sp500_historical_constituents
        WHERE added_date <= :formation_date
          AND (removed_date IS NULL OR removed_date >= :formation_date)
    ),"""

_MEMBERS_JOIN = "JOIN members m ON m.symbol = inc.symbol"


class SpanningMonthlyTestsMixin:
    """Mixin providing monthly-frequency spanning test orchestration."""

    session: AsyncSession  # Set by the concrete class

    async def run_all_spanning_tests_monthly(
        self,
        *,
        start_return_year: int,
        end_return_year: int,
        data_tier: str = "tier1",
        use_july_june: bool = True,
    ) -> Dict[str, Any]:
        """
        Monthly-frequency factor spanning tests (reviewer-friendly for small annual samples).

        Design:
          - Keep the study's annual July reconstitution rule.
          - Compute *monthly* HML_RD returns within each July-June year using month-end
            split-adjusted closes plus dividend events (Tier-1 total-return proxy).
          - Regress monthly HML_RD on monthly FF factors; report alpha annualized (x12).
        """
        if not use_july_june:
            return {"error": "Monthly spanning currently implemented for July-June convention only."}
        if data_tier != "tier1":
            return {"error": f"Monthly spanning currently supports Tier-1 only. Got data_tier={data_tier!r}."}

        # Check membership availability (point-in-time S&P 500 constituents)
        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        monthly_rows: list[dict[str, Any]] = []

        # Build monthly HML_RD across all July-June windows.
        for return_year in range(int(start_return_year), int(end_return_year) + 1):
            formation_year = int(return_year) - 1
            formation_date = _date(int(return_year), 7, 1)
            price_start = _date(int(return_year), 6, 1)
            price_end = _date(int(return_year) + 1, 6, 30)
            window_start_month = _date(int(return_year), 7, 1)
            window_end_month = _date(int(return_year) + 1, 6, 1)

            # Build SQL dynamically based on membership availability
            if membership_available:
                sql = _MONTHLY_HML_SQL.format(members_cte=_MEMBERS_CTE, members_join=_MEMBERS_JOIN)
                params: dict[str, Any] = {
                    "formation_year": formation_year,
                    "formation_date": formation_date,
                    "price_start": price_start,
                    "price_end": price_end,
                    "window_start_month": window_start_month,
                    "window_end_month": window_end_month,
                }
            else:
                sql = _MONTHLY_HML_SQL.format(members_cte="", members_join="")
                params = {
                    "formation_year": formation_year,
                    "price_start": price_start,
                    "price_end": price_end,
                    "window_start_month": window_start_month,
                    "window_end_month": window_end_month,
                }

            result = await self.session.execute(text(sql), params)
            for month, q1, q5, hml, n_q1, n_q5 in result.fetchall():
                if month is None or hml is None:
                    continue
                monthly_rows.append({
                    "date": month,
                    "hml_rd": float(hml),
                    "q1": float(q1) if q1 is not None else None,
                    "q5": float(q5) if q5 is not None else None,
                    "n_q1": int(n_q1 or 0),
                    "n_q5": int(n_q5 or 0),
                })

        if len(monthly_rows) < 120:
            return {"error": "Insufficient monthly data for spanning tests", "n_months": len(monthly_rows)}

        monthly_rows.sort(key=lambda r: r["date"])

        # Fetch monthly FF factors over the same month range
        start_date = monthly_rows[0]["date"]
        end_date = monthly_rows[-1]["date"]
        ff_result = await self.session.execute(
            select(FamaFrenchFactor)
            .where(
                FamaFrenchFactor.frequency == "monthly",
                FamaFrenchFactor.date >= start_date,
                FamaFrenchFactor.date <= end_date,
            )
            .order_by(FamaFrenchFactor.date)
        )
        ff_rows = ff_result.scalars().all()
        ff_map = {
            r.date: {
                "mkt_rf": float(r.mkt_rf) if r.mkt_rf is not None else None,
                "smb": float(r.smb) if r.smb is not None else None,
                "hml": float(r.hml) if r.hml is not None else None,
                "rmw": float(r.rmw) if r.rmw is not None else None,
                "cma": float(r.cma) if r.cma is not None else None,
                "mom": float(r.mom) if r.mom is not None else None,
                "rf": float(r.rf) if r.rf is not None else None,
            }
            for r in ff_rows
        }

        aligned = [
            r for r in monthly_rows
            if r["date"] in ff_map and isinstance(r.get("hml_rd"), (int, float))
        ]
        if len(aligned) < 120:
            return {"error": "Insufficient aligned factor months for spanning tests", "n_months": len(aligned)}

        dates = [r["date"] for r in aligned]
        hml_rd = [float(r["hml_rd"]) for r in aligned]

        # Prepare factor series aligned on month
        mkt_rf = [ff_map[d]["mkt_rf"] for d in dates]
        smb = [ff_map[d]["smb"] for d in dates]
        hml = [ff_map[d]["hml"] for d in dates]
        rmw = [ff_map[d]["rmw"] for d in dates]
        cma = [ff_map[d]["cma"] for d in dates]
        mom = [ff_map[d]["mom"] for d in dates]

        def _mask_valid(xs: list[float | None]) -> list[bool]:
            return [isinstance(x, (int, float)) for x in xs]

        results: Dict[str, Any] = {}
        nw_lags = 12  # monthly HAC convention
        annualize = 12.0  # report alpha annualized for readability

        def _store(model_key: str, res: Optional[SpanningTestResult]) -> None:
            if not res:
                return
            alpha_a = float(res.alpha) * annualize
            se_a = float(res.alpha_se) * annualize
            ci_low = float(alpha_a - 1.96 * se_a)
            ci_high = float(alpha_a + 1.96 * se_a)
            results[model_key] = {
                "alpha": alpha_a,
                "alpha_se": se_a,
                "alpha_ci_95": {"low": ci_low, "high": ci_high},
                "alpha_t": float(res.alpha_t),
                "alpha_p": float(res.alpha_p),
                "is_spanned": bool(res.is_spanned),
                "r_squared": float(res.r_squared),
                "factor_loadings": res.factor_loadings,
            }

        # Build valid-index masks per model and run regressions
        base_mask = [a and b and c for a, b, c in zip(_mask_valid(mkt_rf), _mask_valid(smb), _mask_valid(hml))]

        # FF3
        idx = [i for i, ok in enumerate(base_mask) if ok]
        _store("FF3", self.run_spanning_regression(
            [hml_rd[i] for i in idx],
            {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx]},
            "FF3", nw_lags=nw_lags,
        ))

        # FF3 + MOM
        valid = [bm and m for bm, m in zip(base_mask, _mask_valid(mom))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store("FF3_MOM", self.run_spanning_regression(
            [hml_rd[i] for i in idx],
            {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "mom": [mom[i] for i in idx]},
            "FF3+MOM", nw_lags=nw_lags,
        ))

        # FF5
        valid = [bm and r and c for bm, r, c in zip(base_mask, _mask_valid(rmw), _mask_valid(cma))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store("FF5", self.run_spanning_regression(
            [hml_rd[i] for i in idx],
            {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "rmw": [rmw[i] for i in idx], "cma": [cma[i] for i in idx]},
            "FF5", nw_lags=nw_lags,
        ))

        # FF5 + MOM
        valid = [bm and r and c and m for bm, r, c, m in zip(base_mask, _mask_valid(rmw), _mask_valid(cma), _mask_valid(mom))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store("FF5_MOM", self.run_spanning_regression(
            [hml_rd[i] for i in idx],
            {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "rmw": [rmw[i] for i in idx], "cma": [cma[i] for i in idx], "mom": [mom[i] for i in idx]},
            "FF5+MOM", nw_lags=nw_lags,
        ))

        all_spanned = all(r.get("is_spanned", True) for r in results.values())

        return {
            "models": results,
            "frequency": "monthly",
            "n_months": len(aligned),
            "nw_lags": int(nw_lags),
            "alpha_reporting": "annualized_from_monthly_intercept_x12",
            "interpretation": {
                "is_distinct_factor": not all_spanned,
                "summary": (
                    "R&D premium is NOT fully explained by standard factors (alpha is significant)"
                    if not all_spanned
                    else "R&D premium may be explained by standard factors (alpha is not significant)"
                ),
            },
            "latex_table": self._generate_spanning_latex(results),
        }
