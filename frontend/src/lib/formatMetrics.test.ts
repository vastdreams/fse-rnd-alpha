import { describe, expect, it } from "vitest"
import { formatMultiple4, formatNumber4, formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

describe("research metric formatting", () => {
  it("uses comma-grouped USD and no more than four significant figures", () => {
    expect(formatUsd4(1234567890)).toBe("$1,235,000,000")
    expect(formatUsd4(22470000)).toBe("$22,470,000")
  })

  it("makes rate units explicit", () => {
    expect(formatPercent4(0.13765)).toBe("13.77%")
    expect(formatPercent4(-0.0759679, true)).toBe("-7.597%")
  })

  it("labels productivity as a multiple rather than a bare decimal", () => {
    expect(formatMultiple4(1.23456)).toBe("1.235×")
  })

  it("formats score inputs with four significant figures", () => {
    expect(formatNumber4(83.4567)).toBe("83.46")
  })
})
