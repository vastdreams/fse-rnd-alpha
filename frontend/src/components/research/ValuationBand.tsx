/**
 * PATH: frontend/src/components/research/ValuationBand.tsx
 * PURPOSE: Clean fair-value guide — numbers in cards (never overlapping
 * absolute labels), a simple positional band, and a return window for
 * expectation control. Median = research price target.
 */
import type { ValuationRange } from "@/lib/api/universe"
import { annualizedClose } from "@/components/research/PriceChart"
import { formatPercent4, formatUsd4 } from "@/lib/formatMetrics"
import { computeSellCeiling, fmtSellAnn, fmtSellUpside } from "@/lib/sellCeiling"

const fmt = formatUsd4

export function ValuationBand({
  range,
  mosLive,
}: {
  range: ValuationRange
  mosLive?: number | null
}) {
  const { fair_px_lo: lo, fair_px_med: med, fair_px_hi: hi, price_live: live, price_snapshot: snap } =
    range
  if (lo === null || med === null || hi === null) {
    return range.invalid_band ? (
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        Fair-value band unavailable: the frozen research record does not contain ordered positive low, median,
        and high lenses.
      </div>
    ) : null
  }

  const marks = [
    live != null ? { v: live, key: "live" } : null,
    snap != null ? { v: snap, key: "snap" } : null,
    { v: lo, key: "lo" },
    { v: med, key: "med" },
    { v: hi, key: "hi" },
  ].filter(Boolean) as { v: number; key: string }[]

  const min = Math.min(...marks.map((m) => m.v)) * 0.85
  const max = Math.max(...marks.map((m) => m.v)) * 1.1
  const x = (v: number) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))
  const gap = range.gap_to_median
  const extremeMos = mosLive != null && mosLive > 1
  const sell = computeSellCeiling({
    fair_px_lo: lo,
    fair_px_med: med,
    fair_px_hi: hi,
    price_live: live,
  })

  return (
    <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-black">Fair-value guide</h3>
        <div className="flex flex-wrap items-center gap-2">
          {extremeMos && (
            <span
              className="rounded border border-amber-400 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-950"
              title="MoS > 100% — verify DCF inputs before underwriting"
            >
              MoS {formatPercent4(mosLive)} — verify DCF
            </span>
          )}
          <span className="text-[10px] text-neutral-500">
            {range.fair_value_source || "Fixed research lenses"} · quote moves, guide does not
          </span>
        </div>
      </div>

      {sell.sell_ceil != null && (
        <div
          className={`mt-3 rounded-lg border px-3 py-2.5 ${
            sell.zone === "past_ceiling"
              ? "border-amber-300 bg-amber-50"
              : sell.zone === "in_upper_band"
                ? "border-sky-200 bg-sky-50"
                : "border-emerald-300 bg-emerald-50"
          }`}
          title={sell.note}
        >
          <div className="text-[10px] font-semibold uppercase tracking-wide text-neutral-700">
            Auto-sell ceiling (hold exit)
          </div>
          <div className="mt-1 flex flex-wrap items-end gap-x-4 gap-y-1">
            <div>
              <div className="text-2xl font-semibold tabular-nums text-black">{formatUsd4(sell.sell_ceil)}</div>
              <div className="text-[10px] text-neutral-600">
                {sell.lens === "median"
                  ? "at median price target"
                  : sell.zone === "past_ceiling"
                    ? "through high lens"
                    : "trim at high lens"}
              </div>
            </div>
            {sell.zone !== "past_ceiling" && (
              <>
                <div>
                  <div className="text-sm font-semibold tabular-nums text-neutral-900">
                    {fmtSellUpside(sell.upside_to_ceil)} left
                  </div>
                  <div className="text-[10px] text-neutral-600">
                    {sell.horizon_years != null ? `${sell.horizon_years}y hold horizon` : "horizon n/a"}
                  </div>
                </div>
                {sell.remaining_ann != null && (
                  <div>
                    <div className="text-sm font-semibold tabular-nums text-emerald-900">
                      ≈{fmtSellAnn(sell.remaining_ann)}
                    </div>
                    <div className="text-[10px] text-neutral-600">if gap to ceil closes</div>
                  </div>
                )}
              </>
            )}
          </div>
          <p className="mt-1.5 text-[10px] leading-snug text-neutral-700">{sell.note}</p>
        </div>
      )}

      {/* Numbers live HERE — never as overlapping labels on the band */}
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2.5">
          <div className="text-[10px] font-medium uppercase tracking-wide text-emerald-800">Price target</div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums text-emerald-950">{fmt(med)}</div>
          <div className="text-[10px] text-emerald-800">median lens</div>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2.5">
          <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">
            {range.price_as_of ? "Quote (as-of)" : "Quote"}
          </div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums text-black">{fmt(live)}</div>
          <div className="text-[10px] text-neutral-500">
            {range.price_source || "current quote"}
            {range.price_as_of ? ` · ${range.price_as_of}` : ""}
          </div>
          {gap != null ? (
            <div className={`text-[10px] font-semibold ${gap >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
              {formatPercent4(gap, true)} vs target
            </div>
          ) : (
            <div className="text-[10px] text-neutral-500">
              gap unavailable
            </div>
          )}
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2.5">
          <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">Low lens</div>
          <div className="mt-0.5 text-xl font-semibold tabular-nums text-black">{fmt(lo)}</div>
          <div className="text-[10px] text-neutral-500">conservative</div>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2.5">
          <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">High lens</div>
          <div className="mt-0.5 text-xl font-semibold tabular-nums text-black">{fmt(hi)}</div>
          <div className="text-[10px] text-neutral-500">optimistic</div>
        </div>
      </div>

      {/* Band: ticks only, no text labels (avoids collision when lenses are close) */}
      <div className="relative mt-5 h-3">
        <div className="absolute inset-y-1 left-0 right-0 rounded-full bg-neutral-100" />
        <div
          className="absolute inset-y-1 rounded-full bg-emerald-200"
          style={{ left: `${x(lo)}%`, width: `${Math.max(1, x(hi) - x(lo))}%` }}
        />
        <div
          className="absolute top-0 h-3 w-0.5 bg-emerald-700"
          style={{ left: `${x(lo)}%` }}
          title={`Low ${fmt(lo)}`}
        />
        <div
          className="absolute top-0 h-3 w-1 bg-emerald-900"
          style={{ left: `${x(med)}%` }}
          title={`Target ${fmt(med)}`}
        />
        <div
          className="absolute top-0 h-3 w-0.5 bg-amber-600"
          style={{ left: `${x(hi)}%` }}
          title={`High ${fmt(hi)}`}
        />
        {live != null && (
          <div
            className="absolute -top-1 h-5 w-1.5 rounded-sm bg-black"
            style={{ left: `${x(live)}%` }}
            title={`Quote ${fmt(live)}`}
          />
        )}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-neutral-600">
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-sm bg-black align-middle" /> Quote {fmt(live)}
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 bg-emerald-900 align-middle" /> Target {fmt(med)}
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-0.5 bg-emerald-700 align-middle" /> Low {fmt(lo)}
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-0.5 bg-amber-600 align-middle" /> High {fmt(hi)}
        </span>
        {snap != null && <span className="text-sky-700">Snapshot {fmt(snap)}</span>}
      </div>

      {gap != null && (
        <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2.5">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-sky-900">
            Return window if gap to price target closes
          </div>
          <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(
              [
                [1, "1 year"],
                [2, "2 years"],
                [3, "3 years"],
                [5, "5 years"],
              ] as const
            ).map(([n, label]) => (
              <div key={n} className="rounded-md bg-white/70 px-2 py-1.5 text-center">
                <div className="text-[10px] text-sky-800">{label}</div>
                <div
                  className={`text-base font-semibold tabular-nums ${
                    gap >= 0 ? "text-emerald-800" : "text-rose-800"
                  }`}
                >
                  {annualizedClose(gap, n)}
                  {n > 1 ? <span className="text-[10px] font-normal">/yr</span> : null}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] leading-snug text-sky-900/80">
            One gap, annualized: <span className="font-mono">(target ÷ live)^(1/N) − 1</span>. Not separate
            forecasts. Expectation control against a fixed target.
          </p>
        </div>
      )}

      {range.zone && (
        <p className="mt-3 text-xs leading-relaxed text-neutral-700">
          Live sits <b>{range.zone}</b>
          {gap != null && (
            <>
              {" "}
              (<b>{formatPercent4(gap, true)}</b> from target)
            </>
          )}
          .
          {range.quadrant && <> Quadrant: {range.quadrant.replaceAll("_", " ")}.</>}
          {range.wacc != null && <> WACC {formatPercent4(range.wacc)}.</>}
          {range.rev_cagr != null && <> Revenue CAGR {formatPercent4(range.rev_cagr, true)}.</>}
        </p>
      )}
    </div>
  )
}
