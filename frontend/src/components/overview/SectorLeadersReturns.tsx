/**
 * PATH: src/components/overview/SectorLeadersReturns.tsx
 * PURPOSE: Sector analysis chart, top R&D spenders, market returns chart, and data source footer.
 * WHY: Extracted from Overview.tsx to keep files under 300 lines.
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { FlaskConical, DollarSign, TrendingUp } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip } from "recharts"
import { SafeChart } from "@/components/SafeChart"

interface SectorLeadersReturnsProps {
  overview: any
  rdBySector: any
  rdLeaders: any
  returnsSummary: any
  formatNumber: (num: number | null | undefined) => string
}

export function SectorLeadersReturns({
  overview,
  rdBySector,
  rdLeaders,
  returnsSummary,
  formatNumber,
}: SectorLeadersReturnsProps) {
  return (
    <>
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
              {rdLeaders?.map((leader: any, idx: number) => (
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
    </>
  )
}
