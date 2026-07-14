/**
 * PATH: frontend/src/components/research/BuyPerformanceBook.tsx
 * PURPOSE: Honest PIT research-BUY track record panel (≠ paper HML_RD).
 */
import { useEffect, useState } from "react"
import { getBuyPerformanceBook, type BuyPerformanceBook as Book } from "@/lib/api/universe"
import { formatPercent4 } from "@/lib/formatMetrics"

export function BuyPerformanceBookPanel({
  universeVersion,
}: {
  universeVersion?: string | null
}) {
  const [book, setBook] = useState<Book | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    getBuyPerformanceBook(universeVersion)
      .then((b) => {
        if (!cancelled) setBook(b)
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || "BUY performance book unavailable")
      })
    return () => {
      cancelled = true
    }
  }, [universeVersion])

  if (error) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-950">
        BUY performance book: {error}
      </div>
    )
  }
  if (!book) {
    return (
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[12px] text-neutral-600">
        Loading BUY performance book…
      </div>
    )
  }

  const summary = book.summary as
    | {
        horizons?: Record<
          string,
          { mean_equal_weight: number | null; hit_rate: number | null; n_observed: number }
        >
      }
    | null

  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-[12px] text-neutral-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="font-semibold text-neutral-950">PIT research BUY book</div>
        <div className="text-[10px] uppercase tracking-wide text-neutral-500">
          {book.status} · ≠ paper HML_RD
        </div>
      </div>
      <p className="mt-1 text-[11px] leading-snug text-neutral-600">{book.note}</p>
      {book.status === "empty" || !summary?.horizons ? (
        <p className="mt-2 text-[11px] text-neutral-700">
          No sealed BUY sets yet — track record intentionally empty (not invented). Operator seal via
          `/api/universe/buy-performance-book/seal` after promote.
        </p>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Object.entries(summary.horizons).map(([h, v]) => (
            <div key={h} className="rounded border border-neutral-100 bg-neutral-50 px-2 py-1.5">
              <div className="text-[9px] uppercase tracking-wide text-neutral-500">{h} EW</div>
              <div className="tabular-nums font-semibold text-neutral-950">
                {formatPercent4(v.mean_equal_weight, true)}
              </div>
              <div className="text-[10px] text-neutral-600">
                hit {formatPercent4(v.hit_rate)} · n={v.n_observed}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
