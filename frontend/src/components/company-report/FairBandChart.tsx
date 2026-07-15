/**
 * PATH: frontend/src/components/company-report/FairBandChart.tsx
 * PURPOSE: Fixed-geometry SVG — sealed fair-value band vs live price vs
 * external consensus target. No responsive container, no animation: the same
 * pixels render on screen, in print, and in the PDF renderer.
 */
import type { CompanyReportSnapshot } from "@/lib/api/companyReports"

const W = 660
const H = 84
const PAD = 46

export function FairBandChart({ report }: { report: CompanyReportSnapshot }) {
  const { fair_px_lo: lo, fair_px_med: med, fair_px_hi: hi, price } = report
  const consensusTarget = report.page2
    .find((s) => s.section_id === "consensus_vs_internal")
    ?.scenarios.find((s) => s.name === "consensus")?.fair_px

  if (lo == null || med == null || hi == null) {
    return (
      <div className="report-section">
        <h3>Fair-value band</h3>
        <p className="report-body">Unknown — sealed band unavailable for this build.</p>
      </div>
    )
  }

  const values = [lo, hi, price ?? lo, consensusTarget ?? lo]
  const min = Math.min(...values) * 0.92
  const max = Math.max(...values) * 1.08
  const x = (v: number) => PAD + ((v - min) / (max - min)) * (W - 2 * PAD)
  const mid = H / 2

  const marker = (v: number, label: string, above: boolean, bold = false) => (
    <g key={label}>
      <line x1={x(v)} x2={x(v)} y1={mid - 11} y2={mid + 11} stroke="#171717" strokeWidth={bold ? 2 : 1} />
      <text
        x={x(v)}
        y={above ? mid - 15 : mid + 23}
        textAnchor="middle"
        fontSize={8.5}
        fontFamily="system-ui, sans-serif"
        fill="#171717"
        fontWeight={bold ? 700 : 400}
      >
        {label} ${v.toFixed(0)}
      </text>
    </g>
  )

  return (
    <section className="report-section" data-testid="fair-band-chart">
      <h3>Sealed fair-value band vs price</h3>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Fair value band ${lo.toFixed(0)} to ${hi.toFixed(0)} dollars, median ${med.toFixed(0)}, price ${price?.toFixed(0) ?? "unknown"}`}
      >
        <rect x={x(lo)} y={mid - 8} width={x(hi) - x(lo)} height={16} fill="#e8e8e4" stroke="#d9d9d4" />
        {marker(lo, "Low", false)}
        {marker(med, "Median", true)}
        {marker(hi, "High", false)}
        {price != null && (
          <g>
            <circle cx={x(price)} cy={mid} r={4.5} fill="#171717" />
            <text
              x={x(price)}
              y={mid - 15}
              textAnchor="middle"
              fontSize={8.5}
              fontWeight={700}
              fontFamily="system-ui, sans-serif"
            >
              Price ${price.toFixed(0)}
            </text>
          </g>
        )}
        {consensusTarget != null && (
          <g>
            <circle cx={x(consensusTarget)} cy={mid} r={4} fill="none" stroke="#171717" strokeWidth={1.4} strokeDasharray="2 1.5" />
            <text
              x={x(consensusTarget)}
              y={mid + 23}
              textAnchor="middle"
              fontSize={8}
              fontFamily="system-ui, sans-serif"
              fill="#6b6b6b"
            >
              Street ${consensusTarget.toFixed(0)}
            </text>
          </g>
        )}
      </svg>
      <p className="report-body" style={{ fontSize: "6.4pt", color: "#6b6b6b" }}>
        Band = internal triangulated lenses (model output, not market data). Street = external sell-side
        mean target (licensed consensus), shown for disagreement only.
      </p>
    </section>
  )
}
