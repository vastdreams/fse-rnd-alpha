/**
 * PATH: frontend/src/components/paper4/Paper4Results.tsx
 * PURPOSE: Results section with charts and R&D leaders for Paper 4
 * WHY: Extracted from Paper4.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - recharts: chart rendering
 * - SafeChart: responsive chart wrapper
 * - UI components (Card): layout
 * - react-router-dom Link: company navigation
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SafeChart } from "@/components/SafeChart"
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  LineChart,
  Line,
  Legend,
  AreaChart,
  Area,
} from "recharts"
import { TrendingUp } from "lucide-react"
import { Link } from "react-router-dom"

interface Paper4ResultsProps {
  trendData: any[]
  rdLeaders: any[] | undefined
}

export function Paper4Results({ trendData, rdLeaders }: Paper4ResultsProps) {
  return (
    <section id="results" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <TrendingUp className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">5. Results</h2>
      </div>
      
      <div className="space-y-6">
        {/* R&D Trends Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>5.1 R&D Investment Trends</CardTitle>
            <CardDescription>Evolution of R&D spending and intensity across the S&P 500</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            {trendData.length > 0 ? (
            <SafeChart height={320} minHeight={250}>
              <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `$${v}B`} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="avgIntensity" name="Avg R&D Intensity (%)" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                <Line yAxisId="right" type="monotone" dataKey="totalSpendB" name="Total R&D Spend ($B)" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </SafeChart>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">Loading chart data...</div>
            )}
          </CardContent>
        </Card>

        {/* Company Count */}
        <Card>
          <CardHeader>
            <CardTitle>5.2 R&D Reporting Coverage</CardTitle>
            <CardDescription>Number of companies reporting R&D expenses by year</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            {trendData.length > 0 ? (
            <SafeChart height={256} minHeight={250}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="companyGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <RechartsTooltip formatter={(value) => [value as number, "Companies"]} contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                <Area type="monotone" dataKey="companies" fill="url(#companyGradient)" stroke="#8b5cf6" strokeWidth={2} />
              </AreaChart>
            </SafeChart>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">Loading chart data...</div>
            )}
          </CardContent>
        </Card>

        {/* Top R&D Leaders */}
        <Card>
          <CardHeader>
            <CardTitle>5.3 Top R&D Innovators</CardTitle>
            <CardDescription>Companies with highest R&D intensity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {(rdLeaders || []).slice(0, 10).map((company, i) => (
                <div 
                  key={company.symbol}
                  className="flex items-center justify-between p-4 rounded-lg bg-slate-800 hover:bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/10 flex items-center justify-center text-sm font-bold text-amber-400">
                      {i + 1}
                    </div>
                    <div>
                      <Link to={`/companies/${company.symbol}`} className="font-mono font-bold text-primary hover:underline">
                        {company.symbol}
                      </Link>
                      <p className="text-xs text-slate-600 dark:text-slate-400 truncate max-w-32">{company.name || company.symbol}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-green-600 dark:text-emerald-400">{company.avg_rd_intensity?.toFixed(1)}%</div>
                    <div className="text-xs text-slate-500">${(company.total_rd_spend / 1e9).toFixed(1)}B total</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
