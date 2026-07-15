/**
 * PATH: src/lib/api/companyReports.ts
 * PURPOSE: Client for immutable two-page company brief snapshots.
 * Types mirror backend/app/contracts/company_reports.py. Report views never
 * fall back to live data: the snapshot is the document.
 */

import { fetchApiCached } from "./base"

export type ProvenanceClass =
  | "sealed"
  | "current_overlay"
  | "licensed_consensus"
  | "analyst"
  | "model"

export interface ReportCitation {
  cite_id: string
  provenance: ProvenanceClass
  title: string
  locator: string
  source_id?: string | null
  as_of_date?: string | null
  available_date?: string | null
  url?: string | null
}

export interface ReportMetric {
  label: string
  value: number | null
  display?: string | null
  unit?: string | null
  provenance: ProvenanceClass
  as_of_date?: string | null
  cite_ids: string[]
  methodology?: string | null
}

export interface ReportScenario {
  name: string
  provenance: ProvenanceClass
  rev_growth?: number | null
  margin?: number | null
  fair_px?: number | null
  implied_return?: number | null
  cite_ids: string[]
  note?: string | null
}

export interface ReportSection {
  section_id: string
  title: string
  body: string
  metrics: ReportMetric[]
  scenarios: ReportScenario[]
  cite_ids: string[]
}

export interface CompanyReportSnapshot {
  snapshot_id: string
  ticker: string
  universe_version: string
  template_version: string
  engine_version: string
  created_at: string
  as_of_date: string
  status: "draft" | "validated" | "reviewed" | "published"
  company_name?: string | null
  exchange?: string | null
  sector?: string | null
  industry?: string | null
  stance?: string | null
  price?: number | null
  price_as_of?: string | null
  fair_px_lo?: number | null
  fair_px_med?: number | null
  fair_px_hi?: number | null
  mos_live?: number | null
  implied_ann_return?: number | null
  horizon_years?: number | null
  market_cap?: number | null
  page1: ReportSection[]
  page2: ReportSection[]
  citations: ReportCitation[]
  disclosures: string[]
}

export interface ReportEnvelope {
  snapshot_id: string
  status: string
  content_sha256: string
  reviewed_by: string | null
  published_at: string | null
  report: CompanyReportSnapshot
  note: string
}

export interface ReportListEntry {
  snapshot_id: string
  universe_version: string
  template_version: string
  status: string
  content_sha256: string
  created_at: string
  reviewed_by: string | null
  published_at: string | null
}

export const getReport = (snapshotId: string, signal?: AbortSignal) =>
  fetchApiCached<ReportEnvelope>(`/api/reports/${encodeURIComponent(snapshotId)}`, { signal })

export const listReports = (ticker: string, signal?: AbortSignal) =>
  fetchApiCached<{ ticker: string; snapshots: ReportListEntry[] }>(
    `/api/reports/company/${encodeURIComponent(ticker)}`,
    { signal }
  )

export const reportPdfUrl = (snapshotId: string) =>
  `/api/reports/${encodeURIComponent(snapshotId)}/export.pdf`

export const PROVENANCE_LABELS: Record<ProvenanceClass, string> = {
  sealed: "Sealed",
  current_overlay: "Overlay",
  licensed_consensus: "Consensus",
  analyst: "Analyst",
  model: "Model",
}
