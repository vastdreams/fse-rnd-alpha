import { useState, useMemo, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { portfolioApi } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  Cell,
  PieChart,
  Pie,
  LineChart,
  Line,
  Area,
  ComposedChart,
  ReferenceLine,
} from "recharts"
import { TrendingUp, TrendingDown, Target, BarChart3, Zap, AlertTriangle, CheckCircle2, Eye, FlaskConical, Scale, BookOpen, ChevronDown, ChevronUp, Download } from "lucide-react"
import { exportToCSV } from "@/lib/export"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Link } from "react-router-dom"
import { SafeChart } from "@/components/SafeChart"

// Colors that work well in both light and dark modes
const SECTOR_COLORS = [
  "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
  "#db2777", "#0891b2", "#65a30d", "#ea580c", "#4f46e5", "#0d9488"
]

// Chart color scheme - distinct colors for each data type
const CHART_COLORS = {
  historical: "#0ea5e9",      // Sky blue - historical data
  actuals: "#22c55e",         // Green - actual results after selection
  forecast: "#a855f7",        // Purple - forecasted data
  benchmark: "#64748b",       // Slate - benchmark line
  confidenceBand: "#a855f7",  // Purple - forecast confidence band
}

const CURRENT_YEAR = new Date().getFullYear()

export function Portfolio() {
  const [asOfYear, setAsOfYear] = useState(2023)
  const [nHoldings, setNHoldings] = useState(20)
  const [selectedSector, setSelectedSector] = useState<string | undefined>()
  const [chartsReady, setChartsReady] = useState(false)
  const [activeTab, setActiveTab] = useState("holdings")
  
  // Delay chart rendering to ensure container dimensions are calculated
  // Reset and delay when tab changes to prevent -1 dimension errors
  // Using requestAnimationFrame + timeout for reliable layout calculation
  useEffect(() => {
    setChartsReady(false)
    // First wait for browser to paint, then wait additional time for layout
    const rafId = requestAnimationFrame(() => {
      const timer = setTimeout(() => setChartsReady(true), 250)
      // Store timer cleanup in ref-like pattern
      return () => clearTimeout(timer)
    })
    return () => cancelAnimationFrame(rafId)
  }, [activeTab])

  // Dynamic holdings based on selected year
  // Use "rd_alpha" method which uses July-June returns per Fama-French convention
  const { data: holdings, isLoading: loadingHoldings } = useQuery({
    queryKey: ["etfHoldings", nHoldings, selectedSector, asOfYear],
    queryFn: () => portfolioApi.getETFHoldings(nHoldings, "rd_alpha", selectedSector, asOfYear),
  })

  // Forecast vs Actual for selected year
  const { data: forecastVsActual, isLoading: loadingForecast } = useQuery({
    queryKey: ["forecastVsActual", asOfYear, nHoldings, selectedSector],
    queryFn: () => portfolioApi.getForecastVsActual(asOfYear, nHoldings, "rd_alpha", selectedSector),
  })

  // Backtest from 2005 to the selected year (or last complete year for "Current ETF")
  // Starting in 2000-2002 would include dot-com bubble burst which distorts results
  // IMPORTANT: Use asOfYear as the end date so metrics CHANGE with year selection
  const backtestStart = 2005
  // Cap end year to CURRENT_YEAR - 1 (incomplete data for current year)
  const backtestEnd = Math.min(asOfYear, CURRENT_YEAR - 1)
  const { data: backtest, isLoading: loadingBacktest } = useQuery({
    queryKey: ["backtest", backtestStart, backtestEnd, nHoldings, selectedSector],
    queryFn: () => portfolioApi.backtest(backtestStart, backtestEnd, nHoldings, "rd_alpha", selectedSector),
  })

  const { data: sectors } = useQuery({
    queryKey: ["portfolioSectors"],
    queryFn: portfolioApi.getSectors,
  })

  const { data: sectorAllocation } = useQuery({
    queryKey: ["sectorAllocation", nHoldings, asOfYear],
    queryFn: () => portfolioApi.getSectorAllocation(nHoldings, "rd_alpha", asOfYear),
  })

  // New R&D Alpha queries
  const { data: methodology } = useQuery({
    queryKey: ["methodology"],
    queryFn: portfolioApi.getMethodology,
  })

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

  const [showMethodologyDetails, setShowMethodologyDetails] = useState(false)

  const isLoading = loadingHoldings || loadingBacktest || loadingForecast

  const formatPercent = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "..."
    return `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`
  }

  // Chart-safe series (explicitly use S&P 500 fields for benchmark/alpha displays)
  const yearlyDataForCharts = useMemo(() => {
    const rows = backtest?.yearly_data || []
    return rows.map((d) => ({
      ...d,
      sp500_return: typeof d.sp500_return === "number" ? d.sp500_return : null,
      excess_vs_sp500: typeof d.excess_vs_sp500 === "number" ? d.excess_vs_sp500 : null,
    }))
  }, [backtest?.yearly_data])

  const cumulativeExcessVsSp500 = useMemo(() => {
    const port = backtest?.portfolio_performance?.total_return
    const sp = backtest?.sp500_performance?.total_return
    if (typeof port !== "number" || typeof sp !== "number") return null
    return port - sp
  }, [backtest?.portfolio_performance?.total_return, backtest?.sp500_performance?.total_return])

  // Export holdings to CSV
  const handleExportHoldings = () => {
    if (!holdings || holdings.length === 0) return
    
    exportToCSV(
      holdings.map(h => ({
        rank: h.rank,
        symbol: h.symbol,
        company_name: h.company_name || "",
        sector: h.sector || "",
        rd_intensity: h.rd_intensity?.toFixed(2) || "",
        rd_alpha_score: h.rd_alpha_score?.toFixed(3) || "",
        momentum_score: h.momentum_score?.toFixed(3) || "",
        quality_score: h.quality_score?.toFixed(3) || "",
        weight: (h.weight * 100).toFixed(2) || "",
      })),
      `rd_etf_holdings_${asOfYear}_top${nHoldings}.csv`,
      [
        { key: "rank", header: "Rank" },
        { key: "symbol", header: "Symbol" },
        { key: "company_name", header: "Company Name" },
        { key: "sector", header: "Sector" },
        { key: "rd_intensity", header: "R&D Intensity (%)" },
        { key: "rd_alpha_score", header: "R&D Alpha Score" },
        { key: "momentum_score", header: "Momentum Score" },
        { key: "quality_score", header: "Quality Score" },
        { key: "weight", header: "Portfolio Weight (%)" },
      ]
    )
  }

  // Build year options
  const yearOptions = useMemo(() => {
    const years = []
    for (let y = 2000; y <= CURRENT_YEAR; y++) {
      years.push(y)
    }
    return years.reverse()
  }, [])

  // Build line chart data with SEPARATE lines:
  // - Historical: what we knew up to selected year
  // - Actuals: what ACTUALLY happened after selected year (through now)
  // - Forecast: what we PREDICTED would happen from selected year (based on R&D research)
  // The forecast overlays actuals so you can COMPARE prediction vs reality!
  const performanceLineData = useMemo(() => {
    if (!backtest?.yearly_data || backtest.yearly_data.length === 0) return []
    
    const lastActualYear = CURRENT_YEAR - 1 // 2024 is the last year with complete data
    // Use canonical 5-year R&D premium from research (7.11% verified)
    const forecastPremium = forecastVsActual?.forecast_premium ?? 7.1
    
    // Calculate cumulative values starting at 100
    let portfolioCumulative = 100
    let benchmarkCumulative = 100
    
    // First pass: build historical and actuals
    const chartData: Array<{
      year: number
      date: string
      historical: number | null      // Historical line (up to selected year)
      actuals: number | null         // Actuals line (what actually happened after selection)
      forecast: number | null        // Forecast line (what we predicted from selected year)
      benchmark: number
      portfolioHigh: number | null
      portfolioLow: number | null
    }> = []
    
    // Track the portfolio value at the selected year for forecast starting point
    let portfolioAtSelectionYear = 100
    let benchmarkAtSelectionYear = 100
    
    // Get start year for the baseline point
    const startYear = backtest.yearly_data.length > 0 ? backtest.yearly_data[0].year : 2000
    
    // Add baseline point at start year with both at exactly $100
    // This ensures both lines start at the same point for fair comparison
    chartData.push({
      year: startYear - 1,
      date: `${startYear - 1}`,
      historical: 100,
      actuals: null,
      forecast: null,
      benchmark: 100,
      portfolioHigh: null,
      portfolioLow: null,
    })
    
    // Process historical data through all available years
    // Use S&P 500 return for benchmark when available, fallback to cohort EW benchmark
    backtest.yearly_data.forEach((d) => {
      portfolioCumulative *= (1 + (d.portfolio_return || 0) / 100)
      const benchmarkReturn = typeof d.sp500_return === "number" ? d.sp500_return : 0
      benchmarkCumulative *= (1 + benchmarkReturn / 100)
      
      // Track the value at selection year
      if (d.year === asOfYear) {
        portfolioAtSelectionYear = portfolioCumulative
        benchmarkAtSelectionYear = benchmarkCumulative
      }
      
      const isHistorical = d.year <= asOfYear
      const isActual = d.year > asOfYear && d.year <= lastActualYear
      
      chartData.push({
        year: d.year,
        date: `${d.year}`,
        historical: isHistorical ? parseFloat(portfolioCumulative.toFixed(2)) : null,
        actuals: isActual ? parseFloat(portfolioCumulative.toFixed(2)) : null,
        forecast: null,
        benchmark: parseFloat(benchmarkCumulative.toFixed(2)),
        portfolioHigh: null,
        portfolioLow: null,
      })
    })
    
    // Connect actuals to historical at the transition point
    const transitionIdx = chartData.findIndex(d => d.year === asOfYear)
    if (transitionIdx >= 0 && asOfYear < lastActualYear) {
      chartData[transitionIdx].actuals = chartData[transitionIdx].historical
    }
    
    // Now add FORECAST starting from selected year
    // This is what we PREDICTED would happen based on R&D research
    // Forecast starts at the selected year and goes forward 10 years
    let forecastPortfolio = portfolioAtSelectionYear
    let forecastBenchmark = benchmarkAtSelectionYear
    
    // Add forecast at the starting point (selected year)
    if (transitionIdx >= 0) {
      chartData[transitionIdx].forecast = parseFloat(forecastPortfolio.toFixed(2))
    }
    
    // Generate forecast for years after selected year
    for (let i = 1; i <= 10; i++) {
      const forecastYear = asOfYear + i
      const expectedReturn = (8 + forecastPremium) / 100 // Base market + R&D premium
      const benchmarkReturn = 0.08 // 8% expected market return
      
      forecastPortfolio *= (1 + expectedReturn)
      forecastBenchmark *= (1 + benchmarkReturn)
      
      // Calculate confidence interval that widens over time
      const confidenceSpread = 0.08 + (i * 0.015) // Starts at 8%, increases 1.5% per year
      
      // Find if this year already exists in chartData (it will for actuals)
      const existingIdx = chartData.findIndex(d => d.year === forecastYear)
      
      if (existingIdx >= 0) {
        // Year exists (it's in the actuals period) - add forecast to it
        chartData[existingIdx].forecast = parseFloat(forecastPortfolio.toFixed(2))
        chartData[existingIdx].portfolioHigh = parseFloat((forecastPortfolio * (1 + confidenceSpread)).toFixed(2))
        chartData[existingIdx].portfolioLow = parseFloat((forecastPortfolio * (1 - confidenceSpread)).toFixed(2))
      } else {
        // Year is in the future - add new data point
        chartData.push({
          year: forecastYear,
          date: `${forecastYear}`,
          historical: null,
          actuals: null,
          forecast: parseFloat(forecastPortfolio.toFixed(2)),
          benchmark: parseFloat(forecastBenchmark.toFixed(2)),
          portfolioHigh: parseFloat((forecastPortfolio * (1 + confidenceSpread)).toFixed(2)),
          portfolioLow: parseFloat((forecastPortfolio * (1 - confidenceSpread)).toFixed(2)),
        })
      }
    }
    
    // Sort by year to ensure correct order
    chartData.sort((a, b) => a.year - b.year)
    
    return chartData
  }, [backtest, asOfYear, forecastVsActual])

  // Calculate forecast accuracy
  const forecastAccuracy = useMemo(() => {
    if (!forecastVsActual?.is_historical || forecastVsActual.actual_return === null) return null
    const error = Math.abs(forecastVsActual.forecast_error ?? 0)
    if (error < 5) return { status: "excellent", color: "emerald" }
    if (error < 10) return { status: "good", color: "yellow" }
    return { status: "off", color: "red" }
  }, [forecastVsActual])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <div className="text-lg text-muted-foreground">Building your R&D Alpha portfolio...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header with Premium Feel */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-500/10 via-card to-card border border-purple-500/20 p-8">
        <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
        <div className="relative z-10">
          <div className="flex items-start justify-between flex-wrap gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Zap className="h-8 w-8 text-purple-500" />
                <h1 className="text-4xl font-bold">
                  <span className="text-purple-500">R&D</span>{" "}
                  <span className="text-foreground">Alpha ETF</span>
                </h1>
              </div>
              <p className="text-lg text-muted-foreground max-w-xl">
                Dynamically constructed portfolio of Top {nHoldings} R&D-intensive companies 
                as of <span className="text-purple-500 font-semibold">{asOfYear}</span>
              </p>
              <p className="text-xs text-muted-foreground mt-2 flex items-center gap-2">
                <FlaskConical className="h-3 w-3" />
                <span><strong>Methodology:</strong> July-June returns (Fama-French convention) • Delisting-adjusted • R&D Alpha scoring</span>
              </p>
            </div>
            
            {/* Controls */}
            <TooltipProvider delayDuration={300}>
              <div className="flex flex-wrap gap-3">
                {/* Current ETF Button */}
                <Button
                  onClick={() => setAsOfYear(CURRENT_YEAR)}
                  variant={asOfYear === CURRENT_YEAR ? "default" : "outline"}
                  className={`font-medium ${
                    asOfYear === CURRENT_YEAR
                      ? "bg-purple-600 hover:bg-purple-700 text-white shadow-md"
                      : "border-purple-500/30 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/20"
                  }`}
                >
                  <Zap className="h-4 w-4 mr-1.5" />
                  Current ETF
                </Button>

                {/* Year Selector for Backtesting */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex flex-col items-center gap-1">
                      <Select value={asOfYear.toString()} onValueChange={(v) => setAsOfYear(parseInt(v))}>
                        <SelectTrigger className="w-36 bg-white dark:bg-slate-800 border-border shadow-sm">
                          <SelectValue placeholder="As of Year" />
                        </SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          {yearOptions.map((y) => (
                            <SelectItem key={y} value={y.toString()}>
                              {y} {y === CURRENT_YEAR ? "(Preliminary)" : ""}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <span className="text-xs text-muted-foreground">Check Backtesting</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p className="text-sm">
                      <strong>Backtest Year:</strong> Select a historical year to see what the portfolio would have held 
                      and compare our R&D-based forecast vs actual returns.
                    </p>
                  </TooltipContent>
                </Tooltip>
                
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Select value={nHoldings.toString()} onValueChange={(v) => setNHoldings(parseInt(v))}>
                        <SelectTrigger className="w-28 bg-white dark:bg-slate-800 border-border shadow-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          <SelectItem value="10">Top 10</SelectItem>
                          <SelectItem value="20">Top 20</SelectItem>
                          <SelectItem value="50">Top 50</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p className="text-sm">
                      <strong>Holdings:</strong> Number of highest R&D-intensity companies to include in the portfolio.
                    </p>
                  </TooltipContent>
                </Tooltip>
                
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Select value={selectedSector || "all"} onValueChange={(v) => setSelectedSector(v === "all" ? undefined : v)}>
                        <SelectTrigger className="w-40 bg-white dark:bg-slate-800 border-border shadow-sm">
                          <SelectValue placeholder="All Sectors" />
                        </SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-800">
                          <SelectItem value="all">All Sectors</SelectItem>
                          {(sectors || []).map((s) => (
                            <SelectItem key={s.sector} value={s.sector}>{s.sector}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p className="text-sm">
                      <strong>Sector Filter:</strong> Filter holdings by industry sector.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>
          </div>
        </div>
      </div>

      {/* KEY METRICS - Annualized Returns Front and Center */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20">
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Annualized Return</p>
            <p className="text-3xl font-bold text-emerald-500">
              {backtest?.portfolio_performance?.annualized_return 
                ? `+${backtest.portfolio_performance.annualized_return.toFixed(1)}%`
                : "..."}
            </p>
            <p className="text-xs text-muted-foreground">{backtestStart}-{backtestEnd} ({backtestEnd - backtestStart} years)</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">S&P 500 (Annualized)</p>
            <p className="text-3xl font-bold text-blue-500">
              {backtest?.sp500_performance?.annualized_return 
                ? `+${backtest.sp500_performance.annualized_return.toFixed(1)}%`
                : "..."}
            </p>
            <p className="text-xs text-muted-foreground">Market benchmark</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Excess Return (Annual)</p>
            <p className="text-3xl font-bold text-amber-500">
              {backtest?.excess_vs_sp500 !== undefined && backtest?.excess_vs_sp500 !== null
                ? `${backtest.excess_vs_sp500 >= 0 ? "+" : ""}${backtest.excess_vs_sp500.toFixed(1)}%`
                : "..."}
            </p>
            <p className="text-xs text-muted-foreground">R&D premium vs S&P 500</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">$100 Becomes</p>
            <p className="text-3xl font-bold text-purple-500">
              {backtest?.portfolio_performance?.total_return 
                ? `$${((100 * (1 + backtest.portfolio_performance.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0})}`
                : "..."}
            </p>
            <p className="text-xs text-muted-foreground">
              vs S&P 500: {backtest?.sp500_performance?.total_return 
                ? `$${((100 * (1 + backtest.sp500_performance.total_return / 100))).toLocaleString(undefined, {maximumFractionDigits: 0})}`
                : "..."}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* METHODOLOGY NOTE - Important disclaimer about backtest methodology */}
      <Card className="border border-amber-500/30 bg-gradient-to-br from-amber-500/5 to-card">
        <CardContent className="pt-4 pb-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
            <div className="text-sm text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Backtest Methodology Note</p>
              <p>
                Historical performance uses <strong>point-in-time S&P 500 constituents</strong> to avoid 
                survivorship bias. Only companies that were in the index at the time of selection are included.
                Past performance does not guarantee future results. The R&D premium may be smaller going forward
                as the factor becomes more widely known.
              </p>
              <p className="text-xs">
                Returns use July-June fiscal year convention per Fama-French methodology. 
                {asOfYear < CURRENT_YEAR - 1 && (
                  <span className="text-amber-600 ml-1">
                    Viewing historical ({asOfYear}) — metrics reflect performance through that year only.
                  </span>
                )}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* HOW TO USE THIS TOOL - Investment Instructions */}
      <Card className="border-2 border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5 text-purple-500" />
            How to Use This Tool for Investing
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-purple-500 text-white text-xs flex items-center justify-center">1</span>
                Build Your Portfolio
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1.5 ml-8">
                <li>• Select "Current ETF" to see today's recommended holdings</li>
                <li>• Choose Top 20 holdings for diversification, Top 10 for concentration</li>
                <li>• Equal-weight each position (e.g., 5% each for Top 20)</li>
                <li>• Download holdings via the "Holdings" tab export button</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-purple-500 text-white text-xs flex items-center justify-center">2</span>
                Rebalancing Schedule
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1.5 ml-8">
                <li>• <strong>Annually in July</strong> (Fama-French convention)</li>
                <li>• Wait for prior fiscal-year 10-K filings (typically May-June)</li>
                <li>• Re-rank by R&D intensity and update holdings</li>
                <li>• Expected turnover: ~40% per year</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-purple-500 text-white text-xs flex items-center justify-center">3</span>
                Expected Performance
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1.5 ml-8">
                <li>• Historical R&D premium: <strong>+5-8%</strong> over S&P 500 annually</li>
                <li>• Higher volatility than benchmark (expect ~18-20% annual vol)</li>
                <li>• Sector concentration in Tech & Healthcare</li>
                <li>• See <Link to="/papers/main" className="text-purple-500 hover:underline">Main Paper</Link> for full research</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-amber-500 text-white text-xs flex items-center justify-center">!</span>
                Important Considerations
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1.5 ml-8">
                <li>• <strong>Not investment advice</strong> - research tool only</li>
                <li>• Transaction costs reduce net returns ~0.07% annually</li>
                <li>• Tax implications vary by account type</li>
                <li>• Consider your risk tolerance and time horizon</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Year Selection Explanation & 2025 Disclaimer */}
      {asOfYear === CURRENT_YEAR && (
        <Card className="bg-amber-500/10 border-amber-500/30">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  {CURRENT_YEAR} Data is Preliminary
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  U.S. public companies have varying fiscal year end dates. 
                  {CURRENT_YEAR} financial data may be incomplete as many companies have not yet filed their annual reports. 
                  For rigorous analysis, we recommend using {CURRENT_YEAR - 1} or earlier data.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Research Integration Card */}
      <Card className="bg-blue-500/5 border-blue-500/20">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-start gap-3">
            <FlaskConical className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                Research-Backed Construction
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                This portfolio implements the findings from our <Link to="/papers/main" className="text-blue-500 hover:underline font-medium">R&D Alpha research paper</Link>: 
                <strong> R&D intensity</strong> (R&D/Revenue) predicts future stock returns with a statistically significant premium of 
                <strong> +7.5% annually</strong> (t-stat 2.78). Holdings are selected using the July-June return convention 
                to avoid look-ahead bias, with delisting adjustments for survivorship correction.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Hero: Line Chart with Forecast Cone - Like Analyst Price Target */}
      <Card className="bg-gradient-to-br from-card to-muted/30 border-border">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-3 flex-wrap">
                Portfolio Performance
                <div className="flex items-center gap-2 text-sm font-normal flex-wrap">
                  <span className="px-2 py-1 bg-cyan-500/20 rounded text-cyan-600 dark:text-cyan-300 border border-cyan-500/30">
                    Historical ({backtestStart}-{asOfYear})
                  </span>
                  {asOfYear < CURRENT_YEAR - 1 && (
                    <span className="px-2 py-1 bg-emerald-500/20 rounded text-emerald-600 dark:text-emerald-300 border border-emerald-500/30">
                      Actuals ({asOfYear + 1}-{CURRENT_YEAR - 1})
                    </span>
                  )}
                  <span className="px-2 py-1 bg-purple-500/20 rounded text-purple-600 dark:text-purple-300 border border-purple-500/30">
                    10yr Forecast
                  </span>
                </div>
              </CardTitle>
              <CardDescription className="text-base mt-1">
                Growth of $100 invested in {backtestStart} - R&D Portfolio vs S&P 500 benchmark
              </CardDescription>
            </div>
            
            {forecastAccuracy && forecastVsActual?.is_historical && (
              <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                forecastAccuracy.status === "excellent" ? "bg-emerald-500/10 border border-emerald-500/30" :
                forecastAccuracy.status === "good" ? "bg-yellow-500/10 border border-yellow-500/30" :
                "bg-red-500/10 border border-red-500/30"
              }`}>
                {forecastAccuracy.status === "excellent" ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                ) : forecastAccuracy.status === "good" ? (
                  <Target className="h-5 w-5 text-yellow-400" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-red-400" />
                )}
                <span className={`text-sm font-medium ${
                  forecastAccuracy.status === "excellent" ? "text-emerald-400" :
                  forecastAccuracy.status === "good" ? "text-yellow-400" : "text-red-400"
                }`}>
                  Forecast {forecastAccuracy.status === "excellent" ? "Accurate" : forecastAccuracy.status === "good" ? "Close" : "Divergent"}
                </span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Main Line Chart with Forecast Cone */}
          <div style={{ height: 384, minHeight: 384 }} className="relative">
            {!chartsReady || performanceLineData.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-muted-foreground">
                  <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto mb-2" />
                  <p>Loading performance data...</p>
                </div>
              </div>
            ) : (
            <>
              {/* Marker for the selection year when viewing historical data */}
              {asOfYear < CURRENT_YEAR - 1 && (
                <div className="absolute top-0 bottom-16 w-px bg-sky-500/70 z-10" style={{
                  left: `${((performanceLineData.filter(d => d.historical !== null).length - 0.5) / performanceLineData.length) * 100}%`
                }}>
                  <div className="absolute top-5 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-sky-100 dark:bg-sky-500/20 text-xs text-sky-700 dark:text-sky-400 rounded whitespace-nowrap border border-sky-300 dark:border-sky-500/30">
                    Selected: {asOfYear}
                  </div>
                </div>
              )}
              {/* Marker for "Now" - end of actuals */}
              {asOfYear < CURRENT_YEAR - 1 && (
                <div className="absolute top-0 bottom-16 w-px bg-green-500/70 z-10" style={{
                  left: `${((performanceLineData.filter(d => d.historical !== null || d.actuals !== null).length - 0.5) / performanceLineData.length) * 100}%`
                }}>
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-green-100 dark:bg-green-500/20 text-xs text-green-700 dark:text-green-400 rounded whitespace-nowrap border border-green-300 dark:border-green-500/30">
                    Now ({CURRENT_YEAR - 1})
                  </div>
                </div>
              )}
              
              <SafeChart height={350} debounce={50}>
              <ComposedChart data={performanceLineData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <defs>
                  <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS.forecast} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={CHART_COLORS.forecast} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  className="text-muted-foreground"
                  tick={{ className: 'fill-muted-foreground', fontSize: 12 }}
                  axisLine={{ className: 'stroke-border' }}
                  tickLine={{ className: 'stroke-border' }}
                />
                <YAxis 
                  className="text-muted-foreground"
                  tickFormatter={(v) => `$${v.toLocaleString()}`}
                  tick={{ className: 'fill-muted-foreground', fontSize: 12 }}
                  axisLine={{ className: 'stroke-border' }}
                  tickLine={{ className: 'stroke-border' }}
                  domain={['dataMin - 10', 'dataMax + 20']}
                />
                <RechartsTooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null
                    const data = payload[0]?.payload
                    
                    // Determine which type of data point this is
                    const isForecast = data?.forecast !== null && data?.forecast !== undefined
                    const isActual = data?.actuals !== null && data?.actuals !== undefined
                    
                    // Get the portfolio value from the appropriate field
                    const portfolioValue = data?.forecast ?? data?.actuals ?? data?.historical ?? 0
                    
                    const dataType = isForecast ? "Forecast" : isActual ? "Actuals" : "Historical"
                    const dotColor = isForecast ? CHART_COLORS.forecast : isActual ? CHART_COLORS.actuals : CHART_COLORS.historical
                    const bgClass = isForecast ? "bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300" : 
                                   isActual ? "bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-300" : 
                                   "bg-sky-100 dark:bg-sky-500/20 text-sky-700 dark:text-sky-300"
                    return (
                      <div className="bg-popover border border-border rounded-lg p-4 shadow-xl">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-foreground font-medium">{label}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bgClass}`}>
                            {dataType}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mb-1">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: dotColor }} />
                          <span className="font-bold text-foreground">${portfolioValue?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                          <span className="text-muted-foreground text-sm">R&D ETF</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS.benchmark }} />
                          <span className="font-bold text-foreground">${data?.benchmark?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                          <span className="text-muted-foreground text-sm">S&P 500</span>
                        </div>
                        {isForecast && data?.portfolioLow && data?.portfolioHigh && (
                          <div className="mt-2 pt-2 border-t border-border">
                            <div className="text-muted-foreground text-xs flex items-center gap-1">
                              <Eye className="h-3 w-3" />
                              Confidence Range: ${data.portfolioLow.toLocaleString()} - ${data.portfolioHigh.toLocaleString()}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  }}
                />
                
                {/* Forecast confidence band */}
                <Area
                  type="monotone"
                  dataKey="portfolioHigh"
                  stroke="none"
                  fill="url(#forecastGradient)"
                  fillOpacity={1}
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="portfolioLow"
                  stroke="none"
                  fill="hsl(var(--background))"
                  fillOpacity={1}
                  connectNulls={false}
                />
                
                {/* Benchmark line - dashed, neutral gray */}
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  name="S&P 500 Benchmark ($)"
                  stroke={CHART_COLORS.benchmark}
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={false}
                  connectNulls={false}
                  activeDot={{ r: 6, fill: CHART_COLORS.benchmark, stroke: '#fff', strokeWidth: 2 }}
                />
                
                {/* Historical line - sky blue, solid */}
                <Line
                  type="monotone"
                  dataKey="historical"
                  name="R&D Portfolio Historical ($)"
                  stroke={CHART_COLORS.historical}
                  strokeWidth={3}
                  dot={false}
                  connectNulls={false}
                  activeDot={{ r: 8, fill: CHART_COLORS.historical, stroke: '#fff', strokeWidth: 2 }}
                />
                
                {/* Actuals line - green, solid - SEPARATE LINE showing what actually happened */}
                <Line
                  type="monotone"
                  dataKey="actuals"
                  name="Actual Performance ($)"
                  stroke={CHART_COLORS.actuals}
                  strokeWidth={3}
                  dot={(props) => {
                    const { cx, cy, index } = props
                    if (!cx || !cy) return null
                    // Show dots on actuals line
                    return (
                      <circle 
                        key={`actual-dot-${index}`}
                        cx={cx} 
                        cy={cy} 
                        r={4} 
                        fill={CHART_COLORS.actuals} 
                        stroke="#fff" 
                        strokeWidth={2}
                      />
                    )
                  }}
                  connectNulls={false}
                  activeDot={{ r: 8, fill: CHART_COLORS.actuals, stroke: '#fff', strokeWidth: 2 }}
                />
                
                {/* Forecast line - purple, with dots */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  name="10-Year Forecast ($)"
                  stroke={CHART_COLORS.forecast}
                  strokeWidth={3}
                  strokeDasharray="8 4"
                  dot={(props) => {
                    const { cx, cy, index } = props
                    if (!cx || !cy) return null
                    return (
                      <circle 
                        key={`forecast-dot-${index}`}
                        cx={cx} 
                        cy={cy} 
                        r={4} 
                        fill={CHART_COLORS.forecast} 
                        stroke="#fff" 
                        strokeWidth={2}
                      />
                    )
                  }}
                  connectNulls={false}
                  activeDot={{ r: 8, fill: CHART_COLORS.forecast, stroke: '#fff', strokeWidth: 2 }}
                />
                
                <Legend 
                  verticalAlign="bottom"
                  iconType="circle"
                  wrapperStyle={{ paddingTop: 20 }}
                  formatter={(value: string) => <span className="text-foreground">{value}</span>}
                />
              </ComposedChart>
              </SafeChart>
            </>
            )}
          </div>
          
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-border">
            <div className="text-center p-4 rounded-lg bg-purple-50 dark:bg-purple-500/10">
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">
                ${(performanceLineData[performanceLineData.length - 1]?.forecast || 
                   performanceLineData[performanceLineData.length - 1]?.actuals ||
                   performanceLineData[performanceLineData.length - 1]?.historical)?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "..."}
              </p>
              <p className="text-sm text-muted-foreground">Portfolio Value</p>
              <p className="text-xs text-muted-foreground/70">(Started at $100)</p>
            </div>
            <div className="text-center p-4 rounded-lg bg-slate-100 dark:bg-slate-800">
              <p className="text-3xl font-bold text-slate-600 dark:text-slate-300">
                ${performanceLineData[performanceLineData.length - 1]?.benchmark?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "..."}
              </p>
              <p className="text-sm text-muted-foreground">Benchmark Value</p>
              <p className="text-xs text-muted-foreground/70">(S&P 500)</p>
            </div>
            <div className={`text-center p-4 rounded-lg ${
              cumulativeExcessVsSp500 === null
                ? 'bg-slate-100 dark:bg-slate-800'
                : cumulativeExcessVsSp500 >= 0
                  ? 'bg-green-50 dark:bg-green-500/10'
                  : 'bg-red-50 dark:bg-red-500/10'
            }`}>
              <p className={`text-3xl font-bold ${
                cumulativeExcessVsSp500 === null
                  ? 'text-slate-600 dark:text-slate-300'
                  : cumulativeExcessVsSp500 >= 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
              }`}>
                {formatPercent(cumulativeExcessVsSp500)}
              </p>
              <p className="text-sm text-muted-foreground">Cumulative Excess vs S&P 500</p>
              <p className="text-xs text-muted-foreground/70">(pp difference in total return)</p>
            </div>
            <div className="text-center p-4 rounded-lg bg-amber-50 dark:bg-amber-500/10">
              <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">
                +{(forecastVsActual?.forecast_premium ?? 7.1).toFixed(1)}%
              </p>
              <p className="text-sm text-muted-foreground">Expected R&D Premium (5yr)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20 hover:border-emerald-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Annualized Portfolio</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">
              {formatPercent(backtest?.portfolio_performance?.annualized_return)}
            </div>
            <p className="text-xs text-muted-foreground">
              {backtestStart}-{backtestEnd} average
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Annualized S&P 500</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-400">
              {formatPercent(backtest?.sp500_performance?.annualized_return)}
            </div>
            <p className="text-xs text-muted-foreground">
              Market benchmark
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alpha Generated</CardTitle>
            {(backtest?.excess_vs_sp500 || 0) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-purple-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(backtest?.excess_vs_sp500 || 0) >= 0 ? 'text-purple-400' : 'text-red-400'}`}>
              {formatPercent(backtest?.excess_vs_sp500)}
            </div>
            <p className="text-xs text-muted-foreground">
              Annualized excess vs S&P 500
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20 hover:border-amber-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
            <Target className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-400">
              {backtest?.portfolio_performance?.sharpe_ratio?.toFixed(2) || "..."}
            </div>
            <p className="text-xs text-muted-foreground">
              Risk-adjusted return
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="holdings" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted/50 flex-wrap">
          <TabsTrigger value="holdings">Holdings ({asOfYear})</TabsTrigger>
          <TabsTrigger value="performance">Performance History</TabsTrigger>
          <TabsTrigger value="allocation">Sector Allocation</TabsTrigger>
          <TabsTrigger value="methodology">
            <FlaskConical className="w-4 h-4 mr-1" />
            Methodology
          </TabsTrigger>
          <TabsTrigger value="sector-weights">
            <Scale className="w-4 h-4 mr-1" />
            Sector Weights
          </TabsTrigger>
        </TabsList>

        {/* Holdings Tab */}
        <TabsContent value="holdings" className="space-y-4">
          <Card className="border-border">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>
                  Top {nHoldings} R&D Companies
                  <Badge variant="outline" className="ml-2">As of {asOfYear}</Badge>
                </CardTitle>
                <CardDescription>
                  Dynamically selected based on R&D intensity in {asOfYear}
                </CardDescription>
              </div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExportHoldings}
                      disabled={!holdings || holdings.length === 0}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Export Holdings
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Download current ETF holdings as CSV file
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </CardHeader>
            <CardContent>
              <div className="max-h-[600px] overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-12">#</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Sector</TableHead>
                      <TableHead className="text-right">Weight</TableHead>
                      <TableHead className="text-right">R&D Intensity</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(holdings || []).map((h, i) => (
                      <TableRow key={h.symbol} className="hover:bg-muted/50">
                        <TableCell className="text-muted-foreground font-mono">{i + 1}</TableCell>
                        <TableCell className="font-mono font-bold">
                          <Link to={`/companies/${h.symbol}`} className="text-primary hover:underline">
                            {h.symbol}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-48 truncate text-foreground">{h.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="bg-muted/50">{h.sector}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">{h.weight.toFixed(1)}%</TableCell>
                        <TableCell className="text-right font-mono text-green-600 dark:text-green-400 font-semibold">
                          {h.rd_intensity.toFixed(1)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <CardTitle>Portfolio vs S&P 500 ({backtestStart}-{asOfYear})</CardTitle>
              <CardDescription>Year-over-year comparison of R&D ETF vs S&P 500</CardDescription>
            </CardHeader>
            <CardContent style={{ height: 384, minHeight: 384 }}>
              {chartsReady && activeTab === "performance" && yearlyDataForCharts && yearlyDataForCharts.length > 0 ? (
              <SafeChart key={`perf-chart-${activeTab}`} height={384} minHeight={360} debounce={100}>
                <LineChart data={yearlyDataForCharts}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    formatter={(value) => [`${(value as number)?.toFixed(1)}%`]}
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--popover))", 
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px"
                    }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="portfolio_return" 
                    name="R&D ETF" 
                    stroke="#22c55e" 
                    strokeWidth={3}
                    dot={{ fill: '#22c55e', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 8 }} 
                  />
                  <Line 
                    type="monotone" 
                    dataKey="sp500_return" 
                    name="S&P 500" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
                  />
                </LineChart>
              </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader>
              <CardTitle>Annual Excess Return (Alpha)</CardTitle>
              <CardDescription>R&D ETF outperformance vs S&P 500 each year</CardDescription>
            </CardHeader>
            <CardContent style={{ height: 256, minHeight: 256 }}>
              {chartsReady && activeTab === "performance" && yearlyDataForCharts && yearlyDataForCharts.length > 0 ? (
              <SafeChart key={`alpha-chart-${activeTab}`} height={256} minHeight={240} debounce={100}>
                <BarChart data={yearlyDataForCharts}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    formatter={(value) => [`${(value as number)?.toFixed(1)}%`, "Excess vs S&P 500"]}
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--popover))", 
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px"
                    }}
                  />
                  <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                  <Bar dataKey="excess_vs_sp500" name="Excess vs S&P 500" radius={[4, 4, 0, 0]}>
                    {(yearlyDataForCharts || []).map((entry, index) => (
                      <Cell
                        key={index}
                        fill={(entry.excess_vs_sp500 ?? 0) >= 0 ? "#22c55e" : "#ef4444"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Allocation Tab */}
        <TabsContent value="allocation" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-border">
              <CardHeader>
                <CardTitle>Sector Allocation ({asOfYear})</CardTitle>
                <CardDescription>Portfolio weight distribution by sector</CardDescription>
              </CardHeader>
              <CardContent style={{ height: 320, minHeight: 320 }}>
                {chartsReady && activeTab === "allocation" && sectorAllocation && sectorAllocation.length > 0 ? (
                <SafeChart key={`sector-chart-${activeTab}`} height={320} minHeight={300} debounce={100}>
                  <PieChart>
                    <Pie
                      data={(sectorAllocation || []).map(s => ({ name: s.sector, value: s.weight }))}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ name, value }) => `${name}: ${value}%`}
                      labelLine={{ stroke: '#64748b' }}
                    >
                      {(sectorAllocation || []).map((_, index) => (
                        <Cell key={index} fill={SECTOR_COLORS[index % SECTOR_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      formatter={(value) => [`${value}%`, "Weight"]}
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--popover))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }}
                    />
                  </PieChart>
                </SafeChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
                )}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader>
                <CardTitle>Sector Breakdown</CardTitle>
                <CardDescription>Detailed allocation by sector</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {(sectorAllocation || []).map((s, i) => (
                    <div key={s.sector} className="flex items-center gap-4">
                      <div
                        className="w-4 h-4 rounded-full flex-shrink-0"
                        style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }}
                      />
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm font-medium text-foreground">{s.sector}</span>
                          <span className="font-mono text-sm text-foreground">{s.weight}%</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full transition-all"
                            style={{ 
                              width: `${s.weight}%`,
                              backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length]
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Methodology Tab */}
        <TabsContent value="methodology" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-emerald-500" />
                R&D Alpha Selection Formula
              </CardTitle>
              <CardDescription>
                Research-based, sector-agnostic scoring methodology
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Main Formula */}
              <div className="bg-slate-900 dark:bg-slate-950 rounded-lg p-6 border border-slate-700">
                <h3 className="text-lg font-semibold text-white mb-4">Selection Formula</h3>
                <div className="text-center">
                  <code className="text-xl text-emerald-400 font-mono">
                    {methodology?.formula || "R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility"}
                  </code>
                </div>
              </div>

              {/* Formula Components */}
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  Formula Components
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setShowMethodologyDetails(!showMethodologyDetails)}
                  >
                    {showMethodologyDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </Button>
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  {Object.entries(methodology?.components || {}).map(([key, description]) => (
                    <div key={key} className="bg-muted/50 rounded-lg p-4 border border-border">
                      <div className="font-mono text-sm font-semibold text-emerald-500 mb-2">
                        {key}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {description as string}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sector Constraints */}
              {showMethodologyDetails && (
                <>
                  <div className="border-t border-border pt-6">
                    <h3 className="text-lg font-semibold mb-4">Sector Constraints</h3>
                    <div className="grid gap-4 md:grid-cols-2">
                      {Object.entries(methodology?.sector_constraints || {}).map(([key, constraint]) => (
                        <div key={key} className="bg-muted/50 rounded-lg p-4 border border-border">
                          <div className="font-semibold text-foreground mb-1">
                            {key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                          <div className="text-2xl font-mono text-emerald-500">
                            {((constraint as { value: number }).value * 100).toFixed(0)}%
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {(constraint as { description: string }).description}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Research Citations */}
                  <div className="border-t border-border pt-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <BookOpen className="w-5 h-5" />
                      Research Foundation
                    </h3>
                    <div className="space-y-2">
                      {(methodology?.research_citations || []).map((citation, i) => (
                        <div key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                          <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-xs font-bold flex-shrink-0">
                            {i + 1}
                          </div>
                          <span>{citation}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Parameters */}
                  <div className="border-t border-border pt-6">
                    <h3 className="text-lg font-semibold mb-4">Model Parameters</h3>
                    <div className="grid gap-2 md:grid-cols-3">
                      {Object.entries(methodology?.parameters || {}).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center bg-muted/30 rounded px-3 py-2">
                          <span className="text-sm text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </span>
                          <span className="font-mono text-sm text-foreground">
                            {typeof value === "number" ? value.toFixed(2) : value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <div className="text-xs text-muted-foreground text-right">
                Last updated: {methodology?.last_updated || "..."}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sector Weights Tab */}
        <TabsContent value="sector-weights" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-blue-500" />
                Sector Weight Targets vs Actual
              </CardTitle>
              <CardDescription>
                Sector-agnostic weighting prevents tech/biotech overconcentration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Sector</TableHead>
                    <TableHead className="text-right">Target</TableHead>
                    <TableHead className="text-right">Actual</TableHead>
                    <TableHead className="text-right">Min</TableHead>
                    <TableHead className="text-right">Max</TableHead>
                    <TableHead className="text-right">Companies</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(sectorWeights || []).map((sw) => (
                    <TableRow key={sw.sector} className="hover:bg-muted/50">
                      <TableCell className="font-medium">{sw.sector}</TableCell>
                      <TableCell className="text-right font-mono">{sw.target_weight.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono font-semibold">{sw.actual_weight.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">{sw.min_weight.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">{sw.max_weight.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono">{sw.company_count}</TableCell>
                      <TableCell className="text-center">
                        {sw.status === "on_target" && (
                          <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30">
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            On Target
                          </Badge>
                        )}
                        {sw.status === "overweight" && (
                          <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/30">
                            <TrendingUp className="w-3 h-3 mr-1" />
                            Overweight
                          </Badge>
                        )}
                        {sw.status === "underweight" && (
                          <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30">
                            <TrendingDown className="w-3 h-3 mr-1" />
                            Underweight
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* R&D Alpha Holdings with Scoring Details */}
          {rdAlphaHoldings && (
            <Card className="border-border">
              <CardHeader>
                <CardTitle>R&D Alpha Holdings with Score Breakdown</CardTitle>
                <CardDescription>
                  {rdAlphaHoldings.selected_count} selected from {rdAlphaHoldings.total_candidates} candidates
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-h-[500px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="w-10">#</TableHead>
                        <TableHead>Symbol</TableHead>
                        <TableHead>Sector</TableHead>
                        <TableHead className="text-right">R&D %</TableHead>
                        <TableHead className="text-right">Capped</TableHead>
                        <TableHead className="text-right">Sector Adj</TableHead>
                        <TableHead className="text-right">Quality</TableHead>
                        <TableHead className="text-right">Score</TableHead>
                        <TableHead className="text-right">Weight</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rdAlphaHoldings.holdings.map((h) => (
                        <TableRow key={h.symbol} className="hover:bg-muted/50">
                          <TableCell className="text-muted-foreground font-mono">{h.rank}</TableCell>
                          <TableCell className="font-mono font-bold">
                            <Link to={`/companies/${h.symbol}`} className="text-primary hover:underline">
                              {h.symbol}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="bg-muted/50 text-xs">{h.sector}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono text-green-600 dark:text-green-400">
                            {h.rd_intensity.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {h.rd_intensity_capped.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {h.sector_adjustment.toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {(h.quality_score * 100).toFixed(0)}%
                          </TableCell>
                          <TableCell className="text-right font-mono font-semibold text-emerald-500">
                            {h.final_score.toFixed(3)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {h.weight.toFixed(1)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* S&P 500 Forecast Attribution */}
          {sp500Forecast && (
            <Card className="border-border">
              <CardHeader>
                <CardTitle>S&P 500 Consensus Forecasts</CardTitle>
                <CardDescription>
                  {sp500Forecast.methodology_summary}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Year</TableHead>
                      <TableHead className="text-right">Low</TableHead>
                      <TableHead className="text-right">Mid</TableHead>
                      <TableHead className="text-right">High</TableHead>
                      <TableHead className="text-right">Return (Mid)</TableHead>
                      <TableHead>Type</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sp500Forecast.forecasts.slice(0, 8).map((f) => (
                      <TableRow key={f.year} className="hover:bg-muted/50">
                        <TableCell className="font-semibold">{f.year}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{f.level_low.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono font-semibold">{f.level_mid.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{f.level_high.toLocaleString()}</TableCell>
                        <TableCell className={`text-right font-mono ${f.return_mid >= 0 ? "text-green-600" : "text-red-600"}`}>
                          {f.return_mid >= 0 ? "+" : ""}{f.return_mid.toFixed(1)}%
                        </TableCell>
                        <TableCell>
                          <Badge variant={f.is_forecast ? "outline" : "default"} className={f.is_forecast ? "bg-purple-500/10 text-purple-600" : ""}>
                            {f.is_forecast ? "Forecast" : "Actual"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Sources */}
                <div className="border-t border-border pt-4">
                  <h4 className="text-sm font-semibold mb-3">Forecast Sources</h4>
                  <div className="grid gap-3 md:grid-cols-2">
                    {sp500Forecast.sources.map((source) => (
                      <div key={source.name} className="bg-muted/30 rounded-lg p-3">
                        <div className="font-semibold text-sm">{source.name}</div>
                        <div className="text-xs text-muted-foreground">{source.division}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Updated: {source.last_update} • {source.frequency}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="text-xs text-muted-foreground italic border-t border-border pt-4">
                  {sp500Forecast.disclaimer}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Portfolio
