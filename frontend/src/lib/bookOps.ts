/**
 * PATH: frontend/src/lib/bookOps.ts
 * PURPOSE: Server-book merge helpers (equal-weight after append).
 */
import type { BookHolding, SavedBookRecord } from "@/lib/api/universe"

export const MAX_POSITION_WEIGHT_PCT = 15

/** Apply server construction-proxy weights onto existing holdings (0 for unknowns). */
export function applyProxyWeights(
  existing: BookHolding[],
  proxyHoldings: Array<{ ticker: string; weight_pct: number }>
): BookHolding[] {
  const now = new Date().toISOString().slice(0, 19)
  const byProxy = new Map(
    proxyHoldings.map((h) => [h.ticker.toUpperCase(), h.weight_pct] as const)
  )
  const map = new Map<string, BookHolding>()
  for (const holding of existing) {
    const ticker = holding.ticker.toUpperCase()
    map.set(ticker, {
      ...holding,
      ticker,
      weight_pct: byProxy.has(ticker) ? byProxy.get(ticker)! : holding.weight_pct,
    })
  }
  for (const [ticker, weight_pct] of byProxy) {
    if (!map.has(ticker)) {
      map.set(ticker, { ticker, weight_pct, added_at: now })
    }
  }
  return Array.from(map.values())
}

export function primaryBookHoldingsCount(books: SavedBookRecord[]): number {
  if (!books.length) return 0
  return (books.find((book) => book.is_primary) || books[0]).holdings?.length ?? 0
}

export function equalWeightHoldings(tickers: string[], existing: BookHolding[] = []): BookHolding[] {
  const now = new Date().toISOString().slice(0, 19)
  const map = new Map<string, BookHolding>()
  for (const h of existing) map.set(h.ticker.toUpperCase(), { ...h })
  for (const raw of tickers) {
    const t = raw.toUpperCase()
    if (!map.has(t)) {
      map.set(t, { ticker: t, weight_pct: 0, added_at: now })
    }
  }
  const list = Array.from(map.values())
  if (list.length === 0) return []
  // A small Book is a valid draft. Cap explicit equal-weight rebalances at
  // the server-enforced per-name limit rather than producing an impossible
  // 100% allocation that the user must manually undo.
  const w = Math.floor((Math.min(MAX_POSITION_WEIGHT_PCT, 100 / list.length)) * 100) / 100
  return list.map((h) => ({ ...h, weight_pct: w }))
}

/**
 * Append research candidates without changing a user's intentional allocation.
 * New names start at 0% until the Book owner explicitly allocates/rebalances.
 */
export function appendUnallocatedHoldings(
  tickers: string[],
  existing: BookHolding[] = []
): BookHolding[] {
  const now = new Date().toISOString().slice(0, 19)
  const map = new Map<string, BookHolding>()
  for (const holding of existing) {
    map.set(holding.ticker.toUpperCase(), { ...holding, ticker: holding.ticker.toUpperCase() })
  }
  for (const raw of tickers) {
    const ticker = raw.trim().toUpperCase()
    if (ticker && !map.has(ticker)) {
      map.set(ticker, { ticker, weight_pct: 0, added_at: now })
    }
  }
  return Array.from(map.values())
}

export type SoftAddWarning = {
  ticker: string
  reasons: string[]
}

export function softAddWarnings(
  tickers: string[],
  byTicker: Map<
    string,
    {
      completeness_grade: string
      retention?: number | null
      mos_live?: number | null
      freshness_ok?: boolean
      kill_active?: boolean | null
    }
  >
): SoftAddWarning[] {
  const out: SoftAddWarning[] = []
  for (const raw of tickers) {
    const t = raw.toUpperCase()
    const r = byTicker.get(t)
    const reasons: string[] = []
    if (!r) {
      reasons.push("not in current ranked screen")
    } else {
      if (r.completeness_grade !== "A") reasons.push(`completeness ${r.completeness_grade} (prefer A)`)
      if (r.retention == null) reasons.push("NRR/retention undisclosed")
      if (r.mos_live != null && r.mos_live > 1) reasons.push(`MoS ${(r.mos_live * 100).toFixed(0)}% — verify DCF`)
      if (r.freshness_ok !== true) reasons.push("research freshness is stale or unknown")
      if (r.kill_active !== false) reasons.push("kill state is active or unknown")
    }
    if (reasons.length) out.push({ ticker: t, reasons })
  }
  return out
}
