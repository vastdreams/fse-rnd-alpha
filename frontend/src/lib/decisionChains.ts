/**
 * PATH: frontend/src/lib/decisionChains.ts
 * PURPOSE: Decision-chain registry — data-driven gates, no opinion.
 */
import chainsJson from "@/fixtures/decision-chains.json"
import { formulaById } from "@/lib/formulaRegistry"

export type GateKind = "hard" | "advisory" | "derived"

export type DecisionStep = {
  id: string
  label: string
  gate_kind: GateKind
  data_fields: string[]
  formula_ids: string[]
  pass_if: string
  fail_if: string
  unknown_if: string
  on_unknown: string
  opinion: boolean
  note?: string
  weights?: Record<string, number>
}

export type DecisionChain = {
  id: string
  name: string
  first_principles: string
  engine: string
  docs: string[]
  output_fields: string[]
  steps: DecisionStep[]
  advisory_not_gates: Array<Record<string, unknown>>
}

export type DecisionChainsRegistry = {
  schema_version: number
  title: string
  authority: string
  assumption_policy: Record<string, string>
  chains: DecisionChain[]
}

export const decisionChainsRegistry = chainsJson as DecisionChainsRegistry

export function decisionChainById(id: string): DecisionChain {
  const row = decisionChainsRegistry.chains.find((c) => c.id === id)
  if (!row) throw new Error(`Unknown decision chain: ${id}`)
  return row
}

/** One-line provenance for tooltips / score card. */
export function decisionChainSummary(id: string): string {
  const chain = decisionChainById(id)
  const hard = chain.steps.filter((s) => s.gate_kind === "hard").map((s) => s.id)
  return `${chain.id}: ${chain.name}. Hard gates [${hard.join(" → ")}]. ${chain.first_principles}`
}

export function explainStepFormulas(step: DecisionStep): string {
  if (!step.formula_ids.length) return step.label
  const bits = step.formula_ids.map((fid) => {
    const f = formulaById(fid)
    return `${fid} (${f.expression})`
  })
  return `${step.label} ← ${bits.join("; ")}`
}
