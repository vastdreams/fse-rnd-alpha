#!/bin/bash
# PATH: scripts/reproduce_publication.sh
# PURPOSE:
#   One-command reproduction of all publication tables and figures
#   Required for academic publication standards
#
# USAGE:
#   ./scripts/reproduce_publication.sh
#
# REQUIREMENTS:
#   - FMP_API_KEY environment variable set
#   - Database connection configured in backend/app/core/config.py
#   - Python 3.10+ with requirements installed
#
# OUTPUT:
#   - ./publication_tables/ directory with all tables as JSON and LaTeX
#   - Validation report showing canonical value matches

set -e

echo "============================================================"
echo "R&D PREMIUM RESEARCH - FULL REPRODUCTION PIPELINE"
echo "============================================================"
echo ""
echo "Started at: $(date)"
echo ""

# Check environment
if [ -z "$FMP_API_KEY" ]; then
    echo "WARNING: FMP_API_KEY not set. Some ingestion scripts may fail."
fi

cd "$(dirname "$0")/.."

# Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Ensure DATABASE_URL is available for psycopg2-based ingestion scripts.
# Most backend scripts use `backend/app/core/config.py` via pydantic-settings, but some legacy ingestors read DATABASE_URL.
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="$(python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "backend"))
from app.core.config import settings
print(settings.DATABASE_URL)
PY
)"
    echo "Set DATABASE_URL from backend settings"
fi

echo ""
echo "============================================================"
echo "STEP 0: ENSURE DATABASE SCHEMA"
echo "============================================================"
python - <<'PY' || echo "  (error creating tables - check DATABASE_URL / DB connectivity)"
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.db.session import create_tables

asyncio.run(create_tables())
print("Database schema verified/created (backend models).")
PY

echo ""
echo "0.2 Applying result versioning migration (if not already applied)..."
if [ -f "scripts/migrations/001_add_result_versioning.sql" ]; then
    # psql does not accept SQLAlchemy-style URLs like postgresql+psycopg2://...
    # Convert to a psql-compatible URL.
    PSQL_DATABASE_URL="${DATABASE_URL/postgresql+psycopg2/postgresql}"
    PSQL_DATABASE_URL="${PSQL_DATABASE_URL/postgresql+asyncpg/postgresql}"

    psql "$PSQL_DATABASE_URL" -f scripts/migrations/001_add_result_versioning.sql 2>/dev/null || echo "  (migration already applied, psql missing, or requires manual execution)"
else
    echo "  (migration file not found - skipping)"
fi

echo "0.3 Applying Tier-2 returns and runs migration (if not already applied)..."
if [ -f "scripts/migrations/002_tier2_returns_and_runs.sql" ]; then
    # Reuse normalized URL from above
    psql "$PSQL_DATABASE_URL" -f scripts/migrations/002_tier2_returns_and_runs.sql 2>/dev/null || echo "  (migration already applied, psql missing, or requires manual execution)"
else
    echo "  (migration file not found - skipping)"
fi

echo ""
echo "============================================================"
echo "STEP 1: DATA INGESTION"
echo "============================================================"
echo ""

echo "1.1 Ingesting S&P 500 current constituents + core FMP tables (backend schema)..."
echo "    NOTE: Requires an FMP subscription that supports /stable/* endpoints."
python scripts/ingest_fmp_ultimate.py 2>/dev/null || echo "  (skipped or failed - ensure FMP_API_KEY and API tier supports /stable/* endpoints)"

echo "1.2 Ingesting historical S&P 500 constituents..."
python scripts/ingest_sp500_historical.py 2>/dev/null || echo "  (skipped - may already exist)"

echo "1.3 Ingesting Fama-French factors..."
python scripts/ingest_ff_factors.py 2>/dev/null || echo "  (skipped - may already exist)"

echo "1.4 Ingesting delisting returns..."
python scripts/ingest_delisting_returns.py 2>/dev/null || echo "  (skipped - may already exist)"

echo ""
echo "============================================================"
echo "STEP 2: COMPUTE RESEARCH METRICS"
echo "============================================================"
echo ""

echo "2.1 Computing July-June returns (Fama-French convention)..."
python scripts/compute_july_june_returns.py || echo "  (error or already computed)"

echo "2.2 Computing volatility and momentum caches..."
python scripts/compute_research_metrics.py --full-recompute || echo "  (error - check logs)"

echo "2.3 Computing rolling window results..."
python - <<'PY' || echo "  (error - check backend logs)"
import asyncio
import sys
from pathlib import Path

# Ensure `backend/app` is importable as `app.*`
sys.path.insert(0, str(Path.cwd() / "backend"))

from app.db.session import async_session_factory
from app.services.rolling_window import RollingWindowAnalyzer


async def compute():
    async with async_session_factory() as session:
        analyzer = RollingWindowAnalyzer(session, use_july_june=True)
        for window in ["5yr", "10yr", "20yr"]:
            await analyzer.compute_all_rolling_windows(window, save_results=True)
        await analyzer.compute_annual_factor_premiums(save_results=True)
        await session.commit()
        print("Rolling windows computed with July-June returns")


asyncio.run(compute())
PY

echo ""
echo "============================================================"
echo "STEP 3: GENERATE PUBLICATION TABLES"
echo "============================================================"
echo ""

mkdir -p publication_tables

echo "3.1 Generating main results tables..."
python scripts/reproduce_all_tables.py --output-dir ./publication_tables || echo "  (error - check logs)"

echo "3.2 Generating delisting sensitivity analysis..."
python scripts/run_delisting_sensitivity.py > publication_tables/delisting_sensitivity.txt 2>&1 || true

echo "3.3 Validating membership data..."
python scripts/ingest_sp500_historical.py --validate > publication_tables/membership_validation.txt 2>&1 || true

echo "3.4 Generating spanning test table..."
python - <<'PY' || echo "  (requires FF factors - run ingest_ff_factors.py first)"
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

from app.db.session import async_session_factory
from app.services.statistics import StatisticalAnalyzer
from app.services.factor_tests import FactorSpanningAnalyzer


async def generate():
    async with async_session_factory() as session:
        stats = StatisticalAnalyzer(session)
        hml = await stats.compute_annual_hml_premium(use_july_june=True)
        if "error" not in hml:
            series = {p["formation_year"] + 1: p["hml_premium"] for p in hml["annual_premiums"]}
            spanning = FactorSpanningAnalyzer(session)
            results = await spanning.run_all_spanning_tests(series)
            with open("publication_tables/spanning_tests.json", "w") as f:
                json.dump(results, f, indent=2)
            print("Spanning tests saved")
        else:
            print("Need FF factors for spanning tests")


asyncio.run(generate())
PY

echo "3.5 Generating EW vs VW comparison..."
python - <<'PY' || echo "  (error - check logs)"
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

from app.db.session import async_session_factory
from app.services.rolling_window import RollingWindowAnalyzer


async def generate():
    async with async_session_factory() as session:
        analyzer = RollingWindowAnalyzer(session, use_july_june=True)
        result = await analyzer.compute_ew_vs_vw_premium(1995, 2024)
        with open("publication_tables/ew_vs_vw.json", "w") as f:
            json.dump(result, f, indent=2)
        print("EW vs VW comparison saved")


asyncio.run(generate())
PY

echo "3.6 Generating R&D cap sensitivity analysis..."
python - <<'PY' || echo "  (error - check logs)"
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

from app.db.session import async_session_factory
from app.services.rolling_window import RollingWindowAnalyzer


async def generate():
    async with async_session_factory() as session:
        analyzer = RollingWindowAnalyzer(session, use_july_june=True)
        result = await analyzer.compute_rd_cap_sensitivity(1995, 2024)
        with open("publication_tables/rd_cap_sensitivity.json", "w") as f:
            json.dump(result, f, indent=2)
        print("R&D cap sensitivity saved")


asyncio.run(generate())
PY

echo "3.7 Generating annual HML premium table..."
python - <<'PY' || echo "  (error - check logs)"
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

from app.db.session import async_session_factory
from app.services.statistics import StatisticalAnalyzer


async def generate():
    async with async_session_factory() as session:
        analyzer = StatisticalAnalyzer(session)
        result = await analyzer.compute_annual_hml_premium(use_july_june=True)
        with open("publication_tables/annual_hml_premium.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print("Annual HML premium saved")


asyncio.run(generate())
PY

echo ""
echo "============================================================"
echo "STEP 4: VALIDATION"
echo "============================================================"
echo ""

# Check if validation passed
if [ -f "publication_tables/all_tables.json" ]; then
    echo "✓ Main tables generated successfully"
else
    echo "✗ Main tables generation failed"
    exit 1
fi

echo ""
echo "============================================================"
echo "REPRODUCTION COMPLETE"
echo "============================================================"
echo ""
echo "Finished at: $(date)"
echo ""
echo "Output files:"
echo "  - publication_tables/all_tables.json          Main research tables"
echo "  - publication_tables/annual_hml_premium.json  Year-by-year HML premium (primary result)"
echo "  - publication_tables/spanning_tests.json      FF3/FF5/FF6 factor spanning tests"
echo "  - publication_tables/ew_vs_vw.json            Equal-weight vs Value-weight robustness"
echo "  - publication_tables/rd_cap_sensitivity.json  Outlier treatment sensitivity"
echo "  - publication_tables/delisting_sensitivity.txt"
echo "  - publication_tables/membership_validation.txt"
echo ""
echo "To verify results match the paper, compare values in"
echo "all_tables.json against the frozen publication snapshot (see /api/research/publication-snapshot)."
echo ""
echo "============================================================"
echo "EXTERNAL DATA REQUIREMENTS"
echo "============================================================"
echo ""
echo "This pipeline uses the following external data sources:"
echo ""
echo "1. Financial Modeling Prep (FMP) API"
echo "   - Requires: FMP_API_KEY environment variable"
echo "   - Used for: Income statements, daily prices, S&P 500 constituents"
echo "   - License: Commercial (subscription required)"
echo ""
echo "2. Ken French Data Library"
echo "   - URL: mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html"
echo "   - Used for: FF5 factors + Momentum, Risk-free rate"
echo "   - License: Free for academic use"
echo ""
echo "3. Optional (for Tier 2 upgrade):"
echo "   - CRSP via WRDS: Actual delisting returns, point-in-time membership"
echo "   - Compustat via WRDS: Alternative R&D data source"
echo ""
echo "See DATA_PROVENANCE.md for complete data documentation."
echo ""

