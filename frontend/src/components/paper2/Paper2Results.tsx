/**
 * PATH: frontend/src/components/paper2/Paper2Results.tsx
 * FILE_ID: PAPER2-RESULTS-001
 * PURPOSE: Results section with charts and sector leaders for Paper2
 * WHY: Extracted from Paper2.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - @/components/ui/*: UI primitives
 * - recharts: chart components
 * - @/components/SafeChart: chart wrapper
 * - lucide-react: icons
 * - react-router-dom: Link
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SafeChart } from "@/components/SafeChart"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts"
import { TrendingUp } from "lucide-react"
import { Link } from "react-router-dom"

const SECTOR_COLORS: Record<string, string> = {
  "Technology": "#3b82f6",
  "Healthcare": "#22c55e",
  "Consumer Cyclical": "#f59e0b",
  "Financial Services": "#8b5cf6",
  "Industrials": "#6366f1",
  "Communication Services": "#ec4899",
  "Consumer Defensive": "#14b8a6",
  "Energy": "#ef4444",
  "Basic Materials": "#84cc16",
  "Real Estate": "#06b6d4",
  "Utilities": "#64748b",
}

interface Paper2ResultsProps {
  sectorData: any[]
  radarData: any[]
  leadersBySector: Record<string, any[]>
}

export function Paper2Results({
  sectorData,
  radarData,
  leadersBySector,
}: Paper2ResultsProps) {
  return (
    <section id="results" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <TrendingUp className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">5. Results</h2>
      </div>
      
      <div className="space-y-6">
        {/* R&D Intensity by Sector */}
        <Card>
          <CardHeader>
            <CardTitle>5.1 R&D Intensity Distribution</CardTitle>
            <CardDescription>Average R&D/Revenue ratio by GICS sector</CardDescription>
          </CardHeader>
          <CardContent className="h-[400px]">
            <SafeChart height={400} minHeight={300}>
              <BarChart data={sectorData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                <YAxis 
                  type="category" 
                  dataKey="sector" 
                  stroke="hsl(var(--muted-foreground))" 
                  width={120}
                  tick={{ fontSize: 11 }}
                />
                <RechartsTooltip
                  formatter={(value) => [`${(value as number)?.toFixed(2)}%`, "R&D Intensity"]}
                  contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                />
                <Bar dataKey="avg_rd_intensity" radius={[0, 4, 4, 0]}>
                  {sectorData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </SafeChart>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>5.2 Multi-Dimensional Sector Profile</CardTitle>
            <CardDescription>R&D intensity vs. company count by sector</CardDescription>
          </CardHeader>
          <CardContent className="h-[400px]">
            <SafeChart height={400} minHeight={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="hsl(var(--border))" />
                <PolarAngleAxis dataKey="sector" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={{ fill: "#64748b", fontSize: 10 }} />
                <RechartsTooltip
                  formatter={(value, name) => [
                    name === "intensity" ? `${(value as number).toFixed(1)}%` : (value as number).toFixed(0),
                    name === "intensity" ? "R&D Intensity" : "Companies"
                  ]}
                  contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                />
                <Radar name="R&D Intensity" dataKey="intensity" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                <Radar name="Companies" dataKey="companies" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
              </RadarChart>
            </SafeChart>
          </CardContent>
        </Card>

        {/* Sector Leaders */}
        <Card>
          <CardHeader>
            <CardTitle>5.3 Sector R&D Leaders</CardTitle>
            <CardDescription>Top R&D-intensive companies by sector</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(leadersBySector).slice(0, 6).map(([sector, leaders]) => (
                <div key={sector} className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-2 mb-3">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: SECTOR_COLORS[sector] || "#64748b" }}
                    />
                    <span className="font-medium text-sm">{sector}</span>
                  </div>
                  <div className="space-y-1.5">
                    {(leaders || []).slice(0, 3).map((company: any) => (
                      <div key={company.symbol} className="flex items-center justify-between text-sm">
                        <Link 
                          to={`/companies/${company.symbol}`}
                          className="font-mono text-primary hover:underline"
                        >
                          {company.symbol}
                        </Link>
                        <span className="text-green-600 dark:text-emerald-400 font-mono text-xs">
                          {company.avg_rd_intensity?.toFixed(1)}%
                        </span>
                      </div>
                    ))}
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
