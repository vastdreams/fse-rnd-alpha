/** Holdings, Performance, and Allocation tab contents. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { SECTOR_COLORS } from "@/hooks/usePortfolioData"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TabsContent } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, Cell, PieChart, Pie, LineChart, Line, ReferenceLine } from "recharts"
import { Download } from "lucide-react"
import { SafeChart } from "@/components/SafeChart"
import { Link } from "react-router-dom"
import { exportToCSV } from "@/lib/export"

interface Props {
  data: PortfolioData
  asOfYear: number
  nHoldings: number
  chartsReady: boolean
  activeTab: string
}

export function PortfolioCoreTabs({ data, asOfYear, nHoldings, chartsReady, activeTab }: Props) {
  const { holdings, yearlyDataForCharts, sectorAllocation, backtestStart } = data

  const handleExportHoldings = () => {
    if (!holdings || holdings.length === 0) return
    exportToCSV(
      holdings.map((h: any) => ({ rank: h.rank, symbol: h.symbol, company_name: h.company_name || "", sector: h.sector || "", rd_intensity: h.rd_intensity?.toFixed(2) || "", rd_alpha_score: h.rd_alpha_score?.toFixed(3) || "", momentum_score: h.momentum_score?.toFixed(3) || "", quality_score: h.quality_score?.toFixed(3) || "", weight: (h.weight * 100).toFixed(2) || "" })),
      `rd_etf_holdings_${asOfYear}_top${nHoldings}.csv`,
      [{ key: "rank", header: "Rank" }, { key: "symbol", header: "Symbol" }, { key: "company_name", header: "Company Name" }, { key: "sector", header: "Sector" }, { key: "rd_intensity", header: "R&D Intensity (%)" }, { key: "rd_alpha_score", header: "R&D Alpha Score" }, { key: "momentum_score", header: "Momentum Score" }, { key: "quality_score", header: "Quality Score" }, { key: "weight", header: "Portfolio Weight (%)" }]
    )
  }

  return (
    <>
      {/* Holdings Tab */}
      <TabsContent value="holdings" className="space-y-4">
        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>ETF{nHoldings} R&amp;D Alpha Selection <Badge variant="outline" className="ml-2">July {asOfYear}</Badge></CardTitle>
              <CardDescription>Point-in-time selection using FY{asOfYear - 1} R&amp;D intensity data</CardDescription>
            </div>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="sm" onClick={handleExportHoldings} disabled={!holdings || holdings.length === 0}>
                    <Download className="w-4 h-4 mr-2" />Export Holdings
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download current ETF holdings as CSV file</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </CardHeader>
          <CardContent>
            <div className="max-h-[600px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Symbol</TableHead><TableHead>Name</TableHead><TableHead>Sector</TableHead>
                    <TableHead className="text-right">Weight</TableHead><TableHead className="text-right">R&amp;D Intensity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(holdings || []).map((h: any, i: number) => (
                    <TableRow key={h.symbol} className="hover:bg-muted/50">
                      <TableCell className="text-muted-foreground font-mono">{i + 1}</TableCell>
                      <TableCell className="font-mono font-bold"><Link to={`/companies/${h.symbol}`} className="text-primary hover:underline">{h.symbol}</Link></TableCell>
                      <TableCell className="max-w-48 truncate text-foreground">{h.name}</TableCell>
                      <TableCell><Badge variant="outline" className="bg-muted/50">{h.sector}</Badge></TableCell>
                      <TableCell className="text-right font-mono">{h.weight.toFixed(1)}%</TableCell>
                      <TableCell className="text-right font-mono text-green-600 dark:text-green-400 font-semibold">{h.rd_intensity.toFixed(1)}%</TableCell>
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
            <CardTitle>ETF{nHoldings} vs S&amp;P 500 ({backtestStart}-{asOfYear})</CardTitle>
            <CardDescription>Year-over-year comparison of ETF{nHoldings} R&amp;D Alpha vs S&amp;P 500</CardDescription>
          </CardHeader>
          <CardContent style={{ height: 384, minHeight: 384 }}>
            {chartsReady && activeTab === "performance" && yearlyDataForCharts && yearlyDataForCharts.length > 0 ? (
            <SafeChart key={`perf-chart-${activeTab}`} height={384} minHeight={360} debounce={100}>
              <LineChart data={yearlyDataForCharts}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                <RechartsTooltip formatter={(value) => [`${(value as number)?.toFixed(1)}%`]} contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                <Legend />
                <Line type="monotone" dataKey="portfolio_return" name={`ETF${nHoldings} R&D Alpha`} stroke="#22c55e" strokeWidth={3} dot={{ fill: '#22c55e', strokeWidth: 2, r: 4 }} activeDot={{ r: 8 }} />
                <Line type="monotone" dataKey="sp500_return" name="S&P 500" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }} />
              </LineChart>
            </SafeChart>
            ) : (<div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>)}
          </CardContent>
        </Card>
        <Card className="border-border">
          <CardHeader>
            <CardTitle>Annual Excess Return (Alpha)</CardTitle>
            <CardDescription>ETF{nHoldings} outperformance vs S&amp;P 500 each year</CardDescription>
          </CardHeader>
          <CardContent style={{ height: 256, minHeight: 256 }}>
            {chartsReady && activeTab === "performance" && yearlyDataForCharts && yearlyDataForCharts.length > 0 ? (
            <SafeChart key={`alpha-chart-${activeTab}`} height={256} minHeight={240} debounce={100}>
              <BarChart data={yearlyDataForCharts}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
                <YAxis tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                <RechartsTooltip formatter={(value) => [`${(value as number)?.toFixed(1)}%`, "Excess vs S&P 500"]} contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                <Bar dataKey="excess_vs_sp500" name="Excess vs S&P 500" radius={[4, 4, 0, 0]}>
                  {(yearlyDataForCharts || []).map((entry: any, index: number) => (
                    <Cell key={index} fill={(entry.excess_vs_sp500 ?? 0) >= 0 ? "#22c55e" : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </SafeChart>
            ) : (<div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>)}
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
                  <Pie data={(sectorAllocation || []).map((s: any) => ({ name: s.sector, value: s.weight }))} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, value }) => `${name}: ${value}%`} labelLine={{ stroke: '#64748b' }}>
                    {(sectorAllocation || []).map((_: any, index: number) => (<Cell key={index} fill={SECTOR_COLORS[index % SECTOR_COLORS.length]} />))}
                  </Pie>
                  <RechartsTooltip formatter={(value) => [`${value}%`, "Weight"]} contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                </PieChart>
              </SafeChart>
              ) : (<div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>)}
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardHeader>
              <CardTitle>Sector Breakdown</CardTitle>
              <CardDescription>Detailed allocation by sector</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(sectorAllocation || []).map((s: any, i: number) => (
                  <div key={s.sector} className="flex items-center gap-4">
                    <div className="w-4 h-4 rounded-full flex-shrink-0" style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm font-medium text-foreground">{s.sector}</span>
                        <span className="font-mono text-sm text-foreground">{s.weight}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${s.weight}%`, backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </>
  )
}
