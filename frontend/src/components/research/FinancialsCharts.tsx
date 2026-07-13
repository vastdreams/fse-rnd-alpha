/**
 * PATH: frontend/src/components/research/FinancialsCharts.tsx
 * PURPOSE: Graphs over the as-reported Sharadar SF1 history — revenue & FCF
 * bars with margin lines, and a returns (ROIC/ROE/ROA) chart. Pure display of
 * reported values; nothing modeled.
 */
import { useEffect, useRef, useState } from "react"
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ErrorBanner } from "@/components/research/ErrorBanner"
import { getFinancials, type FinancialsResponse } from "@/lib/api/universe"

const fmtB = (v: number) => (Math.abs(v) >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : `${(v / 1e6).toFixed(0)}M`)
const fmtPctAxis = (v: number) => `${(v * 100).toFixed(0)}%`

export function FinancialsCharts({ ticker, years = 12 }: { ticker: string; years?: number }) {
  const [data, setData] = useState<FinancialsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setData(null)
    setError(null)
    getFinancials(ticker, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setData(result)
        }
      })
      .catch((e) => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        setData(null)
        setError(String(e))
      })
    return () => controller.abort()
  }, [ticker])

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!data) return null

  const rows = data.annual.slice(-years).map((r) => ({
    year: r.calendardate.slice(0, 4),
    revenue: r.revenue,
    fcf: r.fcf,
    grossmargin: r.grossmargin,
    netmargin: r.netmargin,
    roic: r.roic,
    roe: r.roe,
    roa: r.roa,
  }))
  if (rows.length < 2) return null

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">Revenue & free cash flow (reported)</h3>
        <div className="mt-2 h-56">
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tickFormatter={fmtB} tick={{ fontSize: 10 }} width={52} />
              <Tooltip formatter={(v: number | string) => (typeof v === "number" ? fmtB(v) : v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="revenue" name="Revenue" fill="#0f172a" radius={[2, 2, 0, 0]} />
              <Bar dataKey="fcf" name="FCF" fill="#10b981" radius={[2, 2, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">Margins & returns (reported)</h3>
        <div className="mt-2 h-56">
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tickFormatter={fmtPctAxis} tick={{ fontSize: 10 }} width={44} />
              <Tooltip formatter={(v: number | string) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line dataKey="grossmargin" name="Gross margin" stroke="#0f172a" dot={false} strokeWidth={2} />
              <Line dataKey="netmargin" name="Net margin" stroke="#6366f1" dot={false} strokeWidth={2} />
              <Line dataKey="roic" name="ROIC" stroke="#10b981" dot={false} strokeWidth={2} />
              <Line dataKey="roe" name="ROE" stroke="#f59e0b" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
