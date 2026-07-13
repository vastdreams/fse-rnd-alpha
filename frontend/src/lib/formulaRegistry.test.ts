import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import {
  auditedFormulaIds,
  formulaById,
  formulaRegistry,
  formulaTip,
} from "@/lib/formulaRegistry"
import { annualizedFromPrices, holdHorizonYears } from "@/lib/sellCeiling"
import { computeLiveVsTargetPct, mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"

const here = dirname(fileURLToPath(import.meta.url))

describe("formulaRegistry (proven + referenced)", () => {
  it("loads schema and required formula IDs", () => {
    expect(formulaRegistry.schema_version).toBe(1)
    for (const id of [
      "F_VS_MEDIAN_PCT",
      "F_SELL_CEILING",
      "F_SCORE_ROBUST_Z",
      "F_HOLD_HORIZON",
      "F_IMPLIED_ANN_RETURN",
      "F_MOS_VS_IDENTITY",
    ]) {
      expect(formulaById(id).expression.length).toBeGreaterThan(5)
      expect(formulaById(id).reference.cite.length).toBeGreaterThan(5)
    }
    expect(auditedFormulaIds().length).toBeGreaterThanOrEqual(12)
  })

  it("FE fixture matches repo contracts/formula-registry.json bytes", () => {
    const fe = readFileSync(join(here, "../fixtures/formula-registry.json"))
    const repo = readFileSync(join(here, "../../../contracts/formula-registry.json"))
    expect(createHash("sha256").update(fe).digest("hex")).toBe(
      createHash("sha256").update(repo).digest("hex")
    )
  })

  it("F_MOS_VS_IDENTITY holds for golden KSPI algebra", () => {
    const price = 89.67
    const fair = 249.77850114953984
    const mos = fair / price - 1
    const vs = computeLiveVsTargetPct(price, fair)
    expect(vs).not.toBeNull()
    expect(Math.abs(mos - (vs as number))).toBeLessThan(1e-12)
    expect(mosDiffersFromLiveGap(mos, vs)).toBe(false)
  })

  it("F_HOLD_HORIZON and F_IMPLIED_ANN_RETURN match documented buckets", () => {
    expect(holdHorizonYears(0.1)).toBe(1)
    expect(holdHorizonYears(0.25)).toBe(2)
    expect(holdHorizonYears(0.6)).toBe(3)
    const ann = annualizedFromPrices(100, 150, 2)
    expect(ann).not.toBeNull()
    expect(Math.abs((ann as number) - (Math.pow(1.5, 0.5) - 1))).toBeLessThan(1e-12)
  })

  it("formulaTip embeds id for UI audit trail", () => {
    const tip = formulaTip("F_VS_MEDIAN_PCT", "Live gap vs target.")
    expect(tip).toContain("[F_VS_MEDIAN_PCT:")
    expect(tip).toContain("(fair_px_med - price_live) / price_live")
  })
})
