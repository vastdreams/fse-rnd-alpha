/**
 * PATH: frontend/src/components/company-report/SectionBlock.tsx
 * PURPOSE: One titled report section — cited narrative, metric grid, scenario
 * table. Unknown renders as Unknown; every value shows its provenance class.
 */
import type { ReportMetric, ReportScenario, ReportSection } from "@/lib/api/companyReports"
import { PROVENANCE_LABELS } from "@/lib/api/companyReports"

function fmtMetric(m: ReportMetric): string {
  if (m.display) return m.display
  if (m.value === null || m.value === undefined) return "Unknown"
  if (m.unit === "%") {
    // Sealed ratios arrive as fractions except score-like axes (>1.5).
    const v = Math.abs(m.value) <= 1.5 ? m.value * 100 : m.value
    return `${v.toFixed(1)}%`
  }
  if (Math.abs(m.value) >= 1e9) return `$${(m.value / 1e9).toFixed(1)}B`
  return m.value.toFixed(2)
}

function fmtPx(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `$${v.toFixed(2)}`
}

function fmtPct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`
}

function Cites({ ids }: { ids: string[] }) {
  if (!ids.length) return null
  return (
    <>
      {ids.map((id) => (
        <a key={id} href={`#cite-${id}`} className="report-cite">
          [{id}]
        </a>
      ))}
    </>
  )
}

function MetricCell({ metric }: { metric: ReportMetric }) {
  const unknown = metric.value === null && !metric.display
  return (
    <div className="report-metric" title={metric.methodology ?? undefined}>
      <div className="label">
        {metric.label} <span className="report-provenance">{PROVENANCE_LABELS[metric.provenance]}</span>
      </div>
      <div className={`value${unknown ? " unknown" : ""}`}>
        {fmtMetric(metric)}
        <Cites ids={metric.cite_ids} />
      </div>
    </div>
  )
}

function ScenarioTable({ scenarios }: { scenarios: ReportScenario[] }) {
  if (!scenarios.length) return null
  return (
    <table className="report-scenarios">
      <thead>
        <tr>
          <th>Case</th>
          <th>Rev growth</th>
          <th>Margin</th>
          <th>Fair value</th>
          <th>Implied return</th>
          <th>Note</th>
        </tr>
      </thead>
      <tbody>
        {scenarios.map((s) => (
          <tr key={s.name}>
            <td>
              {s.name} <span className="report-provenance">{PROVENANCE_LABELS[s.provenance]}</span>
              <Cites ids={s.cite_ids} />
            </td>
            <td>{fmtPct(s.rev_growth)}</td>
            <td>{fmtPct(s.margin)}</td>
            <td>{fmtPx(s.fair_px)}</td>
            <td>{fmtPct(s.implied_return)}</td>
            <td>{s.note ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function SectionBlock({ section }: { section: ReportSection }) {
  return (
    <section className="report-section" data-testid={`report-section-${section.section_id}`}>
      <h3>{section.title}</h3>
      {section.body && (
        <p className="report-body">
          {section.body}
          <Cites ids={section.cite_ids} />
        </p>
      )}
      {section.metrics.length > 0 && (
        <div className="report-metrics">
          {section.metrics.map((m) => (
            <MetricCell key={m.label} metric={m} />
          ))}
        </div>
      )}
      <ScenarioTable scenarios={section.scenarios} />
    </section>
  )
}
