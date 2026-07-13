/**
 * PATH: frontend/src/lib/formulaRegistry.ts
 * PURPOSE: Load sealed formula-registry.json — every investor number ID + cite.
 */
import registryJson from "@/fixtures/formula-registry.json"

export type FormulaStatus = "audited" | "documented" | "pending"

export type FormulaEntry = {
  id: string
  name: string
  expression: string
  surfaces: string[]
  compute: string[]
  display: string[]
  audit: string[]
  reference: { kind: string; cite: string }
  status: FormulaStatus
}

export type FormulaRegistry = {
  schema_version: number
  title: string
  authority: string
  formulas: FormulaEntry[]
}

export const formulaRegistry = registryJson as FormulaRegistry

export function formulaById(id: string): FormulaEntry {
  const row = formulaRegistry.formulas.find((f) => f.id === id)
  if (!row) throw new Error(`Unknown formula id: ${id}`)
  return row
}

/** Tip suffix: `[F_VS_MEDIAN_PCT]` for auditability in the UI. */
export function formulaTip(id: string, body: string): string {
  const row = formulaById(id)
  return `${body} [${row.id}: ${row.expression}]`
}

export function auditedFormulaIds(): string[] {
  return formulaRegistry.formulas.filter((f) => f.status === "audited").map((f) => f.id)
}
