"""
PATH: backend/app/services/factor_tests/spanning_regression.py
PURPOSE: Mixin for OLS regression with Newey-West standard errors and LaTeX output
WHY: Core regression logic shared by annual and monthly spanning test orchestrators
DEPENDENCIES:
  - numpy, scipy: numerical computation
  - statsmodels: OLS + HAC standard errors (imported at runtime)
"""

from typing import Dict, List, Optional

import numpy as np
from scipy import stats

from app.core.logging import get_logger
from app.services.factor_tests.models import SpanningTestResult

logger = get_logger(__name__)


class SpanningRegressionMixin:
    """Mixin providing OLS spanning regression and LaTeX table generation."""

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
        # - annual: small lags (e.g., 1-4)
        # - monthly: often 6-12
        nw_cov = cov_hac(results, nlags=int(max(0, nw_lags)))
        nw_se = np.sqrt(np.diag(nw_cov))

        # Extract alpha (intercept)
        alpha = results.params[0]
        alpha_se = nw_se[0]
        alpha_t = alpha / alpha_se if alpha_se > 0 else 0
        alpha_p = 2 * (1 - stats.t.cdf(abs(alpha_t), df=n - len(X_cols) - 1))
        alpha_p = float(alpha_p)

        # Factor loadings
        factor_loadings = {
            X_cols[i]: float(results.params[i + 1]) for i in range(len(X_cols))
        }
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

    def _generate_spanning_latex(self, results: Dict) -> str:
        """Generate LaTeX table for spanning test results."""
        def sig_stars(p: float) -> str:
            if p < 0.01:
                return "***"
            if p < 0.05:
                return "**"
            if p < 0.10:
                return "*"
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
