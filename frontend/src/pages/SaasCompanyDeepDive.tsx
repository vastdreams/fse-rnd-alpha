/**
 * PATH: frontend/src/pages/SaasCompanyDeepDive.tsx
 * PURPOSE: MedTwin entity deep-dive — left tabs: Overview | Valuation | FP | Gates | Reports.
 */
import { Link, useParams } from "react-router-dom"
import { useEffect, useState, type ReactNode } from "react"
import { loadSaasBundle, type SaasCompany } from "@/lib/api/saasPortfolio"
import { usePortfolioBucket } from "@/hooks/usePortfolioBucket"
import {
  fmtMoney,
  fmtPct,
  fmtUsdCompact,
  livePrice,
  mosLive,
  totalUpside,
} from "@/lib/portfolioReturns"
import { PriceGuidePanel } from "@/components/portfolio/PriceGuidePanel"
import { OfferingsPanel } from "@/components/portfolio/OfferingsPanel"
import { buildResearchGuideline, researchStatusTone } from "@/lib/priceGuides"
import { buildCompanyRead } from "@/lib/companyRead"
import { companyIdentity } from "@/lib/companyIdentity"
import {
  AUDIT_DATE,
  auditVerdictLabel,
  auditVerdictTone,
  model10Audit,
  paperStrictReplay,
} from "@/lib/paperAudit"

type Tab = "overview" | "offerings" | "guides" | "valuation" | "fp" | "gates" | "reports"

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "offerings", label: "Products (10-K)" },
  { id: "guides", label: "Price guides" },
  { id: "valuation", label: "Valuation" },
  { id: "fp", label: "First principles" },
  { id: "gates", label: "Paper gates" },
  { id: "reports", label: "Reports" },
]

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium tabular-nums">{value ?? "—"}</span>
    </div>
  )
}

export function SaasCompanyDeepDive() {
  const { ticker } = useParams<{ ticker: string }>()
  const [company, setCompany] = useState<SaasCompany | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("overview")
  const { has, toggle } = usePortfolioBucket()

  useEffect(() => {
    if (!ticker) return
    loadSaasBundle()
      .then((b) => {
        const c = b.companies.find((x) => x.ticker === ticker.toUpperCase())
        if (!c) setErr(`${ticker} not in Top-100 bundle`)
        else {
          setCompany(c)
          setTab("overview")
        }
      })
      .catch((e) => setErr(String(e)))
  }, [ticker])

  if (err) {
    return (
      <div className="p-6 space-y-2">
        <Link to="/app" className="text-sm text-slate-900 hover:underline">
          ← Investigate
        </Link>
        <div className="text-rose-600">{err}</div>
      </div>
    )
  }
  if (!company) {
    return <div className="p-8 text-muted-foreground">Loading {ticker}…</div>
  }

  const price = livePrice(company)
  const up = totalUpside(company)
  const mos = mosLive(company)
  const inBook = has(company.ticker)
  const g = company.gates
  const mf = company.mgmt_factors || {}
  const status = buildResearchGuideline(company)
  const companyRead = buildCompanyRead(company)
  const id = companyIdentity(company)
  const audit = model10Audit(company.ticker)
  const strict = paperStrictReplay(company)

  return (
    <div className="flex min-h-full flex-col lg:flex-row">
      {/* Left sectional nav — MedTwin patient detail analogue */}
      <aside className="lg:w-52 border-b lg:border-b-0 lg:border-r border-border bg-white shrink-0">
        <div className="p-4 border-b border-border">
          <Link to="/app" className="text-xs text-slate-900 hover:underline">
            ← Investigate
          </Link>
          <h1 className="mt-2 text-xl font-bold !text-black">{company.ticker}</h1>
          <p className="mt-1 text-xs font-medium leading-relaxed text-neutral-800">
            {id.line}
          </p>
          <p className="mt-1 text-[11px] leading-snug text-neutral-700">
            {id.description}
          </p>
          {company.paper_tier && (
            <p className="mt-1 text-[11px] uppercase text-amber-700">{company.paper_tier}</p>
          )}
          <button
            type="button"
            onClick={() => toggle(company.ticker)}
            className={`mt-3 w-full rounded-lg px-3 py-2 text-sm font-medium ${
              inBook ? "border border-slate-800 bg-slate-800 text-white" : "border border-border hover:bg-muted"
            }`}
          >
            {inBook ? "In My Book ✓" : "+ Add to My Book"}
          </button>
          <button
            type="button"
            onClick={() => setTab("guides")}
            className={`mt-2 w-full rounded-lg border px-3 py-2 text-left text-xs ${researchStatusTone(status.action)}`}
          >
            <div className="font-semibold">{status.label}</div>
            <div className="mt-0.5 line-clamp-2">{status.summary}</div>
          </button>
        </div>
        <nav className="p-2 flex lg:flex-col gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-2 text-left text-sm whitespace-nowrap ${
                tab === t.id
                  ? "bg-slate-200 text-slate-950 font-medium"
                  : "text-muted-foreground hover:bg-muted"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="flex-1 p-4 sm:p-6 space-y-5 max-w-4xl">
        {/* Always-visible metric strip */}
        <div className="grid gap-2 sm:grid-cols-4">
          <Metric label="Live price" value={fmtMoney(price)} />
          <Metric label="Valuation median" value={fmtMoney(company.fair_px_med)} />
          <Metric label="Gap to valuation median" value={fmtPct(up, 0)} />
          <Metric label="Margin vs median" value={fmtPct(mos, 0)} />
        </div>

        {tab === "overview" && (
          <section className="space-y-4">
            {audit && (
              <div className={`rounded-xl border p-5 ${auditVerdictTone(audit.verdict)}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-semibold">{auditVerdictLabel(audit.verdict)}</h2>
                  <span className="text-[11px] font-medium">AI audit · {AUDIT_DATE}</span>
                </div>
                <p className="mt-2 text-sm leading-relaxed">{audit.headline}</p>
                <p className="mt-1 text-xs font-medium">Deciding gate: {audit.decidingGate}</p>
                {audit.flags.length > 0 && (
                  <ul className="mt-3 space-y-1.5 text-xs leading-relaxed">
                    {audit.flags.map((f) => (
                      <li key={f} className="flex gap-2">
                        <span aria-hidden>•</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <OfferingsPanel ticker={company.ticker} filingUrl={company.filing_url} />
            <PriceGuidePanel company={company} />
            <div className="rounded-xl border border-border bg-white p-5">
              <h2 className="font-semibold">Investment read</h2>
              <p className="mt-2 text-sm leading-relaxed">{companyRead.conclusion}</p>
              <div className="mt-5 grid gap-5 md:grid-cols-2">
                <ReadList title="Why it qualifies for research" items={companyRead.whyItQualifies} />
                <ReadList title="What could break the case" items={companyRead.whatCouldBreak} />
              </div>
              <div className="mt-5 border-t border-border pt-4">
                <ReadList title="What to check next" items={companyRead.nextChecks} />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-white p-4 space-y-1">
                <h3 className="font-medium mb-2">Quality</h3>
                <Row label="Rev CAGR" value={company.rev_cagr_pct != null ? `${company.rev_cagr_pct.toFixed(1)}%` : "—"} />
                <Row label="FCF margin" value={company.fcfm_sbc_l != null ? `${(company.fcfm_sbc_l * 100).toFixed(1)}%` : "—"} />
                <Row label="Rule of 40" value={company.rule40_sbc_l != null ? fmtPct(company.rule40_sbc_l, 0) : "—"} />
                <Row label="R&D productivity" value={company.rd_prod != null ? company.rd_prod.toFixed(2) : "—"} />
                <Row label="Intangible score" value={company.intangible_score} />
              </div>
              <div className="rounded-xl border border-border bg-white p-4 space-y-1">
                <h3 className="font-medium mb-2">Size</h3>
                <Row label="Market cap" value={fmtUsdCompact(company.live_marketcap_usd ?? company.marketcap_usd)} />
                <Row label="Revenue" value={fmtUsdCompact(company.revenue_usd)} />
                <Row label="Quadrant" value={company.quadrant} />
                <Row label="Paper tier" value={company.paper_tier || "—"} />
              </div>
            </div>
          </section>
        )}

        {tab === "offerings" && (
          <OfferingsPanel ticker={company.ticker} filingUrl={company.filing_url} />
        )}

        {tab === "guides" && <PriceGuidePanel company={company} />}

        {tab === "valuation" && (
          <section className="rounded-xl border border-border bg-white p-5 space-y-1">
            <h2 className="font-semibold mb-2">Triangulated valuation</h2>
            <p className="mb-4 text-xs leading-relaxed text-muted-foreground">
              Low, median, and high are the range across owner-earnings DCF,
              normalized-margin DCF, and a peer-multiple model. They are not three
              independent DCF scenarios.
            </p>
            {company.fair_px_lo != null && company.fair_px_hi != null && (
              <div className="mb-4 rounded-lg bg-muted/40 p-3 text-sm">
                Fair band: {fmtMoney(company.fair_px_lo)} → {fmtMoney(company.fair_px_med)} →{" "}
                {fmtMoney(company.fair_px_hi)}
              </div>
            )}
            {company.ev_dcf_fcf != null &&
              company.ev_dcf_norm != null &&
              company.ev_dcf_fcf === company.ev_dcf_norm && (
                <div className="mb-4 rounded-lg border border-rose-300 bg-rose-50 p-3 text-xs leading-relaxed text-rose-950">
                  Data flag ({AUDIT_DATE} audit): the two DCF models are identical in this bundle,
                  which two independent models cannot legitimately be. Treat the low band as
                  unverified until the bundle is rebuilt.
                </div>
              )}
            <Row label="Upside to mid" value={fmtPct(up, 1)} />
            <Row label="WACC" value={company.wacc != null ? `${(company.wacc * 100).toFixed(1)}%` : "—"} />
            <Row label="Implied growth" value={company.impl_g_l != null ? `${(company.impl_g_l * 100).toFixed(1)}%` : "—"} />
            <Row
              label="Realised − implied growth"
              value={company.impl_vs_realised != null ? `${(company.impl_vs_realised * 100).toFixed(1)} pp` : "—"}
            />
            <Row label="EV DCF (FCF)" value={company.ev_dcf_fcf != null ? `$${(company.ev_dcf_fcf / 1e9).toFixed(2)}B` : "—"} />
            <Row label="EV DCF (norm)" value={company.ev_dcf_norm != null ? `$${(company.ev_dcf_norm / 1e9).toFixed(2)}B` : "—"} />
            <Row label="SBC % rev" value={company.sbc_pct_l != null ? `${(company.sbc_pct_l * 100).toFixed(1)}%` : "—"} />
            <Row label="Dilution" value={company.dilution_ann != null ? `${(company.dilution_ann * 100).toFixed(1)}%` : "—"} />
            <div className="mt-4 rounded-lg border border-border bg-muted/20 p-4 text-sm">
              <div className="font-medium">Do not read a horizon percentage as a forecast</div>
              <p className="mt-1 leading-relaxed text-muted-foreground">
                It is the annualized price return required for today's live price to reach one of
                today's valuation estimates after that many years. Open Price guides to compare the low,
                median, and high lenses over 1, 2, and 3 years.
              </p>
            </div>
          </section>
        )}

        {tab === "fp" && (
          <section className="space-y-4">
            <div className="rounded-xl border border-border bg-white p-5 space-y-1">
              <h2 className="font-semibold mb-2">First-principles overlay</h2>
              <Row label="FP overlay present" value={company.fp_overlay ? "Yes" : "No"} />
              <Row label="Overlay coverage/status" value={company.mgmt_score || "—"} />
              <Row label="Cash trajectory" value={String(mf.cash_trajectory ?? "—")} />
              <Row label="Dilution drag" value={String(mf.dilution_drag ?? "—")} />
              <Row label="SBC intensity" value={String(mf.sbc_intensity ?? "—")} />
              <Row
                label={retentionLabel(mf.nrr_kind)}
                value={
                  mf.nrr_disclosed != null && mf.nrr_disclosed !== false
                    ? `${typeof mf.nrr_operator === "string" ? mf.nrr_operator : ""}${formatRatio(mf.nrr_disclosed)}`
                    : mf.nrr_operator != null
                      ? formatRatio(mf.nrr_operator)
                      : "missing / not disclosed"
                }
              />
              <Row
                label="Top-customer concentration"
                value={
                  mf.concentration_top10 != null && mf.concentration_top10 !== false
                    ? formatRatio(mf.concentration_top10)
                    : "missing / not disclosed"
                }
              />
              <Row
                label="10-K AI risk extraction"
                value={
                  mf.has_10k_ai_risk === true
                    ? "Risk language extracted"
                    : mf.has_10k_ai_risk === false
                      ? "No matched excerpt"
                      : "Not examined / unknown"
                }
              />
              <Row label="Intangible score" value={company.intangible_score} />
            </div>
            {company.mgmt_note && (
              <div className="rounded-xl border border-border bg-white p-5">
                <h3 className="text-xs uppercase text-muted-foreground">Management note</h3>
                <p className="mt-2 text-sm leading-relaxed">{company.mgmt_note}</p>
              </div>
            )}
            {company.kill_criterion && (
              <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-5">
                <h3 className="text-xs uppercase text-amber-800">Kill criterion</h3>
                <p className="mt-2 text-sm leading-relaxed">{company.kill_criterion}</p>
              </div>
            )}
          </section>
        )}

        {tab === "gates" && (
          <section className="space-y-4">
            <div
              className={`rounded-xl border p-5 ${
                strict.pass
                  ? "border-emerald-700 bg-emerald-50"
                  : "border-amber-700 bg-amber-50"
              }`}
            >
              <h2 className="font-semibold">
                Paper's full Table-20 filter (all 12 conditions): {strict.pass ? "PASS" : "FAIL"}
              </h2>
              <p className="mt-1 text-xs leading-relaxed text-neutral-800">
                Replayed from raw fields, independent of the screening flags below. This is the
                filter the paper actually used to pick its four survivors.
              </p>
              {strict.failures.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm">
                  {strict.failures.map((f) => (
                    <li key={f} className="flex gap-2">
                      <span className="font-mono text-[10px] mt-1">FAIL</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              )}
              {strict.notEvaluable.length > 0 && (
                <ul className="mt-2 space-y-1 text-sm text-neutral-700">
                  {strict.notEvaluable.map((f) => (
                    <li key={f} className="flex gap-2">
                      <span className="font-mono text-[10px] mt-1">N/A</span>
                      <span>{f} — the paper treats missing data as a fail.</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-border bg-white p-5">
              <h2 className="font-semibold">Paper snapshot and live-price gates</h2>
              <p className="mb-3 mt-1 text-xs leading-relaxed text-muted-foreground">
                Operating gates and paper tiers are the 31 March 2026 research snapshot. Rows marked
                “live” recompute only the price-dependent gate using the latest price. “Relaxed core
                screen” is 6 of the paper's 12 conditions — wider than the strict filter above.
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {(
                  [
                    [g.g1_saas_universe, "G1 SaaS universe (ex payments)"],
                    [g.g2_fcf_positive, "G2 FCF-positive"],
                    [g.g3_base_mos_positive, "G3 paper-date MoS > 0"],
                    [g.g3_base_mos_positive_live ?? false, "G3 live-price MoS > 0"],
                    [g.g4_core_exposed_incumbent, "G4 Exposed incumbent (core)"],
                    [g.g5_improving_cash, "G5 Improving SBC-FCF margin"],
                    [g.g5_moat_quality, "G5 Moat (R&D prod / Rule-40)"],
                    [g.core_thesis_path, "Relaxed core screen · paper date"],
                    [g.core_thesis_path_live ?? false, "Relaxed core screen · live price"],
                    [g.research_longlist, "Research long-list · paper date"],
                    [g.research_longlist_live ?? false, "Research long-list · live price"],
                  ] as const
                ).map(([ok, label]) => (
                  <div
                    key={label}
                    className={`rounded-lg border px-3 py-2 text-sm ${
                      ok
                        ? "border-slate-400 bg-slate-100 text-slate-950"
                        : "border-border bg-muted/30 text-muted-foreground"
                    }`}
                  >
                    <span className="font-mono text-[10px] mr-2">{ok ? "PASS" : "FAIL"}</span>
                    {label}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {tab === "reports" && (
          <section className="space-y-4">
            <div className="rounded-xl border border-border bg-white p-5">
              <h2 className="font-semibold mb-2">Filings & excerpts</h2>
              {company.filing_url ? (
                <a
                  href={company.filing_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
                >
                  Open linked 10-K on SEC →
                </a>
              ) : (
                <p className="text-sm text-muted-foreground">No filing URL in bundle for this name.</p>
              )}
              {company.accession && (
                <p className="mt-2 text-xs text-muted-foreground">Accession: {company.accession}</p>
              )}
            </div>
            <div className="rounded-xl border border-border bg-white p-5">
              <h3 className="text-xs uppercase text-muted-foreground">AI risk excerpt (10-K)</h3>
              {company.ai_risk_excerpt ? (
                <p className="mt-3 text-sm leading-relaxed whitespace-pre-wrap">{company.ai_risk_excerpt}</p>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  No AI-risk excerpt extracted for this name yet. This means the
                  current extraction has no matched evidence—not that the filing has
                  no AI-related risk.
                </p>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Deep narrative underwriting (FRSH / DOCU / PCTY / WDAY) lives in the gated watchlist FP
              deep-dive docs on the research site.
            </p>
          </section>
        )}

        <p className="text-xs text-muted-foreground">Not investment advice.</p>
      </div>
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-border bg-white px-3 py-3">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${tone || ""}`}>{value}</div>
    </div>
  )
}

function ReadList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      <ul className="mt-2 space-y-2 text-sm leading-relaxed">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span aria-hidden className="mt-1 text-muted-foreground">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Filings disclose different retention metrics; naming them prevents a gross
 * or floor figure from reading as NRR (the WDAY audit finding).
 */
function retentionLabel(kind: unknown): string {
  if (kind === "net_dollar") return "Net dollar retention (disclosed)"
  if (kind === "gross") return "Gross revenue retention (disclosed — not NRR)"
  if (kind === "annual_revenue") return "Annual revenue retention (disclosed floor)"
  return "Retention disclosed"
}

function formatRatio(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value ?? "—")
  return value >= -1 && value <= 1 ? `${(value * 100).toFixed(0)}%` : String(value)
}
