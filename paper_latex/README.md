## R&D Alpha — Submission-Ready LaTeX Paper (Print/PDF)

This folder contains a **publication/submission-ready LaTeX manuscript** generated from the **frozen publication snapshot** used by `research.finsoeasy.com`.

### Why this exists
- **Browser print is brittle** (pagination, margins, font metrics).
- A canonical PDF for SSRN/arXiv/journal submission should be produced from **typeset source** (LaTeX).
- **No manual copy/paste of numbers**: all tables/figures are generated from a pinned snapshot to prevent drift.

### What’s inside
- `main.tex`: the manuscript
- `references.bib`: BibTeX references (all citations are deliberate and checked)
- `data/publication_snapshot.json`: pinned results used by the website “Main Paper”
- `scripts/build_assets.py`: generates LaTeX-ready assets from the snapshot:
  - `data/metrics.tex` (macros used in prose)
  - `data/*.csv` (inputs for vector plots via `pgfplots`)
  - `tables/*.tex` (tables included into the manuscript)

### Workflow (local)
1. Refresh snapshot (optional): replace `data/publication_snapshot.json` with the latest frozen snapshot.
2. Generate assets:

```bash
python3 scripts/build_assets.py
```

3. Compile PDF (pick one):
- **Overleaf**: upload the entire `paper_latex/` folder and set `main.tex` as the root document.
- **Local TeX** (if installed):

```bash
latexmk -pdf main.tex
```

### Notes on graphs (you won’t lose them)
All figures are rendered with **`pgfplots`** from the CSV files under `data/`.
This produces **vector** plots (crisp at any zoom level) and avoids screenshots.


