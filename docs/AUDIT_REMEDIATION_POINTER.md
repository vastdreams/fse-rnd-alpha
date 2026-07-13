# Audit remediation plan — pointer

**Source of truth (canvas):**  
`~/.cursor/projects/Users-abhisheksehgal-Desktop-duraloop-paper/canvases/audit-remediation-roi-plan.canvas.tsx`

**Related audits (read-only context):**  
- `canvases/pick10-roi-gaps.canvas.tsx` — ROI-ranked gaps (data + UX + code)  
- `canvases/research-platform-strict-audit.canvas.tsx` — coverage scorecard  

## Rules of engagement

1. Do **not** duplicate the phased plan here — open the canvas.  
2. Job = enable **pick 10 stocks** end-to-end (select → book → diligence).  
3. Waterfall: Sprint 0 → A (book loop) → B (sort/filter) → C (trust) → D (kill ack) → E (coverage).  
4. **Never** loosen L0 25% drawdown or invent NRR/catalysts.  
5. Schedule slip: cut **Phase E only**.  
6. Product code: `/Users/abhisheksehgal/fse-rnd-alpha-work`.  

## Book badge contract (Sprint 0)

- Shell “My Book” badge count = **primary server book** holdings length via `listBooks()` / `useServerBookCount`.
- Legacy `usePortfolioBucket` localStorage is **not** the badge source (legacy routes only).
- `VITE_UNIVERSE_BOOK_SELECT` defaults **true**; set `false` to hide Universe checkboxes / Add bar.

## Known unknowns (Phase E)

See `docs/KNOWN_UNKNOWNS_L4.md` (12 L4 UNKNOWN reasons + filing_map / stance backfill commands).

## Sell ceiling

See `docs/SELL_CEILING.md` — auto-sell from fair-value band × hold horizon (`sellCeiling.ts`).

## If you are an agent

- Update the canvas **Execution state** first every session.  
- Next work unit is whatever the canvas says under `executionState.next`.  
- If the canvas path is missing, **stop and ask** — do not invent a parallel plan.
