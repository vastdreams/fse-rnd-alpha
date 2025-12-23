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
fse-rnd-alpha/
├── backend/           # FastAPI backend with research computations
│   ├── app/
│   │   ├── api/       # REST API endpoints
│   │   ├── services/  # Core research logic
│   │   └── db/        # Database models
│   └── requirements.txt
├── frontend/          # React + TypeScript dashboard
│   ├── src/
│   │   ├── pages/     # Main Paper, ETF simulator, Analysis
│   │   └── components/
│   └── package.json
├── deploy/            # Docker Compose production deployment
├── scripts/           # Data ingestion and analysis scripts
├── docs/              # Additional documentation
└── papers/            # Research paper drafts
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
git clone https://github.com/vastdreams/fse-rnd-alpha.git
cd fse-rnd-alpha

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
| CRSP/Compustat | Premium data (optional) | Tier 2 |

### Statistical Framework

1. **Quintile Sorting**: Firms ranked by R&D/Revenue annually
2. **HML-RD Factor**: Q5 (High R&D) minus Q1 (Low R&D) returns
3. **Inference**: Newey-West HAC standard errors (lag=1)
4. **Robustness**: Factor spanning, size controls, delisting sensitivity

### Key References

- Chan, Lakonishok & Sougiannis (2001) - R&D and stock returns
- Fama & French (1993, 2015) - Factor models
- Shumway (1997) - Delisting bias correction

---

## 📄 Documentation

- [Data Availability](DATA_AVAILABILITY.md) - Data sources and access
- [Data Provenance](DATA_PROVENANCE.md) - Collection methodology
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production setup

---

## 🔬 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/research/publication-snapshot` | Frozen research results |
| `GET /api/research/rolling-windows` | Time-varying premium |
| `GET /api/portfolio/etf-holdings` | Current R&D ETF holdings |
| `GET /api/research/factor-spanning` | Factor regression results |

Full API documentation: `/docs` (Swagger UI)

---

## 📜 Citation

If you use this research, please cite:

```bibtex
@software{rd_alpha_2024,
  author = {Sehgal, Abhishek},
  title = {R&D Alpha: Innovation-Driven Investment Research},
  year = {2024},
  url = {https://github.com/vastdreams/fse-rnd-alpha}
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
