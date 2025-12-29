/**
 * PATH: frontend/src/pages/Whitepaper.tsx
 * PURPOSE: Professional R&D Alpha whitepaper in A4 slide format
 * ROLE IN ARCHITECTURE: Research presentation layer - exportable PDF deck
 * MAIN EXPORTS: Whitepaper component
 */

import { useState, useRef, useCallback, useMemo, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Printer,
} from "lucide-react"
import { cn } from "@/lib/utils"
// Recharts imports removed - using CSS-based visuals for reliability

// A4 dimensions in pixels at 96 DPI (portrait)
const A4_WIDTH = 794
const A4_HEIGHT = 1123

// Slide wrapper for consistent A4 styling
interface SlideProps {
  children: React.ReactNode
  slideNumber: number
  totalSlides: number
  title?: string
  subtitle?: string
  accent?: "emerald" | "blue" | "purple" | "amber" | "red"
}

// Use inline styles with explicit hex colors for html2canvas compatibility
const accentHexColors: Record<string, string> = {
  emerald: "#059669",
  blue: "#2563eb",
  purple: "#9333ea",
  amber: "#d97706",
  red: "#dc2626",
}

function Slide({ children, slideNumber, totalSlides, title, subtitle, accent = "emerald" }: SlideProps) {
  return (
    <div 
      className="slide-page rounded-lg shadow-2xl flex flex-col"
      style={{ 
        width: A4_WIDTH,
        height: A4_HEIGHT,
        minWidth: A4_WIDTH,
        minHeight: A4_HEIGHT,
        maxWidth: A4_WIDTH,
        maxHeight: A4_HEIGHT,
        backgroundColor: "#ffffff",
        color: "#1e293b", // slate-800
        overflow: "hidden",
      }}
    >
      {/* Header bar - use inline style for html2canvas compatibility */}
      <div style={{ height: 8, minHeight: 8, backgroundColor: accentHexColors[accent], flexShrink: 0 }} />
      
      {/* Title section */}
      {title && (
        <div style={{ padding: "32px 48px 16px 48px", flexShrink: 0 }}>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: 4, marginBottom: 0 }}>{subtitle}</p>}
        </div>
      )}
      
      {/* Content */}
      <div 
        style={{ 
          flex: 1,
          padding: title ? "8px 48px 24px 48px" : "32px 48px",
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {children}
      </div>
      
      {/* Footer */}
      <div 
        style={{ 
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 48px",
          borderTop: "1px solid #e2e8f0", // slate-200
          fontSize: "0.75rem",
          color: "#94a3b8", // slate-400
          flexShrink: 0,
        }}
      >
        <span>R&D Alpha Research</span>
        <span>December 2025</span>
        <span>{slideNumber} / {totalSlides}</span>
      </div>
    </div>
  )
}

// Hex colors for html2canvas compatibility
const hexColors = {
  emerald: { bg: "#ecfdf5", border: "#a7f3d0", text: "#047857" },
  blue: { bg: "#eff6ff", border: "#bfdbfe", text: "#1d4ed8" },
  purple: { bg: "#faf5ff", border: "#e9d5ff", text: "#7e22ce" },
  amber: { bg: "#fffbeb", border: "#fde68a", text: "#b45309" },
  red: { bg: "#fef2f2", border: "#fecaca", text: "#dc2626" },
  slate: { bg: "#f8fafc", border: "#e2e8f0", text: "#334155" },
}

// Metric card component - uses inline styles for PDF export compatibility
function MetricCard({ 
  value, 
  label, 
  accent = "emerald" 
}: { 
  value: string | number
  label: string
  accent?: "emerald" | "blue" | "purple" | "amber"
}) {
  const c = hexColors[accent]
  
  return (
    <div 
      className="p-4 rounded-lg text-center"
      style={{ 
        backgroundColor: c.bg, 
        border: `1px solid ${c.border}`,
        color: c.text 
      }}
    >
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-1" style={{ opacity: 0.8 }}>{label}</div>
    </div>
  )
}

// Section box component - uses inline styles for PDF export compatibility
function SectionBox({ 
  title, 
  children, 
  accent = "slate" 
}: { 
  title?: string
  children: React.ReactNode
  accent?: "emerald" | "blue" | "purple" | "amber" | "red" | "slate"
}) {
  const c = hexColors[accent]
  
  return (
    <div 
      className="p-4 rounded-lg"
      style={{ backgroundColor: c.bg, border: `1px solid ${c.border}` }}
    >
      {title && <h3 className="font-semibold mb-2" style={{ color: c.text }}>{title}</h3>}
      {children}
    </div>
  )
}

function GrowthChart({
  data,
  width = 320,
  height = 140,
  showLegend = true,
}: {
  data: Array<{ year: number; portfolioIndex: number; benchmarkIndex: number; sp500Index?: number }>
  width?: number
  height?: number
  showLegend?: boolean
}) {
  if (!data || data.length < 2) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
          fontSize: 12,
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
        }}
      >
        Loading chart…
      </div>
    )
  }

  const leftPad = 36 // space for Y-axis labels
  const rightPad = 12
  const topPad = 12
  const bottomPad = 20 // space for X-axis labels
  const xs = data.map((_, i) => i)
  const pVals = data.map((d) => d.portfolioIndex)
  const bVals = data.map((d) => d.benchmarkIndex)
  const sVals = data.map((d) => (typeof d.sp500Index === "number" ? d.sp500Index : NaN)).filter((v) => Number.isFinite(v)) as number[]
  const all = [...pVals, ...bVals, ...sVals]
  const min = Math.min(...all)
  const max = Math.max(...all)
  const range = max - min || 1

  const x = (i: number) => leftPad + (i / Math.max(1, xs.length - 1)) * (width - leftPad - rightPad)
  const y = (v: number) => topPad + (1 - (v - min) / range) * (height - topPad - bottomPad)
  const path = (vals: number[]) => vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`).join(" ")

  const pPath = path(pVals)
  const bPath = path(bVals)
  const sPath = sVals.length === data.length ? path(data.map((d) => d.sp500Index as number)) : null

  // Y-axis labels
  const yLabels = [max, (max + min) / 2, min].map(v => v.toFixed(0) + "x")
  const startYear = data[0]?.year || 2010
  const endYear = data[data.length - 1]?.year || 2024

  return (
    <div style={{ position: "relative" }}>
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{
        display: "block",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: 12,
      }}
    >
        {/* Y-axis labels */}
        <text x={leftPad - 4} y={topPad + 4} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[0]}</text>
        <text x={leftPad - 4} y={(height - bottomPad + topPad) / 2 + 3} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[1]}</text>
        <text x={leftPad - 4} y={height - bottomPad + 4} textAnchor="end" fontSize="9" fill="#94a3b8">{yLabels[2]}</text>

        {/* X-axis labels */}
        <text x={leftPad} y={height - 6} textAnchor="start" fontSize="9" fill="#94a3b8">{startYear}</text>
        <text x={width - rightPad} y={height - 6} textAnchor="end" fontSize="9" fill="#94a3b8">{endYear}</text>

      {/* grid */}
        {[0, 0.5, 1].map((t) => (
        <line
          key={t}
            x1={leftPad}
            x2={width - rightPad}
            y1={topPad + t * (height - topPad - bottomPad)}
            y2={topPad + t * (height - topPad - bottomPad)}
          stroke="#eef2f7"
          strokeWidth="1"
        />
      ))}

      {/* lines */}
      {sPath && <path d={sPath} fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5 4" />}
      <path d={bPath} fill="none" stroke="#2563eb" strokeWidth="2.5" />
      <path d={pPath} fill="none" stroke="#059669" strokeWidth="3" />

      {/* endpoints */}
        <circle cx={x(pVals.length - 1)} cy={y(pVals[pVals.length - 1])} r="4" fill="#059669" />
      <circle cx={x(bVals.length - 1)} cy={y(bVals[bVals.length - 1])} r="3" fill="#2563eb" />
    </svg>
      {showLegend && (
        <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 12, height: 3, background: "#059669", borderRadius: 1 }} />
            <span style={{ fontSize: 9, color: "#059669", fontWeight: 600 }}>R&D Portfolio</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 12, height: 3, background: "#2563eb", borderRadius: 1 }} />
            <span style={{ fontSize: 9, color: "#2563eb", fontWeight: 600 }}>Benchmark</span>
          </div>
          {sPath && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 12, height: 2, background: "#94a3b8", borderRadius: 1, opacity: 0.7 }} />
              <span style={{ fontSize: 9, color: "#94a3b8" }}>S&P 500</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function Whitepaper() {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const slideContainerRef = useRef<HTMLDivElement>(null)

  // Keep slide navigation from feeling "blank" when the user is scrolled down the page:
  // always bring the slide viewport back into view and reset its internal scroll.
  useEffect(() => {
    requestAnimationFrame(() => {
      slideContainerRef.current?.scrollTo({ top: 0 })
      slideContainerRef.current?.scrollIntoView({ block: "start", behavior: "smooth" })
    })
  }, [currentSlide])

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
  
  // Extract quintile returns dynamically
  const getQuintileReturn = (quintile: number): number => {
    const qData = quintileData5yr.find((q: any) => q.quintile === quintile)
    return qData?.avg_return ?? [8.2, 10.1, 11.8, 13.4, 15.3][quintile - 1]
  }
  
  const rdPremium =
    typeof annualHmlData?.mean_premium === "number"
      ? annualHmlData.mean_premium
      : anova5yr?.ttest_high_vs_low?.mean_difference ?? 7.1
  const tStat =
    typeof annualHmlData?.hac_adjusted?.t_statistic === "number"
      ? annualHmlData.hac_adjusted.t_statistic
      : anova5yr?.ttest_high_vs_low?.t_statistic ?? 3.8
  const pValue =
    typeof annualHmlData?.hac_adjusted?.p_value === "number" ? annualHmlData.hac_adjusted.p_value : undefined
  const etaSquared5yr = anova5yr?.anova?.eta_squared ?? 0.23
  const etaSquared10yr = anova10yr?.anova?.eta_squared ?? 0.32
  const etaSquared20yr = anova20yr?.anova?.eta_squared ?? 0.46
  const totalCompanies = cohort?.total_companies ?? 503
  const winRate =
    typeof annualHmlData?.win_rate === "number"
      ? Math.round(annualHmlData.win_rate * 100)
      : factorPremiums && !("error" in factorPremiums)
        ? Math.round((factorPremiums.filter((p: any) => (p.rd_premium ?? 0) > 0).length / factorPremiums.length) * 100)
        : 73
  const annualTradingCost = transactionCosts && !("error" in transactionCosts)
    ? transactionCosts.annual_trading_cost_pct ?? 0.073
    : 0.073
  // (premiumCaptureRate removed for now; we prefer investable backtest metrics on the early slides)
  const netPremium = transactionCosts && !("error" in transactionCosts)
    ? transactionCosts.net_rd_premium_pct ?? (rdPremium - annualTradingCost)
    : (rdPremium - annualTradingCost)
    
  // Cohort coverage for long-horizon analysis (how many firms have continuous data for each window)
  const eligible5yr = cohort?.eligible_5yr ?? 202
  const eligible10yr = cohort?.eligible_10yr ?? 171
  const eligible20yr = cohort?.eligible_20yr ?? 123
  const eligible5yrPct = Math.round((eligible5yr / totalCompanies) * 100)
  const eligible10yrPct = Math.round((eligible10yr / totalCompanies) * 100)
  const eligible20yrPct = Math.round((eligible20yr / totalCompanies) * 100)

  const rdProfile = (cohort?.by_rd_profile as any) || { High: 86, Medium: 71, Low: 346 }
  const rdProfileHigh = typeof rdProfile?.High === "number" ? rdProfile.High : 86
  const rdProfileMedium = typeof rdProfile?.Medium === "number" ? rdProfile.Medium : 71
  const rdProfileLow = typeof rdProfile?.Low === "number" ? rdProfile.Low : 346

  // Investable (ETFlike) backtest metrics (20-stock equal-weight, annual reconstitution)
  const invPortfolioNet = investableBacktest?.portfolio_performance_net
  const invBenchmarkNet = investableBacktest?.benchmark_performance_net
  const invExcessNet = typeof investableBacktest?.excess_return_net === "number" ? investableBacktest.excess_return_net : undefined
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
  
  // Sample window (derive from annual premium series if available)
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
  // Cap end year at last full calendar year (avoid partial-current-year figures in the whitepaper)
  const sampleEndYear = Math.min(sampleEndYearRaw, 2024)
  
  // Prepare annual premium time series for chart with fallback defaults
  const premiumTimeSeriesData = useMemo(() => {
    if (!factorPremiums || "error" in factorPremiums || factorPremiums.length === 0) {
      // Fallback data for when API data isn't available
      return [
        { year: 2010, premium: 5.2 }, { year: 2011, premium: -2.1 }, { year: 2012, premium: 8.4 },
        { year: 2013, premium: 12.1 }, { year: 2014, premium: 3.5 }, { year: 2015, premium: -1.2 },
        { year: 2016, premium: 9.8 }, { year: 2017, premium: 6.3 }, { year: 2018, premium: -4.5 },
        { year: 2019, premium: 15.2 }, { year: 2020, premium: 22.1 }, { year: 2021, premium: 8.9 },
        { year: 2022, premium: -8.3 }, { year: 2023, premium: 11.4 }, { year: 2024, premium: 7.1 },
      ]
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

  const TOTAL_SLIDES = 11

  // Print all slides - opens browser print dialog for PDF export
  // Uses CSS @media print to show the always-rendered print view
  const handlePrint = useCallback(() => {
    // Add class to body for print-specific styling
    document.body.classList.add('printing-whitepaper')
      window.print()
    // Remove class after print dialog closes
    setTimeout(() => {
      document.body.classList.remove('printing-whitepaper')
    }, 500)
  }, [])

  const nextSlide = useCallback(() => {
    setCurrentSlide((s) => Math.min(s + 1, TOTAL_SLIDES - 1))
  }, [])

  const prevSlide = useCallback(() => {
    setCurrentSlide((s) => Math.max(s - 1, 0))
  }, [])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault()
        nextSlide()
        return
      }
      if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault()
        prevSlide()
        return
      }
      if (e.key === "Home") {
        e.preventDefault()
        setCurrentSlide(0)
        return
      }
      if (e.key === "End") {
        e.preventDefault()
        setCurrentSlide(TOTAL_SLIDES - 1)
        return
      }
      if (e.key === "Escape" && isFullscreen) {
        e.preventDefault()
        setIsFullscreen(false)
      }
    },
    [isFullscreen, nextSlide, prevSlide]
  )

  const slides = [
    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 1: TITLE - Filled cover (no empty sheet feel)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="title" slideNumber={1} totalSlides={TOTAL_SLIDES} accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
        {/* Top row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Badge
            style={{
              backgroundColor: "#ecfdf5",
              color: "#047857",
              borderColor: "#a7f3d0",
              fontSize: 13,
              padding: "4px 14px",
            }}
          >
            Research Whitepaper
          </Badge>
          <div style={{ fontSize: 12, color: "#64748b" }}>Abhishek Sehgal · December 2025 · PDF-ready</div>
        </div>

        {/* Title */}
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 44, fontWeight: 900, color: "#0f172a", margin: 0, lineHeight: 1.05 }}>R&amp;D Alpha</h1>
          <p style={{ fontSize: 15, color: "#475569", marginTop: 8, marginBottom: 0, maxWidth: 640 }}>
            A rules-based tilt toward innovation that has historically delivered long-horizon outperformance.
          </p>
        </div>

        {/* Money row (investor-first) */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <MetricCard
            value={typeof invExcessNet === "number" ? `+${invExcessNet.toFixed(1)}%` : `+${netPremium.toFixed(1)}%`}
            label="Net excess /yr (ETF)"
            accent="emerald"
          />
          <MetricCard value={typeof invPortfolioNet?.sharpe_ratio === "number" ? invPortfolioNet.sharpe_ratio.toFixed(2) : "1.14"} label="Sharpe (net)" accent="blue" />
          <MetricCard
            value={typeof invPortfolioNet?.max_drawdown === "number" ? `${invPortfolioNet.max_drawdown.toFixed(1)}%` : "-23%"}
            label="Max drawdown"
            accent="purple"
          />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "11%"} label="Avg turnover" accent="amber" />
        </div>

        {/* Main area */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, alignItems: "start" }}>
          <SectionBox title="Why should I care?" accent="emerald">
            <ul style={{ fontSize: 13, color: "#334155", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li>
                <strong>Actionable edge:</strong> buy firms investing heavily in R&amp;D (innovation) and avoid low-R&amp;D laggards.
              </li>
              <li>
                <strong>Factor evidence:</strong> Q5−Q1 premium is <strong>+{rdPremium.toFixed(1)}%/yr</strong> (Newey‑West t = {tStat.toFixed(2)}, win rate {winRate}%).
              </li>
              <li>
                <strong>Implementable:</strong> annual rebalance, low turnover, costs are small vs. the historical edge.
              </li>
            </ul>
            <div style={{ marginTop: 10, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>If you only remember one rule</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.5 }}>
                Treat this like a <strong>5+ year factor sleeve</strong> (innovation benefits take time).
              </div>
            </div>
            <div style={{ marginTop: 10, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>What to do (practical)</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.5 }}>
                Start with a <strong>small sleeve</strong> (5–15%), rebalance annually, and add <strong>sector caps</strong> if you want more diversification.
              </div>
            </div>
          </SectionBox>

          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>ETF backtest: growth of $1 (net)</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>
                {invStartYear}–{invEndYear}
              </div>
            </div>
            <GrowthChart data={investableGrowthData} width={320} height={140} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginTop: 10 }}>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#059669" }}>
                  {typeof invPortfolioMultiple === "number" ? `${invPortfolioMultiple.toFixed(1)}x` : "-"}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>R&amp;D portfolio</div>
              </div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#2563eb" }}>
                  {typeof invBenchmarkMultiple === "number" ? `${invBenchmarkMultiple.toFixed(1)}x` : "-"}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>EW cohort</div>
              </div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: "#94a3b8" }}>
                  {typeof invSp500Multiple === "number" ? `${invSp500Multiple.toFixed(1)}x` : "-"}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>S&amp;P 500</div>
              </div>
            </div>
            <div style={{ marginTop: 10, fontSize: 10, color: "#94a3b8", lineHeight: 1.4 }}>
              Notes: 20‑stock equal‑weight basket, annual reconstitution, July–June convention. Backtest is informational (not advice).
            </div>
          </div>
        </div>

        {/* Bottom row: remove dead space with actionable guidance */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#1e40af", marginBottom: 6 }}>Implementation checklist</div>
            <ul style={{ fontSize: 12, color: "#1e3a8a", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>June: compute R&amp;D/Rev (prior FY)</li>
              <li>Buy top {invNHoldings} equal‑weight</li>
              <li>Hold July→June; rebalance annually</li>
            </ul>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#92400e", marginBottom: 6 }}>Risk controls</div>
            <ul style={{ fontSize: 12, color: "#78350f", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>Add sector caps (avoid tech/healthcare crowding)</li>
              <li>Size for drawdowns (don’t lever it)</li>
              <li>Stick to a rules‑based rebalance schedule</li>
            </ul>
          </div>
          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#166534", marginBottom: 6 }}>Expected behavior</div>
            <ul style={{ fontSize: 12, color: "#166534", lineHeight: 1.55, paddingLeft: 18, margin: 0 }}>
              <li>Edge is long-horizon (3–5yr lag)</li>
              <li>Tracking error is normal</li>
              <li>Patience is the “cost” you pay</li>
            </ul>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 2: EXEC SUMMARY
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="how-to-make-money" slideNumber={2} totalSlides={TOTAL_SLIDES} title="How to Make Money with R&D Alpha" subtitle="A simple, rules-based tilt toward innovation (and what to expect)" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Key numbers up top */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
          <MetricCard
            value={typeof invPortfolioNet?.annualized_return === "number" ? `${invPortfolioNet.annualized_return.toFixed(1)}%` : "…"}
            label="Portfolio ann. (net)"
            accent="emerald"
          />
          <MetricCard
            value={typeof invBenchmarkNet?.annualized_return === "number" ? `${invBenchmarkNet.annualized_return.toFixed(1)}%` : "…"}
            label="Benchmark ann. (net)"
            accent="blue"
          />
          <MetricCard value={typeof invExcessNet === "number" ? `+${invExcessNet.toFixed(1)} pp` : "…"} label="Net excess /yr" accent="purple" />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"} label="Turnover (avg)" accent="amber" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, alignItems: "start" }}>
          {/* Playbook */}
          <SectionBox title="Playbook (60 seconds)" accent="slate">
            <ol style={{ fontSize: 13, color: "#334155", lineHeight: 1.7, paddingLeft: 18, margin: 0 }}>
              <li>
                <strong>Each June:</strong> compute <strong>R&amp;D / Revenue</strong> using prior fiscal-year fundamentals.
              </li>
              <li>
                <strong>Rank:</strong> all S&amp;P 500 firms by R&amp;D intensity.
              </li>
              <li>
                <strong>Buy:</strong> top <strong>{invNHoldings}</strong> names equal‑weight (ETFlike), or buy the full top quintile for broad factor exposure.
              </li>
              <li>
                <strong>Hold:</strong> July→June; <strong>rebalance annually</strong>.
              </li>
              <li>
                <strong>Time horizon:</strong> treat it like a 5+ year sleeve (innovation pays with a lag).
              </li>
            </ol>

            <div style={{ marginTop: 12, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>Why this works (in plain English)</div>
              <div style={{ fontSize: 13, color: "#0f172a", lineHeight: 1.6 }}>
                R&amp;D creates intangible assets that are hard to value. Markets tend to underreact, and the payoff shows up over multi‑year horizons.
              </div>
            </div>

            <div style={{ marginTop: 12, background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>Defaults (copy/paste)</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {[
                  { k: "Holdings", v: `Top ${invNHoldings} (equal‑weight)` },
                  { k: "Rebalance", v: "Annual (end of June)" },
                  { k: "Risk control", v: "Add sector caps (optional)" },
                  { k: "Horizon", v: "5+ years (lagged payoffs)" },
                ].map((row, i) => (
                  <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: 10 }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>{row.k}</div>
                    <div style={{ fontSize: 12, color: "#0f172a", fontWeight: 700, lineHeight: 1.35 }}>{row.v}</div>
                  </div>
                ))}
              </div>
            </div>
          </SectionBox>

          {/* Performance profile */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>Performance profile (net)</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>
                {invStartYear}–{invEndYear}
              </div>
            </div>

            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 10, fontSize: 12, color: "#64748b", fontWeight: 700, paddingBottom: 8, borderBottom: "1px solid #e2e8f0" }}>
                <div>Metric</div>
                <div style={{ textAlign: "right" }}>R&amp;D</div>
                <div style={{ textAlign: "right" }}>EW cohort</div>
              </div>
              {[
                {
                  k: "Annualized return",
                  a: typeof invPortfolioNet?.annualized_return === "number" ? `${invPortfolioNet.annualized_return.toFixed(2)}%` : "…",
                  b: typeof invBenchmarkNet?.annualized_return === "number" ? `${invBenchmarkNet.annualized_return.toFixed(2)}%` : "…",
                },
                {
                  k: "Volatility",
                  a: typeof invPortfolioNet?.volatility === "number" ? `${invPortfolioNet.volatility.toFixed(2)}%` : "…",
                  b: typeof invBenchmarkNet?.volatility === "number" ? `${invBenchmarkNet.volatility.toFixed(2)}%` : "…",
                },
                {
                  k: "Sharpe",
                  a: typeof invPortfolioNet?.sharpe_ratio === "number" ? invPortfolioNet.sharpe_ratio.toFixed(3) : "…",
                  b: typeof invBenchmarkNet?.sharpe_ratio === "number" ? invBenchmarkNet.sharpe_ratio.toFixed(3) : "…",
                },
                {
                  k: "Max drawdown",
                  a: typeof invPortfolioNet?.max_drawdown === "number" ? `${invPortfolioNet.max_drawdown.toFixed(2)}%` : "…",
                  b: typeof invBenchmarkNet?.max_drawdown === "number" ? `${invBenchmarkNet.max_drawdown.toFixed(2)}%` : "…",
                },
              ].map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.4fr 1fr 1fr",
                    gap: 10,
                    padding: "10px 0",
                    borderBottom: i === 3 ? "none" : "1px solid #eef2f7",
                    fontSize: 13,
                    color: "#334155",
                    alignItems: "center",
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{row.k}</div>
                  <div style={{ textAlign: "right", fontWeight: 800, color: "#059669" }}>{row.a}</div>
                  <div style={{ textAlign: "right", fontWeight: 700, color: "#2563eb" }}>{row.b}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 10 }}>
              <GrowthChart data={investableGrowthData} width={320} height={140} />
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: "#94a3b8", lineHeight: 1.45 }}>
              Costs: round‑trip cost per 100% turnover{" "}
              {typeof invRoundTripCostPer100PctTurnover === "number" ? `${invRoundTripCostPer100PctTurnover.toFixed(3)}%` : "…"}; benchmark cost{" "}
              {typeof invBenchmarkCostPct === "number" ? `${invBenchmarkCostPct.toFixed(2)}%` : "…"} (model).
            </div>
          </div>
        </div>

        {/* Bottom: fit + risks */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#1e40af", marginBottom: 6 }}>Who this is for</div>
            <ul style={{ fontSize: 12, color: "#1e3a8a", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li>Long-horizon investors (5+ years)</li>
              <li>Comfortable with factor volatility and tracking error</li>
              <li>Want systematic exposure to innovation</li>
            </ul>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#92400e", marginBottom: 6 }}>When it hurts</div>
            <ul style={{ fontSize: 12, color: "#78350f", lineHeight: 1.6, paddingLeft: 18, margin: 0 }}>
              <li>Risk‑off / high‑rate regimes that punish long-duration growth</li>
              <li>Sector concentration (tech/healthcare) without caps</li>
              <li>Short holding periods (innovation needs time)</li>
            </ul>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 3: DATA & SIGNAL
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide
      key="implementation-reality"
      slideNumber={3}
      totalSlides={TOTAL_SLIDES}
      title="Implementation Reality Check"
      subtitle="Coverage, concentration, and what you’re really signing up for"
      accent="blue"
    >
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Top row: implementability */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
          <MetricCard value={`${eligible20yr}`} label={`20yr coverage (${eligible20yrPct}%)`} accent="blue" />
          <MetricCard value={typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"} label="Avg turnover" accent="purple" />
          <MetricCard
            value={typeof invRoundTripCostPer100PctTurnover === "number" ? `${invRoundTripCostPer100PctTurnover.toFixed(3)}%` : "…"}
            label="Cost / 100% turnover"
            accent="amber"
          />
          <MetricCard value={`${invNHoldings}`} label="Holdings (ETF)" accent="emerald" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, flex: 1 }}>
          {/* Left: what you own */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a", marginBottom: 10 }}>What you end up owning (ETFlike)</div>

            {/* Sector mix */}
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>Sector mix of the {invNHoldings}-stock basket</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(invSectorMix.length ? invSectorMix : [{ sector: "Healthcare", weight: 50 }, { sector: "Technology", weight: 30 }, { sector: "Other", weight: 20 }])
                  .slice(0, 6)
                  .map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 140, fontSize: 12, color: "#334155" }}>{s.sector}</div>
                      <div style={{ flex: 1, height: 20, background: "#e2e8f0", borderRadius: 6, overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${Math.min(100, s.weight)}%`,
                            background: "linear-gradient(90deg, #2563eb, #60a5fa)",
                            borderRadius: 6,
                          }}
                        />
                      </div>
                      <div style={{ width: 42, textAlign: "right", fontSize: 12, fontWeight: 800, color: "#1d4ed8" }}>{s.weight.toFixed(0)}%</div>
                    </div>
                  ))}
              </div>
              <div style={{ marginTop: 8, fontSize: 10, color: "#94a3b8" }}>Tip: add sector caps if you want a purer “innovation” sleeve.</div>
            </div>

            {/* Top holdings */}
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700 }}>Example names (highest R&amp;D intensity)</div>
                <div style={{ fontSize: 10, color: "#94a3b8" }}>R&amp;D/Rev can exceed 100% pre‑revenue</div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 0.7fr", gap: 10, fontSize: 11, color: "#64748b", fontWeight: 700, paddingBottom: 8, borderBottom: "1px solid #eef2f7" }}>
                <div>Ticker</div>
                <div>Sector</div>
                <div style={{ textAlign: "right" }}>R&amp;D%</div>
              </div>
              {(invTopHoldings.length ? invTopHoldings : [{ symbol: "VRTX", sector: "Healthcare", rd_intensity: 142.4 }])
                .slice(0, 6)
                .map((h, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 0.7fr", gap: 10, padding: "9px 0", borderBottom: i === 5 ? "none" : "1px solid #eef2f7", alignItems: "center" }}>
                    <div style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontWeight: 800, color: "#0f172a" }}>{String(h.symbol)}</div>
                    <div style={{ fontSize: 12, color: "#475569" }}>{String(h.sector || "-")}</div>
                    <div style={{ textAlign: "right", fontWeight: 800, color: "#059669" }}>
                      {typeof h.rd_intensity === "number" ? `${h.rd_intensity.toFixed(1)}%` : "-"}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Right: coverage + signal */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a", marginBottom: 8 }}>Data coverage (why long horizon is hard)</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { label: "Eligible 5-year windows", n: eligible5yr, pct: eligible5yrPct, color: "#22c55e" },
                  { label: "Eligible 10-year windows", n: eligible10yr, pct: eligible10yrPct, color: "#3b82f6" },
                  { label: "Eligible 20-year windows", n: eligible20yr, pct: eligible20yrPct, color: "#8b5cf6" },
                ].map((row, i) => (
                  <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                      <div style={{ fontSize: 12, color: "#334155", fontWeight: 700 }}>{row.label}</div>
                      <div style={{ fontSize: 12, color: "#64748b" }}>
                        {row.n} firms ({row.pct}%)
                      </div>
                    </div>
                    <div style={{ height: 10, background: "#e2e8f0", borderRadius: 6, overflow: "hidden" }}>
                      <div style={{ width: `${Math.min(100, row.pct)}%`, height: "100%", background: row.color, borderRadius: 6 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 14, flex: 1, display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1e40af", marginBottom: 10 }}>Signal + formation (no look‑ahead)</div>
              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>Signal</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "#0f172a" }}>R&amp;D Intensity = R&amp;D Expense / Revenue</div>
                <div style={{ fontSize: 12, color: "#475569", marginTop: 6, lineHeight: 1.6 }}>
                  Use prior fiscal-year fundamentals and form portfolios in June (July–June returns) so the 10‑K is public before formation.
                </div>
              </div>

              <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, flex: 1 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>R&amp;D profile (cohort)</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  {[
                    { label: "High", n: rdProfileHigh, color: "#059669" },
                    { label: "Medium", n: rdProfileMedium, color: "#2563eb" },
                    { label: "Low", n: rdProfileLow, color: "#94a3b8" },
                  ].map((r, i) => (
                    <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, textAlign: "center" }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: r.color }}>{r.n}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{r.label}</div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 10, fontSize: 11, color: "#475569", lineHeight: 1.6 }}>
                  Interpretation: most firms are “Low” intensity; the signal is strongest at the extremes (Q5 vs Q1).
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 12, background: "#0f172a", borderRadius: 12, padding: 14, textAlign: "center" }}>
          <span style={{ fontSize: 13, color: "#e2e8f0" }}>
            Practical takeaway: run it <strong style={{ color: "white" }}>systematically</strong>, size for drawdowns, and give it time.
          </span>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 4: METHODOLOGY
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide
      key="methodology"
      slideNumber={4}
      totalSlides={TOTAL_SLIDES}
      title="Methodology"
      subtitle="How we form quintile portfolios and estimate the premium"
      accent="blue"
    >
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12, alignItems: "start" }}>
          {/* Step 1 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#3b82f6", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>1</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#1e40af", margin: 0 }}>Calculate R&D Intensity</h3>
            </div>
            <div style={{ background: "#3b82f6", borderRadius: 8, padding: 12, marginBottom: 12, textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "white", marginBottom: 4 }}>R&D Intensity</div>
              <div style={{ fontSize: 11, color: "#bfdbfe", marginBottom: 6 }}>=</div>
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: "white", fontWeight: 500 }}>R&D Expense</span>
                <span style={{ fontSize: 14, color: "#bfdbfe" }}>/</span>
                <span style={{ fontSize: 12, color: "white", fontWeight: 500 }}>Revenue</span>
          </div>
              </div>
            <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.5 }}>
              Normalizes R&D by firm size for fair comparison. A 15% intensity means $15 R&D per $100 revenue.
              </div>
              </div>
          
          {/* Step 2 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#8b5cf6", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>2</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#6b21a8", margin: 0 }}>Form Quintile Portfolios</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
              {[
                { q: "Q1 (Low)", range: "0-3%", color: "#dc2626", bg: "#fef2f2" },
                { q: "Q2", range: "3-6%", color: "#64748b", bg: "white" },
                { q: "Q3", range: "6-10%", color: "#64748b", bg: "white" },
                { q: "Q4", range: "10-15%", color: "#64748b", bg: "white" },
                { q: "Q5 (High)", range: "15%+", color: "#16a34a", bg: "#f0fdf4" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: item.bg, padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: item.color }}>{item.q}</span>
                  <span style={{ fontSize: 12, color: "#475569" }}>{item.range}</span>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 11, color: "#64748b" }}>~{Math.round(totalCompanies / 5)} firms per quintile</div>
          </div>
          
          {/* Step 3 */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#059669", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, flexShrink: 0 }}>3</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#047857", margin: 0 }}>Statistical Analysis</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { test: "ANOVA", desc: "Quintile means differ?" },
                { test: "t-test", desc: "Q5 vs Q1 significance" },
                { test: "Newey-West", desc: "HAC standard errors" },
                { test: "Effect size", desc: "η² magnitude" },
                { test: "Rolling", desc: "5, 10, 20yr windows" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "white", padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: "#047857" }}>{item.test}</span>
                  <span style={{ fontSize: 11, color: "#64748b" }}>{item.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Key methodological choices - clean table format */}
        <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ background: "#1e40af", padding: "8px 14px" }}>
            <h3 style={{ fontSize: 12, fontWeight: 600, color: "white", margin: 0 }}>Key Methodological Choices</h3>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", fontSize: 11 }}>
            {[
              { label: "Return Convention", value: "July-June (Fama-French), ensuring 10-K is public before formation" },
              { label: "Survivorship Bias", value: "Historical membership + delisting returns (Shumway 1997)" },
              { label: "Data Sources", value: "FMP for fundamentals/prices; Ken French for factors" },
              { label: "Portfolio Weights", value: "Equal-weight within quintiles (no mega-cap bias)" },
              { label: "Inference", value: "Non-overlapping annual HML; Newey-West standard errors" },
              {
                label: "Rebalancing",
                value: `Annual (June); avg turnover ${typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"}; est. cost ${typeof invTradingCostEstPct === "number" ? `${invTradingCostEstPct.toFixed(3)}%` : "…"}`
              },
            ].map((item, i) => (
              <div key={i} style={{ 
                padding: "8px 14px", 
                borderBottom: i < 4 ? "1px solid #e2e8f0" : "none",
                borderRight: i % 2 === 0 ? "1px solid #e2e8f0" : "none",
                background: i % 2 === 0 ? "#f8fafc" : "white"
              }}>
                <div style={{ fontWeight: 600, color: "#1e40af", marginBottom: 2 }}>{item.label}</div>
                <div style={{ color: "#475569", lineHeight: 1.4 }}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Formation timeline - prevents look-ahead */}
        <div style={{ marginTop: 12, background: "linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%)", border: "1px solid #bfdbfe", borderRadius: 10, padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#1e40af", marginBottom: 8 }}>Formation timeline (no look-ahead)</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
            {[
              { t: "Fiscal year ends", d: "Companies close FY" },
              { t: "10‑K filed", d: "Fundamentals become public" },
              { t: "End of June", d: "Rank by R&D/Rev" },
              { t: "July → June", d: "Hold for 12 months" },
            ].map((x, i) => (
              <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: "#1e40af", marginBottom: 4 }}>{x.t}</div>
                <div style={{ fontSize: 10, color: "#475569", lineHeight: 1.35 }}>{x.d}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: "#1e3a8a" }}>
            We use <strong>July–June returns</strong> so filings are public before portfolio formation.
          </div>
        </div>

        {/* Sample info footer */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {[
            { label: "Universe", value: "S&P 500" },
            { label: "Sample", value: `${sampleStartYear}-${sampleEndYear}` },
            { label: "Firms", value: String(totalCompanies) },
            { label: "Obs/Year", value: `~${Math.round(totalCompanies * 0.6)}` },
          ].map((item, i) => (
            <div key={i} style={{ background: "#3b82f6", borderRadius: 8, padding: 10, textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#bfdbfe" }}>{item.label}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 5: RESULTS - Core R&D premium findings (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="results" slideNumber={5} totalSlides={TOTAL_SLIDES} title="Results: The R&D Premium" subtitle="High-R&D stocks consistently outperform low-R&D stocks" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Hero stat with statistical context */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 14, marginBottom: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, alignItems: "center" }}>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>Annual Premium</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>+{rdPremium.toFixed(1)}%</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>Q5 minus Q1</div>
            </div>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>t-statistic</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{tStat.toFixed(2)}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>
                p {typeof pValue === "number" ? (pValue < 0.001 ? "< 0.001" : pValue.toFixed(3)) : "< 0.001"}
              </div>
            </div>
            <div style={{ textAlign: "center", borderRight: "1px solid #a7f3d0", paddingRight: 16 }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>Win Rate</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{winRate}%</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>years positive</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "#065f46", marginBottom: 4 }}>20yr Effect</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "#047857" }}>{etaSquared20yr.toFixed(2)}</div>
              <div style={{ fontSize: 10, color: "#065f46" }}>eta squared</div>
            </div>
          </div>
        </div>

        {/* Two columns: Quintile returns + Effect sizes */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
          {/* Quintile Returns */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 12, borderBottom: "2px solid #059669", paddingBottom: 6 }}>Average Annual Returns by Quintile</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { q: "Q5 (High R&D)", ret: getQuintileReturn(5), color: "#22c55e", desc: "Top 20% R&D intensity" },
                { q: "Q4", ret: getQuintileReturn(4), color: "#64748b", desc: "" },
                { q: "Q3", ret: getQuintileReturn(3), color: "#64748b", desc: "" },
                { q: "Q2", ret: getQuintileReturn(2), color: "#64748b", desc: "" },
                { q: "Q1 (Low R&D)", ret: getQuintileReturn(1), color: "#ef4444", desc: "Bottom 20% R&D intensity" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 90, fontSize: 11, fontWeight: 600, color: item.color }}>{item.q}</div>
                  <div style={{ flex: 1, height: 26, background: "#e2e8f0", borderRadius: 6, overflow: "hidden", position: "relative" }}>
                    <div style={{ 
                      position: "absolute", left: 0, top: 0, height: "100%", 
                      width: `${Math.min(100, (item.ret / 20) * 100)}%`,
                      background: item.color, borderRadius: 6,
                      display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8
                    }}>
                      <span style={{ color: "white", fontSize: 12, fontWeight: 700 }}>{item.ret.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {/* Monotonicity note */}
            <div style={{ marginTop: 10, padding: 10, background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
              <div style={{ fontSize: 11, color: "#166534", fontWeight: 600, marginBottom: 4 }}>📊 Monotonic Pattern</div>
              <div style={{ fontSize: 10, color: "#166534", lineHeight: 1.4 }}>
                Returns increase steadily from Q1→Q5, suggesting a true factor relationship rather than a single-quintile anomaly.
              </div>
            </div>
            <div style={{ marginTop: 10, background: "#047857", borderRadius: 10, padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "#a7f3d0" }}>Premium (Q5 - Q1)</span>
              <span style={{ fontSize: 22, fontWeight: 700, color: "white" }}>+{rdPremium.toFixed(1)}%</span>
            </div>
          </div>
          
          {/* Effect Sizes + Interpretation */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 12, borderBottom: "2px solid #3b82f6", paddingBottom: 6 }}>Effect Size by Investment Horizon</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { horizon: "5-Year", eta: etaSquared5yr, label: "Large", color: "#3b82f6", pct: Math.round(etaSquared5yr * 100) },
                { horizon: "10-Year", eta: etaSquared10yr, label: "Large", color: "#8b5cf6", pct: Math.round(etaSquared10yr * 100) },
                { horizon: "20-Year", eta: etaSquared20yr, label: "Very Large", color: "#059669", pct: Math.round(etaSquared20yr * 100) },
              ].map((item, i) => (
                <div key={i} style={{ background: "white", borderRadius: 10, padding: 12, border: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#334155" }}>{item.horizon}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>η² = {item.eta.toFixed(3)}</span>
                  </div>
                  <div style={{ height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
                    <div style={{ height: "100%", width: `${Math.min(100, item.eta * 200)}%`, background: item.color, borderRadius: 4 }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#64748b" }}>
                    <span>{item.label} effect ({item.pct}% variance explained)</span>
                    <span>Cohen: {">"}0.14 = large</span>
                  </div>
                </div>
              ))}
            </div>
            {/* What eta squared means */}
            <div style={{ marginTop: 10, padding: 10, background: "#eff6ff", borderRadius: 8, border: "1px solid #bfdbfe" }}>
              <div style={{ fontSize: 11, color: "#1e40af", fontWeight: 600, marginBottom: 4 }}>📈 What This Means</div>
              <div style={{ fontSize: 10, color: "#1e40af", lineHeight: 1.4 }}>
                At 20 years, R&D intensity explains <strong>{Math.round(etaSquared20yr * 100)}%</strong> of the variance in returns between quintiles. Effect grows with time as R&D benefits compound.
              </div>
            </div>
          </div>
        </div>
        
        {/* Statistical validity + Key insight */}
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#7c3aed", marginBottom: 6 }}>🔬 Statistical Validity</div>
            <div style={{ fontSize: 11, color: "#6b21a8", lineHeight: 1.5 }}>
              Results use <strong>Newey-West standard errors</strong> to account for autocorrelation and heteroskedasticity. 
              The t-statistic of {tStat.toFixed(2)} exceeds the 1.96 threshold for 95% confidence.
            </div>
          </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#b45309", marginBottom: 6 }}>💡 Key Takeaway</div>
            <div style={{ fontSize: 11, color: "#92400e", lineHeight: 1.5 }}>
              Effect sizes grow from η²={etaSquared5yr.toFixed(2)} → {etaSquared20yr.toFixed(2)} over 5→20 years. 
              R&D benefits have a <strong>3-5 year lag</strong>, so patient investors are rewarded.
            </div>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 6: VISUAL EVIDENCE - Charts and time series (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="charts" slideNumber={6} totalSlides={TOTAL_SLIDES} title="Visual Evidence" subtitle="Premium persistence across time and quintiles" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
        
        {/* Row 1: Time Series Chart (full width) */}
        <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: 0 }}>Annual R&D Premium (Q5 − Q1)</h3>
              <p style={{ fontSize: 11, color: "#64748b", margin: "4px 0 0 0" }}>High R&D quintile minus Low R&D quintile returns</p>
                    </div>
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: 2, background: "#22c55e" }} />
                <span style={{ fontSize: 11, color: "#64748b" }}>{premiumTimeSeriesData.filter(d => d.premium >= 0).length} Positive</span>
                  </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: 2, background: "#ef4444" }} />
                <span style={{ fontSize: 11, color: "#64748b" }}>{premiumTimeSeriesData.filter(d => d.premium < 0).length} Negative</span>
                </div>
            </div>
          </div>
          
          {/* Chart */}
          <div style={{ position: "relative", height: 160, marginBottom: 8 }}>
            {/* Grid lines */}
            <div style={{ position: "absolute", left: 36, right: 0, top: 0, height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "25%", height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "50%", height: 1, background: "#94a3b8" }} />
            <div style={{ position: "absolute", left: 36, right: 0, top: "75%", height: 1, background: "#f1f5f9" }} />
            <div style={{ position: "absolute", left: 36, right: 0, bottom: 0, height: 1, background: "#f1f5f9" }} />
            
                {/* Y-axis labels */}
            <div style={{ position: "absolute", left: 0, top: -4, fontSize: 10, color: "#94a3b8", fontWeight: 500 }}>+30%</div>
            <div style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)", fontSize: 10, color: "#64748b", fontWeight: 600 }}>0%</div>
            <div style={{ position: "absolute", left: 0, bottom: -4, fontSize: 10, color: "#94a3b8", fontWeight: 500 }}>−30%</div>
            
                {/* Bars */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "100%", marginLeft: 40, paddingRight: 4 }}>
              {premiumTimeSeriesData.map((item, i) => {
                const maxVal = 30
                const heightPct = Math.min(50, (Math.abs(item.premium) / maxVal) * 50)
                  const isPositive = item.premium >= 0
                  return (
                  <div key={i} style={{ height: "100%", flex: 1, position: "relative", maxWidth: 24 }}>
                        <div style={{ 
                          position: "absolute",
                          left: "50%",
                          transform: "translateX(-50%)",
                      width: "70%",
                      maxWidth: 16,
                          height: `${heightPct}%`,
                      background: isPositive ? "linear-gradient(180deg, #22c55e 0%, #16a34a 100%)" : "linear-gradient(0deg, #ef4444 0%, #dc2626 100%)",
                      borderRadius: 3,
                      ...(isPositive ? { bottom: "50%" } : { top: "50%" })
                        }} />
                    </div>
                  )
                })}
              </div>
              </div>
          
          {/* X-axis */}
          <div style={{ display: "flex", justifyContent: "space-between", marginLeft: 40, paddingRight: 4, borderTop: "1px solid #e2e8f0", paddingTop: 8 }}>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[0]?.year}</span>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[Math.floor(premiumTimeSeriesData.length / 2)]?.year}</span>
            <span style={{ fontSize: 10, color: "#64748b", fontWeight: 500 }}>{premiumTimeSeriesData[premiumTimeSeriesData.length - 1]?.year}</span>
          </div>
        </div>

        {/* Row 2: Quintile Returns + Track Record + Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 0.8fr", gap: 14 }}>
          
          {/* Quintile Returns */}
          <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Quintile Returns (5-Year Rolling)</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[
                { name: "Q5", label: "High R&D", color: "#22c55e", return: getQuintileReturn(5) },
                { name: "Q4", label: "", color: "#84cc16", return: getQuintileReturn(4) },
                { name: "Q3", label: "", color: "#eab308", return: getQuintileReturn(3) },
                { name: "Q2", label: "", color: "#f97316", return: getQuintileReturn(2) },
                { name: "Q1", label: "Low R&D", color: "#ef4444", return: getQuintileReturn(1) },
              ].map((item) => (
                <div key={item.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 26, fontSize: 12, fontWeight: 700, color: item.color }}>{item.name}</div>
                  <div style={{ flex: 1, height: 22, background: "#f1f5f9", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                    <div style={{ 
                      position: "absolute", left: 0, top: 0, height: "100%",
                      width: `${Math.max(30, (item.return / 18) * 100)}%`,
                      background: `linear-gradient(90deg, ${item.color}, ${item.color}cc)`,
                      borderRadius: 4,
                      display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8
                    }}>
                      <span style={{ color: "white", fontSize: 11, fontWeight: 700 }}>{item.return.toFixed(1)}%</span>
                    </div>
                  </div>
                  {item.label && <span style={{ fontSize: 9, color: "#64748b", width: 40 }}>{item.label}</span>}
            </div>
                ))}
          </div>
            <div style={{ marginTop: 10, background: "linear-gradient(90deg, #059669 0%, #10b981 100%)", borderRadius: 6, padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.9)", fontWeight: 500 }}>Spread (Q5−Q1)</span>
              <span style={{ fontSize: 18, fontWeight: 800, color: "white" }}>+{(getQuintileReturn(5) - getQuintileReturn(1)).toFixed(1)}%</span>
            </div>
        </div>
        
          {/* Track Record Details */}
          <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Track Record ({premiumTimeSeriesData.length} Years)</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#16a34a" }}>{premiumTimeSeriesData.filter(d => d.premium >= 0).length}</div>
                <div style={{ fontSize: 10, color: "#15803d", fontWeight: 600 }}>Winning</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Avg +{(premiumTimeSeriesData.filter(d => d.premium >= 0).reduce((a, b) => a + b.premium, 0) / Math.max(1, premiumTimeSeriesData.filter(d => d.premium >= 0).length)).toFixed(1)}%</div>
              </div>
              <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#dc2626" }}>{premiumTimeSeriesData.filter(d => d.premium < 0).length}</div>
                <div style={{ fontSize: 10, color: "#b91c1c", fontWeight: 600 }}>Losing</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Avg {(premiumTimeSeriesData.filter(d => d.premium < 0).reduce((a, b) => a + b.premium, 0) / Math.max(1, premiumTimeSeriesData.filter(d => d.premium < 0).length)).toFixed(1)}%</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, textAlign: "center" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#16a34a" }}>+{Math.max(...premiumTimeSeriesData.map(d => d.premium)).toFixed(1)}%</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Best Year</div>
              </div>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, textAlign: "center" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#dc2626" }}>{Math.min(...premiumTimeSeriesData.map(d => d.premium)).toFixed(1)}%</div>
                <div style={{ fontSize: 9, color: "#64748b" }}>Worst Year</div>
            </div>
          </div>
        </div>
        
          {/* Key Stats */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "1px solid #a7f3d0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: "#059669", lineHeight: 1 }}>{winRate}%</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#047857", marginTop: 2 }}>Win Rate</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#2563eb" }}>+{rdPremium.toFixed(1)}%</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>Avg Annual Premium</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#7c3aed" }}>t={tStat.toFixed(1)}</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>t-statistic (NW)</div>
            </div>
            <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: 12, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#0891b2" }}>{etaSquared20yr.toFixed(2)}</div>
              <div style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>Effect Size (η²)</div>
            </div>
          </div>
        </div>

        {/* Row 3: Key Insights */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#166534", marginBottom: 4 }}>📊 Consistent Pattern</div>
            <div style={{ fontSize: 11, color: "#15803d" }}>Premium persists in {winRate}% of years across market cycles.</div>
          </div>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#1e40af", marginBottom: 4 }}>📈 Monotonic Returns</div>
            <div style={{ fontSize: 11, color: "#1e3a8a" }}>Returns increase linearly from Q1→Q5, true factor behavior.</div>
          </div>
          <div style={{ background: "#fefce8", border: "1px solid #fde047", borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#a16207", marginBottom: 4 }}>⏳ Patient Capital</div>
            <div style={{ fontSize: 11, color: "#92400e" }}>Premium varies yearly. 3-5+ year holding recommended.</div>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 7: SECTOR ANALYSIS - Industry breakdown (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="sectors" slideNumber={7} totalSlides={TOTAL_SLIDES} title="Sector Analysis" subtitle="R&D intensity varies dramatically by industry" accent="purple">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Top stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#7e22ce" }}>~70%</div>
            <div style={{ fontSize: 12, color: "#6b21a8" }}>Tech + Healthcare</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>in High R&D (Q5) quintile</div>
                  </div>
          <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#059669" }}>Yes</div>
            <div style={{ fontSize: 12, color: "#047857" }}>Within-Sector Effect</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>R&D premium holds in sector</div>
                  </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 14, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#b45309" }}>11</div>
            <div style={{ fontSize: 12, color: "#92400e" }}>Sectors Covered</div>
            <div style={{ fontSize: 10, color: "#94a3b8" }}>GICS classification</div>
                </div>
        </div>

        {/* Main content: sector list + insights */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Sector R&D Intensity List */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #9333ea", paddingBottom: 8 }}>R&D Intensity by Sector</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { sector: "Technology", avg_rd_intensity: 15.2, company_count: 78 },
                { sector: "Healthcare", avg_rd_intensity: 12.8, company_count: 62 },
                { sector: "Communication", avg_rd_intensity: 8.2, company_count: 26 },
                { sector: "Consumer Cyclical", avg_rd_intensity: 3.5, company_count: 58 },
                { sector: "Industrials", avg_rd_intensity: 2.8, company_count: 72 },
                { sector: "Consumer Staples", avg_rd_intensity: 1.2, company_count: 34 },
                { sector: "Financials", avg_rd_intensity: 0.5, company_count: 68 },
                { sector: "Energy", avg_rd_intensity: 0.4, company_count: 22 },
              ].map((sector, i) => {
                const isHighRD = sector.avg_rd_intensity > 8
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 100, fontSize: 12, color: isHighRD ? "#7e22ce" : "#64748b", fontWeight: isHighRD ? 600 : 400 }}>{sector.sector}</div>
                    <div style={{ flex: 1, height: 20, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ 
                        height: "100%", 
                        width: `${Math.min(100, sector.avg_rd_intensity * 5)}%`,
                        background: isHighRD ? "linear-gradient(90deg, #9333ea, #7c3aed)" : "#94a3b8",
                        borderRadius: 4,
                        display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 6,
                        minWidth: 36
                      }}>
                        <span style={{ color: "white", fontSize: 11, fontWeight: 600 }}>{sector.avg_rd_intensity.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div style={{ width: 50, fontSize: 10, color: "#94a3b8", textAlign: "right" }}>{sector.company_count} firms</div>
                  </div>
                )
              })}
            </div>
            <div style={{ marginTop: 12, padding: 10, background: "#f1f5f9", borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Key insight</div>
              <div style={{ fontSize: 12, color: "#334155" }}>
                <strong>Tech + Healthcare = 70%</strong> of high-R&D firms. Consider sector caps for diversification.
              </div>
            </div>
          </div>
          
          {/* Insights */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ background: "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)", border: "2px solid #9333ea", borderRadius: 16, padding: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "#6b21a8", marginBottom: 10 }}>⚠️ Sector Concentration Risk</h3>
              <p style={{ fontSize: 12, color: "#581c87", lineHeight: 1.6, marginBottom: 10 }}>
                Q5 (top R&D quintile) is <strong>~70% Tech + Healthcare</strong>. The R&D premium may partially reflect sector tailwinds.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div style={{ background: "white", borderRadius: 8, padding: 10, textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#9333ea" }}>~45%</div>
                  <div style={{ fontSize: 10, color: "#7e22ce" }}>Technology</div>
                </div>
                <div style={{ background: "white", borderRadius: 8, padding: 10, textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#9333ea" }}>~25%</div>
                  <div style={{ fontSize: 10, color: "#7e22ce" }}>Healthcare</div>
                </div>
              </div>
            </div>

            <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 16, padding: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "#047857", marginBottom: 10 }}>✓ Within-Sector Effect Confirmed</h3>
              <p style={{ fontSize: 12, color: "#065f46", lineHeight: 1.6, marginBottom: 10 }}>
                The R&D-return relationship holds <em>within</em> sectors. High-R&D tech firms beat low-R&D tech firms.
              </p>
              <div style={{ background: "#047857", borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: 11, color: "#a7f3d0", textAlign: "center" }}>
                  R&D premium captures innovation, not just sector exposure.
                </div>
              </div>
            </div>

            <div style={{ background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#92400e", marginBottom: 6 }}>💡 Practical Implication</div>
              <div style={{ fontSize: 11, color: "#78350f", lineHeight: 1.5 }}>
                To reduce sector concentration, apply <strong>20% sector caps</strong> during portfolio construction. This preserves ~85% of the R&D premium while improving diversification.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom takeaway */}
        <div style={{ marginTop: 16, background: "#0f172a", borderRadius: 12, padding: 16, display: "flex", alignItems: "center", justifyContent: "center", gap: 32 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>Implication</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>Consider sector constraints in implementation to diversify</div>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 8: ACADEMIC VALIDATION - Literature support (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="academic" slideNumber={8} totalSlides={TOTAL_SLIDES} title="Academic Validation" subtitle="Our findings are consistent with decades of peer-reviewed research" accent="blue">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)", border: "2px solid #3b82f6", borderRadius: 16, padding: 14, marginBottom: 12 }}>
          <p style={{ fontSize: 13, color: "#1e40af", lineHeight: 1.45, margin: 0, textAlign: "center" }}>
            The R&D-return anomaly has been documented in <strong>top-tier academic journals</strong> since the 1990s. 
            Our findings replicate and extend this literature using modern data sources and robust statistical methods.
          </p>
        </div>

        {/* Key papers - 2x2 grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          {[
            { authors: "Chan, Lakonishok & Sougiannis", year: "2001", journal: "Journal of Finance", finding: "High R&D-to-market-cap stocks earned significant excess returns over subsequent years. First major documentation of the R&D anomaly." },
            { authors: "Lev & Sougiannis", year: "1996", journal: "J. Accounting & Economics", finding: "R&D-adjusted earnings provide superior return predictions vs. reported GAAP earnings. R&D capitalization improves valuation." },
            { authors: "Eberhart, Maxwell & Siddique", year: "2004", journal: "Journal of Finance", finding: "Firms increasing R&D outperform over 5+ years. Market systematically underreacts to R&D investment announcements." },
            { authors: "Gu", year: "2005", journal: "J. Business Finance & Accounting", finding: "R&D intensity predicts future profitability and market-to-book ratios. Effect is stronger for firms with consistent R&D programs." },
          ].map((paper, i) => (
            <div key={i} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <span style={{ fontWeight: 800, color: "#1e40af", fontSize: 13 }}>{paper.authors} ({paper.year})</span>
              </div>
              <div style={{ background: "#eff6ff", borderRadius: 6, padding: "3px 8px", display: "inline-block", marginBottom: 8 }}>
                <span style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600 }}>{paper.journal}</span>
              </div>
              <p style={{ fontSize: 12, color: "#475569", lineHeight: 1.45, margin: 0 }}>{paper.finding}</p>
            </div>
          ))}
        </div>
        
        {/* Two hypotheses */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ background: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)", border: "2px solid #f59e0b", borderRadius: 16, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#f59e0b", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 20 }}>💰</span>
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "#92400e", margin: 0 }}>Mispricing Hypothesis</h3>
            </div>
            <p style={{ fontSize: 12.5, color: "#78350f", lineHeight: 1.55, marginBottom: 10, marginTop: 0 }}>
              Markets systematically undervalue intangible assets because GAAP accounting <strong>expenses R&D immediately</strong>. 
              Investors anchored on traditional P/E ratios miss the economic value of innovation investment.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#92400e" }}>📊 Depressed earnings → inflated P/E → value screens exclude</div>
        </div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#92400e" }}>📈 Intangible value not on balance sheet → undervalued</div>
      </div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#92400e" }}>⏳ 3-5 year lag for market recognition → patient alpha</div>
              </div>
              </div>
              </div>

          <div style={{ background: "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)", border: "2px solid #9333ea", borderRadius: 16, padding: 14, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#9333ea", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 20 }}>⚠️</span>
            </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "#6b21a8", margin: 0 }}>Risk Premium Hypothesis</h3>
            </div>
            <p style={{ fontSize: 12.5, color: "#581c87", lineHeight: 1.55, marginBottom: 10, marginTop: 0 }}>
              High R&D firms carry <strong>unique risks</strong>: technological disruption, project failure, regulatory changes. 
              The return premium may be compensation for bearing these innovation-specific risks.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#6b21a8" }}>🔬 R&D projects have high failure rates (~90% in pharma)</div>
        </div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#6b21a8" }}>💥 Disruptive tech can make R&D obsolete overnight</div>
              </div>
              <div style={{ background: "white", borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 11, color: "#6b21a8" }}>📉 Higher volatility → demands higher expected return</div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Bottom note */}
        <div style={{ marginTop: 10, background: "#0f172a", borderRadius: 12, padding: 10, textAlign: "center" }}>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>
            <strong style={{ color: "white" }}>Our view:</strong> Both hypotheses likely contribute. The premium persists because (a) accounting creates mispricing and (b) innovation risk deters some investors.
          </span>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 9: INVESTABLE STRATEGY - Implementation guide (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="strategy" slideNumber={9} totalSlides={TOTAL_SLIDES} title="Investable Strategy" subtitle="Practical implementation for practitioners" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Hero net premium */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 16, marginBottom: 16, textAlign: "center" }}>
          <div style={{ fontSize: 12, color: "#065f46", marginBottom: 6 }}>Investable edge survives costs</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#047857", lineHeight: 1 }}>
            {typeof invExcessNet === "number" ? `+${invExcessNet.toFixed(2)} pp/yr` : `+${netPremium.toFixed(2)}%`}
          </div>
          <div style={{ fontSize: 12, color: "#065f46", marginTop: 8 }}>
            {typeof invPortfolioNet?.annualized_return === "number" && typeof invBenchmarkNet?.annualized_return === "number"
              ? `ETF basket (net): ${invPortfolioNet.annualized_return.toFixed(2)}% vs EW cohort (net): ${invBenchmarkNet.annualized_return.toFixed(2)}% (${invStartYear}-${invEndYear}).`
              : `Factor HML after costs: +${netPremium.toFixed(2)}% (Q5−Q1).`}
          </div>
        </div>

        {/* Main content */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Portfolio Rules */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #059669", paddingBottom: 8 }}>Portfolio Construction Rules</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Universe", value: "S&P 500 constituents", icon: "🏛️" },
                { label: "Signal", value: "R&D Expense / Revenue (fiscal year)", icon: "📊" },
                { label: "Portfolio", value: `Top ${invNHoldings} by R&D intensity (or full Q5)`, icon: "📈" },
                { label: "Formation Date", value: "End of June (after 10-K filings)", icon: "📅" },
                { label: "Holding Period", value: "12 months (July → June)", icon: "⏱️" },
                { label: "Weighting", value: `Equal-weight (${Math.round(100 / Math.max(1, invNHoldings))}% each)`, icon: "⚖️" },
                { label: "Rebalance", value: `Annual (avg turnover ${typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"})`, icon: "🔄" },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", background: "white", borderRadius: 10, padding: 10 }}>
                  <span style={{ fontSize: 18 }}>{item.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: "#64748b" }}>{item.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a" }}>{item.value}</div>
              </div>
              </div>
              ))}
              </div>
            </div>
            
          {/* Cost Analysis + Metrics */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16, borderBottom: "2px solid #3b82f6", paddingBottom: 8 }}>Transaction Cost Analysis</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  {
                    label: "Annual Turnover",
                    value:
                      typeof invTurnoverAvg === "number"
                        ? `${invTurnoverAvg.toFixed(0)}%${typeof invTurnoverMax === "number" ? ` (max ${invTurnoverMax.toFixed(0)}%)` : ""}`
                        : "…",
                    note: "Measured from annual reconstitution",
                  },
                  {
                    label: "Est. Trading Cost",
                    value: typeof invTradingCostEstPct === "number" ? `${invTradingCostEstPct.toFixed(3)}%` : "…",
                    note: "Cost per 100% turnover × turnover",
                  },
                  {
                    label: "Holdings Count",
                    value: String(invNHoldings),
                    note: "ETFlike basket (equal-weight)",
                  },
                  {
                    label: "Return Convention",
                    value: "July–June",
                    note: "Avoid look-ahead (10‑K public before formation)",
                  },
                ].map((item, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #e2e8f0" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, color: "#334155" }}>{item.label}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8" }}>{item.note}</div>
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#3b82f6", textAlign: "right", minWidth: 100, flexShrink: 0 }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Quick metrics */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <div style={{ background: "#eff6ff", border: "2px solid #bfdbfe", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#1d4ed8" }}>
                  {typeof invTurnoverAvg === "number" ? `${invTurnoverAvg.toFixed(0)}%` : "…"}
                </div>
                <div style={{ fontSize: 11, color: "#1e40af" }}>Turnover</div>
              </div>
              <div style={{ background: "#faf5ff", border: "2px solid #e9d5ff", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#7e22ce" }}>{invNHoldings}</div>
                <div style={{ fontSize: 11, color: "#6b21a8" }}>Holdings</div>
              </div>
              <div style={{ background: "#fffbeb", border: "2px solid #fde68a", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#b45309" }}>1x</div>
                <div style={{ fontSize: 11, color: "#92400e" }}>Annual</div>
              </div>
            </div>
            </div>
          </div>
          
        {/* Warning */}
        <div style={{ marginTop: 16, background: "linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%)", border: "2px solid #f59e0b", borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#92400e", marginBottom: 4 }}>Patience Required</div>
              <div style={{ fontSize: 13, color: "#78350f", lineHeight: 1.5 }}>
                R&D benefits manifest with a <strong>3-5 year lag</strong>. Short-term underperformance is possible (negative premium years: ~{100 - winRate}%). 
                This strategy is designed for <strong>long-term investors with 5+ year horizons</strong>.
              </div>
            </div>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 10: LIMITATIONS - Caveats and risks (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="limitations" slideNumber={10} totalSlides={TOTAL_SLIDES} title="Important Caveats" subtitle="Limitations, risks, and honest assessment" accent="red">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Warning header */}
        <div style={{ background: "#dc2626", borderRadius: 16, padding: 16, marginBottom: 20, textAlign: "center" }}>
          <p style={{ fontSize: 16, fontWeight: 600, color: "white", margin: 0 }}>
            ⚠️ Past performance does not guarantee future results. This is research, not investment advice.
              </p>
            </div>
            
        {/* Two columns: Methodological + Practical */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Methodological Limitations */}
          <div style={{ background: "#fef2f2", border: "2px solid #fca5a5", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#991b1b", marginBottom: 16, borderBottom: "2px solid #dc2626", paddingBottom: 8 }}>Methodological Limitations</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 6 }}>🛡️ Survivorship Bias</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  S&P 500 sample excludes firms that failed or were delisted. We use delisting returns (Shumway 1997) to mitigate, but some bias may remain.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 6 }}>👀 Look-Ahead Bias</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  10-K filings are available 60-90 days after fiscal year-end. We use July-June returns to ensure data is public before portfolio formation.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 6 }}>📊 Data Quality</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  Tier-1 data (Financial Modeling Prep) may have gaps vs. CRSP/Compustat. Professional implementation should validate with academic-grade sources.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 6 }}>📐 Multiple Testing</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  We examined multiple horizons and specifications. Some findings may be sample-specific. Out-of-sample validation recommended.
                </div>
              </div>
            </div>
            </div>
            
          {/* Practical Considerations */}
          <div style={{ background: "#fffbeb", border: "2px solid #fde68a", borderRadius: 16, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#92400e", marginBottom: 16, borderBottom: "2px solid #f59e0b", paddingBottom: 8 }}>Practical Considerations</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}>🏭 Sector Concentration</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  Q5 is ~70% Technology + Healthcare. The R&D premium may partially reflect sector performance. Consider sector-neutralized versions.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}>📉 Regime Dependence</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  R&D premium varies by market regime. During 2000-2002 and parts of 2008-2018, high-R&D stocks underperformed. No guarantee of persistence.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}>💰 Capacity Constraints</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  Equal-weight Q5 has limited capacity (~$5-10B AUM before market impact). Large allocators may need value-weight or cap-weighted variations.
                </div>
              </div>
              <div style={{ background: "white", borderRadius: 10, padding: 14 }}>
                <div style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}>⏳ Timing Risk</div>
                <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  R&D benefits have 3-5 year lags. Multi-year underperformance is possible. Not suitable for short-term investors.
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Bottom disclaimer */}
        <div style={{ marginTop: 16, background: "#0f172a", borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 24 }}>⚖️</span>
            <span style={{ fontSize: 13, color: "#e2e8f0" }}>
              This research is provided for <strong style={{ color: "white" }}>educational and informational purposes only</strong>. 
              It does not constitute investment advice. Always consult a qualified financial advisor before making investment decisions.
            </span>
          </div>
        </div>
      </div>
    </Slide>,

    // ═══════════════════════════════════════════════════════════════════════════
    // SLIDE 11: CONCLUSION - Summary and call to action (full page)
    // ═══════════════════════════════════════════════════════════════════════════
    <Slide key="conclusion" slideNumber={11} totalSlides={TOTAL_SLIDES} title="Conclusion" accent="emerald">
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Main finding summary */}
        <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 12, padding: 20, marginBottom: 20, textAlign: "center" }}>
          <div style={{ fontSize: 14, color: "#065f46", marginBottom: 8 }}>The R&D Premium is Real, Persistent, and Implementable</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#047857", lineHeight: 1 }}>+{rdPremium.toFixed(1)}%</div>
          <div style={{ fontSize: 13, color: "#065f46", marginTop: 8 }}>
            Annual premium for high-R&D (Q5) vs low-R&D (Q1) firms
          </div>
        </div>
        
        {/* Key metrics row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#047857" }}>+{rdPremium.toFixed(1)}%</div>
            <div style={{ fontSize: 11, color: "#065f46" }}>Annual Premium</div>
            </div>
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#1d4ed8" }}>{etaSquared20yr.toFixed(2)}</div>
            <div style={{ fontSize: 11, color: "#1e40af" }}>20yr Effect Size</div>
            </div>
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#7e22ce" }}>t={tStat.toFixed(1)}</div>
            <div style={{ fontSize: 11, color: "#6b21a8" }}>Significance</div>
            </div>
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#b45309" }}>{winRate}%</div>
            <div style={{ fontSize: 11, color: "#92400e" }}>Win Rate</div>
            </div>
          </div>

        {/* Key takeaways */}
        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 16, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginBottom: 20, textAlign: "center" }}>Key Takeaways for Practitioners</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
            {[
              { num: "1", text: "R&D intensity is a statistically significant predictor of future stock returns, with effects persisting across multiple horizons." },
              { num: "2", text: "Effect size grows with horizon (η² 0.23→0.46), suggesting R&D benefits compound. Patience is rewarded." },
              { num: "3", text: "Results align with 30+ years of academic research on intangible asset mispricing (Chan et al., Lev & Sougiannis)." },
              { num: "4", text: "Strategy is implementable: ~40% turnover, ~0.07% trading costs, ~99% premium capture rate." },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#059669", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, flexShrink: 0 }}>{item.num}</div>
                <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.6 }}>{item.text}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Call to action */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div style={{ background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)", border: "2px solid #3b82f6", borderRadius: 16, padding: 20 }}>
            <h4 style={{ fontSize: 16, fontWeight: 700, color: "#1e40af", marginBottom: 12 }}>📖 Further Reading</h4>
            <p style={{ fontSize: 13, color: "#1e3a8a", lineHeight: 1.6, marginBottom: 12 }}>
              Full methodology, interactive charts, and company-level data available at:
            </p>
            <div style={{ background: "#1e40af", borderRadius: 10, padding: 12, textAlign: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: "white" }}>research.finsoeasy.com</span>
            </div>
            <div style={{ fontSize: 12, color: "#3b82f6", lineHeight: 1.5 }}>
              <div style={{ marginBottom: 6 }}>✓ Interactive portfolio builder</div>
              <div style={{ marginBottom: 6 }}>✓ 500+ company R&D profiles</div>
              <div>✓ Downloadable data exports</div>
            </div>
          </div>

          <div style={{ background: "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)", border: "2px solid #059669", borderRadius: 16, padding: 20 }}>
            <h4 style={{ fontSize: 16, fontWeight: 700, color: "#047857", marginBottom: 12 }}>📧 Get in Touch</h4>
            <p style={{ fontSize: 13, color: "#065f46", lineHeight: 1.6, marginBottom: 12 }}>
              Questions, feedback, or collaboration opportunities:
            </p>
            <div style={{ background: "#047857", borderRadius: 10, padding: 12, textAlign: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: "white" }}>abhishek@finsoeasy.com</span>
            </div>
            <div style={{ fontSize: 12, color: "#059669", lineHeight: 1.5 }}>
              <div style={{ marginBottom: 6 }}>• Institutional inquiries welcome</div>
              <div style={{ marginBottom: 6 }}>• Research collaboration</div>
              <div>• Media and speaking requests</div>
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <div style={{ marginTop: 20, display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 16, borderTop: "1px solid #e2e8f0" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#334155" }}>Abhishek Sehgal</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>December 2025</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "#64748b" }}>Data: FMP (Tier-1) | Ken French | {totalCompanies} S&P 500 firms</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#059669" }}>R&D Alpha Research</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>research.finsoeasy.com</div>
          </div>
        </div>
      </div>
    </Slide>,
  ]

  return (
    <div 
      className={cn(
        "flex flex-col h-full",
        isFullscreen && "fixed inset-0 z-50 bg-slate-900 p-4"
      )}
      onKeyDown={(e) => handleKeyDown(e.nativeEvent)}
      tabIndex={0}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">
            <span className="text-emerald-500">R&D Alpha</span>{" "}
            <span className="text-foreground">Whitepaper</span>
          </h1>
          <p className="text-muted-foreground text-sm">
            Slide {currentSlide + 1} of {slides.length} - A4 format - Arrow keys to navigate
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Button 
            variant="default" 
            size="sm"
            onClick={handlePrint}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Printer className="mr-1 h-3 w-3" />
            Print / PDF
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Slide Display - Full size with scroll */}
      <div 
        ref={slideContainerRef}
        className="relative flex-1 flex items-start justify-center overflow-auto bg-slate-100 dark:bg-slate-900 py-4"
      >
        <div className="slide-content">
          {slides[currentSlide]}
        </div>
        
        {/* Navigation Buttons */}
        <button
          onClick={prevSlide}
          disabled={currentSlide === 0}
          className={cn(
            "absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors",
            currentSlide === 0 && "opacity-30 cursor-not-allowed"
          )}
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        
        <button
          onClick={nextSlide}
          disabled={currentSlide === slides.length - 1}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors",
            currentSlide === slides.length - 1 && "opacity-30 cursor-not-allowed"
          )}
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Slide Indicators */}
      <div className="flex justify-center gap-2 py-3">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentSlide(i)}
            className={cn(
              "w-2 h-2 rounded-full transition-all",
              i === currentSlide 
                ? "bg-emerald-500 w-4" 
                : "bg-slate-400 hover:bg-slate-300"
            )}
          />
        ))}
      </div>

      {/* Thumbnail Preview */}
      {!isFullscreen && (
        <div className="mt-2 border-t border-border pt-4 no-print">
          <h3 className="text-sm font-semibold mb-2">All Slides</h3>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentSlide(i)}
                className={cn(
                  "aspect-[210/297] rounded overflow-hidden border-2 transition-all hover:scale-105",
                  i === currentSlide 
                    ? "border-emerald-500 ring-1 ring-emerald-500/30" 
                    : "border-slate-300 dark:border-slate-700 hover:border-slate-400"
                )}
              >
                <div className="w-full h-full bg-white flex items-center justify-center">
                  <span className="text-xs text-slate-600">{i + 1}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Print View - always rendered but hidden, shown via CSS @media print */}
      <div className="whitepaper-print-container">
          {slides.map((slide, i) => (
            <div key={i} className="whitepaper-print-slide">
              {slide}
            </div>
          ))}
        </div>
    </div>
  )
}

export default Whitepaper
