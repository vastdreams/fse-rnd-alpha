/**
 * PATH: frontend/src/lib/formatMetrics.ts
 * PURPOSE: Consistent, legible presentation for research metrics.
 *
 * Values use at most four significant figures. Currency uses standard
 * comma-grouping (not an ambiguous bare "M"/"B" abbreviation).
 */

const USD_4_SIG = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumSignificantDigits: 4,
  useGrouping: true,
})

const NUMBER_4_SIG = new Intl.NumberFormat("en-US", {
  maximumSignificantDigits: 4,
  useGrouping: true,
})

const PERCENT_4_SIG = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumSignificantDigits: 4,
  useGrouping: true,
})

const PERCENT_4_SIG_SIGNED = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumSignificantDigits: 4,
  useGrouping: true,
  signDisplay: "exceptZero",
})

const PERCENT_RESEARCH_AXES = new Set([
  "mos_live",
  "mos_snapshot",
  "retention",
  "concentration",
  "gm",
  "fcfm_sbc",
  "roic",
  "rule40",
  "sbc_intensity",
  "rev_cagr",
  "dilution_ann",
  "ret_1m",
  "ret_3m",
  "ret_12m",
  "drawdown_from_peak",
  "rd_int",
  "rd_gp",
  "rd_mom",
  "rd_capital",
])

const MULTIPLE_RESEARCH_AXES = new Set(["rd_prod", "rd_cap_to_ev"])

function known(value: number | null | undefined): value is number {
  return value != null && Number.isFinite(value)
}

/** USD with comma grouping and at most four significant figures. */
export function formatUsd4(value: number | null | undefined): string {
  return known(value) ? USD_4_SIG.format(value) : "—"
}

/** A plain ratio, e.g. 1.234× gross-profit created per $1 R&D. */
export function formatMultiple4(value: number | null | undefined): string {
  return known(value) ? `${NUMBER_4_SIG.format(value)}×` : "—"
}

/** Plain number with comma grouping and at most four significant figures. */
export function formatNumber4(value: number | null | undefined): string {
  return known(value) ? NUMBER_4_SIG.format(value) : "—"
}

/** Ratio stored as decimal; renders with a mandatory % sign. */
export function formatPercent4(
  value: number | null | undefined,
  signed = false
): string {
  if (!known(value)) return "—"
  return (signed ? PERCENT_4_SIG_SIGNED : PERCENT_4_SIG).format(value)
}

/** Format a research metric consistently when only its metric key is known. */
export function formatResearchMetric4(axis: string, value: number | null | undefined): string {
  if (PERCENT_RESEARCH_AXES.has(axis)) return formatPercent4(value)
  if (MULTIPLE_RESEARCH_AXES.has(axis)) return formatMultiple4(value)
  return formatNumber4(value)
}

/** Full precision in intent, plain-English screen-reader / tooltip support. */
export function formatMetricTitle(
  label: string,
  value: number | null | undefined,
  unit: "usd" | "percent" | "multiple"
): string {
  const formatted =
    unit === "usd"
      ? formatUsd4(value)
      : unit === "percent"
        ? formatPercent4(value)
        : formatMultiple4(value)
  return `${label}: ${formatted}`
}
