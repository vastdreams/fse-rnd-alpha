import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { BuyDenseRow } from "@/components/research/BuyDenseRow"
import type { RankedRow, StanceListRow } from "@/lib/api/universe"

const row: RankedRow = {
  ticker: "SPSC",
  recipe_id: "R3",
  universe_version: "univ_test",
  rank: 1,
  score: 89.01,
  contributions: {
    rd_prod: 0.327,
    retention: 0.305,
    mos_live: 0.236,
    fcfm_sbc: 0.21,
  },
  completeness_grade: "A",
  freshness_ok: true,
  kill_active: false,
  reviewer_passed: true,
  name: "SPS Commerce",
  industry: "Software - Application",
  price_live: 240.55,
  fair_px_lo: 67.7,
  fair_px_med: 110.2,
  fair_px_hi: 109.2,
  mos_live: 0.4689,
  fundamentals_baseline_as_of: "2023-12-31",
  fundamentals_as_of: "2026-03-31",
  revenue_usd: 2_760_000_000,
  rev_cagr: 0.1961,
  npm: 0.031,
  net_profit_usd: 85_560_000,
  gm: 0.681,
  fcfm_sbc: 0.143,
  fcf_usd: 390_000_000,
  roic: 0.208,
  rd_int: 0.0975,
  rd_prod: 0.8361,
  retention: null,
}

const stance: StanceListRow = {
  ticker: "SPSC",
  stance: "BUY",
  confidence: "high",
  score: 89.01,
  horizon_years: 2,
  implied_ann_return: 0.1937,
  horizon_note: null,
  blockers: [],
  watermark: "test",
}

describe("BuyDenseRow", () => {
  it("renders comma-formatted dollars and explained R&D metrics", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <BuyDenseRow
          r={row}
          displayRank={1}
          stance={stance}
          selectEnabled
          selected
          onToggle={() => undefined}
        />
      </MemoryRouter>
    )

    expect(html).toContain("$2,760,000,000")
    expect(html).toContain("R&amp;D intensity")
    expect(html).toContain("R&amp;D spend ÷ revenue")
    expect(html).toContain("R&amp;D productivity")
    expect(html).toContain("GP gain Dec 2023–Mar 2026 / R&amp;D 2023–25")
  })

  it("renders below-target BUY rows without throwing (sell-ceiling upside path)", () => {
    const belowTarget: RankedRow = {
      ...row,
      price_live: 88.4,
      fair_px_lo: 90,
      fair_px_med: 110.2,
      fair_px_hi: 140,
      mos_live: 0.1978,
    }
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <BuyDenseRow
          r={belowTarget}
          displayRank={1}
          stance={stance}
          selectEnabled
          selected={false}
          onToggle={() => undefined}
        />
      </MemoryRouter>
    )
    expect(html).toContain("to sell")
    expect(html).toContain("Sell ceiling")
    expect(html).toContain("$110.2")
  })

  it("renders the thesis strip with skew, RD cohort, survivability and dated catalyst", () => {
    const withThesis: RankedRow = {
      ...row,
      payoff_skew: 4.2,
      payoff_skew_label: null,
      rd_elig: true,
      rd_composite: 1.8,
      survivable: true,
    }
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <BuyDenseRow
          r={withThesis}
          displayRank={1}
          stance={stance}
          selectEnabled={false}
          selected={false}
          onToggle={() => undefined}
        />
      </MemoryRouter>
    )
    expect(html).toContain("skew 4.2:1")
    expect(html).toContain("RD cohort ✓ (1.8σ)")
    expect(html).toContain("survivable ✓")
    expect(html).toContain("dated catalyst ✓")
  })

  it("thesis strip is honest about UNKNOWN fields (pre-thesis universes)", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <BuyDenseRow
          r={row}
          displayRank={1}
          stance={stance}
          selectEnabled={false}
          selected={false}
          onToggle={() => undefined}
        />
      </MemoryRouter>
    )
    expect(html).toContain("skew: UNKNOWN")
    expect(html).toContain("RD cohort UNKNOWN")
    expect(html).toContain("survivability UNKNOWN")
  })
})
