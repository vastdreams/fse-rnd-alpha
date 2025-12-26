# R&D Alpha Project Handoff Documentation

---

## 1. Product Overview

### What is R&D Alpha?

**R&D Alpha** is a quantitative research platform that investigates whether companies investing heavily in R&D (Research & Development) outperform those that don't. It's a sub-product of the **Finsoeasy** ecosystem, providing:

1. **Academic-grade research** proving the R&D premium exists
2. **Investable strategy** (R&D ETF) that captures this premium
3. **Interactive tools** for exploring the data

### The Core Thesis

> Companies that invest more in R&D (as a % of revenue) generate higher long-term stock returns.

This happens because:
- **Accounting quirk**: GAAP requires R&D to be expensed immediately (not capitalized), making R&D-heavy firms look less profitable on paper
- **Market underreaction**: Investors undervalue these "hidden assets"
- **Long-term payoff**: R&D investments take 3-5 years to show up in returns

### Key Research Findings

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Annual R&D Premium** | +7.55% | High-R&D stocks beat low-R&D by 7.55%/year |
| **t-Statistic** | 2.78 | Statistically significant (>2.0) |
| **p-Value** | 0.0107 | 99% confidence the effect is real |
| **Win Rate** | 71% | Premium was positive in 17 of 24 years |
| **Net Premium (after costs)** | +5.33% | What you actually keep after trading |
| **Sample Period** | 1995-2024 | 30 years of data |

### Who Uses This?

1. **Individual investors** - Implement the R&D ETF strategy
2. **Financial advisors** - Research-backed factor tilt for clients
3. **Academics** - Replicable methodology and frozen datasets
4. **Finsoeasy users** - Integrated research for the main platform

---

## 2. Product Features

### 2.1 Main Paper (`/papers/main`)
- Publication-ready academic paper
- 12 sections: Introduction → Conclusion
- All tables and figures rendered from frozen data
- PDF export with proper A4 formatting
- ~4000 lines of React code

### 2.2 Whitepaper Slide Deck (`/whitepaper`)
- 11 investor-focused slides
- "Why should I care?" hook on slide 1
- Implementation timeline and checklist
- PDF-ready A4 format

### 2.3 R&D ETF Tool (`/portfolio`)
- Live holdings based on current R&D rankings
- Backtest with transaction costs
- Sector allocation analysis
- Forecast vs actual performance
- Export to CSV

### 2.4 Research Dashboard (`/research`)
- Quintile return analysis
- Rolling premium visualization
- Factor spanning tests
- Statistical inference tables

### 2.5 Company Explorer (`/companies`)
- Individual company R&D profiles
- Historical R&D intensity charts
- Sector comparisons

---

## 3. Data Architecture

### Data Sources

| Source | What We Get | API/Method | Tier |
|--------|-------------|------------|------|
| **Financial Modeling Prep (FMP)** | Fundamentals (R&D, revenue), prices, S&P 500 list | REST API | Tier 1 |
| **Ken French Data Library** | Fama-French factors (MKT, SMB, HML, etc.) | CSV download | Tier 1 |
| **SEC EDGAR** | 10-K filings for validation | Public filings | Tier 1 |
| **CRSP/Compustat** | Premium academic data (optional) | WRDS | Tier 2 |

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FMP API       │────▶│   PostgreSQL    │────▶│   FastAPI       │
│   (fundamentals)│     │   (storage)     │     │   (backend)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│  Ken French     │────▶│   Factor        │──────────────┤
│  (factors)      │     │   Tables        │              │
└─────────────────┘     └─────────────────┘              │
                                                         ▼
                                               ┌─────────────────┐
                                               │   React         │
                                               │   Frontend      │
                                               └─────────────────┘
```

### Database Tables (Key)

| Table | Purpose |
|-------|---------|
| `companies` | Company metadata (ticker, name, sector) |
| `financials` | Annual fundamentals (R&D, revenue, etc.) |
| `prices` | Daily stock prices |
| `quintile_assignments` | Annual R&D quintile assignments |
| `factor_returns` | Fama-French factor data |
| `publication_snapshots` | Frozen research results |

### Publication Snapshot

The research paper uses a **frozen snapshot** to ensure reproducibility:
- Snapshot ID: Unique identifier for each computation run
- Git commit: Links to exact code version
- Built date: When the snapshot was created
- Served from: `/api/research/publication-snapshot`

---

## 4. AWS Infrastructure

### Current Setup (EC2 Only)

| Resource | Details |
|----------|---------|
| **EC2 Instance** | Ubuntu, hosts Docker stack |
| **Domain** | `research.finsoeasy.com` |
| **SSL** | Not yet configured (HTTP only) |
| **Database** | PostgreSQL in Docker (not RDS) |
| **Storage** | Local EBS volume |

### S3 Bucket (Optional, Not Currently Active)

The codebase supports S3 for data storage, but it's **not currently configured**:

```python
# In deploy/docker-compose.yml
S3_BUCKET: ${S3_BUCKET:-fse-rnd-alpha-data}
AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION: ${AWS_REGION:-us-east-1}
```

**To enable S3:**
1. Create bucket: `fse-rnd-alpha-data`
2. Create IAM user with S3 access
3. Add credentials to `deploy/.env`
4. Run `python deploy/setup_aws.py --upload`

### IAM Requirements (If Using S3)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::fse-rnd-alpha-data",
        "arn:aws:s3:::fse-rnd-alpha-data/*"
      ]
    }
  ]
}
```

---

## 5. Repository Information

| Property | Value |
|----------|-------|
| **GitHub Repo** | `https://github.com/vastdreams/fse-rnd-alpha.git` |
| **Main Branch** | `main` |
| **Local Path** | `/Users/abhisheksehgal/Desktop/fse-rnd-alpha` |

### Clone Command
```bash
git clone https://github.com/vastdreams/fse-rnd-alpha.git
cd fse-rnd-alpha
```

---

## AWS EC2 Credentials & Access

### Server Details
| Property | Value |
|----------|-------|
| **Domain** | `research.finsoeasy.com` |
| **EC2 User** | `ubuntu` |
| **SSH Key Path** | `~/.ssh/fse-rnd-alpha-key.pem` |
| **Deployment Path** | `/home/ubuntu/fse-rnd-alpha/` |
| **Frontend Dist** | `/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/` |

### SSH Access
```bash
ssh -i ~/.ssh/fse-rnd-alpha-key.pem ubuntu@research.finsoeasy.com
```

### Frontend-Only Deployment (Quick)
```bash
# Build locally
cd frontend && npm run build && cd ..

# Deploy to EC2
scp -i ~/.ssh/fse-rnd-alpha-key.pem -r frontend/dist/* ubuntu@research.finsoeasy.com:/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/
```

### Full Stack Restart
```bash
ssh -i ~/.ssh/fse-rnd-alpha-key.pem ubuntu@research.finsoeasy.com "cd /home/ubuntu/fse-rnd-alpha/deploy && docker compose restart"
```

---

## Project Structure

```
fse-rnd-alpha/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── services/          # Business logic
│   │   └── main.py            # Entry point
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/             # Main pages
│   │   │   ├── papers/
│   │   │   │   └── MainPaper.tsx    # Academic paper
│   │   │   ├── Whitepaper.tsx       # Slide deck
│   │   │   ├── Portfolio.tsx        # R&D ETF tool
│   │   │   └── Research.tsx         # Research overview
│   │   ├── components/        # Reusable components
│   │   ├── lib/api.ts         # API client
│   │   └── index.css          # Global styles + print CSS
│   ├── package.json
│   └── vite.config.ts
├── deploy/                     # Production deployment
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── frontend/dist/         # Mounted to nginx container
├── scripts/                    # Data pipeline scripts
├── data/                       # Local data files
└── papers/                     # Markdown methodology docs
```

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 15 (via asyncpg)
- **Cache:** Redis 7
- **Task Queue:** Celery
- **Data:** FMP API, Ken French factors

### Frontend
- **Framework:** React 19 + TypeScript
- **Build:** Vite 7
- **Styling:** Tailwind CSS 4
- **Charts:** Recharts
- **State:** TanStack Query
- **UI Components:** shadcn/ui (Radix)

### Infrastructure
- **Server:** AWS EC2 (Ubuntu)
- **Reverse Proxy:** Nginx (Alpine)
- **Containers:** Docker Compose

---

## Key Files Reference

### Frontend Pages
| File | Description |
|------|-------------|
| `frontend/src/pages/papers/MainPaper.tsx` | Full academic paper (~4000 lines) |
| `frontend/src/pages/Whitepaper.tsx` | 11-slide presentation deck |
| `frontend/src/pages/Portfolio.tsx` | R&D ETF interactive tool |
| `frontend/src/pages/Research.tsx` | Research overview page |

### Critical Components
| File | Description |
|------|-------------|
| `frontend/src/components/InfoTooltip.tsx` | Metric explanations dictionary |
| `frontend/src/components/SafeChart.tsx` | Recharts wrapper (prevents -1 dimension errors) |
| `frontend/src/components/RightTableOfContents.tsx` | Paper navigation |
| `frontend/src/index.css` | Global + print styles |

### Backend API Routes
| File | Description |
|------|-------------|
| `backend/app/api/routes/research.py` | Research endpoints |
| `backend/app/api/routes/portfolio.py` | Portfolio/ETF endpoints |
| `backend/app/api/routes/fmp.py` | FMP data proxy |

---

## Environment Variables

### Backend (.env in deploy/)
```env
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/rd_alpha

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys
FMP_API_KEY=your_fmp_api_key

# AWS (for S3 data storage)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_BUCKET=fse-rnd-alpha-data

# Security
SECRET_KEY=your_secret_key
DEBUG=false
```

---

## Common Operations

### Build Frontend
```bash
cd frontend
npm install
npm run build
```

### Run Backend Locally
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run Frontend Dev Server
```bash
cd frontend
npm run dev
# Opens at http://localhost:5173
```

### Check Docker Services on EC2
```bash
ssh -i ~/.ssh/fse-rnd-alpha-key.pem ubuntu@research.finsoeasy.com \
  "cd /home/ubuntu/fse-rnd-alpha/deploy && docker compose ps"
```

### View Backend Logs
```bash
ssh -i ~/.ssh/fse-rnd-alpha-key.pem ubuntu@research.finsoeasy.com \
  "cd /home/ubuntu/fse-rnd-alpha/deploy && docker compose logs -f backend"
```

---

## API Endpoints (Key)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research/publication-snapshot` | GET | Frozen research data for papers |
| `/api/research/cohort-summary` | GET | Sample statistics |
| `/api/research/annual-hml-premium` | GET | Annual factor premiums |
| `/api/portfolio/etf/holdings` | GET | Current R&D ETF holdings |
| `/api/portfolio/backtest` | GET | Strategy backtesting |
| `/api/fmp/companies` | GET | Company fundamentals |
| `/health` | GET | Health check |

---

## Print/PDF Export

The Main Paper has a "Download PDF" button that uses browser print-to-PDF:
- Print styles are in `frontend/src/index.css` under `@media print`
- The `printing-paper` class on body activates print mode
- Grid layouts are preserved (not collapsed to single column)
- No forced page breaks between sections

---

## Recent Changes (Dec 2025)

1. **Whitepaper redesign** - Investor-first content, filled slides, no blank space
2. **Section 9 expansion** - Implementation timeline, practical checklist, FAQs
3. **PDF print fix** - Removed page breaks, preserved grid layouts
4. **Em-dash removal** - Replaced AI-style "—" with natural punctuation
5. **Reader Guide redesign** - 3-column layout with deep-dive chips
6. **Right nav toggle fix** - Collapse arrow no longer clipped

---

## Integration as Subrepo

To add this as a subrepo in finsoeasy main project:

```bash
# From finsoeasy root
git submodule add https://github.com/vastdreams/fse-rnd-alpha.git research
git submodule update --init --recursive

# Or as a subtree
git subtree add --prefix=research https://github.com/vastdreams/fse-rnd-alpha.git main --squash
```

---

## Contacts & Resources

- **GitHub:** https://github.com/vastdreams/fse-rnd-alpha
- **Live Site:** http://research.finsoeasy.com
- **API Docs:** http://research.finsoeasy.com/docs

---

---

## 12. Research Methodology Details

### Quintile Sorting Process

Each June:
1. Get all S&P 500 constituents (point-in-time, ~500 companies)
2. Exclude firms with zero R&D (banks, utilities, ~100 firms)
3. Calculate R&D Intensity = R&D Expense / Revenue (from prior fiscal year)
4. Sort firms into 5 quintiles (Q1 = lowest, Q5 = highest)
5. Track returns July → June (Fama-French convention)

### Why July-June?

Companies have 90 days after fiscal year end to file 10-K. Most have December fiscal year end. By July, all 10-Ks are public, avoiding look-ahead bias.

```
Fiscal Year End: Dec 31, 2023
10-K Filed By: Mar 31, 2024
Portfolio Formation: June 30, 2024
Holding Period: July 1, 2024 → June 30, 2025
```

### Transaction Cost Model

Uses Novy-Marx & Velikov (2016) methodology:
- **Bid-ask spread**: ~10 bps for S&P 500 stocks
- **Market impact**: Minimal for equal-weight small positions
- **Round-trip cost**: ~20 bps per 100% turnover
- **Average turnover**: ~15% annually

---

## 13. Finsoeasy Integration

### Relationship to Main Platform

R&D Alpha is a **research sub-product** of finsoeasy.com:
- Separate codebase for research independence
- Shares design language (Tailwind, shadcn/ui)
- Links back to main finsoeasy site
- Uses `research.finsoeasy.com` subdomain

### Future Integration Points

1. **User accounts**: Share authentication with main finsoeasy
2. **Portfolio integration**: Add R&D tilt to user portfolios
3. **Alerts**: Notify users of annual rebalance
4. **Data API**: Expose research data to main platform

---

## 14. Development Guidelines

### Code Conventions

- **File headers**: Every file has PATH, PURPOSE, and DEPENDENCIES comments
- **No hardcoded values**: All research numbers come from API
- **TypeScript**: Strict mode, no `any` where avoidable
- **Tailwind**: Use `cn()` utility for conditional classes
- **Charts**: Always wrap Recharts in `SafeChart` component

### Testing Checklist

Before deploying:
1. [ ] `npm run build` succeeds without errors
2. [ ] Main Paper renders all sections
3. [ ] Whitepaper slides 1-11 all visible
4. [ ] PDF export produces non-blank pages
5. [ ] API endpoints return data (`/api/research/publication-snapshot`)

### Known Issues

| Issue | Workaround |
|-------|------------|
| Recharts `-1` dimension error | Use `SafeChart` wrapper |
| Print blank pages | CSS removes page-break rules |
| Right nav cutoff | Toggle positioned outside overflow |

---

## 15. Notes for AI Agents

### Critical Rules

1. **SSH Key Required:** The key at `~/.ssh/fse-rnd-alpha-key.pem` is needed for EC2 access
2. **Frontend Deploy Path:** Always deploy to `/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/` (NOT `frontend/dist/`)
3. **Print Styles:** If modifying, test with browser print preview before deploying
4. **Recharts:** Use `SafeChart` wrapper to prevent dimension errors
5. **Build Command:** `npm --prefix frontend run build` from project root

### File Locations (Most Edited)

| File | What It Does | Lines |
|------|--------------|-------|
| `frontend/src/pages/papers/MainPaper.tsx` | Academic paper | ~4000 |
| `frontend/src/pages/Whitepaper.tsx` | Slide deck | ~2000 |
| `frontend/src/index.css` | Global + print styles | ~750 |
| `frontend/src/components/InfoTooltip.tsx` | Metric explanations | ~370 |
| `backend/app/api/routes/research.py` | Research API | ~500 |

### Deployment Checklist

```bash
# 1. Build
npm --prefix frontend run build

# 2. Verify build
ls frontend/dist/  # Should have index.html, assets/

# 3. Deploy
scp -i ~/.ssh/fse-rnd-alpha-key.pem -r frontend/dist/* \
  ubuntu@research.finsoeasy.com:/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/

# 4. Verify live site
curl -I http://research.finsoeasy.com  # Should return 200
```

### Emergency Rollback

```bash
# SSH to server
ssh -i ~/.ssh/fse-rnd-alpha-key.pem ubuntu@research.finsoeasy.com

# Check git log for last good commit
cd /home/ubuntu/fse-rnd-alpha
git log --oneline -5

# Checkout previous version
git checkout <commit-hash>

# Rebuild and restart
cd deploy && docker compose restart frontend
```

---

## 16. Contact & Resources

| Resource | URL |
|----------|-----|
| **Live Site** | http://research.finsoeasy.com |
| **GitHub Repo** | https://github.com/vastdreams/fse-rnd-alpha |
| **API Docs** | http://research.finsoeasy.com/docs |
| **Main Finsoeasy** | https://finsoeasy.com |

---

*Last updated: December 2025*

