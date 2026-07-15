/**
 * PATH: frontend/src/components/company-report/ReportHeader.tsx
 * PURPOSE: Page-1 identity band — company, stance, price vs band, key
 * decision numbers, as-of provenance.
 */
import type { CompanyReportSnapshot } from "@/lib/api/companyReports"

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "Unknown" : `${(v * 100).toFixed(1)}%`
}

function usd(v: number | null | undefined): string {
  return v === null || v === undefined ? "Unknown" : `$${v.toFixed(2)}`
}

export function ReportHeader({ report }: { report: CompanyReportSnapshot }) {
  return (
    <header data-testid="report-header">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div className="report-kicker">
            Finsoeasy Research · Two-page company brief · {report.as_of_date}
          </div>
          <div className="report-h1">
            {report.company_name ?? report.ticker}{" "}
            <span style={{ fontSize: "11pt", fontWeight: 400, color: "#6b6b6b" }}>
              {report.ticker}
              {report.exchange ? ` · ${report.exchange}` : ""}
              {report.industry ? ` · ${report.industry}` : ""}
            </span>
          </div>
        </div>
        <div style={{ textAlign: "right", fontFamily: "system-ui, sans-serif" }}>
          <div className="report-kicker">Research stance</div>
          <div style={{ fontSize: "15pt", fontWeight: 700 }}>
            {report.stance ?? "UNKNOWN"}
            {report.horizon_years != null && (
              <span style={{ fontSize: "8pt", fontWeight: 500, color: "#6b6b6b" }}>
                {" "}
                {report.horizon_years}y
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="report-metrics" style={{ marginTop: 6, gridTemplateColumns: "repeat(6, 1fr)" }}>
        <div className="report-metric">
          <div className="label">Price{report.price_as_of ? ` (${report.price_as_of})` : ""}</div>
          <div className="value">{usd(report.price)}</div>
        </div>
        <div className="report-metric">
          <div className="label">Fair band (lo/med/hi)</div>
          <div className="value">
            {usd(report.fair_px_lo)} / {usd(report.fair_px_med)} / {usd(report.fair_px_hi)}
          </div>
        </div>
        <div className="report-metric">
          <div className="label">Margin of safety</div>
          <div className="value">{pct(report.mos_live)}</div>
        </div>
        <div className="report-metric">
          <div className="label">Implied ann. return</div>
          <div className="value">{pct(report.implied_ann_return)}</div>
        </div>
        <div className="report-metric">
          <div className="label">Market cap</div>
          <div className="value">
            {report.market_cap == null ? "Unknown" : `$${(report.market_cap / 1e9).toFixed(1)}B`}
          </div>
        </div>
        <div className="report-metric">
          <div className="label">Universe build</div>
          <div className="value" style={{ fontSize: "6.8pt", fontWeight: 500 }}>
            {report.universe_version}
          </div>
        </div>
      </div>
    </header>
  )
}
