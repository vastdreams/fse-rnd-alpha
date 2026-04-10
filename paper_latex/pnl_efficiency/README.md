# P&L Efficiency Alpha — LaTeX Paper

## Structure

```
pnl_efficiency/
├── main.tex          # Full manuscript source
├── references.bib    # Curated BibTeX bibliography (25 entries)
├── README.md         # This file
├── data/
│   └── metrics.tex   # Auto-generated snapshot macros (pending)
├── tables/
│   └── *.tex         # Auto-generated LaTeX tables (pending)
└── scripts/
    └── build_assets.py  # Generates data/*.csv, tables/*.tex, data/metrics.tex (pending)
```

## Build

```bash
# Once metrics.tex exists:
cd paper_latex/pnl_efficiency
tectonic main.tex        # Or: pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Status

- **Abstract**: Drafted
- **Introduction**: Drafted
- **Literature Review**: Drafted (4 subsections)
- **Hypotheses**: 4 hypotheses stated
- **Data**: Drafted
- **Variable Construction**: Drafted (equations, z-scoring, composite)
- **Empirical Design**: Drafted (quintile sorts, factor spanning, Fama-MacBeth, orthogonality)
- **Core Results**: PENDING (requires frozen snapshot)
- **Robustness**: PENDING (8 tests planned)
- **Portfolio Implications**: PENDING
- **Limitations**: Drafted (7 items)
- **Conclusion**: Structure in place
- **Appendices**: Variable definitions, sector distribution (pending), snapshot provenance (pending)
