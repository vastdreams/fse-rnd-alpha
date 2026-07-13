/**
 * PATH: frontend/src/components/portfolio/PriceGuidePanel.tsx
 * PURPOSE: Current DCF lenses, convergence math, and evidence-bounded research status.
 */
import type { SaasCompany } from "@/lib/api/saasPortfolio"
import {
  buildResearchGuideline,
  buildPriceGuides,
  researchStatusTone,
} from "@/lib/priceGuides"
import { fmtMoney, fmtPct, livePrice } from "@/lib/portfolioReturns"

export function PriceGuidePanel({ company }: { company: SaasCompany }) {
  const guides = buildPriceGuides(company)
  const status = buildResearchGuideline(company)
  const price = livePrice(company)

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Research status</div>
            <div className={`mt-2 inline-flex rounded-md border px-2.5 py-1 text-sm font-semibold ${researchStatusTone(status.action)}`}>
              {status.label}
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground">{status.summary}</p>
          </div>
          <div className="text-right text-sm tabular-nums">
            <div>Live {fmtMoney(price)}</div>
            <div className="text-muted-foreground">Gap to median {fmtPct(status.mos, 0)}</div>
          </div>
        </div>
        <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
          {status.reasons.map((r) => (
            <li key={r}>· {r}</li>
          ))}
        </ul>
        <div className="mt-4 grid gap-2 sm:grid-cols-3 text-sm">
          <Anchor label="Low lens" hint="Lowest triangulated model" value={status.valuationAnchors.conservative} price={price} />
          <Anchor label="Median lens" hint="Median triangulated model" value={status.valuationAnchors.median} price={price} />
          <Anchor label="High lens" hint="Highest triangulated model" value={status.valuationAnchors.high} price={price} />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-white p-5">
        <div className="mb-4">
          <div>
            <h2 className="font-semibold">What the horizon return means</h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">{guides.methodNote}</p>
          </div>
        </div>

        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border">
              <tr>
                <th className="py-2 pr-3 text-left font-medium">Horizon</th>
                <th className="py-2 px-3 text-right font-medium">To low lens</th>
                <th className="py-2 px-3 text-right font-medium">To median lens</th>
                <th className="py-2 px-3 text-right font-medium">To high lens</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/60 bg-muted/20">
                <td className="py-2.5 pr-3 font-medium">Paper-date valuation band</td>
                <td className="py-2.5 px-3 text-right tabular-nums">{fmtMoney(guides.today.low)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums">{fmtMoney(guides.today.mid)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums">{fmtMoney(guides.today.high)}</td>
              </tr>
              {guides.years.map((y) => (
                <tr key={y.year} className="border-b border-border/60">
                  <td className="py-2.5 pr-3 font-medium">{y.year}-year annualized return</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-medium">{fmtPct(y.low, 1)}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-medium">{fmtPct(y.mid, 1)}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-medium">{fmtPct(y.high, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed">
          Example: a 13.5% three-year median-lens return means the share price would need to compound
          by 13.5% per year for three years to move from today's price to today's median triangulated value.
          It does not mean the model predicts 13.5% every year.
        </p>
      </div>
    </div>
  )
}

function Anchor({
  label,
  hint,
  value,
  price,
}: {
  label: string
  hint: string
  value: number | null
  price: number | null
}) {
  const below = value != null && price != null && price <= value
  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-2">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{fmtMoney(value)}</div>
      <div className="text-[11px] text-muted-foreground">{hint}</div>
      <div className="mt-1 text-[11px] font-medium">
        {below ? "Live price is below this estimate" : "Live price is above this estimate"}
      </div>
    </div>
  )
}
