# Database Schema Reference

**Database**: PostgreSQL 15+
**ORM**: SQLAlchemy 2.0
**Async Driver**: asyncpg

> **Note (Jan 2026):** This document includes legacy schema context from earlier iterations of the project.
> The source of truth for the live platform schema is `backend/app/db/models.py`.
> In the current Tier-1 publication pipeline, the key market-data tables are:
> - `fmp_daily_prices` (split-adjusted close), and
> - `fmp_dividends` (ex-dividend events, used to construct a total-return proxy).

---

## Connection Setup

### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
createdb rd_alpha
```

### Docker

```bash
docker run -d \
  --name rd_alpha_postgres \
  -e POSTGRES_DB=rd_alpha \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine
```

### Connection String

Set in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rd_alpha
```

---

## Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE TABLES                                    │
├─────────────────┬─────────────────┬─────────────────┬──────────────────┤
│   companies     │  company_year   │  financials_    │    prices        │
│                 │    _core        │    core         │                  │
└────────┬────────┴────────┬────────┴────────┬────────┴────────┬─────────┘
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DERIVED TABLES                                   │
├─────────────────┬─────────────────┬─────────────────┬──────────────────┤
│ financials_     │  text_factor_   │  backtest_runs  │ quintile_        │
│   ratios        │    rd           │                 │   assignments    │
└─────────────────┴─────────────────┴─────────────────┴──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ANALYSIS TABLES                                   │
├─────────────────┬─────────────────┬─────────────────┬──────────────────┤
│ backtest_       │  rolling_window │  anova_results  │  publication_    │
│   results       │    _results     │                 │   snapshots      │
└─────────────────┴─────────────────┴─────────────────┴──────────────────┘
```

---

## Core Tables

### companies

Company metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `ticker` | VARCHAR(10) | NO | Primary key, stock ticker |
| `name` | VARCHAR(255) | NO | Company name |
| `sector` | VARCHAR(100) | YES | GICS sector |
| `industry` | VARCHAR(100) | YES | GICS industry |
| `cik` | VARCHAR(10) | YES | SEC CIK number |
| `exchange` | VARCHAR(20) | YES | Stock exchange |
| `is_active` | BOOLEAN | NO | Currently trading |
| `created_at` | TIMESTAMP | NO | Record creation time |
| `updated_at` | TIMESTAMP | NO | Last update time |

```sql
CREATE TABLE companies (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    cik VARCHAR(10),
    exchange VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_cik ON companies(cik);
```

---

### company_year_core

Annual company snapshot linking all year-specific data.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `fiscal_year` | INTEGER | NO | Fiscal year |
| `data_date` | DATE | YES | Data as-of date |
| `created_at` | TIMESTAMP | NO | Record creation |

```sql
CREATE TABLE company_year_core (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL REFERENCES companies(ticker),
    fiscal_year INTEGER NOT NULL,
    data_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, fiscal_year)
);

CREATE INDEX idx_coreYear_ticker ON company_year_core(ticker);
CREATE INDEX idx_coreYear_year ON company_year_core(fiscal_year);
```

---

### financials_core

Core financial data from income statements.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `company_year_id` | INTEGER | NO | FK to company_year_core |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `fiscal_year` | INTEGER | NO | Fiscal year |
| `revenue` | NUMERIC(18,2) | YES | Total revenue |
| `rd_expense` | NUMERIC(18,2) | YES | R&D expense |
| `gross_profit` | NUMERIC(18,2) | YES | Gross profit |
| `operating_income` | NUMERIC(18,2) | YES | Operating income |
| `net_income` | NUMERIC(18,2) | YES | Net income |
| `total_assets` | NUMERIC(18,2) | YES | Total assets |
| `total_equity` | NUMERIC(18,2) | YES | Total equity |
| `shares_outstanding` | NUMERIC(18,2) | YES | Shares outstanding |
| `source` | VARCHAR(50) | YES | Data source (FMP, WRDS) |
| `data_tier` | VARCHAR(10) | YES | tier1 or tier2 |

```sql
CREATE TABLE financials_core (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER REFERENCES company_year_core(id),
    ticker VARCHAR(10) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    revenue NUMERIC(18,2),
    rd_expense NUMERIC(18,2),
    gross_profit NUMERIC(18,2),
    operating_income NUMERIC(18,2),
    net_income NUMERIC(18,2),
    total_assets NUMERIC(18,2),
    total_equity NUMERIC(18,2),
    shares_outstanding NUMERIC(18,2),
    source VARCHAR(50),
    data_tier VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, fiscal_year)
);

CREATE INDEX idx_fin_ticker ON financials_core(ticker);
CREATE INDEX idx_fin_year ON financials_core(fiscal_year);
```

---

### financials_ratios

Computed financial ratios.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `company_year_id` | INTEGER | NO | FK to company_year_core |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `fiscal_year` | INTEGER | NO | Fiscal year |
| `rd_intensity` | NUMERIC(10,6) | YES | R&D / Revenue |
| `gross_margin` | NUMERIC(10,6) | YES | Gross profit / Revenue |
| `operating_margin` | NUMERIC(10,6) | YES | Operating income / Revenue |
| `net_margin` | NUMERIC(10,6) | YES | Net income / Revenue |
| `roe` | NUMERIC(10,6) | YES | Return on equity |
| `roa` | NUMERIC(10,6) | YES | Return on assets |

```sql
CREATE TABLE financials_ratios (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER REFERENCES company_year_core(id),
    ticker VARCHAR(10) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    rd_intensity NUMERIC(10,6),
    gross_margin NUMERIC(10,6),
    operating_margin NUMERIC(10,6),
    net_margin NUMERIC(10,6),
    roe NUMERIC(10,6),
    roa NUMERIC(10,6),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, fiscal_year)
);
```

---

### prices

Daily stock prices.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `date` | DATE | NO | Price date |
| `open` | NUMERIC(12,4) | YES | Open price |
| `high` | NUMERIC(12,4) | YES | High price |
| `low` | NUMERIC(12,4) | YES | Low price |
| `close` | NUMERIC(12,4) | YES | Close price |
| `adj_close` | NUMERIC(12,4) | YES | Adjusted close |
| `volume` | BIGINT | YES | Trading volume |

```sql
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4),
    adj_close NUMERIC(12,4),
    volume BIGINT,
    UNIQUE(ticker, date)
);

CREATE INDEX idx_prices_ticker ON prices(ticker);
CREATE INDEX idx_prices_date ON prices(date);
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date);
```

---

## Text Factor Tables

### text_factor_rd

R&D signals extracted from text.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `company_year_id` | INTEGER | NO | FK to company_year_core |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `fiscal_year` | INTEGER | NO | Fiscal year |
| `rd_mentions` | INTEGER | YES | Count of R&D mentions |
| `rd_tone_score` | NUMERIC(5,3) | YES | Tone score (-1 to +1) |
| `rd_topics` | JSONB | YES | Topics array |
| `confidence` | NUMERIC(5,3) | YES | Extraction confidence |
| `source_doc` | VARCHAR(255) | YES | Source document |

```sql
CREATE TABLE text_factor_rd (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER REFERENCES company_year_core(id),
    ticker VARCHAR(10) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    rd_mentions INTEGER,
    rd_tone_score NUMERIC(5,3),
    rd_topics JSONB,
    confidence NUMERIC(5,3),
    source_doc VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, fiscal_year)
);
```

---

### text_chunks

Document text chunks for processing.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `annual_report_id` | INTEGER | NO | FK to annual_reports |
| `chunk_index` | INTEGER | NO | Chunk sequence number |
| `content` | TEXT | NO | Chunk text content |
| `page_number` | INTEGER | YES | Source page number |
| `section` | VARCHAR(100) | YES | Document section |
| `processed` | BOOLEAN | NO | Processing status |

```sql
CREATE TABLE text_chunks (
    id SERIAL PRIMARY KEY,
    annual_report_id INTEGER REFERENCES annual_reports(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    section VARCHAR(100),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Backtest Tables

### backtest_runs

Backtest execution metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `spec_hash` | VARCHAR(32) | NO | Hash of backtest spec |
| `factor_id` | VARCHAR(50) | NO | Factor being tested |
| `universe` | TEXT | NO | Universe description |
| `start_year` | INTEGER | NO | Start year |
| `end_year` | INTEGER | NO | End year |
| `formation_schedule` | VARCHAR(50) | NO | Formation timing |
| `holding_period_years` | INTEGER | NO | Holding period |
| `spec_json` | JSONB | NO | Full specification |
| `status` | VARCHAR(20) | NO | running, completed, failed |
| `started_at` | TIMESTAMP | NO | Start time |
| `completed_at` | TIMESTAMP | YES | Completion time |

```sql
CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    spec_hash VARCHAR(32) UNIQUE NOT NULL,
    factor_id VARCHAR(50) NOT NULL,
    universe TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    formation_schedule VARCHAR(50),
    holding_period_years INTEGER,
    spec_json JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

### backtest_results

Backtest results by year and bucket.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `backtest_run_id` | INTEGER | NO | FK to backtest_runs |
| `spec_hash` | VARCHAR(32) | NO | Backtest spec hash |
| `formation_year` | INTEGER | NO | Portfolio formation year |
| `horizon_years` | INTEGER | NO | Holding period |
| `bucket` | VARCHAR(20) | NO | Quintile label |
| `mean_ret` | NUMERIC(10,6) | YES | Mean return |
| `t_stat` | NUMERIC(10,4) | YES | T-statistic |
| `n` | INTEGER | YES | Number of observations |
| `stderr` | NUMERIC(10,6) | YES | Standard error |
| `sharpe_ratio` | NUMERIC(10,4) | YES | Sharpe ratio |

```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    backtest_run_id INTEGER REFERENCES backtest_runs(id),
    spec_hash VARCHAR(32) NOT NULL,
    formation_year INTEGER NOT NULL,
    horizon_years INTEGER NOT NULL,
    bucket VARCHAR(20) NOT NULL,
    mean_ret NUMERIC(10,6),
    t_stat NUMERIC(10,4),
    n INTEGER,
    stderr NUMERIC(10,6),
    sharpe_ratio NUMERIC(10,4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Research Tables

### quintile_assignments

Annual quintile assignments for each company.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `ticker` | VARCHAR(10) | NO | Company ticker |
| `formation_year` | INTEGER | NO | Formation year (June) |
| `factor_id` | VARCHAR(50) | NO | Factor used for sorting |
| `quintile` | INTEGER | NO | Quintile (1-5) |
| `factor_value` | NUMERIC(10,6) | YES | Actual factor value |
| `data_tier` | VARCHAR(10) | YES | Data tier used |

```sql
CREATE TABLE quintile_assignments (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    formation_year INTEGER NOT NULL,
    factor_id VARCHAR(50) NOT NULL,
    quintile INTEGER NOT NULL CHECK (quintile BETWEEN 1 AND 5),
    factor_value NUMERIC(10,6),
    data_tier VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, formation_year, factor_id)
);
```

---

### rolling_window_results

Rolling window analysis results.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `window_type` | VARCHAR(10) | NO | 5yr, 10yr, 20yr |
| `end_year` | INTEGER | NO | Window end year |
| `quintile` | INTEGER | YES | Quintile (null for HML) |
| `mean_return` | NUMERIC(10,6) | YES | Mean return |
| `t_stat` | NUMERIC(10,4) | YES | T-statistic |
| `p_value` | NUMERIC(10,6) | YES | P-value |
| `n_observations` | INTEGER | YES | Sample size |
| `data_tier` | VARCHAR(10) | YES | Data tier |

```sql
CREATE TABLE rolling_window_results (
    id SERIAL PRIMARY KEY,
    window_type VARCHAR(10) NOT NULL,
    end_year INTEGER NOT NULL,
    quintile INTEGER,
    mean_return NUMERIC(10,6),
    t_stat NUMERIC(10,4),
    p_value NUMERIC(10,6),
    n_observations INTEGER,
    data_tier VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### anova_results

ANOVA test results.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `analysis_type` | VARCHAR(50) | NO | Type of analysis |
| `window_type` | VARCHAR(10) | YES | Window type if applicable |
| `f_statistic` | NUMERIC(10,4) | YES | F-statistic |
| `p_value` | NUMERIC(10,6) | YES | P-value |
| `df_between` | INTEGER | YES | Degrees of freedom (between) |
| `df_within` | INTEGER | YES | Degrees of freedom (within) |

```sql
CREATE TABLE anova_results (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL,
    window_type VARCHAR(10),
    f_statistic NUMERIC(10,4),
    p_value NUMERIC(10,6),
    df_between INTEGER,
    df_within INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### publication_snapshots

Frozen research results for papers.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `snapshot_id` | VARCHAR(50) | NO | Unique snapshot ID |
| `git_commit` | VARCHAR(40) | YES | Git commit hash |
| `data_json` | JSONB | NO | Frozen results |
| `built_at` | TIMESTAMP | NO | Build timestamp |

```sql
CREATE TABLE publication_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_id VARCHAR(50) UNIQUE NOT NULL,
    git_commit VARCHAR(40),
    data_json JSONB NOT NULL,
    built_at TIMESTAMP DEFAULT NOW()
);
```

---

## Factor Tables

### factor_returns

Fama-French and custom factor returns.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `date` | DATE | NO | Return date |
| `factor` | VARCHAR(20) | NO | Factor name (MKT, SMB, HML, RD) |
| `return` | NUMERIC(10,6) | YES | Factor return |
| `source` | VARCHAR(50) | YES | Data source |

```sql
CREATE TABLE factor_returns (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    factor VARCHAR(20) NOT NULL,
    return NUMERIC(10,6),
    source VARCHAR(50),
    UNIQUE(date, factor)
);

CREATE INDEX idx_factor_returns_date ON factor_returns(date);
CREATE INDEX idx_factor_returns_factor ON factor_returns(factor);
```

---

## Virtual ETF Tables

### virtual_etf_specs

ETF specification definitions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `etf_name` | VARCHAR(50) | NO | ETF name |
| `factor_id` | VARCHAR(50) | NO | Sorting factor |
| `universe` | VARCHAR(50) | NO | Universe |
| `top_n` | INTEGER | NO | Number of holdings |
| `weighting` | VARCHAR(20) | NO | equal, market_cap |
| `rebalance_frequency` | VARCHAR(20) | NO | annual, quarterly |

```sql
CREATE TABLE virtual_etf_specs (
    id SERIAL PRIMARY KEY,
    etf_name VARCHAR(50) UNIQUE NOT NULL,
    factor_id VARCHAR(50) NOT NULL,
    universe VARCHAR(50) NOT NULL,
    top_n INTEGER NOT NULL,
    weighting VARCHAR(20) DEFAULT 'equal',
    rebalance_frequency VARCHAR(20) DEFAULT 'annual',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### virtual_etf_holdings

Current ETF holdings.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `etf_spec_id` | INTEGER | NO | FK to virtual_etf_specs |
| `as_of_date` | DATE | NO | Holdings date |
| `ticker` | VARCHAR(10) | NO | Stock ticker |
| `weight` | NUMERIC(10,6) | NO | Portfolio weight |
| `shares` | NUMERIC(18,4) | YES | Number of shares |

```sql
CREATE TABLE virtual_etf_holdings (
    id SERIAL PRIMARY KEY,
    etf_spec_id INTEGER REFERENCES virtual_etf_specs(id),
    as_of_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    weight NUMERIC(10,6) NOT NULL,
    shares NUMERIC(18,4),
    UNIQUE(etf_spec_id, as_of_date, ticker)
);
```

---

## Audit Table

### audits

Audit trail for data changes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `table_name` | VARCHAR(100) | NO | Affected table |
| `record_id` | VARCHAR(100) | NO | Affected record ID |
| `action` | VARCHAR(20) | NO | INSERT, UPDATE, DELETE |
| `old_data` | JSONB | YES | Previous values |
| `new_data` | JSONB | YES | New values |
| `user_id` | VARCHAR(100) | YES | User performing action |
| `timestamp` | TIMESTAMP | NO | Action timestamp |

```sql
CREATE TABLE audits (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audits_table ON audits(table_name);
CREATE INDEX idx_audits_timestamp ON audits(timestamp);
```

---

## Migrations

### Using Alembic

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show current version
alembic current
```

### Migration Files

Located in `migrations/`:
- `001_add_result_versioning.sql`
- `002_tier2_returns_and_runs.sql`
- `003_publication_snapshots.sql`

---

## Common Queries

### Get Latest R&D Intensity Rankings

```sql
SELECT 
    c.ticker,
    c.name,
    c.sector,
    fr.rd_intensity,
    NTILE(5) OVER (ORDER BY fr.rd_intensity) as quintile
FROM companies c
JOIN financials_ratios fr ON c.ticker = fr.ticker
WHERE fr.fiscal_year = (SELECT MAX(fiscal_year) FROM financials_ratios)
  AND fr.rd_intensity IS NOT NULL
ORDER BY fr.rd_intensity DESC;
```

### Get Quintile Performance

```sql
SELECT 
    qa.quintile,
    AVG(ar.annual_return) as mean_return,
    STDDEV(ar.annual_return) as std_return,
    COUNT(*) as n
FROM quintile_assignments qa
JOIN annual_returns ar ON qa.ticker = ar.ticker 
    AND qa.formation_year = ar.formation_year
GROUP BY qa.quintile
ORDER BY qa.quintile;
```

### Get Rolling Window Premium

```sql
SELECT 
    end_year,
    mean_return as hml_premium,
    t_stat
FROM rolling_window_results
WHERE window_type = '5yr'
  AND quintile IS NULL  -- HML spread
ORDER BY end_year;
```

---

*Last updated: December 2025*
