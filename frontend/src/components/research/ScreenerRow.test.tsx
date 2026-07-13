import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { ScreenerRow } from "@/components/research/ScreenerRow"
import type { RankedRow } from "@/lib/api/universe"
import { formatUsdCompact } from "@/lib/formatMetrics"
import { auditRankRow, mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"
import { driverBarWidth, formatScoreDrivers } from "@/lib/scoreBaseline"

const base: RankedRow = {
  ticker: "KSPI",
  recipe_id: "R3",
  universe_version: "univ_test",
  rank: 1,
  score: 9.877425,
  contributions: { rd_prod: 4.5, mos_live: 4.5, roic: 0.4939 },
  completeness_grade: "C",
  freshness_ok: true,
  kill_active: false,
  reviewer_passed: false,
  name: "Joint Stock Co Kaspikz",
  industry: "Infrastructure",
  price_live: 89.67,
  fair_px_lo: 207.5951403270201,
  fair_px_med: 249.77850114953984,
  fair_px_hi: 291.9618619720595,
  mos_live: 1.7855302905045147,
  vs_median_pct: 1.7855302905045147,
  revenue_usd: 9112728620,
  rev_cagr: 0.4344,
  gm: 0.7351,
  fcfm_sbc: 0.1617,
  roic: 0.27,
  rd_prod: 4.759,
  retention: null,
}

function renderRow(row: RankedRow): string {
  return renderToStaticMarkup(
    <MemoryRouter>
      <ScreenerRow
        r={row}
        displayRank={1}
        selectEnabled={false}
        selected={false}
        onToggle={() => undefined}
        showStance={false}
      />
    </MemoryRouter>
  )
}

describe("formatScoreDrivers", () => {
  it("labels the strongest axes in plain English", () => {
    expect(formatScoreDrivers({ mos_live: 0.8, rd_prod: 0.4 })).toContain("Value gap vs target")
    expect(formatScoreDrivers({ mos_live: 0.8, rd_prod: 0.4 })).toContain("R&D productivity")
  })

  it("returns empty string when there are no contributions", () => {
    expect(formatScoreDrivers(undefined)).toBe("")
    expect(formatScoreDrivers({})).toBe("")
  })
})

describe("driverBarWidth", () => {
  it("scales contribution magnitude", () => {
    expect(driverBarWidth(0.5, 1)).toBe(50)
    expect(driverBarWidth(0, 1)).toBe(8)
  })
})

describe("ScreenerRow render contracts", () => {
  it("fixture itself passes first-principles audit", () => {
    expect(auditRankRow(base)).toEqual([])
  })

  it("does not show duplicate MoS when it equals live vs-target", () => {
    expect(mosDiffersFromLiveGap(base.mos_live, base.vs_median_pct)).toBe(false)
    const html = renderRow(base)
    expect(html).toContain("vs target")
    expect(html).toContain("Sell ceiling")
    expect(html).toContain(formatUsdCompact(base.revenue_usd))
    // MoS label must not appear as a metric column when equal
    expect(html).not.toMatch(/>\s*MoS\s*</)
    expect(html).not.toContain("Research MoS")
  })

  it("shows Research MoS only when frozen MoS disagrees with live gap", () => {
    const row = { ...base, mos_live: 0.4, vs_median_pct: 1.7855302905045147 }
    expect(mosDiffersFromLiveGap(row.mos_live, row.vs_median_pct)).toBe(true)
    const html = renderRow(row)
    expect(html).toContain("Research MoS")
  })

  it("renders compact revenue and a fair-band gauge", () => {
    const html = renderRow(base)
    expect(html).toContain("$9.11B")
    expect(html).toContain("Fair band")
    expect(html).toContain("Below fair band")
    expect(html).toContain("9.877")
  })

  it("uses a filled 5-column valuation strip (no empty sixth cell placeholder)", () => {
    const html = renderRow(base)
    for (const label of ["Price", "Target", "vs target", "Sell ceiling", "Revenue"]) {
      expect(html.toLowerCase()).toContain(label.toLowerCase())
    }
  })

  it("flags Above fair band for APP-class rows once (chip, not duplicated on gauge)", () => {
    const html = renderRow({
      ...base,
      ticker: "APP",
      price_live: 506.98,
      fair_px_lo: 64.08,
      fair_px_med: 78.96,
      fair_px_hi: 93.84,
      mos_live: -0.844,
      vs_median_pct: -0.844,
      score: 8.85,
      contributions: { rd_prod: 4.5, fcfm_sbc: 3, mos_live: -1.6 },
    })
    expect(html).toContain("Above fair band")
    expect(html.split("Above fair band").length - 1).toBe(1)
  })

  it("hides UNKNOWN stance chips on buy cards", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <ScreenerRow
          r={base}
          displayRank={1}
          selectEnabled={false}
          selected={false}
          onToggle={() => undefined}
          showStance
          stance={{
            ticker: "KSPI",
            stance: "UNKNOWN",
            confidence: "none",
            score: null,
            horizon_years: null,
            implied_ann_return: null,
            horizon_note: null,
            blockers: ["incomplete"],
            watermark: "research",
          }}
        />
      </MemoryRouter>
    )
    expect(html).not.toContain(">UNKNOWN<")
  })
})
