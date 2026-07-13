import { describe, expect, it } from "vitest"
import { formatScoreDrivers, scoreDrivers, scoreQuality } from "@/lib/scoreBaseline"

describe("scoreQuality", () => {
  it("marks A + fresh as strong", () => {
    const q = scoreQuality({ completeness_grade: "A", freshness_ok: true, kill_active: false })
    expect(q.level).toBe("strong")
    expect(q.label).toBe("Strong")
    expect(q.baseline).toMatch(/solid evidence/i)
  })

  it("marks kill as blocked", () => {
    const q = scoreQuality({ completeness_grade: "A", freshness_ok: true, kill_active: true })
    expect(q.level).toBe("blocked")
    expect(q.label).toBe("Blocked")
  })

  it("marks thin filings as limited", () => {
    const q = scoreQuality({ completeness_grade: "C", freshness_ok: true, kill_active: false })
    expect(q.level).toBe("limited")
    expect(q.baseline).toMatch(/directional only/i)
  })
})

describe("scoreDrivers", () => {
  it("orders by absolute contribution with plain labels", () => {
    const rows = scoreDrivers({ mos_live: 0.8, rd_prod: -0.4, gm: 0.1 })
    expect(rows.map((r) => r.label)).toEqual([
      "Value gap vs target",
      "R&D productivity",
      "Gross margin",
    ])
    expect(rows[0].detail).toMatch(/fair value/i)
  })
})

describe("formatScoreDrivers", () => {
  it("returns empty when no contributions", () => {
    expect(formatScoreDrivers(undefined)).toBe("")
  })
})
