/**
 * PATH: frontend/src/components/portfolio/OfferingsPanel.tsx
 * PURPOSE: Show what the company sells from 10-K Business, with provenance.
 */
import { filingOffering, offeringSourceLabel } from "@/lib/filingOfferings"

export function OfferingsPanel({
  ticker,
  filingUrl,
  compact = false,
}: {
  ticker: string
  filingUrl?: string | null
  compact?: boolean
}) {
  const o = filingOffering(ticker)
  if (!o) {
    return (
      <div className={compact ? "text-[11px] text-neutral-700" : "rounded-xl border border-border bg-white p-5 text-sm"}>
        No filing-backed product extract for {ticker} yet.
      </div>
    )
  }

  const body = (
    <>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">
            What they sell
          </div>
          <p className="mt-1 text-sm font-medium leading-snug text-black">{o.headline}</p>
        </div>
        <div className="text-[10px] text-neutral-600 max-w-[220px] text-right">{offeringSourceLabel(o)}</div>
      </div>
      <ul className="mt-3 space-y-1 text-sm text-neutral-800">
        {o.offerings.map((item) => (
          <li key={item} className="flex gap-2">
            <span aria-hidden className="text-neutral-400">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
      {!compact && o.excerpt && (
        <blockquote className="mt-4 border-l-2 border-neutral-300 pl-3 text-xs leading-relaxed text-neutral-700">
          “{o.excerpt}”
        </blockquote>
      )}
      {o.note && <p className="mt-2 text-[11px] text-amber-900">{o.note}</p>}
      {(o.url || filingUrl) && !compact && (
        <a
          href={o.url || filingUrl || undefined}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block text-xs font-medium text-black underline underline-offset-2"
        >
          Open source 10-K →
        </a>
      )}
    </>
  )

  if (compact) return <div className="mt-1 space-y-1">{body}</div>
  return <div className="rounded-xl border border-border bg-white p-5">{body}</div>
}
