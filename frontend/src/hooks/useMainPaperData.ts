/**
 * PATH: src/hooks/useMainPaperData.ts
 * PURPOSE: Data computation layer for the Main Paper page
 * WHY: Extracted from MainPaper.tsx (4,597 lines) to separate data logic from presentation.
 *      All numeric computations are preserved exactly — no formula changes.
 *      Derived computations live in useMainPaperDerived.ts (pure I→O functions).
 * FLOW:
 *   ┌──────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐
 *   │ Publication       │ → │ Computed derivations │ → │ Props for sections   │
 *   │ Snapshot (API)    │   │ (useMemo)           │   │ (charts, tables)     │
 *   └──────────────────┘   └─────────────────────┘   └──────────────────────┘
 */

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import {
  deriveTopSectors,
  deriveHeadlinePremiums,
  deriveQuintileReturnBar5yr,
  deriveRollingPremium5yr,
  deriveRollingPremium20yr,
  deriveRolling20yrEndpoints,
  deriveSectorIntensityData,
  deriveSectorCoverageData,
  deriveSectorRadarData,
  deriveRdTrendData,
  deriveRdLeadersBySector,
} from "./useMainPaperDerived"
import {
  deriveDoubleSortTableRows,
  deriveFactorPremiumSeries,
  deriveRegimePremiumTable,
  deriveSampleYearRange,
  deriveGrowthOf1,
  deriveInvestableGrowth,
  deriveInvestableNetExcessVsSp500Pp,
  deriveInvestableTurnoverAvgPct,
  deriveInvestableUnderperformPct,
} from "./useMainPaperDerivedStrategy"

// Re-export color constants so any consumer that relied on them keeps working
export { QUINTILE_COLORS, SECTOR_COLORS } from "./useMainPaperDerived"

export function useMainPaperData() {
  // Publication snapshot (frozen submission-grade dataset for paper pages)
  const { data: snapshot, isLoading: snapshotLoading } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const snapshotPayload = snapshot?.payload

  const cohortSummary =
    snapshotPayload?.cohort_summary && typeof snapshotPayload.cohort_summary === "object" && !("error" in snapshotPayload.cohort_summary)
      ? snapshotPayload.cohort_summary
      : undefined

  const aggregateAnova =
    snapshotPayload?.aggregate_anova && typeof snapshotPayload.aggregate_anova === "object" && !("error" in snapshotPayload.aggregate_anova)
      ? snapshotPayload.aggregate_anova
      : undefined

  const annualHmlData =
    snapshotPayload?.annual_hml_premium && typeof snapshotPayload.annual_hml_premium === "object" && !("error" in snapshotPayload.annual_hml_premium)
      ? snapshotPayload.annual_hml_premium
      : undefined

  const rdBySector = Array.isArray(snapshotPayload?.rd_by_sector) ? snapshotPayload?.rd_by_sector : undefined

  const netOfCost5yr =
    snapshotPayload?.net_of_cost_returns &&
    typeof snapshotPayload.net_of_cost_returns === "object" &&
    !("error" in snapshotPayload.net_of_cost_returns)
      ? snapshotPayload.net_of_cost_returns["5yr"]
      : undefined

  const rollingAggregates =
    snapshotPayload?.rolling_window_aggregates &&
    typeof snapshotPayload.rolling_window_aggregates === "object" &&
    !("error" in snapshotPayload.rolling_window_aggregates)
      ? snapshotPayload.rolling_window_aggregates
      : undefined

  const transactionCosts =
    snapshotPayload?.transaction_costs && typeof snapshotPayload.transaction_costs === "object" && !("error" in snapshotPayload.transaction_costs)
      ? snapshotPayload.transaction_costs
      : undefined

  const methodologyParameters =
    snapshotPayload?.methodology_parameters &&
    typeof snapshotPayload.methodology_parameters === "object" &&
    snapshotPayload.methodology_parameters !== null &&
    !("error" in (snapshotPayload.methodology_parameters as Record<string, unknown>))
      ? (snapshotPayload.methodology_parameters as Record<string, unknown>)
      : undefined

  const rollingWindows =
    snapshotPayload?.rolling_windows &&
    typeof snapshotPayload.rolling_windows === "object" &&
    snapshotPayload.rolling_windows !== null &&
    !Array.isArray(snapshotPayload.rolling_windows) &&
    !("error" in (snapshotPayload.rolling_windows as Record<string, unknown>))
      ? (snapshotPayload.rolling_windows as Record<string, unknown>)
      : undefined

  const snapshotBuiltAtYear = useMemo(() => {
    const iso = snapshotPayload?.built_at
    if (typeof iso !== "string") return undefined
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return undefined
    return d.getUTCFullYear()
  }, [snapshotPayload?.built_at])

  const rdTrendsRaw = Array.isArray(snapshotPayload?.rd_trends) ? snapshotPayload.rd_trends : undefined
  const rdTrends = useMemo(() => {
    if (!rdTrendsRaw) return undefined
    if (!snapshotBuiltAtYear) return rdTrendsRaw
    const maxCompleteFiscalYear = snapshotBuiltAtYear - 1
    return rdTrendsRaw.filter((t) => typeof t.year === "number" && t.year <= maxCompleteFiscalYear)
  }, [rdTrendsRaw, snapshotBuiltAtYear])

  const rdLeaderboard = Array.isArray(snapshotPayload?.rd_leaderboard) ? snapshotPayload.rd_leaderboard : undefined
  const rdLeaderboardBySector =
    snapshotPayload?.rd_leaderboard_by_sector &&
    typeof snapshotPayload.rd_leaderboard_by_sector === "object" &&
    snapshotPayload.rd_leaderboard_by_sector !== null &&
    !Array.isArray(snapshotPayload.rd_leaderboard_by_sector) &&
    !("error" in (snapshotPayload.rd_leaderboard_by_sector as Record<string, unknown>))
      ? (snapshotPayload.rd_leaderboard_by_sector as Record<string, any[]>)
      : undefined

  const factorPremiums = Array.isArray(snapshotPayload?.factor_premiums) ? snapshotPayload.factor_premiums : []

  const publicationStats =
    snapshotPayload?.publication_stats && typeof snapshotPayload.publication_stats === "object" && !("error" in snapshotPayload.publication_stats)
      ? snapshotPayload.publication_stats
      : undefined

  const spanningTests =
    snapshotPayload?.spanning_tests_full &&
    typeof snapshotPayload.spanning_tests_full === "object" &&
    !("error" in snapshotPayload.spanning_tests_full)
      ? snapshotPayload.spanning_tests_full
      : undefined

  const ff5SpanningModel = spanningTests?.models?.FF5
  const ff5AlphaPercent = typeof ff5SpanningModel?.alpha === "number" ? ff5SpanningModel.alpha * 100 : undefined
  const ff5AlphaPValue = typeof ff5SpanningModel?.alpha_p === "number" ? ff5SpanningModel.alpha_p : undefined

  const mispricingTests =
    snapshotPayload?.mispricing_tests && typeof snapshotPayload.mispricing_tests === "object" && !("error" in snapshotPayload.mispricing_tests)
      ? snapshotPayload.mispricing_tests
      : undefined

  const doubleSortData =
    snapshotPayload?.double_sort_analysis &&
    typeof snapshotPayload.double_sort_analysis === "object" &&
    !("error" in snapshotPayload.double_sort_analysis)
      ? snapshotPayload.double_sort_analysis
      : undefined

  const investableBacktest =
    snapshotPayload?.investable_backtest &&
    typeof snapshotPayload.investable_backtest === "object" &&
    !("error" in (snapshotPayload.investable_backtest as Record<string, unknown>))
      ? (snapshotPayload.investable_backtest as Record<string, unknown>)
      : undefined

  const delistingSensitivity =
    snapshotPayload?.delisting_sensitivity &&
    typeof snapshotPayload.delisting_sensitivity === "object" &&
    !("error" in (snapshotPayload.delisting_sensitivity as Record<string, unknown>))
      ? (snapshotPayload.delisting_sensitivity as Record<string, unknown>)
      : undefined

  // ── Derived computations (pure functions from useMainPaperDerived) ──
  const topSectors = useMemo(() => deriveTopSectors(rdBySector), [rdBySector])
  const headlinePremiums = useMemo(() => deriveHeadlinePremiums(aggregateAnova), [aggregateAnova])
  const quintileReturnBar5yr = useMemo(() => deriveQuintileReturnBar5yr(rollingAggregates), [rollingAggregates])
  const rollingPremium5yr = useMemo(() => deriveRollingPremium5yr(rollingWindows), [rollingWindows])
  const rollingPremium20yr = useMemo(() => deriveRollingPremium20yr(rollingWindows), [rollingWindows])
  const rolling20yrEndpoints = useMemo(() => deriveRolling20yrEndpoints(rollingPremium20yr), [rollingPremium20yr])
  const sectorIntensityData = useMemo(() => deriveSectorIntensityData(rdBySector), [rdBySector])
  const sectorCoverageData = useMemo(() => deriveSectorCoverageData(cohortSummary), [cohortSummary])
  const sectorRadarData = useMemo(() => deriveSectorRadarData(sectorIntensityData), [sectorIntensityData])
  const rdTrendData = useMemo(() => deriveRdTrendData(rdTrends), [rdTrends])
  const rdLeadersBySector = useMemo(() => deriveRdLeadersBySector(rdLeaderboard, rdLeaderboardBySector), [rdLeaderboard, rdLeaderboardBySector])
  const doubleSortTableRows = useMemo(() => deriveDoubleSortTableRows(doubleSortData), [doubleSortData])
  const factorPremiumSeries = useMemo(() => deriveFactorPremiumSeries(factorPremiums), [factorPremiums])
  const regimePremiumTable = useMemo(() => deriveRegimePremiumTable(factorPremiumSeries), [factorPremiumSeries])
  const sampleYearRange = useMemo(() => deriveSampleYearRange(snapshotPayload, factorPremiumSeries), [snapshotPayload, factorPremiumSeries])

  const snapshotBuiltAtLabel = useMemo(() => {
    const builtAt = snapshot?.meta?.built_at
    if (!builtAt) return undefined
    const d = new Date(builtAt)
    if (Number.isNaN(d.getTime())) return builtAt
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" })
  }, [snapshot?.meta?.built_at])

  const returnConventionLabel = useMemo(() => {
    const v = snapshot?.meta?.return_convention
    if (!v) return "July-June (Fama-French)"
    if (v === "july_june") return "July-June (Fama-French)"
    if (v === "calendar") return "Calendar year"
    return v
  }, [snapshot?.meta?.return_convention])

  const growthOf1 = useMemo(() => deriveGrowthOf1(factorPremiumSeries), [factorPremiumSeries])
  const investableGrowth = useMemo(() => deriveInvestableGrowth(investableBacktest), [investableBacktest])
  const investableNetExcessVsSp500Pp = useMemo(() => deriveInvestableNetExcessVsSp500Pp(investableBacktest, transactionCosts), [investableBacktest, transactionCosts])
  const investableTurnoverAvgPct = useMemo(() => deriveInvestableTurnoverAvgPct(investableBacktest), [investableBacktest])
  const investableUnderperformPct = useMemo(() => deriveInvestableUnderperformPct(investableBacktest), [investableBacktest])

  return {
    // Loading state
    snapshot,
    snapshotLoading,
    snapshotPayload,
    // Parsed snapshot sections
    cohortSummary,
    aggregateAnova,
    annualHmlData,
    rdBySector,
    netOfCost5yr,
    rollingAggregates,
    transactionCosts,
    methodologyParameters,
    rollingWindows,
    rdTrends,
    rdLeaderboard,
    rdLeaderboardBySector,
    factorPremiums,
    publicationStats,
    spanningTests,
    ff5SpanningModel,
    ff5AlphaPercent,
    ff5AlphaPValue,
    mispricingTests,
    doubleSortData,
    investableBacktest,
    delistingSensitivity,
    // Derived computations
    snapshotBuiltAtYear,
    topSectors,
    headlinePremiums,
    quintileReturnBar5yr,
    rollingPremium5yr,
    rollingPremium20yr,
    rolling20yrEndpoints,
    sectorIntensityData,
    sectorCoverageData,
    sectorRadarData,
    rdTrendData,
    rdLeadersBySector,
    doubleSortTableRows,
    factorPremiumSeries,
    regimePremiumTable,
    sampleYearRange,
    snapshotBuiltAtLabel,
    returnConventionLabel,
    growthOf1,
    investableGrowth,
    investableNetExcessVsSp500Pp,
    investableTurnoverAvgPct,
    investableUnderperformPct,
  }
}
