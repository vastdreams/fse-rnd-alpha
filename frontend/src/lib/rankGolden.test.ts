import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import { formatPercent4, formatUsdCompact, formatUsd4, formatNumber4 } from "@/lib/formatMetrics"
import { auditRankRows, fairBandZone, formatRankViolations, mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"

const here = dirname(fileURLToPath(import.meta.url))
const fixturePath = join(here, "../fixtures/rank-golden.json")
const sidecarPath = join(here, "../fixtures/rank-golden.json.sha256")
const fixtureBytes = readFileSync(fixturePath)
const golden = JSON.parse(fixtureBytes.toString("utf8")) as {
  meta: {
    universe_version: string
    recipe_id: string
    captured_at: string
    source: string
  }
  rows: Array<Record<string, unknown> & { ticker: string; edge_tags?: string[] }>
}

describe("rank-golden fixture seal (S2)", () => {
  it("pins universe + recipe and has required edge coverage", () => {
    expect(golden.meta.universe_version).toBe("univ_2026-07-13_f0c9acf6f41f")
    expect(golden.meta.recipe_id).toBe("R3")
    expect(golden.rows.length).toBeGreaterThanOrEqual(12)

    const tags = new Set(golden.rows.flatMap((r) => r.edge_tags ?? []))
    for (const required of [
      "below_band",
      "inside_band",
      "above_band",
      "mos_eq_vs",
      "mos_ne_vs",
      "retention_null",
      "retention_disclosed",
      "grade_c",
    ]) {
      expect(tags.has(required), `missing edge tag ${required}`).toBe(true)
    }
  })

  it("sidecar sha256 matches exact committed fixture bytes", () => {
    const sidecar = readFileSync(sidecarPath, "utf8").trim().split(/\s+/)[0]
    const actual = createHash("sha256").update(fixtureBytes).digest("hex")
    expect(actual).toBe(sidecar)
  })

  it("every golden row passes first-principles audit", () => {
    const violations = auditRankRows(golden.rows)
    expect(formatRankViolations(violations)).toBe("ok")
    expect(violations).toEqual([])
  })

  it("edge tags match fair-band zones and MoS visibility", () => {
    for (const row of golden.rows) {
      const zone = fairBandZone(
        row.price_live as number | null,
        row.fair_px_lo as number | null,
        row.fair_px_hi as number | null
      )
      const tags = new Set(row.edge_tags ?? [])
      if (tags.has("below_band")) expect(zone).toBe("below")
      if (tags.has("inside_band")) expect(zone).toBe("inside")
      if (tags.has("above_band")) expect(zone).toBe("above")
      if (tags.has("mos_eq_vs")) {
        expect(mosDiffersFromLiveGap(row.mos_live as number, row.vs_median_pct as number)).toBe(false)
      }
      if (tags.has("mos_ne_vs")) {
        expect(mosDiffersFromLiveGap(row.mos_live as number, row.vs_median_pct as number)).toBe(true)
      }
    }
  })

  it("formatter golden strings for KSPI, APP, GRND", () => {
    const expected: Record<string, { price: string; revenue: string; vs: string; score: string }> = {
      KSPI: { price: "$89.67", revenue: "$9.11B", vs: "+178.6%", score: "9.877" },
      APP: { price: "$507", revenue: "$6.16B", vs: "-84.42%", score: "8.853" },
      GRND: { price: "$15.69", revenue: "$475.9M", vs: "+70.07%", score: "8.628" },
    }
    for (const [ticker, want] of Object.entries(expected)) {
      const row = golden.rows.find((r) => r.ticker === ticker)
      expect(row, ticker).toBeTruthy()
      expect(formatUsd4(row!.price_live as number)).toBe(want.price)
      expect(formatUsdCompact(row!.revenue_usd as number)).toBe(want.revenue)
      expect(formatPercent4(row!.vs_median_pct as number, true)).toBe(want.vs)
      expect(formatNumber4(row!.score as number)).toBe(want.score)
    }
  })
})
