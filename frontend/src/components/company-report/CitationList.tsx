/**
 * PATH: frontend/src/components/company-report/CitationList.tsx
 * PURPOSE: Compact numbered source list with anchors for in-document [n] refs.
 */
import type { ReportCitation } from "@/lib/api/companyReports"
import { PROVENANCE_LABELS } from "@/lib/api/companyReports"

export function CitationList({ citations }: { citations: ReportCitation[] }) {
  return (
    <section className="report-section" data-testid="report-citations">
      <h3>Sources & citations</h3>
      <ol className="report-citations">
        {citations.map((c) => (
          <li key={c.cite_id} id={`cite-${c.cite_id}`}>
            [{c.cite_id}] <span className="report-provenance">{PROVENANCE_LABELS[c.provenance]}</span>{" "}
            {c.url ? (
              <a href={c.url} style={{ color: "inherit" }}>
                {c.title}
              </a>
            ) : (
              c.title
            )}
            {" — "}
            {c.locator}
            {c.as_of_date ? ` · as of ${c.as_of_date}` : ""}
            {c.available_date ? ` · available ${c.available_date}` : ""}
          </li>
        ))}
      </ol>
    </section>
  )
}
