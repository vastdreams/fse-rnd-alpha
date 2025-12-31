# R&D Alpha: Innovation-Driven Investment Research

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Demo-research.finsoeasy.com-green)](https://research.finsoeasy.com)

**A comprehensive research platform investigating the relationship between R&D investment intensity and stock returns.**

---

## 📊 Research Summary

This project presents evidence that companies with higher R&D intensity (R&D expenditure as a percentage of revenue) generate statistically significant excess returns over extended time horizons.

### Key Findings

| Metric | Value |
|--------|-------|
| **Annual R&D Premium** | +7.55% (t-stat: 2.78) |
| **Win Rate** | 71% (17/24 years positive) |
| **Net-of-Cost Premium** | +5.33% annually |
| **Statistical Significance** | p = 0.0107 |

### Methodology Highlights

- **Return Convention**: July-June (Fama-French) to avoid look-ahead bias
- **Universe**: Point-in-time S&P 500 constituents
- **Sample Period**: 1995-2024 (30 years)
- **Delisting Adjustment**: Literature-calibrated (Shumway 1997)

---

## 🚀 Live Demo

**[research.finsoeasy.com](https://research.finsoeasy.com)**

Features:
- Interactive R&D premium analysis
- Rolling window visualizations
- Factor spanning tests
- Implementable R&D ETF simulator
- Publication-ready research paper

---

## 📁 Repository Structure

```
rd-alpha-research/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/         # REST API endpoints
│   │   │   ├── research.py     # Core research endpoints
│   │   │   ├── portfolio.py    # ETF/portfolio endpoints
│   │   │   ├── companies.py    # Company data
│   │   │   ├── factors.py      # Factor analysis
│   │   │   ├── backtests.py    # Backtesting
│   │   │   ├── fmp.py          # FMP data proxy
│   │   │   ├── ai_analysis.py  # AI-powered analysis
│   │   │   ├── papers.py       # Paper content
│   │   │   ├── admin.py        # Admin dashboard
│   │   │   └── analytics.py    # Page tracking
│   │   ├── services/           # Business logic
│   │   │   ├── publication_snapshot.py  # Frozen research data
│   │   │   ├── rolling_window.py        # Time-series analysis
│   │   │   ├── etf_backtester.py        # ETF simulation
│   │   │   ├── factor_tests.py          # Statistical tests
│   │   │   ├── fmp_client.py            # FMP API client
│   │   │   └── rd_alpha_scorer.py       # R&D scoring
│   │   ├── core/               # Configuration and security
│   │   ├── db/                 # Database session management
│   │   └── main.py             # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/              # Main application pages
│   │   │   ├── papers/
│   │   │   │   └── MainPaper.tsx    # Academic paper (~4000 lines)
│   │   │   ├── Whitepaper.tsx       # 11-slide investor deck
│   │   │   ├── Portfolio.tsx        # R&D ETF simulator
│   │   │   ├── Research.tsx         # Research overview
│   │   │   ├── Companies.tsx        # Company explorer
│   │   │   ├── Statistics.tsx       # Statistical analysis
│   │   │   └── Methodology.tsx      # Methodology details
│   │   ├── components/
│   │   │   ├── layout/              # Sidebar, Navbar, Footer
│   │   │   ├── ui/                  # shadcn/ui components
│   │   │   ├── SafeChart.tsx        # Recharts wrapper
│   │   │   ├── InfoTooltip.tsx      # Metric explanations
│   │   │   └── TableOfContents.tsx  # Paper navigation
│   │   ├── lib/
│   │   │   ├── api.ts               # API client
│   │   │   ├── analytics.ts         # Page view tracking
│   │   │   └── utils.ts             # Utility functions
│   │   └── hooks/                   # React Query hooks
│   ├── package.json
│   └── vite.config.ts
│
├── src/                        # Core research modules (Python)
│   ├── ai/                     # AI agents for R&D extraction
│   │   ├── agents/
│   │   │   ├── rd_factor_agent.py   # R&D signal extraction
│   │   │   └── rd_factor_agent_v2.py
│   │   ├── orchestrator/            # Multi-agent coordination
│   │   ├── prompts/                 # GPT prompts
│   │   ├── schemas/                 # Pydantic schemas
│   │   └── utils/                   # Caching, cost tracking
│   │
│   ├── backtesting/            # Backtesting engine
│   │   ├── engine.py                # Main backtest runner
│   │   ├── enhanced_engine.py       # Advanced backtesting
│   │   ├── portfolio_construction.py # Quintile sorting
│   │   ├── statistics.py            # Statistical calculations
│   │   ├── returns_calculator.py    # Return computation
│   │   ├── regression_analysis.py   # Factor regressions
│   │   └── publication_grade/       # Academic-quality analysis
│   │       ├── factor_returns.py    # HML-RD factor
│   │       ├── inference.py         # Newey-West t-stats
│   │       ├── portfolio_engine.py  # Portfolio construction
│   │       └── universe.py          # S&P 500 management
│   │
│   ├── services/               # Business logic layer
│   │   ├── company_service.py       # Company data retrieval
│   │   ├── backtest_service.py      # Backtest execution
│   │   ├── portfolio_service.py     # ETF management
│   │   ├── price_service.py         # Price data
│   │   ├── rd_service.py            # R&D calculations
│   │   └── audit_service.py         # Audit trail
│   │
│   ├── ingestion/              # Data ingestion
│   │   ├── sec_crawler.py           # SEC EDGAR crawler
│   │   ├── xbrl_ingestor.py         # XBRL parsing
│   │   ├── xbrl_tag_mapping.py      # Tag standardization
│   │   ├── universe_builder.py      # S&P 500 constituents
│   │   └── annual_report_text_extractor.py
│   │
│   ├── factors/                # Factor definitions
│   │   └── rd/
│   │       ├── rd_numeric_engine.py # Quantitative R&D factor
│   │       ├── rd_text_engine.py    # Text-based R&D factor
│   │       └── rd_text_engine_v2.py
│   │
│   ├── financials/             # Financial data processing
│   │   ├── canonical_schema.py      # Standardized schema
│   │   ├── normaliser.py            # Data normalization
│   │   ├── ratios.py                # Financial ratios
│   │   ├── validation.py            # Data validation
│   │   └── data_quality_scoring.py
│   │
│   ├── models/                 # Data models
│   │   ├── orm/                     # SQLAlchemy ORM models
│   │   │   ├── company.py           # Company metadata
│   │   │   ├── financials_core.py   # Core financial data
│   │   │   ├── financials_ratios.py # Computed ratios
│   │   │   ├── price.py             # Stock prices
│   │   │   ├── backtest_run.py      # Backtest metadata
│   │   │   ├── text_factor_rd.py    # Text R&D signals
│   │   │   └── virtual_etf_*.py     # ETF models
│   │   └── dto/                     # Data transfer objects
│   │
│   ├── api/                    # Flask API (admin dash)
│   │   ├── app_factory.py           # Flask app creation
│   │   ├── blueprints/              # API blueprints
│   │   └── middleware/              # Error handling, metrics
│   │
│   ├── admin_dash/             # Plotly Dash admin dashboard
│   ├── user_dash/              # Plotly Dash user dashboard
│   │
│   ├── db/                     # Database utilities
│   │   ├── connection.py            # Connection management
│   │   ├── health.py                # Health checks
│   │   └── transaction_safety.py
│   │
│   ├── logging/                # Structured logging
│   ├── monitoring/             # Metrics and Sentry
│   ├── utils/                  # Utility functions
│   └── tests/                  # Test suite
│
├── scripts/                    # Data pipeline scripts
│   ├── ingest_fmp_ultimate.py       # FMP data ingestion
│   ├── ingest_ff_factors.py         # Fama-French factors
│   ├── ingest_sp500_historical.py   # S&P 500 history
│   ├── ingest_wrds_tier2.py         # WRDS/CRSP data
│   ├── compute_july_june_returns.py # Return calculation
│   ├── compute_rd_factors.py        # R&D factor computation
│   ├── crawl_sec_filings.py         # SEC crawler
│   ├── reproduce_publication.sh     # Full reproduction
│   └── init_db.py                   # Database setup
│
├── deploy/                     # Production deployment
│   ├── docker-compose.yml           # Service orchestration
│   ├── nginx.conf                   # Reverse proxy
│   ├── deploy.sh                    # Deployment script
│   └── frontend/dist/               # Mounted to nginx
│
├── papers/                     # Research paper drafts
│   ├── METHODOLOGY.md
│   ├── paper_1_rd_returns.md
│   ├── paper_2_industry_analysis.md
│   ├── paper_3_multifactor.md
│   └── paper_4_fundamental.md
│
├── docs/                       # Additional documentation
│   ├── api.md
│   ├── database.md
│   └── DATA_ACQUISITION.md
│
├── config/                     # Configuration files
│   ├── settings.py                  # App settings
│   ├── logging.yml                  # Logging config
│   └── universe.yml                 # Universe definitions
│
├── data/                       # Data files
│   ├── exports/                     # Exported datasets
│   └── reference/                   # Reference data
│
├── migrations/                 # Alembic migrations
│
├── DATA_AVAILABILITY.md        # Data sources & replication
├── DATA_PROVENANCE.md          # Data collection methods
├── DEPLOYMENT_GUIDE.md         # Deployment instructions
├── FSE_RND_ALPHA_HANDOFF.md    # Complete handoff docs
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Local Docker setup
├── alembic.ini                 # Migration config
└── pytest.ini                  # Test config
```

---

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis (optional, for caching)

### Local Development

```bash
# Clone repository
git clone https://github.com/vastdreams/rd-alpha-research.git
cd rd-alpha-research

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Docker Deployment

```bash
cd deploy
cp .env.example .env
# Edit .env with your database credentials
docker compose up -d
```

---

## 📈 Research Methodology

### Data Sources

| Source | Description | Tier |
|--------|-------------|------|
| Financial Modeling Prep | Fundamentals, prices | Tier 1 |
| Ken French Data Library | Factor returns | Tier 1 |
| SEC EDGAR | 10-K filings | Tier 1 |
| CRSP/Compustat | Premium data (optional) | Tier 2 |

### Statistical Framework

1. **Quintile Sorting**: Firms ranked by R&D/Revenue annually (June)
2. **HML-RD Factor**: Q5 (High R&D) minus Q1 (Low R&D) returns
3. **Inference**: Newey-West HAC standard errors (lag=1)
4. **Robustness**: Factor spanning, size controls, delisting sensitivity

### Return Convention

```
Fiscal Year End: Dec 31, 2023
10-K Filed By: Mar 31, 2024
Portfolio Formation: June 30, 2024
Holding Period: July 1, 2024 → June 30, 2025
```

### Key References

- Chan, Lakonishok & Sougiannis (2001) - R&D and stock returns
- Fama & French (1993, 2015) - Factor models
- Shumway (1997) - Delisting bias correction

---

## 🔌 API Endpoints

### Research Analysis
| Endpoint | Description |
|----------|-------------|
| `GET /api/research/publication-snapshot` | Frozen research results |
| `GET /api/research/quintile-performance/{window}` | Returns by quintile |
| `GET /api/research/rolling-windows/{window}` | Time-varying premium |
| `GET /api/research/aggregate-anova` | Statistical tests |
| `GET /api/research/fama-macbeth/{window}` | Fama-MacBeth regression |

### Portfolio & ETF
| Endpoint | Description |
|----------|-------------|
| `GET /api/portfolio/etf-holdings` | Current R&D ETF holdings |
| `GET /api/portfolio/sector-weights` | Sector allocation |
| `GET /api/portfolio/all-candidates` | All candidate stocks |
| `GET /api/portfolio/forecast-vs-actual` | Forecast performance |

### Data Export
| Endpoint | Description |
|----------|-------------|
| `GET /api/research/export/cohort-data.csv` | Full research cohort |
| `GET /api/research/export/quintile-performance.csv` | Quintile returns |
| `GET /api/research/export/rolling-windows.csv` | Rolling window data |
| `GET /api/research/export/methodology-parameters.json` | Methodology params |

Full API documentation: `/docs` (Swagger UI)

---

## 🧠 Core Modules

### AI Agents (`src/ai/`)

The AI layer uses GPT-4 for extracting R&D signals from unstructured text:

```python
# R&D factor extraction from 10-K chunks
from src.ai.agents.rd_factor_agent import extract_rd_from_chunk

signals = extract_rd_from_chunk(
    chunk_text="...",
    chunk_id="chunk_001",
    page=42,
    section="Business"
)
# Returns: RDChunkSignals(rd_mentions=5, topics=["AI", "Cloud"], tone_score=0.7)
```

### Backtesting Engine (`src/backtesting/`)

Publication-grade backtesting with Fama-French methodology:

```python
from src.backtesting.engine import run_backtest
from src.backtesting.specs import BacktestSpec

spec = BacktestSpec(
    factor_id="RND_v1_numeric",
    universe=["pilot_top10"],
    start_year=1995,
    end_year=2024,
    num_buckets=5,
    holding_period_years=1
)
results = run_backtest(spec)
```

### Services Layer (`src/services/`)

Business logic abstraction over data access:

```python
from src.services.company_service import get_company_details
from src.services.rd_service import calculate_rd_intensity

company = get_company_details("AAPL")
rd_intensity = calculate_rd_intensity("AAPL", 2023)
```

---

## 🗄️ Database Schema

### Key Tables

| Table | Description |
|-------|-------------|
| `companies` | Company metadata (ticker, name, sector, CIK) |
| `financials_core` | Annual fundamentals (R&D, revenue, assets) |
| `financials_ratios` | Computed ratios (R&D intensity, ROE) |
| `prices` | Daily stock prices (adj_close) |
| `company_year_core` | Annual company snapshots |
| `text_factor_rd` | Text-derived R&D signals |
| `backtest_run` | Backtest execution metadata |
| `backtest_result` | Backtest results by year/bucket |
| `publication_snapshots` | Frozen research results |

---

## 🔧 Environment Variables

```env
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/rd_alpha

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys
FMP_API_KEY=your_fmp_api_key
OPENAI_API_KEY=your_openai_key  # For AI agents

# AWS (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=fse-rnd-alpha-data

# Security
SECRET_KEY=your_secret_key
DEBUG=false
```

---

## 📋 Scripts Reference

### Data Ingestion
```bash
# Full FMP ingestion
python scripts/ingest_fmp_ultimate.py

# Fama-French factors
python scripts/ingest_ff_factors.py

# S&P 500 constituents
python scripts/ingest_sp500_historical.py

# SEC filings
python scripts/crawl_sec_filings.py
```

### Research Computation
```bash
# Compute returns (July-June)
python scripts/compute_july_june_returns.py --data-tier tier1

# Compute R&D factors
python scripts/compute_rd_factors.py

# Generate research metrics
python scripts/compute_research_metrics.py

# Full reproduction
./scripts/reproduce_publication.sh
```

### Database
```bash
# Initialize
python scripts/init_db.py

# Migrations
alembic upgrade head
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov=backend

# Specific test file
pytest tests/unit/test_backtesting.py
```

---

## 📄 Documentation

- [Data Availability](DATA_AVAILABILITY.md) - Data sources and access
- [Data Provenance](DATA_PROVENANCE.md) - Collection methodology
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production setup
- [Handoff Documentation](FSE_RND_ALPHA_HANDOFF.md) - Complete project handoff

---

## 📜 Citation

If you use this research, please cite:

```bibtex
@software{rd_alpha_2024,
  author = {Sehgal, Abhishek},
  title = {R&D Alpha: Innovation-Driven Investment Research},
  year = {2024},
  url = {https://github.com/vastdreams/rd-alpha-research}
}
```

---

## ⚠️ Disclaimer

This research is provided for educational and informational purposes only. It does not constitute investment advice. Past performance does not guarantee future results. The authors are not responsible for any investment decisions made based on this research.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

---

**Built with ❤️ by [Finsoeasy](https://finsoeasy.com)**
