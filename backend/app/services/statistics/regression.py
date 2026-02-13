"""
PATH: backend/app/services/statistics/regression.py
PURPOSE: OLS regression, publication statistics, and LaTeX table export.
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional
import numpy as np
from scipy import stats
from sqlalchemy import select

from app.db.models import FactorPremium
from app.core.logging import get_logger
from app.services.statistics.models import RegressionResult

logger = get_logger(__name__)


class RegressionMixin:
    """Mixin providing OLS regression and publication output methods."""

    def run_regression(
        self,
        y: List[float],
        X: Dict[str, List[float]]
    ) -> RegressionResult:
        """
        Run OLS regression.
        
        Args:
            y: Dependent variable (portfolio returns)
            X: Dict of independent variables (factors)
        """
        try:
            import statsmodels.api as sm
            
            y_arr = np.array(y)
            X_df = np.column_stack([np.array(v) for v in X.values()])
            X_with_const = sm.add_constant(X_df)
            
            model = sm.OLS(y_arr, X_with_const)
            results = model.fit()
            
            factor_names = list(X.keys())
            
            betas = {name: results.params[i + 1] for i, name in enumerate(factor_names)}
            beta_t_stats = {name: results.tvalues[i + 1] for i, name in enumerate(factor_names)}
            beta_p_values = {name: results.pvalues[i + 1] for i, name in enumerate(factor_names)}
            
            return RegressionResult(
                alpha=float(results.params[0]),
                alpha_t_stat=float(results.tvalues[0]),
                alpha_p_value=float(results.pvalues[0]),
                betas=betas,
                beta_t_stats=beta_t_stats,
                beta_p_values=beta_p_values,
                r_squared=float(results.rsquared),
                adj_r_squared=float(results.rsquared_adj),
                n_observations=len(y)
            )
        except ImportError:
            logger.warning("statsmodels not available for regression")
            return RegressionResult(
                alpha=0, alpha_t_stat=0, alpha_p_value=1,
                betas={}, beta_t_stats={}, beta_p_values={},
                r_squared=0, adj_r_squared=0, n_observations=0
            )

    async def get_publication_statistics(self) -> Dict:
        """
        Generate comprehensive statistics for academic publication.
        """
        from scipy import stats as scipy_stats
        
        pub_result = {
            "5yr": await self.compute_aggregate_anova("5yr"),
            "10yr": await self.compute_aggregate_anova("10yr"),
            "20yr": await self.compute_aggregate_anova("20yr")
        }
        
        # Get factor premium statistics
        premium_result = await self.session.execute(
            select(FactorPremium).order_by(FactorPremium.year)
        )
        premiums = premium_result.scalars().all()
        
        if premiums:
            rd_premiums = [p.rd_premium for p in premiums if p.rd_premium is not None]
            
            if rd_premiums:
                # T-test: Is R&D premium significantly different from zero?
                t_stat, p_value = scipy_stats.ttest_1samp(rd_premiums, 0)
                
                pub_result["rd_factor_premium"] = {
                    "mean": round(float(np.mean(rd_premiums)), 2),
                    "std": round(float(np.std(rd_premiums, ddof=1)), 2),
                    "min": round(float(np.min(rd_premiums)), 2),
                    "max": round(float(np.max(rd_premiums)), 2),
                    "n_years": len(rd_premiums),
                    "t_statistic": round(float(t_stat), 3),
                    "p_value": round(float(p_value), 6),
                    "significant": bool(p_value < 0.05),
                    "positive_years": sum(1 for p in rd_premiums if p > 0),
                    "negative_years": sum(1 for p in rd_premiums if p < 0)
                }
        
        return pub_result
    
    async def export_latex_tables(self) -> Dict[str, str]:
        """Generate LaTeX-formatted tables for publication."""
        pub_stats = await self.get_publication_statistics()
        
        tables = {}
        
        # Table 1: Quintile Performance by Window
        table1 = r"""
\begin{table}[htbp]
\centering
\caption{R\&D Quintile Portfolio Performance by Analysis Window}
\label{tab:quintile_performance}
\begin{tabular}{lcccccc}
\toprule
Window & Q1 (Low) & Q2 & Q3 & Q4 & Q5 (High) & Premium \\
\midrule
"""
        for window in ["5yr", "10yr", "20yr"]:
            if window in pub_stats:
                means = pub_stats[window].get("quintile_means", {})
                q1 = means.get("Q1", 0)
                q5 = means.get("Q5", 0)
                table1 += f"{window} & {q1:.1f}\\% & {means.get('Q2', 0):.1f}\\% & {means.get('Q3', 0):.1f}\\% & {means.get('Q4', 0):.1f}\\% & {q5:.1f}\\% & {q5-q1:.1f}\\% \\\\\n"
        
        table1 += r"""
\bottomrule
\end{tabular}
\end{table}
"""
        tables["quintile_performance"] = table1
        
        # Table 2: ANOVA Results
        table2 = r"""
\begin{table}[htbp]
\centering
\caption{ANOVA Results for R\&D Quintile Comparisons}
\label{tab:anova_results}
\begin{tabular}{lcccccc}
\toprule
Window & F-stat & p-value & $\eta^2$ & $\omega^2$ & Significant \\
\midrule
"""
        for window in ["5yr", "10yr", "20yr"]:
            if window in pub_stats:
                anova = pub_stats[window].get("anova", {})
                sig = "***" if anova.get("significant_001") else ("**" if anova.get("significant_005") else "")
                table2 += f"{window} & {anova.get('f_statistic', 0):.2f} & {anova.get('p_value', 0):.4f} & {anova.get('eta_squared', 0):.3f} & {anova.get('omega_squared', 0):.3f} & {sig} \\\\\n"
        
        table2 += r"""
\bottomrule
\multicolumn{6}{l}{\footnotesize *** p < 0.01, ** p < 0.05} \\
\end{tabular}
\end{table}
"""
        tables["anova_results"] = table2
        
        # Table 3: Fama-MacBeth Regression Results
        fm_result = await self.run_fama_macbeth_with_controls("5yr", ["size", "bm"])
        if "error" not in fm_result:
            table3 = r"""
\begin{table}[htbp]
\centering
\caption{Fama-MacBeth (1973) Multivariate Regression Results (5-Year Windows)}
\label{tab:fama_macbeth}
\begin{tabular}{lccc}
\toprule
Factor & Mean Beta & t-stat (HAC) & p-value \\
\midrule
"""
            res = fm_result.get("results", {})
            for factor, stats in res.items():
                name = factor.replace("_", " ").title()
                table3 += f"{name} & {stats.get('mean_beta', 0):.4f} & {stats.get('t_statistic_hac', 0):.2f} & {stats.get('p_value_hac', 0):.4f} \\\\\n"
            
            table3 += r"""
\bottomrule
\end{tabular}
\end{table}
"""
            tables["fama_macbeth"] = table3
        
        return tables
