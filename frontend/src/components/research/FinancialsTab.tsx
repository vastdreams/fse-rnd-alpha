/**
 * PATH: frontend/src/components/research/FinancialsTab.tsx
 * PURPOSE: Year-on-year financial statements + key ratios per company
 * (Yahoo-Finance-style tables, SimplyWallSt-style depth). All values are
 * as-reported Sharadar SF1 — never computed here beyond labelled YoY deltas.
 */
import { useEffect, useMemo, useRef, useState } from "react"
import { FinancialsCharts } from "@/components/research/FinancialsCharts"
import { getFinancials, type FinancialRow, type FinancialsResponse } from "@/lib/api/universe"
import { formatNumber4, formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

const fmtMoney = formatUsd4
const fmtPct = formatPercent4
const fmtX = formatNumber4

const yoyTone = (v: number | null | undefined): string =>
  v === null || v === undefined ? "text-neutral-400" : v >= 0 ? "text-emerald-700" : "text-rose-700"

type LineFmt = "money" | "pct" | "x" | "eps"

interface Line {
  label: string
  field: string
  fmt: LineFmt
  bold?: boolean
  indent?: boolean
  yoy?: boolean
}

const INCOME_LINES: Line[] = [
  { label: "Revenue", field: "revenue", fmt: "money", bold: true, yoy: true },
  { label: "Gross profit", field: "gp", fmt: "money", yoy: true },
  { label: "Operating expenses", field: "opex", fmt: "money", indent: true },
  { label: "R&D", field: "rnd", fmt: "money", indent: true, yoy: true },
  { label: "SG&A", field: "sgna", fmt: "money", indent: true },
  { label: "Operating income", field: "opinc", fmt: "money", bold: true, yoy: true },
  { label: "EBITDA", field: "ebitda", fmt: "money" },
  { label: "Net income", field: "netinc", fmt: "money", bold: true, yoy: true },
  { label: "Diluted EPS", field: "epsdil", fmt: "eps", yoy: true },
]

const CASHFLOW_LINES: Line[] = [
  { label: "Operating cash flow", field: "ncfo", fmt: "money", bold: true },
  { label: "Capex", field: "capex", fmt: "money", indent: true },
  { label: "Free cash flow", field: "fcf", fmt: "money", bold: true, yoy: true },
  { label: "Stock-based comp", field: "sbcomp", fmt: "money", indent: true },
]

const BALANCE_LINES: Line[] = [
  { label: "Total assets", field: "assets", fmt: "money", bold: true },
  { label: "Cash & equivalents", field: "cashnequsd", fmt: "money", indent: true },
  { label: "Total liabilities", field: "liabilities", fmt: "money" },
  { label: "Total debt", field: "debt", fmt: "money", indent: true },
  { label: "Shareholders' equity", field: "equity", fmt: "money", bold: true },
  { label: "Diluted shares", field: "shareswadil", fmt: "money" },
]

const RATIO_LINES: Line[] = [
  { label: "Gross margin", field: "grossmargin", fmt: "pct", bold: true },
  { label: "EBITDA margin", field: "ebitdamargin", fmt: "pct" },
  { label: "Net margin", field: "netmargin", fmt: "pct" },
  { label: "ROA", field: "roa", fmt: "pct", bold: true },
  { label: "ROE", field: "roe", fmt: "pct" },
  { label: "ROIC", field: "roic", fmt: "pct", bold: true },
  { label: "Debt / equity", field: "de", fmt: "x" },
  { label: "Current ratio", field: "currentratio", fmt: "x" },
  { label: "P/E", field: "pe", fmt: "x" },
  { label: "P/S", field: "ps", fmt: "x" },
  { label: "P/B", field: "pb", fmt: "x" },
  { label: "Dividend yield", field: "divyield", fmt: "pct" },
]

function fmtCell(fmt: LineFmt, v: number | null | undefined): string {
  if (fmt === "money") return fmtMoney(v)
  if (fmt === "pct") return fmtPct(v)
  if (fmt === "eps") return formatUsd4(v)
  return fmtX(v)
}

function StatementTable({ title, lines, rows }: { title: string; lines: Line[]; rows: FinancialRow[] }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-semibold text-neutral-950">{title}</h3>
      <div className="overflow-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-[11px] uppercase tracking-wide text-foreground/60">
            <tr>
              <th className="sticky left-0 z-10 bg-muted/50 px-3 py-2 text-left backdrop-blur">Line</th>
              {rows.map((r) => (
                <th key={r.calendardate} className="px-3 py-2 text-right whitespace-nowrap">
                  {r.calendardate.slice(0, 7)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <FragmentRow key={line.field} line={line} rows={rows} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FragmentRow({ line, rows }: { line: Line; rows: FinancialRow[] }) {
  const anyValue = rows.some((r) => r[line.field] !== null && r[line.field] !== undefined)
  if (!anyValue) return null
  return (
    <>
      <tr className="border-t border-border/70 hover:bg-muted/30">
        <td
          className={`sticky left-0 z-10 bg-white px-3 py-1.5 whitespace-nowrap ${
            line.bold ? "font-semibold text-black" : "text-neutral-800"
          } ${line.indent ? "pl-6" : ""}`}
        >
          {line.label}
        </td>
        {rows.map((r) => (
          <td
            key={r.calendardate}
            className={`px-3 py-1.5 text-right tabular-nums whitespace-nowrap ${
              line.bold ? "font-semibold text-black" : "text-neutral-800"
            }`}
          >
            {fmtCell(line.fmt, r[line.field] as number | null)}
          </td>
        ))}
      </tr>
      {line.yoy && (
        <tr className="bg-neutral-50/60">
          <td className="sticky left-0 z-10 bg-neutral-50/60 px-3 py-0.5 pl-6 text-[10px] text-neutral-500 whitespace-nowrap">
            YoY
          </td>
          {rows.map((r) => {
            const g = r[`derived_${line.field}_yoy`] as number | null | undefined
            return (
              <td key={r.calendardate} className={`px-3 py-0.5 text-right text-[10px] tabular-nums ${yoyTone(g)}`}>
                {g === null || g === undefined ? "" : formatPercent4(g, true)}
              </td>
            )
          })}
        </tr>
      )}
    </>
  )
}

export function FinancialsTab({ ticker }: { ticker: string }) {
  const [data, setData] = useState<FinancialsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [years, setYears] = useState<5 | 10 | 99>(10)
  const requestGenerationRef = useRef(0)

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setData(null)
    setError(null)
    void getFinancials(ticker, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setData(result)
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setError(String(e))
      })
    return () => controller.abort()
  }, [ticker])

  const rows = useMemo(() => (data ? data.annual.slice(-years) : []), [data, years])

  if (error)
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Financial statements unavailable for {ticker}: {error}
      </div>
    )
  if (!data) return <div className="p-8 text-center text-sm text-neutral-600">Loading financials…</div>

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-xs text-neutral-600">
          {data.n_years} fiscal years of current as-reported overlay · {data.source}
          {data.fetched_at ? ` · fetched ${String(data.fetched_at).slice(0, 10)}` : ""}
        </div>
        <div className="flex-1" />
        <div className="flex gap-1">
          {([5, 10, 99] as const).map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setYears(y)}
              className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
                years === y ? "border-black bg-black text-white" : "border-border bg-white text-black hover:bg-muted"
              }`}
            >
              {y === 99 ? "All" : `${y}y`}
            </button>
          ))}
        </div>
      </div>

      <FinancialsCharts ticker={ticker} years={years === 99 ? 30 : years} />

      <StatementTable title="Income statement (annual)" lines={INCOME_LINES} rows={rows} />
      <StatementTable title="Cash flow" lines={CASHFLOW_LINES} rows={rows} />
      <StatementTable title="Balance sheet" lines={BALANCE_LINES} rows={rows} />
      <StatementTable title="Key ratios & returns" lines={RATIO_LINES} rows={rows} />

      {data.quarterly.length > 0 && (
        <StatementTable title="Recent quarters (income)" lines={INCOME_LINES} rows={data.quarterly} />
      )}

      <p className="text-[11px] text-neutral-500">
        Current overlay from Sharadar SF1 (period end / filing date carried per column), shown separately
        from the frozen research vector. YoY rows are pure arithmetic on adjacent reported values — nothing
        here is modeled or imputed.
      </p>
    </div>
  )
}
