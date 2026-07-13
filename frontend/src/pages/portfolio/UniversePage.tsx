/**
 * PATH: frontend/src/pages/portfolio/UniversePage.tsx
 * PURPOSE: Three modes — What to Buy · R&D Alpha ETF · All stocks.
 * Multi-select → server book; click-sort; CSV; factor chips; recipe pills.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { ErrorBanner } from "@/components/research/ErrorBanner"
import { BuyDenseRow } from "@/components/research/BuyDenseRow"
import { addTickersToPrimaryBook } from "@/lib/addToBook"
import { softAddWarnings } from "@/lib/bookOps"
import {
  getRank,
  getResearchStances,
  gradeTone,
  type ExcludedRow,
  type RankResponse,
  type RankedRow,
  type StanceListRow,
} from "@/lib/api/universe"
import {
  rowsToCsv,
  sortRows,
  toggleSort,
  universeBookSelectEnabled,
  type SortDir,
  type SortKey,
} from "@/lib/universeTable"
import {
  computeSellCeiling,
  fmtSellAnn,
  fmtSellUpside,
  type SellCeiling,
} from "@/lib/sellCeiling"
import { formatNumber4, formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

type Mode = "buy" | "etf" | "all"

const MODES: { id: Mode; label: string; blurb: string; recipe: string }[] = [
  {
    id: "buy",
    label: "What to Buy?",
    recipe: "R3",
    blurb:
      "Cleared BUYs only. The waterfall must know the catalyst, kill state, valuation gap, and evidence before a name appears here. Review the broader R3 candidates separately.",
  },
  {
    id: "etf",
    label: "R&D Alpha ETF",
    recipe: "R4",
    blurb: "Paper-1 R&D alpha path: intensity, momentum, capitalized R&D, quality — ETF-style ranking.",
  },
  {
    id: "all",
    label: "Universe (All stocks)",
    recipe: "R7",
    blurb: "Full research panel. Filter the table by first-principles factors — nothing is hidden behind recipes.",
  },
]

const TIPS: Record<string, string> = {
  vs_target:
    "Gap vs our fixed research price target (median fair-value lens). Positive = trading below target (cheap). Negative = above target. The guide does not move with the tape.",
  fair_guide:
    "Triangulated low / median (price target) / high from the paper run (2-stage DCF + normalized DCF + peer multiple). Fixed guide.",
  score:
    "Weighted robust-z composite for the active mode. Higher = stronger on the mode’s axes. Missing inputs exclude a name from ranking — never imputed.",
  contributions:
    "Which first-principles axes drove the score (e.g. rd_prod, mos_live). Sorted by absolute contribution.",
  completeness:
    "Underwrite eligibility (A/B/C/Incomplete) — filing fetched, claims, DCF reproducibility. Separate from attractiveness.",
  freshness: "Fundamentals within refresh SLA. Stale = past SLA; still visible, not portfolio-ready.",
  kill: "Paper kill criterion active (e.g. MoS flipped). Blocks research BUY.",
  mos: "Margin of safety / gap vs median fair value at live price. First-principles value axis.",
  rd_prod: "R&D productivity (Paper-1) — how well R&D spend converts to economics.",
  retention: "Disclosed NRR / retention from 10-K. Unknown = not disclosed — never estimated.",
  rev_cagr: "Revenue CAGR from fundamentals. Negative = shrinking top line.",
  stance:
    "Close-call waterfall verdict (BUY/HOLD/WATCH/OUT/UNKNOWN). BUY requires named catalyst + MoS+ + completeness A|B + no kill + score ≥ 65.",
  horizon:
    "Years over which the live→target gap would need to close for the implied annualized rate. Convergence math, not a forecast.",
  confidence: "high/med only when catalyst is known and gates clear. none/low when critical inputs are Unknown.",
  sell_ceil:
    "Auto-sell from the research fair-value band. Below median → sell at price target (median). Between median and high → trim at high. At/above high → past ceiling. Remaining % and hold horizon use the same gap buckets as stance (1y/2y/3y). Pure maths — not a forecast.",
}

function Tip({ tip, children }: { tip: string; children: ReactNode }) {
  return (
    <span
      tabIndex={0}
      className="group relative inline-flex cursor-help items-center gap-0.5 border-b border-dotted border-neutral-400 outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
    >
      {children}
      <span className="pointer-events-none absolute left-0 top-full z-40 mt-1 hidden w-64 rounded-lg border border-neutral-200 bg-white p-2 text-[11px] font-normal normal-case tracking-normal text-neutral-700 shadow-lg group-hover:block group-focus:block">
        {tip}
      </span>
    </span>
  )
}

function SortableHeader({
  sk,
  align = "right",
  activeKey,
  activeDir,
  onSort,
  children,
}: {
  sk: SortKey
  align?: "left" | "right"
  activeKey: SortKey | null
  activeDir: SortDir
  onSort: (key: SortKey) => void
  children: ReactNode
}) {
  const caret = activeKey === sk ? (activeDir === "desc" ? " ↓" : " ↑") : ""
  return (
    <th className={`px-3 py-2.5 ${align === "left" ? "text-left" : "text-right"}`}>
      <button
        type="button"
        onClick={() => onSort(sk)}
        className="inline-flex min-h-11 items-center gap-0.5 font-inherit uppercase tracking-wide hover:text-neutral-900"
      >
        {children}
        <span className="text-neutral-400">{caret}</span>
      </button>
    </th>
  )
}

type FactorId =
  | "mos_pos"
  | "mos_neg"
  | "compl_ab"
  | "fresh"
  | "no_kill"
  | "retention_known"
  | "rd_contrib"
  | "below_target"
  | "stance_buy"

const FACTORS: { id: FactorId; label: string; tip: string; modes?: Mode[] }[] = [
  { id: "stance_buy", label: "Waterfall BUY only", tip: TIPS.stance, modes: ["buy"] },
  { id: "below_target", label: "Below price target", tip: TIPS.vs_target },
  { id: "mos_pos", label: "MoS+", tip: TIPS.mos },
  { id: "mos_neg", label: "MoS−", tip: TIPS.mos },
  { id: "compl_ab", label: "Completeness A|B", tip: TIPS.completeness },
  { id: "fresh", label: "Fresh", tip: TIPS.freshness },
  { id: "no_kill", label: "No kill", tip: TIPS.kill },
  { id: "retention_known", label: "Retention disclosed", tip: TIPS.retention },
  { id: "rd_contrib", label: "R&D prod in score", tip: TIPS.rd_prod },
]

function passesFactors(
  r: RankedRow,
  factors: Set<FactorId>,
  stanceByTicker: Map<string, StanceListRow>
): boolean {
  if (factors.has("stance_buy")) {
    const s = stanceByTicker.get(r.ticker)
    if (!s || s.stance !== "BUY") return false
  }
  if (factors.has("below_target") && !(r.vs_median_pct != null && r.vs_median_pct > 0)) return false
  if (factors.has("mos_pos") && !(r.mos_live != null && r.mos_live > 0)) return false
  if (factors.has("mos_neg") && !(r.mos_live != null && r.mos_live <= 0)) return false
  if (factors.has("compl_ab") && !(r.completeness_grade === "A" || r.completeness_grade === "B")) return false
  if (factors.has("fresh") && !r.freshness_ok) return false
  if (factors.has("no_kill") && r.kill_active !== false) return false
  if (factors.has("retention_known") && r.retention == null) return false
  if (factors.has("rd_contrib") && !(r.contributions && "rd_prod" in r.contributions)) return false
  return true
}

const CSV_COLS = [
  { key: "ticker" as const, header: "Ticker" },
  { key: "score" as const, header: "Score" },
  { key: "mos_live" as const, header: "MoS" },
  { key: "vs_median_pct" as const, header: "VsTarget" },
  { key: "retention" as const, header: "Retention" },
  { key: "completeness_grade" as const, header: "Completeness" },
  { key: "kill_active" as const, header: "Kill" },
  { key: "stance" as const, header: "Stance" },
  { key: "price_live" as const, header: "Live" },
  { key: "sell_ceil" as const, header: "SellCeil" },
  { key: "upside_to_ceil" as const, header: "UpsideToCeil" },
]

export function UniversePage() {
  const selectEnabled = universeBookSelectEnabled()
  const [params, setParams] = useSearchParams()
  const mode = (["buy", "etf", "all"].includes(params.get("mode") || "")
    ? params.get("mode")
    : "buy") as Mode
  const q = params.get("q") || ""
  const reviewR3 = mode === "buy" && params.get("review") === "1"
  const requestedUniverseVersion = params.get("universe_version") || undefined

  const [rank, setRank] = useState<RankResponse | null>(null)
  const [stances, setStances] = useState<StanceListRow[]>([])
  const [stanceCoverage, setStanceCoverage] = useState<{
    analyzed: number
    universe: number
  } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [bookMsg, setBookMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [adding, setAdding] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  /** What to Buy: show only the top-10 cleared BUYs by score (default on). */
  const [pick10Only, setPick10Only] = useState(true)
  const selectionScopeRef = useRef<string | null>(null)
  const requestGenerationRef = useRef(0)
  const [factors, setFactors] = useState<Set<FactorId>>(
    () => (mode === "buy" && !reviewR3 ? new Set(["stance_buy"]) : new Set())
  )

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v)
    else next.delete(k)
    setParams(next, { replace: true })
  }

  const load = useCallback(async (signal: AbortSignal) => {
    const generation = ++requestGenerationRef.current
    setLoading(true)
    setError(null)
    setRank(null)
    setStances([])
    setStanceCoverage(null)
    const recipeId = mode === "etf" ? "R4" : mode === "buy" ? "R3" : "R7"
    const includeExcluded = mode === "all"
    try {
      const r = await getRank(recipeId, requestedUniverseVersion, includeExcluded, signal)
      // The stance waterfall is derived from exactly the rank response's
      // immutable universe, not a second floating "latest" lookup.
      const s =
        mode === "buy"
          ? await getResearchStances(undefined, undefined, r.universe_version, signal)
          : { rows: [] as StanceListRow[], n_analyzed: 0, n_universe: 0 }
      if (signal.aborted || generation !== requestGenerationRef.current) return
      setRank(r)
      setStances(s.rows || [])
      setStanceCoverage(
        mode === "buy"
          ? {
              analyzed: s.n_analyzed ?? s.rows.length,
              universe: s.n_universe ?? s.rows.length,
            }
          : null
      )
    } catch (e) {
      if (signal.aborted || generation !== requestGenerationRef.current) return
      setRank(null)
      setStances([])
      setStanceCoverage(null)
      setError(String(e))
    } finally {
      if (!signal.aborted && generation === requestGenerationRef.current) setLoading(false)
    }
  }, [mode, requestedUniverseVersion])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  const stanceByTicker = useMemo(() => {
    const m = new Map<string, StanceListRow>()
    for (const s of stances) m.set(s.ticker, s)
    return m
  }, [stances])

  const toggleFactor = (id: FactorId) => {
    setFactors((prev) => {
      const next = new Set(prev)
      if (id === "mos_pos") next.delete("mos_neg")
      if (id === "mos_neg") next.delete("mos_pos")
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectMode = (nextMode: Mode) => {
    setFactors(nextMode === "buy" ? new Set(["stance_buy"]) : new Set())
    setSortKey(null)
    setSelected(new Set())
    setPick10Only(nextMode === "buy")
    const next = new URLSearchParams(params)
    next.set("mode", nextMode)
    next.delete("review")
    setParams(next, { replace: true })
  }

  const openReview = () => {
    setFactors(new Set())
    setSortKey(null)
    setSelected(new Set())
    const next = new URLSearchParams(params)
    next.set("mode", "buy")
    next.set("review", "1")
    setParams(next, { replace: true })
  }

  const returnToBuyOnly = () => {
    setFactors(new Set(["stance_buy"]))
    setSortKey(null)
    setPick10Only(true)
    setSelected(new Set(top10Buys.map((row) => row.ticker)))
    const next = new URLSearchParams(params)
    next.set("mode", "buy")
    next.delete("review")
    setParams(next, { replace: true })
  }

  const rankedRows = useMemo(() => {
    if (!rank) return [] as RankedRow[]
    let list = [...rank.rows]
    if (q.trim()) {
      const needle = q.trim().toLowerCase()
      list = list.filter(
        (r) => r.ticker.toLowerCase().includes(needle) || (r.name || "").toLowerCase().includes(needle)
      )
    }
    if (factors.size) list = list.filter((r) => passesFactors(r, factors, stanceByTicker))
    if (sortKey) {
      const withStance = list.map((r) => {
        const sc = computeSellCeiling({
          fair_px_lo: r.fair_px_lo,
          fair_px_med: r.fair_px_med,
          fair_px_hi: r.fair_px_hi,
          price_live: r.price_live,
          stanceHorizon: stanceByTicker.get(r.ticker)?.horizon_years ?? null,
        })
        return {
          ...r,
          stance: stanceByTicker.get(r.ticker)?.stance ?? null,
          sell_ceil: sc.sell_ceil,
          upside_to_ceil: sc.upside_to_ceil,
        }
      })
      return sortRows(withStance, sortKey, sortDir) as RankedRow[]
    }
    if (mode === "buy") {
      list.sort((a, b) => {
        const sa = stanceByTicker.get(a.ticker)?.stance === "BUY" ? 1 : 0
        const sb = stanceByTicker.get(b.ticker)?.stance === "BUY" ? 1 : 0
        if (sb !== sa) return sb - sa
        return b.score - a.score
      })
    }
    return list
  }, [rank, q, factors, stanceByTicker, mode, sortKey, sortDir])

  const excludedRows = useMemo(() => {
    if (!rank?.excluded || mode !== "all") return [] as ExcludedRow[]
    let list = rank.excluded
    if (q.trim()) {
      const needle = q.trim().toLowerCase()
      list = list.filter(
        (e) => e.ticker.toLowerCase().includes(needle) || (e.name || "").toLowerCase().includes(needle)
      )
    }
    if (factors.has("no_kill")) list = list.filter((e) => e.kill_active === false)
    if (factors.has("compl_ab")) {
      list = list.filter((e) => e.completeness_grade === "A" || e.completeness_grade === "B")
    }
    return list
  }, [rank, mode, q, factors])

  /**
   * The dense shortlist must use precisely the same filtered/sorted pipeline
   * as the count, selection, and export controls. "Top 10" means the first
   * ten cleared BUYs after the user's active search, factor chips, and sort.
   */
  const clearedBuyRows = useMemo(
    () =>
      mode === "buy"
        ? rankedRows.filter(
            (row) =>
              stanceByTicker.get(row.ticker)?.stance === "BUY" &&
              row.freshness_ok &&
              row.kill_active === false
          )
        : ([] as RankedRow[]),
    [mode, rankedRows, stanceByTicker]
  )
  const buyCount = clearedBuyRows.length
  const top10Buys = useMemo(() => clearedBuyRows.slice(0, 10), [clearedBuyRows])
  const top10TickerKey = top10Buys.map((row) => row.ticker).join("|")
  const selectionScope = `${mode}:${reviewR3}:${rank?.universe_version ?? "pending"}:${top10TickerKey}`

  useEffect(() => {
    if (selectionScopeRef.current === selectionScope) return
    const timer = window.setTimeout(() => {
      selectionScopeRef.current = selectionScope
      if (selectEnabled && mode === "buy" && !reviewR3) {
        setSelected(new Set(top10TickerKey ? top10TickerKey.split("|") : []))
        setPick10Only(true)
      } else {
        setSelected(new Set())
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [mode, reviewR3, selectEnabled, selectionScope, top10TickerKey])

  const displayRows =
    mode === "buy" && !reviewR3 && pick10Only
      ? top10Buys
      : rankedRows

  const allVisibleSelected =
    displayRows.length > 0 && displayRows.every((r) => selected.has(r.ticker))

  const toggleSelect = (ticker: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(ticker)) next.delete(ticker)
      else next.add(ticker)
      return next
    })
  }

  const toggleSelectAll = () => {
    setSelected((previous) => {
      const next = new Set(previous)
      for (const row of displayRows) {
        if (allVisibleSelected) next.delete(row.ticker)
        else next.add(row.ticker)
      }
      return next
    })
  }

  const selectTop10 = () => {
    setPick10Only(true)
    setSelected(new Set(top10Buys.map((r) => r.ticker)))
  }

  const onSort = (key: SortKey) => {
    const next = toggleSort(sortKey, sortDir, key)
    setSortKey(next.key)
    setSortDir(next.dir)
  }

  const exportCsv = () => {
    const rows = displayRows.map((r) => {
      const sc = computeSellCeiling({
        fair_px_lo: r.fair_px_lo,
        fair_px_med: r.fair_px_med,
        fair_px_hi: r.fair_px_hi,
        price_live: r.price_live,
        stanceHorizon: stanceByTicker.get(r.ticker)?.horizon_years ?? null,
      })
      return {
        ...r,
        stance: stanceByTicker.get(r.ticker)?.stance ?? null,
        sell_ceil: sc.sell_ceil,
        upside_to_ceil: sc.upside_to_ceil,
      }
    })
    const csv = rowsToCsv(rows, CSV_COLS)
    const blob = new Blob([csv], { type: "text/csv" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = `universe_${mode}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
  }

  const addSelectedToBook = async () => {
    const tickers = [...selected]
    if (!tickers.length) return
    const byTicker = new Map(
      (rank?.rows || []).map((r) => [
        r.ticker,
        {
          completeness_grade: r.completeness_grade,
          retention: r.retention,
          mos_live: r.mos_live,
          freshness_ok: r.freshness_ok,
          kill_active: r.kill_active,
        },
      ])
    )
    const warnings = softAddWarnings(tickers, byTicker)
    if (warnings.length) {
      const lines = warnings.map((w) => `${w.ticker}: ${w.reasons.join("; ")}`).join("\n")
      const ok = window.confirm(
        `Soft warnings on ${warnings.length} name(s):\n\n${lines}\n\nAdd to book anyway?`
      )
      if (!ok) return
    }
    setAdding(true)
    setBookMsg(null)
    setError(null)
    const res = await addTickersToPrimaryBook(tickers, rank?.universe_version)
    setAdding(false)
    if (!res.ok) {
      if ("breaches" in res && res.breaches) {
        setError(res.breaches.map((b) => b.detail).join(" · "))
      } else if ("error" in res) {
        setError(res.error)
      }
      return
    }
    setBookMsg(`Added ${res.added} new · book now ${res.holdings.length} holdings.`)
    setSelected(new Set())
  }

  const active = MODES.find((m) => m.id === mode)!
  const activeLabel = reviewR3 ? "R3 Candidate Review" : active.label
  const activeBlurb = reviewR3
    ? "Review-only rows from the R3 desk screen. These are not BUY recommendations; open a row for its full waterfall, or return to cleared BUYs."
    : active.blurb
  const showStanceCols = mode === "buy"

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 pb-28 sm:p-6 sm:pb-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-950">Universe</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-700">
            Three views. Full research columns stay on the table — hover dotted terms for definitions.
            Research only, not investment advice.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={exportCsv}
            disabled={!displayRows.length}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm font-medium text-black hover:bg-muted disabled:opacity-40"
          >
            Export CSV
          </button>
          <Link
            to="/app/book"
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm font-medium text-black hover:bg-muted"
          >
            My Book →
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => selectMode(m.id)}
            className={`min-h-11 rounded-lg border px-4 py-2 text-sm font-semibold ${
              mode === m.id
                ? "border-black bg-black text-white"
                : "border-border bg-white text-black hover:bg-muted"
            }`}
            title={`Recipe ${m.recipe}`}
          >
            {m.label}
            <span className="ml-1.5 text-[10px] font-normal opacity-70">{m.recipe}</span>
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3">
        <div className="text-sm font-semibold text-sky-950">
          {mode === "buy" && !reviewR3
            ? `What to Buy — top ${Math.min(10, buyCount)} matching cleared BUYs`
            : activeLabel}
        </div>
        <p className="mt-0.5 text-xs text-sky-900">
          {mode === "buy" && !reviewR3
            ? "Pre-selected top 10 after the current search, filters, and sort. All money is USD with comma grouping and at most four significant figures. Targets are research fair values, not price forecasts."
            : activeBlurb}
        </p>
        {rank && (
          <p className="mt-1 font-mono text-[11px] text-sky-800">
            {rank.recipe.recipe_id} · {rank.recipe.formula_exact} · {rank.n_ranked} ranked of{" "}
            {rank.n_universe}
            {mode === "buy" && (
              <>
                {" "}
                · {reviewR3 ? `${rank.n_ranked} review rows` : `${buyCount} cleared BUY`} · analysis{" "}
                {stanceCoverage?.analyzed ?? "…"}/{stanceCoverage?.universe ?? "…"} names
              </>
            )}
            {mode === "all" && rank.n_excluded != null ? ` · ${rank.n_excluded} also listed` : ""}
          </p>
        )}
        {mode === "buy" && (
          <div className="mt-2 flex flex-wrap gap-2">
            {!reviewR3 && (
              <>
                <button
                  type="button"
                  onClick={selectTop10}
                  className="rounded-lg border border-black bg-black px-3 py-1.5 text-xs font-semibold text-white"
                >
                  Reset top 10 selection
                </button>
                <button
                  type="button"
                  onClick={() => setPick10Only((v) => !v)}
                  className="rounded-lg border border-sky-800 bg-white px-3 py-1.5 text-xs font-semibold text-sky-950 hover:bg-sky-100"
                >
                  {pick10Only ? `Show all ${buyCount} BUYs` : "Show top 10 only"}
                </button>
                <button
                  type="button"
                  onClick={openReview}
                  className="rounded-lg border border-sky-800 bg-white px-3 py-1.5 text-xs font-semibold text-sky-950 hover:bg-sky-100"
                >
                  Review R3 candidates
                  {rank ? ` (${rank.n_ranked})` : ""}
                </button>
              </>
            )}
            {reviewR3 && (
              <button
                type="button"
                onClick={returnToBuyOnly}
                className="rounded-lg border border-black bg-black px-3 py-1.5 text-xs font-semibold text-white"
              >
                ← Back to cleared BUYs
              </button>
            )}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setParam("q", e.target.value)}
            placeholder="Search ticker or name…"
            className="h-11 w-full max-w-[220px] rounded-lg border border-border bg-background px-3 text-sm text-black"
          />
          <span className="text-xs text-neutral-600">
            {mode === "buy" && !reviewR3
              ? `${displayRows.length} in list`
              : reviewR3
                ? `${rankedRows.length} review rows`
                : `${rankedRows.length} shown`}
            {mode === "all" ? ` · ${excludedRows.length} other` : ""}
            {mode === "buy" ? ` · ${buyCount} BUY` : ""}
            {selectEnabled && selected.size > 0 ? ` · ${selected.size} selected` : ""}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {mode === "buy" && reviewR3 ? (
            <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
              Review mode · not BUY — factor chips available
            </span>
          ) : (
            <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
              Filter by
            </span>
          )}
          {FACTORS.filter((f) => !f.modes || f.modes.includes(mode)).map((f) => (
            <button
              key={f.id}
              type="button"
              title={f.tip}
              onClick={() => toggleFactor(f.id)}
              className={`min-h-11 rounded-full border px-2.5 py-1 text-[11px] font-medium sm:min-h-0 ${
                factors.has(f.id)
                  ? "border-black bg-black text-white"
                  : "border-border bg-white text-neutral-800 hover:bg-muted"
              }`}
            >
              {f.label}
            </button>
          ))}
          {factors.size > 0 && (
            <button
              type="button"
              onClick={() => setFactors(new Set())}
              className="text-[11px] text-sky-800 underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}
      {bookMsg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          {bookMsg}{" "}
          <Link to="/app/book" className="font-semibold underline">
            Open Book
          </Link>
        </div>
      )}
      {loading && <div className="p-8 text-center text-sm text-neutral-600">Loading…</div>}

      {rank && !loading && mode === "buy" && !reviewR3 && (
        <div className="overflow-hidden rounded-xl border border-border bg-white">
          <div className="flex flex-wrap items-center gap-2 border-b border-border bg-neutral-100 px-3 py-2 text-[11px] uppercase tracking-wide text-neutral-600">
            {selectEnabled && (
              <label className="inline-flex min-h-11 items-center gap-2 normal-case tracking-normal">
                <input
                  type="checkbox"
                  className="h-5 w-5"
                  checked={allVisibleSelected}
                  onChange={toggleSelectAll}
                  aria-label="Select all visible"
                />
                Select all
              </label>
            )}
            <span className="font-semibold text-neutral-800">
              {pick10Only ? "Top 10 matching cleared BUYs" : `All ${buyCount} matching cleared BUYs`}
            </span>
            <span className="flex flex-wrap items-center gap-1 normal-case tracking-normal">
              <span className="mr-1 text-[10px] font-medium text-neutral-500">Sort shortlist:</span>
              {(
                [
                  ["score", "Score"],
                  ["mos_live", "MoS"],
                  ["completeness_grade", "Grade"],
                  ["vs_median_pct", "Vs target"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => onSort(key)}
                  className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                    sortKey === key
                      ? "border-neutral-800 bg-neutral-900 text-white"
                      : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-100"
                  }`}
                >
                  {label}
                  {sortKey === key ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                </button>
              ))}
            </span>
            <span className="ml-auto normal-case tracking-normal text-neutral-500">
              3 compact rows · valuation · financials · durable economics
            </span>
            <p className="basis-full border-t border-neutral-200 pt-2 normal-case tracking-normal text-neutral-700">
              <b>How to read this:</b> target = median research fair value; MoS = % below that target;
              net income* = revenue × net margin; FCF margin = SBC-adjusted free cash flow ÷ revenue;
              R&amp;D intensity = R&amp;D spend ÷ revenue; R&amp;D productivity = gross profit created per $1
              of cumulative R&amp;D. Quotes show their provider and as-of timestamp; financials carry the panel as-of date.
            </p>
          </div>
          {displayRows.length === 0 ? (
            <div className="px-3 py-8 text-center text-sm text-neutral-600">
              <div className="font-semibold text-neutral-900">No cleared BUY candidates right now.</div>
              <div className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-neutral-600">
                Names with an unknown catalyst or kill state stay out of BUY instead of being guessed.
              </div>
              {rank.n_ranked > 0 && (
                <button
                  type="button"
                  onClick={openReview}
                  className="mt-3 rounded-lg border border-black bg-black px-3 py-1.5 text-xs font-semibold text-white"
                >
                  Review {rank.n_ranked} R3 candidates
                </button>
              )}
            </div>
          ) : (
            displayRows.map((r, i) => (
              <BuyDenseRow
                key={r.ticker}
                r={r}
                displayRank={i + 1}
                stance={stanceByTicker.get(r.ticker)}
                selectEnabled={selectEnabled}
                selected={selected.has(r.ticker)}
                onToggle={() => toggleSelect(r.ticker)}
              />
            ))
          )}
        </div>
      )}

      {rank && !loading && !(mode === "buy" && !reviewR3) && (
        <div className="overflow-auto rounded-xl border border-border bg-white">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 z-10 bg-neutral-100 text-[11px] uppercase tracking-wide text-foreground/60">
              <tr>
                {selectEnabled && (
                  <th className="px-2 py-2.5 text-center">
                    <input
                      type="checkbox"
                      className="h-5 w-5"
                      checked={allVisibleSelected}
                      onChange={toggleSelectAll}
                      aria-label="Select all visible rows"
                    />
                  </th>
                )}
                <th className="px-3 py-2.5 text-right">#</th>
                <SortableHeader sk="ticker" align="left" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  Company
                </SortableHeader>
                {showStanceCols && (
                  <>
                    <SortableHeader sk="stance" align="left" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                      <Tip tip={TIPS.stance}>Stance</Tip>
                    </SortableHeader>
                    <th className="px-3 py-2.5 text-left">
                      <Tip tip={TIPS.confidence}>Conf.</Tip>
                    </th>
                    <th className="px-3 py-2.5 text-right">
                      <Tip tip={TIPS.horizon}>Horizon</Tip>
                    </th>
                  </>
                )}
                <SortableHeader sk="price_live" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>Quote (as-of)</SortableHeader>
                <SortableHeader sk="vs_median_pct" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.vs_target}>vs price target</Tip>
                </SortableHeader>
                <th className="px-3 py-2.5 text-left">
                  <Tip tip={TIPS.fair_guide}>Fair-value guide</Tip>
                </th>
                <SortableHeader sk="upside_to_ceil" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.sell_ceil}>Sell ceil</Tip>
                </SortableHeader>
                <SortableHeader sk="mos_live" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.mos}>MoS</Tip>
                </SortableHeader>
                <SortableHeader sk="retention" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.retention}>Retention</Tip>
                </SortableHeader>
                <SortableHeader sk="rev_cagr" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.rev_cagr}>Rev CAGR</Tip>
                </SortableHeader>
                <SortableHeader sk="score" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.score}>Score</Tip>
                </SortableHeader>
                <th className="px-3 py-2.5 text-left">
                  <Tip tip={TIPS.contributions}>Top factors</Tip>
                </th>
                <SortableHeader sk="completeness_grade" align="left" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.completeness}>Compl.</Tip>
                </SortableHeader>
                <th className="px-3 py-2.5 text-left">
                  <Tip tip={TIPS.freshness}>Fresh</Tip>
                </th>
                <SortableHeader sk="kill_active" align="left" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.kill}>Kill</Tip>
                </SortableHeader>
                {showStanceCols && <th className="px-3 py-2.5 text-left">Blockers</th>}
              </tr>
            </thead>
            <tbody>
              {rankedRows.length === 0 && (
                <tr>
                  <td colSpan={19} className="px-3 py-8 text-center text-sm text-neutral-600">
                    {mode === "buy" && !reviewR3 && factors.has("stance_buy") && !q.trim() ? (
                      <div className="mx-auto max-w-md space-y-2">
                        <div className="font-semibold text-neutral-900">No cleared BUY candidates right now.</div>
                        <div className="text-xs leading-relaxed text-neutral-600">
                          Names with an unknown catalyst or kill state stay out of BUY instead of being guessed.
                          Twelve names stay L4 UNKNOWN because L0 (≥25% drawdown) did not fire or no anchors
                          fell in the event window — fail-closed, not missing data.
                        </div>
                        {rank.n_ranked > 0 && (
                          <button
                            type="button"
                            onClick={openReview}
                            className="rounded-lg border border-black bg-black px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
                          >
                            Review {rank.n_ranked} R3 candidates
                          </button>
                        )}
                      </div>
                    ) : (
                      "No rows match the current filters. Clear chips or search."
                    )}
                  </td>
                </tr>
              )}
              {rankedRows.map((r, i) => (
                <RankRow
                  key={r.ticker}
                  r={r}
                  displayRank={i + 1}
                  stance={stanceByTicker.get(r.ticker)}
                  showStance={showStanceCols}
                  selectEnabled={selectEnabled}
                  selected={selected.has(r.ticker)}
                  onToggle={() => toggleSelect(r.ticker)}
                  sell={computeSellCeiling({
                    fair_px_lo: r.fair_px_lo,
                    fair_px_med: r.fair_px_med,
                    fair_px_hi: r.fair_px_hi,
                    price_live: r.price_live,
                    stanceHorizon: stanceByTicker.get(r.ticker)?.horizon_years ?? null,
                  })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rank && mode === "all" && !loading && excludedRows.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-neutral-950">
            Also in universe — not scored on this composite ({excludedRows.length})
          </h2>
          <div className="overflow-auto rounded-xl border border-border bg-white">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 z-10 bg-neutral-100 text-[11px] uppercase tracking-wide text-foreground/60">
                <tr>
                  <th className="px-3 py-2.5 text-left">Company</th>
                  <th className="px-3 py-2.5 text-left">Why not scored</th>
                  <th className="px-3 py-2.5 text-left">Compl.</th>
                  <th className="px-3 py-2.5 text-left">Route</th>
                </tr>
              </thead>
              <tbody>
                {excludedRows.map((e) => (
                  <tr key={e.ticker} className="border-t border-border/70 hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <Link
                        to={`/app/company/${e.ticker}?universe_version=${encodeURIComponent(rank.universe_version)}`}
                        className="!text-black font-bold hover:underline"
                      >
                        {e.ticker}
                      </Link>
                      <div className="text-[11px] text-neutral-700">{e.name || e.ticker}</div>
                      {e.description && (
                        <div className="mt-0.5 max-w-[360px] text-[11px] text-neutral-600">{e.description}</div>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-neutral-700">{e.reasons.join(" · ")}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${gradeTone(e.completeness_grade)}`}
                      >
                        {e.completeness_grade}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-neutral-600">{e.route}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectEnabled && selected.size > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 p-3 shadow-lg backdrop-blur sm:static sm:rounded-xl sm:border sm:shadow-none sm:backdrop-blur-none">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-neutral-900">{selected.size} selected</span>
            <button
              type="button"
              disabled={adding}
              onClick={addSelectedToBook}
              className="min-h-11 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
            >
              {adding
                ? "Adding…"
                : selected.size === 10
                  ? "Add top 10 to Book"
                  : `Add ${selected.size} to Book`}
            </button>
            <button
              type="button"
              onClick={() => setSelected(new Set())}
              className="min-h-11 text-sm text-neutral-600 underline"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function RankRow({
  r,
  displayRank,
  stance,
  showStance,
  selectEnabled,
  selected,
  onToggle,
  sell,
}: {
  r: RankedRow
  displayRank: number
  stance?: StanceListRow
  showStance: boolean
  selectEnabled: boolean
  selected: boolean
  onToggle: () => void
  sell: SellCeiling
}) {
  const stanceTone =
    stance?.stance === "BUY"
      ? "border-emerald-400 bg-emerald-50 text-emerald-900"
      : stance?.stance === "UNKNOWN"
        ? "border-neutral-300 bg-neutral-50 text-neutral-700"
        : stance
          ? "border-amber-300 bg-amber-50 text-amber-900"
          : ""

  return (
    <tr className="border-t border-border/70 align-top hover:bg-muted/30">
      {selectEnabled && (
        <td className="px-2 py-2.5 text-center">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={selected}
            onChange={onToggle}
            aria-label={`Select ${r.ticker}`}
          />
        </td>
      )}
      <td className="px-3 py-2.5 text-right tabular-nums text-neutral-600">{displayRank}</td>
      <td className="px-3 py-2.5">
        <Link
          to={`/app/company/${r.ticker}?universe_version=${encodeURIComponent(r.universe_version)}${
            showStance ? "&tab=stance" : ""
          }`}
          className="!text-black font-bold hover:underline"
        >
          {r.ticker}
        </Link>
        <div className="text-[11px] font-medium leading-tight text-neutral-800">
          {r.name || r.ticker}
          {r.industry ? (
            <span className="font-normal text-neutral-500"> · {r.industry.replace("Software - ", "")}</span>
          ) : null}
        </div>
        {r.description && (
          <div className="mt-0.5 max-w-[360px] text-[11px] leading-snug text-neutral-600">{r.description}</div>
        )}
      </td>
      {showStance && (
        <>
          <td className="px-3 py-2.5">
            {stance ? (
              <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${stanceTone}`}>
                {stance.stance}
              </span>
            ) : (
              <span
                className="rounded border border-neutral-200 bg-neutral-50 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600"
                title="On the MoS+ desk shortlist. Open Stance tab — BUY only when catalyst waterfall clears."
              >
                desk
              </span>
            )}
          </td>
          <td className="px-3 py-2.5 text-[11px] capitalize text-neutral-700">
            {stance?.confidence ?? "—"}
          </td>
          <td className="px-3 py-2.5 text-right tabular-nums">
            {stance?.horizon_years != null ? (
              <>
                <div className="font-semibold">{stance.horizon_years}y</div>
                {stance.implied_ann_return != null && (
                  <div className="text-[10px] text-neutral-600">
                    ≈{(stance.implied_ann_return * 100).toFixed(0)}%/yr
                  </div>
                )}
              </>
            ) : (
              <span className="text-neutral-400">—</span>
            )}
          </td>
        </>
      )}
      <td className="px-3 py-2.5 text-right tabular-nums">
        {r.price_live != null ? (
          <>
            <div className="font-semibold text-black">{formatUsd4(r.price_live)}</div>
            <div className="text-[9px] text-neutral-500">
              {r.price_is_derived
                ? "research price basis"
                : `${r.price_source || "quote"}${r.price_as_of ? ` · ${String(r.price_as_of).slice(0, 10)}` : ""}`}
              {r.price_stale ? " · stale" : ""}
            </div>
            {r.price_change_pct != null && (
              <div className={`text-[10px] ${r.price_change_pct >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                {formatPercent4(r.price_change_pct, true)}
              </div>
            )}
          </>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-right tabular-nums">
        {r.vs_median_pct != null ? (
          <>
            <div className={`font-semibold ${r.vs_median_pct >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
              {formatPercent4(r.vs_median_pct, true)}
            </div>
            {r.vs_median_usd != null && (
              <div className={`text-[10px] ${r.vs_median_usd >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                {formatUsd4(r.vs_median_usd)}
              </div>
            )}
            <div className="text-[9px] text-neutral-500">
              {r.vs_median_pct >= 0 ? "below target" : "above target"}
            </div>
          </>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 whitespace-nowrap font-mono text-[11px] text-neutral-800">
        {r.fair_px_lo != null && r.fair_px_hi != null ? (
          <>
            <div>
              {formatUsd4(r.fair_px_lo)} – <b>{formatUsd4(r.fair_px_med)}</b> – {formatUsd4(r.fair_px_hi)}
            </div>
            <div className="font-sans text-[9px] text-neutral-500">low · median · high</div>
          </>
        ) : (
          "—"
        )}
      </td>
      <td className="px-3 py-2.5 text-right tabular-nums" title={sell.note}>
        {sell.sell_ceil != null ? (
          <>
            <div
              className={`font-semibold ${
                sell.zone === "past_ceiling"
                  ? "text-amber-800"
                  : sell.zone === "in_upper_band"
                    ? "text-sky-900"
                    : "text-black"
              }`}
            >
              {formatUsd4(sell.sell_ceil)}
            </div>
            {sell.zone === "past_ceiling" ? (
              <div className="text-[10px] font-medium text-amber-800">past ceiling</div>
            ) : (
              <>
                <div className="text-[10px] text-neutral-700">
                  {fmtSellUpside(sell.upside_to_ceil)}
                  {sell.horizon_years != null ? ` · ${sell.horizon_years}y` : ""}
                </div>
                {sell.remaining_ann != null && (
                  <div className="text-[10px] text-emerald-800">≈{fmtSellAnn(sell.remaining_ann)}</div>
                )}
              </>
            )}
            <div className="text-[9px] text-neutral-500">
              {sell.lens === "median"
                ? "auto @ median"
                : sell.lens === "high"
                  ? sell.zone === "past_ceiling"
                    ? "through high"
                    : "trim @ high"
                  : "—"}
            </div>
          </>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-right tabular-nums">
        {r.mos_live != null ? (
          <span
            className={
              r.mos_live > 1
                ? "font-semibold text-amber-800"
                : r.mos_live > 0
                  ? "text-emerald-700"
                  : "text-rose-700"
            }
            title={r.mos_live > 1 ? "MoS > 100% — verify DCF inputs" : undefined}
          >
            {formatPercent4(r.mos_live, true)}
            {r.mos_live > 1 ? " ⚠" : ""}
          </span>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-right tabular-nums text-[11px]">
        {r.retention != null ? formatPercent4(r.retention) : <span className="text-neutral-400">unk</span>}
      </td>
      <td className="px-3 py-2.5 text-right tabular-nums text-[11px]">
        {r.rev_cagr != null ? (
          <span className={r.rev_cagr >= 0 ? "text-neutral-800" : "text-rose-700"}>
            {formatPercent4(r.rev_cagr, true)}
          </span>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-right font-medium tabular-nums text-black">{formatNumber4(r.score)}</td>
      <td className="px-3 py-2.5">
        <span className="font-mono text-[10px] text-neutral-700">
          {Object.entries(r.contributions)
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
            .slice(0, 3)
            .map(([k, v]) => `${k} ${v >= 0 ? "+" : ""}${formatNumber4(v)}`)
            .join(" · ")}
        </span>
      </td>
      <td className="px-3 py-2.5">
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${gradeTone(r.completeness_grade)}`}>
          {r.completeness_grade}
        </span>
      </td>
      <td className="px-3 py-2.5 text-[11px]">
        {r.freshness_ok ? (
          <span className="text-emerald-700">fresh</span>
        ) : (
          <span className="font-medium text-amber-800">stale</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-[11px]">
        {r.kill_active === true ? (
          <span className="font-semibold text-rose-700">KILL</span>
        ) : r.kill_active === false ? (
          <span className="text-neutral-400">—</span>
        ) : (
          <span className="font-medium text-amber-700">unknown</span>
        )}
      </td>
      {showStance && (
        <td className="max-w-[200px] px-3 py-2.5 text-[10px] leading-snug text-neutral-600">
          {stance?.blockers?.length ? stance.blockers.join(" · ") : "—"}
        </td>
      )}
    </tr>
  )
}
