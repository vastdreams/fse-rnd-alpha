/**
 * PATH: frontend/src/pages/portfolio/InvestigatePage.tsx
 * PURPOSE: MedTwin Patients-analogue — path funnel, selectable universe, bulk add to book.
 */
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  filterByPath,
  loadSaasBundle,
  type SaasBundle,
  type SaasCompany,
} from "@/lib/api/saasPortfolio"
import { usePortfolioBucket } from "@/hooks/usePortfolioBucket"
import {
  fmtMoney,
  fmtPct,
  livePrice,
  mosLive,
  toneReturn,
  totalUpside,
} from "@/lib/portfolioReturns"
import { buildResearchGuideline, researchStatusTone } from "@/lib/priceGuides"
import { companyIdentity } from "@/lib/companyIdentity"
import {
  MODEL_PORTFOLIO_TICKERS,
  modelHolding,
  modelTierLabel,
} from "@/lib/modelPortfolio"
import { filingOffering } from "@/lib/filingOfferings"
import { AUDIT_DATE, auditVerdictTone, model10Audit } from "@/lib/paperAudit"

const PRIMARY_PATHS = ["model_10", "table20", "full_100"] as const

const GATE_EXPLAINER: { id: string; title: string; body: string }[] = [
  {
    id: "g1",
    title: "Gate 1 — SaaS universe",
    body: "Keep software companies; drop payments/fintech float businesses that break owner-earnings DCF.",
  },
  {
    id: "g2",
    title: "Gate 2 — FCF-positive",
    body: "SBC-adjusted free cash flow must be positive. Pre-FCF names use a separate valuation route and are not in the core book.",
  },
  {
    id: "g3",
    title: "Gate 3 — MoS > 0",
    body: "Live price below the paper-date triangulated valuation median. Fundamentals are still the March snapshot.",
  },
  {
    id: "g5",
    title: "Gate 5 — Moat / quality",
    body: "R&D productivity ≥ 0.25 or Rule-of-40 ≥ 20%. Quality screen, not a buy rating.",
  },
  {
    id: "core",
    title: "Core screen (relaxed)",
    body: "Exposed-incumbent + MoS + moat + size + FCF+. This is 6 of the paper's 12 Table-20 conditions — it deliberately omits the improving-margin, growth ≥ 5%, filing-quality, dilution and carve-out gates, so it is wider than the paper.",
  },
  {
    id: "t20",
    title: "Paper Table 20 (strict)",
    body: "The paper's actual 12-condition output: exactly four survivors (FRSH, DOCU Tier 1; PCTY, WDAY Tier 2). The 2026-07-12 audit re-verified these against the 10-K filings.",
  },
  {
    id: "m10",
    title: "Model 10 research book",
    body: "Audited 2026-07-12: 3 paper-core names, WDAY on hold (its kill criterion fired at live prices), and 6 watchlist names that each fail at least one real paper gate. Watchlist ≠ buy.",
  },
]

function pathCopy(path: { id: string; label: string; description: string }) {
  if (path.id === "model_10") {
    return {
      label: "Model 10 · research book",
      description:
        "Audited 2026-07-12: 3 paper core (FRSH, DOCU, PCTY) · WDAY on hold · 6 watchlist. Badges on each row say why.",
    }
  }
  if (path.id === "table20") {
    return {
      label: "Paper Table 20 · 4 only",
      description: "FRSH, DOCU, PCTY, WDAY — the paper’s full 12-gate survivor set.",
    }
  }
  if (path.id === "core_thesis") {
    return {
      label: "Relaxed core screen · 6 of 12 gates",
      description:
        "Wider than the paper by design — omits the improving-margin, growth, filing-quality, dilution and carve-out gates.",
    }
  }
  if (path.id === "full_100") {
    return {
      label: "Full investable universe",
      description: "Top-100 SaaS screen before gating down.",
    }
  }
  return { label: path.label, description: path.description }
}

export function InvestigatePage() {
  const [bundle, setBundle] = useState<SaasBundle | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pathId, setPathId] = useState("model_10")
  const [q, setQ] = useState("")
  const [selected, setSelected] = useState<string[]>([])
  const [sortKey, setSortKey] = useState<"upside" | "mos" | "rd_prod" | "intangible" | "rank">(
    "upside"
  )
  const [showGates, setShowGates] = useState(false)
  const { bucket, addMany, toggle, has } = usePortfolioBucket()

  useEffect(() => {
    loadSaasBundle()
      .then(setBundle)
      .catch((e) => setError(String(e)))
  }, [])

  const primaryCards = useMemo(() => {
    if (!bundle) return []
    const byId = Object.fromEntries(
      bundle.selection_paths.map((p) => [p.id, p])
    ) as Record<string, { id: string; label: string; description: string }>
    return PRIMARY_PATHS.map((id) => {
      const base =
        id === "model_10"
          ? { id, label: "Model 10", description: "" }
          : byId[id] || { id, label: id, description: "" }
      return {
        ...base,
        n: filterByPath(bundle.companies, id).length,
      }
    })
  }, [bundle])

  const advancedPaths = useMemo(() => {
    if (!bundle) return []
    return bundle.selection_paths
      .filter((p) => !PRIMARY_PATHS.includes(p.id as (typeof PRIMARY_PATHS)[number]))
      .map((p) => ({
        ...p,
        n: filterByPath(bundle.companies, p.id).length,
      }))
  }, [bundle])

  const rows = useMemo(() => {
    if (!bundle) return []
    let list = filterByPath(bundle.companies, pathId)
    if (pathId === "model_10") {
      const order = new Map(MODEL_PORTFOLIO_TICKERS.map((t, i) => [t, i]))
      list = [...list].sort(
        (a, b) => (order.get(a.ticker) ?? 99) - (order.get(b.ticker) ?? 99)
      )
    }
    if (q.trim()) {
      const ql = q.trim().toLowerCase()
      list = list.filter(
        (c) =>
          c.ticker.toLowerCase().includes(ql) ||
          (c.cohort || "").toLowerCase().includes(ql) ||
          String((c as { live_name?: string }).live_name || "")
            .toLowerCase()
            .includes(ql)
      )
    }
    if (pathId === "model_10" && !q.trim()) return list
    return [...list].sort((a, b) => {
      if (sortKey === "rank") return a.rank - b.rank
      if (sortKey === "mos") return (mosLive(b) ?? -999) - (mosLive(a) ?? -999)
      if (sortKey === "rd_prod") return (b.rd_prod ?? -999) - (a.rd_prod ?? -999)
      if (sortKey === "intangible") return (b.intangible_score ?? 0) - (a.intangible_score ?? 0)
      return (totalUpside(b) ?? -999) - (totalUpside(a) ?? -999)
    })
  }, [bundle, pathId, q, sortKey])

  const toggleSelect = (t: string) => {
    setSelected((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  const selectAllVisible = () => setSelected(rows.map((r) => r.ticker))
  const clearSelect = () => setSelected([])

  if (error) return <div className="p-6 text-rose-800">{error}</div>
  if (!bundle) {
    return <div className="flex h-64 items-center justify-center text-neutral-700">Loading universe…</div>
  }

  const prov = bundle.provenance as { as_of_fundamentals?: string[]; live_refresh?: { at?: string } }

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-950">Investigate</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-700">
            Paper Table 20 has exactly <span className="font-semibold text-neutral-950">4</span> survivors.
            The 10-name research book was independently audited on{" "}
            <span className="font-semibold text-neutral-950">{AUDIT_DATE}</span>: 3 paper core,
            WDAY on hold, 6 watchlist. Each row's badge says why. Fundamentals as-of{" "}
            {(prov.as_of_fundamentals || []).join(" · ") || "—"}.
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {primaryCards.map((p) => {
          const active = pathId === p.id
          const copy = pathCopy(p)
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setPathId(p.id)
                clearSelect()
              }}
              className={`text-left rounded-xl border p-4 transition ${
                active
                  ? "border-black bg-neutral-100 shadow-sm"
                  : "border-border bg-white hover:bg-muted/40"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-black">{copy.label}</span>
                <span className="text-2xl font-semibold tabular-nums text-black">{p.n}</span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-neutral-700">
                {copy.description}
              </p>
            </button>
          )
        })}
      </div>

      <div className="rounded-xl border border-border bg-white">
        <button
          type="button"
          onClick={() => setShowGates((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <div>
            <div className="text-sm font-semibold text-black">
              How screening works (paper gates)
            </div>
            <div className="text-xs text-neutral-700">
              Gates live here — not as a random strip of cards. Open a company for the full pass/fail board.
            </div>
          </div>
          <span className="text-xs font-medium text-neutral-600">{showGates ? "Hide" : "Show"}</span>
        </button>
        {showGates && (
          <div className="space-y-4 border-t border-border px-4 pb-4 pt-3">
            <div className="grid gap-3 md:grid-cols-2">
              {GATE_EXPLAINER.map((g) => (
                <div key={g.id} className="rounded-lg border border-border bg-neutral-50 p-3">
                  <div className="text-xs font-semibold text-black">{g.title}</div>
                  <p className="mt-1 text-[11px] leading-relaxed text-neutral-700">
                    {g.body}
                  </p>
                </div>
              ))}
            </div>
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-600">
                Advanced filters
              </div>
              <div className="flex flex-wrap gap-2">
                {advancedPaths.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setPathId(p.id)
                      clearSelect()
                    }}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      pathId === p.id
                        ? "border-black bg-black text-white"
                        : "border-border bg-white text-foreground hover:bg-muted"
                    }`}
                  >
                    {pathCopy(p).label} ({p.n})
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search ticker or name…"
          className="h-9 w-full max-w-xs rounded-lg border border-border bg-background px-3 text-sm text-black"
        />
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as typeof sortKey)}
          className="h-9 rounded-lg border border-border bg-background px-2 text-sm text-black"
        >
          <option value="upside">Sort: upside to fair</option>
          <option value="mos">Sort: MoS</option>
          <option value="rd_prod">Sort: R&D prod</option>
          <option value="intangible">Sort: intangible</option>
          <option value="rank">Sort: rank</option>
        </select>
        <span className="text-xs text-neutral-700">{rows.length} names</span>
        <div className="flex-1" />
        <Link to="/app/book" className="text-sm font-medium text-black underline-offset-2 hover:underline">
          My Book ({bucket.length}) →
        </Link>
      </div>

      {selected.length > 0 && (
        <div className="sticky top-0 z-20 flex flex-wrap items-center gap-2 rounded-xl border border-neutral-300 bg-neutral-100 px-4 py-2.5">
          <span className="text-sm font-medium text-black">{selected.length} selected</span>
          <button
            type="button"
            className="rounded-lg bg-black px-3 py-1.5 text-xs font-medium text-white"
            onClick={() => {
              addMany(selected)
              clearSelect()
            }}
          >
            Add to My Book
          </button>
          <button type="button" className="text-xs text-neutral-700 hover:underline" onClick={selectAllVisible}>
            Select all visible
          </button>
          <button type="button" className="text-xs text-neutral-700 hover:underline" onClick={clearSelect}>
            Clear
          </button>
        </div>
      )}

      <div className="overflow-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-[11px] uppercase tracking-wide text-foreground/60">
            <tr>
              <th className="w-8 px-2 py-2.5 text-left">
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selected.length === rows.length}
                  onChange={(e) => (e.target.checked ? selectAllVisible() : clearSelect())}
                />
              </th>
              <th className="px-2 py-2.5 text-left">Company</th>
              <th className="px-2 py-2.5 text-right">Price</th>
              <th className="px-2 py-2.5 text-right">Fair</th>
              <th className="px-2 py-2.5 text-right">Upside</th>
              <th className="px-2 py-2.5 text-right">MoS</th>
              <th className="px-2 py-2.5 text-left">Evidence</th>
              <th className="px-2 py-2.5 text-left">Research status</th>
              <th className="px-2 py-2.5 text-right">Book</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <UniverseRow
                key={c.ticker}
                c={c}
                checked={selected.includes(c.ticker)}
                inBook={has(c.ticker)}
                onCheck={() => toggleSelect(c.ticker)}
                onToggleBook={() => toggle(c.ticker)}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-2">
        {bundle.bucket_presets.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => addMany(p.tickers)}
            className="rounded-full border border-border bg-white px-3 py-1 text-xs text-foreground hover:bg-muted"
          >
            Add preset: {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function UniverseRow({
  c,
  checked,
  inBook,
  onCheck,
  onToggleBook,
}: {
  c: SaasCompany
  checked: boolean
  inBook: boolean
  onCheck: () => void
  onToggleBook: () => void
}) {
  const up = totalUpside(c)
  const status = buildResearchGuideline(c)
  const id = companyIdentity(c)
  const holding = modelHolding(c.ticker)
  const offering = filingOffering(c.ticker)
  const audit = model10Audit(c.ticker)
  return (
    <tr className="border-t border-border/70 hover:bg-muted/30">
      <td className="px-2 py-3 align-top">
        <input type="checkbox" checked={checked} onChange={onCheck} />
      </td>
      <td className="min-w-[300px] max-w-[460px] px-2 py-3 align-top">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <Link
            to={`/app/company/${c.ticker}`}
            className="!text-black font-bold hover:underline"
          >
            {c.ticker}
          </Link>
          {holding && (
            <span
              className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                audit ? auditVerdictTone(audit.verdict) : "border-neutral-300 bg-neutral-50 text-black"
              }`}
              title={audit ? `${AUDIT_DATE} audit — ${audit.decidingGate}` : undefined}
            >
              {modelTierLabel(holding.tier)}
            </span>
          )}
          {!holding && c.paper_tier && (
            <span className="text-[10px] font-medium uppercase text-amber-900">
              {c.paper_tier}
            </span>
          )}
        </div>
        <div className="mt-0.5 text-xs font-medium text-neutral-800">{id.line}</div>
        {audit && (
          <div className="mt-1 text-[11px] leading-snug text-neutral-800">
            <span className="font-semibold">Audit {AUDIT_DATE}: </span>
            {audit.headline}
          </div>
        )}
        <div className="mt-1 text-[11px] leading-snug text-neutral-700">
          {offering?.headline || holding?.basis || id.description}
        </div>
        {offering && (
          <div className="mt-1.5 text-[11px] leading-snug text-neutral-700">
            <span className="font-medium text-neutral-800">Products: </span>
            {offering.offerings.slice(0, 3).join(" · ")}
            {offering.offerings.length > 3 ? " · …" : ""}
            <span className="ml-1 text-neutral-400">
              ({offering.source_type === "10-K Item 1 Business" ? "10-K" : "pending 10-K"})
            </span>
          </div>
        )}
      </td>
      <td className="px-2 py-3 text-right align-top tabular-nums text-black">
        {fmtMoney(livePrice(c))}
      </td>
      <td className="px-2 py-3 text-right align-top tabular-nums text-black">
        {fmtMoney(c.fair_px_med)}
      </td>
      <td className={`px-2 py-3 text-right align-top tabular-nums font-medium ${toneReturn(up)}`}>
        {fmtPct(up, 0)}
      </td>
      <td className={`px-2 py-3 text-right align-top tabular-nums ${toneReturn(mosLive(c))}`}>
        {fmtPct(mosLive(c), 0)}
      </td>
      <td className="px-2 py-3 align-top text-[11px] text-neutral-700">
        <div className="font-medium text-black">
          {holding ? `10% model weight` : c.mgmt_score || (c.fp_overlay ? "FP overlay" : "model")}
        </div>
        <div>
          {c.gates.g5_moat_quality ? "Moat gate · " : ""}
          {c.gates.g3_base_mos_positive_live === true
            ? "MoS+ live"
            : c.gates.g3_base_mos_positive
              ? "MoS+ paper"
              : "MoS−"}
        </div>
      </td>
      <td className="px-2 py-3 align-top">
        <span
          className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-medium ${researchStatusTone(status.action)}`}
        >
          {status.label}
        </span>
      </td>
      <td className="px-2 py-3 text-right align-top">
        <button
          type="button"
          onClick={onToggleBook}
          className={`rounded-md border px-2 py-1 text-xs font-medium ${
            inBook
              ? "border-black bg-black text-white"
              : "border-border text-black hover:bg-muted"
          }`}
        >
          {inBook ? "✓" : "+"}
        </button>
      </td>
    </tr>
  )
}
