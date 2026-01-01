"""
PATH: backend/app/services/factor_tests.py
PURPOSE:
  - Factor spanning tests for R&D return premium
  - Tests if HML_RD is spanned by FF3/FF5/Carhart factors
  - Uses Newey-West standard errors for time-series regressions

ROLE IN ARCHITECTURE:
  - Research validation layer
  - Required for academic publication claims about "factor" status

MAIN EXPORTS:
  - FactorSpanningAnalyzer: Main analysis class

NON-RESPONSIBILITIES:
  - Does not fetch factor data (assumes FamaFrenchFactor table populated)
  - Does not construct the HML_RD series (uses RollingWindowAnalyzer)

NOTES FOR FUTURE AI:
  - "Spanning" means the factor can be explained by existing factors
  - If alpha is significant after controlling for FF factors, HML_RD is NOT spanned
  - A non-spanned factor may represent a distinct source of risk/return
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date
import numpy as np
from scipy import stats
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FamaFrenchFactor
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SpanningTestResult:
    """Result from factor spanning test."""
    model_name: str  # e.g., "FF3", "FF5", "FF5+MOM"
    alpha: float     # Intercept (excess return)
    alpha_se: float  # Standard error (Newey-West)
    alpha_t: float   # t-statistic
    alpha_p: float   # p-value
    is_spanned: bool  # True if alpha is NOT significant (can be explained by factors)
    r_squared: float
    n_observations: int
    factor_loadings: Dict[str, float]  # Beta coefficients
    factor_t_stats: Dict[str, float]   # t-statistics for betas


class FactorSpanningAnalyzer:
    """
    Tests if R&D premium is spanned by standard factor models.
    
    Methodology:
    1. Construct monthly or annual HML_RD returns (Q5 - Q1)
    2. Regress HML_RD on factor models:
       - FF3: MKT-RF, SMB, HML
       - FF3 + MOM: Add momentum factor
       - FF5: Add RMW, CMA
    3. Test if alpha (intercept) is significantly different from zero
    4. If alpha > 0 and significant: HML_RD is NOT spanned (distinct premium)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_ff_factors_calendar(
        self,
        start_year: int,
        end_year: int,
        frequency: str = "annual"
    ) -> Dict[int, Dict[str, float]]:
        """
        Get Fama-French factors from database.
        
        Returns dict: year -> {mkt_rf, smb, hml, rmw, cma, mom, rf}
        """
        result = await self.session.execute(
            select(FamaFrenchFactor)
            .where(
                FamaFrenchFactor.frequency == frequency,
                func.extract("year", FamaFrenchFactor.date) >= start_year,
                func.extract("year", FamaFrenchFactor.date) <= end_year
            )
            .order_by(FamaFrenchFactor.date)
        )
        rows = result.scalars().all()
        
        factors = {}
        for r in rows:
            year = r.date.year
            factors[year] = {
                "mkt_rf": r.mkt_rf,
                "smb": r.smb,
                "hml": r.hml,
                "rmw": r.rmw,
                "cma": r.cma,
                "mom": r.mom,
                "rf": r.rf
            }
        
        return factors

    async def get_ff_factors_july_june(
        self,
        start_year: int,
        end_year: int,
    ) -> Dict[int, Dict[str, float]]:
        """
        Build July-June annual factor returns by compounding monthly FF factors.

        Alignment:
          - For return year label Y (July Y -> June Y+1), we compound months:
              Jul(Y), Aug(Y), ..., Dec(Y), Jan(Y+1), ..., Jun(Y+1)

        Returns dict: return_year_start -> {mkt_rf, smb, hml, rmw, cma, mom, rf}
        """
        start_date = date(int(start_year), 7, 1)
        end_date = date(int(end_year) + 1, 6, 1)

        result = await self.session.execute(
            select(FamaFrenchFactor)
            .where(
                FamaFrenchFactor.frequency == "monthly",
                FamaFrenchFactor.date >= start_date,
                FamaFrenchFactor.date <= end_date,
            )
            .order_by(FamaFrenchFactor.date)
        )
        rows = result.scalars().all()

        buckets: Dict[int, Dict[str, List[float]]] = {}
        keys = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]

        for r in rows:
            y = int(r.date.year) if int(r.date.month) >= 7 else int(r.date.year) - 1
            if y < start_year or y > end_year:
                continue

            if y not in buckets:
                buckets[y] = {k: [] for k in keys}

            for k in keys:
                v = getattr(r, k, None)
                if v is None:
                    # Missing factor data in a required month -> skip year later
                    buckets[y][k].append(np.nan)
                else:
                    buckets[y][k].append(float(v))

        def compound(xs: List[float]) -> Optional[float]:
            arr = np.array(xs, dtype=float)
            if len(arr) != 12:
                return None
            if not np.isfinite(arr).all():
                return None
            return float(np.prod(1.0 + arr) - 1.0)

        factors: Dict[int, Dict[str, float]] = {}
        for y, series in buckets.items():
            out: Dict[str, float] = {}
            ok = True
            for k in keys:
                c = compound(series.get(k, []))
                if c is None:
                    ok = False
                    break
                out[k] = c
            if ok:
                factors[int(y)] = out

        return factors
    
    def run_spanning_regression(
        self,
        hml_rd: List[float],
        factors: Dict[str, List[float]],
        model_name: str,
        *,
        nw_lags: int = 4,
    ) -> Optional[SpanningTestResult]:
        """
        Run time-series regression of HML_RD on factor model.
        
        Uses Newey-West standard errors to account for autocorrelation.
        """
        try:
            import statsmodels.api as sm
            from statsmodels.stats.sandwich_covariance import cov_hac
        except ImportError:
            logger.warning("statsmodels not available for spanning tests")
            return None
        
        y = np.array(hml_rd)
        n = len(y)
        
        if n < 20:
            return SpanningTestResult(
                model_name=model_name,
                alpha=0, alpha_se=0, alpha_t=0, alpha_p=1,
                is_spanned=True,
                r_squared=0,
                n_observations=n,
                factor_loadings={},
                factor_t_stats={}
            )
        
        # Build X matrix
        X_cols = list(factors.keys())
        X = np.column_stack([np.array(factors[k]) for k in X_cols])
        X_with_const = sm.add_constant(X)
        
        # Run OLS
        model = sm.OLS(y, X_with_const)
        results = model.fit()
        
        # Get Newey-West standard errors (HAC). Lag choice depends on frequency:
        # - annual: small lags (e.g., 1–4)
        # - monthly: often 6–12
        nw_cov = cov_hac(results, nlags=int(max(0, nw_lags)))
        nw_se = np.sqrt(np.diag(nw_cov))
        
        # Extract alpha (intercept)
        alpha = results.params[0]
        alpha_se = nw_se[0]
        alpha_t = alpha / alpha_se if alpha_se > 0 else 0
        alpha_p = 2 * (1 - stats.t.cdf(abs(alpha_t), df=n - len(X_cols) - 1))
        alpha_p = float(alpha_p)
        
        # Factor loadings
        factor_loadings = {X_cols[i]: float(results.params[i + 1]) for i in range(len(X_cols))}
        factor_t_stats = {
            X_cols[i]: float(results.params[i + 1] / nw_se[i + 1]) if nw_se[i + 1] > 0 else 0
            for i in range(len(X_cols))
        }
        
        # Spanned if alpha is NOT significant at 5%
        is_spanned = bool(alpha_p >= 0.05)
        
        return SpanningTestResult(
            model_name=model_name,
            alpha=float(alpha),
            alpha_se=float(alpha_se),
            alpha_t=float(alpha_t),
            alpha_p=float(alpha_p),
            is_spanned=is_spanned,
            r_squared=float(results.rsquared),
            n_observations=n,
            factor_loadings=factor_loadings,
            factor_t_stats=factor_t_stats
        )
    
    async def run_all_spanning_tests(
        self,
        hml_rd_series: Dict[int, float],  # year -> HML_RD return (decimal)
        *,
        use_july_june: bool = True,
    ) -> Dict[str, Any]:
        """
        Run spanning tests against all standard factor models.
        
        Models tested:
        1. FF3: MKT-RF, SMB, HML
        2. FF3+MOM: Add momentum
        3. FF5: Add RMW, CMA
        4. FF5+MOM: Full model
        
        Returns:
            Dict with results for each model and interpretation
        """
        years = sorted(hml_rd_series.keys())
        
        if len(years) < 10:
            return {"error": "Insufficient data for spanning tests", "n_years": len(years)}
        
        # Get FF factors aligned to the return convention
        ff_factors = (
            await self.get_ff_factors_july_june(min(years), max(years))
            if use_july_june
            else await self.get_ff_factors_calendar(min(years), max(years), frequency="annual")
        )
        
        # Align data
        aligned_years = [y for y in years if y in ff_factors]
        
        if len(aligned_years) < 10:
            return {
                "error": "Insufficient factor data for spanning tests",
                "available_years": len(aligned_years),
                "required_years": 10
            }
        
        hml_rd = [hml_rd_series[y] for y in aligned_years]
        
        # Prepare factor series
        mkt_rf = [ff_factors[y]["mkt_rf"] for y in aligned_years]
        smb = [ff_factors[y]["smb"] for y in aligned_years]
        hml = [ff_factors[y]["hml"] for y in aligned_years]
        rmw = [ff_factors[y]["rmw"] for y in aligned_years]
        cma = [ff_factors[y]["cma"] for y in aligned_years]
        mom = [ff_factors[y]["mom"] for y in aligned_years]
        
        results = {}
        
        # FF3
        ff3_result = self.run_spanning_regression(
            hml_rd,
            {"mkt_rf": mkt_rf, "smb": smb, "hml": hml},
            "FF3",
            nw_lags=4,
        )
        if ff3_result:
            ci_low = float(ff3_result.alpha - 1.96 * ff3_result.alpha_se)
            ci_high = float(ff3_result.alpha + 1.96 * ff3_result.alpha_se)
            results["FF3"] = {
                "alpha": ff3_result.alpha,
                "alpha_se": ff3_result.alpha_se,
                "alpha_ci_95": {"low": ci_low, "high": ci_high},
                "alpha_t": ff3_result.alpha_t,
                "alpha_p": ff3_result.alpha_p,
                "is_spanned": ff3_result.is_spanned,
                "r_squared": ff3_result.r_squared,
                "factor_loadings": ff3_result.factor_loadings
            }
        
        # FF3 + MOM
        ff3mom_result = self.run_spanning_regression(
            hml_rd,
            {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "mom": mom},
            "FF3+MOM",
            nw_lags=4,
        )
        if ff3mom_result:
            ci_low = float(ff3mom_result.alpha - 1.96 * ff3mom_result.alpha_se)
            ci_high = float(ff3mom_result.alpha + 1.96 * ff3mom_result.alpha_se)
            results["FF3_MOM"] = {
                "alpha": ff3mom_result.alpha,
                "alpha_se": ff3mom_result.alpha_se,
                "alpha_ci_95": {"low": ci_low, "high": ci_high},
                "alpha_t": ff3mom_result.alpha_t,
                "alpha_p": ff3mom_result.alpha_p,
                "is_spanned": ff3mom_result.is_spanned,
                "r_squared": ff3mom_result.r_squared,
                "factor_loadings": ff3mom_result.factor_loadings
            }
        
        # FF5
        ff5_result = self.run_spanning_regression(
            hml_rd,
            {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "rmw": rmw, "cma": cma},
            "FF5",
            nw_lags=4,
        )
        if ff5_result:
            ci_low = float(ff5_result.alpha - 1.96 * ff5_result.alpha_se)
            ci_high = float(ff5_result.alpha + 1.96 * ff5_result.alpha_se)
            results["FF5"] = {
                "alpha": ff5_result.alpha,
                "alpha_se": ff5_result.alpha_se,
                "alpha_ci_95": {"low": ci_low, "high": ci_high},
                "alpha_t": ff5_result.alpha_t,
                "alpha_p": ff5_result.alpha_p,
                "is_spanned": ff5_result.is_spanned,
                "r_squared": ff5_result.r_squared,
                "factor_loadings": ff5_result.factor_loadings
            }
        
        # FF5 + MOM
        ff5mom_result = self.run_spanning_regression(
            hml_rd,
            {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "rmw": rmw, "cma": cma, "mom": mom},
            "FF5+MOM",
            nw_lags=4,
        )
        if ff5mom_result:
            ci_low = float(ff5mom_result.alpha - 1.96 * ff5mom_result.alpha_se)
            ci_high = float(ff5mom_result.alpha + 1.96 * ff5mom_result.alpha_se)
            results["FF5_MOM"] = {
                "alpha": ff5mom_result.alpha,
                "alpha_se": ff5mom_result.alpha_se,
                "alpha_ci_95": {"low": ci_low, "high": ci_high},
                "alpha_t": ff5mom_result.alpha_t,
                "alpha_p": ff5mom_result.alpha_p,
                "is_spanned": ff5mom_result.is_spanned,
                "r_squared": ff5mom_result.r_squared,
                "factor_loadings": ff5mom_result.factor_loadings
            }
        
        # Interpretation
        all_spanned = all(r.get("is_spanned", True) for r in results.values())
        
        return {
            "models": results,
            "n_years": len(aligned_years),
            "frequency": "annual",
            "interpretation": {
                "is_distinct_factor": not all_spanned,
                "summary": (
                    "R&D premium is NOT fully explained by standard factors (alpha is significant)" 
                    if not all_spanned else
                    "R&D premium may be explained by standard factors (alpha is not significant)"
                ),
                "recommendation": (
                    "The evidence suggests R&D intensity may represent a distinct pricing factor."
                    if not all_spanned else
                    "The R&D premium does not appear to be distinct from known factors."
                )
            },
            "latex_table": self._generate_spanning_latex(results)
        }

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
          - Compute *monthly* HML_RD returns within each July-June year using month-end split-adjusted
            closes plus dividend events (Tier-1 total-return proxy).
          - Regress monthly HML_RD on monthly FF factors; report alpha annualized (×12) for readability.
        """
        from datetime import date as _date
        from sqlalchemy import text
        from app.db.models import FamaFrenchFactor, SP500HistoricalConstituent

        if not use_july_june:
            return {"error": "Monthly spanning currently implemented for July-June convention only."}
        if data_tier != "tier1":
            return {"error": f"Monthly spanning currently supports Tier-1 only. Got data_tier={data_tier!r}."}

        # Membership availability (point-in-time S&P 500 constituents)
        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        monthly_rows: list[dict[str, Any]] = []

        # Build monthly HML_RD across all July-June windows.
        for return_year in range(int(start_return_year), int(end_return_year) + 1):
            formation_year = int(return_year) - 1
            formation_date = _date(int(return_year), 7, 1)
            # Include the prior month-end (June) so July return has a lag price.
            price_start = _date(int(return_year), 6, 1)
            price_end = _date(int(return_year) + 1, 6, 30)
            window_start_month = _date(int(return_year), 7, 1)
            window_end_month = _date(int(return_year) + 1, 6, 1)

            if membership_available:
                q = text("""
                    WITH members AS (
                        SELECT DISTINCT symbol
                        FROM sp500_historical_constituents
                        WHERE added_date <= :formation_date
                          AND (removed_date IS NULL OR removed_date >= :formation_date)
                    ),
                    rd_data AS (
                        SELECT
                            inc.symbol,
                            CASE
                                WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL
                            END AS rd_intensity
                        FROM fmp_income_statements inc
                        JOIN members m ON m.symbol = inc.symbol
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
                """)
                params = {
                    "formation_year": formation_year,
                    "formation_date": formation_date,
                    "price_start": price_start,
                    "price_end": price_end,
                    "window_start_month": window_start_month,
                    "window_end_month": window_end_month,
                }
            else:
                q = text("""
                    WITH rd_data AS (
                        SELECT
                            inc.symbol,
                            CASE
                                WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL
                            END AS rd_intensity
                        FROM fmp_income_statements inc
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
                """)
                params = {
                    "formation_year": formation_year,
                    "price_start": price_start,
                    "price_end": price_end,
                    "window_start_month": window_start_month,
                    "window_end_month": window_end_month,
                }

            result = await self.session.execute(q, params)
            for month, q1, q5, hml, n_q1, n_q5 in result.fetchall():
                if month is None or hml is None:
                    continue
                monthly_rows.append(
                    {
                        "date": month,  # month-start date
                        "hml_rd": float(hml),  # decimal return
                        "q1": float(q1) if q1 is not None else None,
                        "q5": float(q5) if q5 is not None else None,
                        "n_q1": int(n_q1 or 0),
                        "n_q5": int(n_q5 or 0),
                    }
                )

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

        aligned = [r for r in monthly_rows if r["date"] in ff_map and isinstance(r.get("hml_rd"), (int, float))]
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

        # Defensive: drop any months with missing factors in required columns (model by model)
        def _mask_valid(xs: list[float | None]) -> list[bool]:
            return [isinstance(x, (int, float)) for x in xs]

        results: Dict[str, Any] = {}
        nw_lags = 12  # monthly HAC convention
        annualize = 12.0  # report alpha annualized for readability

        def _store(model_key: str, res: Optional[SpanningTestResult]) -> None:
            if not res:
                return
            # Annualize alpha and its SE for reporting (t-stat and p-value unchanged).
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

        # FF3
        valid = [a and b and c and d for a, b, c, d in zip(_mask_valid(mkt_rf), _mask_valid(smb), _mask_valid(hml), [True]*len(dates))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store(
            "FF3",
            self.run_spanning_regression(
                [hml_rd[i] for i in idx],
                {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx]},
                "FF3",
                nw_lags=nw_lags,
            ),
        )

        # FF3 + MOM
        valid = [a and b and c and d for a, b, c, d in zip(_mask_valid(mkt_rf), _mask_valid(smb), _mask_valid(hml), _mask_valid(mom))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store(
            "FF3_MOM",
            self.run_spanning_regression(
                [hml_rd[i] for i in idx],
                {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "mom": [mom[i] for i in idx]},
                "FF3+MOM",
                nw_lags=nw_lags,
            ),
        )

        # FF5
        valid = [a and b and c and d and e for a, b, c, d, e in zip(_mask_valid(mkt_rf), _mask_valid(smb), _mask_valid(hml), _mask_valid(rmw), _mask_valid(cma))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store(
            "FF5",
            self.run_spanning_regression(
                [hml_rd[i] for i in idx],
                {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "rmw": [rmw[i] for i in idx], "cma": [cma[i] for i in idx]},
                "FF5",
                nw_lags=nw_lags,
            ),
        )

        # FF5 + MOM
        valid = [a and b and c and d and e and f for a, b, c, d, e, f in zip(_mask_valid(mkt_rf), _mask_valid(smb), _mask_valid(hml), _mask_valid(rmw), _mask_valid(cma), _mask_valid(mom))]
        idx = [i for i, ok in enumerate(valid) if ok]
        _store(
            "FF5_MOM",
            self.run_spanning_regression(
                [hml_rd[i] for i in idx],
                {"mkt_rf": [mkt_rf[i] for i in idx], "smb": [smb[i] for i in idx], "hml": [hml[i] for i in idx], "rmw": [rmw[i] for i in idx], "cma": [cma[i] for i in idx], "mom": [mom[i] for i in idx]},
                "FF5+MOM",
                nw_lags=nw_lags,
            ),
        )

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
    
    def _generate_spanning_latex(self, results: Dict) -> str:
        """Generate LaTeX table for spanning test results."""
        def sig_stars(p):
            if p < 0.01: return "***"
            if p < 0.05: return "**"
            if p < 0.10: return "*"
            return ""
        
        rows = []
        for model, data in results.items():
            alpha = data.get("alpha", 0)
            alpha_se = data.get("alpha_se", 0)
            ci = data.get("alpha_ci_95", {}) if isinstance(data.get("alpha_ci_95"), dict) else {}
            ci_low = ci.get("low", None)
            ci_high = ci.get("high", None)
            t_stat = data.get("alpha_t", 0)
            p_val = data.get("alpha_p", 1)
            r2 = data.get("r_squared", 0)
            alpha_pct = float(alpha) * 100.0
            alpha_se_pct = float(alpha_se) * 100.0 if isinstance(alpha_se, (int, float)) else 0.0
            ci_low_pct = float(ci_low) * 100.0 if isinstance(ci_low, (int, float)) else None
            ci_high_pct = float(ci_high) * 100.0 if isinstance(ci_high, (int, float)) else None
            ci_label = (
                f"[{ci_low_pct:.2f}, {ci_high_pct:.2f}]"
                if isinstance(ci_low_pct, (int, float)) and isinstance(ci_high_pct, (int, float))
                else "--"
            )
            rows.append(
                f"{model} & {alpha_pct:.2f} & {alpha_se_pct:.2f} & {ci_label} & {t_stat:.2f}{sig_stars(p_val)} & {r2:.3f} \\\\"
            )
        
        return f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Factor Spanning Tests for R\\&D Premium}}
\\label{{tab:spanning_tests}}
\\begin{{tabular}}{{lccccc}}
\\toprule
Model & Alpha (\\%/yr) & SE & 95\\% CI & t-stat & R$^2$ \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\multicolumn{{6}}{{l}}{{\\footnotesize Newey--West HAC standard errors. Stars denote significance: *** p < 0.01, ** p < 0.05, * p < 0.10.}} \\\\
\\end{{tabular}}
\\end{{table}}
"""


class MispricingAnalyzer:
    """
    Tests whether R&D premium is due to Mispricing (behavioral) vs Risk (rational).
    
    Mispricing Hypothesis:
    - Premium is higher where arbitrage is costly (illiquid, small, high idiosyncratic vol)
    - Premium is higher where investors are less sophisticated (low inst. ownership)
    
    Risk Hypothesis:
    - Premium is compensation for innovation risk
    - Premium should persist regardless of arbitrage costs
    
    Tests:
    1. Analyst Coverage: Premium higher in low-coverage stocks?
    2. Institutional Ownership: Premium higher in low-inst stocks?
    3. Idiosyncratic Volatility: Premium higher in high-ivol stocks?
    4. Liquidity: Premium higher in illiquid stocks?
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
        
        Returns:
            Dict with test results and interpretation
        """
        from sqlalchemy import text
        import pandas as pd
        from sqlalchemy import select
        from sqlalchemy import func
        from app.db.models import SP500HistoricalConstituent
        from datetime import date
        
        # Collect company-level data for each year
        all_data = []

        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)
        
        for year in range(start_year, end_year):
            # Return-year label used for delisting integration:
            # - July-June: return_year = formation_year + 1 (Jul start year)
            # - Calendar: return_year = year + 1
            return_year = year + 1

            if use_july_june:
                # Use July-June returns (formation_year = prior year)
                if membership_available:
                    q = text("""
                        WITH members AS (
                            SELECT DISTINCT symbol
                            FROM sp500_historical_constituents
                            WHERE added_date <= :formation_date
                              AND (removed_date IS NULL OR removed_date >= :formation_date)
                        ),
                        company_data AS (
                            SELECT 
                                inc.symbol,
                                inc.revenue,
                                CASE 
                                    WHEN inc.revenue > 100000000 
                                    THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL 
                                END as rd_intensity,
                                -- Proxy for size (liquidity proxy)
                                LOG(NULLIF(inc.revenue, 0)) as log_size,
                                -- Count of years with data (proxy for analyst coverage)
                                (
                                    SELECT COUNT(*) FROM fmp_income_statements i2 
                                    WHERE i2.symbol = inc.symbol 
                                    AND i2.fiscal_year <= inc.fiscal_year
                                ) as years_tracked,
                                -- Sector concentration (proxy for institutional interest)
                                (
                                    SELECT COUNT(*) FROM sp500_companies sp 
                                    WHERE sp.sector = (
                                        SELECT sector FROM sp500_companies WHERE symbol = inc.symbol LIMIT 1
                                    )
                                ) as sector_size
                            FROM fmp_income_statements inc
                            JOIN members m ON m.symbol = inc.symbol
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
                    """)
                else:
                    q = text("""
                    WITH company_data AS (
                        SELECT 
                            inc.symbol,
                            inc.revenue,
                            CASE 
                                WHEN inc.revenue > 100000000 
                                THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity,
                            -- Proxy for size (liquidity proxy)
                            LOG(NULLIF(inc.revenue, 0)) as log_size,
                            -- Count of years with data (proxy for analyst coverage)
                            (
                                SELECT COUNT(*) FROM fmp_income_statements i2 
                                WHERE i2.symbol = inc.symbol 
                                AND i2.fiscal_year <= inc.fiscal_year
                            ) as years_tracked,
                            -- Sector concentration (proxy for institutional interest)
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
                """)
            else:
                # Use calendar year returns (legacy)
                q = text("""
                    WITH company_data AS (
                        SELECT 
                            inc.symbol,
                            inc.revenue,
                            CASE 
                                WHEN inc.revenue > 100000000 
                                THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity,
                            -- Proxy for size (liquidity proxy)
                            LOG(NULLIF(inc.revenue, 0)) as log_size,
                            -- Count of years with data (proxy for analyst coverage)
                            (
                                SELECT COUNT(*) FROM fmp_income_statements i2 
                                WHERE i2.symbol = inc.symbol 
                                AND i2.fiscal_year <= inc.fiscal_year
                            ) as years_tracked,
                            -- Sector concentration (proxy for institutional interest)
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
                """)
            
            params = {"prior_year": year, "return_year": year + 1, "data_tier": data_tier}
            if use_july_june and membership_available:
                params["formation_date"] = date(int(return_year), 7, 1)
            result = await self.session.execute(q, params)
            rows = result.fetchall()
            
            for row in rows:
                symbol = row[0]
                return_pct = float(row[5]) if row[5] is not None else None
                if return_pct is None:
                    continue

                all_data.append({
                    "year": year,
                    "symbol": symbol,
                    "rd_intensity": float(row[1]) if row[1] else 0,
                    "log_size": float(row[2]) if row[2] else 0,
                    "years_tracked": int(row[3]) if row[3] else 0,
                    "sector_size": int(row[4]) if row[4] else 0,
                    "return_pct": float(return_pct),
                    "volatility": float(row[6]) if row[6] else 0.3  # Default vol
                })
        
        if len(all_data) < 100:
            return {"error": "Insufficient data for mispricing tests"}
        
        df = pd.DataFrame(all_data)
        
        # ----------------------------------------------------------------------
        # Conditional sorting (publication-grade, avoids missing cells)
        # ----------------------------------------------------------------------
        # We compute the R&D premium (Q5–Q1) within each arbitrage-cost proxy bucket,
        # by year, then average across years. This avoids pooling bias and ensures
        # each bucket has its own internal R&D quintiles (so Q1/Q5 exist by construction).
        #
        # Proxy definitions:
        # - Size: terciles of log(revenue) within year (liquidity proxy)
        # - Volatility: terciles of July–June volatility within year
        # - Coverage: terciles of years_tracked within year (PROXY, not analyst coverage)

        def _safe_qcut(series: "pd.Series", q: int, labels: list) -> "pd.Series":
            """Robust qcut with fallback when there are too few unique values."""
            ranked = series.rank(method="first")
            try:
                return pd.qcut(ranked, q, labels=labels)
            except ValueError:
                return pd.cut(ranked, q, labels=labels)

        # Build proxy buckets within each year (stabilizes across regimes)
        df["size_tercile"] = df.groupby("year")["log_size"].transform(
            lambda s: _safe_qcut(s, 3, ["Small", "Medium", "Large"])
        )
        df["vol_tercile"] = df.groupby("year")["volatility"].transform(
            lambda s: _safe_qcut(s, 3, ["Low", "Medium", "High"])
        )
        df["coverage_tercile"] = df.groupby("year")["years_tracked"].transform(
            lambda s: _safe_qcut(s, 3, ["Low", "Medium", "High"])
        )

        def _conditional_rd_premium(
            data: "pd.DataFrame",
            proxy_col: str,
            proxy_label: str,
        ) -> Dict[str, Any]:
            """
            Compute mean (by-year) Q5–Q1 premium within a proxy bucket.

            Returns dict with:
              - premium: mean premium (%) across years (float)
              - n_obs: total observations contributing (int)
              - n_years: number of years contributing (int)
              - method: 'by_year' or fallback
            """
            subset_all = data[data[proxy_col] == proxy_label]
            if subset_all.empty:
                return {"premium": None, "n_obs": 0, "n_years": 0, "method": "empty"}

            premiums_by_year: list[float] = []
            n_obs_total = 0
            n_years_used = 0

            for y, sub in subset_all.groupby("year"):
                # Need enough firms to define quintiles
                if len(sub) < 10:
                    continue
                sub = sub.copy()
                sub["rd_quintile"] = _safe_qcut(sub["rd_intensity"], 5, [1, 2, 3, 4, 5])

                q5 = sub[sub["rd_quintile"] == 5]["return_pct"].mean()
                q1 = sub[sub["rd_quintile"] == 1]["return_pct"].mean()
                if pd.isna(q5) or pd.isna(q1):
                    continue

                premiums_by_year.append(float(q5 - q1))
                n_obs_total += int(len(sub))
                n_years_used += 1

            if premiums_by_year:
                return {
                    "premium": round(float(sum(premiums_by_year) / len(premiums_by_year)), 2),
                    "n_obs": int(n_obs_total),
                    "n_years": int(n_years_used),
                    "method": "by_year",
                }

            # Fallback (should be rare): pooled conditional sort within the proxy bucket.
            pooled = subset_all.copy()
            if len(pooled) >= 10:
                pooled["rd_quintile"] = _safe_qcut(pooled["rd_intensity"], 5, [1, 2, 3, 4, 5])
                q5 = pooled[pooled["rd_quintile"] == 5]["return_pct"].mean()
                q1 = pooled[pooled["rd_quintile"] == 1]["return_pct"].mean()
                if pd.notna(q5) and pd.notna(q1):
                    return {
                        "premium": round(float(q5 - q1), 2),
                        "n_obs": int(len(pooled)),
                        "n_years": 0,
                        "method": "pooled_fallback",
                    }

            return {"premium": None, "n_obs": int(len(subset_all)), "n_years": 0, "method": "insufficient"}

        results: Dict[str, Any] = {}
        
        # Test 1: R&D premium by Size (conditional on size tercile)
        results["by_size"] = {
            size: _conditional_rd_premium(df, "size_tercile", size)
            for size in ["Small", "Medium", "Large"]
        }
        
        # Test 2: R&D premium by Volatility (conditional on volatility tercile)
        results["by_volatility"] = {
            vol: _conditional_rd_premium(df, "vol_tercile", vol)
            for vol in ["Low", "Medium", "High"]
        }
        
        # Test 3: R&D premium by Coverage proxy (years_tracked; proxy only)
        results["by_coverage"] = {
            cov: _conditional_rd_premium(df, "coverage_tercile", cov)
            for cov in ["Low", "Medium", "High"]
        }
        
        # Interpret: Mispricing hypothesis predicts premium is higher in:
        # - Small stocks (vs Large)
        # - High volatility (vs Low)
        # - Low coverage (vs High)
        
        mispricing_evidence = 0
        
        small_premium = results.get("by_size", {}).get("Small", {}).get("premium")
        large_premium = results.get("by_size", {}).get("Large", {}).get("premium")
        if small_premium and large_premium and small_premium > large_premium:
            mispricing_evidence += 1
        
        high_vol_premium = results.get("by_volatility", {}).get("High", {}).get("premium")
        low_vol_premium = results.get("by_volatility", {}).get("Low", {}).get("premium")
        if high_vol_premium and low_vol_premium and high_vol_premium > low_vol_premium:
            mispricing_evidence += 1
        
        low_cov_premium = results.get("by_coverage", {}).get("Low", {}).get("premium")
        high_cov_premium = results.get("by_coverage", {}).get("High", {}).get("premium")
        if low_cov_premium and high_cov_premium and low_cov_premium > high_cov_premium:
            mispricing_evidence += 1
        
        # Interpretation
        if mispricing_evidence >= 2:
            interpretation = "MISPRICING"
            explanation = (
                "The R&D premium is higher in stocks with higher arbitrage costs "
                "(smaller firms, higher volatility, lower analyst coverage). "
                "This pattern is consistent with a behavioral/mispricing explanation: "
                "investors underreact to R&D information, and the mispricing persists "
                "because arbitrage is costly."
            )
        else:
            interpretation = "RISK"
            explanation = (
                "The R&D premium does not concentrate in hard-to-arbitrage stocks. "
                "This pattern is more consistent with a risk-based explanation: "
                "high R&D firms have higher expected returns because they are exposed "
                "to innovation risk that investors dislike."
            )
        
        return {
            "tests": results,
            "total_observations": len(df),
            "n_years": int(df["year"].nunique()),
            "mispricing_evidence_count": mispricing_evidence,
            "interpretation": {
                "likely_explanation": interpretation,
                "confidence": "High" if mispricing_evidence >= 2 else "Medium",
                "explanation": explanation
            },
            "proxy_notes": {
                "coverage": "Coverage is proxied by years_tracked (count of historical income statement years), not analyst coverage.",
            },
            "latex_summary": self._generate_mispricing_latex(results)
        }
    
    def _generate_mispricing_latex(self, results: Dict) -> str:
        """Generate LaTeX table for mispricing tests."""
        rows = []
        
        # By Size
        for size in ["Small", "Medium", "Large"]:
            prem = results.get("by_size", {}).get(size, {}).get("premium", "-")
            n = results.get("by_size", {}).get(size, {}).get("n_obs", 0)
            rows.append(f"Size: {size} & {prem} & {n}")
        
        # By Volatility
        for vol in ["Low", "Medium", "High"]:
            prem = results.get("by_volatility", {}).get(vol, {}).get("premium", "-")
            n = results.get("by_volatility", {}).get(vol, {}).get("n_obs", 0)
            rows.append(f"Volatility: {vol} & {prem} & {n}")
        
        # By Coverage
        for cov in ["Low", "Medium", "High"]:
            prem = results.get("by_coverage", {}).get(cov, {}).get("premium", "-")
            n = results.get("by_coverage", {}).get(cov, {}).get("n_obs", 0)
            rows.append(f"Coverage: {cov} & {prem} & {n}")
        
        # NOTE: Avoid backslashes inside f-string expressions (Python limitation).
        latex_rows = chr(10).join([r + " \\\\" for r in rows])

        return f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{R\\&D Premium by Arbitrage Cost Proxies}}
\\label{{tab:mispricing_tests}}
\\begin{{tabular}}{{lcc}}
\\toprule
Group & R\\&D Premium (\\%) & N \\\\
\\midrule
{latex_rows}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


class LiquidityModerationAnalyzer:
    """
    Liquidity moderation test for the characteristic premium (HML_RD = Q5 − Q1).

    PURPOSE:
      Provide a direct, publication-grade proxy for information frictions by conditioning the
      R&D premium on liquidity / illiquidity, motivated by Ahmed, Bu, and Ye (2025).

    WHY:
      Size is an imperfect proxy for trading frictions and information asymmetry. A direct
      liquidity proxy reduces reviewer friction when interpreting “mispricing vs risk”.

    METHOD (Tier-1, July-June aligned):
      - Compute pre-formation liquidity over Jul(Y)-Jun(Y+1) for formation_year = Y.
      - Bucket stocks into terciles by liquidity within each formation year.
      - Within each tercile, compute internal RD quintiles and the Q5−Q1 premium by year.
      - Aggregate across years and report mean premium + Newey-West t-stat on the annual series.

    OUTPUT:
      Two panels:
        (A) Amihud (2002) illiquidity using daily close returns and dollar volume
        (B) Dollar volume proxy (avg close × volume), inverted so higher = more illiquid
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
        from sqlalchemy import text
        import pandas as pd
        import numpy as np

        # Reuse the publication-grade HAC utility (Newey-West) used elsewhere in the paper.
        from app.services.statistics import StatisticalAnalyzer

        if end_formation_year <= start_formation_year:
            return {"error": "end_formation_year must be > start_formation_year"}

        q = text(
            """
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
        )

        result = await self.session.execute(
            q,
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
                "formation_year",
                "symbol",
                "rd_intensity",
                "return_pct",
                "trading_days",
                "amihud_illiq",
                "avg_dollar_volume",
            ],
        )

        def _safe_qcut(series: "pd.Series", qn: int, labels: list[str]) -> "pd.Series":
            ranked = series.rank(method="first")
            try:
                return pd.qcut(ranked, qn, labels=labels)
            except ValueError:
                return pd.cut(ranked, qn, labels=labels)

        # Liquidity terciles
        df["amihud_bucket"] = df.groupby("formation_year")["amihud_illiq"].transform(
            lambda s: _safe_qcut(s, 3, ["Liquid", "Medium", "Illiquid"])
        )
        # Dollar volume: invert so “Illiquid” means lower dollar volume
        df["dvol_bucket"] = df.groupby("formation_year")["avg_dollar_volume"].transform(
            lambda s: _safe_qcut((-s), 3, ["Liquid", "Medium", "Illiquid"])
        )

        def _assign_rd_quintiles(sub: "pd.DataFrame") -> "pd.DataFrame":
            sub = sub.copy()
            sub["rd_quintile"] = _safe_qcut(sub["rd_intensity"], 5, [1, 2, 3, 4, 5])
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
                out.append(
                    {
                        "formation_year": int(y),
                        "bucket": str(b),
                        "premium": float(q5 - q1),
                        "n_firms": int(len(sub2)),
                    }
                )
            return pd.DataFrame(out)

        amihud_yearly = _yearly_premiums("amihud_bucket")
        dvol_yearly = _yearly_premiums("dvol_bucket")

        if amihud_yearly.empty or dvol_yearly.empty:
            return {"error": "Insufficient yearly bucket data for liquidity moderation."}

        stats = StatisticalAnalyzer(self.session, use_july_june=True, data_tier=data_tier)

        def _summarize(yearly: "pd.DataFrame") -> Dict[str, Any]:
            buckets: dict[str, Any] = {}
            for name in ["Liquid", "Medium", "Illiquid"]:
                s = yearly[yearly["bucket"] == name].sort_values("formation_year")
                series = s["premium"].tolist()
                hac = stats.compute_hac_ttest(series, hypothesis_value=0.0, lags=1)
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
                hac_spread = stats.compute_hac_ttest(spread_series, hypothesis_value=0.0, lags=1)
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
                "proxy": "Average daily dollar volume (close × volume), inverted for 'Illiquid' bucket",
                **_summarize(dvol_yearly),
            },
            "note": (
                "This is a descriptive conditional-sort diagnostic (not primary inference). "
                "Motivated by evidence that the R&D premium strengthens with illiquidity."
            ),
        }
