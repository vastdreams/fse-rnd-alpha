import { formatNumber4 } from "@/lib/formatMetrics"

/**
 * Score quality + driver baseline for Universe cards.
 * Pure helpers so the UI can show *why* a score exists, not just the number.
 */

export type ScoreQualityLevel = "strong" | "good" | "limited" | "blocked"

export type ScoreQuality = {
  level: ScoreQualityLevel
  label: string
  baseline: string
  filingGrade: string
  fresh: boolean
  kill: boolean | null
}

export type ScoreDriver = {
  key: string
  label: string
  contribution: number
  detail: string
}

const DRIVER_META: Record<string, { label: string; detail: string }> = {
  mos_live: {
    label: "Value gap vs target",
    detail:
      "How far live price sits below (or above) the research median fair value. Positive lifts the score when the name looks cheap vs target.",
  },
  rd_prod: {
    label: "R&D productivity",
    detail:
      "Gross profit created per $1 of cumulative R&D. Higher means R&D converted more efficiently into durable economics.",
  },
  fcfm_sbc: {
    label: "FCF margin",
    detail: "SBC-adjusted free cash flow ÷ revenue. Cash generation quality after stock-based compensation.",
  },
  roic: {
    label: "Return on capital",
    detail: "Return on invested capital — profit earned per dollar of capital employed.",
  },
  retention: {
    label: "Net revenue retention",
    detail: "Disclosed NRR / retention from filings. Missing means not disclosed — never estimated.",
  },
  gm: {
    label: "Gross margin",
    detail: "Gross profit ÷ revenue. Higher supports operating leverage and value creation.",
  },
  rule40: {
    label: "Rule of 40",
    detail: "Growth + profitability heuristic used on this screen’s quality axis.",
  },
  delta_fcfm_sbc: {
    label: "Improving FCF margin",
    detail: "Change in SBC-adjusted FCF margin — improving cash economics lifts the score.",
  },
  delta_roic: {
    label: "Improving ROIC",
    detail: "Change in return on invested capital — improving capital returns lift the score.",
  },
}

export function driverLabel(key: string): string {
  return DRIVER_META[key]?.label || key.replaceAll("_", " ")
}

export function driverDetail(key: string): string {
  return (
    DRIVER_META[key]?.detail ||
    `Contribution from ${key.replaceAll("_", " ")} on this screen’s composite score.`
  )
}

export function scoreQuality(input: {
  completeness_grade: string
  freshness_ok: boolean
  kill_active: boolean | null | undefined
}): ScoreQuality {
  const filingGrade = input.completeness_grade || "Incomplete"
  const fresh = Boolean(input.freshness_ok)
  const kill = input.kill_active === true ? true : input.kill_active === false ? false : null

  if (kill === true) {
    return {
      level: "blocked",
      label: "Blocked",
      baseline: "Kill flag is on — do not treat this score as a buy signal.",
      filingGrade,
      fresh,
      kill,
    }
  }

  if (filingGrade === "Incomplete" || filingGrade === "C") {
    return {
      level: "limited",
      label: "Limited",
      baseline: fresh
        ? `Filing evidence is ${filingGrade} — score is directional only.`
        : `Filing evidence is ${filingGrade} and data is stale — treat cautiously.`,
      filingGrade,
      fresh,
      kill,
    }
  }

  if (!fresh) {
    return {
      level: "limited",
      label: "Stale",
      baseline: `Filing grade ${filingGrade}, but fundamentals are past refresh — confirm before acting.`,
      filingGrade,
      fresh,
      kill,
    }
  }

  if (filingGrade === "A") {
    return {
      level: "strong",
      label: "Strong",
      baseline: "Filing grade A and fresh inputs — score rests on a solid evidence base.",
      filingGrade,
      fresh,
      kill,
    }
  }

  return {
    level: "good",
    label: "Good",
    baseline: "Filing grade B and fresh inputs — usable score with normal diligence.",
    filingGrade,
    fresh,
    kill,
  }
}

export function scoreDrivers(
  contributions: Record<string, number> | null | undefined,
  limit = 4
): ScoreDriver[] {
  return Object.entries(contributions || {})
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, limit)
    .map(([key, contribution]) => ({
      key,
      label: driverLabel(key),
      contribution,
      detail: driverDetail(key),
    }))
}

export function formatScoreDrivers(
  contributions: Record<string, number> | null | undefined,
  limit = 3
): string {
  return scoreDrivers(contributions, limit)
    .map((d) => {
      const sign = d.contribution >= 0 ? "+" : ""
      return `${d.label} ${sign}${formatNumber4(d.contribution)}`
    })
    .join(" · ")
}

export function qualityTone(level: ScoreQualityLevel): string {
  if (level === "strong") return "border-emerald-300 bg-emerald-50 text-emerald-950"
  if (level === "good") return "border-sky-300 bg-sky-50 text-sky-950"
  if (level === "blocked") return "border-rose-300 bg-rose-50 text-rose-950"
  return "border-amber-300 bg-amber-50 text-amber-950"
}

export function driverBarWidth(contribution: number, maxAbs: number): number {
  if (!(maxAbs > 0) || !Number.isFinite(contribution)) return 8
  return Math.max(8, Math.round((Math.abs(contribution) / maxAbs) * 100))
}
