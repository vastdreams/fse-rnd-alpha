/**
 * PATH: src/components/research/PnlEfficiencyTab.tsx
 * PURPOSE: PNL Efficiency Alpha research tab — scores table, quintile chart, methodology
 */

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import type { PnlEfficiencyScore, PnlQuintile } from "@/lib/api/types"

const QUINTILE_COLORS = ["#2563eb", "#16a34a", "#ca8a04", "#ea580c", "#dc2626"]

export function PnlEfficiencyTab() {
  const { data: scores, isLoading: loadingScores } = useQuery({
    queryKey: ["pnlScoresResearch"],
    queryFn: () => api.getPnlScores(undefined, 50),
    staleTime: 5 * 60 * 1000,
  })

  const { data: quintiles, isLoading: loadingQuintiles } = useQuery({
    queryKey: ["pnlQuintiles"],
    queryFn: () => api.getPnlQuintiles(),
    staleTime: 5 * 60 * 1000,
  })

  const { data: methodology } = useQuery({
    queryKey: ["pnlMethodology"],
    queryFn: api.getPnlMethodology,
    staleTime: 30 * 60 * 1000,
  })

  if (loadingScores || loadingQuintiles) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground animate-pulse">Loading PNL efficiency data...</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="border-blue-500/20 bg-gradient-to-r from-blue-500/5 to-purple-500/5">
        <CardHeader>
          <CardTitle>PNL Efficiency Alpha</CardTitle>
          <CardDescription>
            Operating efficiency scoring based on sector-relative P&L ratios.
            Phase 1 covers gross, overhead, operating efficiency and profit conversion.
            Labor/payroll factors are deferred to Phase 2.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Quintile Chart + Table */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>PNL Efficiency by Quintile</CardTitle>
            <CardDescription>Average composite z-score by quintile (sorted by efficiency)</CardDescription>
          </CardHeader>
          <CardContent style={{ height: 320, minHeight: 320 }}>
            {quintiles && quintiles.length > 0 ? (
              <SafeChart height={320} minHeight={300} debounce={50}>
                <BarChart data={quintiles}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="label" tick={{ fill: "hsl(var(--foreground))", fontSize: 11 }} />
                  <YAxis tickFormatter={(v: number) => v.toFixed(2)} tick={{ fill: "hsl(var(--foreground))" }} />
                  <Tooltip
                    formatter={(value: number) => [value.toFixed(3), "Composite Z"]}
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                  />
                  <Bar dataKey="avg_composite_z" name="Avg Composite Z" radius={[4, 4, 0, 0]}>
                    {(quintiles || []).map((_: PnlQuintile, i: number) => (
                      <Cell key={i} fill={QUINTILE_COLORS[i]} />
                    ))}
                  </Bar>
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">No data</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quintile Breakdown</CardTitle>
            <CardDescription>Component averages by efficiency quintile</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quintile</TableHead>
                  <TableHead className="text-right">Gross Eff</TableHead>
                  <TableHead className="text-right">Overhead</TableHead>
                  <TableHead className="text-right">Operating</TableHead>
                  <TableHead className="text-right">Profit Conv</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(quintiles || []).map((q: PnlQuintile) => (
                  <TableRow key={q.quintile}>
                    <TableCell>
                      <Badge style={{ backgroundColor: QUINTILE_COLORS[q.quintile - 1] }} className="text-white">
                        {q.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono">{(q.avg_gross_eff * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right font-mono">{(q.avg_overhead_eff * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right font-mono">{(q.avg_operating_eff * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right font-mono">{(q.avg_profit_conv * 100).toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Top Scores Table */}
      <Card>
        <CardHeader>
          <CardTitle>Top PNL Efficiency Scores</CardTitle>
          <CardDescription>Companies ranked by composite operating efficiency (sector-relative)</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Sector</TableHead>
                <TableHead className="text-right">Composite Z</TableHead>
                <TableHead className="text-right">Gross Eff</TableHead>
                <TableHead className="text-right">Overhead</TableHead>
                <TableHead className="text-right">Operating</TableHead>
                <TableHead className="text-right">Profit Conv</TableHead>
                <TableHead className="text-right">Sector %ile</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(scores || []).map((s: PnlEfficiencyScore) => (
                <TableRow key={s.symbol}>
                  <TableCell className="text-muted-foreground font-mono">{s.selection_rank}</TableCell>
                  <TableCell className="font-mono font-bold text-primary">{s.symbol}</TableCell>
                  <TableCell><Badge variant="outline" className="bg-muted/50">{s.sector}</Badge></TableCell>
                  <TableCell className={`text-right font-mono font-bold ${s.composite_z > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>{s.composite_z.toFixed(3)}</TableCell>
                  <TableCell className="text-right font-mono">{(s.gross_efficiency * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono">{(s.overhead_efficiency * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono">{(s.operating_efficiency * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right font-mono">{(s.profit_conversion * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right">{s.sector_percentile.toFixed(0)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Methodology */}
      {methodology && (
        <Card>
          <CardHeader>
            <CardTitle>Methodology</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Scoring</p>
              <p className="text-sm">{methodology.scoring_method}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Normalization</p>
              <p className="text-sm">{methodology.normalization}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Components</p>
              <div className="grid gap-2 md:grid-cols-2">
                {Object.entries(methodology.components).map(([key, desc]) => (
                  <div key={key} className="rounded border p-3">
                    <p className="font-mono text-xs text-muted-foreground">{key}</p>
                    <p className="text-sm mt-1">{desc as string}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Phase</p>
              <p className="text-sm">{methodology.phase}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Excluded (Phase 2)</p>
              <ul className="text-sm list-disc list-inside space-y-1">
                {methodology.excluded.map((item: string, i: number) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
