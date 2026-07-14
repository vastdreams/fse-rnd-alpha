/**
 * PATH: frontend/src/components/research/BuyDenseRow.tsx
 * PURPOSE: Compact 3-line company card for What-to-Buy — identity, valuation,
 * fundamentals (rev / growth / profit), and score-driving metrics.
 */
import { Link } from "react-router-dom"
import { gradeTone, type RankedRow, type StanceListRow } from "@/lib/api/universe"
import { formatMultiple4, formatNumber4, formatPercent4, formatUsd4, formatUsdCompact } from "@/lib/formatMetrics"
import {
  computeSellCeiling,
  fmtSellUpside,
} from "@/lib/sellCeiling"

const DRIVER_LABELS: Record<string, string> = {
  mos_live: "Value gap vs target",
  rd_prod: "R&D productivity",
  fcfm_sbc: "FCF margin",
  roic: "Return on capital",
  retention: "Net revenue retention",
  gm: "Gross margin",
  rule40: "Rule of 40",
}

function dateLabel(value: string | null | undefined): string {
  if (!value) return "panel date unavailable"
  const date = new Date(`${value}T00:00:00Z`)
  if (Number.isNaN(date.valueOf())) return value
  return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" }).format(date)
}

function MetricTile({
  label,
  value,
  meaning,
  title,
  tone = "text-neutral-950",
}: {
  label: string
  value: string
  meaning: string
  title: string
  tone?: string
}) {
  return (
    <div
      title={title}
      className="min-w-0 border-l border-neutral-200 pl-2 first:border-l-0 first:pl-0"
    >
      <div className="text-[9px] font-medium uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-0.5 break-words text-[12px] font-semibold leading-tight tabular-nums ${tone}`}>
        {value}
      </div>
      <div className="mt-0.5 text-[9px] leading-tight text-neutral-600">{meaning}</div>
    </div>
  )
}

export function BuyDenseRow({
  r,
  displayRank,
  stance,
  selectEnabled,
  selected,
  onToggle,
}: {
  r: RankedRow
  displayRank: number
  stance?: StanceListRow
  selectEnabled: boolean
  selected: boolean
  onToggle: () => void
}) {
  const sell = computeSellCeiling({
    fair_px_lo: r.fair_px_lo,
    fair_px_med: r.fair_px_med,
    fair_px_hi: r.fair_px_hi,
    price_live: r.price_live,
    stanceHorizon: stance?.horizon_years ?? null,
  })

  const drivers = Object.entries(r.contributions || {})
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 4)
  const grossProfitPeriod =
    r.fundamentals_baseline_as_of && r.fundamentals_as_of
      ? `${dateLabel(r.fundamentals_baseline_as_of)}–${dateLabel(r.fundamentals_as_of)}`
      : "panel baseline-to-latest period"

  const stanceTone =
    stance?.stance === "BUY"
      ? "border-emerald-400 bg-emerald-50 text-emerald-900"
      : stance?.stance === "UNKNOWN"
        ? "border-neutral-300 bg-neutral-50 text-neutral-700"
        : stance
          ? "border-amber-300 bg-amber-50 text-amber-900"
          : "border-neutral-200 bg-neutral-50 text-neutral-600"

  return (
    <div
      className={`border-b border-border/80 px-2 py-2 sm:px-3 ${
        selected ? "bg-sky-50/60" : "bg-white hover:bg-neutral-50/80"
      }`}
    >
      {/* Row 1 — identity + stance + score */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {selectEnabled && (
          <input
            type="checkbox"
            className="h-5 w-5 shrink-0"
            checked={selected}
            onChange={onToggle}
            aria-label={`Select ${r.ticker}`}
          />
        )}
        <span className="w-6 shrink-0 text-right text-[11px] tabular-nums text-neutral-500">
          {displayRank}
        </span>
        <Link
          to={`/app/company/${r.ticker}?universe_version=${encodeURIComponent(r.universe_version)}&tab=stance`}
          className="!text-black shrink-0 text-sm font-bold hover:underline"
        >
          {r.ticker}
        </Link>
        <span className="min-w-0 truncate text-[12px] font-medium text-neutral-800">
          {r.name || r.ticker}
          {r.industry ? (
            <span className="font-normal text-neutral-500">
              {" "}
              · {r.industry.replace("Software - ", "")}
            </span>
          ) : null}
        </span>
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${stanceTone}`}>
          {stance?.stance ?? "desk"}
        </span>
        {stance?.horizon_years != null && (
          <span className="text-[10px] tabular-nums text-neutral-600">
            {stance.horizon_years}y
            {stance.implied_ann_return != null && (
              <>
                {" "}
                · ≈{formatPercent4(stance.implied_ann_return, true)}/yr gap-close
                <span className="font-normal text-neutral-500"> (not a forecast · not a size)</span>
              </>
            )}
          </span>
        )}
        <span className="ml-auto text-[11px] font-semibold tabular-nums text-black">
          score {formatNumber4(r.score)}
        </span>
        <span className={`rounded border px-1 py-0.5 text-[10px] font-medium ${gradeTone(r.completeness_grade)}`}>
          {r.completeness_grade}
        </span>
      </div>

      <div className="mt-1 pl-0 text-[9px] text-neutral-500 sm:pl-14">
        {r.price_is_derived ? "research price basis" : r.price_source || "quote source"}
        {r.price_as_of ? ` as of ${r.price_as_of}` : ""} · financials as of {dateLabel(r.fundamentals_as_of)} · all money figures USD
        {r.price_stale ? " · quote stale" : ""}
        {" · "}
        ADV 20d {r.adv_usd_20d != null ? formatUsdCompact(r.adv_usd_20d) : "unknown"}
        <span className="text-neutral-400"> · capacity not auto-sized</span>
      </div>
      <div className="mt-1 pl-0 text-[9px] leading-snug text-neutral-600 sm:pl-14">
        Research BUY = underwriting clearance, not an order. MoS is frozen research MoS (not live IV).
        FCF match is advisory only. Paper HML_RD ≠ this BUY engine.
      </div>

      {/* Row 2 — valuation: exactly how the target and sell ceiling relate */}
      <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-2 pl-0 sm:grid-cols-5 sm:pl-14">
        <MetricTile
          label={r.price_as_of ? "Quote (as-of)" : "Quote"}
          value={formatUsd4(r.price_live)}
          meaning={
            r.price_is_derived
              ? "Research price basis"
              : `${r.price_source || "Market quote"}${r.price_stale ? " · stale" : ""}`
          }
          title="Quoted market price with source/as-of metadata; not a model estimate."
        />
        <MetricTile
          label="Research target"
          value={formatUsd4(r.fair_px_med)}
          meaning="Median fair value"
          title="Median of the triangulated fair-value lenses. This is the research price target."
        />
        <MetricTile
          label="Value band"
          value={`${formatUsd4(r.fair_px_lo)} – ${formatUsd4(r.fair_px_hi)}`}
          meaning="Low to high lens"
          title="Triangulated fair-value range: conservative low lens through optimistic high lens."
        />
        <MetricTile
          label="Sell ceiling"
          value={formatUsd4(sell.sell_ceil)}
          meaning={
            sell.zone === "past_ceiling"
              ? "Already through high lens"
              : sell.lens === "high"
                ? "Trim at high lens"
                : "Exit at median target"
          }
          title={sell.note}
          tone={sell.zone === "past_ceiling" ? "text-amber-800" : "text-sky-900"}
        />
        <MetricTile
          label="Margin of safety"
          value={formatPercent4(r.mos_live, true)}
          meaning={
            sell.zone === "past_ceiling"
              ? "No value gap remains"
              : `${fmtSellUpside(sell.upside_to_ceil)} to sell`
          }
          title="Percent that live price is below the median research target. Positive means the price is below target."
          tone={r.mos_live != null && r.mos_live > 0 ? "text-emerald-800" : "text-rose-800"}
        />
      </div>

      {/* Row 3 — financials: the operating inputs behind the fair-value guide */}
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-neutral-100 pt-2 pl-0 sm:grid-cols-5 sm:pl-14">
        <MetricTile
          label="FY revenue"
          value={formatUsd4(r.revenue_usd)}
          meaning="Latest panel revenue"
          title="Latest annual revenue in the research panel, in US dollars."
        />
        <MetricTile
          label="Revenue growth"
          value={formatPercent4(r.rev_cagr, true)}
          meaning="Annualized CAGR"
          title="Annualized compound revenue growth rate across the panel measurement window."
          tone={r.rev_cagr != null && r.rev_cagr >= 0 ? "text-emerald-800" : "text-rose-800"}
        />
        <MetricTile
          label="Net income*"
          value={formatUsd4(r.net_profit_usd)}
          meaning={`Net margin ${formatPercent4(r.npm, true)}`}
          title="Derived transparently as latest panel revenue × latest net profit margin; not an invented forecast."
          tone={r.net_profit_usd != null && r.net_profit_usd >= 0 ? "text-emerald-800" : "text-rose-800"}
        />
        <MetricTile
          label="Gross margin"
          value={formatPercent4(r.gm)}
          meaning="Revenue after direct costs"
          title="Gross profit divided by revenue. Higher supports more operating leverage and value creation."
        />
        <MetricTile
          label="FCF margin"
          value={formatPercent4(r.fcfm_sbc)}
          meaning="Cash margin, SBC-adjusted"
          title="Free cash flow divided by revenue after adjusting for stock-based compensation."
          tone={r.fcfm_sbc != null && r.fcfm_sbc >= 0 ? "text-emerald-800" : "text-rose-800"}
        />
      </div>

      {/* Row 4 — durable economics and research investment that explain the valuation */}
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-neutral-100 pt-2 pl-0 sm:grid-cols-5 sm:pl-14">
        <MetricTile
          label="FCF (SBC-adj.)"
          value={formatUsd4(r.fcf_usd)}
          meaning="Cash generation in USD"
          title="Free cash flow after the stock-based-compensation adjustment; a direct cash-economics input."
          tone={r.fcf_usd != null && r.fcf_usd >= 0 ? "text-emerald-800" : "text-rose-800"}
        />
        <MetricTile
          label="Return on capital"
          value={formatPercent4(r.roic)}
          meaning="ROIC"
          title="Return on invested capital: profit earned per dollar of capital employed."
        />
        <MetricTile
          label="R&D intensity"
          value={formatPercent4(r.rd_int)}
          meaning="R&D spend ÷ revenue"
          title="R&D intensity equals R&D expense divided by revenue. It measures how much of each revenue dollar is reinvested in product development."
        />
        <MetricTile
          label="R&D productivity"
          value={formatMultiple4(r.rd_prod)}
          meaning={`GP gain ${grossProfitPeriod} / R&D 2023–25`}
          title={`Gross profit created from ${grossProfitPeriod} per dollar of cumulative R&D spent in 2023–2025. A higher multiple means R&D converted more efficiently into durable gross profit.`}
        />
        <MetricTile
          label="Net revenue retention"
          value={r.retention != null ? formatPercent4(r.retention) : "Not disclosed"}
          meaning="Existing-customer revenue kept"
          title="Disclosed net revenue retention, where available. Missing means not disclosed — it is never estimated."
        />
      </div>

      {drivers.length > 0 && (
        <div className="mt-2 pl-0 text-[10px] leading-relaxed text-neutral-600 sm:pl-14">
          <span className="font-semibold text-neutral-800">Why this ranks:</span>{" "}
          {drivers
            .map(([key, contribution]) => {
              const label = DRIVER_LABELS[key] || key.replaceAll("_", " ")
              const sign = contribution >= 0 ? "+" : ""
              return `${label} ${sign}${formatNumber4(contribution)} score`
            })
            .join(" · ")}
          {r.kill_active === true ? (
            <span className="ml-2 font-semibold text-rose-700">KILL</span>
          ) : null}
        </div>
      )}
    </div>
  )
}
