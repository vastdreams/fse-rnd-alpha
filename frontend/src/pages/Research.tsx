import { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ReferenceLine,
} from "recharts"
import { Building2, TrendingUp, FlaskConical, CheckCircle, XCircle, Calculator, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { exportToCSV } from "@/lib/export"
import { Link } from "react-router-dom"
import { SafeChart } from "@/components/SafeChart"

// Colors for quintiles that work in both light and dark modes
const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#2563eb"]

export function Research() {
  const [selectedWindow, setSelectedWindow] = useState<string>("5yr")
  const [chartsReady, setChartsReady] = useState(false)
  const [activeTab, setActiveTab] = useState("quintiles")
  
  // Delay chart rendering to ensure container dimensions are calculated
  // Reset and delay when tab changes to prevent -1 dimension errors
  useEffect(() => {
    setChartsReady(false)
    const timer = setTimeout(() => setChartsReady(true), 150)
    return () => clearTimeout(timer)
  }, [activeTab])

  // Queries
  const { data: cohortSummary, isLoading: loadingSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: api.getCohortSummary,
  })

  const { data: quintilePerf, isLoading: loadingQuintile } = useQuery({
    queryKey: ["quintilePerf", selectedWindow],
    queryFn: () => api.getQuintilePerformance(selectedWindow),
  })

  const { data: factorPremiumsRaw, isLoading: loadingPremiums } = useQuery({
    queryKey: ["factorPremiums"],
    queryFn: api.getFactorPremiums,
  })

  // Filter out current year (incomplete data)
  const factorPremiums = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return (factorPremiumsRaw || []).filter((f: any) => f.year < currentYear)
  }, [factorPremiumsRaw])

  const { data: aggregateAnova, isLoading: loadingAnova } = useQuery({
    queryKey: ["aggregateAnova"],
    queryFn: api.getAggregateAnova,
  })

  const { data: cohortCompanies, isLoading: loadingCompanies } = useQuery({
    queryKey: ["cohort500", selectedWindow],
    queryFn: () => api.getCohort500(selectedWindow),
  })

  const { data: rollingWindows } = useQuery({
    queryKey: ["rollingWindows", selectedWindow],
    queryFn: () => api.getRollingWindows(selectedWindow),
  })

  const formatPercent = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "..."
    return `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`
  }

  // Export cohort companies to CSV
  const handleExportCohort = () => {
    if (!cohortCompanies || cohortCompanies.length === 0) return
    
    exportToCSV(
      cohortCompanies.map((c) => ({
        symbol: c.symbol,
        name: c.name || "",
        sector: c.sector || "",
        avg_rd_intensity: c.avg_rd_intensity?.toFixed(2) || "",
        rd_profile: c.rd_profile || "",
        data_quality_score: c.data_quality_score?.toFixed(2) || "",
        years_with_data: c.years_with_data || 0,
      })),
      `research_cohort_${selectedWindow}_${new Date().toISOString().split("T")[0]}.csv`,
      [
        { key: "symbol", header: "Symbol" },
        { key: "name", header: "Company Name" },
        { key: "sector", header: "Sector" },
        { key: "avg_rd_intensity", header: "Avg R&D Intensity (%)" },
        { key: "rd_profile", header: "R&D Profile" },
        { key: "data_quality_score", header: "Data Quality Score" },
        { key: "years_with_data", header: "Years with Data" },
      ]
    )
  }

  // Export quintile performance to CSV
  const handleExportQuintiles = () => {
    if (!quintilePerf || quintilePerf.length === 0) return
    
    exportToCSV(
      quintilePerf.map((q: { label: string; avg_rd_intensity?: number; avg_return?: number; volatility?: number; sharpe?: number; num_companies?: number }) => ({
        quintile: q.label,
        avg_rd_intensity: q.avg_rd_intensity?.toFixed(2) || "",
        avg_return: q.avg_return?.toFixed(2) || "",
        volatility: q.volatility?.toFixed(2) || "",
        sharpe: q.sharpe?.toFixed(3) || "",
        num_companies: q.num_companies || 0,
      })),
      `quintile_performance_${selectedWindow}_${new Date().toISOString().split("T")[0]}.csv`,
      [
        { key: "quintile", header: "Quintile" },
        { key: "avg_rd_intensity", header: "Avg R&D Intensity (%)" },
        { key: "avg_return", header: "Avg Return (%)" },
        { key: "volatility", header: "Volatility (%)" },
        { key: "sharpe", header: "Sharpe Ratio" },
        { key: "num_companies", header: "# Companies" },
      ]
    )
  }

  const formatPValue = (p: number | null | undefined) => {
    if (p === null || p === undefined) return "..."
    if (p < 0.001) return "<0.001***"
    if (p < 0.01) return `${p.toFixed(3)}**`
    if (p < 0.05) return `${p.toFixed(3)}*`
    return p.toFixed(3)
  }

  const isLoading = loadingSummary || loadingQuintile || loadingPremiums || loadingAnova

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading research data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Research Analysis</h1>
          <p className="text-muted-foreground">
            {cohortSummary?.total_companies || "~500"}-Company Cohort • Rolling Window Analysis • Statistical Tests
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            <span className="font-medium">Sample:</span> 1995-{new Date().getFullYear() - 1} •{" "}
            <span className="font-medium">Methodology:</span> July-June returns (Fama-French convention) • Delisting-adjusted • HAC standard errors
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={selectedWindow} onValueChange={setSelectedWindow}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5yr">5-Year</SelectItem>
              <SelectItem value="10yr">10-Year</SelectItem>
              <SelectItem value="20yr">20-Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Data Quality Warning Banner */}
      <Card className="bg-amber-500/10 border-amber-500/30">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-start gap-3">
            <div className="text-amber-500 mt-0.5">⚠️</div>
            <div className="space-y-1 text-sm">
              <p className="font-semibold text-amber-600 dark:text-amber-400">Research Caveats & Limitations</p>
              <p className="text-muted-foreground">
                <strong>Data tier:</strong> Tier-1 (FMP). Survivorship bias is substantially mitigated via historical constituents
                and delisting return adjustments, but Tier-2 CRSP/Compustat remains the gold standard. 
                <strong> Overlapping windows:</strong> Rolling observations are correlated; overlapping-window inference requires HAC adjustments. 
                <strong> Sector concentration:</strong> Q5 is dominated by Tech/Healthcare. 
                <Link to="/documentation" className="text-amber-600 dark:text-amber-400 hover:underline ml-1">
                  Read full methodology →
                </Link>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cohort Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cohort</CardTitle>
            <Building2 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cohortSummary?.total_companies || 0}</div>
            <p className="text-xs text-muted-foreground">S&P 500 companies</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">5-Year Window</CardTitle>
            <FlaskConical className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cohortSummary?.eligible_5yr || 0}</div>
            <p className="text-xs text-muted-foreground">eligible companies</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">10-Year Window</CardTitle>
            <TrendingUp className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cohortSummary?.eligible_10yr || 0}</div>
            <p className="text-xs text-muted-foreground">eligible companies</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">20-Year Window</CardTitle>
            <Calculator className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cohortSummary?.eligible_20yr || 0}</div>
            <p className="text-xs text-muted-foreground">eligible companies</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Analysis Views */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1 bg-muted/50 p-1">
          <TabsTrigger value="quintiles" className="flex-1 min-w-[120px]">Quintile Analysis</TabsTrigger>
          <TabsTrigger value="premium" className="flex-1 min-w-[120px]">Factor Premium</TabsTrigger>
          <TabsTrigger value="anova" className="flex-1 min-w-[120px]">ANOVA Results</TabsTrigger>
          <TabsTrigger value="companies" className="flex-1 min-w-[120px]">Cohort Companies</TabsTrigger>
          <TabsTrigger value="papers" className="flex-1 min-w-[80px]">Papers</TabsTrigger>
          <TabsTrigger value="methodology" className="flex-1 min-w-[100px]">Methodology</TabsTrigger>
        </TabsList>

        {/* Quintile Analysis Tab */}
        <TabsContent value="quintiles" className="space-y-4">
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
        </TabsContent>

        {/* Factor Premium Tab */}
        <TabsContent value="premium" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Annual R&D Factor Premium</CardTitle>
              <CardDescription>
                Year-over-year premium of high R&D stocks over low R&D stocks
              </CardDescription>
            </CardHeader>
            <CardContent style={{ height: 384, minHeight: 384 }}>
              {chartsReady && factorPremiums && factorPremiums.length > 0 ? (
                <SafeChart height={384} minHeight={360} debounce={50}>
                  <LineChart data={factorPremiums || []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="year" className="text-xs" />
                    <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                    <Tooltip
                      formatter={(value, name) => [`${(value as number)?.toFixed(2)}%`, name as string]}
                      contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                    />
                    <Legend />
                    <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" />
                    <Line type="monotone" dataKey="rd_premium" name="R&D Premium (Annual %)" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="q5_return" name="Q5 High R&D (Annual %)" stroke="#22c55e" strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="q1_return" name="Q1 Low R&D (Annual %)" stroke="#ef4444" strokeWidth={1} dot={false} />
                  </LineChart>
                </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
              )}
            </CardContent>
          </Card>

          {/* Quintile Returns Over Time */}
          <Card>
            <CardHeader>
              <CardTitle>Quintile Returns by Year</CardTitle>
            </CardHeader>
            <CardContent style={{ height: 320, minHeight: 320 }}>
              {chartsReady && factorPremiums && factorPremiums.length > 0 ? (
                <SafeChart height={320} minHeight={300} debounce={50}>
                  <LineChart data={factorPremiums || []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="year" className="text-xs" />
                    <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                    <Tooltip
                      formatter={(value, name) => [`${(value as number)?.toFixed(2)}%`, name as string]}
                      contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="q1_return" name="Q1 (Annual %)" stroke={QUINTILE_COLORS[0]} strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="q2_return" name="Q2 (Annual %)" stroke={QUINTILE_COLORS[1]} strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="q3_return" name="Q3 (Annual %)" stroke={QUINTILE_COLORS[2]} strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="q4_return" name="Q4 (Annual %)" stroke={QUINTILE_COLORS[3]} strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="q5_return" name="Q5 (Annual %)" stroke={QUINTILE_COLORS[4]} strokeWidth={1} dot={false} />
                  </LineChart>
                </SafeChart>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ANOVA Results Tab */}
        <TabsContent value="anova" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {["5yr", "10yr", "20yr"].map((windowType) => {
              const anova = aggregateAnova?.[windowType]
              return (
                <Card key={windowType}>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      {windowType} Window
                      {anova?.anova?.significant_005 ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                    </CardTitle>
                    <CardDescription>
                      {anova?.n_windows || 0} rolling windows analyzed
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">ANOVA Test</h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="text-muted-foreground">F-statistic</div>
                        <div className="text-right font-mono">{anova?.anova?.f_statistic?.toFixed(2) || "..."}</div>
                        <div className="text-muted-foreground">p-value</div>
                        <div className="text-right font-mono">{formatPValue(anova?.anova?.p_value)}</div>
                        <div className="text-muted-foreground">η² (effect)</div>
                        <div className="text-right font-mono">{anova?.anova?.eta_squared?.toFixed(3) || "..."}</div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">T-Test (High vs Low)</h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="text-muted-foreground">t-statistic</div>
                        <div className="text-right font-mono">{anova?.ttest_high_vs_low?.t_statistic?.toFixed(2) || "..."}</div>
                        <div className="text-muted-foreground">p-value</div>
                        <div className="text-right font-mono">{formatPValue(anova?.ttest_high_vs_low?.p_value)}</div>
                        <div className="text-muted-foreground">Mean diff</div>
                        <div className="text-right font-mono">{formatPercent(anova?.ttest_high_vs_low?.mean_difference)}</div>
                        <div className="text-muted-foreground">Cohen's d</div>
                        <div className="text-right font-mono">{anova?.ttest_high_vs_low?.cohens_d?.toFixed(3) || "..."}</div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">Quintile Means</h4>
                      <div className="flex justify-between text-sm">
                        {Object.entries(anova?.quintile_means || {}).map(([q, mean]) => (
                          <div key={q} className="text-center">
                            <div className="text-muted-foreground text-xs">{q}</div>
                            <div className="font-mono">{(mean as number)?.toFixed(1)}%</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Publication Summary */}
          <Card className="overflow-hidden">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">Publication Summary</CardTitle>
              <CardDescription>Key findings for research paper</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left py-4 px-6 font-semibold text-foreground min-w-[200px]">Metric</th>
                      <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">5-Year</th>
                      <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">10-Year</th>
                      <th className="text-center py-4 px-6 font-semibold text-foreground w-[120px]">20-Year</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                      <td className="py-5 px-6 font-medium text-foreground">R&D Premium (Q5-Q1)</td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                          {formatPercent(aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference)}
                        </span>
                      </td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                          {formatPercent(aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference)}
                        </span>
                      </td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                          {formatPercent(aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference)}
                        </span>
                      </td>
                    </tr>
                    <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                      <td className="py-5 px-6 font-medium text-foreground">Statistical Significance</td>
                      <td className="py-5 px-6 text-center">
                        {aggregateAnova?.["5yr"]?.anova?.significant_005 ? (
                          <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                        ) : (
                          <Badge variant="secondary" className="px-3 py-1">No</Badge>
                        )}
                      </td>
                      <td className="py-5 px-6 text-center">
                        {aggregateAnova?.["10yr"]?.anova?.significant_005 ? (
                          <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                        ) : (
                          <Badge variant="secondary" className="px-3 py-1">No</Badge>
                        )}
                      </td>
                      <td className="py-5 px-6 text-center">
                        {aggregateAnova?.["20yr"]?.anova?.significant_005 ? (
                          <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 px-3 py-1">Yes</Badge>
                        ) : (
                          <Badge variant="secondary" className="px-3 py-1">No</Badge>
                        )}
                      </td>
                    </tr>
                    <tr className="hover:bg-muted/20 transition-colors">
                      <td className="py-5 px-6 font-medium text-foreground">Effect Size (η²)</td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg text-muted-foreground">
                          {aggregateAnova?.["5yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                        </span>
                      </td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg text-muted-foreground">
                          {aggregateAnova?.["10yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                        </span>
                      </td>
                      <td className="py-5 px-6 text-center">
                        <span className="font-mono text-lg text-muted-foreground">
                          {aggregateAnova?.["20yr"]?.anova?.eta_squared?.toFixed(3) || "..."}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Companies Tab */}
        <TabsContent value="companies" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Cohort Companies ({selectedWindow} Window)</CardTitle>
                <CardDescription>
                  {loadingCompanies ? "Loading..." : `${cohortCompanies?.length || 0} companies eligible`}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCohort}
                disabled={!cohortCompanies || cohortCompanies.length === 0}
              >
                <Download className="w-4 h-4 mr-2" />
                Export Cohort
              </Button>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                      <TableHead>Symbol</TableHead>
                    <TableHead>Name</TableHead>
                      <TableHead>Sector</TableHead>
                      <TableHead className="text-right">Years</TableHead>
                      <TableHead className="text-right">R&D %</TableHead>
                      <TableHead>Profile</TableHead>
                      <TableHead className="text-right">Quality</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                    {(cohortCompanies || []).slice(0, 100).map((c) => (
                      <TableRow key={c.symbol} className="cursor-pointer hover:bg-muted/50">
                        <TableCell className="font-mono font-medium">
                          <Link to={`/companies/${c.symbol}`} className="text-primary hover:underline">
                            {c.symbol}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-48 truncate">{c.name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{c.sector}</TableCell>
                        <TableCell className="text-right">{c.years_with_rd}</TableCell>
                        <TableCell className="text-right font-mono">
                          {c.avg_rd_intensity?.toFixed(1)}%
                      </TableCell>
                      <TableCell>
                          <Badge variant={
                            c.rd_profile === "High" ? "default" :
                            c.rd_profile === "Medium" ? "secondary" : "outline"
                          }>
                            {c.rd_profile}
                        </Badge>
                      </TableCell>
                        <TableCell className="text-right">{c.data_quality_score?.toFixed(0)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
            </CardContent>
          </Card>

          {/* Sector Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Sector Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-4">
                {(cohortSummary?.by_sector || []).map((s) => (
                  <div key={s.sector} className="flex items-center justify-between p-2 border rounded">
                    <span className="text-sm truncate">{s.sector || "Unknown"}</span>
                    <Badge variant="secondary">{s.total}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Papers Tab */}
        <TabsContent value="papers" className="space-y-4">
          <Card>
            <CardHeader>
                <CardTitle>Main Paper & Sub-Research</CardTitle>
                <CardDescription>Website manuscript plus supporting deep dives (all results sourced from the API)</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <Link to="/papers/main">
                    <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <CardHeader>
                        <CardTitle className="text-lg">Main Paper: R&D Investment Intensity and Long-Term Stock Returns</CardTitle>
                        <CardDescription>Consolidated manuscript + investable strategy + frozen publication snapshot</CardDescription>
                      </CardHeader>
                    </Card>
                  </Link>
                  <Link to="/papers/1">
                    <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <CardHeader>
                        <CardTitle className="text-lg">Sub-Research 1: Returns & Inference</CardTitle>
                        <CardDescription>Core return premium results and inference visuals</CardDescription>
                      </CardHeader>
                    </Card>
                  </Link>
                  <Link to="/papers/2">
                    <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <CardHeader>
                        <CardTitle className="text-lg">Sub-Research 2: Sector Patterns</CardTitle>
                        <CardDescription>Cross-sector analysis of R&D investment patterns</CardDescription>
                      </CardHeader>
                    </Card>
                  </Link>
                  <Link to="/papers/3">
                    <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <CardHeader>
                        <CardTitle className="text-lg">Sub-Research 3: Factor Tests</CardTitle>
                        <CardDescription>Multi-factor analysis and portfolio construction</CardDescription>
                      </CardHeader>
                    </Card>
                  </Link>
                  <Link to="/papers/4">
                    <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <CardHeader>
                        <CardTitle className="text-lg">Sub-Research 4: Mechanisms (Qualitative)</CardTitle>
                        <CardDescription>R&D investment beyond stock price returns</CardDescription>
                      </CardHeader>
                    </Card>
                  </Link>
                </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Methodology Tab */}
        <TabsContent value="methodology" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Methodology</CardTitle>
              <CardDescription>Bias mitigation, data tier disclosure, and replication guidance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>
                The platform’s publication-grade methodology is documented on the dedicated Methodology page and in the
                Papers & Documentation hub.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link to="/methodology" className="underline hover:no-underline">
                  Open Methodology →
                </Link>
                <Link to="/documentation" className="underline hover:no-underline">
                  Papers & Documentation →
                </Link>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>
    </div>
  )
}

