/**
 * PATH: frontend/src/components/company-report/CompanyReport.test.tsx
 * PURPOSE: Static-render tests for the two-page brief components — citation
 * anchors resolve, unknowns render as Unknown, provenance labels show, and
 * the fair-band chart degrades honestly without a band.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { CitationList } from "@/components/company-report/CitationList"
import { FairBandChart } from "@/components/company-report/FairBandChart"
import { ReportHeader } from "@/components/company-report/ReportHeader"
import { SectionBlock } from "@/components/company-report/SectionBlock"
import type {
  CompanyReportSnapshot,
  ReportCitation,
  ReportSection,
} from "@/lib/api/companyReports"

const citations: ReportCitation[] = [
  {
    cite_id: "S1",
    provenance: "sealed",
    title: "Sealed universe vector",
    locator: "metric_vectors:univ_test:WIX",
    as_of_date: "2026-06-30",
    available_date: "2026-07-15",
  },
  {
    cite_id: "A1",
    provenance: "analyst",
    title: "Wix 20-F FY2025",
    locator: "sec:0001576914-26-000010",
    url: "https://www.sec.gov/Archives/edgar/data/1576914/xyz.htm",
  },
]

const section: ReportSection = {
  section_id: "moat",
  title: "Moat evidence",
  body: "Switching costs anchored in hosted production websites.",
  cite_ids: ["A1"],
  metrics: [
    {
      label: "Net revenue retention",
      value: null,
      provenance: "sealed",
      cite_ids: [],
    },
    {
      label: "Gross margin",
      value: 0.68,
      unit: "%",
      provenance: "sealed",
      cite_ids: ["S1"],
    },
  ],
  scenarios: [],
}

const report: CompanyReportSnapshot = {
  snapshot_id: "rpt_fixture",
  ticker: "WIX",
  universe_version: "univ_test",
  template_version: "brief_2p_v1",
  engine_version: "report_builder_v1",
  created_at: "2026-07-15T08:00:00",
  as_of_date: "2026-07-15",
  status: "published",
  company_name: "Wix.com Ltd",
  exchange: "NASDAQ",
  industry: "Software",
  stance: "BUY",
  price: 150,
  fair_px_lo: 160,
  fair_px_med: 210,
  fair_px_hi: 280,
  mos_live: 0.4,
  implied_ann_return: 0.12,
  horizon_years: 3,
  market_cap: 8.4e9,
  page1: [],
  page2: [
    {
      section_id: "consensus_vs_internal",
      title: "Consensus vs internal underwriting",
      body: "",
      cite_ids: [],
      metrics: [],
      scenarios: [
        {
          name: "consensus",
          provenance: "licensed_consensus",
          fair_px: 205,
          cite_ids: ["S1"],
        },
      ],
    },
  ],
  citations,
  disclosures: ["Research only."],
}

describe("SectionBlock", () => {
  it("renders unknown metrics as Unknown and cited metrics with anchors", () => {
    const html = renderToStaticMarkup(<SectionBlock section={section} />)
    expect(html).toContain("Unknown")
    expect(html).toContain("68.0%")
    expect(html).toContain('href="#cite-S1"')
    expect(html).toContain('href="#cite-A1"')
    expect(html).toContain("Sealed")
  })
})

describe("CitationList", () => {
  it("creates one anchor target per citation with provenance labels", () => {
    const html = renderToStaticMarkup(<CitationList citations={citations} />)
    expect(html).toContain('id="cite-S1"')
    expect(html).toContain('id="cite-A1"')
    expect(html).toContain("available 2026-07-15")
    expect(html).toContain("https://www.sec.gov/")
  })

  it("every in-document reference resolves to a listed citation", () => {
    const sectionHtml = renderToStaticMarkup(<SectionBlock section={section} />)
    const listHtml = renderToStaticMarkup(<CitationList citations={citations} />)
    const refs = [...sectionHtml.matchAll(/href="#cite-([^"]+)"/g)].map((m) => m[1])
    for (const ref of refs) {
      expect(listHtml).toContain(`id="cite-${ref}"`)
    }
  })
})

describe("ReportHeader", () => {
  it("shows stance, band, and universe lineage", () => {
    const html = renderToStaticMarkup(<ReportHeader report={report} />)
    expect(html).toContain("BUY")
    expect(html).toContain("$160.00 / $210.00 / $280.00")
    expect(html).toContain("univ_test")
    expect(html).toContain("40.0%")
  })
})

describe("FairBandChart", () => {
  it("renders fixed-size accessible SVG with street target", () => {
    const html = renderToStaticMarkup(<FairBandChart report={report} />)
    expect(html).toContain("<svg")
    expect(html).toContain('width="660"')
    expect(html).toContain("aria-label")
    expect(html).toContain("Street $205")
  })

  it("degrades to Unknown without a sealed band", () => {
    const noBand = { ...report, fair_px_lo: null, fair_px_med: null, fair_px_hi: null }
    const html = renderToStaticMarkup(<FairBandChart report={noBand} />)
    expect(html).not.toContain("<svg")
    expect(html).toContain("Unknown")
  })
})
