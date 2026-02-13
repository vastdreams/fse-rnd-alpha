/**
 * PATH: src/components/research/QuintileAnalysisTab.tsx
 * PURPOSE: Quintile R&D intensity chart, statistics table, and rolling-window premium bar chart
 * WHY: Extracted from Research.tsx to keep each file under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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
  Tooltip,
  Legend,
  Cell,
  ReferenceLine,
} from "recharts"
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SafeChart } from "@/components/SafeChart"
import { QUINTILE_COLORS } from "@/hooks/useResearchData"
import type { QuintilePerf, WindowResult } from "@/lib/api"

interface QuintileAnalysisTabProps {
  selectedWindow: string
  chartsReady: boolean
  quintilePerf: QuintilePerf[] | undefined
  rollingWindows: WindowResult[] | undefined
  handleExportQuintiles: () => void
  formatPercent: (val: number | null | undefined) => string
}

export function QuintileAnalysisTab({
  selectedWindow,
  chartsReady,
  quintilePerf,
  rollingWindows,
  handleExportQuintiles,
  formatPercent,
}: QuintileAnalysisTabProps) {
  return (
    <>
      <div className="flex justify-end mb-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleExportQuintiles}
          disabled={!quintilePerf || quintilePerf.length === 0}
        >
          <Download className="w-4 h-4 mr-2" />
          Export Quintile Data
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {/* Quintile R&D Intensity Chart */}
        <Card>
          <CardHeader>
            <CardTitle>R&D Intensity by Quintile ({selectedWindow})</CardTitle>
            <CardDescription>
              Q1 = Low R&D Intensity, Q5 = High R&D Intensity
            </CardDescription>
          </CardHeader>
          <CardContent style={{ height: 320, minHeight: 320 }}>
            {chartsReady && quintilePerf && quintilePerf.length > 0 ? (
              <SafeChart height={320} minHeight={300} debounce={50}>
                <BarChart data={quintilePerf || []} barGap={0}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="label" className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
                  <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
                  <Tooltip
                    formatter={(value, name) => [`${(value as number)?.toFixed(2)}%`, name as string]}
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", color: "hsl(var(--foreground))" }}
                  />
                  <Legend />
                  <Bar dataKey="avg_rd_intensity" name="R&D Intensity (% of Revenue)" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                    {(quintilePerf || []).map((_, index) => (
                      <Cell key={index} fill={QUINTILE_COLORS[index]} />
                    ))}
                  </Bar>
                </BarChart>
              </SafeChart>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
            )}
          </CardContent>
        </Card>

        {/* Quintile Statistics Table */}
        <Card>
          <CardHeader>
            <CardTitle>Quintile Statistics</CardTitle>
            <CardDescription>Performance metrics by R&D intensity quintile</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quintile</TableHead>
                  <TableHead className="text-right">R&D %</TableHead>
                  <TableHead className="text-right">Avg Return</TableHead>
                  <TableHead className="text-right">Volatility</TableHead>
                  <TableHead className="text-right">Sharpe</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(quintilePerf || []).map((q) => (
                  <TableRow key={q.quintile}>
                    <TableCell>
                      <Badge
                        style={{ backgroundColor: QUINTILE_COLORS[q.quintile - 1] }}
                        className="text-white"
                      >
                        {q.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{q.avg_rd_intensity?.toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{formatPercent(q.avg_return)}</TableCell>
                    <TableCell className="text-right">{q.avg_volatility?.toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{q.avg_sharpe?.toFixed(3)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Rolling Window Heatmap */}
      <Card>
        <CardHeader>
          <CardTitle>R&D Premium Over Time ({selectedWindow} Windows)</CardTitle>
          <CardDescription>High R&D (Q5) minus Low R&D (Q1) return differential</CardDescription>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
            Note: Rolling windows sort stocks once at window start and do not rebalance. Longer horizons show lower premiums due to signal staleness, not strategy failure. See Main Paper Section 8.2.
          </p>
        </CardHeader>
        <CardContent style={{ height: 256, minHeight: 256 }}>
          {chartsReady && rollingWindows && rollingWindows.length > 0 ? (
            <SafeChart height={256} minHeight={240} debounce={50}>
              <BarChart data={rollingWindows || []}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="start_year" 
                  className="text-xs"
                  tickFormatter={(v) => `${v}`}
                />
                <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                <Tooltip
                  formatter={(value) => [`${(value as number).toFixed(2)}%`, "R&D Premium"]}
                  labelFormatter={(v) => `Window starting ${v}`}
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                <Bar dataKey="rd_premium" name="R&D Premium (Q5-Q1, %)">
                  {(rollingWindows || []).map((entry, index) => (
                    <Cell 
                      key={index} 
                      fill={entry.rd_premium >= 0 ? "#16a34a" : "#dc2626"} 
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
    </>
  )
}
