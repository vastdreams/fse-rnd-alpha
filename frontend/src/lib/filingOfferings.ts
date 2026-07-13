/**
 * PATH: frontend/src/lib/filingOfferings.ts
 * PURPOSE: Auditable products/offerings from 10-K Item 1 Business (not website scrape).
 */
import offerings from "@/data/filingOfferings.json"

export type FilingOffering = {
  source_type: "10-K Item 1 Business" | "pending_10k_extract" | string
  fy?: string | null
  filed?: string | null
  accession?: string | null
  url?: string | null
  headline: string
  offerings: string[]
  excerpt?: string | null
  note?: string | null
}

const MAP = offerings as Record<string, FilingOffering>

export function filingOffering(ticker: string): FilingOffering | null {
  return MAP[ticker.toUpperCase()] || null
}

export function offeringSourceLabel(o: FilingOffering): string {
  if (o.source_type === "10-K Item 1 Business") {
    return `10-K Item 1 Business${o.fy ? ` · ${o.fy}` : ""}${o.filed ? ` · filed ${o.filed}` : ""}`
  }
  return "Pending 10-K extract — paper product category only"
}
