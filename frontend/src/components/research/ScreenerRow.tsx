/**
 * Universe card — dense metric grid left, score explanation right.
 * No decorative empty space. Numbers come straight from the ranked row API.
 */
import { type ReactNode } from "react"
import { Link } from "react-router-dom"
import { type RankedRow, type StanceListRow } from "@/lib/api/universe"
import { fairBandLayout } from "@/lib/fairBand"
import { aboveBandFlag } from "@/lib/aboveBandPolicy"
import { formulaTip } from "@/lib/formulaRegistry"
import { decisionChainSummary } from "@/lib/decisionChains"
import { formatMultiple4, formatNumber4, formatPercent4, formatUsd4, formatUsdCompact } from "@/lib/formatMetrics"
import { mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"
import { computeSellCeiling, fmtSellUpside } from "@/lib/sellCeiling"
import {
  driverBarWidth,
  scoreDrivers,
  scoreQuality,
  type ScoreQualityLevel,
} from "@/lib/scoreBaseline"

function stanceTone(stance: string | undefined): string {
  if (stance === "BUY") return "border-emerald-300 bg-emerald-50 text-emerald-900"
  if (stance === "HOLD" || stance === "WATCH") return "border-amber-300 bg-amber-50 text-amber-900"
  if (stance === "OUT") return "border-rose-300 bg-rose-50 text-rose-900"
  return "border-neutral-200 bg-neutral-50 text-neutral-700"
}

/** Actionable close-call stances only — hide UNKNOWN/— noise on buy cards. */
export function isActionableStance(stance: string | null | undefined): boolean {
  return stance === "BUY" || stance === "HOLD" || stance === "WATCH" || stance === "OUT"
}

function gapTone(vs: number | null | undefined): string {
  if (vs == null) return "text-neutral-900"
  return vs > 0 ? "text-emerald-700" : "text-rose-700"
}

function qualityBadgeTone(level: ScoreQualityLevel): string {
  if (level === "strong") return "border-emerald-200 bg-emerald-50 text-emerald-800"
  if (level === "good") return "border-sky-200 bg-sky-50 text-sky-800"
  if (level === "blocked") return "border-rose-200 bg-rose-50 text-rose-800"
  return "border-amber-200 bg-amber-50 text-amber-800"
}

function gradeTextTone(g: string): string {
  if (g === "A" || g === "B") return "text-emerald-700"
  if (g === "C") return "text-amber-700"
  return "text-rose-700"
}

function zoneTone(zone: string): string {
  if (zone === "below") return "text-emerald-700"
  if (zone === "above") return "text-rose-700"
  if (zone === "inside") return "text-sky-800"
  return "text-neutral-500"
}

function HoverTip({
  tip,
  children,
  align = "left",
}: {
  tip: string
  children: ReactNode
  align?: "left" | "right"
}) {
  return (
    <span
      tabIndex={0}
      className="group relative inline-flex max-w-full cursor-help outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
    >
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute bottom-[calc(100%+6px)] z-[80] hidden w-56 rounded-md border border-neutral-700 bg-neutral-900 px-2.5 py-2 text-left text-[11px] font-normal leading-snug text-neutral-100 shadow-xl group-hover:block group-focus-within:block ${
          align === "right" ? "right-0" : "left-0"
        }`}
      >
        {tip}
      </span>
    </span>
  )
}

function Col({
  label,
  value,
  tip,
  tone = "text-neutral-900",
}: {
  label: string
  value: string
  tip: string
  tone?: string
}) {
  return (
    <HoverTip tip={tip}>
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">{label}</div>
        <div className={`mt-0.5 text-[13px] font-semibold tabular-nums leading-none ${tone}`}>{value}</div>
      </div>
    </HoverTip>
  )
}

function FairBand({
  price,
  lo,
  med,
  hi,
  suppressZoneLabel = false,
}: {
  price: number | null | undefined
  lo: number | null | undefined
  med: number | null | undefined
  hi: number | null | undefined
  /** When parent already shows an above-band chip, avoid duplicate zone text. */
  suppressZoneLabel?: boolean
}) {
  const layout = fairBandLayout(price ?? null, lo ?? null, med ?? null, hi ?? null)
  if (!layout) {
    return (
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">Fair band</div>
        <div className="mt-0.5 text-[13px] font-semibold text-neutral-400">—</div>
      </div>
    )
  }

  const tipZone = suppressZoneLabel
    ? "Price sits above the fair-value range (chip already shown)."
    : `${layout.zoneLabel}.`

  return (
    <HoverTip
      tip={`Fair value ${formatUsd4(lo)}–${formatUsd4(hi)}. Price ${formatUsd4(price)}. ${tipZone}`}
    >
      <div className="w-full min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">Fair band</span>
          {!suppressZoneLabel && (
            <span className={`text-[10px] font-semibold ${zoneTone(layout.zone)}`}>{layout.zoneLabel}</span>
          )}
        </div>
        <div className="relative mt-1.5 h-2 rounded-full bg-neutral-100">
          <div
            className="absolute inset-y-0 rounded-full bg-emerald-400/80"
            style={{ left: `${layout.bandLeft}%`, width: `${layout.bandWidth}%` }}
          />
          {layout.medPct != null && (
            <div
              className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-emerald-800/70"
              style={{ left: `${layout.medPct}%` }}
              aria-hidden
            />
          )}
          {layout.pricePct != null && (
            <div
              className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-neutral-900 shadow"
              style={{ left: `${layout.pricePct}%` }}
              aria-hidden
            />
          )}
        </div>
        <div className="mt-1 flex items-center justify-between gap-2 text-[10px] tabular-nums text-neutral-500">
          <span>{formatUsd4(lo)}</span>
          <span className="font-medium text-neutral-700">
            now {formatUsd4(price)}
            {med != null ? ` · tgt ${formatUsd4(med)}` : ""}
          </span>
          <span>{formatUsd4(hi)}</span>
        </div>
      </div>
    </HoverTip>
  )
}

export function ScreenerRow({
  r,
  displayRank,
  stance,
  selectEnabled,
  selected,
  onToggle,
  showStance,
}: {
  r: RankedRow
  displayRank: number
  stance?: StanceListRow
  selectEnabled: boolean
  selected: boolean
  onToggle: () => void
  showStance: boolean
}) {
  const sell = computeSellCeiling({
    fair_px_lo: r.fair_px_lo,
    fair_px_med: r.fair_px_med,
    fair_px_hi: r.fair_px_hi,
    price_live: r.price_live,
    stanceHorizon: stance?.horizon_years ?? null,
  })
  const quality = scoreQuality({
    completeness_grade: r.completeness_grade,
    freshness_ok: r.freshness_ok,
    kill_active: r.kill_active,
  })
  const drivers = scoreDrivers(r.contributions, 3)
  const maxAbs = Math.max(0, ...drivers.map((d) => Math.abs(d.contribution)))
  const industry = r.industry?.replace("Software - ", "") || null
  // Live gap is always (target − price) / price. MoS is the frozen research
  // field — only surface it when it actually disagrees with the live quote gap.
  const showMos = mosDiffersFromLiveGap(r.mos_live, r.vs_median_pct)
  const bandFlag = aboveBandFlag(r)

  return (
    <article
      className={`border-b border-neutral-200 px-3 py-2.5 sm:px-4 ${
        selected ? "bg-sky-50/40" : "bg-white hover:bg-neutral-50/70"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            {selectEnabled && (
              <input
                type="checkbox"
                className="h-4 w-4 shrink-0"
                checked={selected}
                onChange={onToggle}
                aria-label={`Select ${r.ticker}`}
              />
            )}
            <span className="w-5 shrink-0 text-right text-[11px] tabular-nums text-neutral-400">
              {displayRank}
            </span>
            <Link
              to={`/app/company/${r.ticker}?universe_version=${encodeURIComponent(r.universe_version)}${
                showStance ? "&tab=stance" : ""
              }`}
              className="!text-neutral-950 shrink-0 text-sm font-bold hover:underline"
            >
              {r.ticker}
            </Link>
            <span className="min-w-0 truncate text-[13px] text-neutral-700">
              {r.name || r.ticker}
              {industry ? <span className="text-neutral-400"> · {industry}</span> : null}
            </span>
            {bandFlag.active && (
              <HoverTip tip={bandFlag.detail}>
                <span className="shrink-0 rounded border border-rose-300 bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold text-rose-900">
                  {bandFlag.label}
                </span>
              </HoverTip>
            )}
            {showStance && isActionableStance(stance?.stance) && (
              <HoverTip
                tip={
                  stance?.blockers?.length
                    ? `${stance.stance}: ${stance.blockers.join(" · ")}`
                    : `Research stance: ${stance?.stance ?? "unavailable"}`
                }
              >
                <span
                  className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-bold ${stanceTone(
                    stance?.stance
                  )}`}
                >
                  {stance?.stance}
                </span>
              </HoverTip>
            )}
          </div>

          <div className="grid grid-cols-3 gap-x-3 gap-y-2 sm:grid-cols-6">
            <Col label="Price" value={formatUsd4(r.price_live)} tip="Latest quoted market price. [pass-through]" />
            <Col
              label="Target"
              value={formatUsd4(r.fair_px_med)}
              tip={formulaTip(
                "F_FAIR_BAND_ORDER",
                "Sealed research median target (panel/vector). Not a live DCF workbench replay."
              )}
            />
            <Col
              label="vs target"
              value={formatPercent4(r.vs_median_pct, true)}
              tip={formulaTip(
                "F_VS_MEDIAN_PCT",
                "Live gap vs sealed target. Positive = below target. May differ from frozen MoS (shown only when it disagrees)."
              )}
              tone={gapTone(r.vs_median_pct)}
            />
            <Col
              label="Sell ceiling"
              value={formatUsd4(sell.sell_ceil)}
              tip={
                sell.zone === "past_ceiling"
                  ? formulaTip("F_SELL_CEILING", "Already through the high fair-value lens.")
                  : formulaTip(
                      "F_SELL_CEILING",
                      `Auto sell/trim level. Upside: ${fmtSellUpside(sell.upside_to_ceil)}.`
                    )
              }
              tone={sell.zone === "past_ceiling" ? "text-amber-800" : "text-neutral-900"}
            />
            <Col
              label="Revenue"
              value={formatUsdCompact(r.revenue_usd)}
              tip={formulaTip(
                "F_FMT_USD_COMPACT",
                `Latest panel revenue. Exact: ${formatUsd4(r.revenue_usd)}.`
              )}
            />
            <Col
              label="ADV 20d"
              value={formatUsdCompact(r.adv_usd_20d ?? r.liquidity_usd)}
              tip={formulaTip(
                "F_ADV_USD_20D",
                r.tradability_note ||
                  "20-session average dollar volume from SEP cache. UNKNOWN when volume missing — not a size order."
              )}
            />
          </div>

          {showMos && (
            <div className="text-[11px] text-neutral-500">
              Research MoS{" "}
              <span className={`font-semibold tabular-nums ${gapTone(r.mos_live)}`}>
                {formatPercent4(r.mos_live, true)}
              </span>
              <span className="text-neutral-400"> — frozen; differs from live vs target</span>
            </div>
          )}

          <FairBand
            price={r.price_live}
            lo={r.fair_px_lo}
            med={r.fair_px_med}
            hi={r.fair_px_hi}
            suppressZoneLabel={bandFlag.active}
          />

          <div className="grid grid-cols-3 gap-x-3 gap-y-2 border-t border-neutral-100 pt-2 sm:grid-cols-6">
            <Col
              label="Growth"
              value={formatPercent4(r.rev_cagr, true)}
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "Revenue CAGR — sealed panel/vector pass-through (not re-derived in API)."
              )}
              tone={r.rev_cagr != null && r.rev_cagr >= 0 ? "text-emerald-700" : "text-rose-700"}
            />
            <Col
              label="Gross margin"
              value={formatPercent4(r.gm)}
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "Gross profit ÷ revenue — sealed pass-through (not re-derived in API)."
              )}
            />
            <Col
              label="FCF margin"
              value={formatPercent4(r.fcfm_sbc)}
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "SBC-adjusted FCF ÷ revenue — sealed pass-through (not re-derived in API)."
              )}
              tone={r.fcfm_sbc != null && r.fcfm_sbc >= 0 ? "text-emerald-700" : "text-rose-700"}
            />
            <Col
              label="ROIC"
              value={formatPercent4(r.roic)}
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "ROIC — sealed pass-through (not re-derived in API)."
              )}
            />
            <Col
              label="R&D productivity"
              value={formatMultiple4(r.rd_prod)}
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "GP per $1 cumulative R&D — sealed pass-through (Paper-1; not re-derived in API)."
              )}
            />
            <HoverTip
              tip={formulaTip(
                "F_PASS_THROUGH_FUNDAMENTALS",
                "Disclosed NRR/retention. Missing = not disclosed — never estimated."
              )}
            >
              <div className="min-w-0">
                <div className="text-[10px] font-medium uppercase tracking-wide text-neutral-500">Retention</div>
                <div className="mt-0.5 text-[13px] font-semibold leading-none text-neutral-800">
                  {r.retention != null ? formatPercent4(r.retention) : "n/d"}
                </div>
              </div>
            </HoverTip>
          </div>
        </div>

        {/* Score card — natural height, no stretch filler */}
        <aside className="hidden w-[12.5rem] shrink-0 sm:block lg:w-[13.5rem]">
          <div className="rounded-lg border border-sky-200 bg-sky-50/70">
            <div
              className="border-b border-sky-200 px-2.5 py-2"
              title={`${formulaTip("F_SCORE_ROBUST_Z", `${quality.label}. ${quality.baseline}`)} · ${decisionChainSummary("D_RANK_R3")}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Score</span>
                <span
                  className={`rounded-full border px-1.5 py-0.5 text-[10px] font-semibold leading-none ${qualityBadgeTone(
                    quality.level
                  )}`}
                >
                  {quality.label}
                </span>
              </div>
              <div className="mt-1 text-[28px] font-semibold tabular-nums leading-none tracking-tight text-slate-950">
                {formatNumber4(r.score)}
              </div>
              <p className="mt-1 text-[10px] leading-snug text-slate-500">{quality.baseline}</p>
              <p className="mt-1 text-[9px] leading-snug text-slate-400">
                Provenance: D_RANK_R3 · no imputation · rank ≠ BUY
                {bandFlag.active ? " · above fair band (flagged, not excluded)" : ""}
              </p>
            </div>

            <div className="grid grid-cols-3 divide-x divide-sky-200 border-b border-sky-200 bg-white/40 text-center">
              <HoverTip tip={`Filing evidence grade ${quality.filingGrade}. A/B = stronger underwrite base.`}>
                <div className="w-full px-1 py-1.5">
                  <div className="text-[9px] font-medium uppercase tracking-wide text-slate-400">Filing</div>
                  <div className={`mt-0.5 text-[11px] font-bold ${gradeTextTone(r.completeness_grade)}`}>
                    {quality.filingGrade}
                  </div>
                </div>
              </HoverTip>
              <HoverTip tip={quality.fresh ? "Fundamentals within refresh window." : "Fundamentals past refresh."}>
                <div className="w-full px-1 py-1.5">
                  <div className="text-[9px] font-medium uppercase tracking-wide text-slate-400">Data</div>
                  <div className={`mt-0.5 text-[11px] font-bold ${quality.fresh ? "text-emerald-700" : "text-amber-700"}`}>
                    {quality.fresh ? "Fresh" : "Stale"}
                  </div>
                </div>
              </HoverTip>
              <HoverTip tip={quality.kill ? "Kill flag active — not a buy signal." : "No kill flag on this name."}>
                <div className="w-full px-1 py-1.5">
                  <div className="text-[9px] font-medium uppercase tracking-wide text-slate-400">Kill</div>
                  <div className={`mt-0.5 text-[11px] font-bold ${quality.kill ? "text-rose-700" : "text-emerald-700"}`}>
                    {quality.kill ? "On" : "None"}
                  </div>
                </div>
              </HoverTip>
            </div>

            <div className="px-2.5 py-2">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Why this score</div>
              {drivers.length === 0 ? (
                <p className="mt-1 text-[11px] text-neutral-400">No factor drivers</p>
              ) : (
                <ul className="mt-1.5 space-y-1.5">
                  {drivers.map((d) => {
                    const width = driverBarWidth(d.contribution, maxAbs)
                    const positive = d.contribution >= 0
                    return (
                      <li key={d.key}>
                        <HoverTip
                          align="right"
                          tip={`${d.detail} Contribution: ${positive ? "+" : ""}${formatNumber4(d.contribution)}.`}
                        >
                          <div className="w-full">
                            <div className="flex items-baseline justify-between gap-2">
                              <span className="min-w-0 truncate text-[11px] text-slate-700">{d.label}</span>
                              <span
                                className={`shrink-0 text-[11px] font-semibold tabular-nums ${
                                  positive ? "text-emerald-700" : "text-rose-700"
                                }`}
                              >
                                {positive ? "+" : ""}
                                {formatNumber4(d.contribution)}
                              </span>
                            </div>
                            <div className="mt-0.5 h-0.5 overflow-hidden rounded-full bg-sky-100">
                              <div
                                className={`h-full rounded-full ${positive ? "bg-emerald-500" : "bg-rose-400"}`}
                                style={{ width: `${width}%` }}
                              />
                            </div>
                          </div>
                        </HoverTip>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </aside>
      </div>
    </article>
  )
}

export function ScreenerHeader() {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-neutral-200 bg-neutral-50 px-3 py-1.5 text-[11px] text-neutral-500 sm:px-4">
      <span className="font-semibold text-neutral-700">Cards</span>
      <span>metrics left · score right</span>
      <span>hover for definitions</span>
    </div>
  )
}

export { formatScoreDrivers } from "@/lib/scoreBaseline"
export { mosDiffersFromLiveGap } from "@/lib/rankRowInvariants"
