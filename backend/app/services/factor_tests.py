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
        model_name: str
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
        
        # Get Newey-West standard errors
        nw_cov = cov_hac(results, nlags=4)  # 4 lags for annual data
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
            "FF3"
        )
        if ff3_result:
            results["FF3"] = {
                "alpha": ff3_result.alpha,
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
            "FF3+MOM"
        )
        if ff3mom_result:
            results["FF3_MOM"] = {
                "alpha": ff3mom_result.alpha,
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
            "FF5"
        )
        if ff5_result:
            results["FF5"] = {
                "alpha": ff5_result.alpha,
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
            "FF5+MOM"
        )
        if ff5mom_result:
            results["FF5_MOM"] = {
                "alpha": ff5mom_result.alpha,
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
            t_stat = data.get("alpha_t", 0)
            p_val = data.get("alpha_p", 1)
            r2 = data.get("r_squared", 0)
            alpha_pct = float(alpha) * 100.0
            rows.append(
                f"{model} & {alpha_pct:.2f} & {t_stat:.2f} & {r2:.3f} & {sig_stars(p_val)} \\\\"
            )
        
        return f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Factor Spanning Tests for R\\&D Premium}}
\\label{{tab:spanning_tests}}
\\begin{{tabular}}{{lcccc}}
\\toprule
Model & Alpha (\\%) & t-stat & R$^2$ & \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\multicolumn{{5}}{{l}}{{\\footnotesize *** p < 0.01, ** p < 0.05, * p < 0.10. Alpha is annual percent.}} \\\\
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
        use_july_june: bool = True
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

        from app.db.models import DelistingReturn
        from app.services.delisting_utils import bounds_for_return_year
        
        # Collect company-level data for each year
        all_data = []
        
        for year in range(start_year, end_year):
            # Return-year label used for delisting integration:
            # - July-June: return_year = formation_year + 1 (Jul start year)
            # - Calendar: return_year = year + 1
            return_year = year + 1
            start_date, end_date = bounds_for_return_year(return_year, use_july_june=use_july_june)

            delist_result = await self.session.execute(
                select(DelistingReturn.symbol, DelistingReturn.delist_return)
                .where(
                    DelistingReturn.delist_date.isnot(None),
                    DelistingReturn.delist_date >= start_date,
                    DelistingReturn.delist_date <= end_date,
                )
            )
            # Store as pct to match return_pct fields
            year_delistings = {r.symbol: float(r.delist_return) * 100 for r in delist_result.fetchall()}

            if use_july_june:
                # Use July-June returns (formation_year = prior year)
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
                    ),
                    volatility AS (
                        SELECT symbol, volatility as vol
                        FROM july_june_returns
                        WHERE formation_year = :prior_year
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
            
            result = await self.session.execute(q, {"prior_year": year, "return_year": year + 1})
            rows = result.fetchall()
            
            for row in rows:
                symbol = row[0]
                # Integrate delisting returns for survivorship correction (publication-grade)
                # If the company delisted during the return period, use delisting return instead
                return_pct = year_delistings.get(symbol)
                if return_pct is None:
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
        
        # Create R&D quintiles
        df["rd_quintile"] = pd.qcut(df["rd_intensity"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        
        # Create proxies for mispricing
        # 1. Size (smaller = harder to arbitrage)
        df["size_tercile"] = pd.qcut(df["log_size"], 3, labels=["Small", "Medium", "Large"])
        
        # 2. Volatility (higher = higher arbitrage risk)
        df["vol_tercile"] = pd.qcut(
            df["volatility"].rank(method="first"), 3, labels=["Low", "Medium", "High"]
        )
        
        # 3. Years tracked (proxy for analyst coverage - more years = more coverage)
        df["coverage_tercile"] = pd.qcut(
            df["years_tracked"].rank(method="first"), 3, labels=["Low", "Medium", "High"]
        )
        
        results = {}
        
        # Test 1: R&D premium by Size
        size_premiums = {}
        for size in ["Small", "Medium", "Large"]:
            subset = df[df["size_tercile"] == size]
            q5_ret = subset[subset["rd_quintile"] == 5]["return_pct"].mean()
            q1_ret = subset[subset["rd_quintile"] == 1]["return_pct"].mean()
            size_premiums[size] = {
                "premium": round(q5_ret - q1_ret, 2) if pd.notna(q5_ret) and pd.notna(q1_ret) else None,
                "n_obs": len(subset)
            }
        results["by_size"] = size_premiums
        
        # Test 2: R&D premium by Volatility
        vol_premiums = {}
        for vol in ["Low", "Medium", "High"]:
            subset = df[df["vol_tercile"] == vol]
            q5_ret = subset[subset["rd_quintile"] == 5]["return_pct"].mean()
            q1_ret = subset[subset["rd_quintile"] == 1]["return_pct"].mean()
            vol_premiums[vol] = {
                "premium": round(q5_ret - q1_ret, 2) if pd.notna(q5_ret) and pd.notna(q1_ret) else None,
                "n_obs": len(subset)
            }
        results["by_volatility"] = vol_premiums
        
        # Test 3: R&D premium by Analyst Coverage proxy
        coverage_premiums = {}
        for cov in ["Low", "Medium", "High"]:
            subset = df[df["coverage_tercile"] == cov]
            q5_ret = subset[subset["rd_quintile"] == 5]["return_pct"].mean()
            q1_ret = subset[subset["rd_quintile"] == 1]["return_pct"].mean()
            coverage_premiums[cov] = {
                "premium": round(q5_ret - q1_ret, 2) if pd.notna(q5_ret) and pd.notna(q1_ret) else None,
                "n_obs": len(subset)
            }
        results["by_coverage"] = coverage_premiums
        
        # Interpret: Mispricing hypothesis predicts premium is higher in:
        # - Small stocks (vs Large)
        # - High volatility (vs Low)
        # - Low coverage (vs High)
        
        mispricing_evidence = 0
        
        small_premium = size_premiums.get("Small", {}).get("premium")
        large_premium = size_premiums.get("Large", {}).get("premium")
        if small_premium and large_premium and small_premium > large_premium:
            mispricing_evidence += 1
        
        high_vol_premium = vol_premiums.get("High", {}).get("premium")
        low_vol_premium = vol_premiums.get("Low", {}).get("premium")
        if high_vol_premium and low_vol_premium and high_vol_premium > low_vol_premium:
            mispricing_evidence += 1
        
        low_cov_premium = coverage_premiums.get("Low", {}).get("premium")
        high_cov_premium = coverage_premiums.get("High", {}).get("premium")
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
            "n_years": end_year - start_year,
            "mispricing_evidence_count": mispricing_evidence,
            "interpretation": {
                "likely_explanation": interpretation,
                "confidence": "High" if mispricing_evidence >= 2 else "Medium",
                "explanation": explanation
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
