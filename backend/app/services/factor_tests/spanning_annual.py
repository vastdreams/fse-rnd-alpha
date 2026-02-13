"""
PATH: backend/app/services/factor_tests/spanning_annual.py
PURPOSE: Mixin for annual-frequency factor spanning tests (FF3, FF5, etc.)
WHY: Tests whether annual HML_RD alpha is significant after controlling for standard factors
"""

from typing import Dict, Any


class SpanningAnnualTestsMixin:
    """Mixin providing annual-frequency spanning test orchestration."""

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

        def _store(model_key: str, factor_dict: Dict, model_name: str) -> None:
            res = self.run_spanning_regression(hml_rd, factor_dict, model_name, nw_lags=4)
            if res:
                ci_low = float(res.alpha - 1.96 * res.alpha_se)
                ci_high = float(res.alpha + 1.96 * res.alpha_se)
                results[model_key] = {
                    "alpha": res.alpha,
                    "alpha_se": res.alpha_se,
                    "alpha_ci_95": {"low": ci_low, "high": ci_high},
                    "alpha_t": res.alpha_t,
                    "alpha_p": res.alpha_p,
                    "is_spanned": res.is_spanned,
                    "r_squared": res.r_squared,
                    "factor_loadings": res.factor_loadings
                }

        _store("FF3", {"mkt_rf": mkt_rf, "smb": smb, "hml": hml}, "FF3")
        _store("FF3_MOM", {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "mom": mom}, "FF3+MOM")
        _store("FF5", {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "rmw": rmw, "cma": cma}, "FF5")
        _store(
            "FF5_MOM",
            {"mkt_rf": mkt_rf, "smb": smb, "hml": hml, "rmw": rmw, "cma": cma, "mom": mom},
            "FF5+MOM",
        )

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
