/**
 * PATH: src/components/overview/DatasetOverview.tsx
 * PURPOSE: Dataset key metrics cards and R&D Intensity Trends chart with explanation.
 * WHY: Extracted from Overview.tsx to keep files under 300 lines.
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Building2, FlaskConical, BarChart3, Calendar, Info } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip } from "recharts"
import { SafeChart } from "@/components/SafeChart"

interface DatasetOverviewProps {
  overview: any
  rdTrends: any
}

export function DatasetOverview({ overview, rdTrends }: DatasetOverviewProps) {
  return (
    <>
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
    </>
  )
}
