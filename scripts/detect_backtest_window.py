#!/usr/bin/env python3
"""
PATH: scripts/detect_backtest_window.py
PURPOSE:
  - Auto-detect the earliest feasible formation year for the backtest window
  - Based on actual coverage: membership, fundamentals (R&D + revenue), prices/dividends, returns
  - Persists the detected window into snapshot metadata

COVERAGE THRESHOLDS (configurable):
  - n_members_at_formation >= 450 OR >= 80% of that year's membership union
  - n_with_signal >= 300 (companies with R&D + revenue data)
  - n_with_returns >= 300 (companies with July-June returns)

USAGE:
  python scripts/detect_backtest_window.py              # Detect and print
  python scripts/detect_backtest_window.py --persist    # Persist to config
"""

import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Coverage thresholds
MIN_MEMBERS_ABSOLUTE = 450
MIN_MEMBERS_RELATIVE = 0.80  # 80% of that year's membership union
MIN_SIGNAL_COVERAGE = 300
MIN_RETURN_COVERAGE = 300

# Search range
EARLIEST_POSSIBLE_YEAR = 1990  # Don't go before this
LATEST_POSSIBLE_YEAR = 2024    # Current practical limit

# Output path for persisted window config
CONFIG_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "backtest_window_config.json"


async def get_coverage_by_year(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Compute coverage metrics by formation year.
    
    Returns list of dicts with:
      - formation_year
      - n_members: count of S&P 500 members at July 1 (formation date)
      - n_with_signal: count with R&D + revenue data for that fiscal year
      - n_with_returns: count with July-June returns for that formation year
    """
    
    # Query membership, signal, and return coverage per formation year
    query = text("""
        WITH years AS (
            SELECT generate_series(CAST(:start_year AS INT), CAST(:end_year AS INT)) AS formation_year
        ),
        -- Members at formation date (July 1 of formation_year + 1)
        membership AS (
            SELECT 
                y.formation_year,
                COUNT(DISTINCT h.symbol) AS n_members
            FROM years y
            LEFT JOIN sp500_historical_constituents h
                ON h.added_date <= make_date(y.formation_year + 1, 7, 1)
                AND (h.removed_date IS NULL OR h.removed_date >= make_date(y.formation_year + 1, 7, 1))
            GROUP BY y.formation_year
        ),
        -- Companies with signal (R&D + revenue) for that fiscal year
        signal_coverage AS (
            SELECT 
                y.formation_year,
                COUNT(DISTINCT i.symbol) AS n_with_signal
            FROM years y
            LEFT JOIN fmp_income_statements i
                ON i.fiscal_year = y.formation_year
                AND i.rd_expenses IS NOT NULL
                AND i.rd_expenses > 0
                AND i.revenue IS NOT NULL
                AND i.revenue > 0
            GROUP BY y.formation_year
        ),
        -- Companies with July-June returns for that formation year
        return_coverage AS (
            SELECT 
                y.formation_year,
                COUNT(DISTINCT r.symbol) AS n_with_returns
            FROM years y
            LEFT JOIN july_june_returns r
                ON r.formation_year = y.formation_year
                AND r.data_tier = 'tier1'
                AND r.total_return IS NOT NULL
            GROUP BY y.formation_year
        )
        SELECT 
            m.formation_year,
            COALESCE(m.n_members, 0) AS n_members,
            COALESCE(s.n_with_signal, 0) AS n_with_signal,
            COALESCE(r.n_with_returns, 0) AS n_with_returns
        FROM membership m
        LEFT JOIN signal_coverage s ON s.formation_year = m.formation_year
        LEFT JOIN return_coverage r ON r.formation_year = m.formation_year
        ORDER BY m.formation_year
    """)
    
    result = await session.execute(query, {
        "start_year": EARLIEST_POSSIBLE_YEAR,
        "end_year": LATEST_POSSIBLE_YEAR,
    })
    
    rows = result.fetchall()
    return [
        {
            "formation_year": int(row[0]),
            "n_members": int(row[1]),
            "n_with_signal": int(row[2]),
            "n_with_returns": int(row[3]),
        }
        for row in rows
    ]


def detect_earliest_feasible_year(
    coverage_data: List[Dict[str, Any]],
    min_members_absolute: int = MIN_MEMBERS_ABSOLUTE,
    min_members_relative: float = MIN_MEMBERS_RELATIVE,
    min_signal: int = MIN_SIGNAL_COVERAGE,
    min_returns: int = MIN_RETURN_COVERAGE,
) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    """
    Detect the earliest formation year that meets coverage thresholds.
    
    Returns:
        Tuple of (earliest_year, coverage_with_status)
    """
    max_members_seen = max((d["n_members"] for d in coverage_data), default=0)
    
    annotated = []
    earliest_feasible = None
    
    for d in coverage_data:
        year = d["formation_year"]
        n_members = d["n_members"]
        n_signal = d["n_with_signal"]
        n_returns = d["n_with_returns"]
        
        # Check thresholds
        members_ok = n_members >= min_members_absolute or (
            max_members_seen > 0 and n_members >= min_members_relative * max_members_seen
        )
        signal_ok = n_signal >= min_signal
        returns_ok = n_returns >= min_returns
        
        feasible = members_ok and signal_ok and returns_ok
        
        annotated.append({
            **d,
            "members_ok": members_ok,
            "signal_ok": signal_ok,
            "returns_ok": returns_ok,
            "feasible": feasible,
        })
        
        if feasible and earliest_feasible is None:
            earliest_feasible = year
    
    return earliest_feasible, annotated


async def detect_window() -> Dict[str, Any]:
    """
    Main detection function.
    
    Returns dict with:
      - earliest_formation_year
      - latest_formation_year
      - backtest_start (July of earliest_formation_year + 1)
      - backtest_end (June of latest_formation_year + 2)
      - coverage_by_year
    """
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            coverage = await get_coverage_by_year(session)
            earliest, annotated = detect_earliest_feasible_year(coverage)
            
            # Find latest feasible year (usually current - 1)
            feasible_years = [d["formation_year"] for d in annotated if d["feasible"]]
            latest = max(feasible_years) if feasible_years else None
            
            if earliest and latest:
                backtest_start_year = earliest + 1  # Returns start July of formation_year + 1
                backtest_end_year = latest + 2      # Returns end June of formation_year + 2
                n_years = latest - earliest + 1
            else:
                backtest_start_year = None
                backtest_end_year = None
                n_years = 0
            
            return {
                "earliest_formation_year": earliest,
                "latest_formation_year": latest,
                "backtest_start_year": backtest_start_year,
                "backtest_end_year": backtest_end_year,
                "backtest_period_label": f"Jul{backtest_start_year}-Jun{backtest_end_year}" if backtest_start_year else None,
                "n_formation_years": n_years,
                "thresholds": {
                    "min_members_absolute": MIN_MEMBERS_ABSOLUTE,
                    "min_members_relative": MIN_MEMBERS_RELATIVE,
                    "min_signal": MIN_SIGNAL_COVERAGE,
                    "min_returns": MIN_RETURN_COVERAGE,
                },
                "coverage_by_year": annotated,
                "detection_date": date.today().isoformat(),
            }
    finally:
        await engine.dispose()


def persist_window_config(config: Dict[str, Any]) -> None:
    """Save the detected window configuration to a JSON file."""
    CONFIG_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Save only the essential config (not full coverage breakdown)
    essential = {
        "earliest_formation_year": config["earliest_formation_year"],
        "latest_formation_year": config["latest_formation_year"],
        "backtest_start_year": config["backtest_start_year"],
        "backtest_end_year": config["backtest_end_year"],
        "backtest_period_label": config["backtest_period_label"],
        "n_formation_years": config["n_formation_years"],
        "detection_date": config["detection_date"],
        "thresholds": config["thresholds"],
    }
    
    with open(CONFIG_OUTPUT_PATH, "w") as f:
        json.dump(essential, f, indent=2)
    
    logger.info(f"Persisted window config to {CONFIG_OUTPUT_PATH}")


def load_window_config() -> Optional[Dict[str, Any]]:
    """Load previously persisted window configuration."""
    if not CONFIG_OUTPUT_PATH.exists():
        return None
    
    with open(CONFIG_OUTPUT_PATH, "r") as f:
        return json.load(f)


async def main(persist: bool = False, verbose: bool = True):
    """
    Detect backtest window and optionally persist.
    """
    config = await detect_window()
    
    if verbose:
        logger.info("=" * 70)
        logger.info("BACKTEST WINDOW AUTO-DETECTION")
        logger.info("=" * 70)
        logger.info(f"Earliest feasible formation year: {config['earliest_formation_year']}")
        logger.info(f"Latest feasible formation year: {config['latest_formation_year']}")
        logger.info(f"Backtest period: {config['backtest_period_label']}")
        logger.info(f"Total formation years: {config['n_formation_years']}")
        logger.info("")
        logger.info("Coverage by year:")
        logger.info("-" * 70)
        logger.info(f"{'Year':>6} {'Members':>8} {'Signal':>8} {'Returns':>8} {'Status':>10}")
        logger.info("-" * 70)
        
        for d in config["coverage_by_year"]:
            status = "✓ OK" if d["feasible"] else "✗ SKIP"
            details = []
            if not d["members_ok"]:
                details.append("mem")
            if not d["signal_ok"]:
                details.append("sig")
            if not d["returns_ok"]:
                details.append("ret")
            
            status_str = status if d["feasible"] else f"✗ ({','.join(details)})"
            logger.info(f"{d['formation_year']:>6} {d['n_members']:>8} {d['n_with_signal']:>8} {d['n_with_returns']:>8} {status_str:>10}")
        
        logger.info("=" * 70)
    
    if persist:
        persist_window_config(config)
    
    return config


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Detect earliest feasible backtest window")
    parser.add_argument("--persist", action="store_true", help="Persist detected window to config file")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()
    
    asyncio.run(main(persist=args.persist, verbose=not args.quiet))

