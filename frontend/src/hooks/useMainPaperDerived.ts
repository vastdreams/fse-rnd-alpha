/**
 * PATH: src/hooks/useMainPaperDerived.ts
 * PURPOSE: Pure helper functions for derived data computations used by useMainPaperData
 * WHY: Extracted from useMainPaperData.ts (587 lines) to stay under 300-line limit.
 *      All numeric computations are preserved exactly — no formula changes.
 *      Each function is a pure I→O transform (no React hooks / side effects).
 */

// Chart colors (work in both light and dark modes)
export const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0d9488"]
export const SECTOR_COLORS: Record<string, string> = {
  Technology: "#3b82f6",
  Healthcare: "#22c55e",
  "Consumer Cyclical": "#f59e0b",
  "Financial Services": "#8b5cf6",
  Industrials: "#6366f1",
  "Communication Services": "#ec4899",
  "Consumer Defensive": "#14b8a6",
  Energy: "#ef4444",
  "Basic Materials": "#84cc16",
  "Real Estate": "#06b6d4",
  Utilities: "#64748b",
}

/* eslint-disable @typescript-eslint/no-explicit-any */

export function deriveTopSectors(rdBySector: any[] | undefined) {
  return (rdBySector || [])
    .filter((s) => typeof s.avg_rd_intensity === "number")
    .slice()
    .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
    .slice(0, 5)
}

export function deriveHeadlinePremiums(aggregateAnova: any) {
  const horizons: Array<"5yr" | "10yr" | "20yr"> = ["5yr", "10yr", "20yr"]
  return horizons.map((h) => {
    const node = aggregateAnova?.[h]
    return {
      horizon: h,
      premiumPct: node?.ttest_high_vs_low?.mean_difference,
      t: node?.ttest_high_vs_low?.t_statistic,
      p: node?.ttest_high_vs_low?.p_value,
      eta2: node?.anova?.eta_squared,
      cohensD: node?.ttest_high_vs_low?.cohens_d,
    }
  })
}

export function deriveQuintileReturnBar5yr(rollingAggregates: any) {
  const rows = rollingAggregates?.["5yr"] || []
  return rows.map((q: any) => ({
    quintile: `Q${q.quintile}`,
    label: q.label,
    avgReturn: typeof q.avg_return === "number" ? q.avg_return : null,
    fill: QUINTILE_COLORS[Math.max(0, Math.min(4, (q.quintile || 1) - 1))],
  }))
}

export function deriveRollingPremium5yr(rollingWindows: any) {
  const windows = (rollingWindows && Array.isArray(rollingWindows["5yr"]) ? (rollingWindows["5yr"] as any[]) : []) || []
  return windows
    .filter((w) => typeof w?.start_year === "number" && typeof w?.end_year === "number")
    .map((w) => ({
      period: `${w.start_year}-${w.end_year}`,
      startYear: w.start_year,
      rdPremium: typeof w.rd_premium === "number" ? w.rd_premium : 0,
    }))
}

export function deriveRollingPremium20yr(rollingWindows: any) {
  const windows = (rollingWindows && Array.isArray(rollingWindows["20yr"]) ? (rollingWindows["20yr"] as any[]) : []) || []
  return windows
    .filter((w) => typeof w?.start_year === "number" && typeof w?.end_year === "number" && typeof w?.rd_premium === "number")
    .map((w) => ({
      period: `${w.start_year}-${w.end_year}`,
      startYear: w.start_year,
      endYear: w.end_year,
      rdPremium: w.rd_premium,
    }))
    .sort((a, b) => a.startYear - b.startYear)
}

export function deriveRolling20yrEndpoints(rollingPremium20yr: ReturnType<typeof deriveRollingPremium20yr>) {
  if (!rollingPremium20yr.length) return undefined
  return {
    first: rollingPremium20yr[0],
    last: rollingPremium20yr[rollingPremium20yr.length - 1],
    n: rollingPremium20yr.length,
  }
}

export function deriveSectorIntensityData(rdBySector: any[] | undefined) {
  const rows = (rdBySector || [])
    .slice()
    .filter((s) => typeof s.avg_rd_intensity === "number")
    .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
  return rows.map((s) => ({
    sector: s.sector,
    avgRdIntensity: s.avg_rd_intensity,
    companies: s.company_count,
    totalRdB: s.total_rd_spend / 1e9,
    fill: SECTOR_COLORS[s.sector] || "#64748b",
  }))
}

export function deriveSectorCoverageData(cohortSummary: any) {
  const rows = cohortSummary?.by_sector || []
  return rows.map((s: any) => {
    const total = s.total || 0
    const cov = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0)
    return {
      sector: s.sector,
      total,
      coverage5yr: cov(s.n_5yr),
      coverage10yr: cov(s.n_10yr),
      coverage20yr: cov(s.n_20yr),
      fill: SECTOR_COLORS[s.sector] || "#64748b",
    }
  })
}

export function deriveSectorRadarData(sectorIntensityData: ReturnType<typeof deriveSectorIntensityData>) {
  return sectorIntensityData.slice(0, 8).map((s) => ({
    sector: s.sector.length > 15 ? `${s.sector.slice(0, 12)}...` : s.sector,
    fullSector: s.sector,
    intensity: s.avgRdIntensity,
    companies: s.companies,
    spend: Math.min(s.totalRdB, 100),
  }))
}

export function deriveRdTrendData(rdTrends: any[] | undefined) {
  return (rdTrends || []).map((t) => ({
    year: t.year,
    companies: t.companies,
    avgIntensity: t.avg_rd_intensity,
    totalSpendB: t.total_rd_spend / 1e9,
  }))
}

export function deriveRdLeadersBySector(rdLeaderboard: any[] | undefined, rdLeaderboardBySector: Record<string, any[]> | undefined) {
  const sanitizeLeader = (r: any) => {
    if (!r || typeof r.symbol !== "string" || !r.symbol) return null
    const intensity = typeof r.avg_rd_intensity === "number" ? r.avg_rd_intensity : null
    return {
      symbol: r.symbol,
      name: typeof r.name === "string" ? r.name : null,
      avg_rd_intensity: intensity,
      years_of_data: typeof r.years_of_data === "number" ? r.years_of_data : null,
    }
  }

  if (rdLeaderboardBySector) {
    return Object.entries(rdLeaderboardBySector)
      .map(([sector, rows]) => {
        const leaders = (Array.isArray(rows) ? rows : [])
          .map(sanitizeLeader)
          .filter((x): x is NonNullable<typeof x> => Boolean(x))
          .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
          .slice(0, 3)
        return { sector, leaders }
      })
      .filter((s) => s.leaders.length > 0)
      .sort((a, b) => ((b.leaders[0]?.avg_rd_intensity as number) || 0) - ((a.leaders[0]?.avg_rd_intensity as number) || 0))
  }

  const grouped: Record<string, ReturnType<typeof sanitizeLeader>[]> = {}
  for (const r of rdLeaderboard || []) {
    const sectorKey = typeof r?.sector === "string" && r.sector ? r.sector : "Unknown"
    grouped[sectorKey] = grouped[sectorKey] || []
    grouped[sectorKey].push(sanitizeLeader(r))
  }

  return Object.entries(grouped)
    .map(([sector, rows]) => {
      const leaders = rows
        .filter((x): x is NonNullable<typeof x> => Boolean(x))
        .sort((a, b) => (b.avg_rd_intensity || 0) - (a.avg_rd_intensity || 0))
        .slice(0, 3)
      return { sector, leaders }
    })
    .filter((s) => s.leaders.length > 0)
    .sort((a, b) => ((b.leaders[0]?.avg_rd_intensity as number) || 0) - ((a.leaders[0]?.avg_rd_intensity as number) || 0))
}

// Strategy/investable derived functions are in useMainPaperDerivedStrategy.ts
