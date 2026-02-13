/** Whitepaper data hook – fetching + derived metrics for all 11 slides. */
import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export type WhitepaperData = ReturnType<typeof useWhitepaperData>

export function useWhitepaperData() {
  // Fetch data
  const { data: snapshot } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
    staleTime: Infinity,
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  // Extract metrics from snapshot
  const payload = snapshot?.payload
  const anovaData = payload?.aggregate_anova
  const annualHmlPremium = payload?.annual_hml_premium
  const factorPremiums = payload?.factor_premiums
  const investableBacktestRaw = payload?.investable_backtest
  const transactionCosts = payload?.transaction_costs
  const rollingAggregates = payload?.rolling_window_aggregates
  const rdBySector = Array.isArray(payload?.rd_by_sector) ? (payload?.rd_by_sector as any[]) : []
  const spanningTests =
    payload?.spanning_tests_full && typeof payload.spanning_tests_full === "object" && !("error" in payload.spanning_tests_full)
      ? (payload.spanning_tests_full as any)
      : undefined
  const cohortSummaryFromSnapshot =
    payload?.cohort_summary && typeof payload.cohort_summary === "object" && !("error" in payload.cohort_summary)
      ? (payload.cohort_summary as any)
      : undefined
  const annualHmlData =
    annualHmlPremium && typeof annualHmlPremium === "object" && !("error" in annualHmlPremium)
      ? (annualHmlPremium as any)
      : undefined
  const investableBacktest =
    investableBacktestRaw && typeof investableBacktestRaw === "object" && !("error" in investableBacktestRaw)
      ? (investableBacktestRaw as any)
      : undefined
  const cohort = cohortSummary ?? cohortSummaryFromSnapshot
  
  // Safely access anova data with type guards
  const anova5yr = anovaData && !("error" in anovaData) ? anovaData["5yr"] : undefined
  const anova10yr = anovaData && !("error" in anovaData) ? anovaData["10yr"] : undefined
  const anova20yr = anovaData && !("error" in anovaData) ? anovaData["20yr"] : undefined
  
  // Rolling window quintile returns (5yr)
  const quintileData5yr = rollingAggregates && !("error" in rollingAggregates) 
    ? (rollingAggregates as Record<string, any[]>)["5yr"] || []
    : []
  
  // Extract quintile returns dynamically (no hard-coded fallback numbers)
  const getQuintileReturn = (quintile: number): number | null => {
    const qData = quintileData5yr.find((q: any) => q.quintile === quintile)
    return typeof qData?.avg_return === "number" ? qData.avg_return : null
  }
  
  const transactionCostsSafe = transactionCosts && typeof transactionCosts === "object" && !("error" in transactionCosts)
    ? (transactionCosts as any)
    : undefined
  
  const rdPremium =
    typeof annualHmlData?.mean_premium === "number"
      ? annualHmlData.mean_premium
      : typeof anova5yr?.ttest_high_vs_low?.mean_difference === "number"
        ? anova5yr.ttest_high_vs_low.mean_difference
        : undefined

  const tStat =
    typeof annualHmlData?.hac_adjusted?.t_statistic === "number"
      ? annualHmlData.hac_adjusted.t_statistic
      : typeof anova5yr?.ttest_high_vs_low?.t_statistic === "number"
        ? anova5yr.ttest_high_vs_low.t_statistic
        : undefined

  const pValue = typeof annualHmlData?.hac_adjusted?.p_value === "number" ? annualHmlData.hac_adjusted.p_value : undefined
  const etaSquared5yr = typeof anova5yr?.anova?.eta_squared === "number" ? anova5yr.anova.eta_squared : undefined
  const etaSquared10yr = typeof anova10yr?.anova?.eta_squared === "number" ? anova10yr.anova.eta_squared : undefined
  const etaSquared20yr = typeof anova20yr?.anova?.eta_squared === "number" ? anova20yr.anova.eta_squared : undefined
  const totalCompanies = typeof cohort?.total_companies === "number" ? cohort.total_companies : undefined
  const winRate =
    typeof annualHmlData?.win_rate === "number"
      ? Math.round(annualHmlData.win_rate * 100)
      : factorPremiums && !("error" in factorPremiums) && factorPremiums.length > 0
        ? Math.round((factorPremiums.filter((p: any) => (p.rd_premium ?? 0) > 0).length / factorPremiums.length) * 100)
        : undefined
  const annualTradingCost = typeof transactionCostsSafe?.annual_trading_cost_pct === "number" ? transactionCostsSafe.annual_trading_cost_pct : undefined
  const premiumCaptureRate =
    typeof transactionCostsSafe?.premium_capture_rate_pct === "number"
      ? transactionCostsSafe.premium_capture_rate_pct
      : typeof transactionCostsSafe?.premium_after_costs_pct === "number"
        ? transactionCostsSafe.premium_after_costs_pct
        : undefined
  const netPremium =
    typeof transactionCostsSafe?.net_rd_premium_pct === "number"
      ? transactionCostsSafe.net_rd_premium_pct
      : typeof rdPremium === "number" && typeof annualTradingCost === "number"
        ? rdPremium - annualTradingCost
        : undefined
  const backtestPeriodLabel =
    typeof transactionCostsSafe?.period_label === "string"
      ? transactionCostsSafe.period_label
      : "N/A"

  const ff5SpanningModel = spanningTests?.models?.FF5
  const ff5AlphaPercent = typeof ff5SpanningModel?.alpha === "number" ? ff5SpanningModel.alpha * 100 : undefined
  const ff5AlphaPValue = typeof ff5SpanningModel?.alpha_p === "number" ? ff5SpanningModel.alpha_p : undefined
    
  // Cohort coverage for long-horizon analysis
  const eligible5yr = typeof cohort?.eligible_5yr === "number" ? cohort.eligible_5yr : undefined
  const eligible10yr = typeof cohort?.eligible_10yr === "number" ? cohort.eligible_10yr : undefined
  const eligible20yr = typeof cohort?.eligible_20yr === "number" ? cohort.eligible_20yr : undefined
  const eligible5yrPct = typeof eligible5yr === "number" && typeof totalCompanies === "number" && totalCompanies > 0
    ? Math.round((eligible5yr / totalCompanies) * 100)
    : undefined
  const eligible10yrPct = typeof eligible10yr === "number" && typeof totalCompanies === "number" && totalCompanies > 0
    ? Math.round((eligible10yr / totalCompanies) * 100)
    : undefined
  const eligible20yrPct = typeof eligible20yr === "number" && typeof totalCompanies === "number" && totalCompanies > 0
    ? Math.round((eligible20yr / totalCompanies) * 100)
    : undefined

  const rdProfile = (cohort?.by_rd_profile as any) || undefined
  const rdProfileHigh = typeof rdProfile?.High === "number" ? rdProfile.High : undefined
  const rdProfileMedium = typeof rdProfile?.Medium === "number" ? rdProfile.Medium : undefined
  const rdProfileLow = typeof rdProfile?.Low === "number" ? rdProfile.Low : undefined

  // Investable (ETF-like) backtest metrics
  const invPortfolioNet = investableBacktest?.portfolio_performance_net
  const invBenchmarkNet = investableBacktest?.benchmark_performance_net
  const invSp500Annualized =
    typeof investableBacktest?.sp500_performance?.annualized_return === "number"
      ? investableBacktest.sp500_performance.annualized_return
      : undefined

  const invNetExcessVsSPY =
    typeof invPortfolioNet?.annualized_return === "number" && typeof invSp500Annualized === "number"
      ? invPortfolioNet.annualized_return - invSp500Annualized
      : undefined
  const invNHoldings = typeof investableBacktest?.meta?.n_holdings === "number" ? investableBacktest.meta.n_holdings : 20
  const invTurnoverAvg = typeof investableBacktest?.turnover?.avg_turnover_pct === "number" ? investableBacktest.turnover.avg_turnover_pct : undefined
  const invTurnoverMax = typeof investableBacktest?.turnover?.max_turnover_pct === "number" ? investableBacktest.turnover.max_turnover_pct : undefined
  const invRoundTripCostPer100PctTurnover =
    typeof investableBacktest?.cost_assumptions?.round_trip_cost_per_100pct_turnover_pct === "number"
      ? investableBacktest.cost_assumptions.round_trip_cost_per_100pct_turnover_pct
      : undefined
  const invBenchmarkCostPct =
    typeof investableBacktest?.cost_assumptions?.benchmark_cost_pct === "number"
      ? investableBacktest.cost_assumptions.benchmark_cost_pct
      : undefined
  const invTradingCostEstPct =
    typeof invRoundTripCostPer100PctTurnover === "number" && typeof invTurnoverAvg === "number"
      ? (invRoundTripCostPer100PctTurnover * invTurnoverAvg) / 100
      : undefined
  const invHoldings = Array.isArray(investableBacktest?.holdings) ? (investableBacktest.holdings as any[]) : []
  const invSectorMix = useMemo(() => {
    const map = new Map<string, number>()
    for (const h of invHoldings) {
      const sector = typeof h?.sector === "string" && h.sector ? h.sector : "Unknown"
      const w = typeof h?.weight === "number" ? h.weight : 0
      map.set(sector, (map.get(sector) || 0) + w)
    }
    return Array.from(map.entries())
      .map(([sector, weight]) => ({ sector, weight }))
      .sort((a, b) => b.weight - a.weight)
  }, [invHoldings])
  const invTopHoldings = useMemo(() => {
    const rows = invHoldings
      .filter((h) => h && typeof h.symbol === "string")
      .slice()
      .sort((a, b) => (typeof b.rd_intensity === "number" ? b.rd_intensity : 0) - (typeof a.rd_intensity === "number" ? a.rd_intensity : 0))
    return rows.slice(0, 6)
  }, [invHoldings])
  
  // Sample window
  const factorYears =
    factorPremiums && !("error" in factorPremiums)
      ? (factorPremiums as any[])
          .map((p: any) => p?.year)
          .filter((y: any) => typeof y === "number")
      : []
  const sampleStartYear = factorYears.length
    ? Math.max(1995, factorYears.reduce((min: number, y: number) => Math.min(min, y), factorYears[0] as number))
    : 1995
  const sampleEndYearRaw = factorYears.length
    ? factorYears.reduce((max: number, y: number) => Math.max(max, y), factorYears[0] as number)
    : 2024
  const sampleEndYear = Math.min(sampleEndYearRaw, 2024)
  
  // Annual premium time series for chart
  const premiumTimeSeriesData = useMemo(() => {
    if (!factorPremiums || "error" in factorPremiums || factorPremiums.length === 0) {
      return []
    }
    return factorPremiums
      .filter((p: any) => p.year && p.rd_premium !== null)
      .map((p: any) => ({
        year: p.year,
        premium: p.rd_premium,
      }))
      .sort((a: any, b: any) => a.year - b.year)
  }, [factorPremiums])

  const investableGrowthData = useMemo(() => {
    const rows = Array.isArray(investableBacktest?.yearly_data) ? (investableBacktest.yearly_data as any[]) : []
    const usable = rows
      .filter(
        (r) =>
          typeof r?.year === "number" &&
          r.year <= sampleEndYear &&
          typeof r?.portfolio_return_net === "number" &&
          typeof r?.benchmark_return_net === "number"
      )
      .sort((a, b) => a.year - b.year)

    let portfolioIndex = 1
    let benchmarkIndex = 1
    let sp500Index = 1

    const out: Array<{ year: number; portfolioIndex: number; benchmarkIndex: number; sp500Index: number }> = []
    for (const r of usable) {
      portfolioIndex *= 1 + r.portfolio_return_net / 100
      benchmarkIndex *= 1 + r.benchmark_return_net / 100
      if (typeof r.sp500_return === "number") sp500Index *= 1 + r.sp500_return / 100
      out.push({ year: r.year, portfolioIndex, benchmarkIndex, sp500Index })
    }
    return out
  }, [investableBacktest, sampleEndYear])

  const invStartYear = investableGrowthData.length ? investableGrowthData[0].year : 2010
  const invEndYear = investableGrowthData.length ? investableGrowthData[investableGrowthData.length - 1].year : sampleEndYear
  const invPortfolioMultiple = investableGrowthData.length ? investableGrowthData[investableGrowthData.length - 1].portfolioIndex : undefined
  const invBenchmarkMultiple = investableGrowthData.length ? investableGrowthData[investableGrowthData.length - 1].benchmarkIndex : undefined
  const invSp500Multiple = investableGrowthData.length ? investableGrowthData[investableGrowthData.length - 1].sp500Index : undefined

  return {
    snapshot,
    rdBySector,
    annualHmlData,
    investableBacktest,
    rdPremium,
    tStat,
    pValue,
    etaSquared5yr,
    etaSquared10yr,
    etaSquared20yr,
    totalCompanies,
    winRate,
    annualTradingCost,
    premiumCaptureRate,
    netPremium,
    backtestPeriodLabel,
    ff5AlphaPercent,
    ff5AlphaPValue,
    eligible5yr,
    eligible10yr,
    eligible20yr,
    eligible5yrPct,
    eligible10yrPct,
    eligible20yrPct,
    rdProfileHigh,
    rdProfileMedium,
    rdProfileLow,
    invPortfolioNet,
    invBenchmarkNet,
    invSp500Annualized,
    invNetExcessVsSPY,
    invNHoldings,
    invTurnoverAvg,
    invTurnoverMax,
    invRoundTripCostPer100PctTurnover,
    invBenchmarkCostPct,
    invTradingCostEstPct,
    invHoldings,
    invSectorMix,
    invTopHoldings,
    sampleStartYear,
    sampleEndYear,
    premiumTimeSeriesData,
    investableGrowthData,
    invStartYear,
    invEndYear,
    invPortfolioMultiple,
    invBenchmarkMultiple,
    invSp500Multiple,
    getQuintileReturn,
    spanningTests,
  }
}
