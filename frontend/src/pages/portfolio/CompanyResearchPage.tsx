/**
 * PATH: frontend/src/pages/portfolio/CompanyResearchPage.tsx
 * PURPOSE: Eight-tab company deep dive (Overview · Stance · Financials ·
 * Business · Research scores · Valuation · Audit · Memo) with sticky digest
 * strip and click-any-number → Audit drawer. Tab state lives in the URL.
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import { AuditDrawer } from "@/components/research/AuditDrawer"
import { ErrorBanner } from "@/components/research/ErrorBanner"
import { FinancialsCharts } from "@/components/research/FinancialsCharts"
import { FinancialsTab } from "@/components/research/FinancialsTab"
import { PriceChart } from "@/components/research/PriceChart"
import { StanceTab } from "@/components/research/StanceTab"
import { ValuationBand } from "@/components/research/ValuationBand"
import { addTickersToPrimaryBook } from "@/lib/addToBook"
import { softAddWarnings } from "@/lib/bookOps"
import {
  fmtVal,
  getAuditPack,
  getCompanyResearch,
  getMemos,
  gradeTone,
  runDcf,
  saveMemo,
  type CompanyResearch,
  type DcfInputs,
  type DcfOutputs,
  type MetricValue,
} from "@/lib/api/universe"
import {
  formatNumber4,
  formatPercent4,
  formatResearchMetric4,
  formatUsd4,
} from "@/lib/formatMetrics"

const TABS = ["overview", "stance", "financials", "business", "research", "valuation", "audit", "memo"] as const
type Tab = (typeof TABS)[number]
const TAB_LABELS: Record<Tab, string> = {
  overview: "Overview",
  stance: "Stance",
  financials: "Financials",
  business: "Business",
  research: "Research scores",
  valuation: "Valuation",
  audit: "Audit",
  memo: "Memo",
}
const DEFAULT_DCF_INPUTS: Partial<DcfInputs> = {
  growth: 0.12,
  wacc: 0.1,
  terminal_g: 0.03,
  target_margin: 0.2,
  net_cash_usd: 0,
}

export function CompanyResearchPage() {
  const { ticker = "" } = useParams<{ ticker: string }>()
  const [params, setParams] = useSearchParams()
  const tab = (TABS.includes(params.get("tab") as Tab) ? params.get("tab") : "overview") as Tab
  const requestedUniverseVersion = params.get("universe_version") || undefined
  const [data, setData] = useState<CompanyResearch | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [drawerAxis, setDrawerAxis] = useState<string | null>(null)
  const [bookMsg, setBookMsg] = useState<string | null>(null)
  const [addingBook, setAddingBook] = useState(false)
  const requestGenerationRef = useRef(0)

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setData(null)
    setError(null)
    setBookMsg(null)
    setAddingBook(false)
    void getCompanyResearch(ticker, requestedUniverseVersion, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setData(result)
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) setError(String(e))
      })
    return () => controller.abort()
  }, [ticker, requestedUniverseVersion])

  const appendSavedDcf = (run: {
    run_id: string
    inputs: DcfInputs
    outputs: DcfOutputs
    universe_version: string
  }) => {
    setData((current) => {
      if (
        !current ||
        current.universe_version !== run.universe_version ||
        current.vector.ticker.toUpperCase() !== run.inputs.ticker.toUpperCase() ||
        current.dcf_runs.some((existing) => existing.run_id === run.run_id)
      ) {
        return current
      }
      return {
        ...current,
        dcf_runs: [
          {
            run_id: run.run_id,
            scenario: run.inputs.scenario,
            inputs: run.inputs,
            outputs: run.outputs,
            engine_version: run.outputs.engine_version,
            created_at: new Date().toISOString(),
            universe_version: run.universe_version,
            visibility: "private",
          },
          ...current.dcf_runs,
        ],
      }
    })
  }

  const setTab = (t: Tab) => {
    const next = new URLSearchParams(params)
    next.set("tab", t)
    setParams(next, { replace: true })
  }

  const addToBook = async () => {
    if (!data) return
    const v = data.vector
    const generation = requestGenerationRef.current
    const universeVersion = data.universe_version
    const warnings = softAddWarnings(
      [v.ticker],
      new Map([
        [
          v.ticker,
          {
            completeness_grade: v.completeness.grade,
            retention: v.retention?.value ?? null,
            mos_live: v.mos_live?.value ?? null,
            freshness_ok: !v.completeness.stale,
            kill_active: v.kill_active,
          },
        ],
      ])
    )
    if (warnings.length) {
      const lines = warnings.map((w) => `${w.ticker}: ${w.reasons.join("; ")}`).join("\n")
      if (!window.confirm(`Soft warnings:\n\n${lines}\n\nAdd to book anyway?`)) return
    }
    setAddingBook(true)
    setBookMsg(null)
    setError(null)
    try {
      const res = await addTickersToPrimaryBook([v.ticker], universeVersion)
      if (generation !== requestGenerationRef.current) return
      if (!res.ok) {
        if ("breaches" in res && res.breaches) {
          setError(res.breaches.map((b) => b.detail).join(" · "))
        } else if ("error" in res) {
          setError(res.error)
        }
        return
      }
      setBookMsg(
        res.added
          ? `Added ${v.ticker} as an unallocated research candidate (${res.holdings.length} holdings).`
          : `${v.ticker} already in Book.`
      )
    } catch (e) {
      if (generation === requestGenerationRef.current) setError(String(e))
    } finally {
      if (generation === requestGenerationRef.current) setAddingBook(false)
    }
  }

  if (error && !data) {
    return (
      <div className="p-6">
        <ErrorBanner>{error}</ErrorBanner>
      </div>
    )
  }
  if (!data) return <div className="flex h-64 items-center justify-center text-neutral-600">Loading research…</div>

  const v = data.vector
  const open = (axis: string) => setDrawerAxis(axis)
  const stance = data.close_call_waterfall?.aggregate

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {bookMsg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          {bookMsg}{" "}
          <Link to="/app/book" className="font-semibold underline">
            Open Book
          </Link>
        </div>
      )}
      {/* Sticky digest strip */}
      <div className="sticky top-0 z-30 -mx-4 border-b border-border bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
          <div>
            <span className="text-xl font-bold text-black">{v.ticker}</span>
            {(data.profile?.name || data.identity?.name) && (
              <div className="text-[11px] leading-tight text-neutral-600">
                {data.profile?.name || data.identity?.name}
                {data.identity?.industry && <> · {data.identity.industry}</>}
                {data.identity?.size && <> · {data.identity.size.split(" - ")[1] || data.identity.size} cap</>}
              </div>
            )}
          </div>
          {stance && (
            <button
              type="button"
              onClick={() => setTab("stance")}
              className={`rounded-md border px-2 py-1 text-left ${
                stance.stance === "BUY"
                  ? "border-emerald-400 bg-emerald-50"
                  : stance.stance === "UNKNOWN"
                    ? "border-neutral-300 bg-neutral-50"
                    : "border-amber-300 bg-amber-50"
              }`}
              title="Open stance waterfall"
            >
              <span className="block text-[9px] uppercase tracking-wide text-neutral-500">Research stance</span>
              <span className="text-sm font-bold tabular-nums text-black">
                {stance.stance}
                {stance.horizon_years != null && (
                  <span className="ml-1 text-[11px] font-medium text-neutral-600">{stance.horizon_years}y</span>
                )}
              </span>
            </button>
          )}
          <Digit label="Vs price target" onClick={() => open("mos_live")} value={fmtVal(v.mos_live, true)} tone={num(v.mos_live) > 0 ? "text-emerald-700" : "text-rose-700"} />
          <Digit label="Retention" onClick={() => open("retention")} value={fmtVal(v.retention, true)} />
          <Digit label="R&D prod" onClick={() => open("rd_prod")} value={fmtVal(v.rd_prod)} />
          <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${gradeTone(v.completeness.grade)}`}>
            Completeness {v.completeness.grade}
          </span>
          {v.completeness.stale && (
            <span className="rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-900">
              STALE — fundamentals past SLA
            </span>
          )}
          {v.kill_active && (
            <span className="rounded border border-rose-300 bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">
              KILL CRITERION ACTIVE
            </span>
          )}
          <span className="text-[10px] text-neutral-500">
            {data.reviewer_passed === true ? "reviewer_passed" : data.reviewer_passed === false ? "review failed" : "review pending"}
          </span>
          <div className="flex-1" />
          <button
            type="button"
            disabled={addingBook}
            onClick={addToBook}
            className="min-h-11 rounded-lg bg-black px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
          >
            {addingBook ? "Adding…" : "Add to Book"}
          </button>
          <Link
            to={`/app/universe?mode=buy&universe_version=${encodeURIComponent(data.universe_version)}`}
            className="text-xs font-medium text-neutral-700 hover:underline"
          >
            ← Universe
          </Link>
        </div>
        {/* Tabs */}
        <div className="mt-2 flex flex-wrap gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1 text-xs font-medium capitalize ${
                tab === t ? "bg-black text-white" : "text-neutral-700 hover:bg-muted"
              }`}
            >
              {t === "stance" ? `Stance · ${stance?.stance ?? "Unknown"}` : TAB_LABELS[t]}
            </button>
          ))}
        </div>
      </div>

      {tab === "overview" && <OverviewTab data={data} open={open} goStance={() => setTab("stance")} />}
      {tab === "stance" && (
        <StanceTab
          waterfall={data.close_call_waterfall}
          dataMode={data.close_call_data_mode}
        />
      )}
      {tab === "financials" && <FinancialsTab ticker={v.ticker} />}
      {tab === "business" && <BusinessTab data={data} open={open} />}
      {tab === "research" && <ResearchTab data={data} open={open} />}
      {tab === "valuation" && (
        <ValuationTab data={data} open={open} onDcfSaved={appendSavedDcf} />
      )}
      {tab === "audit" && <AuditTab data={data} open={open} />}
      {tab === "memo" && (
        <MemoTab
          ticker={v.ticker}
          universeVersion={data.universe_version}
          availableCitationIds={vectorClaimIds(v)}
        />
      )}

      <p className="text-[11px] text-neutral-500">
        Research only — not investment advice. Click any number for its evidence trail.
      </p>

      {drawerAxis && (
        <AuditDrawer
          ticker={v.ticker}
          axis={drawerAxis}
          universeVersion={data.universe_version}
          onClose={() => setDrawerAxis(null)}
        />
      )}
    </div>
  )
}

const num = (m: MetricValue) => m.value ?? 0

function vectorClaimIds(vector: CompanyResearch["vector"]): string[] {
  return [
    ...new Set(
      Object.values(vector).flatMap((value) =>
        value &&
        typeof value === "object" &&
        "claim_ids" in value &&
        Array.isArray(value.claim_ids)
          ? value.claim_ids
          : []
      )
    ),
  ]
}

function Digit({ label, value, onClick, tone }: { label: string; value: string; onClick: () => void; tone?: string }) {
  return (
    <button type="button" onClick={onClick} className="text-left" title={`${label} — click for evidence`}>
      <span className="block text-[9px] uppercase tracking-wide text-neutral-500">{label}</span>
      <span className={`text-sm font-semibold tabular-nums underline decoration-dotted underline-offset-2 ${tone || "text-black"}`}>
        {value}
      </span>
    </button>
  )
}

function MetricCell({ label, m, pct, open, axis }: { label: string; m: MetricValue; pct?: boolean; open: (a: string) => void; axis: string }) {
  return (
    <button
      type="button"
      onClick={() => open(axis)}
      className="rounded-lg border border-border bg-white p-3 text-left hover:bg-muted/40"
      title="Click for evidence trail"
    >
      <div className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold tabular-nums ${m.value === null ? "text-neutral-400" : "text-black"}`}>
        {fmtVal(m, pct)}
      </div>
      <div className="text-[9px] text-neutral-500">
        {m.as_of_date ? `as-of ${m.as_of_date}` : "not disclosed / not computed"}
      </div>
    </button>
  )
}

function firstSentences(text: string, n = 2): string {
  const parts = text.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+/)
  if (parts.length <= n) return text.trim()
  return parts.slice(0, n).join(" ")
}

function OverviewTab({
  data,
  open,
  goStance,
}: {
  data: CompanyResearch
  open: (a: string) => void
  goStance: () => void
}) {
  const v = data.vector
  const p = data.profile
  const id = data.identity
  const stance = data.close_call_waterfall?.aggregate
  const change = p?.price_change
  const changePct = p?.price_change_pct
  const changeUp = change != null && change >= 0
  const facts: { label: string; value: ReactNode }[] = []
  if (p?.name || id?.name) facts.push({ label: "Company", value: p?.name || id?.name })
  if (p?.industry || id?.industry) facts.push({ label: "Industry", value: p?.industry || id?.industry })
  if (p?.sector || id?.sector) facts.push({ label: "Sector", value: p?.sector || id?.sector })
  if (p?.ceo) facts.push({ label: "CEO", value: p.ceo })
  if (p?.employees) facts.push({ label: "Employees", value: Number(p.employees).toLocaleString() })
  if (p?.ipo_date) facts.push({ label: "IPO", value: p.ipo_date })
  if (p?.website) {
    facts.push({
      label: "Website",
      value: (
        <a href={p.website} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">
          {p.website.replace(/^https?:\/\/(www\.)?/, "")}
        </a>
      ),
    })
  }
  if (p?.price_live != null) {
    facts.push({
      label: p.price_as_of ? "Quote (as-of)" : "Quote",
      value: (
        <span className="tabular-nums">
          <b className="text-black">{formatUsd4(p.price_live)}</b>
          {change != null && changePct != null && (
            <span className={`ml-2 font-medium ${changeUp ? "text-emerald-700" : "text-rose-700"}`}>
              {formatUsd4(change)} ({formatPercent4(changePct, true)})
            </span>
          )}
          <span className="ml-2 text-[10px] text-neutral-500">
            {p.price_source || "quote source"}
            {p.price_as_of ? ` · ${p.price_as_of}` : ""}
            {p.price_stale ? " · stale" : ""}
          </span>
        </span>
      ),
    })
  }
  if (p?.range_52w) facts.push({ label: "52w range", value: `$${p.range_52w}` })
  if (p?.market_cap != null) facts.push({ label: "Market cap", value: formatUsd4(p.market_cap) })
  if (p?.beta != null) facts.push({ label: "Beta", value: formatNumber4(p.beta) })

  return (
    <div className="space-y-4">
      {(facts.length > 0 || p?.description) && (
        <div className="overflow-hidden rounded-xl border border-border bg-white">
          <div className="border-b border-border px-4 py-2.5">
            <h3 className="text-sm font-semibold text-black">Company</h3>
          </div>
          <table className="w-full text-sm">
            <tbody>
              {facts.map((f) => (
                <tr key={f.label} className="border-b border-neutral-100 last:border-0">
                  <th className="w-28 whitespace-nowrap px-4 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-neutral-500 align-top">
                    {f.label}
                  </th>
                  <td className="px-4 py-2 text-neutral-900">{f.value}</td>
                </tr>
              ))}
              {p?.description && (
                <tr>
                  <th className="w-28 whitespace-nowrap px-4 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-neutral-500 align-top">
                    About
                  </th>
                  <td className="px-4 py-2 leading-relaxed text-neutral-800">
                    {firstSentences(p.description, 2)}
                    {p.source && <span className="mt-1 block text-[10px] text-neutral-400">{p.source}</span>}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {data.valuation_range && <ValuationBand range={data.valuation_range} />}

      <PriceChart ticker={v.ticker} range={data.valuation_range} years={3} />

      {stance && (
        <button
          type="button"
          onClick={goStance}
          className={`w-full rounded-xl border-2 p-4 text-left ${
            stance.stance === "BUY"
              ? "border-emerald-400 bg-emerald-50"
              : stance.stance === "UNKNOWN"
                ? "border-neutral-300 bg-neutral-50"
                : "border-amber-300 bg-amber-50"
          }`}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
                Research stance · close-call waterfall
              </div>
              <div className="text-2xl font-bold text-black">
                {stance.stance}
                {stance.horizon_years != null && (
                  <span className="ml-2 text-base font-semibold text-neutral-700">{stance.horizon_years}y horizon</span>
                )}
              </div>
            </div>
            <span className="text-xs font-medium text-sky-800 underline">Open flowchart →</span>
          </div>
          <p className="mt-1 text-xs text-neutral-700">
            Confidence {stance.confidence}
            {stance.score != null && <> · score {stance.score}/100</>}
            {stance.blockers[0] ? <> · {stance.blockers[0]}</> : null}
          </p>
        </button>
      )}

      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <MetricCell label="Gap vs price target" m={v.mos_live} pct open={open} axis="mos_live" />
        <MetricCell label="Gap at snapshot" m={v.mos_snapshot} pct open={open} axis="mos_snapshot" />
        <MetricCell label="R&D productivity" m={v.rd_prod} open={open} axis="rd_prod" />
        <MetricCell label="Rule of 40" m={v.rule40} pct open={open} axis="rule40" />
        <MetricCell label="FCF margin (SBC-adj)" m={v.fcfm_sbc} pct open={open} axis="fcfm_sbc" />
        <MetricCell label="ROIC" m={v.roic} pct open={open} axis="roic" />
        <MetricCell label="Retention (disclosed)" m={v.retention} pct open={open} axis="retention" />
        <MetricCell label="12m return" m={v.ret_12m} pct open={open} axis="ret_12m" />
      </div>
      <div className="rounded-xl border border-border bg-white p-4 text-sm">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-neutral-800">
          <span>Route: <b>{v.route || "unknown"}</b></span>
          <span>Cohort: <b>{v.cohort || "—"}</b></span>
          <span>Table-20 gates passed: <b>{v.table20_pass_count ?? "—"}/12</b></span>
          <span>Carve-out: <b>{v.carve_out === true ? "yes (payments/float)" : v.carve_out === false ? "no" : "unknown"}</b></span>
          <span>Universe: <b>{v.universe_version}</b></span>
        </div>
      </div>

      {/* Financial history at a glance */}
      <FinancialsCharts ticker={v.ticker} />
    </div>
  )
}

function BusinessTab({ data, open }: { data: CompanyResearch; open: (a: string) => void }) {
  const v = data.vector
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCell label="Retention / NRR" m={v.retention} pct open={open} axis="retention" />
        <MetricCell label="Customer concentration" m={v.concentration} pct open={open} axis="concentration" />
        <MetricCell label="Offering quality z (vs peers)" m={v.offering_quality_z} open={open} axis="offering_quality_z" />
        <MetricCell label="Gross margin" m={v.gm} pct open={open} axis="gm" />
        <MetricCell label="AI text stance" m={v.ai_text_stance} open={open} axis="ai_text_stance" />
        <MetricCell label="SBC intensity" m={v.sbc_intensity} pct open={open} axis="sbc_intensity" />
      </div>
      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">Disclosure status</h3>
        <p className="mt-1 text-xs leading-relaxed text-neutral-700">
          Retention and concentration come only from verbatim 10-K disclosures. “Unknown” means the
          company did not disclose — it is never estimated. Filing fetched:{" "}
          <b>{v.completeness.filing_fetched ? "yes" : "no"}</b> · overlay fill rate{" "}
          <b>{formatPercent4(v.completeness.overlay_fill_rate)}</b> · claims recorded{" "}
          <b>{formatNumber4(v.completeness.claims_n)}</b>.
        </p>
      </div>
    </div>
  )
}

function ResearchTab({ data, open }: { data: CompanyResearch; open: (a: string) => void }) {
  const v = data.vector
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-black">R&D Alpha constructs (Paper-1)</h3>
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCell label="R&D intensity" m={v.rd_int} open={open} axis="rd_int" />
        <MetricCell label="R&D / gross profit" m={v.rd_gp} open={open} axis="rd_gp" />
        <MetricCell label="R&D momentum" m={v.rd_mom} open={open} axis="rd_mom" />
        <MetricCell label="Capitalized R&D" m={v.rd_capital} open={open} axis="rd_capital" />
        <MetricCell label="R&D productivity" m={v.rd_prod} open={open} axis="rd_prod" />
        <MetricCell label="Cap R&D / EV" m={v.rd_cap_to_ev} open={open} axis="rd_cap_to_ev" />
      </div>
      <h3 className="text-sm font-semibold text-black">Growth / risk / momentum</h3>
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCell label="Revenue CAGR" m={v.rev_cagr} pct open={open} axis="rev_cagr" />
        <MetricCell label="Annual dilution" m={v.dilution_ann} pct open={open} axis="dilution_ann" />
        <MetricCell label="Runway (yrs, pre-FCF)" m={v.runway_yrs} open={open} axis="runway_yrs" />
        <MetricCell label="3m return" m={v.ret_3m} pct open={open} axis="ret_3m" />
        <MetricCell label="12m return" m={v.ret_12m} pct open={open} axis="ret_12m" />
        <MetricCell label="Drawdown from peak" m={v.drawdown_from_peak} pct open={open} axis="drawdown_from_peak" />
      </div>
    </div>
  )
}

function ValuationTab({
  data,
  open,
  onDcfSaved,
}: {
  data: CompanyResearch
  open: (a: string) => void
  onDcfSaved: (run: {
    run_id: string
    inputs: DcfInputs
    outputs: DcfOutputs
    universe_version: string
  }) => void
}) {
  const v = data.vector
  const seeded = data.dcf_runs?.[0]?.inputs
  const [inputs, setInputs] = useState<Partial<DcfInputs>>(() =>
    seeded
      ? { ...seeded }
      : { ...DEFAULT_DCF_INPUTS }
  )
  const [out, setOut] = useState<DcfOutputs | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)

  useEffect(() => {
    const latest = data.dcf_runs?.[0]?.inputs
    setInputs(latest ? { ...latest } : { ...DEFAULT_DCF_INPUTS })
  }, [data.dcf_runs, v.ticker, data.universe_version])

  useEffect(() => {
    const generation = ++requestGenerationRef.current
    setOut(null)
    setErr(null)
    setBusy(false)
    return () => {
      if (requestGenerationRef.current === generation) requestGenerationRef.current += 1
    }
  }, [v.ticker, data.universe_version])

  const run = () => {
    const years = Number(inputs.years ?? 10)
    const glideYears = Number(inputs.glide_years ?? 7)
    if (!Number.isInteger(years) || years < 2 || years > 30 || !Number.isInteger(glideYears) || glideYears < 1 || glideYears > years) {
      setErr("Projection years must be 2–30 and margin glide years must be 1–projection years.")
      return
    }
    const generation = ++requestGenerationRef.current
    const expectedTicker = v.ticker.toUpperCase()
    const expectedUniverseVersion = data.universe_version
    setBusy(true)
    setErr(null)
    runDcf(
      v.ticker,
      { ticker: v.ticker, scenario: "custom", ...inputs } as DcfInputs,
      true,
      expectedUniverseVersion
    )
      .then((r) => {
        if (
          generation !== requestGenerationRef.current ||
          r.universe_version !== expectedUniverseVersion ||
          r.inputs.ticker.toUpperCase() !== expectedTicker
        ) {
          return
        }
        setOut(r.outputs)
        if (r.run_id) {
          onDcfSaved({
            run_id: r.run_id,
            inputs: r.inputs,
            outputs: r.outputs,
            universe_version: r.universe_version,
          })
        }
      })
      .catch((e) => {
        if (generation === requestGenerationRef.current) setErr(String(e))
      })
      .finally(() => {
        if (generation === requestGenerationRef.current) setBusy(false)
      })
  }

  const gap = v.mos_live.value
  return (
    <div className="space-y-4">
      {data.valuation_range && (
        <ValuationBand range={data.valuation_range} mosLive={v.mos_live?.value ?? null} />
      )}
      <PriceChart ticker={v.ticker} range={data.valuation_range} years={3} />
      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">The one valuation gap (not a forecast)</h3>
        {gap !== null ? (
          <p className="mt-1 text-sm text-neutral-800">
            The as-of quote is <b>{formatPercent4(Math.abs(gap))}</b> {gap >= 0 ? "below" : "above"} the snapshot
            triangulated median fair value. Closing that same gap over N years implies an annual rate of
            <span className="font-mono"> (FV/P)^(1/N) − 1</span>:{" "}
            <b>{yearly(gap, 1)}</b> over 1y · <b>{yearly(gap, 2)}</b>/yr over 2y · <b>{yearly(gap, 3)}</b>/yr over 3y.
            One gap, annualized — not three predictions, and never divided by N.
          </p>
        ) : (
          <p className="mt-1 text-sm text-neutral-600">No gap vs price target available (price or fair value missing).</p>
        )}
        <button type="button" onClick={() => open("mos_live")} className="mt-2 text-xs font-medium text-sky-800 underline">
          Evidence trail for this number →
        </button>
      </div>

      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">DCF workbench (saved, reproducible runs)</h3>
        <p className="mt-1 text-[11px] text-neutral-600">
          Same formulas as the paper engine (2-stage owner-earnings + path-to-profit + peer multiple triangle).
          Every run is stored with its assumptions and engine version.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {(
            [
              ["revenue_usd", "Revenue (USD)"],
              ["fcf_sbc_usd", "FCF SBC-adj (USD)"],
              ["fcfm_sbc", "FCF margin (0-1)"],
              ["net_cash_usd", "Net cash (USD)"],
              ["ev_mult_usd", "Peer-multiple EV (USD)"],
              ["shares_fut_implied", "Future shares"],
              ["price", "Price"],
              ["growth", "Growth (initial)"],
              ["wacc", "WACC"],
              ["terminal_g", "Terminal g"],
              ["target_margin", "Target margin"],
              ["years", "Projection years"],
              ["glide_years", "Margin glide years"],
            ] as const
          ).map(([k, label]) => (
            <label key={k} className="text-[11px] text-neutral-700">
              {label}
              <input
                type="number"
                step={k === "years" || k === "glide_years" ? 1 : "any"}
                min={k === "years" ? 2 : k === "glide_years" ? 1 : undefined}
                max={k === "years" || k === "glide_years" ? 30 : undefined}
                value={(inputs as Record<string, number | null | undefined>)[k] ?? ""}
                onChange={(e) =>
                  setInputs((prev) => ({ ...prev, [k]: e.target.value === "" ? null : Number(e.target.value) }))
                }
                className="mt-0.5 h-8 w-full rounded-md border border-border px-2 text-sm text-black"
              />
            </label>
          ))}
        </div>
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="mt-3 rounded-lg bg-black px-4 py-2 text-xs font-medium text-white disabled:opacity-40"
        >
          {busy ? "Running…" : "Run + save scenario"}
        </button>
        {err && <div className="mt-2"><ErrorBanner>{err}</ErrorBanner></div>}
        {seeded && (
          <p className="mt-2 text-[11px] text-neutral-600">
            Inputs seeded from latest saved run ({data.dcf_runs[0].run_id.slice(0, 8)}).
          </p>
        )}
        {out && (
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-4">
            <Out label="Fair px low" v={out.fair_px_lo} />
            <Out label="Fair px median" v={out.fair_px_med} />
            <Out label="Fair px high" v={out.fair_px_hi} />
            <Out label="Implied MoS" v={out.mos} pct />
          </div>
        )}
        {data.dcf_runs.length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs font-semibold text-neutral-700">Saved runs</h4>
            <div className="mt-1 space-y-1">
              {data.dcf_runs.slice(0, 6).map((r) => (
                <div key={r.run_id} className="flex flex-wrap gap-x-4 text-[11px] text-neutral-700">
                  <span className="font-mono">{r.run_id.slice(0, 8)}</span>
                  <span>{r.scenario}</span>
                  <span>g={r.inputs.growth} wacc={r.inputs.wacc}</span>
                  <span>med {formatUsd4(r.outputs.fair_px_med)}</span>
                  <span>{r.engine_version}</span>
                  <span>{String(r.created_at).slice(0, 10)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Out({ label, v, pct }: { label: string; v: number | null; pct?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-neutral-50 p-2">
      <div className="text-[10px] uppercase text-neutral-500">{label}</div>
      <div className="font-semibold tabular-nums text-black">
        {v === null ? "—" : pct ? formatPercent4(v) : formatUsd4(v)}
      </div>
    </div>
  )
}

const yearly = (gap: number, n: number) => formatPercent4((1 + gap) ** (1 / n) - 1, true)

function AuditTab({ data, open }: { data: CompanyResearch; open: (a: string) => void }) {
  const v = data.vector
  const [downloading, setDownloading] = useState(false)
  const [exportErr, setExportErr] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)
  const requestKey = `${v.ticker}:${data.universe_version}`

  useEffect(() => {
    requestGenerationRef.current += 1
    setDownloading(false)
    setExportErr(null)
    return () => {
      requestGenerationRef.current += 1
    }
  }, [requestKey])

  const download = () => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setDownloading(true)
    setExportErr(null)
    getAuditPack(v.ticker, data.universe_version, controller.signal)
      .then((pack) => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" })
        const a = document.createElement("a")
        a.href = URL.createObjectURL(blob)
        a.download = `${v.ticker}_audit_pack.json`
        a.click()
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setExportErr(String(e))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setDownloading(false)
        }
      })
  }
  const axes = [
    "mos_live", "mos_snapshot", "rd_prod", "rd_int", "gm", "fcfm_sbc", "roic",
    "rule40", "retention", "concentration", "ret_12m", "offering_quality_z",
  ]
  return (
    <div className="space-y-4">
      {exportErr && <ErrorBanner>{exportErr}</ErrorBanner>}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-neutral-700">
          Every rank-moving metric with its trail. Click a row for the full drawer (claims, snapshots, literature, PIT dates).
        </p>
        <button
          type="button"
          onClick={download}
          disabled={downloading}
          className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-black hover:bg-muted disabled:opacity-40"
        >
          {downloading ? "Building…" : "Export audit pack (watermarked JSON)"}
        </button>
      </div>
      <div className="overflow-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-[11px] uppercase text-foreground/60">
            <tr>
              <th className="px-3 py-2 text-left">Axis</th>
              <th className="px-3 py-2 text-right">Value</th>
              <th className="px-3 py-2 text-left">As-of / available (PIT)</th>
              <th className="px-3 py-2 text-left">Formula</th>
              <th className="px-3 py-2 text-left">Claims</th>
            </tr>
          </thead>
          <tbody>
            {axes.map((a) => {
              const m = (v as unknown as Record<string, MetricValue>)[a]
              if (!m || typeof m !== "object") return null
              return (
                <tr key={a} className="cursor-pointer border-t border-border/70 hover:bg-muted/30" onClick={() => open(a)}>
                  <td className="px-3 py-2 font-mono text-xs text-black">{a}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-black">
                    {m.value === null ? "Unknown" : formatResearchMetric4(a, m.value)}
                  </td>
                  <td className="px-3 py-2 text-[11px] text-neutral-700">{m.as_of_date || "—"} / {m.available_date || "—"}</td>
                  <td className="max-w-[300px] px-3 py-2 text-[11px] text-neutral-700">{m.formula || "—"}</td>
                  <td className="px-3 py-2 text-[11px] text-neutral-700">{m.claim_ids.length}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border bg-white p-4">
          <h3 className="text-sm font-semibold text-black">Gate evaluations</h3>
          <div className="mt-2 space-y-1">
            {data.gates.map((g) => (
              <div key={g.gate_id} className="flex justify-between text-[11px]">
                <span className="text-neutral-700">{g.gate_id}</span>
                <span className={g.passed ? "text-emerald-700" : "text-rose-700"}>{g.passed ? "pass" : "fail"}</span>
              </div>
            ))}
            {data.gates.length === 0 && <p className="text-xs text-neutral-600">No gate evaluations recorded.</p>}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-white p-4">
          <h3 className="text-sm font-semibold text-black">AI audit + final review</h3>
          <div className="mt-2 space-y-1 text-[11px] text-neutral-700">
            {data.deepseek_runs.map((r) => (
              <div key={r.run_id} className="flex justify-between">
                <span>{r.job} ({r.output_kind})</span>
                <span>{r.status}{r.severity ? ` · ${r.severity}` : ""}</span>
              </div>
            ))}
            {data.deepseek_runs.length === 0 && <p>No DeepSeek runs yet.</p>}
            <div className="mt-2 border-t border-border pt-2">
              Final review:{" "}
              {data.final_review
                ? `${data.final_review.passed ? "PASSED" : "FAILED"} (${data.final_review.trigger})`
                : "not yet reviewed (Cursor agent sampled+risk queue)"}
            </div>
            <p className="text-[10px] text-neutral-500">
              DeepSeek only maps filings and flags gaps — the numbers above come from engines and verbatim extractors.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function MemoTab({
  ticker,
  universeVersion,
  availableCitationIds,
}: {
  ticker: string
  universeVersion: string
  availableCitationIds: string[]
}) {
  const [memos, setMemos] = useState<
    {
      memo_id: string
      version: number
      thesis: string
      risks: string | null
      created_at: string
      analyst_judgment_ack: boolean
      citations: string[]
      citation_records: { claim_id: string; value_text: string; excerpt_locator: string }[]
    }[]
  >([])
  const [thesis, setThesis] = useState("")
  const [risks, setRisks] = useState("")
  const [citationText, setCitationText] = useState("")
  const [ack, setAck] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const requestGenerationRef = useRef(0)
  const load = useCallback(() => {
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    getMemos(ticker, universeVersion, controller.signal)
      .then((result) => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        setMemos(result.memos)
        setLoadErr(null)
      })
      .catch((e) => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        setMemos([])
        setLoadErr(String(e))
      })
    return () => controller.abort()
  }, [ticker, universeVersion])

  useEffect(() => {
    setMemos([])
    setLoadErr(null)
    setThesis("")
    setRisks("")
    setCitationText("")
    setAck(false)
    setErr(null)
    setBusy(false)
    const cancel = load()
    return () => {
      requestGenerationRef.current += 1
      cancel()
    }
  }, [load])

  const save = () => {
    const citations = [...new Set(citationText.split(/[\s,]+/).map((id) => id.trim()).filter(Boolean))]
    if (citations.length === 0 && !ack) {
      setErr("Citations empty — check analyst judgment ack, or add claim IDs.")
      return
    }
    const generation = ++requestGenerationRef.current
    const controller = new AbortController()
    setBusy(true)
    setErr(null)
    saveMemo(ticker, {
      thesis,
      risks: risks || undefined,
      citations,
      universe_version: universeVersion,
      analyst_judgment_ack: ack,
    }, controller.signal)
      .then(() => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        setThesis("")
        setRisks("")
        setCitationText("")
        setAck(false)
        setBusy(false)
        load()
      })
      .catch((e) => {
        if (controller.signal.aborted || generation !== requestGenerationRef.current) return
        const msg = String(e)
        // Surface FastAPI 422 detail when present in Error message
        setErr(msg.includes("detail") ? msg : msg)
      })
      .finally(() => {
        if (!controller.signal.aborted && generation === requestGenerationRef.current) {
          setBusy(false)
        }
      })
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-white p-4">
        <h3 className="text-sm font-semibold text-black">New memo version</h3>
        <p className="mt-1 text-[11px] text-neutral-600">
          Every sentence must trace to an evidence claim, or the memo must be explicitly marked analyst judgment.
        </p>
        <textarea
          value={thesis}
          onChange={(e) => setThesis(e.target.value)}
          placeholder="Thesis…"
          rows={4}
          className="mt-2 w-full rounded-md border border-border p-2 text-sm text-black"
        />
        <textarea
          value={risks}
          onChange={(e) => setRisks(e.target.value)}
          placeholder="Risks / kill criteria…"
          rows={2}
          className="mt-2 w-full rounded-md border border-border p-2 text-sm text-black"
        />
        <label className="mt-2 block text-[11px] font-medium text-neutral-700">
          Evidence claim IDs (comma, space, or newline separated)
          <textarea
            value={citationText}
            onChange={(e) => setCitationText(e.target.value)}
            placeholder="claim_id_1, claim_id_2"
            rows={2}
            className="mt-1 w-full rounded-md border border-border p-2 font-mono text-xs text-black"
          />
        </label>
        {availableCitationIds.length > 0 && (
          <div className="mt-2">
            <p className="text-[11px] text-neutral-600">Claims on this frozen research record — click to cite:</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {availableCitationIds.slice(0, 24).map((claimId) => (
                <button
                  key={claimId}
                  type="button"
                  onClick={() =>
                    setCitationText((previous) =>
                      previous.split(/[\s,]+/).includes(claimId)
                        ? previous
                        : [previous.trim(), claimId].filter(Boolean).join(", ")
                    )
                  }
                  className="rounded border border-border bg-neutral-50 px-1.5 py-0.5 font-mono text-[10px] text-neutral-700 hover:bg-neutral-100"
                >
                  {claimId}
                </button>
              ))}
            </div>
          </div>
        )}
        <label className="mt-2 flex min-h-11 items-center gap-2 text-xs text-neutral-700">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          This memo contains analyst judgment not directly cited to a claim (required if no citations)
        </label>
        {(err || loadErr) && <div className="mt-2"><ErrorBanner>{err || loadErr || ""}</ErrorBanner></div>}
        <button
          type="button"
          onClick={save}
          disabled={busy || !thesis.trim() || (!ack && !citationText.trim())}
          className="mt-3 rounded-lg bg-black px-4 py-2 text-xs font-medium text-white disabled:opacity-40"
          title={!ack && !citationText.trim() ? "Add citations or acknowledge analyst judgment" : undefined}
        >
          Save version
        </button>
      </div>
      <div className="space-y-2">
        {memos.map((m) => (
          <div key={m.memo_id} className="rounded-xl border border-border bg-white p-4">
            <div className="flex justify-between text-[11px] text-neutral-600">
              <span>v{m.version} · {String(m.created_at).slice(0, 10)}</span>
              <span>{m.analyst_judgment_ack ? "analyst judgment" : "cited"}</span>
            </div>
            <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-900">{m.thesis}</p>
            {m.risks && <p className="mt-1 whitespace-pre-wrap text-xs text-neutral-700">Risks: {m.risks}</p>}
            {m.citation_records.length > 0 && (
              <ul className="mt-2 space-y-1 border-t border-border pt-2 text-[11px] text-neutral-700">
                {m.citation_records.map((citation) => (
                  <li key={citation.claim_id}>
                    <span className="font-mono text-neutral-900">{citation.claim_id}</span>
                    {" · "}
                    {citation.value_text}
                    {citation.excerpt_locator ? ` (${citation.excerpt_locator})` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {memos.length === 0 && <p className="text-sm text-neutral-600">No memo versions yet.</p>}
      </div>
    </div>
  )
}
