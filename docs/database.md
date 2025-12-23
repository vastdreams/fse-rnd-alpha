# Database Setup

## PostgreSQL

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

### Connection

Set in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rd_alpha
```

## Schema

Key tables:
- `sp500_company` - Company metadata
- `fmp_income_statement` - Financial statements
- `fmp_annual_return` - Stock returns
- `rolling_window_results` - Quintile analysis results
- `anova_results` - Statistical test results
