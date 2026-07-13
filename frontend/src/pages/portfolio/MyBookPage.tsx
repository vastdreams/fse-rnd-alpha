/**
 * PATH: frontend/src/pages/portfolio/MyBookPage.tsx
 * PURPOSE: Selection board — holdings, horizon returns, FP compare strip.
 */
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { loadSaasBundle, type SaasBundle, type SaasCompany } from "@/lib/api/saasPortfolio"
import { usePortfolioBucket } from "@/hooks/usePortfolioBucket"
import {
  equalWeightPortfolioStats,
  fmtMoney,
  fmtPct,
  livePrice,
  totalUpside,
} from "@/lib/portfolioReturns"
import { buildPriceGuides } from "@/lib/priceGuides"
import {
  modelHolding,
  modelTierLabel,
} from "@/lib/modelPortfolio"
import { companyIdentity } from "@/lib/companyIdentity"
import { filingOffering } from "@/lib/filingOfferings"
import { AUDIT_DATE, auditVerdictTone, model10Audit } from "@/lib/paperAudit"

export function MyBookPage() {
  const [bundle, setBundle] = useState<SaasBundle | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { bucket, clear, toggle } = usePortfolioBucket()

  useEffect(() => {
    loadSaasBundle()
      .then(setBundle)
      .catch((e) => setError(String(e)))
  }, [])

  // Auto-seeding Model 10 was removed (ship rule: books start empty; the
  // explicit "Load model 10" button below is the only, deliberate, path).

  const companies = useMemo(() => {
    if (!bundle) return [] as SaasCompany[]
    const by = Object.fromEntries(bundle.companies.map((c) => [c.ticker, c]))
    return bucket.map((t) => by[t]).filter(Boolean) as SaasCompany[]
  }, [bundle, bucket])

  const stats = useMemo(() => equalWeightPortfolioStats(companies), [companies])

  if (error) return <div className="p-6 text-rose-600">{error}</div>
  if (!bundle) {
    return <div className="flex h-64 items-center justify-center text-muted-foreground">Loading book…</div>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">My Book</h1>
          <p className="text-sm text-muted-foreground mt-1">
            A transparent 10-name research model, independently audited {AUDIT_DATE}: three
            paper-core names, WDAY on hold, and six watchlist names that each fail at least one
            paper gate. Equal 10% weights are a research convention — the tier badges are the signal.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {bucket.length > 0 && (
            <button type="button" onClick={clear} className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Holdings" value={String(stats.n)} sub={stats.n ? `${(stats.weight * 100).toFixed(0)}% each` : "Empty"} />
        <Card label="Avg valuation gap" value={fmtPct(stats.avgUpside, 0)} sub={`live price to valuation median · ${stats.nValued}/${stats.n} valued`} />
        <Card label="3y convergence rate" value={fmtPct(stats.avgCagr3y, 1)} sub="annualized if current median is reached" />
        <Card label="Median valuation gap" value={fmtPct(stats.medianMos, 0)} sub="valuation median ÷ live price − 1" />
      </div>

      <div className="rounded-xl border border-border bg-white p-5">
        <h2 className="font-semibold">How this portfolio is structured (audited {AUDIT_DATE})</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Structure
            title="Paper core · 3 names"
            body="FRSH, DOCU and PCTY pass the paper's full 12-condition filter with a positive live margin of safety, and their 10-K claims were verified verbatim. Strongest evidence — still not guaranteed buys."
          />
          <Structure
            title="On hold · 1 name"
            body="WDAY was a paper Tier 2 survivor, but at current prices its margin of safety is negative — its own kill criterion has fired. The paper protocol is hold off / trim until the price or the fundamentals change."
          />
          <Structure
            title="Watchlist · 6 names"
            body="MNDY, PAYC, NICE, DBX, APPF and BILL each fail at least one real paper gate (margin trend, growth, filing quality, live price, or a named carve-out). They are research leads, not core holdings — each row says exactly which gate fails."
          />
        </div>
        <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
          Equal 10% weights are a neutral research convention, not an optimized allocation, and
          watchlist status is not a buy rating. Rebalance only after checking current filings,
          valuation inputs, concentration, taxes, and your own risk capacity.
        </p>
      </div>

      {companies.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-white p-10 text-center">
          <p className="text-muted-foreground">No holdings yet.</p>
          <Link to="/app" className="mt-3 inline-block text-sm font-medium text-slate-900 hover:underline">
              Go to Investigate →
          </Link>
        </div>
      ) : (
        <>
          <div className="overflow-auto rounded-xl border border-border bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/50 text-[11px] uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2.5 text-left">Name</th>
                  <th className="px-3 py-2.5 text-left">Evidence tier</th>
                  <th className="px-3 py-2.5 text-left">Why included</th>
                  <th className="px-3 py-2.5 text-right">Price</th>
                  <th className="px-3 py-2.5 text-right">Valuation median</th>
                  <th className="px-3 py-2.5 text-right">Valuation gap</th>
                  <th className="px-3 py-2.5 text-right">3y annualized to current median</th>
                  <th className="px-3 py-2.5 text-right" />
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => {
                  const guides = buildPriceGuides(c)
                  const y3 = guides.years[2]
                  const holding = modelHolding(c.ticker)
                  const id = companyIdentity(c)
                  const audit = model10Audit(c.ticker)
                  return (
                  <tr key={c.ticker} className="border-t border-border/70 hover:bg-muted/20">
                    <td className="min-w-[240px] px-3 py-2.5">
                      <Link
                        to={`/app/legacy/company/${c.ticker}`}
                        className="!text-black font-bold underline-offset-2 hover:underline"
                      >
                        {c.ticker}
                      </Link>
                      <div className="mt-0.5 text-[11px] font-medium text-neutral-800">
                        {id.line}
                      </div>
                      <div className="mt-1 text-[11px] leading-snug text-neutral-700">
                        {holding?.basis || id.description}
                      </div>
                      {(() => {
                        const o = filingOffering(c.ticker)
                        if (!o) return null
                        return (
                          <div className="mt-1 text-[11px] text-neutral-700">
                            <span className="font-medium text-neutral-800">Products: </span>
                            {o.offerings.slice(0, 3).join(" · ")}
                            <span className="ml-1 text-neutral-400">
                              ({o.source_type === "10-K Item 1 Business" ? "10-K" : "pending 10-K"})
                            </span>
                          </div>
                        )
                      })()}
                      <div className="mt-0.5 text-[10px] text-neutral-600">
                        {holding ? "10% model weight" : "Personal selection"}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`inline-block rounded-md border px-2 py-1 text-[10px] font-medium ${
                          audit ? auditVerdictTone(audit.verdict) : "border-border bg-muted/40"
                        }`}
                        title={audit ? `${AUDIT_DATE} audit — ${audit.decidingGate}` : undefined}
                      >
                        {holding ? modelTierLabel(holding.tier) : "Personal selection"}
                      </span>
                    </td>
                    <td className="max-w-[280px] px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
                      {audit?.headline ||
                        holding?.basis ||
                        "Added manually; open the company brief to review the evidence chain."}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtMoney(livePrice(c))}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtMoney(c.fair_px_med)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums font-medium">
                      {fmtPct(totalUpside(c), 0)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {fmtPct(y3.mid, 1)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={() => toggle(c.ticker)}
                        className="text-xs text-muted-foreground hover:text-rose-600"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-muted-foreground">
            The three-year rate is not a forecast. It is the annualized price return required to move
            from today's price to today's median triangulated valuation over three years; dividends, taxes, and
            future estimate revisions are excluded.
          </p>
        </>
      )}
    </div>
  )
}

function Structure({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{body}</p>
    </div>
  )
}

function Card({
  label,
  value,
  sub,
  tone,
}: {
  label: string
  value: string
  sub: string
  tone?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-white p-4">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${tone || ""}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{sub}</div>
    </div>
  )
}
