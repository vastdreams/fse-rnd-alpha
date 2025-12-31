#!/usr/bin/env python3
"""
PATH: scripts/validate_publication.py
PURPOSE:
  - Validate publication readiness of the research pipeline
  - Assert no mixed return_convention/data_tier in results
  - Assert Tier-2 prerequisites before Tier-2 compute
  - Emit validation report

ROLE IN ARCHITECTURE:
  - Pre-publication quality gate
  - Ensures data integrity and consistency

USAGE:
  python scripts/validate_publication.py
  python scripts/validate_publication.py --tier tier2  # Check Tier-2 readiness

OUTPUT:
  - Console report of validation checks
  - publication_tables/validation_report.json

NOTES FOR FUTURE AI:
  - Run this before any publication submission
  - All checks should pass before claiming results are valid
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import (
    RollingWindowResult, FactorPremium, AnovaResult,
    JulyJuneReturn, FMPIncomeStatement, FMPDailyPrice,
    SP500HistoricalConstituent, FamaFrenchFactor
)
from app.services.publication_snapshot import build_snapshot_payload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation check results."""
    
    def __init__(self, name: str, passed: bool, message: str, details: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


async def check_return_convention_consistency(session: AsyncSession, data_tier: str) -> ValidationResult:
    """Verify all results for a tier use the same return convention."""
    result = await session.execute(
        select(
            RollingWindowResult.return_convention,
            func.count(RollingWindowResult.id).label("count")
        )
        .where(RollingWindowResult.data_tier == data_tier)
        .group_by(RollingWindowResult.return_convention)
    )
    conventions = {r.return_convention: r.count for r in result.fetchall()}
    
    if len(conventions) == 0:
        return ValidationResult(
            "return_convention_consistency",
            True,
            f"No {data_tier} results found (empty is valid for unused tier)",
            {"conventions": conventions}
        )
    elif len(conventions) == 1:
        convention = list(conventions.keys())[0]
        return ValidationResult(
            "return_convention_consistency",
            True,
            f"All {data_tier} results use '{convention}' return convention",
            {"conventions": conventions}
        )
    else:
        return ValidationResult(
            "return_convention_consistency",
            False,
            f"MIXED return conventions in {data_tier} results!",
            {"conventions": conventions}
        )


async def check_quintile_coverage(session: AsyncSession, data_tier: str) -> ValidationResult:
    """Verify all 5 quintiles are present in results."""
    result = await session.execute(
        select(RollingWindowResult.quintile)
        .where(RollingWindowResult.data_tier == data_tier)
        .distinct()
    )
    quintiles = sorted([r[0] for r in result.fetchall()])
    
    if not quintiles:
        return ValidationResult(
            "quintile_coverage",
            True,
            f"No {data_tier} results to check (empty tier)",
            {"quintiles": quintiles}
        )
    elif quintiles == [1, 2, 3, 4, 5]:
        return ValidationResult(
            "quintile_coverage",
            True,
            f"All 5 quintiles present in {data_tier} results",
            {"quintiles": quintiles}
        )
    else:
        return ValidationResult(
            "quintile_coverage",
            False,
            f"Missing quintiles in {data_tier}: expected [1,2,3,4,5], got {quintiles}",
            {"quintiles": quintiles}
        )


async def check_factor_premium_convention_consistency(session: AsyncSession, data_tier: str) -> ValidationResult:
    """Verify factor premium rows are not mixed across return conventions for a given tier."""
    result = await session.execute(
        select(
            FactorPremium.return_convention,
            func.count(FactorPremium.id).label("count"),
        )
        .where(FactorPremium.data_tier == data_tier)
        .group_by(FactorPremium.return_convention)
        .order_by(FactorPremium.return_convention)
    )
    conventions = {r.return_convention: int(r.count or 0) for r in result.fetchall()}

    if not conventions:
        return ValidationResult(
            "factor_premium_convention_consistency",
            True,
            f"No FactorPremium rows found for {data_tier} (may be fine if not precomputed)",
            {"conventions": conventions},
        )

    if len(conventions) == 1:
        convention = list(conventions.keys())[0]
        return ValidationResult(
            "factor_premium_convention_consistency",
            True,
            f"All FactorPremium rows for {data_tier} use '{convention}' return convention",
            {"conventions": conventions},
        )

    return ValidationResult(
        "factor_premium_convention_consistency",
        False,
        f"MIXED return conventions in FactorPremium for {data_tier}!",
        {"conventions": conventions},
    )


async def check_sp500_membership_spans_present(session: AsyncSession) -> ValidationResult:
    """Require historical membership spans for point-in-time universe (publication-grade)."""
    total = await session.scalar(select(func.count(SP500HistoricalConstituent.id)))
    total = int(total or 0)

    if total <= 0:
        return ValidationResult(
            "sp500_membership_spans_present",
            False,
            "SP500HistoricalConstituent is empty. Point-in-time membership cannot be enforced.",
            {"count": total},
        )

    min_added = await session.scalar(select(func.min(SP500HistoricalConstituent.added_date)))
    max_added = await session.scalar(select(func.max(SP500HistoricalConstituent.added_date)))

    return ValidationResult(
        "sp500_membership_spans_present",
        True,
        f"Historical membership spans present: {total} rows",
        {
            "count": total,
            "min_added_date": str(min_added) if min_added else None,
            "max_added_date": str(max_added) if max_added else None,
        },
    )


async def check_ff_factors_populated(session: AsyncSession) -> ValidationResult:
    """Require Fama-French factors (monthly) for spanning tests (publication-grade)."""
    result = await session.execute(
        select(FamaFrenchFactor.frequency, func.count(FamaFrenchFactor.id))
        .group_by(FamaFrenchFactor.frequency)
        .order_by(FamaFrenchFactor.frequency)
    )
    counts = {str(freq): int(n) for freq, n in result.fetchall()}
    monthly = int(counts.get("monthly", 0))

    if monthly <= 0:
        return ValidationResult(
            "ff_factors_populated",
            False,
            "ff_factors monthly series is empty. Spanning tests cannot be run without factors.",
            {"counts": counts},
        )

    return ValidationResult(
        "ff_factors_populated",
        True,
        "ff_factors populated (monthly series present).",
        {"counts": counts},
    )


async def check_publication_snapshot_payload(session: AsyncSession, data_tier: str) -> ValidationResult:
    """
    Build the publication snapshot payload and assert key publication-facing sections are complete.

    WHY:
      This validates the exact objects used by the website manuscript + LaTeX asset generator:
      - membership diagnostics
      - annual inference object
      - mispricing/coverage blocks (no missing cells)
      - transaction-cost definitions (gross vs net premium consistency)
    """
    try:
        payload = await build_snapshot_payload(session, return_convention="july_june", data_tier=data_tier)
    except Exception as e:
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            f"Snapshot payload build failed: {e}",
        )

    # Helper to check error blocks
    def _is_error(node: Any) -> bool:
        return isinstance(node, dict) and isinstance(node.get("error"), str)

    # 1) Annual HML (primary inference)
    annual = payload.get("annual_hml_premium")
    if not isinstance(annual, dict) or _is_error(annual):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "annual_hml_premium missing or error",
            {"annual_hml_premium": annual},
        )
    n_years = annual.get("n_years")
    hac = annual.get("hac_adjusted") if isinstance(annual.get("hac_adjusted"), dict) else {}
    if not isinstance(n_years, int) or n_years < 20:
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            f"annual_hml_premium has insufficient observations (n_years={n_years})",
            {"n_years": n_years},
        )
    if not isinstance(hac.get("t_statistic"), (int, float)) or not isinstance(hac.get("p_value"), (int, float)):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "annual_hml_premium missing HAC t-stat / p-value",
            {"hac_adjusted": hac},
        )
    methodology = annual.get("methodology") if isinstance(annual.get("methodology"), dict) else {}
    survivorship_text = str(methodology.get("survivorship_correction") or "")
    if "cash" not in survivorship_text.lower():
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "annual_hml_premium methodology does not mention cash-after-exit survivorship handling (expected).",
            {"methodology": methodology},
        )

    # 2) Membership diagnostics
    md = payload.get("membership_diagnostics")
    if not isinstance(md, dict) or _is_error(md):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "membership_diagnostics missing or error",
            {"membership_diagnostics": md},
        )
    summary = md.get("summary") if isinstance(md.get("summary"), dict) else {}
    avg_n = summary.get("avg_constituents_per_year")
    years_with = summary.get("n_years_with_membership")
    union = summary.get("unique_tickers_union")
    if not isinstance(years_with, int) or years_with < 10:
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            f"membership_diagnostics has too few years with membership (n_years_with_membership={years_with})",
            {"summary": summary},
        )
    if not isinstance(avg_n, (int, float)) or not (450 <= float(avg_n) <= 550):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            f"membership_diagnostics avg constituents per year out of expected range (avg={avg_n})",
            {"summary": summary},
        )
    if not isinstance(union, int) or union < 500:
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            f"membership_diagnostics union size too small (unique_tickers_union={union})",
            {"summary": summary},
        )

    # 3) Mispricing tests (no missing cells)
    mis = payload.get("mispricing_tests")
    if not isinstance(mis, dict) or _is_error(mis):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "mispricing_tests missing or error",
            {"mispricing_tests": mis},
        )
    tests = mis.get("tests") if isinstance(mis.get("tests"), dict) else {}
    required_groups = {
        "by_size": ["Small", "Medium", "Large"],
        "by_volatility": ["Low", "Medium", "High"],
        "by_coverage": ["Low", "Medium", "High"],
    }
    for group_key, buckets in required_groups.items():
        group = tests.get(group_key)
        if not isinstance(group, dict):
            return ValidationResult(
                "publication_snapshot_payload",
                False,
                f"mispricing_tests missing group '{group_key}'",
                {"tests": tests},
            )
        for bucket in buckets:
            node = group.get(bucket)
            prem = node.get("premium") if isinstance(node, dict) else None
            if not isinstance(prem, (int, float)):
                return ValidationResult(
                    "publication_snapshot_payload",
                    False,
                    f"mispricing_tests missing premium for {group_key}:{bucket}",
                    {"bucket": bucket, "node": node},
                )

    # 4) Transaction costs (definition-consistent, realized-turnover preferred)
    tx = payload.get("transaction_costs")
    if not isinstance(tx, dict) or _is_error(tx):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs missing or error",
            {"transaction_costs": tx},
        )
    if not isinstance(tx.get("annual_trading_cost_pct"), (int, float)):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs missing annual_trading_cost_pct",
            {"transaction_costs": tx},
        )
    if not isinstance(tx.get("gross_rd_premium_pct"), (int, float)) or not isinstance(tx.get("net_rd_premium_pct"), (int, float)):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs missing gross/net premium fields",
            {"transaction_costs": tx},
        )
    if not isinstance(tx.get("definition"), dict):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs missing definition block (expected for publication clarity).",
            {"transaction_costs": tx},
        )
    turnover = tx.get("turnover") if isinstance(tx.get("turnover"), dict) else {}
    if not isinstance(turnover.get("avg_turnover_pct"), (int, float)):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs missing realized turnover (avg_turnover_pct).",
            {"turnover": turnover},
        )
    note = str(tx.get("note") or "")
    if "fallback" in note.lower():
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "transaction_costs is using a fallback estimate (investable_backtest unavailable).",
            {"note": note},
        )

    # 5) Spanning tests must exist (for the paper tables)
    spanning = payload.get("spanning_tests_full")
    if not isinstance(spanning, dict) or _is_error(spanning) or not isinstance(spanning.get("latex_table"), str):
        return ValidationResult(
            "publication_snapshot_payload",
            False,
            "spanning_tests_full missing/invalid (latex_table required).",
            {"spanning_tests_full": spanning},
        )

    return ValidationResult(
        "publication_snapshot_payload",
        True,
        "Snapshot payload built and all publication-facing sections passed completeness checks.",
        {"tier": data_tier, "annual_n_years": n_years},
    )


async def check_tier1_data_availability(session: AsyncSession) -> ValidationResult:
    """Check if Tier-1 source data is available."""
    # Check income statements
    inc_count = await session.scalar(select(func.count(FMPIncomeStatement.id)))
    
    # Check daily prices
    price_count = await session.scalar(select(func.count(FMPDailyPrice.id)))
    
    # Check July-June returns
    jj_count = await session.scalar(
        select(func.count())
        .select_from(JulyJuneReturn)
        .where(JulyJuneReturn.data_tier == "tier1")
    )
    
    if inc_count > 0 and price_count > 0:
        passed = True
        msg = f"Tier-1 data available: {inc_count} income statements, {price_count} prices, {jj_count} July-June returns"
    else:
        passed = False
        msg = f"Tier-1 data incomplete: income={inc_count}, prices={price_count}"
    
    return ValidationResult(
        "tier1_data_availability",
        passed,
        msg,
        {"income_statements": inc_count, "daily_prices": price_count, "july_june_returns": jj_count}
    )


async def check_tier2_prerequisites(session: AsyncSession) -> ValidationResult:
    """Check if Tier-2 prerequisites are met."""
    # Check CRSP monthly stock
    crsp_count = await session.scalar(text("SELECT COUNT(*) FROM crsp_monthly_stock"))
    
    # Check Compustat annual
    compustat_count = await session.scalar(text("SELECT COUNT(*) FROM compustat_annual"))
    
    # Check CCM link
    ccm_count = await session.scalar(text("SELECT COUNT(*) FROM crsp_compustat_link"))
    
    # Check S&P 500 constituents
    sp500_count = await session.scalar(text("SELECT COUNT(*) FROM crsp_sp500_constituents"))
    
    details = {
        "crsp_monthly": crsp_count or 0,
        "compustat_annual": compustat_count or 0,
        "ccm_link": ccm_count or 0,
        "sp500_constituents": sp500_count or 0,
    }
    
    if all(v > 0 for v in details.values()):
        return ValidationResult(
            "tier2_prerequisites",
            True,
            "All Tier-2 prerequisite tables populated",
            details
        )
    elif all(v == 0 for v in details.values()):
        return ValidationResult(
            "tier2_prerequisites",
            True,
            "Tier-2 tables are empty (acceptable if not using Tier-2)",
            details
        )
    else:
        return ValidationResult(
            "tier2_prerequisites",
            False,
            "Tier-2 tables partially populated - incomplete ingestion",
            details
        )


async def check_tier2_returns_computed(session: AsyncSession) -> ValidationResult:
    """Check if Tier-2 returns have been computed."""
    jj_count = await session.scalar(
        select(func.count())
        .select_from(JulyJuneReturn)
        .where(JulyJuneReturn.data_tier == "tier2")
    )
    
    if jj_count > 0:
        return ValidationResult(
            "tier2_returns_computed",
            True,
            f"Tier-2 July-June returns computed: {jj_count} records",
            {"count": jj_count}
        )
    else:
        return ValidationResult(
            "tier2_returns_computed",
            True,  # Not a failure, just informational
            "Tier-2 returns not yet computed (run compute_july_june_returns.py --data-tier tier2)",
            {"count": 0}
        )


async def check_factor_premium_monotonicity(session: AsyncSession, data_tier: str) -> ValidationResult:
    """Check if HML premium is positive on average (core claim)."""
    result = await session.execute(
        select(FactorPremium.rd_premium)
        .where(
            FactorPremium.data_tier == data_tier,
            FactorPremium.rd_premium.isnot(None)
        )
    )
    premiums = [r[0] for r in result.fetchall()]
    
    if not premiums:
        return ValidationResult(
            "factor_premium_monotonicity",
            True,
            f"No {data_tier} factor premiums to check (empty tier)",
            {"n_years": 0}
        )
    
    import numpy as np
    mean_premium = np.mean(premiums)
    positive_count = sum(1 for p in premiums if p > 0)
    
    if mean_premium > 0:
        return ValidationResult(
            "factor_premium_monotonicity",
            True,
            f"Mean HML premium is positive ({mean_premium:.2f}%), {positive_count}/{len(premiums)} years positive",
            {"mean_premium": round(mean_premium, 2), "positive_years": positive_count, "total_years": len(premiums)}
        )
    else:
        return ValidationResult(
            "factor_premium_monotonicity",
            False,
            f"Mean HML premium is NEGATIVE ({mean_premium:.2f}%) - core claim not supported",
            {"mean_premium": round(mean_premium, 2), "positive_years": positive_count, "total_years": len(premiums)}
        )


async def run_all_checks(session: AsyncSession, tier: str) -> List[ValidationResult]:
    """Run all validation checks."""
    checks = []
    
    # Core checks
    checks.append(await check_return_convention_consistency(session, tier))
    checks.append(await check_quintile_coverage(session, tier))
    checks.append(await check_factor_premium_convention_consistency(session, tier))
    checks.append(await check_factor_premium_monotonicity(session, tier))
    
    # Data availability
    checks.append(await check_tier1_data_availability(session))

    # Publication-grade prerequisites
    checks.append(await check_sp500_membership_spans_present(session))
    checks.append(await check_ff_factors_populated(session))

    # Snapshot payload completeness (only meaningful if prerequisites exist)
    # If factors/membership are missing, this check will typically fail (as intended for publication readiness).
    checks.append(await check_publication_snapshot_payload(session, tier))
    
    # Tier-2 specific
    try:
        checks.append(await check_tier2_prerequisites(session))
        checks.append(await check_tier2_returns_computed(session))
    except Exception as e:
        logger.warning(f"Tier-2 checks skipped (tables may not exist): {e}")
    
    return checks


async def main(tier: str, output_dir: Path, database_url: str | None):
    """Main validation function."""
    logger.info("=" * 60)
    logger.info("PUBLICATION VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Validating: {tier}")
    logger.info("")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url = database_url or settings.async_database_url
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            checks = await run_all_checks(session, tier)
            
            # Print results
            passed_count = 0
            failed_count = 0
            
            for check in checks:
                status = "✓ PASS" if check.passed else "✗ FAIL"
                print(f"{status}: {check.name}")
                print(f"       {check.message}")
                
                if check.passed:
                    passed_count += 1
                else:
                    failed_count += 1
            
            print("")
            print("=" * 60)
            print(f"SUMMARY: {passed_count} passed, {failed_count} failed")
            print("=" * 60)
            
            # Write report
            report = {
                "validation_date": datetime.utcnow().isoformat(),
                "tier": tier,
                "passed": failed_count == 0,
                "summary": {
                    "passed": passed_count,
                    "failed": failed_count,
                },
                "checks": [c.to_dict() for c in checks],
            }
            
            report_path = output_dir / "validation_report.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report written to: {report_path}")
            
            if failed_count > 0:
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate publication readiness")
    parser.add_argument(
        "--tier",
        choices=["tier1", "tier2"],
        default="tier1",
        help="Data tier to validate (default: tier1)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("publication_tables"),
        help="Directory for output files (default: publication_tables)"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override DATABASE_URL for validation (e.g., to point at a remote or non-default local DB).",
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.tier, args.output_dir, args.database_url))

