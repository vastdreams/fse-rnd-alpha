/**
 * PATH: src/components/research/AuditDrawer.tsx
 * PURPOSE: Click-any-number → proof drawer. Shows the full evidence trail for
 * one metric: value, PIT dates, formula, claims (verbatim excerpts), source
 * snapshots (accessions), literature binds, DeepSeek run status, final review.
 */
import { useEffect, useRef, useState } from "react"
import { getAuditTrail, type AuditTrail } from "@/lib/api/universe"
import { formatResearchMetric4 } from "@/lib/formatMetrics"

export function AuditDrawer({
  ticker,
  axis,
  universeVersion,
  onClose,
}: {
  ticker: string
  axis: string
  universeVersion?: string
  onClose: () => void
}) {
  const [trail, setTrail] = useState<AuditTrail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)
  const closeRef = useRef<HTMLButtonElement>(null)
  const priorFocusRef = useRef<HTMLElement | null>(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setTrail(null)
    setError(null)
    getAuditTrail(ticker, axis, universeVersion, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setTrail(result)
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setError(String(e))
        }
      })
    return () => controller.abort()
  }, [ticker, axis, universeVersion])

  useEffect(() => {
    priorFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault()
        onCloseRef.current()
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("keydown", onKeyDown)
      priorFocusRef.current?.focus()
    }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="audit-drawer-title"
        className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 id="audit-drawer-title" className="text-lg font-semibold text-black">
              {ticker} · <span className="font-mono text-base">{axis}</span>
            </h2>
            <p className="text-[11px] text-neutral-600">Evidence trail — research only, not investment advice</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-2 py-1 text-xs"
          >
            Close
          </button>
        </div>

        {error && <p className="mt-4 text-sm text-rose-700">{error}</p>}
        {!trail && !error && <p className="mt-4 text-sm text-neutral-600">Loading trail…</p>}

        {trail && (
          <div className="mt-4 space-y-4">
            <Section title="Metric value">
              <div className="text-2xl font-semibold tabular-nums text-black">
                {trail.metric.value === null || trail.metric.value === undefined
                  ? "Unknown"
                  : formatResearchMetric4(axis, trail.metric.value)}
              </div>
              <KV k="Formula" v={trail.metric.formula || "—"} />
              <KV k="Engine" v={trail.metric.engine_version || "—"} />
              <KV k="As-of (period)" v={trail.metric.as_of_date || "—"} />
              <KV k="Available (knowable from)" v={trail.metric.available_date || "—"} />
              {trail.metric.value === null && (
                <p className="mt-1 text-[11px] text-neutral-600">
                  Unknown means not disclosed / not computed — never imputed.
                </p>
              )}
            </Section>

            <Section title={`Evidence claims (${trail.claims.length})`}>
              {trail.claims.length === 0 && (
                <p className="text-xs text-neutral-600">No claims recorded for this metric.</p>
              )}
              {trail.claims.map((c) => (
                <div key={c.claim_id} className="rounded-md border border-border bg-neutral-50 p-2">
                  <div className="text-[11px] font-medium text-black">
                    {c.field} {c.operator && c.operator !== "=" ? c.operator : ""}{" "}
                    {c.value_numeric !== null ? c.value_numeric : ""} {c.unit || ""}
                  </div>
                  <div className="mt-1 text-[11px] italic leading-snug text-neutral-700">
                    “{c.value_text.slice(0, 300)}
                    {c.value_text.length > 300 ? "…" : ""}”
                  </div>
                  <div className="mt-1 text-[10px] text-neutral-500">
                    {c.excerpt_locator} · extractor {c.extractor}
                  </div>
                </div>
              ))}
            </Section>

            <Section title={`Source snapshots (${trail.snapshots.length})`}>
              {trail.snapshots.map((s) => (
                <div key={s.snapshot_id} className="rounded-md border border-border p-2">
                  <div className="text-[11px] font-medium text-black">{s.kind}</div>
                  <div className="break-all text-[10px] text-neutral-600">{s.locator}</div>
                  <div className="text-[10px] text-neutral-500">
                    as-of {s.as_of_date} · available {s.available_date}
                  </div>
                </div>
              ))}
            </Section>

            <Section title="Literature">
              {trail.literature.length === 0 && (
                <p className="text-xs text-neutral-600">No literature bind for this axis.</p>
              )}
              {trail.literature.map((l) => (
                <div key={l.bib_key} className="text-[11px] text-neutral-800">
                  <span className="font-medium">{l.citation}</span>
                  {l.paper_section ? <span className="text-neutral-500"> — {l.paper_section}</span> : null}
                </div>
              ))}
            </Section>

            <Section title="AI audit & review">
              <KV
                k="DeepSeek run"
                v={
                  trail.deepseek_run
                    ? `${trail.deepseek_run.job} · ${trail.deepseek_run.status}${trail.deepseek_run.severity ? ` · ${trail.deepseek_run.severity}` : ""}`
                    : "none"
                }
              />
              <KV
                k="Final review (Cursor)"
                v={
                  trail.final_review
                    ? trail.final_review.passed
                      ? "reviewer_passed"
                      : "review failed"
                    : "not yet reviewed"
                }
              />
              <p className="mt-1 text-[10px] text-neutral-500">
                DeepSeek maps and flags gaps only — it never authors metric values.
              </p>
            </Section>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-2 text-[11px]">
      <span className="text-neutral-600">{k}</span>
      <span className="text-right font-medium text-black">{v}</span>
    </div>
  )
}
