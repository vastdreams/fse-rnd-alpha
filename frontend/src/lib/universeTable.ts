/**
 * PATH: frontend/src/lib/universeTable.ts
 * PURPOSE: Typed sort keys + pure helpers for Universe table (pick-10 remediation).
 */

export type SortKey =
  | "ticker"
  | "score"
  | "mos_live"
  | "vs_median_pct"
  | "retention"
  | "rev_cagr"
  | "completeness_grade"
  | "kill_active"
  | "stance"
  | "price_live"
  | "fcfm_sbc"
  | "sell_ceil"
  | "upside_to_ceil"

export type SortDir = "asc" | "desc"

export type SortableRow = {
  ticker: string
  score: number
  mos_live?: number | null
  vs_median_pct?: number | null
  retention?: number | null
  rev_cagr?: number | null
  completeness_grade: string
  kill_active?: boolean | null
  price_live?: number | null
  fcfm_sbc?: number | null
  stance?: string | null
  sell_ceil?: number | null
  upside_to_ceil?: number | null
}

const GRADE_RANK: Record<string, number> = { A: 4, B: 3, C: 2, Incomplete: 1 }

function cmpNullLast(a: number | null | undefined, b: number | null | undefined, dir: SortDir): number {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  return dir === "asc" ? a - b : b - a
}

export function sortRows<T extends SortableRow>(rows: T[], key: SortKey, dir: SortDir): T[] {
  const list = [...rows]
  list.sort((a, b) => {
    switch (key) {
      case "ticker": {
        const c = a.ticker.localeCompare(b.ticker)
        return dir === "asc" ? c : -c
      }
      case "score":
        return dir === "asc" ? a.score - b.score : b.score - a.score
      case "mos_live":
        return cmpNullLast(a.mos_live, b.mos_live, dir)
      case "vs_median_pct":
        return cmpNullLast(a.vs_median_pct, b.vs_median_pct, dir)
      case "retention":
        return cmpNullLast(a.retention, b.retention, dir)
      case "rev_cagr":
        return cmpNullLast(a.rev_cagr, b.rev_cagr, dir)
      case "price_live":
        return cmpNullLast(a.price_live, b.price_live, dir)
      case "fcfm_sbc":
        return cmpNullLast(a.fcfm_sbc, b.fcfm_sbc, dir)
      case "sell_ceil":
        return cmpNullLast(a.sell_ceil, b.sell_ceil, dir)
      case "upside_to_ceil":
        return cmpNullLast(a.upside_to_ceil, b.upside_to_ceil, dir)
      case "completeness_grade": {
        const ga = GRADE_RANK[a.completeness_grade] ?? 0
        const gb = GRADE_RANK[b.completeness_grade] ?? 0
        return dir === "asc" ? ga - gb : gb - ga
      }
      case "kill_active": {
        const ka = a.kill_active === true ? 1 : a.kill_active === false ? 0 : -1
        const kb = b.kill_active === true ? 1 : b.kill_active === false ? 0 : -1
        return dir === "asc" ? ka - kb : kb - ka
      }
      case "stance": {
        const c = (a.stance || "").localeCompare(b.stance || "")
        return dir === "asc" ? c : -c
      }
      default:
        return 0
    }
  })
  return list
}

export function toggleSort(
  prevKey: SortKey | null,
  prevDir: SortDir,
  nextKey: SortKey
): { key: SortKey; dir: SortDir } {
  if (prevKey === nextKey) {
    return { key: nextKey, dir: prevDir === "asc" ? "desc" : "asc" }
  }
  return { key: nextKey, dir: "desc" }
}

export function rowsToCsv(rows: SortableRow[], columns: { key: keyof SortableRow | "ticker"; header: string }[]): string {
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const header = columns.map((c) => c.header).join(",")
  const body = rows
    .map((r) => columns.map((c) => esc(r[c.key as keyof SortableRow])).join(","))
    .join("\n")
  return `${header}\n${body}\n`
}

/** Feature flag — default on so pick-10 select ships; set VITE_UNIVERSE_BOOK_SELECT=false to roll back. */
export function universeBookSelectEnabled(): boolean {
  const v = import.meta.env.VITE_UNIVERSE_BOOK_SELECT
  if (v === undefined || v === "") return true
  return v !== "0" && v !== "false" && v !== "False"
}
