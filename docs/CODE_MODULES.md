# Code Modules Reference

**PATH**: `research/src/`

This document provides a comprehensive reference to all code modules in the R&D Alpha research platform.

---

## Module Overview

```
src/
├── ai/                # AI agents for text extraction
├── api/               # Flask API (admin dashboard)
├── backtesting/       # Backtesting engine
├── db/                # Database utilities
├── factors/           # Factor definitions
├── financials/        # Financial data processing
├── ingestion/         # Data ingestion
├── logging/           # Structured logging
├── models/            # ORM and DTO models
├── monitoring/        # Metrics and error tracking
├── services/          # Business logic layer
├── utils/             # Utility functions
├── admin_dash/        # Plotly Dash admin UI
├── user_dash/         # Plotly Dash user UI
├── adapters/          # External API adapters
├── research/          # Report generation
└── tests/             # Test suite
```

---

## AI Module (`src/ai/`)

AI-powered text extraction and analysis using GPT-4.

### Agents (`ai/agents/`)

| File | Purpose |
|------|---------|
| `rd_factor_agent.py` | Extract R&D signals from 10-K text chunks |
| `rd_factor_agent_v2.py` | Enhanced extraction with multi-signal support |
| `financial_statement_rd_extractor.py` | Extract R&D from structured financial statements |

**Key Function:**
```python
def extract_rd_from_chunk(
    chunk_text: str,
    chunk_id: str,
    page: Optional[int] = None,
    section: Optional[str] = None
) -> Optional[RDChunkSignals]:
    """Extract R&D signals from a single text chunk."""
```

### Orchestrator (`ai/orchestrator/`)

| File | Purpose |
|------|---------|
| `aggregation.py` | Aggregate chunk-level signals to company-level |
| `aggregation_v2.py` | Enhanced aggregation with confidence scoring |

### Schemas (`ai/schemas/`)

| File | Purpose |
|------|---------|
| `rd_chunk_schema.py` | Schema for chunk-level R&D signals |
| `rd_company_schema.py` | Schema for company-level R&D signals |
| `rd_extraction_schema.py` | Schema for extraction results |
| `rd_extraction_v2_schema.py` | Enhanced extraction schema |

### Utils (`ai/utils/`)

| File | Purpose |
|------|---------|
| `gpt_cache.py` | Redis caching for GPT responses |
| `gpt_cost_tracker.py` | Track GPT API costs |
| `html_table_extractor.py` | Extract tables from HTML documents |

### Supporting Files

| File | Purpose |
|------|---------|
| `client.py` | OpenAI API client wrapper |
| `config.py` | AI configuration (model, temperature) |
| `analysis_assistant.py` | General analysis prompts |
| `mapping_assistant.py` | Data mapping assistance |
| `narrative_assistant.py` | Generate narrative from computed results |

### Prompts (`ai/prompts/`)

Markdown files containing GPT prompts:
- `rd_extraction_v2_prompt.md` - R&D extraction instructions
- `analysis_base.md` - Analysis prompt template
- `mapping_base.md` - Mapping prompt template
- `narrative_base.md` - Narrative generation template

---

## Backtesting Module (`src/backtesting/`)

Publication-grade backtesting with Fama-French methodology.

### Core Engine

| File | Purpose |
|------|---------|
| `engine.py` | Main backtest orchestration |
| `enhanced_engine.py` | Advanced backtesting with more features |
| `specs.py` | Backtest specification dataclass |

**Key Class:**
```python
@dataclass
class BacktestSpec:
    factor_id: str           # e.g., "RND_v1_numeric"
    universe: List[str]      # Ticker list or ["pilot_top10"]
    start_year: int
    end_year: int
    num_buckets: int = 5     # Quintiles
    holding_period_years: int = 1
    formation_schedule: str = "annual_june"
```

### Portfolio Construction

| File | Purpose |
|------|---------|
| `portfolio_construction.py` | Quintile sorting, portfolio building |
| `portfolio_attribution.py` | Return attribution analysis |

**Key Functions:**
```python
def assign_buckets(
    factor_values: Dict[str, float],
    num_buckets: int
) -> Dict[str, int]:
    """Assign stocks to quintile buckets based on factor values."""

def build_long_short_portfolio(
    buckets: Dict[str, int],
    num_buckets: int
) -> Tuple[List[str], List[str]]:
    """Build long-short portfolio (Q5 long, Q1 short)."""
```

### Statistics

| File | Purpose |
|------|---------|
| `statistics.py` | Return calculations, t-stats, Sharpe ratios |
| `returns_calculator.py` | Detailed return computation |
| `regression_analysis.py` | Factor regressions, Fama-MacBeth |
| `cross_sectional.py` | Cross-sectional analysis |
| `time_segmentation.py` | Subperiod analysis |

**Key Functions:**
```python
def calculate_statistics(returns: List[float]) -> Dict:
    """Calculate mean, std, t-stat, Sharpe for a return series."""

def newey_west_tstat(returns: np.array, lag: int = 1) -> float:
    """Compute Newey-West HAC t-statistic."""
```

### Publication Grade (`backtesting/publication_grade/`)

Academic-quality analysis with rigorous methodology:

| File | Purpose |
|------|---------|
| `factor_returns.py` | HML-RD factor construction |
| `inference.py` | Newey-West HAC standard errors |
| `portfolio_engine.py` | Publication-grade portfolio construction |
| `run_backtest.py` | Entry point for publication backtests |
| `schemas.py` | Result schemas |
| `universe.py` | S&P 500 point-in-time management |

---

## Services Module (`src/services/`)

Business logic layer abstracting data access.

| File | Purpose |
|------|---------|
| `company_service.py` | Company data retrieval and search |
| `backtest_service.py` | Backtest execution and results retrieval |
| `portfolio_service.py` | ETF portfolio management |
| `price_service.py` | Stock price data access |
| `rd_service.py` | R&D factor calculations |
| `audit_service.py` | Audit trail logging |

**Example Usage:**
```python
from src.services.company_service import get_company_details

company = get_company_details("AAPL")
# Returns: Company(ticker="AAPL", name="Apple Inc.", sector="Technology", ...)
```

---

## Ingestion Module (`src/ingestion/`)

Data pipeline for external data sources.

| File | Purpose |
|------|---------|
| `sec_crawler.py` | Crawl SEC EDGAR for 10-K filings |
| `sec_submissions_api.py` | SEC submissions API client |
| `xbrl_ingestor.py` | Parse XBRL financial data |
| `xbrl_schemas.py` | XBRL schema definitions |
| `xbrl_tag_mapping.py` | Map XBRL tags to canonical schema |
| `universe_builder.py` | Build S&P 500 constituent universe |
| `url_validator.py` | Validate SEC URLs |
| `annual_report_text_extractor.py` | Extract text from annual reports |

**Key Functions:**
```python
def crawl_10k_filings(
    ticker: str,
    start_year: int,
    end_year: int
) -> List[Filing]:
    """Crawl SEC EDGAR for 10-K filings."""

def parse_xbrl(filing_path: str) -> FinancialsCore:
    """Parse XBRL filing and extract financials."""
```

---

## Factors Module (`src/factors/`)

Factor definitions and computation.

### R&D Factors (`factors/rd/`)

| File | Purpose |
|------|---------|
| `rd_numeric_engine.py` | Quantitative R&D factor (R&D/Revenue) |
| `rd_text_engine.py` | Text-based R&D factor (tone, mentions) |
| `rd_text_engine_v2.py` | Enhanced text factor with topics |

**Factor IDs:**
- `RND_v1_numeric` - R&D intensity (R&D/Revenue)
- `RND_v1_text` - Text-derived R&D tone score
- `RND_v1_combined` - Weighted combination

---

## Financials Module (`src/financials/`)

Financial data processing and validation.

| File | Purpose |
|------|---------|
| `canonical_schema.py` | Standardized financial schema |
| `normaliser.py` | Normalize different data sources |
| `comprehensive_normalization.py` | Full normalization pipeline |
| `ratios.py` | Compute financial ratios |
| `validation.py` | Data quality validation |
| `data_quality_scoring.py` | Quality scores for data |

**Key Functions:**
```python
def compute_rd_intensity(rd_expense: float, revenue: float) -> float:
    """Compute R&D intensity ratio."""
    if revenue <= 0:
        return None
    return rd_expense / revenue

def validate_financials(data: FinancialsCore) -> ValidationResult:
    """Validate financial data for completeness and sanity."""
```

---

## Models Module (`src/models/`)

### ORM Models (`models/orm/`)

SQLAlchemy models for database tables:

| Model | Table | Purpose |
|-------|-------|---------|
| `Company` | `companies` | Company metadata |
| `CompanyYearCore` | `company_year_core` | Annual company snapshots |
| `FinancialsCore` | `financials_core` | Core financial data |
| `FinancialsRatios` | `financials_ratios` | Computed ratios |
| `Price` | `prices` | Daily stock prices |
| `BacktestRun` | `backtest_runs` | Backtest metadata |
| `BacktestResult` | `backtest_results` | Backtest results |
| `TextFactorRD` | `text_factor_rd` | Text R&D signals |
| `AnnualReport` | `annual_reports` | 10-K filing metadata |
| `TextChunk` | `text_chunks` | Document text chunks |
| `FactorSpec` | `factor_specs` | Factor definitions |
| `FactorValue` | `factor_values` | Computed factor values |
| `VirtualETFSpec` | `virtual_etf_specs` | ETF specifications |
| `VirtualETFHolding` | `virtual_etf_holdings` | ETF holdings |
| `VirtualETFNav` | `virtual_etf_nav` | ETF NAV history |
| `Audit` | `audits` | Audit trail |
| `Job` | `jobs` | Background job tracking |
| `DocumentMap` | `document_maps` | Data mapping records |
| `RDFact` | `rd_facts` | Extracted R&D facts |

**Example:**
```python
class Company(Base):
    __tablename__ = "companies"
    
    ticker = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    sector = Column(String)
    industry = Column(String)
    cik = Column(String)
    
    financials = relationship("FinancialsCore", back_populates="company")
```

### DTO Models (`models/dto/`)

Data transfer objects:

| File | Purpose |
|------|---------|
| `backtest_dto.py` | Backtest request/response DTOs |
| `company_dto.py` | Company data DTOs |
| `ui_dto.py` | UI-specific DTOs |

---

## Database Module (`src/db/`)

Database utilities and connection management.

| File | Purpose |
|------|---------|
| `connection.py` | Database connection and session management |
| `base.py` | SQLAlchemy base class |
| `health.py` | Database health checks |
| `transaction_safety.py` | Transaction management utilities |

**Key Functions:**
```python
@contextmanager
def db_session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## API Module (`src/api/`)

Flask API for admin dashboard.

### Blueprints (`api/blueprints/`)

| File | Purpose |
|------|---------|
| `health_api.py` | Health check endpoints |
| `factor_api.py` | Factor data endpoints |
| `backtest_api.py` | Backtest endpoints |
| `company_api.py` | Company data endpoints |
| `unified_api.py` | Unified research endpoints |
| `metrics_api.py` | Prometheus metrics |
| `admin_api.py` | Admin operations |
| `user_api.py` | User-facing API |

### Supporting Files

| File | Purpose |
|------|---------|
| `app_factory.py` | Flask app creation |
| `auth.py` | Authentication middleware |
| `extensions.py` | Flask extensions (CORS, etc.) |

### Middleware (`api/middleware/`)

| File | Purpose |
|------|---------|
| `error_handler.py` | Global error handling |
| `metrics_middleware.py` | Request metrics collection |

### Schemas (`api/schemas/`)

| File | Purpose |
|------|---------|
| `openapi_spec.py` | OpenAPI specification |
| `admin_api_schemas.py` | Admin API schemas |
| `user_api_schemas.py` | User API schemas |

---

## Logging Module (`src/logging/`)

Structured logging with context.

| File | Purpose |
|------|---------|
| `logger.py` | Logger factory and configuration |
| `structured_logger.py` | JSON structured logging |
| `context.py` | Logging context management |

**Usage:**
```python
from src.logging.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing company", extra={"ticker": "AAPL", "year": 2023})
```

---

## Monitoring Module (`src/monitoring/`)

Metrics and error tracking.

| File | Purpose |
|------|---------|
| `metrics.py` | Prometheus metrics definitions |
| `sentry_config.py` | Sentry error tracking setup |

---

## Utils Module (`src/utils/`)

General utility functions.

| File | Purpose |
|------|---------|
| `config_loader.py` | Load YAML configuration files |
| `data_validation.py` | Generic data validation |
| `date_utils.py` | Date manipulation utilities |
| `time_utils.py` | Time-related utilities |
| `cik_validation.py` | Validate SEC CIK numbers |
| `exceptions.py` | Custom exception classes |
| `progress_tracker.py` | Progress bar utilities |
| `rate_limiter.py` | API rate limiting |
| `retry_handler.py` | Retry logic for API calls |
| `validations.py` | Input validation functions |
| `docstring_enhancer.py` | Auto-generate docstrings |

---

## Adapters Module (`src/adapters/`)

Adapters for external APIs.

| File | Purpose |
|------|---------|
| `fundamentals_adapter.py` | Adapt fundamental data sources |
| `market_data_adapter.py` | Adapt market data sources |
| `tasks_adapter.py` | Adapt background task systems |

---

## Dashboard Modules

### Admin Dashboard (`src/admin_dash/`)

Plotly Dash admin interface.

| File | Purpose |
|------|---------|
| `app.py` | Dash app entry point |
| `layout.py` | Page layout definitions |
| `callbacks/` | Dash callbacks for interactivity |
| `components/` | Reusable Dash components |
| `assets/` | CSS styles |

### User Dashboard (`src/user_dash/`)

Plotly Dash user-facing dashboard.

| File | Purpose |
|------|---------|
| `app.py` | Dash app entry point |
| `layout.py` | Page layout |
| `callbacks/` | User interaction callbacks |
| `components/` | UI components |
| `pages/` | Dashboard pages |
| `assets/` | CSS styles |

---

## Research Module (`src/research/`)

Report generation utilities.

| File | Purpose |
|------|---------|
| `report_generator.py` | Generate research reports |

---

## Tests Module (`src/tests/`)

Test suite.

### Structure

```
tests/
├── conftest.py           # Pytest fixtures
├── unit/                 # Unit tests
│   ├── test_backtesting.py
│   ├── test_statistics.py
│   └── ...
├── integration/          # Integration tests
│   ├── test_api_endpoints.py
│   └── test_full_pipeline_comprehensive.py
└── e2e/                  # End-to-end tests
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific module
pytest tests/unit/test_backtesting.py

# Verbose
pytest -v
```

---

## Configuration Files

### `config/settings.py`

Application settings loaded from environment:

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    FMP_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    SECRET_KEY: str
    DEBUG: bool = False
```

### `config/logging.yml`

Logging configuration.

### `config/universe.yml`

Universe definitions (S&P 500, pilot companies).

### `config/crawl.yml`

SEC crawling configuration.

---

## Import Conventions

```python
# Services
from src.services.company_service import get_company_details
from src.services.backtest_service import run_backtest

# Models
from src.models.orm.company import Company
from src.models.dto.backtest_dto import BacktestRequest

# Database
from src.db.connection import db_session_scope

# AI
from src.ai.agents.rd_factor_agent import extract_rd_from_chunk

# Utils
from src.utils.date_utils import get_fiscal_year_end
from src.logging.logger import get_logger
```

---

*Last updated: December 2025*

