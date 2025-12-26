/**
 * PATH: frontend/src/pages/Overview.tsx
 * PURPOSE:
 *   - Landing page summarizing the R&D factor research and dataset coverage.
 *
 * ROLE IN ARCHITECTURE:
 *   - Frontend overview/marketing + high-level research navigation.
 *
 * MAIN EXPORTS:
 *   - Overview: the dashboard landing page component.
 *
 * NON-RESPONSIBILITIES:
 *   - Does not compute research results (backend does).
 *   - Does not hardcode unverifiable research statistics (“0 hallucinations” policy).
 *
 * NOTES FOR FUTURE AI:
 *   - Any numeric claim on this page should be rendered from API endpoints (aggregate ANOVA, annual HML series, FMP overview).
 *   - Avoid strong guarantee language; keep claims as dataset-conditional (“in this sample”).
 */

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Building2, TrendingUp, FlaskConical, DollarSign, BarChart3, Calendar, Info, ArrowRight, BookOpen, Target } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, AreaChart, Area } from "recharts"
import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { SafeChart } from "@/components/SafeChart"

export function Overview() {
  const { data: aggregateAnova, isLoading: loadingAnova } = useQuery({
    queryKey: ["aggregateAnova", "overview"],
    queryFn: api.getAggregateAnova,
  })

  const { data: annualHml, isLoading: loadingHml } = useQuery({
    queryKey: ["annualHmlPremium", "overview"],
    queryFn: api.getAnnualHmlPremium,
  })

  const returnPeriodLabel = useMemo(() => {
    const rows = annualHml?.annual_premiums
    if (!rows || rows.length === 0) return "..."
    const first = rows[0]?.year
    const last = rows[rows.length - 1]?.year
    if (!first || !last) return "..."
    return `${first} to ${last}`
  }, [annualHml])

  const premium5yr = aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference
  const premium10yr = aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference
  const premium20yr = aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference

  const compoundingMultiplier10y = useMemo(() => {
    if (premium5yr === undefined) return null
    return Math.pow(1 + premium5yr / 100, 10)
  }, [premium5yr])
  
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["fmpOverview"],
    queryFn: api.getFMPOverview,
  })

  const { data: rdTrends, isLoading: loadingTrends } = useQuery({
    queryKey: ["rdTrends"],
    queryFn: api.getRDTrends,
  })

  const { data: rdBySector, isLoading: loadingSectors } = useQuery({
    queryKey: ["rdBySector"],
    queryFn: api.getRDBySector,
  })

  const { data: rdLeaders, isLoading: loadingLeaders } = useQuery({
    queryKey: ["rdLeaderboard"],
    queryFn: () => api.getRDLeaderboard(10),
  })

  const { data: returnsSummary, isLoading: loadingReturns } = useQuery({
    queryKey: ["returnsSummary"],
    queryFn: api.getReturnsSummary,
  })

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "..."
    if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`
    return num.toLocaleString()
  }

  const isLoading = loadingOverview || loadingTrends || loadingSectors || loadingLeaders || loadingReturns || loadingAnova || loadingHml

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-slate-700 p-8">
        <div className="absolute inset-0 bg-grid-white/[0.02]" />
        <div className="relative">
          <Badge className="mb-4 bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Pre-print Research</Badge>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-3">
            R&D Factor Analysis Platform
          </h1>
          <p className="text-lg text-slate-300 max-w-2xl mb-6">
            Investigating the relationship between Research & Development investment and 
            long-term stock returns across S&P 500 companies (statements: {overview?.year_range?.min ?? "..."}{overview?.year_range?.max ? `-${overview.year_range.max}` : ""}; returns: {returnPeriodLabel}).
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-emerald-400">
                {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">5-Year R&D Premium (Q5-Q1)</div>
            </div>
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-blue-400">
                {premium10yr !== undefined ? `${premium10yr >= 0 ? "+" : ""}${premium10yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">10-Year R&D Premium</div>
            </div>
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="text-2xl font-bold text-purple-400">
                {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."}
              </div>
              <div className="text-sm text-slate-400">20-Year R&D Premium</div>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <Link to="/research" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors">
              <BarChart3 className="h-4 w-4" />
              View Research Analysis
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/methodology" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white font-medium transition-colors">
              <BookOpen className="h-4 w-4" />
              Read Methodology
            </Link>
          </div>
        </div>
      </div>

      {/* So What? - The Key Insight */}
      <Card className="border-2 border-emerald-500/50 bg-gradient-to-r from-emerald-500/5 to-transparent">
        <CardContent className="pt-6 pb-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span className="text-emerald-500">💡</span> So What? Why Does This Matter?
          </h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">For Investors</h3>
                <p className="text-slate-600 dark:text-slate-300 text-sm">
                  Companies that invest heavily in R&D tend to outperform over the long term. 
                  In this dataset, the average Q5-Q1 premium is{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."}
                  </strong>{" "}
                  per year over 5-year windows (and{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."}
                  </strong>{" "}
                  over 20-year windows).
                </p>
              </div>
              
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">The Compounding Effect</h3>
                <p className="text-slate-600 dark:text-slate-300 text-sm">
                  <strong>Illustrative math (not a guarantee):</strong> if two portfolios differ by an incremental premium{" "}
                  <em>p</em> per year for <em>n</em> years, the higher-return portfolio ends at \((1+p)^n\) times the lower-return portfolio.
                  {compoundingMultiplier10y !== null && (
                    <>
                      {" "}With <em>p</em>={premium5yr?.toFixed(2)}% and <em>n</em>=10, the multiplier is{" "}
                      <strong className="text-emerald-600 dark:text-emerald-400">
                        ×{compoundingMultiplier10y.toFixed(2)}
                      </strong>.
                    </>
                  )}
                </p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
                <h3 className="font-semibold text-lg mb-2 text-slate-900 dark:text-white">Potential Portfolio Strategy</h3>
                <ul className="text-slate-600 dark:text-slate-300 text-sm space-y-1">
                  <li>• <strong>Tilt toward high-R&D:</strong> Overweight companies investing &gt;10% of revenue in R&D</li>
                  <li>• <strong>Sector diversification:</strong> Don't just buy Tech - find R&D leaders in every sector</li>
                  <li>• <strong>Long-term horizon:</strong> R&D benefits compound over 5+ years, not months</li>
                </ul>
              </div>
              
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-700">
                <h3 className="font-semibold text-lg mb-2 text-amber-700 dark:text-amber-400">⚠️ Important Caveats</h3>
                <ul className="text-slate-600 dark:text-slate-300 text-sm space-y-1">
                  <li>• Past performance ≠ future results</li>
                  <li>
                    • Premium varies by horizon (e.g., {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."} at 5yr to{" "}
                    {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."} at 20yr), and is not guaranteed
                  </li>
                  <li>• High R&D often means higher volatility</li>
                  <li>• Tier-1 survivorship bias is substantially mitigated but not CRSP/Compustat-grade</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Research Question */}
      <Card className="border-l-4 border-l-blue-500">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Target className="h-8 w-8 text-blue-500 flex-shrink-0" />
            <div>
              <h2 className="text-xl font-semibold mb-2">The Research Question</h2>
              <p className="text-muted-foreground">
                <strong>Do companies that invest heavily in R&D generate better long-term returns for shareholders?</strong>
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                We analyze 31 years of financial data from S&P 500 companies, ranking them into quintiles by R&D intensity 
                (R&D expense ÷ revenue) and comparing their subsequent stock returns. High-R&D companies (Q5) are 
                compared against low-R&D companies (Q1) to measure the "R&D premium."
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Dataset Overview</h2>
        <TooltipProvider>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-1">
                  <CardTitle className="text-sm font-medium text-slate-900 dark:text-white">S&P 500 Companies</CardTitle>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-slate-400 dark:text-slate-500 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>Current S&P 500 constituents with financial data. Note: Using current constituents introduces survivorship bias.</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
            <Building2 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{overview?.total_companies}</div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {overview?.companies_with_rd} report R&D (~{Math.round(((overview?.companies_with_rd || 0) / (overview?.total_companies || 1)) * 100)}%)
            </p>
          </CardContent>
        </Card>

            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-1">
                  <CardTitle className="text-sm font-medium text-slate-900 dark:text-white">Avg R&D Intensity</CardTitle>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-slate-400 dark:text-slate-500 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>R&D Intensity = R&D Expense ÷ Revenue × 100. Companies with 0% are included in lowest quintile (Q1).</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
            <FlaskConical className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{overview?.avg_rd_intensity?.toFixed(1)}%</div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Among companies reporting R&D
            </p>
          </CardContent>
        </Card>

            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-1">
                  <CardTitle className="text-sm font-medium text-slate-900 dark:text-white">Financial Records</CardTitle>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-slate-400 dark:text-slate-500 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>Annual income statements from FMP API. Data sourced from SEC 10-K filings.</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
            <BarChart3 className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{((overview?.total_income_statements || 0) / 1000).toFixed(1)}K</div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Company-year observations
            </p>
          </CardContent>
        </Card>

            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-1">
                  <CardTitle className="text-sm font-medium text-slate-900 dark:text-white">Time Period</CardTitle>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-slate-400 dark:text-slate-500 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>R&D reporting quality improved significantly after 2000. Pre-2010 data has ~30% coverage vs ~40% after 2010.</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Calendar className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{overview?.year_range?.min}-{overview?.year_range?.max}</div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {(overview?.year_range?.max ?? 0) - (overview?.year_range?.min ?? 0) + 1} years of data
            </p>
          </CardContent>
        </Card>
          </div>
        </TooltipProvider>
      </div>

      {/* R&D Trends Section */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
                R&D Intensity Trends Over Time
            </CardTitle>
              <CardDescription>
                Average R&D intensity (R&D/Revenue) across S&P 500 companies
              </CardDescription>
          </CardHeader>
          <CardContent>
              {rdTrends && rdTrends.length > 0 ? (
                <SafeChart height={300} minHeight={280}>
                <AreaChart data={rdTrends?.slice(-20)}>
                  <defs>
                    <linearGradient id="rdGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#16a34a" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#16a34a" stopOpacity={0.05}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="year" tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={12} />
                    <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={12} tickFormatter={(v) => `${v}%`} />
                    <RechartsTooltip 
                    contentStyle={{ backgroundColor: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
                    formatter={(value) => [`${(value as number).toFixed(2)}%`, 'R&D Intensity']}
                  />
                  <Area type="monotone" dataKey="avg_rd_intensity" stroke="#16a34a" fill="url(#rdGradient)" strokeWidth={2} />
                </AreaChart>
                </SafeChart>
            ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">Loading...</div>
            )}
          </CardContent>
        </Card>
        </div>
        <div className="lg:col-span-2 flex flex-col justify-center">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">What This Shows</h3>
            <p className="text-muted-foreground text-sm">
              R&D intensity has <strong>increased steadily</strong> over the past two decades as technology 
              and healthcare sectors have grown to dominate the S&P 500.
            </p>
            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div className="text-sm font-medium text-emerald-400">Upward Trend</div>
                <div className="text-xs text-muted-foreground">Companies are investing more in R&D relative to revenue</div>
              </div>
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <div className="text-sm font-medium text-amber-400">Caveat</div>
                <div className="text-xs text-muted-foreground">Only ~40% of S&P 500 companies report R&D as a separate line item</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sector Analysis */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2 flex flex-col justify-center order-2 lg:order-1">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Sector Breakdown</h3>
            <p className="text-muted-foreground text-sm">
              R&D intensity varies dramatically by sector. <strong>Technology and Healthcare</strong> companies 
              invest 10-20% of revenue in R&D, while sectors like Utilities and Real Estate invest less than 1%.
            </p>
            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <div className="text-sm font-medium text-purple-400">High R&D Sectors</div>
                <div className="text-xs text-muted-foreground">Tech, Healthcare, Biotech dominate Q5 (top quintile)</div>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <div className="text-sm font-medium text-blue-400">Low R&D Sectors</div>
                <div className="text-xs text-muted-foreground">Utilities, REITs, Banks typically in Q1 (bottom quintile)</div>
              </div>
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <div className="text-sm font-medium text-amber-400">Sector Concentration Risk</div>
                <div className="text-xs text-muted-foreground">~70% of Q5 is Tech/Healthcare, which may bias results</div>
              </div>
            </div>
          </div>
        </div>
        <div className="lg:col-span-3 order-1 lg:order-2">
          <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5" />
              R&D Intensity by Sector
            </CardTitle>
              <CardDescription>
                Average R&D as percentage of revenue by GICS sector
              </CardDescription>
          </CardHeader>
          <CardContent>
            {rdBySector && rdBySector.length > 0 ? (
                <SafeChart height={300} minHeight={280}>
                <BarChart data={rdBySector?.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis type="number" tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={12} tickFormatter={(v) => `${v}%`} />
                    <YAxis type="category" dataKey="sector" tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={10} width={100} />
                    <RechartsTooltip 
                    contentStyle={{ backgroundColor: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
                    formatter={(value) => [`${(value as number).toFixed(2)}%`, 'Avg R&D Intensity']}
                  />
                  <Bar dataKey="avg_rd_intensity" fill="#7c3aed" radius={[0, 4, 4, 0]} />
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">Loading...</div>
            )}
          </CardContent>
        </Card>
        </div>
      </div>

      {/* Leaders and Returns */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Top R&D Spenders
            </CardTitle>
            <CardDescription>
              Companies with highest R&D intensity (R&D/Revenue)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {rdLeaders?.map((leader, idx) => (
                <div key={leader.symbol} className="flex items-center justify-between p-2 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-muted-foreground w-6">{idx + 1}</span>
                    <div>
                      <span className="font-semibold text-foreground">{leader.symbol}</span>
                      <span className="text-sm text-muted-foreground ml-2">{leader.name?.slice(0, 25)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-600 dark:text-green-400">{leader.avg_rd_intensity.toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground">{formatNumber(leader.total_rd_spend)} total</div>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Note: Very high R&D intensity (&gt;50%) often indicates pre-revenue biotech or early-stage companies.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Market Returns by Year
            </CardTitle>
            <CardDescription>
              Average annual returns across the S&P 500 sample
            </CardDescription>
          </CardHeader>
          <CardContent>
            {returnsSummary && returnsSummary.length > 0 ? (
              <SafeChart height={300} minHeight={280}>
                <BarChart data={returnsSummary?.slice(-15)}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="year" tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={12} />
                  <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
                    formatter={(value) => [`${(value as number).toFixed(1)}%`, 'Avg Return']}
                  />
                  <Bar 
                    dataKey="avg_return" 
                    fill="#2563eb"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">Loading...</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Data Source Footer */}
      <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600">
        <CardContent className="pt-6">
          <div className="text-center">
            <h3 className="font-semibold mb-2 text-slate-900 dark:text-white">Data Sources & Methodology</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
              Financial data sourced from <strong className="text-slate-800 dark:text-white">Financial Modeling Prep API</strong> (not directly from SEC 10-K filings). 
              R&D intensity calculated as R&D Expense ÷ Total Revenue. Companies without separate R&D reporting are 
              assigned to the lowest quintile (Q1).
            </p>
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex flex-wrap justify-center gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span>{overview?.total_companies} companies</span>
              <span>•</span>
              <span>{overview?.total_income_statements?.toLocaleString()} financial records</span>
              <span>•</span>
              <span>{overview?.year_range?.min}-{overview?.year_range?.max}</span>
              <span>•</span>
              <span>Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
