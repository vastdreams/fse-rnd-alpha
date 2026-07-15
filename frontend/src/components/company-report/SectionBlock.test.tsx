/**
 * PATH: frontend/src/components/company-report/SectionBlock.test.tsx
 * PURPOSE: Report section rendering — unknown states, provenance labels,
 * citation anchors, scenario table.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import type { ReportSection } from "@/lib/api/companyReports"
import { SectionBlock } from "./SectionBlock"

const SECTION: ReportSection = {
  section_id: "financial_trends",
  title: "Financial & KPI trends",
  body: "Cited narrative.",
  cite_ids: ["A1"],
  metrics: [
    {
      label: "Gross margin",
      value: 0.68,
      unit: "%",
      provenance: "sealed",
      cite_ids: ["S1"],
    },
    {
      label: "Net revenue retention",
      value: null,
      provenance: "sealed",
      cite_ids: [],
    },
  ],
  scenarios: [
    {
      name: "consensus",
      provenance: "licensed_consensus",
      fair_px: 205,
      cite_ids: ["S4"],
      note: "External mean target.",
    },
  ],
}

const html = () => renderToStaticMarkup(<SectionBlock section={SECTION} />)

describe("SectionBlock", () => {
  it("renders values with provenance and unknowns as Unknown", () => {
    const out = html()
    expect(out).toContain("68.0%")
    expect(out).toContain("Unknown")
    expect(out).toContain("Sealed")
  })

  it("links citations to numbered anchors", () => {
    const out = html()
    expect(out).toContain('href="#cite-A1"')
    expect(out).toContain("[A1]")
    expect(out).toContain('href="#cite-S1"')
  })

  it("labels the consensus scenario as external licensed data", () => {
    const out = html()
    expect(out).toContain("consensus")
    expect(out).toContain("Consensus")
    expect(out).toContain("$205.00")
  })

  it("keeps the section testid stable for e2e page-count checks", () => {
    expect(html()).toContain('data-testid="report-section-financial_trends"')
  })
})
