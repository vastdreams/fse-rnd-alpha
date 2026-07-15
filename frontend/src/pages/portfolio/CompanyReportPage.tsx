/**
 * PATH: frontend/src/pages/portfolio/CompanyReportPage.tsx
 * PURPOSE: The two-page printable company brief. Renders one immutable
 * snapshot fetched by id — never live data, never a fallback. Signals
 * window.__REPORT_READY__ for the deterministic PDF renderer.
 */
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { CitationList } from "@/components/company-report/CitationList"
import { FairBandChart } from "@/components/company-report/FairBandChart"
import { ReportHeader } from "@/components/company-report/ReportHeader"
import { SectionBlock } from "@/components/company-report/SectionBlock"
import { getReport, reportPdfUrl, type ReportEnvelope } from "@/lib/api/companyReports"
import "@/components/company-report/report-print.css"

declare global {
  interface Window {
    __REPORT_READY__?: boolean
  }
}

export function CompanyReportPage() {
  const { ticker = "", snapshotId = "" } = useParams<{ ticker: string; snapshotId: string }>()
  const [envelope, setEnvelope] = useState<ReportEnvelope | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    window.__REPORT_READY__ = false
    const controller = new AbortController()
    getReport(snapshotId, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        if (data.report.ticker.toUpperCase() !== ticker.toUpperCase()) {
          setError(`Snapshot ${snapshotId} belongs to ${data.report.ticker}, not ${ticker}`)
          return
        }
        setEnvelope(data)
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e))
      })
    return () => controller.abort()
  }, [snapshotId, ticker])

  useEffect(() => {
    if (!envelope) return
    let cancelled = false
    const fonts = (document as Document & { fonts?: { ready: Promise<unknown> } }).fonts
    void Promise.resolve(fonts?.ready).then(() => {
      if (!cancelled) window.__REPORT_READY__ = true
    })
    return () => {
      cancelled = true
    }
  }, [envelope])

  if (error) {
    return (
      <div className="p-6 text-sm text-rose-800" data-testid="report-error">
        Report unavailable: {error}
      </div>
    )
  }
  if (!envelope) {
    return <div className="p-6 text-sm text-neutral-600">Loading report…</div>
  }

  const r = envelope.report
  const footer = (page: number) => (
    <footer className="report-footer">
      <span>
        {r.company_name ?? r.ticker} · {r.ticker} · Snapshot {r.snapshot_id} ·{" "}
        {envelope.status.toUpperCase()} · sha256 {envelope.content_sha256.slice(0, 12)}…
      </span>
      <span>Research only — not investment advice · Page {page} of 2</span>
    </footer>
  )

  return (
    <div className="report-document" data-testid="report-document">
      <div className="report-toolbar">
        <Link to={`/app/company/${r.ticker}`} className="text-xs font-medium text-neutral-700 hover:underline">
          ← {r.ticker} research
        </Link>
        <div className="flex-1" />
        <a
          href={reportPdfUrl(r.snapshot_id)}
          className="rounded-lg bg-black px-3 py-1.5 text-xs font-semibold text-white"
        >
          Download PDF
        </a>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-800"
        >
          Print
        </button>
      </div>

      <article className="report-page" data-testid="report-page-1">
        <ReportHeader report={r} />
        <FairBandChart report={r} />
        {r.page1.map((section) => (
          <SectionBlock key={section.section_id} section={section} />
        ))}
        {footer(1)}
      </article>

      <article className="report-page" data-testid="report-page-2">
        {r.page2.map((section) => (
          <SectionBlock key={section.section_id} section={section} />
        ))}
        <CitationList citations={r.citations} />
        <section className="report-section">
          <h3>Disclosures</h3>
          <ol className="report-citations">
            {r.disclosures.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ol>
        </section>
        {footer(2)}
      </article>
    </div>
  )
}
