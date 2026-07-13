/**
 * PATH: frontend/src/components/research/PriceChart.tsx
 * PURPOSE: Day-by-day price chart with the paper's fixed fair-value guide
 * (low / median=price-target / high) as horizontal overlays. Labels stay in
 * the legend/cards so close lenses never collide on the plot.
 */
import { useEffect, useMemo, useRef, useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { getPriceHistory, type PriceHistoryResponse, type ValuationRange } from "@/lib/api/universe"
import { formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

const fmtPx = (v: number) => formatUsd4(v)

/** Annualized rate if the live→median gap closes over N years: (1+gap)^(1/N) − 1 */
export function annualizedClose(gap: number | null | undefined, years: number): string | null {
  if (gap === null || gap === undefined || !Number.isFinite(gap) || gap <= -0.999) return null
  const rate = Math.pow(1 + gap, 1 / years) - 1
  return formatPercent4(rate, true)
}

export function PriceChart({
  ticker,
  range,
  years = 3,
}: {
  ticker: string
  range?: ValuationRange | null
  years?: number
}) {
  const [data, setData] = useState<PriceHistoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setData(null)
    setError(null)
    void getPriceHistory(ticker, years, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setData(result)
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setError(String(e))
      })
    return () => controller.abort()
  }, [ticker, years])

  const bars = useMemo(
    () =>
      (data?.bars || []).map((b) => ({
        date: b.date,
        close: b.close,
        label: b.date.slice(0, 7),
      })),
    [data]
  )

  if (error) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Price history unavailable: {error}
      </div>
    )
  }
  if (!data) {
    return (
      <div className="rounded-xl border border-border bg-white p-8 text-center text-sm text-neutral-600">
        Loading price history…
      </div>
    )
  }

  const lo = range?.fair_px_lo ?? null
  const med = range?.fair_px_med ?? null
  const hi = range?.fair_px_hi ?? null
  const live = range?.price_live ?? data.last
  const gap = range?.gap_to_median ?? (med && live ? med / live - 1 : null)

  return (
    <div className="rounded-xl border border-border bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-black">Price · {years}y daily</h3>
          <p className="text-[11px] text-neutral-600">
            Current price overlay: adjusted closes from {data.price_source || data.source}
            {data.price_as_of ? ` as of ${data.price_as_of}` : ""}.
            {data.cache_stale ? " Cache is stale." : ""} Green line = frozen price target (median).
            {range?.fair_value_source ? ` ${range.fair_value_source} is fixed.` : " Guide is fixed."}
          </p>
        </div>
        <div className="text-right text-[11px] text-neutral-700">
          Last <b className="text-black">{fmtPx(data.last)}</b>
          <span className="text-neutral-400">
            {" "}
            · {data.start.slice(0, 7)} → {data.end.slice(0, 7)}
          </span>
        </div>
      </div>

      <div className="mt-3 h-56 sm:h-72">
        <ResponsiveContainer>
          <LineChart data={bars} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} minTickGap={48} interval="preserveStartEnd" />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => formatUsd4(v)}
              tick={{ fontSize: 10 }}
              width={44}
            />
            <Tooltip
              formatter={(v: number | string) => (typeof v === "number" ? fmtPx(v) : v)}
              labelFormatter={(l) => String(l)}
            />
            <Line
              type="monotone"
              dataKey="close"
              name="Price"
              stroke="#0f172a"
              dot={false}
              strokeWidth={1.75}
              isAnimationActive={false}
            />
            {/* Guide lines only — no on-plot text (close lenses collide) */}
            {hi != null && <ReferenceLine y={hi} stroke="#d97706" strokeDasharray="4 3" strokeWidth={1} />}
            {med != null && <ReferenceLine y={med} stroke="#059669" strokeWidth={2} />}
            {lo != null && <ReferenceLine y={lo} stroke="#34d399" strokeDasharray="4 3" strokeWidth={1} />}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-neutral-700">
        <span>
          <span className="mr-1 inline-block h-0.5 w-4 bg-slate-900 align-middle" /> Price
        </span>
        {med != null && (
          <span>
            <span className="mr-1 inline-block h-0.5 w-4 bg-emerald-600 align-middle" /> Target {fmtPx(med)}
          </span>
        )}
        {lo != null && (
          <span>
            <span className="mr-1 inline-block h-0.5 w-4 border-t border-dashed border-emerald-400 align-middle" />{" "}
            Low {fmtPx(lo)}
          </span>
        )}
        {hi != null && (
          <span>
            <span className="mr-1 inline-block h-0.5 w-4 border-t border-dashed border-amber-500 align-middle" />{" "}
            High {fmtPx(hi)}
          </span>
        )}
      </div>

      {gap != null && med != null && live != null && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-lg bg-emerald-50 px-2.5 py-2">
            <div className="text-[9px] uppercase tracking-wide text-emerald-800">Target</div>
            <div className="text-lg font-semibold tabular-nums text-emerald-950">{fmtPx(med)}</div>
          </div>
          <div className="rounded-lg bg-neutral-50 px-2.5 py-2">
            <div className="text-[9px] uppercase tracking-wide text-neutral-500">Live</div>
            <div className="text-lg font-semibold tabular-nums text-black">{fmtPx(live)}</div>
            <div className={`text-[10px] font-medium ${gap >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
              {formatPercent4(gap, true)} vs target
            </div>
          </div>
          <div className="col-span-2 rounded-lg bg-sky-50 px-2.5 py-2">
            <div className="text-[9px] uppercase tracking-wide text-sky-900">If gap closes</div>
            <div className="mt-0.5 flex flex-wrap gap-x-3 text-sm tabular-nums">
              <span>
                1y <b>{annualizedClose(gap, 1)}</b>
              </span>
              <span>
                2y <b>{annualizedClose(gap, 2)}/yr</b>
              </span>
              <span>
                3y <b>{annualizedClose(gap, 3)}/yr</b>
              </span>
              <span>
                5y <b>{annualizedClose(gap, 5)}/yr</b>
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
