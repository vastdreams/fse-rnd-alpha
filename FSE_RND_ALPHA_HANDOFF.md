# R&D Alpha Project Handoff Documentation

## Project Overview

**R&D Alpha** is a research platform analyzing the relationship between R&D investment intensity and long-term stock returns. It provides:
- Academic research paper (Main Paper) with publication-ready methodology
- Interactive whitepaper slide deck (11 slides)
- R&D ETF strategy tool with live holdings and backtesting
- Company-level R&D factor analysis

**Live Site:** `http://research.finsoeasy.com`

---

## Repository Information

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

## Notes for AI Agents

1. **SSH Key Required:** The key at `~/.ssh/fse-rnd-alpha-key.pem` is needed for EC2 access
2. **Frontend Deploy Path:** Always deploy to `/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/` (not `frontend/dist/`)
3. **Print Styles:** If modifying, test with browser print preview before deploying
4. **Recharts:** Use `SafeChart` wrapper to prevent dimension errors
5. **Build Command:** `npm --prefix frontend run build` from project root

