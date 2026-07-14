/**
 * PATH: frontend/src/components/research/BuyPerformanceBook.tsx
 * PURPOSE: Honest PIT research-BUY track record panel (≠ paper HML_RD),
 * plus the visually distinct SIMULATED robustness-study block (sim_proxy_v1).
 */
import { useEffect, useState } from "react"
import {
  getBuyPerformanceBook,
  getBuySimStudy,
  type BuyPerformanceBook as Book,
  type BuySimStudyResponse,
} from "@/lib/api/universe"
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

export function SimulatedBuyStudyPanel() {
  const [resp, setResp] = useState<BuySimStudyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getBuySimStudy()
      .then((r) => {
        if (!cancelled) setResp(r)
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || "Simulated study unavailable")
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error || !resp) return null
  if (resp.status !== "ready" || !resp.study) {
    return (
      <div className="rounded-lg border border-dashed border-violet-200 bg-violet-50/40 px-3 py-2 text-[11px] text-violet-900">
        Simulated robustness study: not published in this release. The sealed BUY ledger above is the
        only track record.
      </div>
    )
  }

  const s = resp.study
  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50/60 px-3 py-2.5 text-[12px] text-violet-950">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="font-semibold">Simulated robustness study</div>
        <div className="rounded bg-violet-200 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-violet-900">
          SIMULATED — not a track record
        </div>
      </div>
      <p className="mt-1 text-[11px] leading-snug text-violet-900/80">
        Pre-registered proxy gates ({s.gates_contract}, sha {s.gates_contract_sha256.slice(0, 12)}…),
        monthly rebalances {s.cache_span.start} → {s.cache_span.end}, benchmark {s.benchmark.ticker}.
      </p>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {Object.entries(s.inference.horizons).map(([h, v]) => (
          <div key={h} className="rounded border border-violet-100 bg-white/70 px-2 py-1.5">
            <div className="text-[9px] uppercase tracking-wide text-violet-700">
              {h} · {v.n_rebalances} rebalances
            </div>
            <div className="tabular-nums font-semibold">
              excess {formatPercent4(v.mean_excess_vs_benchmark, true)}
            </div>
            <div className="text-[10px] text-violet-900/80">
              book {formatPercent4(v.mean_book_return, true)} · hit {formatPercent4(v.hit_rate)} · maxDD{" "}
              {formatPercent4(v.max_drawdown_book, true)}
            </div>
            <div className="text-[10px] text-violet-900/80">
              {v.newey_west_excess
                ? `NW t=${v.newey_west_excess.t_stat} (n=${v.newey_west_excess.n}, lags=${v.newey_west_excess.lags})`
                : "NW t: too few observations"}
            </div>
          </div>
        ))}
      </div>
      <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[10px] leading-snug text-violet-900/80">
        {s.disclosures.map((d) => (
          <li key={d}>{d}</li>
        ))}
      </ul>
      <p className="mt-1.5 text-[10px] font-medium">{s.clean_ledger_note}</p>
    </div>
  )
}
