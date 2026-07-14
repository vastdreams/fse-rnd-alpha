/**
 * PATH: frontend/src/pages/portfolio/UniverseStrataView.tsx
 * PURPOSE: The post-login decision surface — three explicit strata:
 *   1. Cleared BUY theses (every close_call_v3 gate passed)
 *   2. Near-misses (exactly one gate blocking, named)
 *   3. Ranked by the weave (ordinal ordering with per-family attribution)
 * Honest empty states — never silently swaps candidates in as if cleared.
 */
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { BuyDenseRow } from "@/components/research/BuyDenseRow"
import type { RankedRow, StanceListRow, WeaveZ } from "@/lib/api/universe"
import { formatPercent4 } from "@/lib/formatMetrics"

const ONBOARDING_KEY = "fse_thesis_onboarding_dismissed"

export function weaveAttribution(z: WeaveZ | null | undefined): string {
  if (!z) return "weave inputs unknown"
  const fmt = (v: number | null, label: string) =>
    v === null ? `${label} ?` : `${label} ${v >= 0 ? "+" : ""}${v.toFixed(1)}σ`
  return [fmt(z.z_rd, "RD"), fmt(z.z_quality, "Qual"), fmt(z.z_valuation, "Val"), fmt(z.z_momentum, "Mom")].join(" · ")
}

/** Split ranked rows into the three strata. Pure — unit-testable. */
export function splitStrata(
  rows: RankedRow[],
  stanceByTicker: Map<string, StanceListRow>
): { cleared: RankedRow[]; nearMisses: { row: RankedRow; blocker: string }[]; weave: RankedRow[] } {
  const cleared: RankedRow[] = []
  const nearMisses: { row: RankedRow; blocker: string }[] = []
  const weave: RankedRow[] = []
  for (const row of rows) {
    const stance = stanceByTicker.get(row.ticker)
    if (stance?.stance === "BUY") {
      cleared.push(row)
    } else if (stance && stance.blockers.length === 1) {
      nearMisses.push({ row, blocker: stance.blockers[0] })
    } else {
      weave.push(row)
    }
  }
  weave.sort((a, b) => {
    const wa = a.weave_score ?? Number.NEGATIVE_INFINITY
    const wb = b.weave_score ?? Number.NEGATIVE_INFINITY
    return wb - wa || b.score - a.score
  })
  return { cleared, nearMisses, weave }
}

function FirstRunBanner() {
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(ONBOARDING_KEY) === "1"
    } catch {
      return true
    }
  })
  if (dismissed) return null
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-[12px] text-sky-950">
      <ol className="flex flex-wrap gap-x-5 gap-y-1">
        <li>
          <span className="font-semibold">1.</span> Theses clear gates — sealed math, fail-closed, no opinion.
        </li>
        <li>
          <span className="font-semibold">2.</span> You select cleared theses into a book.
        </li>
        <li>
          <span className="font-semibold">3.</span> The sizing bound is validated-evidence only — zero today, so capital sizing stays yours.
        </li>
      </ol>
      <button
        type="button"
        onClick={() => {
          try {
            localStorage.setItem(ONBOARDING_KEY, "1")
          } catch {
            /* private mode */
          }
          setDismissed(true)
        }}
        className="text-[11px] font-semibold text-sky-800 underline"
      >
        Got it
      </button>
    </div>
  )
}

function StratumHeader({ title, sub, count }: { title: string; sub: string; count: number }) {
  return (
    <div className="border-b border-border bg-neutral-50 px-3 py-2">
      <div className="text-sm font-semibold text-neutral-950">
        {title} <span className="text-neutral-500">({count})</span>
      </div>
      <p className="text-[11px] text-neutral-600">{sub}</p>
    </div>
  )
}

export function UniverseStrataView({
  rows,
  stanceByTicker,
  universeVersion,
  selectEnabled,
  selected,
  onToggle,
}: {
  rows: RankedRow[]
  stanceByTicker: Map<string, StanceListRow>
  universeVersion: string
  selectEnabled: boolean
  selected: Set<string>
  onToggle: (ticker: string) => void
}) {
  const { cleared, nearMisses, weave } = useMemo(
    () => splitStrata(rows, stanceByTicker),
    [rows, stanceByTicker]
  )

  return (
    <div className="space-y-4">
      <FirstRunBanner />

      {/* Stratum 1 — Cleared BUY theses */}
      <div className="rounded-xl border border-border bg-white">
        <StratumHeader
          title="Complete theses"
          sub="Every gate passed, every claim sealed — repriced × R&D-validated × survivable. Clearance, not an order."
          count={cleared.length}
        />
        {cleared.length === 0 ? (
          <div className="px-4 py-6 text-sm text-neutral-700" data-testid="honest-empty-state">
            <div className="font-semibold text-neutral-900">
              0 complete theses today — the gates are doing their job.
            </div>
            <p className="mt-1 text-[12px] text-neutral-600">
              Nothing below is a cleared thesis. The near-misses show exactly which gate blocks each
              candidate; the weave rank is ordering only.
            </p>
          </div>
        ) : (
          cleared.map((r, i) => (
            <BuyDenseRow
              key={r.ticker}
              r={r}
              displayRank={i + 1}
              stance={stanceByTicker.get(r.ticker)}
              selectEnabled={selectEnabled}
              selected={selected.has(r.ticker)}
              onToggle={() => onToggle(r.ticker)}
            />
          ))
        )}
      </div>

      {/* Stratum 2 — Near-misses */}
      <div className="rounded-xl border border-border bg-white">
        <StratumHeader
          title="Near-misses"
          sub="Exactly one gate blocking — the honest pipeline. The named blocker is the work left, not a loophole."
          count={nearMisses.length}
        />
        {nearMisses.length === 0 ? (
          <div className="px-4 py-4 text-[12px] text-neutral-600">No single-gate near-misses right now.</div>
        ) : (
          nearMisses.map(({ row, blocker }) => (
            <div key={row.ticker} className="flex flex-wrap items-center gap-2 border-t border-border/70 px-3 py-2 text-sm">
              <Link
                to={`/app/company/${row.ticker}?universe_version=${encodeURIComponent(universeVersion)}&tab=stance`}
                className="!text-black font-bold hover:underline"
              >
                {row.ticker}
              </Link>
              <span className="min-w-0 truncate text-[12px] text-neutral-700">{row.name || row.ticker}</span>
              <span className="rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                blocked: {blocker}
              </span>
              <span className="ml-auto text-[11px] tabular-nums text-neutral-600">
                MoS {formatPercent4(row.mos_live, true)} · vs target {formatPercent4(row.vs_median_pct, true)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Stratum 3 — Ranked by the weave */}
      <div className="rounded-xl border border-border bg-white">
        <StratumHeader
          title="Ranked by the weave"
          sub="Ordering only — not clearance and not a return claim. Weights declared in the sealed thesis contract, never fitted to history."
          count={weave.length}
        />
        {weave.length === 0 ? (
          <div className="px-4 py-4 text-[12px] text-neutral-600">No further names in this universe.</div>
        ) : (
          weave.map((r, i) => (
            <div key={r.ticker} className="flex flex-wrap items-center gap-2 border-t border-border/70 px-3 py-2 text-sm">
              <span className="w-6 text-right text-[11px] tabular-nums text-neutral-500">{i + 1}</span>
              <Link
                to={`/app/company/${r.ticker}?universe_version=${encodeURIComponent(universeVersion)}`}
                className="!text-black font-bold hover:underline"
              >
                {r.ticker}
              </Link>
              <span className="min-w-0 truncate text-[12px] text-neutral-700">{r.name || r.ticker}</span>
              {r.weave_partial ? (
                <span
                  className="rounded border border-neutral-300 bg-neutral-100 px-1.5 py-0.5 text-[9px] font-medium text-neutral-600"
                  title="At least one weave family is unknown and contributed 0 — the rank is on partial data."
                >
                  partial data
                </span>
              ) : null}
              <span className="ml-auto text-[10px] tabular-nums text-neutral-600" title="Per-family weave attribution (robust z-scores).">
                {weaveAttribution(r.weave_z)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
