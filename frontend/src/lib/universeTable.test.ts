/**
 * PATH: frontend/src/lib/universeTable.test.ts
 */
import { describe, expect, it } from "vitest"
import fixture from "@/fixtures/buy_cohort_sample.json"
import {
  appendUnallocatedHoldings,
  equalWeightHoldings,
  primaryBookHoldingsCount,
  softAddWarnings,
} from "@/lib/bookOps"
import { rowsToCsv, sortRows, toggleSort, type SortableRow } from "@/lib/universeTable"

describe("sortRows", () => {
  const rows = fixture as SortableRow[]

  it("sorts MoS desc with nulls last", () => {
    const sorted = sortRows(rows, "mos_live", "desc")
    expect(sorted.map((r) => r.ticker)).toEqual(["KSPI", "MNDY", "SPSC"])
  })

  it("sorts score asc", () => {
    const sorted = sortRows(rows, "score", "asc")
    expect(sorted[0].ticker).toBe("KSPI")
  })

  it("toggleSort flips dir on same key", () => {
    expect(toggleSort("score", "desc", "score")).toEqual({ key: "score", dir: "asc" })
    expect(toggleSort("score", "desc", "mos_live")).toEqual({ key: "mos_live", dir: "desc" })
  })

  it("csv includes headers", () => {
    const csv = rowsToCsv(rows, [
      { key: "ticker", header: "Ticker" },
      { key: "score", header: "Score" },
    ])
    expect(csv.startsWith("Ticker,Score\n")).toBe(true)
    expect(csv).toContain("MNDY")
  })
})

describe("bookOps", () => {
  it("caps an explicit small-book rebalance at the position limit", () => {
    const h = equalWeightHoldings(["AAA", "BBB"], [{ ticker: "AAA", weight_pct: 100, added_at: "2026-01-01" }])
    expect(h).toHaveLength(2)
    expect(h.every((x) => x.weight_pct === 15)).toBe(true)
  })

  it("appends research candidates without silently reallocating a book", () => {
    const existing = [{ ticker: "AAA", weight_pct: 60, added_at: "2026-01-01" }]
    const h = appendUnallocatedHoldings(["AAA", "BBB", "CCC"], existing)

    expect(h).toEqual([
      { ticker: "AAA", weight_pct: 60, added_at: "2026-01-01" },
      expect.objectContaining({ ticker: "BBB", weight_pct: 0 }),
      expect.objectContaining({ ticker: "CCC", weight_pct: 0 }),
    ])
  })

  it("soft warnings for null NRR and extreme MoS", () => {
    const map = new Map(
      (fixture as SortableRow[]).map((r) => [
        r.ticker,
        {
          completeness_grade: r.completeness_grade,
          retention: r.retention,
          mos_live: r.mos_live,
          freshness_ok: true,
          kill_active: false,
        },
      ])
    )
    const w = softAddWarnings(["SPSC", "KSPI", "MNDY"], map)
    expect(w.find((x) => x.ticker === "SPSC")?.reasons.some((r) => r.includes("NRR"))).toBe(true)
    expect(w.find((x) => x.ticker === "KSPI")?.reasons.some((r) => r.includes("MoS"))).toBe(true)
    expect(w.find((x) => x.ticker === "MNDY")).toBeUndefined()
  })

  it("uses the explicitly marked primary book for the shell badge", () => {
    const books = [
      { is_primary: false, holdings: [{ ticker: "OLD" }] },
      { is_primary: true, holdings: [{ ticker: "NEW1" }, { ticker: "NEW2" }] },
    ] as never[]

    expect(primaryBookHoldingsCount(books)).toBe(2)
  })
})
