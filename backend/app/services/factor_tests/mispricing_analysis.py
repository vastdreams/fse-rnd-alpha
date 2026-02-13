"""
PATH: backend/app/services/factor_tests/mispricing_analysis.py
PURPOSE: Helper functions for mispricing conditional-sort analysis and interpretation
WHY: Extracted from MispricingAnalyzer to keep each module under ~300 lines
"""

from typing import Dict, Any

import pandas as pd

from app.services.factor_tests.utils import safe_qcut


def conditional_rd_premium(
    data: "pd.DataFrame",
    proxy_col: str,
    proxy_label: str,
) -> Dict[str, Any]:
    """
    Compute mean (by-year) Q5-Q1 premium within a proxy bucket.

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

    for _y, sub in subset_all.groupby("year"):
        # Need enough firms to define quintiles
        if len(sub) < 10:
            continue
        sub = sub.copy()
        sub["rd_quintile"] = safe_qcut(sub["rd_intensity"], 5, [1, 2, 3, 4, 5])

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

    # Fallback (rare): pooled conditional sort within the proxy bucket.
    pooled = subset_all.copy()
    if len(pooled) >= 10:
        pooled["rd_quintile"] = safe_qcut(pooled["rd_intensity"], 5, [1, 2, 3, 4, 5])
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


def interpret_mispricing_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpret conditional-sort results as mispricing vs risk evidence.

    Mispricing hypothesis predicts premium is higher in:
      - Small stocks (vs Large)
      - High volatility (vs Low)
      - Low coverage (vs High)
    """
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
        "mispricing_evidence_count": mispricing_evidence,
        "likely_explanation": interpretation,
        "confidence": "High" if mispricing_evidence >= 2 else "Medium",
        "explanation": explanation,
    }


def generate_mispricing_latex(results: Dict) -> str:
    """Generate LaTeX table for mispricing tests."""
    rows = []

    for size in ["Small", "Medium", "Large"]:
        prem = results.get("by_size", {}).get(size, {}).get("premium", "-")
        n = results.get("by_size", {}).get(size, {}).get("n_obs", 0)
        rows.append(f"Size: {size} & {prem} & {n}")

    for vol in ["Low", "Medium", "High"]:
        prem = results.get("by_volatility", {}).get(vol, {}).get("premium", "-")
        n = results.get("by_volatility", {}).get(vol, {}).get("n_obs", 0)
        rows.append(f"Volatility: {vol} & {prem} & {n}")

    for cov in ["Low", "Medium", "High"]:
        prem = results.get("by_coverage", {}).get(cov, {}).get("premium", "-")
        n = results.get("by_coverage", {}).get(cov, {}).get("n_obs", 0)
        rows.append(f"Coverage: {cov} & {prem} & {n}")

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
