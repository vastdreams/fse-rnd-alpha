"""
PATH: backend/app/main.py
PURPOSE:
  - FastAPI application entry point
  - Configures CORS, routers, and middleware
  - Provides OpenAPI documentation

ROLE IN ARCHITECTURE:
  - API layer entry point

NOTES FOR FUTURE AI:
  - API documentation available at /docs (Swagger) and /redoc (ReDoc)
  - All routes are versioned under /api prefix
  - Research endpoints are the primary public API
"""

from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import companies, factors, backtests, stats, fmp, ai_analysis, research, portfolio, papers, subscribe, donations, admin, analytics, auth, universe_rank, universe_company, books, company_reports
from app.api.routes.auth import ensure_bootstrap_user
from app.core.config import settings
from app.core.observability import init_error_tracking
from app.core.security import SecurityHeadersMiddleware, RateLimitMiddleware
from app.db.session import engine, create_tables


# ==============================================================================
# OpenAPI Configuration
# ==============================================================================

API_DESCRIPTION = """
# R&D Alpha Research API

This API provides access to research on **R&D Investment Intensity and Stock Returns**.

## Overview

The R&D Alpha research platform analyzes the relationship between corporate R&D 
investment and stock market returns, building on foundational work by Chan, 
Lakonishok & Sougiannis (2001) and Lev & Sougiannis (1996).

## Key Endpoints

### Research Analysis
- `/api/research/quintile-performance/{window_type}` - Get returns by R&D quintile
- `/api/research/rolling-windows/{window_type}` - Time-series of R&D premium
- `/api/research/aggregate-anova` - Statistical significance tests
- `/api/research/fama-macbeth/{window_type}` - Fama-MacBeth regression analysis

### Data Export (Replication)
- `/api/research/export/cohort-data.csv` - Full research cohort
- `/api/research/export/quintile-performance.csv` - Quintile returns
- `/api/research/export/rolling-windows.csv` - Rolling window data
- `/api/research/export/methodology-parameters.json` - All methodology parameters

### Portfolio Construction
- `/api/portfolio/etf-holdings` - Current R&D ETF holdings
- `/api/portfolio/sector-weights` - Sector allocation

## Authentication

Currently the API is open for research purposes. Rate limiting may be applied.

## Citation

If you use this data in academic research, please cite:
> R&D Alpha Research Platform (2025). research.finsoeasy.com
"""

TAGS_METADATA = [
    {
        "name": "Research",
        "description": "Core research analysis endpoints for R&D factor analysis",
    },
    {
        "name": "Portfolio",
        "description": "ETF construction and portfolio analysis",
    },
    {
        "name": "Papers",
        "description": "Research paper content and data",
    },
    {
        "name": "Statistics",
        "description": "Statistical analysis and tests",
    },
    {
        "name": "Companies",
        "description": "Company information and data",
    },
    {
        "name": "Factors",
        "description": "Factor construction and analysis",
    },
    {
        "name": "Backtests",
        "description": "Historical backtesting endpoints",
    },
    {
        "name": "FMP Data",
        "description": "Financial Modeling Prep data ingestion",
    },
    {
        "name": "AI Analysis",
        "description": "AI-powered analysis features",
    },
{
    "name": "Admin",
    "description": "Admin authentication and dashboard",
},
{
    "name": "Auth",
    "description": "End-user registration and login for Portfolio Lab",
},
{
    "name": "Analytics",
    "description": "Page view tracking and analytics",
},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Production schema is created only by the explicit release bootstrap and
    # then advanced through the migration ledger. Keeping runtime DDL behind a
    # deliberately named local-development flag prevents an application start
    # from silently changing a sealed release database.
    if os.environ.get("ALLOW_RUNTIME_SCHEMA_BOOTSTRAP") == "true":
        await create_tables()
    try:
        await ensure_bootstrap_user()
    except Exception as exc:
        # The post-migration restart initializes durable account records; do
        # not fall back to image-local auth if the database is not ready yet.
        print(f"[startup] account bootstrap deferred: {exc}")
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


init_error_tracking()

app = FastAPI(
    title="R&D Alpha Research API",
    description=API_DESCRIPTION,
    version="2.1.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "R&D Alpha Research",
        "url": "https://research.finsoeasy.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# ==============================================================================
# Security Middleware Stack (order matters - first added = last executed)
# ==============================================================================

# Rate limiting - enabled in production
if not settings.DEBUG:
    app.add_middleware(RateLimitMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS - more restrictive in production
PRODUCTION_ORIGINS = [
    "https://research.finsoeasy.com",
    "http://research.finsoeasy.com",
    "https://www.research.finsoeasy.com",
    "https://portfolio.finsoeasy.com",
    "http://portfolio.finsoeasy.com",
    "http://100.48.47.77",
    "https://13.211.113.53",
]
DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=PRODUCTION_ORIGINS + DEVELOPMENT_ORIGINS if settings.DEBUG else PRODUCTION_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit-Minute", "X-RateLimit-Remaining-Minute", "X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Include routers
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(factors.router, prefix="/api/factors", tags=["Factors"])
app.include_router(backtests.router, prefix="/api/backtests", tags=["Backtests"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(fmp.router, prefix="/api/fmp", tags=["FMP Data"])
app.include_router(ai_analysis.router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(subscribe.router, prefix="/api", tags=["Subscribe"])
app.include_router(donations.router, prefix="/api", tags=["Donations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(universe_rank.router, prefix="/api/universe", tags=["Universe Rank"])
app.include_router(universe_company.router, prefix="/api/universe", tags=["Universe Rank"])
app.include_router(books.router, prefix="/api/books", tags=["Books"])
app.include_router(company_reports.router, prefix="/api/reports", tags=["Company Reports"])

_RELEASE_METADATA_PATHS = frozenset(
    {
        "release_manifest.json",
        "release_metadata.json",
        "research_snapshot.json",
        "research_records.json",
    }
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_mounted_data_manifest(data_root: Path, manifest: dict[str, object]) -> str | None:
    """Return an integrity error when the mounted release tree differs from its manifest."""

    if manifest.get("schema_version") != 2:
        return "unsupported release manifest schema"
    files = manifest.get("files")
    required_sources = manifest.get("required_sources")
    artifacts = manifest.get("artifacts")
    if not isinstance(files, dict) or not isinstance(required_sources, dict) or not isinstance(artifacts, dict):
        return "manifest has no complete file inventory"

    actual_files: dict[str, dict[str, object]] = {}
    try:
        for candidate in sorted(data_root.rglob("*")):
            relative = candidate.relative_to(data_root).as_posix()
            if relative in _RELEASE_METADATA_PATHS:
                continue
            if candidate.is_symlink():
                return f"data tree contains symbolic link: {relative}"
            if candidate.is_file():
                actual_files[relative] = {
                    "bytes": candidate.stat().st_size,
                    "sha256": _hash_file(candidate),
                }
    except OSError:
        return "data tree could not be read"

    normalized_files: dict[str, dict[str, object]] = {}
    for relative, details in files.items():
        if (
            not isinstance(relative, str)
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not isinstance(details, dict)
            or not isinstance(details.get("bytes"), int)
            or details["bytes"] < 0
            or not isinstance(details.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", details["sha256"])
        ):
            return "manifest file inventory is invalid"
        normalized_files[relative] = {
            "bytes": details["bytes"],
            "sha256": details["sha256"],
        }

    if actual_files != normalized_files:
        return "mounted data files do not match the release inventory"

    canonical_content = {
        "schema_version": 2,
        "universe_version": manifest.get("universe_version"),
        "required_sources": required_sources,
        "artifacts": artifacts,
        "files": normalized_files,
    }
    computed_manifest_sha = hashlib.sha256(
        json.dumps(canonical_content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if computed_manifest_sha != manifest.get("manifest_sha256"):
        return "manifest checksum does not match its inventory"
    return None


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "2.1.0"}


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """Health check endpoint for monitoring (API-prefixed alias)."""
    return {"status": "healthy", "version": "2.1.0"}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe for investor-facing production traffic.

    Unlike /health (liveness), this verifies the deployed database schema,
    an active research universe, and a readable immutable research-data volume.
    Clients must validate this JSON response rather than treating an SPA HTTP 200 as
    readiness.
    """
    from sqlalchemy import text

    from app.db.session import async_session_maker

    checks: dict[str, str] = {}
    release: dict[str, Any] | None = None
    ok = True

    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - env dependent
        checks["database"] = f"error: {type(exc).__name__}"
        ok = False

    required_tables = (
        "metric_vectors",
        "saved_books",
        "dcf_runs",
        "company_memos",
        "user_accounts",
        "universe_builds",
        "universe_evidence_refs",
        "schema_migrations",
        "saved_book_holdings",
        "audit_exports",
        "legacy_account_identities",
    )
    required_migrations = (
        "007_investor_platform_release.sql",
        "013_owner_quarantine_and_versioned_writes.sql",
        "018_immutable_historical_outputs.sql",
        "019_personal_record_owner_foreign_keys.sql",
        "020_personal_history_immutability.sql",
    )
    required_triggers = (
        "trg_saved_books_history_integrity",
        "trg_saved_book_holdings_locked_integrity",
        "trg_dcf_runs_append_only",
        "trg_company_memos_append_only",
        "trg_audit_exports_append_only",
    )
    try:
        async with async_session_maker() as session:
            relation_rows = await session.execute(
                text(
                    "SELECT item AS table_name, to_regclass('public.' || item) AS relation "
                    "FROM unnest(CAST(:tables AS text[])) AS tables(item)"
                ),
                {"tables": list(required_tables)},
            )
            relations = {name: relation for name, relation in relation_rows.all()}
            missing = [name for name in required_tables if relations.get(name) is None]
            if missing:
                checks["investor_schema"] = f"missing: {', '.join(missing)}"
                ok = False
            else:
                checks["investor_schema"] = "ok"
                migration_rows = await session.execute(
                    text(
                        """SELECT filename FROM schema_migrations
                           WHERE filename = ANY(CAST(:migrations AS text[]))"""
                    ),
                    {"migrations": list(required_migrations)},
                )
                applied_migrations = set(migration_rows.scalars().all())
                missing_migrations = [
                    migration for migration in required_migrations if migration not in applied_migrations
                ]
                if missing_migrations:
                    checks["migration_ledger"] = f"missing: {', '.join(missing_migrations)}"
                    ok = False
                else:
                    checks["migration_ledger"] = "ok"

                trigger_rows = await session.execute(
                    text(
                        """SELECT tgname
                             FROM pg_trigger
                            WHERE NOT tgisinternal
                              AND tgenabled <> 'D'
                              AND tgname = ANY(CAST(:triggers AS text[]))"""
                    ),
                    {"triggers": list(required_triggers)},
                )
                enabled_triggers = set(trigger_rows.scalars().all())
                missing_triggers = [
                    trigger for trigger in required_triggers if trigger not in enabled_triggers
                ]
                if missing_triggers:
                    checks["research_integrity_triggers"] = (
                        f"missing or disabled: {', '.join(missing_triggers)}"
                    )
                    ok = False
                else:
                    checks["research_integrity_triggers"] = "ok"
                active_rows = (
                    await session.execute(
                        text(
                            """SELECT build.universe_version, build.source_sha,
                                      build.data_manifest_sha256, count(vector.ticker) AS vector_count
                                 FROM universe_builds AS build
                                 LEFT JOIN metric_vectors AS vector
                                   ON vector.universe_version = build.universe_version
                                WHERE build.is_active
                                  AND build.status = 'sealed'
                                GROUP BY build.universe_version, build.source_sha,
                                         build.data_manifest_sha256"""
                        )
                    )
                ).mappings().all()
                if len(active_rows) != 1:
                    checks["active_universe"] = f"expected one sealed active build, found {len(active_rows)}"
                    ok = False
                else:
                    active = active_rows[0]
                    source_sha = str(active["source_sha"] or "")
                    manifest_sha = str(active["data_manifest_sha256"] or "")
                    if not active["vector_count"]:
                        checks["active_universe"] = "active build has no vectors"
                        ok = False
                    elif not re.fullmatch(r"[0-9a-f]{40}", source_sha):
                        checks["active_universe"] = "active build has no committed source SHA"
                        ok = False
                    elif not re.fullmatch(r"[0-9a-f]{64}", manifest_sha):
                        checks["active_universe"] = "active build has no immutable data manifest"
                        ok = False
                    else:
                        checks["active_universe"] = (
                            f"ok ({active['vector_count']} vectors; {active['universe_version']})"
                        )
                        release = {
                            "universe_version": str(active["universe_version"]),
                            "source_sha": source_sha,
                            "data_manifest_sha256": manifest_sha,
                        }
                        runtime_source_sha = os.environ.get("RELEASE_SOURCE_SHA", "")
                        runtime_release = {
                            "release_ref": os.environ.get("RELEASE_REF", ""),
                            "source_sha": runtime_source_sha,
                            "backend_image": os.environ.get("RELEASE_BACKEND_IMAGE", ""),
                            "frontend_image": os.environ.get("RELEASE_FRONTEND_IMAGE", ""),
                        }
                        if not runtime_source_sha:
                            checks["runtime_release"] = "not attested"
                        elif not re.fullmatch(r"[0-9a-f]{40}", runtime_source_sha):
                            checks["runtime_release"] = "invalid source SHA"
                            ok = False
                        elif runtime_source_sha != source_sha:
                            checks["runtime_release"] = "does not match active universe"
                            ok = False
                        elif not runtime_release["release_ref"]:
                            checks["runtime_release"] = "missing release ref"
                            ok = False
                        else:
                            checks["runtime_release"] = "ok"
                            release["runtime"] = runtime_release
    except Exception as exc:  # pragma: no cover - env dependent
        checks["investor_schema"] = f"error: {type(exc).__name__}"
        ok = False

    data_volume = Path(os.environ.get("APP_DATA_DIR", "/app/data"))
    try:
        readable = data_volume.exists() and os.access(data_volume, os.R_OK)
        checks["research_data_volume"] = "ok" if readable else "unreadable"
        if not readable:
            ok = False
        elif release is None:
            checks["research_data_manifest"] = "no active immutable build"
            ok = False
        else:
            manifest_path = data_volume / "release_manifest.json"
            try:
                manifest = json.loads(manifest_path.read_text())
                if not isinstance(manifest, dict):
                    raise ValueError("release manifest must be an object")
                integrity_error = _verify_mounted_data_manifest(data_volume, manifest)
                if integrity_error:
                    checks["research_data_manifest"] = integrity_error
                    ok = False
                elif (
                    manifest.get("universe_version") != release["universe_version"]
                    or manifest.get("manifest_sha256") != release["data_manifest_sha256"]
                ):
                    checks["research_data_manifest"] = "does not match active universe"
                    ok = False
                else:
                    checks["research_data_manifest"] = "ok"
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                checks["research_data_manifest"] = "missing or invalid"
                ok = False
    except Exception as exc:  # pragma: no cover - path dependent
        checks["research_data_volume"] = f"error: {type(exc).__name__}"
        ok = False

    if (
        settings.AUTH_PUBLIC_REGISTRATION
        and settings.AUTH_REQUIRE_EMAIL_VERIFICATION
        and not settings.DEBUG
    ):
        email_ready = bool(settings.RESEND_API_KEY and settings.AUTH_EMAIL_FROM)
        checks["auth_email_delivery"] = "ok" if email_ready else "missing"
        if not email_ready:
            ok = False

    status_code = 200 if ok else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": ok,
            "checks": checks,
            "release": release,
            "version": "2.1.0",
        },
    )


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint with API info and documentation links.
    
    Returns links to documentation and key endpoints.
    """
    return {
        "name": "R&D Alpha Research API",
        "version": "2.1.0",
        "description": "Research API for R&D Investment Intensity and Stock Returns",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "key_endpoints": {
            "quintile_performance": "/api/research/quintile-performance/5yr",
            "statistical_tests": "/api/research/aggregate-anova",
            "data_export": "/api/research/export/cohort-data.csv",
            "methodology": "/api/research/export/methodology-parameters.json",
            "portfolio": "/api/portfolio/etf-holdings",
        },
        "research_url": "https://research.finsoeasy.com",
    }


@app.get("/api", tags=["Health"])
async def api_root():
    """API root - lists all available endpoints by category."""
    return {
        "version": "2.1.0",
        "categories": {
            "research": {
                "base": "/api/research",
                "description": "Core R&D research analysis",
                "endpoints": [
                    "GET /quintile-performance/{window_type}",
                    "GET /rolling-windows/{window_type}",
                    "GET /aggregate-anova",
                    "GET /fama-macbeth/{window_type}",
                    "GET /summary-statistics",
                    "GET /subperiod-analysis",
                    "GET /transaction-costs",
                    "GET /net-of-cost-returns/{window_type}",
                ],
            },
            "export": {
                "base": "/api/research/export",
                "description": "Data export for replication",
                "endpoints": [
                    "GET /cohort-data.csv",
                    "GET /quintile-performance.csv",
                    "GET /rolling-windows.csv",
                    "GET /statistical-results.csv",
                    "GET /methodology-parameters.json",
                ],
            },
            "portfolio": {
                "base": "/api/portfolio",
                "description": "ETF and portfolio analysis",
                "endpoints": [
                    "GET /etf-holdings",
                    "GET /sector-weights",
                    "GET /all-candidates",
                    "GET /forecast-vs-actual",
                ],
            },
        },
    }
