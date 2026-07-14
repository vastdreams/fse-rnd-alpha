import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import {
  decisionChainById,
  decisionChainSummary,
  decisionChainsRegistry,
  explainStepFormulas,
} from "@/lib/decisionChains"

const here = dirname(fileURLToPath(import.meta.url))

describe("decisionChains (first principles, no opinion)", () => {
  it("loads sealed chains and matches repo bytes", () => {
    expect(decisionChainsRegistry.schema_version).toBe(1)
    expect(decisionChainsRegistry.assumption_policy.imputation).toBe("forbidden")
    const fe = readFileSync(join(here, "../fixtures/decision-chains.json"))
    const repo = readFileSync(join(here, "../../../contracts/decision-chains.json"))
    expect(createHash("sha256").update(fe).digest("hex")).toBe(
      createHash("sha256").update(repo).digest("hex")
    )
  })

  it("hard gates never mark opinion=true", () => {
    for (const chain of decisionChainsRegistry.chains) {
      for (const step of chain.steps) {
        if (step.gate_kind === "hard") {
          expect(step.opinion, `${chain.id}.${step.id}`).toBe(false)
          expect(step.data_fields.length).toBeGreaterThan(0)
          expect(step.on_unknown.length).toBeGreaterThan(0)
        }
      }
    }
  })

  it("D_STANCE_BUY documents P2_FCF as advisory only", () => {
    const buy = decisionChainById("D_STANCE_BUY")
    const adv = buy.advisory_not_gates.find((a) => a.id === "P2_FCF")
    expect(adv).toBeTruthy()
    expect(adv!.gate_kind).toBe("advisory")
    expect(buy.steps.map((s) => s.id)).toEqual(["F1", "F2", "F3", "F3b", "F4", "F5", "F6"])
  })

  it("D_RANK_R3 pins R3 weights and excludes opinion", () => {
    const r3 = decisionChainById("D_RANK_R3")
    const score = r3.steps.find((s) => s.id === "R3_H3")
    expect(score?.weights).toEqual({
      rd_prod: 1.5,
      fcfm_sbc: 1.0,
      roic: 1.0,
      mos_live: 1.5,
    })
    expect(decisionChainSummary("D_RANK_R3")).toContain("D_RANK_R3")
    expect(explainStepFormulas(score!)).toContain("F_SCORE_ROBUST_Z")
  })
})
