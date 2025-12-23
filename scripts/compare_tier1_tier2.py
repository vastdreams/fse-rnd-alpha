#!/usr/bin/env python3
"""
PATH: scripts/compare_tier1_tier2.py
PURPOSE:
  - Compare Tier-1 (FMP) and Tier-2 (CRSP/Compustat) research results
  - Generate publication-grade comparison report
  - Verify that Tier-2 confirms core claims from Tier-1

ROLE IN ARCHITECTURE:
  - Validation layer for publication robustness
  - Produces comparison tables for manuscript appendix

USAGE:
  python scripts/compare_tier1_tier2.py
  python scripts/compare_tier1_tier2.py --output-dir publication_tables

OUTPUT:
  - tier_comparison.json: Full comparison data
  - tier_comparison.md: Markdown summary
  - tier_comparison.tex: LaTeX table for paper

NOTES FOR FUTURE AI:
  - Tier-2 must be computed before running this script
  - Key metrics: mean premium, t-stat, win rate, HML significance
  - Verdict: "confirmed" if Tier-2 premium is significant and same sign
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import RollingWindowResult, FactorPremium, AnovaResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_tier_summary(session: AsyncSession, data_tier: str) -> Dict[str, Any]:
    """Get summary statistics for a specific data tier."""
    return_convention = "july_june"  # Standard for publication
    
    # Get rolling window results
    rw_result = await session.execute(
        select(
            RollingWindowResult.window_type,
            func.count(RollingWindowResult.id).label("n_windows"),
            func.avg(RollingWindowResult.avg_return).label("avg_return"),
        )
        .where(
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == data_tier,
        )
        .group_by(RollingWindowResult.window_type)
    )
    window_counts = {r.window_type: {"n_windows": r.n_windows, "avg_return": float(r.avg_return) if r.avg_return else 0} for r in rw_result.fetchall()}
    
    # Get factor premiums
    fp_result = await session.execute(
        select(FactorPremium)
        .where(
            FactorPremium.return_convention == return_convention,
            FactorPremium.data_tier == data_tier,
        )
        .order_by(FactorPremium.year)
    )
    premiums = [r.rd_premium for r in fp_result.scalars().all() if r.rd_premium is not None]
    
    if premiums:
        mean_premium = float(np.mean(premiums))
        std_premium = float(np.std(premiums, ddof=1)) if len(premiums) > 1 else 0
        t_stat = mean_premium / (std_premium / np.sqrt(len(premiums))) if std_premium > 0 else 0
        positive_years = sum(1 for p in premiums if p > 0)
        win_rate = positive_years / len(premiums) * 100
    else:
        mean_premium = 0
        std_premium = 0
        t_stat = 0
        positive_years = 0
        win_rate = 0
    
    # Get quintile performance for 5yr windows
    quintile_result = await session.execute(
        select(
            RollingWindowResult.quintile,
            func.avg(RollingWindowResult.avg_return).label("avg_return"),
            func.avg(RollingWindowResult.sharpe_ratio).label("sharpe_ratio"),
        )
        .where(
            RollingWindowResult.window_type == "5yr",
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == data_tier,
        )
        .group_by(RollingWindowResult.quintile)
        .order_by(RollingWindowResult.quintile)
    )
    quintiles = {
        r.quintile: {
            "avg_return": round(float(r.avg_return), 2) if r.avg_return else 0,
            "sharpe_ratio": round(float(r.sharpe_ratio), 3) if r.sharpe_ratio else 0,
        }
        for r in quintile_result.fetchall()
    }
    
    # HML premium (Q5 - Q1)
    q1_return = quintiles.get(1, {}).get("avg_return", 0)
    q5_return = quintiles.get(5, {}).get("avg_return", 0)
    hml_premium = q5_return - q1_return
    
    return {
        "data_tier": data_tier,
        "return_convention": return_convention,
        "window_counts": window_counts,
        "factor_premiums": {
            "n_years": len(premiums),
            "mean_premium_pct": round(mean_premium, 2),
            "std_dev_pct": round(std_premium, 2),
            "t_statistic": round(t_stat, 2),
            "positive_years": positive_years,
            "win_rate_pct": round(win_rate, 1),
        },
        "quintile_performance": quintiles,
        "hml_premium_5yr_pct": round(hml_premium, 2),
    }


def compute_comparison(tier1: Dict, tier2: Dict) -> Dict[str, Any]:
    """Compute comparison between Tier-1 and Tier-2 results."""
    t1_premium = tier1["factor_premiums"]["mean_premium_pct"]
    t2_premium = tier2["factor_premiums"]["mean_premium_pct"]
    
    t1_t_stat = tier1["factor_premiums"]["t_statistic"]
    t2_t_stat = tier2["factor_premiums"]["t_statistic"]
    
    t1_win_rate = tier1["factor_premiums"]["win_rate_pct"]
    t2_win_rate = tier2["factor_premiums"]["win_rate_pct"]
    
    t1_hml = tier1["hml_premium_5yr_pct"]
    t2_hml = tier2["hml_premium_5yr_pct"]
    
    # Determine verdict
    same_sign = (t1_premium > 0) == (t2_premium > 0)
    t2_significant = abs(t2_t_stat) >= 1.96
    
    if tier2["factor_premiums"]["n_years"] == 0:
        verdict = "no_tier2_data"
        verdict_explanation = "Tier-2 data not yet computed. Run compute_july_june_returns.py --data-tier tier2 first."
    elif same_sign and t2_significant:
        verdict = "confirmed"
        verdict_explanation = f"Tier-2 confirms core claim: R&D premium is positive and significant (t={t2_t_stat:.2f})"
    elif same_sign and not t2_significant:
        verdict = "directionally_consistent"
        verdict_explanation = f"Tier-2 shows same direction but weaker significance (t={t2_t_stat:.2f} vs critical 1.96)"
    else:
        verdict = "contradicts"
        verdict_explanation = f"Tier-2 results contradict Tier-1: different sign or direction"
    
    return {
        "comparison_date": datetime.utcnow().isoformat(),
        "headline": {
            "tier1_premium_pct": t1_premium,
            "tier2_premium_pct": t2_premium,
            "premium_difference_pct": round(t2_premium - t1_premium, 2),
            "tier1_t_stat": t1_t_stat,
            "tier2_t_stat": t2_t_stat,
            "tier1_win_rate": t1_win_rate,
            "tier2_win_rate": t2_win_rate,
            "tier1_hml_5yr": t1_hml,
            "tier2_hml_5yr": t2_hml,
        },
        "verdict": verdict,
        "verdict_explanation": verdict_explanation,
        "tier1_summary": tier1,
        "tier2_summary": tier2,
    }


def generate_markdown(comparison: Dict) -> str:
    """Generate Markdown comparison report."""
    h = comparison["headline"]
    
    md = f"""# Tier-1 vs Tier-2 Comparison Report

**Generated**: {comparison["comparison_date"]}

## Verdict: {comparison["verdict"].upper().replace('_', ' ')}

{comparison["verdict_explanation"]}

## Headline Comparison

| Metric | Tier-1 (FMP) | Tier-2 (CRSP) | Difference |
|--------|-------------|---------------|------------|
| Mean R&D Premium (%) | {h['tier1_premium_pct']:.2f} | {h['tier2_premium_pct']:.2f} | {h['premium_difference_pct']:.2f} |
| T-Statistic | {h['tier1_t_stat']:.2f} | {h['tier2_t_stat']:.2f} | {h['tier2_t_stat'] - h['tier1_t_stat']:.2f} |
| Win Rate (%) | {h['tier1_win_rate']:.1f} | {h['tier2_win_rate']:.1f} | {h['tier2_win_rate'] - h['tier1_win_rate']:.1f} |
| HML Premium 5yr (%) | {h['tier1_hml_5yr']:.2f} | {h['tier2_hml_5yr']:.2f} | {h['tier2_hml_5yr'] - h['tier1_hml_5yr']:.2f} |

## Data Coverage

### Tier-1 (FMP)
- Years of factor premium data: {comparison['tier1_summary']['factor_premiums']['n_years']}
- Rolling windows (5yr): {comparison['tier1_summary']['window_counts'].get('5yr', {}).get('n_windows', 0)}

### Tier-2 (CRSP)
- Years of factor premium data: {comparison['tier2_summary']['factor_premiums']['n_years']}
- Rolling windows (5yr): {comparison['tier2_summary']['window_counts'].get('5yr', {}).get('n_windows', 0)}

## Interpretation

"""
    
    if comparison["verdict"] == "confirmed":
        md += """The Tier-2 (CRSP/Compustat) analysis **confirms** the core finding from Tier-1 (FMP).
The R&D return premium is robust to the data source used, which strengthens the publication claim.
"""
    elif comparison["verdict"] == "directionally_consistent":
        md += """The Tier-2 analysis shows the same **directional relationship** but with lower statistical significance.
This may be due to sample differences or the gold-standard CRSP delisting return treatment.
Consider discussing this in the paper's robustness section.
"""
    elif comparison["verdict"] == "no_tier2_data":
        md += """**Action Required**: Tier-2 data has not been computed yet.

1. Ingest WRDS data: `python scripts/ingest_wrds_tier2.py --input-dir data/wrds/`
2. Compute Tier-2 returns: `python scripts/compute_july_june_returns.py --data-tier tier2`
3. Compute Tier-2 rolling windows: run the rolling window analyzer with `data_tier=tier2`
4. Re-run this comparison script
"""
    else:
        md += """**Warning**: Tier-2 results contradict Tier-1 findings. Investigate further before publication.
"""
    
    return md


def generate_latex(comparison: Dict) -> str:
    """Generate LaTeX table for paper appendix."""
    h = comparison["headline"]
    
    latex = r"""\begin{table}[htbp]
\centering
\caption{Comparison of R\&D Premium Estimates: FMP vs CRSP Data Sources}
\label{tab:tier_comparison}
\begin{tabular}{lrrr}
\toprule
Metric & Tier-1 (FMP) & Tier-2 (CRSP) & Difference \\
\midrule
"""
    
    latex += f"Mean R\\&D Premium (\\%) & {h['tier1_premium_pct']:.2f} & {h['tier2_premium_pct']:.2f} & {h['premium_difference_pct']:.2f} \\\\\n"
    latex += f"T-Statistic & {h['tier1_t_stat']:.2f} & {h['tier2_t_stat']:.2f} & {h['tier2_t_stat'] - h['tier1_t_stat']:.2f} \\\\\n"
    latex += f"Win Rate (\\%) & {h['tier1_win_rate']:.1f} & {h['tier2_win_rate']:.1f} & {h['tier2_win_rate'] - h['tier1_win_rate']:.1f} \\\\\n"
    latex += f"HML Premium 5yr (\\%) & {h['tier1_hml_5yr']:.2f} & {h['tier2_hml_5yr']:.2f} & {h['tier2_hml_5yr'] - h['tier1_hml_5yr']:.2f} \\\\\n"
    
    latex += r"""\bottomrule
\end{tabular}
\begin{tablenotes}
\small
\item Notes: Tier-1 uses Financial Modeling Prep (FMP) daily prices. Tier-2 uses CRSP monthly returns with official delisting returns. Both use July-June return convention (Fama-French) to eliminate look-ahead bias.
\end{tablenotes}
\end{table}
"""
    
    return latex


async def main(output_dir: Path):
    """Main comparison function."""
    logger.info("Tier-1 vs Tier-2 Comparison Report Generator")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Get summaries for each tier
            logger.info("Fetching Tier-1 (FMP) summary...")
            tier1_summary = await get_tier_summary(session, "tier1")
            
            logger.info("Fetching Tier-2 (CRSP) summary...")
            tier2_summary = await get_tier_summary(session, "tier2")
            
            # Compute comparison
            logger.info("Computing comparison...")
            comparison = compute_comparison(tier1_summary, tier2_summary)
            
            # Write outputs
            json_path = output_dir / "tier_comparison.json"
            with open(json_path, "w") as f:
                json.dump(comparison, f, indent=2, default=str)
            logger.info(f"Written: {json_path}")
            
            md_path = output_dir / "tier_comparison.md"
            with open(md_path, "w") as f:
                f.write(generate_markdown(comparison))
            logger.info(f"Written: {md_path}")
            
            tex_path = output_dir / "tier_comparison.tex"
            with open(tex_path, "w") as f:
                f.write(generate_latex(comparison))
            logger.info(f"Written: {tex_path}")
            
            # Print summary
            print("\n" + "=" * 60)
            print("TIER-1 vs TIER-2 COMPARISON SUMMARY")
            print("=" * 60)
            print(f"Verdict: {comparison['verdict'].upper().replace('_', ' ')}")
            print(f"Tier-1 Premium: {comparison['headline']['tier1_premium_pct']:.2f}% (t={comparison['headline']['tier1_t_stat']:.2f})")
            print(f"Tier-2 Premium: {comparison['headline']['tier2_premium_pct']:.2f}% (t={comparison['headline']['tier2_t_stat']:.2f})")
            print(f"\n{comparison['verdict_explanation']}")
            print("=" * 60)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Tier-1 and Tier-2 research results")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("publication_tables"),
        help="Directory for output files (default: publication_tables)"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.output_dir))

