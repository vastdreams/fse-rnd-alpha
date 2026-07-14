import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import type { RankedRow, StanceListRow } from "@/lib/api/universe"
import { splitStrata, UniverseStrataView, weaveAttribution } from "./UniverseStrataView"

function mkRow(ticker: string, extra: Partial<RankedRow> = {}): RankedRow {
  return {
    ticker,
    recipe_id: "R3",
    universe_version: "univ_test",
    rank: 1,
    score: 50,
    contributions: {},
    completeness_grade: "A",
    freshness_ok: true,
    kill_active: false,
    reviewer_passed: true,
    name: `${ticker} Inc`,
    industry: "Software",
    price_live: 100,
    fair_px_lo: 80,
    fair_px_med: 120,
    fair_px_hi: 160,
    mos_live: 0.2,
    fundamentals_baseline_as_of: null,
    fundamentals_as_of: null,
    revenue_usd: null,
    rev_cagr: null,
    npm: null,
    net_profit_usd: null,
    gm: null,
    fcfm_sbc: null,
    fcf_usd: null,
    roic: null,
    rd_int: null,
    rd_prod: null,
    retention: null,
    ...extra,
  }
}

function mkStance(ticker: string, stance: StanceListRow["stance"], blockers: string[]): StanceListRow {
  return {
    ticker,
    stance,
    confidence: stance === "BUY" ? "high" : "none",
    score: 50,
    horizon_years: 2,
    implied_ann_return: null,
    horizon_note: null,
    blockers,
    watermark: "test",
  }
}

describe("splitStrata", () => {
  it("splits cleared / near-miss (exactly one blocker) / weave-ranked", () => {
    const rows = [
      mkRow("BUY1"),
      mkRow("NEAR1"),
      mkRow("REST1", { weave_score: 0.5 }),
      mkRow("REST2", { weave_score: 1.5 }),
    ]
    const stances = new Map([
      ["BUY1", mkStance("BUY1", "BUY", [])],
      ["NEAR1", mkStance("NEAR1", "HOLD", ["F2b: runway 1.4y < 2y"])],
      ["REST1", mkStance("REST1", "HOLD", ["F1", "F3"])],
    ])
    const { cleared, nearMisses, weave } = splitStrata(rows, stances)
    expect(cleared.map((r) => r.ticker)).toEqual(["BUY1"])
    expect(nearMisses.map((m) => m.row.ticker)).toEqual(["NEAR1"])
    expect(nearMisses[0].blocker).toBe("F2b: runway 1.4y < 2y")
    // Weave stratum ordered by weave_score descending.
    expect(weave.map((r) => r.ticker)).toEqual(["REST2", "REST1"])
  })

  it("names without a stance fall to the weave stratum, never to cleared", () => {
    const { cleared, nearMisses, weave } = splitStrata([mkRow("NOSTANCE")], new Map())
    expect(cleared).toHaveLength(0)
    expect(nearMisses).toHaveLength(0)
    expect(weave.map((r) => r.ticker)).toEqual(["NOSTANCE"])
  })
})

describe("weaveAttribution", () => {
  it("formats per-family sigmas and marks unknowns", () => {
    expect(
      weaveAttribution({ z_rd: 1.8, z_quality: 0.9, z_valuation: -0.4, z_momentum: null })
    ).toBe("RD +1.8σ · Qual +0.9σ · Val -0.4σ · Mom ?")
    expect(weaveAttribution(null)).toBe("weave inputs unknown")
  })
})

describe("UniverseStrataView", () => {
  const render = (rows: RankedRow[], stances: Map<string, StanceListRow>) =>
    renderToStaticMarkup(
      <MemoryRouter>
        <UniverseStrataView
          rows={rows}
          stanceByTicker={stances}
          universeVersion="univ_test"
          selectEnabled={false}
          selected={new Set()}
          onToggle={() => undefined}
        />
      </MemoryRouter>
    )

  it("shows the honest empty state instead of silently promoting candidates", () => {
    const html = render(
      [mkRow("NEAR1"), mkRow("REST1")],
      new Map([["NEAR1", mkStance("NEAR1", "HOLD", ["F0"])]])
    )
    expect(html).toContain("0 complete theses today — the gates are doing their job")
    expect(html).toContain("blocked: F0")
    expect(html).toContain("Ranked by the weave")
    expect(html).toContain("Ordering only")
  })

  it("renders cleared theses with the BuyDenseRow surface when gates pass", () => {
    const html = render(
      [mkRow("BUY1", { payoff_skew: 4.0, rd_elig: true, survivable: true })],
      new Map([["BUY1", mkStance("BUY1", "BUY", [])]])
    )
    expect(html).toContain("Complete theses")
    expect(html).not.toContain("0 complete theses today")
    expect(html).toContain("skew 4.0:1")
  })
})
