/**
 * PATH: frontend/src/pages/portfolio/UniversePage.tsx
 * PURPOSE: Three modes — What to Buy · R&D Alpha ETF · All stocks.
 * Multi-select → server book; click-sort; CSV; factor chips; recipe pills.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ErrorBanner } from "@/components/research/ErrorBanner"
import { ScreenerHeader, ScreenerRow } from "@/components/research/ScreenerRow"
import { BuyPerformanceBookPanel, SimulatedBuyStudyPanel } from "@/components/research/BuyPerformanceBook"
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
import { resolveBuyViewMode } from "@/lib/universeBuyView"
import { UniverseStrataView } from "@/pages/portfolio/UniverseStrataView"
import { isPrimaryFactor } from "@/lib/universeFilters"
import {
  computeSellCeiling,
  type SellCeiling,
} from "@/lib/sellCeiling"
import { formatNumber4, formatPercent4, formatUsd4 } from "@/lib/formatMetrics"

type Mode = "buy" | "etf" | "all"

const MODES: { id: Mode; label: string; blurb: string; recipe: string }[] = [
  {
    id: "buy",
    label: "What to Buy?",
    recipe: "R3",
    blurb: "Stocks our screen ranks highest right now. Tap a ticker for the full research write-up.",
  },
  {
    id: "etf",
    label: "R&D Alpha ETF",
    recipe: "R4",
    blurb: "R&D-focused ranking used for the paper portfolio.",
  },
  {
    id: "all",
    label: "Universe (All stocks)",
    recipe: "R7",
    blurb: "Every name in the research universe. Use filters to narrow the list.",
  },
]

const TIPS: Record<string, string> = {
  vs_target:
    "Live gap vs research price target: (target − live price) / live price. Positive = trading below target. Prefer this filter for tape-relative screening.",
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
  mos:
    "Frozen research MoS from the sealed snapshot — not live intrinsic value. May differ from live vs-target. BUY also requires live vs-target > 0 (F3b).",
  rd_prod: "R&D productivity (Paper-1) — how well R&D spend converts to economics.",
  retention: "Disclosed NRR / retention from 10-K. Unknown = not disclosed — never estimated.",
  rev_cagr: "Revenue CAGR from fundamentals. Negative = shrinking top line.",
  stance:
    "Close-call waterfall verdict. BUY = underwriting clearance (not an order): kill off + completeness A|B + sealed MoS>0 + live vs-target>0 + named catalyst + score≥65. FCF is advisory only. ≠ paper HML_RD.",
  horizon:
    "Years over which the live→target gap would need to close for the implied annualized rate. Convergence math — not a forecast and not a sizing input.",
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
  { id: "below_target", label: "Below target", tip: TIPS.vs_target },
  { id: "mos_pos", label: "Undervalued", tip: TIPS.mos },
  { id: "fresh", label: "Fresh data", tip: TIPS.freshness },
  { id: "stance_buy", label: "Cleared BUY only", tip: TIPS.stance, modes: ["buy"] },
  { id: "mos_neg", label: "Overvalued", tip: TIPS.mos },
  { id: "compl_ab", label: "Filing quality A/B", tip: TIPS.completeness },
  { id: "no_kill", label: "No kill flag", tip: TIPS.kill },
  { id: "retention_known", label: "Retention known", tip: TIPS.retention },
  { id: "rd_contrib", label: "R&D productivity", tip: TIPS.rd_prod },
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
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const mode = (["buy", "etf", "all"].includes(params.get("mode") || "")
    ? params.get("mode")
    : "buy") as Mode
  const q = params.get("q") || ""
  const buyView = resolveBuyViewMode(params)
  const strataView = mode === "buy" && buyView === "strata"
  const reviewR3 = mode === "buy" && buyView === "candidates"
  const requestedUniverseVersion = params.get("universe_version") || undefined

  const [rank, setRank] = useState<RankResponse | null>(null)
  const [stances, setStances] = useState<StanceListRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [bookMsg, setBookMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [adding, setAdding] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  /** Cleared-BUY shortlist: top-10 by score (only when that view is active). */
  const [pick10Only, setPick10Only] = useState(() => mode === "buy" && buyView === "cleared")
  const [showMoreFilters, setShowMoreFilters] = useState(false)
  const selectionScopeRef = useRef<string | null>(null)
  const requestGenerationRef = useRef(0)
  const [factors, setFactors] = useState<Set<FactorId>>(
    () => (mode === "buy" && buyView === "cleared" ? new Set(["stance_buy"]) : new Set())
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
    } catch (e) {
      if (signal.aborted || generation !== requestGenerationRef.current) return
      setRank(null)
      setStances([])
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
    // What to Buy opens on the three-strata decision surface (plain params).
    setFactors(new Set())
    setSortKey(null)
    setSelected(new Set())
    setPick10Only(false)
    const next = new URLSearchParams(params)
    next.set("mode", nextMode)
    next.delete("review")
    next.delete("cleared")
    setParams(next, { replace: true })
  }

  const openStrata = () => {
    setFactors(new Set())
    setSortKey(null)
    setSelected(new Set())
    setPick10Only(false)
    const next = new URLSearchParams(params)
    next.set("mode", "buy")
    next.delete("review")
    next.delete("cleared")
    setParams(next, { replace: true })
  }

  const openReview = () => {
    setFactors(new Set())
    setSortKey(null)
    setSelected(new Set())
    setPick10Only(false)
    const next = new URLSearchParams(params)
    next.set("mode", "buy")
    next.set("review", "1")
    next.delete("cleared")
    setParams(next, { replace: true })
  }

  const returnToBuyOnly = () => {
    setFactors(new Set(["stance_buy"]))
    setSortKey(null)
    setPick10Only(true)
    setSelected(new Set(top10Buys.map((row) => row.ticker)))
    const next = new URLSearchParams(params)
    next.set("mode", "buy")
    next.set("cleared", "1")
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
  const selectionScope = `${mode}:${buyView}:${rank?.universe_version ?? "pending"}:${top10TickerKey}`

  useEffect(() => {
    if (selectionScopeRef.current === selectionScope) return
    const timer = window.setTimeout(() => {
      selectionScopeRef.current = selectionScope
      if (selectEnabled && mode === "buy" && buyView === "cleared") {
        setSelected(new Set(top10TickerKey ? top10TickerKey.split("|") : []))
        setPick10Only(true)
      } else {
        setSelected(new Set())
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [mode, buyView, selectEnabled, selectionScope, top10TickerKey])

  const displayRows =
    mode === "buy" && buyView === "cleared" && pick10Only
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
    const res = await addTickersToPrimaryBook(tickers, rank?.universe_version, {
      applyConstructionProxy: strataView,
    })
    setAdding(false)
    if (!res.ok) {
      if ("breaches" in res && res.breaches) {
        setError(res.breaches.map((b) => b.detail).join(" · "))
      } else if ("error" in res) {
        setError(res.error)
      }
      return
    }
    setBookMsg(
      `Added ${res.added} new · book now ${res.holdings.length} holdings` +
        (res.proxyApplied ? " · construction proxy weights applied" : "") +
        "."
    )
    setSelected(new Set())
    // Build-portfolio flow: land on the book, where the sizing wall
    // (max_factor_sizing, bound 0 today) is immediately visible.
    if (strataView) navigate("/app/book")
  }

  const active = MODES.find((m) => m.id === mode)!
  const activeLabel = strataView
    ? `Select your portfolio — ${buyCount} complete ${buyCount === 1 ? "thesis" : "theses"}`
    : reviewR3
      ? `What to Buy — ${rank?.n_ranked ?? "…"} ranked names`
      : `Cleared BUY shortlist — ${buyCount}`
  const activeBlurb = strataView
    ? "Three strata: complete theses (every gate passed) → near-misses (one named blocker) → weave rank (ordering only)."
    : reviewR3
      ? "Metric columns on the left. Score card (quality + why) on the right. Hover for definitions."
      : "Only names that fully cleared the research BUY gates. Often empty — use ranked names above."
  const showStanceCols = mode === "buy"
  const visibleFactors = FACTORS.filter((f) => {
    if (f.modes && !f.modes.includes(mode)) return false
    if (showMoreFilters) return true
    return isPrimaryFactor(f.id)
  })

  // Honest empty state: when zero theses clear, the strata view says so plainly.
  // We never silently swap ranked candidates in as if they were cleared —
  // the old auto-fallback to review=1 is intentionally gone.

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 pb-28 sm:p-6 sm:pb-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-950">Universe</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-700">
            Find names, compare price vs our research target, add to your book. Not investment advice.
          </p>
          <p className="mt-2 max-w-2xl text-[12px] leading-snug text-neutral-600">
            Research BUY is underwriting clearance — not an order and not a size. Do not auto-size from
            implied %/yr. MoS ≠ live IV. FCF advisory ≠ underwrite. Paper HML_RD ≠ this BUY engine.
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

      {mode === "buy" && (
        <>
          <BuyPerformanceBookPanel universeVersion={rank?.universe_version} />
          <SimulatedBuyStudyPanel />
        </>
      )}

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
          {mode === "buy" ? activeLabel : active.label}
        </div>
        <p className="mt-0.5 text-xs text-sky-900">
          {mode === "buy" ? activeBlurb : active.blurb}
        </p>
        {rank && (
          <p className="mt-1 text-[11px] text-sky-800">
            {rank.n_ranked} of {rank.n_universe} names pass this screen
            {mode === "buy" && buyCount > 0 ? ` · ${buyCount} cleared BUY` : ""}
            {mode === "all" && rank.n_excluded != null ? ` · ${rank.n_excluded} also listed` : ""}
          </p>
        )}
        {mode === "buy" && (
          <div className="mt-2 flex flex-wrap gap-2">
            {!strataView && (
              <button
                type="button"
                onClick={openStrata}
                className="rounded-lg border border-black bg-black px-3 py-1.5 text-xs font-semibold text-white"
              >
                Portfolio selection (strata)
              </button>
            )}
            {!reviewR3 && (
              <button
                type="button"
                onClick={openReview}
                className="rounded-lg border border-sky-800 bg-white px-3 py-1.5 text-xs font-semibold text-sky-950 hover:bg-sky-100"
              >
                Ranked list ({rank?.n_ranked ?? 0})
              </button>
            )}
            {buyView !== "cleared" && (
              <button
                type="button"
                onClick={returnToBuyOnly}
                className="rounded-lg border border-sky-800 bg-white px-3 py-1.5 text-xs font-semibold text-sky-950 hover:bg-sky-100"
              >
                Cleared BUY only ({buyCount})
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
            className="h-11 w-full max-w-md rounded-lg border border-border bg-background px-3 text-sm text-black"
          />
          <span className="text-xs text-neutral-600">
            {displayRows.length} shown
            {selectEnabled && selected.size > 0 ? ` · ${selected.size} selected` : ""}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-neutral-500">Quick filters</span>
          {visibleFactors.map((f) => (
            <button
              key={f.id}
              type="button"
              title={f.tip}
              onClick={() => toggleFactor(f.id)}
              className={`min-h-9 rounded-lg border px-2.5 py-1 text-[12px] font-medium ${
                factors.has(f.id)
                  ? "border-black bg-black text-white"
                  : "border-border bg-white text-neutral-800 hover:bg-muted"
              }`}
            >
              {f.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowMoreFilters((v) => !v)}
            className="min-h-9 rounded-lg border border-dashed border-neutral-300 px-2.5 py-1 text-[12px] font-medium text-neutral-700 hover:bg-muted"
          >
            {showMoreFilters ? "Fewer filters" : "More filters"}
          </button>
          {factors.size > 0 && (
            <button
              type="button"
              onClick={() => setFactors(new Set())}
              className="text-[12px] text-sky-800 underline"
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

      {rank && !loading && strataView && (
        <UniverseStrataView
          rows={rankedRows}
          stanceByTicker={stanceByTicker}
          universeVersion={rank.universe_version}
          selectEnabled={selectEnabled}
          selected={selected}
          onToggle={toggleSelect}
        />
      )}

      {rank && !loading && mode === "buy" && !strataView && (
        <div className="rounded-xl border border-border bg-white">
          <div className="flex flex-wrap items-center gap-2 border-b border-border bg-neutral-50 px-3 py-2">
            {selectEnabled && (
              <label className="inline-flex items-center gap-2 text-xs text-neutral-700">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={allVisibleSelected}
                  onChange={toggleSelectAll}
                  aria-label="Select all visible"
                />
                Select all
              </label>
            )}
            <div className="ml-auto flex flex-wrap gap-1">
              {(
                [
                  ["score", "Score"],
                  ["mos_live", "MoS"],
                  ["vs_median_pct", "vs target"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => onSort(key)}
                  className={`rounded border px-2 py-1 text-[11px] font-medium ${
                    sortKey === key
                      ? "border-neutral-800 bg-neutral-900 text-white"
                      : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-100"
                  }`}
                >
                  Sort: {label}
                  {sortKey === key ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                </button>
              ))}
            </div>
          </div>
          <ScreenerHeader />
          {displayRows.length === 0 ? (
            <div className="px-3 py-10 text-center text-sm text-neutral-600">
              <div className="font-semibold text-neutral-900">No names match these filters.</div>
              <button
                type="button"
                onClick={() => setFactors(new Set())}
                className="mt-3 text-xs font-semibold text-sky-800 underline"
              >
                Clear filters
              </button>
            </div>
          ) : (
            displayRows.map((r, i) => (
              <ScreenerRow
                key={r.ticker}
                r={r}
                displayRank={i + 1}
                stance={stanceByTicker.get(r.ticker)}
                selectEnabled={selectEnabled}
                selected={selected.has(r.ticker)}
                onToggle={() => toggleSelect(r.ticker)}
                showStance={showStanceCols}
              />
            ))
          )}
        </div>
      )}

      {rank && !loading && mode !== "buy" && (
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
                <SortableHeader sk="price_live" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  Price
                </SortableHeader>
                <SortableHeader sk="vs_median_pct" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.vs_target}>vs target</Tip>
                </SortableHeader>
                <SortableHeader sk="mos_live" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.mos}>MoS</Tip>
                </SortableHeader>
                <SortableHeader sk="score" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  <Tip tip={TIPS.score}>Score</Tip>
                </SortableHeader>
                <SortableHeader sk="rev_cagr" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  Growth
                </SortableHeader>
                <SortableHeader sk="completeness_grade" align="left" activeKey={sortKey} activeDir={sortDir} onSort={onSort}>
                  Quality
                </SortableHeader>
              </tr>
            </thead>
            <tbody>
              {rankedRows.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-3 py-8 text-center text-sm text-neutral-600">
                    No rows match the current filters. Clear filters or search.
                  </td>
                </tr>
              )}
              {rankedRows.map((r, i) => (
                <RankRow
                  key={r.ticker}
                  r={r}
                  displayRank={i + 1}
                  stance={stanceByTicker.get(r.ticker)}
                  showStance={false}
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
                  compact
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
                ? "Building…"
                : strataView
                  ? `Build portfolio (${selected.size})`
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
  selectEnabled,
  selected,
  onToggle,
}: {
  r: RankedRow
  displayRank: number
  stance?: StanceListRow
  showStance: boolean
  selectEnabled: boolean
  selected: boolean
  onToggle: () => void
  sell: SellCeiling
  compact?: boolean
}) {
  return (
    <tr className="border-t border-border/70 hover:bg-muted/30">
      {selectEnabled && (
        <td className="px-2 py-2 text-center">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={selected}
            onChange={onToggle}
            aria-label={`Select ${r.ticker}`}
          />
        </td>
      )}
      <td className="px-3 py-2 text-right tabular-nums text-neutral-500">{displayRank}</td>
      <td className="px-3 py-2">
        <Link
          to={`/app/company/${r.ticker}?universe_version=${encodeURIComponent(r.universe_version)}`}
          className="!text-black font-bold hover:underline"
        >
          {r.ticker}
        </Link>
        <div className="truncate text-[11px] text-neutral-600">{r.name || r.ticker}</div>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-semibold">{formatUsd4(r.price_live)}</td>
      <td
        className={`px-3 py-2 text-right tabular-nums font-semibold ${
          r.vs_median_pct != null && r.vs_median_pct >= 0 ? "text-emerald-700" : "text-rose-700"
        }`}
      >
        {formatPercent4(r.vs_median_pct, true)}
      </td>
      <td
        className={`px-3 py-2 text-right tabular-nums font-semibold ${
          r.mos_live != null && r.mos_live > 0 ? "text-emerald-700" : "text-rose-700"
        }`}
      >
        {formatPercent4(r.mos_live, true)}
      </td>
      <td className="px-3 py-2 text-right font-semibold tabular-nums">{formatNumber4(r.score)}</td>
      <td className="px-3 py-2 text-right tabular-nums text-[12px]">{formatPercent4(r.rev_cagr, true)}</td>
      <td className="px-3 py-2">
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${gradeTone(r.completeness_grade)}`}>
          {r.completeness_grade}
        </span>
      </td>
    </tr>
  )
}
