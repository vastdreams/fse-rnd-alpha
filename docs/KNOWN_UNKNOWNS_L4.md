# Known unknowns — L4 catalyst UNKNOWN & missing filings

**Rule:** do not invent catalysts, NRR, or loosen L0 (≥25% drawdown). UNKNOWN is a
valid research outcome.

## L4 UNKNOWN (12 names) — fail-closed, not missing tape

These clear the panel but stay L4 UNKNOWN after SEC/AV/Sharadar enrichment:

| Ticker | Why UNKNOWN |
|--------|-------------|
| ATEN | L0: no ≥25% drawdown window despite bars + anchors |
| CSGS | L0: no ≥25% drawdown |
| DBD | L0: no ≥25% drawdown |
| IMXI | L0: no ≥25% drawdown |
| LSAK | L0: no ≥25% drawdown |
| MITK | L0: no ≥25% drawdown |
| NATL | L0: no ≥25% drawdown |
| NTCT | L0: no ≥25% drawdown |
| ONTF | L0: no ≥25% drawdown |
| PLUS | L0: no ≥25% drawdown |
| YOU | L0: no ≥25% drawdown |
| CYBR | L0 known, but no anchors in peak−30d…trough+45d window |

UI copy for these reasons lives on Stance tab (UNKNOWN) and Universe empty-BUY blurb.

## Missing / thin filings (~10)

Filings not in `data/filings_cache/` (or empty) block verbatim NRR/concentration
extract and DeepSeek `filing_map` locators. Treat as completeness Incomplete —
never estimate. Sync via existing filings fetch; then:

```bash
./scripts/run_filing_map_batch.sh 40
backend/.venv/bin/python scripts/backfill_ai_text_stance_from_transcripts.py
# then rebuild vectors
backend/.venv/bin/python scripts/build_universe.py
```

## Phase E ops

- `filing_map`: quote-substring locators only (`deepseek_audit.py filing_map`).
- `ai_text_stance`: measured from `av_transcripts_raw` via `text_exposure` — blank
  when no AI-salient sentences.
- **No gate threshold changes.**
