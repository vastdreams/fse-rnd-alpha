# Labor Efficiency Alpha — LaTeX Paper

## Structure

```
labor_efficiency/
├── main.tex          # Full manuscript source (empirical sections GATED)
├── references.bib    # Curated BibTeX bibliography (26 entries)
├── README.md         # This file
├── data/
│   └── metrics.tex   # Auto-generated snapshot macros (pending data pipeline)
├── tables/
│   └── *.tex         # Auto-generated LaTeX tables (pending data pipeline)
└── scripts/
    └── build_assets.py  # Will generate assets once data pipeline is operational
```

## Status

**Paper sections completed (not gated on data):**
- Abstract (with readiness gate notice)
- Introduction
- Literature review (4 substantive subsections)
- Hypotheses (5 hypotheses)
- Data sources
- Extraction methodology (XBRL pipeline, NLP fallback, QA)
- Variable definitions (RPE, RPP, composite, combined PNL+Labor signal)
- Empirical design
- Measurement error analysis
- Data engineering workstream plan
- Expected robustness challenges
- Limitations (7 items)
- Conclusion
- Appendices (variable defs, XBRL tags, Gantt pending)

**Paper sections gated on labor-data pipeline:**
- Core results (Tables 1–5, Figures 1–2)
- Robustness tests (7 tests planned)
- Portfolio implications

## Data Pipeline Prerequisite

Empirical sections cannot proceed until:
1. XBRL ingestion pipeline is built
2. Employee count panel achieves ≥70% coverage per formation year
3. Payroll panel achieves ≥50% coverage per formation year
4. QA and coverage diagnostics pass
