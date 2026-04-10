/** Portfolio data hook – all queries + derived metrics for the ETF R&D Alpha page. */
import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api, portfolioApi } from "@/lib/api"
import type { AlphaFamily } from "@/lib/api/types"

const CURRENT_YEAR = new Date().getFullYear()

export type PortfolioData = ReturnType<typeof usePortfolioData>

export function usePortfolioData(asOfYear: number, nHoldings: number, selectedSector?: string, alphaFamily: AlphaFamily = "rd_alpha") {
  // ── Frozen publication snapshot ──
  const { data: publicationSnapshot } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: api.getPublicationSnapshot,
    staleTime: 5 * 60 * 1000,
  })

  const annualHmlPremium = useMemo(() => {
    const annual = publicationSnapshot?.payload?.annual_hml_premium
    if (!annual || typeof annual !== "object") return undefined
    if ("error" in annual) return undefined
    return annual
  }, [publicationSnapshot?.payload?.annual_hml_premium])

  const transactionCosts = useMemo(() => {
    const costs = publicationSnapshot?.payload?.transaction_costs
    if (!costs || typeof costs !== "object") return undefined
    if ("error" in costs) return undefined
    return costs
  }, [publicationSnapshot?.payload?.transaction_costs])

  const annualMeanPremiumPct =
    typeof annualHmlPremium?.mean_premium === "number" ? annualHmlPremium.mean_premium : undefined
  const annualTStat =
    typeof annualHmlPremium?.hac_adjusted?.t_statistic === "number" ? annualHmlPremium.hac_adjusted.t_statistic : undefined
  const annualPValue =
    typeof annualHmlPremium?.hac_adjusted?.p_value === "number" ? annualHmlPremium.hac_adjusted.p_value : undefined
  const annualNYears = typeof annualHmlPremium?.n_years === "number" ? annualHmlPremium.n_years : undefined
  const annualTradingCostPct =
    typeof transactionCosts?.annual_trading_cost_pct === "number" ? transactionCosts.annual_trading_cost_pct : undefined

  // ── Holdings ──
  const { data: holdings, isLoading: loadingHoldings } = useQuery({
    queryKey: ["etfHoldings", nHoldings, selectedSector, asOfYear, alphaFamily],
    queryFn: () => portfolioApi.getETFHoldings(nHoldings, alphaFamily, selectedSector, asOfYear),
  })

  // ── Forecast vs Actual ──
  const { data: forecastVsActual, isLoading: loadingForecast } = useQuery({
    queryKey: ["forecastVsActual", asOfYear, nHoldings, selectedSector, alphaFamily],
    queryFn: () => portfolioApi.getForecastVsActual(asOfYear, nHoldings, alphaFamily, selectedSector),
  })

  // ── Backtest ──
  const backtestStart = 2005
  const backtestEndForQuery = CURRENT_YEAR - 1
  const backtestEnd = Math.min(asOfYear, CURRENT_YEAR - 1)

  const { data: backtest, isLoading: loadingBacktest } = useQuery({
    queryKey: ["backtest-full-chart", backtestStart, backtestEndForQuery, nHoldings, selectedSector, alphaFamily],
    queryFn: () => portfolioApi.backtest(backtestStart, backtestEndForQuery, nHoldings, alphaFamily, selectedSector),
    staleTime: 5 * 60 * 1000,
  })

  // ── Supporting data ──
  const { data: sectors } = useQuery({ queryKey: ["portfolioSectors"], queryFn: portfolioApi.getSectors })
  const { data: sectorAllocation } = useQuery({
    queryKey: ["sectorAllocation", nHoldings, asOfYear, alphaFamily],
    queryFn: () => portfolioApi.getSectorAllocation(nHoldings, alphaFamily, asOfYear),
  })
  const { data: methodology } = useQuery({ queryKey: ["methodology"], queryFn: portfolioApi.getMethodology })
  const { data: rdAlphaHoldings } = useQuery({
    queryKey: ["rdAlphaHoldings", nHoldings, asOfYear],
    queryFn: () => portfolioApi.getRDAlphaHoldings(nHoldings, asOfYear),
  })
  const { data: sectorWeights } = useQuery({
    queryKey: ["sectorWeights", nHoldings, asOfYear],
    queryFn: () => portfolioApi.getSectorWeights(nHoldings, asOfYear),
  })
  const { data: sp500Forecast } = useQuery({
    queryKey: ["sp500Forecast"],
    queryFn: () => portfolioApi.getSP500Forecast(10, true),
  })

  const isLoading = loadingHoldings || loadingBacktest || loadingForecast

  // ── Derived: yearly chart data ──
  const yearlyDataForCharts = useMemo(() => {
    const rows = backtest?.yearly_data || []
    return rows.map((d) => ({
      ...d,
      sp500_return: typeof d.sp500_return === "number" ? d.sp500_return : null,
      excess_vs_sp500: typeof d.excess_vs_sp500 === "number" ? d.excess_vs_sp500 : null,
    }))
  }, [backtest?.yearly_data])

  // ── Derived: selected year metrics ──
  const selectedYearMetrics = useMemo(() => {
    const rows = backtest?.yearly_data || []
    const filteredRows = rows.filter(d => d.year >= backtestStart && d.year <= backtestEnd)
    if (filteredRows.length === 0) return null

    const portfolioReturns = filteredRows.map(d => (d.portfolio_return || 0) / 100)
    const sp500Returns = filteredRows.map(d => (d.sp500_return || 0) / 100)
    const portfolioTotal = portfolioReturns.reduce((acc, r) => acc * (1 + r), 1) - 1
    const sp500Total = sp500Returns.reduce((acc, r) => acc * (1 + r), 1) - 1
    const nYears = filteredRows.length
    const portfolioAnnualized = nYears > 0 ? Math.pow(1 + portfolioTotal, 1 / nYears) - 1 : 0
    const sp500Annualized = nYears > 0 ? Math.pow(1 + sp500Total, 1 / nYears) - 1 : 0
    const mean = portfolioReturns.reduce((a, b) => a + b, 0) / portfolioReturns.length
    const variance = portfolioReturns.reduce((acc, r) => acc + Math.pow(r - mean, 2), 0) / (portfolioReturns.length - 1 || 1)
    const volatility = Math.sqrt(variance)
    const riskFreeRate = 0.02
    const sharpeRatio = volatility > 0 ? (portfolioAnnualized - riskFreeRate) / volatility : 0
    let peak = 1, maxDrawdown = 0, cumulative = 1
    for (const r of portfolioReturns) {
      cumulative *= (1 + r)
      if (cumulative > peak) peak = cumulative
      const drawdown = (cumulative - peak) / peak
      if (drawdown < maxDrawdown) maxDrawdown = drawdown
    }
    return {
      portfolio: { total_return: portfolioTotal * 100, annualized_return: portfolioAnnualized * 100, volatility: volatility * 100, sharpe_ratio: sharpeRatio, max_drawdown: maxDrawdown * 100 },
      sp500: { total_return: sp500Total * 100, annualized_return: sp500Annualized * 100 },
      excess_vs_sp500: (portfolioAnnualized - sp500Annualized) * 100,
    }
  }, [backtest?.yearly_data, backtestStart, backtestEnd])

  const cumulativeExcessVsSp500 = useMemo(() => {
    if (!selectedYearMetrics) return null
    return selectedYearMetrics.portfolio.total_return - selectedYearMetrics.sp500.total_return
  }, [selectedYearMetrics])

  // ── Derived: performance line chart data ──
  const performanceLineData = useMemo(() => {
    if (!backtest?.yearly_data || backtest.yearly_data.length === 0) return []
    const lastActualYear = CURRENT_YEAR - 1
    const defaultForecastPremium = typeof annualMeanPremiumPct === "number" ? annualMeanPremiumPct : 5.0
    const forecastPremium = forecastVsActual?.forecast_premium ?? defaultForecastPremium

    let portfolioCumulative = 100
    let benchmarkCumulative = 100
    const chartData: Array<{ year: number; date: string; historical: number | null; actuals: number | null; forecast: number | null; benchmark: number; portfolioHigh: number | null; portfolioLow: number | null }> = []
    let portfolioAtSelectionYear = 100
    const startYear = backtest.yearly_data.length > 0 ? backtest.yearly_data[0].year : 2000

    chartData.push({ year: startYear - 1, date: `${startYear - 1}`, historical: 100, actuals: null, forecast: null, benchmark: 100, portfolioHigh: null, portfolioLow: null })

    backtest.yearly_data.forEach((d) => {
      portfolioCumulative *= (1 + (d.portfolio_return || 0) / 100)
      const benchmarkReturn = typeof d.sp500_return === "number" ? d.sp500_return : 0
      benchmarkCumulative *= (1 + benchmarkReturn / 100)
      if (d.year === asOfYear) { portfolioAtSelectionYear = portfolioCumulative }
      const isHistorical = d.year <= asOfYear
      const isActual = d.year > asOfYear && d.year <= lastActualYear
      chartData.push({ year: d.year, date: `${d.year}`, historical: isHistorical ? parseFloat(portfolioCumulative.toFixed(2)) : null, actuals: isActual ? parseFloat(portfolioCumulative.toFixed(2)) : null, forecast: null, benchmark: parseFloat(benchmarkCumulative.toFixed(2)), portfolioHigh: null, portfolioLow: null })
    })

    const transitionIdx = chartData.findIndex(d => d.year === asOfYear)
    if (transitionIdx >= 0 && asOfYear < lastActualYear) { chartData[transitionIdx].actuals = chartData[transitionIdx].historical }
    let forecastPortfolio = portfolioAtSelectionYear
    if (transitionIdx >= 0) { chartData[transitionIdx].forecast = parseFloat(forecastPortfolio.toFixed(2)) }

    for (let i = 1; i <= 10; i++) {
      const forecastYear = asOfYear + i
      const expectedReturn = (8 + forecastPremium) / 100
      forecastPortfolio *= (1 + expectedReturn)
      const confidenceSpread = 0.08 + (i * 0.015)
      const existingIdx = chartData.findIndex(d => d.year === forecastYear)
      if (existingIdx >= 0) {
        chartData[existingIdx].forecast = parseFloat(forecastPortfolio.toFixed(2))
        chartData[existingIdx].portfolioHigh = parseFloat((forecastPortfolio * (1 + confidenceSpread)).toFixed(2))
        chartData[existingIdx].portfolioLow = parseFloat((forecastPortfolio * (1 - confidenceSpread)).toFixed(2))
      } else {
        chartData.push({ year: forecastYear, date: `${forecastYear}`, historical: null, actuals: null, forecast: parseFloat(forecastPortfolio.toFixed(2)), benchmark: parseFloat((benchmarkCumulative * Math.pow(1.08, i)).toFixed(2)), portfolioHigh: parseFloat((forecastPortfolio * (1 + confidenceSpread)).toFixed(2)), portfolioLow: parseFloat((forecastPortfolio * (1 - confidenceSpread)).toFixed(2)) })
      }
    }
    chartData.sort((a, b) => a.year - b.year)
    return chartData
  }, [backtest, asOfYear, forecastVsActual, annualMeanPremiumPct])

  const hasActualsData = useMemo(() => {
    return performanceLineData.filter(d => d.actuals !== null && d.year > asOfYear).length > 0
  }, [performanceLineData, asOfYear])

  const actualsYearRange = useMemo(() => {
    const actualsPoints = performanceLineData.filter(d => d.actuals !== null)
    if (actualsPoints.length === 0) return null
    const years = actualsPoints.map(d => d.year)
    return { min: Math.min(...years), max: Math.max(...years) }
  }, [performanceLineData])

  const forecastAccuracy = useMemo(() => {
    if (!forecastVsActual?.is_historical || forecastVsActual.actual_return === null) return null
    const error = Math.abs(forecastVsActual.forecast_error ?? 0)
    if (error < 5) return { status: "excellent" as const, color: "emerald" as const }
    if (error < 10) return { status: "good" as const, color: "yellow" as const }
    return { status: "off" as const, color: "red" as const }
  }, [forecastVsActual])

  const yearOptions = useMemo(() => {
    const years = []
    for (let y = 2000; y <= CURRENT_YEAR; y++) years.push(y)
    return years.reverse()
  }, [])

  return {
    // Raw data
    holdings, backtest, forecastVsActual, sectors, sectorAllocation, alphaFamily,
    methodology, rdAlphaHoldings, sectorWeights, sp500Forecast,
    publicationSnapshot,
    // Publication metrics
    annualMeanPremiumPct, annualTStat, annualPValue, annualNYears, annualTradingCostPct,
    // Derived
    yearlyDataForCharts, selectedYearMetrics, cumulativeExcessVsSp500,
    performanceLineData, hasActualsData, actualsYearRange, forecastAccuracy,
    yearOptions,
    // Loading
    isLoading,
    // Constants
    backtestStart, backtestEnd, CURRENT_YEAR,
  }
}

export const formatPercent = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "..."
  return `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`
}

export const SECTOR_COLORS = [
  "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
  "#db2777", "#0891b2", "#65a30d", "#ea580c", "#4f46e5", "#0d9488"
]

export const CHART_COLORS = {
  historical: "#0ea5e9",
  actuals: "#22c55e",
  forecast: "#a855f7",
  benchmark: "#64748b",
  confidenceBand: "#a855f7",
}
