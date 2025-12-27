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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.api.routes import companies, factors, backtests, stats, fmp, ai_analysis, research, portfolio, papers, subscribe, donations, admin, analytics
from app.core.config import settings
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
        "name": "Analytics",
        "description": "Page view tracking and analytics",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_tables()
    yield
    # Shutdown
    await engine.dispose()


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
    "http://100.48.47.77",
]
DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=PRODUCTION_ORIGINS + DEVELOPMENT_ORIGINS if settings.DEBUG else PRODUCTION_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restrict methods
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
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(subscribe.router, prefix="/api", tags=["Subscribe"])
app.include_router(donations.router, prefix="/api", tags=["Donations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "2.1.0"}


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
