import { describe, expect, it } from "vitest"
import {
  auditRankRow,
  auditRankRows,
  computeLiveVsTargetPct,
  fairBandZone,
  formatRankViolations,
  mosDiffersFromLiveGap,
} from "@/lib/rankRowInvariants"

/** Real-shaped fixture from production R3 payload (KSPI). */
const kspi = {
  ticker: "KSPI",
  price_live: 89.67,
  fair_px_lo: 207.5951403270201,
  fair_px_med: 249.77850114953984,
  fair_px_hi: 291.9618619720595,
  mos_live: 1.7855302905045147,
  vs_median_pct: 1.7855302905045147,
  revenue_usd: 9112728620,
  score: 9.877425,
  contributions: { rd_prod: 4.5, mos_live: 4.5, roic: 0.4939 },
}

describe("computeLiveVsTargetPct", () => {
  it("is (target − price) / price", () => {
    expect(computeLiveVsTargetPct(100, 150)).toBeCloseTo(0.5)
    expect(computeLiveVsTargetPct(200, 100)).toBeCloseTo(-0.5)
    expect(computeLiveVsTargetPct(0, 100)).toBeNull()
    expect(computeLiveVsTargetPct(null, 100)).toBeNull()
  })
})

describe("mosDiffersFromLiveGap", () => {
  it("hides MoS when it matches live vs-target (trust contract)", () => {
    expect(mosDiffersFromLiveGap(1.78553, 1.78553)).toBe(false)
    expect(mosDiffersFromLiveGap(0.22, 0.221)).toBe(false)
  })

  it("surfaces MoS only when frozen research disagrees", () => {
    expect(mosDiffersFromLiveGap(0.5, 0.2)).toBe(true)
    expect(mosDiffersFromLiveGap(0.3, null)).toBe(true)
    expect(mosDiffersFromLiveGap(null, 0.2)).toBe(false)
  })
})

describe("fairBandZone", () => {
  it("classifies price vs band", () => {
    expect(fairBandZone(90, 200, 290)).toBe("below")
    expect(fairBandZone(240, 200, 290)).toBe("inside")
    expect(fairBandZone(300, 200, 290)).toBe("above")
  })
})

describe("auditRankRow — first principles", () => {
  it("passes a consistent production-shaped row", () => {
    expect(auditRankRow(kspi)).toEqual([])
  })

  it("catches vs_median that does not equal (target−price)/price", () => {
    const bad = { ...kspi, vs_median_pct: 0.5 }
    const v = auditRankRow(bad)
    expect(v.some((x) => x.code === "VS_MEDIAN_MISMATCH")).toBe(true)
  })

  it("catches unordered fair band", () => {
    const bad = { ...kspi, fair_px_lo: 300, fair_px_med: 250, fair_px_hi: 200 }
    const v = auditRankRow(bad)
    expect(v.some((x) => x.code === "FAIR_BAND_ORDER")).toBe(true)
  })

  it("catches below-band price with non-positive vs gap", () => {
    const bad = {
      ...kspi,
      price_live: 50,
      vs_median_pct: -0.1,
      mos_live: -0.1,
    }
    const v = auditRankRow(bad)
    expect(v.some((x) => x.code === "FAIR_BAND_ZONE_CONTRADICTION")).toBe(true)
  })

  it("catches MoS sign contradicting price vs target", () => {
    const bad = {
      ...kspi,
      price_live: 400,
      fair_px_med: 250,
      fair_px_lo: 200,
      fair_px_hi: 290,
      vs_median_pct: (250 - 400) / 400,
      mos_live: 0.5, // positive while above target
    }
    const v = auditRankRow(bad)
    expect(v.some((x) => x.code === "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET")).toBe(true)
  })

  it("catches score without drivers", () => {
    const bad = { ...kspi, contributions: {} }
    const v = auditRankRow(bad)
    expect(v.some((x) => x.code === "SCORE_WITHOUT_DRIVERS")).toBe(true)
  })

  it("audits a batch and formats CI output", () => {
    const violations = auditRankRows([
      kspi,
      { ...kspi, ticker: "BAD", vs_median_pct: 9 },
    ])
    expect(violations.length).toBeGreaterThan(0)
    expect(formatRankViolations(violations)).toContain("VS_MEDIAN_MISMATCH")
  })
})
