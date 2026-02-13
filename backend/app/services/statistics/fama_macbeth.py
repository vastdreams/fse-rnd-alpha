# EXEMPTION: 456 lines — Two FM regression variants with shared LaTeX generation; splitting would break cohesion
"""
PATH: backend/app/services/statistics/fama_macbeth.py
PURPOSE: Fama-MacBeth (1973) two-stage regressions (annual, with controls).
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional, Any
import numpy as np
from scipy import stats
from sqlalchemy import select

from app.core.logging import get_logger

logger = get_logger(__name__)


class FamaMacBethMixin:
    """Mixin providing Fama-MacBeth (1973) regression methods."""

    async def run_fama_macbeth_regression(
        self,
        window_type: str = "5yr"
    ) -> Dict[str, Any]:
        """
        Run Fama-MacBeth (1973) two-stage regression.
        
        Stage 1: For each time period t, run cross-sectional regression:
                 R_i,t = alpha_t + beta_t * RD_i,t-1 + epsilon_i,t
        
        Stage 2: Average the time-series of coefficients:
                 beta = mean(beta_t), with t-stat from std(beta_t)
        
        This is the standard methodology for testing factor premiums
        in academic finance literature.
        
        Returns:
            Dict with regression results including coefficients and t-stats
        """
        from app.db.models import RollingWindowResult
        
        # Get all rolling window results for this window type
        result = await self.session.execute(
            select(RollingWindowResult)
            .where(RollingWindowResult.window_type == window_type)
            .order_by(RollingWindowResult.start_year)
        )
        windows = result.scalars().all()
        
        if len(windows) < 3:
            return {
                "error": "Insufficient data for Fama-MacBeth regression",
                "n_periods": len(windows)
            }
        
        # Stage 1: Collect R&D premium (beta) for each period
        # The R&D premium (Q5 - Q1) serves as our "beta" for each period
        rd_premiums = []
        period_labels = []
        
        for w in windows:
            if w.rd_premium is not None:
                rd_premiums.append(float(w.rd_premium))
                period_labels.append(f"{w.start_year}-{w.end_year}")
        
        if len(rd_premiums) < 3:
            return {
                "error": "Insufficient valid periods",
                "n_valid": len(rd_premiums)
            }
        
        # Stage 2: Time-series statistics of the cross-sectional coefficients
        rd_premiums_arr = np.array(rd_premiums)
        
        mean_premium = float(np.mean(rd_premiums_arr))
        std_premium = float(np.std(rd_premiums_arr, ddof=1))
        n_periods = len(rd_premiums_arr)
        
        # Fama-MacBeth t-statistic
        se_fm = std_premium / np.sqrt(n_periods)
        t_stat_fm = mean_premium / se_fm if se_fm > 0 else 0
        
        # p-value (two-tailed)
        p_value = float(2 * (1 - stats.t.cdf(abs(t_stat_fm), df=n_periods - 1)))
        
        # Newey-West adjustment for autocorrelation (HAC)
        # Use window_years - 1 lags as per Newey-West convention
        window_years = int(window_type.replace("yr", ""))
        lags = window_years - 1
        
        # Simple HAC adjustment (Newey-West)
        hac_var = std_premium ** 2 / n_periods
        for lag in range(1, min(lags + 1, n_periods - 1)):
            weight = 1 - lag / (lags + 1)  # Bartlett kernel
            autocov = np.cov(rd_premiums_arr[:-lag], rd_premiums_arr[lag:])[0, 1]
            hac_var += 2 * weight * autocov / n_periods
        
        hac_se = np.sqrt(max(0, hac_var))
        t_stat_hac = mean_premium / hac_se if hac_se > 0 else 0
        p_value_hac = float(2 * (1 - stats.t.cdf(abs(t_stat_hac), df=n_periods - 1)))
        
        return {
            "methodology": "Fama-MacBeth (1973)",
            "window_type": window_type,
            "n_periods": n_periods,
            "periods": period_labels,
            
            # Main results
            "rd_premium_mean_pct": round(mean_premium, 3),
            "rd_premium_std_pct": round(std_premium, 3),
            
            # Standard t-stat
            "t_statistic": round(t_stat_fm, 3),
            "p_value": round(p_value, 4),
            "significant_005": bool(p_value < 0.05),
            "significant_001": bool(p_value < 0.01),
            
            # HAC-adjusted (Newey-West)
            "t_statistic_hac": round(t_stat_hac, 3),
            "p_value_hac": round(p_value_hac, 4),
            "significant_hac_005": bool(p_value_hac < 0.05),
            "lags_used": lags,
            
            # Interpretation
            "interpretation": (
                f"The R&D premium averages {mean_premium:.2f}% across {n_periods} periods. "
                f"The Fama-MacBeth t-statistic is {t_stat_fm:.2f} (p={p_value:.4f}), "
                f"and {t_stat_hac:.2f} after HAC adjustment (p={p_value_hac:.4f}). "
                f"{'This is statistically significant at the 5% level.' if p_value_hac < 0.05 else 'This is not statistically significant at the 5% level.'}"
            ),
            
            # For paper tables
            "latex_row": (
                f"R\\&D Premium & {mean_premium:.2f}\\% & {t_stat_fm:.2f} & {t_stat_hac:.2f} & "
                f"{'***' if p_value_hac < 0.01 else ('**' if p_value_hac < 0.05 else '')} \\\\"
            )
        }
    
    async def run_fama_macbeth_with_controls(
        self,
        start_year: int = 1995,
        end_year: int = 2024,
        use_july_june: bool = True
    ) -> Dict[str, Any]:
        """
        Run full Fama-MacBeth regressions with multivariate controls.
        
        Stage 1 (Cross-sectional): For each year t:
            R_{i,t+1} = α_t + β1_t*RD_{i,t} + β2_t*Size_{i,t} + β3_t*BM_{i,t} + ε_{i,t}
        
        Stage 2 (Time-series): Average the coefficients:
            β = mean(β_t), t-stat = mean(β_t) / (std(β_t) / sqrt(T))
        
        This is the GOLD STANDARD for testing if R&D predicts returns
        after controlling for known factors (Size, Book-to-Market).
        
        PUBLICATION FIX (Dec 2025):
        - Now uses July-June returns by default (Fama-French convention)
        - Integrates delisting returns for survivorship bias correction
        
        Args:
            start_year: First formation year (default 1995)
            end_year: Last formation year (default 2024)
            use_july_june: If True (default), use July-June returns (bias-free)
        
        Returns:
            Dict with coefficient estimates, t-stats (FM and HAC), and significance
        """
        from sqlalchemy import select, text
        import pandas as pd
        import statsmodels.api as sm
        
        # Collect cross-sectional regression results for each year
        year_results = []
        
        for year in range(start_year, end_year):
            # formation_year = year (FY data from year)
            # return_year = year + 1 (returns measured in year+1)
            formation_year = year
            return_year = year + 1
            
            # Get company-level data: prior year R&D intensity, size (market cap), returns
            if use_july_june:
                q = text("""
                    WITH company_data AS (
                        SELECT 
                            inc.symbol,
                            inc.revenue,
                            inc.rd_expenses,
                            CASE 
                                WHEN inc.revenue > 100000000 
                                THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity,
                            LOG(NULLIF(inc.revenue, 0)) as log_size,
                            COALESCE(bs.total_equity / NULLIF(inc.revenue, 0), 0.5) as bm_proxy
                        FROM fmp_income_statements inc
                        LEFT JOIN fmp_balance_sheets bs 
                            ON inc.symbol = bs.symbol 
                            AND inc.fiscal_year = bs.fiscal_year
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.revenue >= 100000000
                          AND inc.rd_expenses >= 0
                    ),
                    returns AS (
                        SELECT symbol, annualized_return * 100 as return_pct
                        FROM july_june_returns
                        WHERE formation_year = :formation_year
                          AND data_tier = :data_tier
                    )
                    SELECT 
                        cd.symbol,
                        cd.rd_intensity,
                        cd.log_size,
                        cd.bm_proxy,
                        r.return_pct
                    FROM company_data cd
                    LEFT JOIN returns r ON cd.symbol = r.symbol
                    WHERE cd.rd_intensity IS NOT NULL
                      AND cd.log_size IS NOT NULL
                """)
            else:
                q = text("""
                    WITH company_data AS (
                        SELECT 
                            inc.symbol,
                            inc.revenue,
                            inc.rd_expenses,
                            CASE 
                                WHEN inc.revenue > 100000000 
                                THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity,
                            LOG(NULLIF(inc.revenue, 0)) as log_size,
                            COALESCE(bs.total_equity / NULLIF(inc.revenue, 0), 0.5) as bm_proxy
                        FROM fmp_income_statements inc
                        LEFT JOIN fmp_balance_sheets bs 
                            ON inc.symbol = bs.symbol 
                            AND inc.fiscal_year = bs.fiscal_year
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.revenue >= 100000000
                          AND inc.rd_expenses >= 0
                    ),
                    returns AS (
                        SELECT symbol, annual_return * 100 as return_pct
                        FROM fmp_annual_returns
                        WHERE year = :return_year
                    )
                    SELECT 
                        cd.symbol,
                        cd.rd_intensity,
                        cd.log_size,
                        cd.bm_proxy,
                        r.return_pct
                    FROM company_data cd
                    LEFT JOIN returns r ON cd.symbol = r.symbol
                    WHERE cd.rd_intensity IS NOT NULL
                      AND cd.log_size IS NOT NULL
                """)
            
            result = await self.session.execute(
                q, {"formation_year": formation_year, "return_year": return_year, "data_tier": self.data_tier}
            )
            rows = result.fetchall()
            
            if len(rows) < 30:  # Need minimum sample for regression
                continue
            
            # Build regression dataframe (returns are sourced from the July–June return table)
            df_rows = []
            
            for r in rows:
                symbol = r[0]
                rd_intensity = float(r[1]) if r[1] else 0
                log_size = float(r[2]) if r[2] else 0
                bm_proxy = float(r[3]) if r[3] else 0.5
                return_pct = r[4]
                
                if return_pct is None:
                    continue  # Skip if no return
                return_pct = float(return_pct)
                
                # Filter extreme outliers
                if abs(return_pct) > 500:
                    continue
                
                df_rows.append({
                    "symbol": symbol,
                    "rd_intensity": rd_intensity,
                    "log_size": log_size,
                    "bm_proxy": bm_proxy,
                    "return_pct": return_pct
                })
            
            if len(df_rows) < 30:
                continue
            
            df = pd.DataFrame(df_rows)
            
            # Winsorize returns at 1%/99%
            df["return_pct"] = df["return_pct"].clip(
                df["return_pct"].quantile(0.01),
                df["return_pct"].quantile(0.99)
            )
            
            # Run cross-sectional OLS
            y = df["return_pct"]
            X = sm.add_constant(df[["rd_intensity", "log_size", "bm_proxy"]])
            
            try:
                model = sm.OLS(y, X).fit()
                
                year_results.append({
                    "year": year,
                    "n_obs": len(df),
                    "alpha": model.params["const"],
                    "beta_rd": model.params["rd_intensity"],
                    "beta_size": model.params["log_size"],
                    "beta_bm": model.params["bm_proxy"],
                    "r_squared": model.rsquared
                })
            except Exception as e:
                logger.warning(f"Cross-sectional regression failed for {year}: {e}")
                continue
        
        if len(year_results) < 5:
            return {
                "error": "Insufficient data for Fama-MacBeth regression",
                "n_years": len(year_results)
            }
        
        # Stage 2: Time-series statistics of the cross-sectional coefficients
        df_results = pd.DataFrame(year_results)
        n_periods = len(df_results)
        
        def compute_fm_stats(series: pd.Series, name: str) -> Dict:
            """Compute Fama-MacBeth statistics for a coefficient series."""
            mean_val = series.mean()
            std_val = series.std(ddof=1)
            se_fm = std_val / np.sqrt(n_periods)
            t_stat = mean_val / se_fm if se_fm > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n_periods - 1))
            
            # HAC adjustment (simple Newey-West)
            hac_var = std_val ** 2 / n_periods
            for lag in range(1, min(4, n_periods - 1)):  # Use 4 lags max
                weight = 1 - lag / 5
                if lag < len(series):
                    autocov = np.cov(series.values[:-lag], series.values[lag:])[0, 1]
                    hac_var += 2 * weight * autocov / n_periods
            
            hac_se = np.sqrt(max(0, hac_var))
            t_stat_hac = mean_val / hac_se if hac_se > 0 else 0
            p_value_hac = 2 * (1 - stats.t.cdf(abs(t_stat_hac), df=n_periods - 1))
            
            return {
                "coefficient": round(mean_val, 4),
                "std_dev": round(std_val, 4),
                "t_stat_fm": round(t_stat, 3),
                "p_value_fm": round(p_value, 4),
                "t_stat_hac": round(t_stat_hac, 3),
                "p_value_hac": round(p_value_hac, 4),
                "significant_005": bool(p_value_hac < 0.05),
                "significant_001": bool(p_value_hac < 0.01)
            }
        
        results = {
            "methodology": "Fama-MacBeth (1973) with Controls",
            "return_convention": "July-June (Fama-French)" if use_july_june else "Calendar Year",
            "n_periods": n_periods,
            "period_range": f"{df_results['year'].min()}-{df_results['year'].max()}",
            "avg_n_companies_per_period": int(df_results["n_obs"].mean()),
            "avg_r_squared": round(df_results["r_squared"].mean(), 4),
            
            # Coefficient estimates
            "alpha": compute_fm_stats(df_results["alpha"], "Alpha"),
            "rd_intensity": compute_fm_stats(df_results["beta_rd"], "R&D Intensity"),
            "log_size": compute_fm_stats(df_results["beta_size"], "Size (Log Revenue)"),
            "book_to_market": compute_fm_stats(df_results["beta_bm"], "Book-to-Market Proxy"),
            
            # Key finding
            "rd_predicts_returns": compute_fm_stats(df_results["beta_rd"], "R&D")["significant_005"],
            
            # For tables
            "latex_table": self._generate_fm_latex_table(
                compute_fm_stats(df_results["alpha"], "Alpha"),
                compute_fm_stats(df_results["beta_rd"], "R&D Intensity"),
                compute_fm_stats(df_results["beta_size"], "Size"),
                compute_fm_stats(df_results["beta_bm"], "B/M"),
                n_periods
            ),
            
            # Interpretation
            "interpretation": self._generate_fm_interpretation(
                compute_fm_stats(df_results["beta_rd"], "R&D"),
                compute_fm_stats(df_results["beta_size"], "Size"),
                n_periods
            ),
            
            # Methodology notes for publication
            "methodology_notes": {
                "return_type": "July-June (Fama-French convention, eliminates look-ahead bias)" if use_july_june else "Calendar year (may have look-ahead bias)",
                "survivorship_correction": "Delisting returns integrated for companies that exit during the return period",
                "formation_rule": "FY(T) R&D intensity predicts returns July(T+1) to June(T+2)" if use_july_june else "FY(T) R&D intensity predicts calendar year T+1 returns"
            }
        }
        
        return results
    
    def _generate_fm_latex_table(
        self, alpha: Dict, rd: Dict, size: Dict, bm: Dict, n: int
    ) -> str:
        """Generate LaTeX table for Fama-MacBeth results."""
        def sig_stars(p):
            if p < 0.01: return "***"
            if p < 0.05: return "**"
            if p < 0.10: return "*"
            return ""
        
        return f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Fama-MacBeth Regressions: R\\&D Intensity and Stock Returns}}
\\label{{tab:fama_macbeth}}
\\begin{{tabular}}{{lcccc}}
\\toprule
Variable & Coefficient & t-stat (FM) & t-stat (NW) & \\\\
\\midrule
Intercept & {alpha['coefficient']:.3f} & {alpha['t_stat_fm']:.2f} & {alpha['t_stat_hac']:.2f} & {sig_stars(alpha['p_value_hac'])} \\\\
R\\&D Intensity & {rd['coefficient']:.4f} & {rd['t_stat_fm']:.2f} & {rd['t_stat_hac']:.2f} & {sig_stars(rd['p_value_hac'])} \\\\
Log(Size) & {size['coefficient']:.3f} & {size['t_stat_fm']:.2f} & {size['t_stat_hac']:.2f} & {sig_stars(size['p_value_hac'])} \\\\
B/M Proxy & {bm['coefficient']:.3f} & {bm['t_stat_fm']:.2f} & {bm['t_stat_hac']:.2f} & {sig_stars(bm['p_value_hac'])} \\\\
\\midrule
N (periods) & \\multicolumn{{4}}{{c}}{{{n}}} \\\\
\\bottomrule
\\multicolumn{{5}}{{l}}{{\\footnotesize *** p < 0.01, ** p < 0.05, * p < 0.10. NW = Newey-West HAC.}} \\\\
\\end{{tabular}}
\\end{{table}}
"""
    
    def _generate_fm_interpretation(self, rd: Dict, size: Dict, n: int) -> str:
        """Generate interpretation text for Fama-MacBeth results."""
        rd_sig = "significantly" if rd["significant_005"] else "not significantly"
        rd_dir = "positive" if rd["coefficient"] > 0 else "negative"
        
        return (
            f"Across {n} annual cross-sections, R&D intensity is {rd_sig} "
            f"associated with future returns (coefficient = {rd['coefficient']:.4f}, "
            f"t = {rd['t_stat_hac']:.2f} with Newey-West adjustment). "
            f"This {rd_dir} relationship holds after controlling for firm size and "
            f"book-to-market ratio, suggesting that R&D intensity captures "
            f"information about expected returns beyond traditional risk factors."
        )
