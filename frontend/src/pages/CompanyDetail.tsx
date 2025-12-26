import { useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api, companyApi } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Building2, TrendingUp, FlaskConical, DollarSign, FileText, ExternalLink, MessageSquare, TrendingDown } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area, BarChart, Bar, Cell } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { Button } from "@/components/ui/button"

export function CompanyDetail() {
  const { ticker } = useParams<{ ticker: string }>()

  const { data: company, isLoading } = useQuery({
    queryKey: ["fmpCompany", ticker],
    queryFn: () => api.getFMPCompany(ticker!),
    enabled: !!ticker,
  })

  const { data: prices } = useQuery({
    queryKey: ["fmpPrices", ticker],
    queryFn: () => api.getFMPPrices(ticker!, 1260), // 5 years
    enabled: !!ticker,
  })

  const { data: annualReports } = useQuery({
    queryKey: ["annualReports", ticker],
    queryFn: () => companyApi.getAnnualReports(ticker!),
    enabled: !!ticker,
  })

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "..."
    if (Math.abs(num) >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
    if (Math.abs(num) >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
    if (Math.abs(num) >= 1e6) return `$${(num / 1e6).toFixed(0)}M`
    return `$${num.toLocaleString()}`
  }

  const formatPercent = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "..."
    return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading {ticker}...</div>
      </div>
    )
  }

  if (!company) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Company not found</div>
      </div>
    )
  }

  const latestIncome = company.income_statements[0]
  const latestBalance = company.balance_sheets[0]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{company.symbol}</h1>
            <Badge variant="outline" className="text-sm">{company.sector}</Badge>
          </div>
          <p className="text-muted-foreground">{company.name}</p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue (Latest)</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(latestIncome?.revenue)}</div>
            <p className="text-xs text-muted-foreground">FY {latestIncome?.fiscal_year}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Income</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(latestIncome?.net_income)}</div>
            <p className="text-xs text-muted-foreground">
              Margin: {latestIncome?.revenue && latestIncome?.net_income 
                ? ((latestIncome.net_income / latestIncome.revenue) * 100).toFixed(1) + '%' 
                : '-'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">R&D Expense</CardTitle>
            <FlaskConical className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(latestIncome?.rd_expenses)}</div>
            <p className="text-xs text-muted-foreground">
              Intensity: {company.rd_analysis.avg_rd_intensity.toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(latestBalance?.total_assets)}</div>
            <p className="text-xs text-muted-foreground">
              Equity: {formatNumber(latestBalance?.total_equity)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="financials" className="space-y-4">
        <TabsList className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
          <TabsTrigger value="financials">Financials</TabsTrigger>
          <TabsTrigger value="rd">R&D Analysis</TabsTrigger>
          <TabsTrigger value="returns">Returns</TabsTrigger>
          <TabsTrigger value="prices">Price Chart</TabsTrigger>
          <TabsTrigger value="annual-reports">
            <FileText className="h-4 w-4 mr-1" />
            Annual Reports
          </TabsTrigger>
        </TabsList>

        {/* Financials Tab */}
        <TabsContent value="financials" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Revenue & Income Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Revenue & Net Income</CardTitle>
              </CardHeader>
              <CardContent>
                <SafeChart height={300} minHeight={300}>
                  <BarChart data={[...company.income_statements].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="fiscal_year" stroke="#888" fontSize={12} />
                    <YAxis stroke="#888" fontSize={12} tickFormatter={(v) => `${(v / 1e9).toFixed(0)}B`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                      formatter={(value) => [formatNumber(value as number), '']}
                    />
                    <Bar dataKey="revenue" fill="#3b82f6" name="Revenue" />
                    <Bar dataKey="net_income" fill="#10b981" name="Net Income" />
                  </BarChart>
                </SafeChart>
              </CardContent>
            </Card>

            {/* Balance Sheet Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Assets vs Liabilities</CardTitle>
              </CardHeader>
              <CardContent>
                <SafeChart height={300} minHeight={300}>
                  <AreaChart data={[...company.balance_sheets].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="fiscal_year" stroke="#888" fontSize={12} />
                    <YAxis stroke="#888" fontSize={12} tickFormatter={(v) => `${(v / 1e9).toFixed(0)}B`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                      formatter={(value) => [formatNumber(value as number), '']}
                    />
                    <Area type="monotone" dataKey="total_assets" fill="#3b82f6" fillOpacity={0.3} stroke="#3b82f6" name="Assets" />
                    <Area type="monotone" dataKey="total_liabilities" fill="#ef4444" fillOpacity={0.3} stroke="#ef4444" name="Liabilities" />
                  </AreaChart>
                </SafeChart>
              </CardContent>
            </Card>
          </div>

          {/* Income Statement Table */}
          <Card>
            <CardHeader>
              <CardTitle>Income Statement History</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Year</TableHead>
                    <TableHead className="text-right">Revenue</TableHead>
                    <TableHead className="text-right">Gross Profit</TableHead>
                    <TableHead className="text-right">R&D</TableHead>
                    <TableHead className="text-right">Operating Inc</TableHead>
                    <TableHead className="text-right">Net Income</TableHead>
                    <TableHead className="text-right">EPS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {company.income_statements.slice(0, 10).map((row) => (
                    <TableRow key={row.fiscal_year}>
                      <TableCell className="font-medium">{row.fiscal_year}</TableCell>
                      <TableCell className="text-right font-mono">{formatNumber(row.revenue)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNumber(row.gross_profit)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNumber(row.rd_expenses)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNumber(row.operating_income)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNumber(row.net_income)}</TableCell>
                      <TableCell className="text-right font-mono">${row.eps?.toFixed(2) || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* R&D Tab */}
        <TabsContent value="rd" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Total R&D Spend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(company.rd_analysis.total_rd_spend)}</div>
                <p className="text-xs text-muted-foreground">{company.rd_analysis.years_with_rd} years of data</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Avg R&D Intensity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">{company.rd_analysis.avg_rd_intensity.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">R&D / Revenue ratio</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Latest R&D</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(company.rd_analysis.rd_by_year[0]?.rd_expense)}</div>
                <p className="text-xs text-muted-foreground">FY {company.rd_analysis.rd_by_year[0]?.year}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>R&D Intensity Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <SafeChart height={300} minHeight={300}>
                <LineChart data={[...company.rd_analysis.rd_by_year].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="year" stroke="#888" fontSize={12} />
                  <YAxis stroke="#888" fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                    formatter={(value) => [`${(value as number)?.toFixed(2)}%`, 'R&D Intensity']}
                  />
                  <Line type="monotone" dataKey="rd_intensity" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} />
                </LineChart>
              </SafeChart>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Returns Tab */}
        <TabsContent value="returns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Annual Returns & Volatility</CardTitle>
            </CardHeader>
            <CardContent>
              <SafeChart height={300} minHeight={300}>
                <BarChart data={[...company.annual_returns].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="year" stroke="#888" fontSize={12} />
                  <YAxis stroke="#888" fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                    formatter={(value) => [`${(value as number)?.toFixed(1)}%`, '']}
                  />
                  <Bar dataKey="annual_return" fill="#3b82f6" name="Return" />
                </BarChart>
              </SafeChart>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Returns History</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Year</TableHead>
                    <TableHead className="text-right">Annual Return</TableHead>
                    <TableHead className="text-right">Volatility</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {company.annual_returns.slice(0, 15).map((row) => (
                    <TableRow key={row.year}>
                      <TableCell className="font-medium">{row.year}</TableCell>
                      <TableCell className={`text-right font-mono ${row.annual_return && row.annual_return >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {formatPercent(row.annual_return)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {row.volatility ? `${row.volatility.toFixed(1)}%` : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Prices Tab */}
        <TabsContent value="prices" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Stock Price (5 Years)</CardTitle>
            </CardHeader>
            <CardContent>
              <SafeChart height={400} minHeight={400}>
                <AreaChart data={prices}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="date" stroke="#888" fontSize={12} tickFormatter={(v) => v.slice(0, 7)} />
                  <YAxis stroke="#888" fontSize={12} tickFormatter={(v) => `$${v}`} domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                    formatter={(value) => [`$${(value as number).toFixed(2)}`, 'Price']}
                    labelFormatter={(label) => `Date: ${label}`}
                  />
                  <Area type="monotone" dataKey="adj_close" stroke="#3b82f6" fill="url(#priceGradient)" strokeWidth={2} />
                </AreaChart>
              </SafeChart>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Annual Reports Tab */}
        <TabsContent value="annual-reports" className="space-y-4">
          {/* Check if we have annual reports data */}
          {(!annualReports?.filings || annualReports.filings.length === 0) ? (
            <Card className="bg-amber-500/10 border-amber-500/30">
              <CardContent className="py-8">
                <div className="text-center">
                  <FileText className="h-12 w-12 text-amber-500 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    No Annual Report Data Available
                  </h3>
                  <p className="text-muted-foreground max-w-lg mx-auto mb-4">
                    We don't have textual R&D analysis data for this company's SEC filings yet. 
                    This could be because:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 mb-6">
                    <li>• The company hasn't been processed in our annual report analysis pipeline</li>
                    <li>• The company reports minimal or no R&D activity</li>
                    <li>• Recent filings are still being analyzed</li>
                  </ul>
                  <div className="flex items-center justify-center gap-4">
                    <a 
                      href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=${company.name}&type=10-K&dateb=&owner=include&count=40`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                      View Filings on SEC EDGAR
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
          <>
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  Total Filings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-400">
                  {annualReports?.total_filings || 0}
                </div>
                <p className="text-xs text-muted-foreground">SEC 10-K filings</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-emerald-500" />
                  Total R&D Mentions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-400">
                  {annualReports?.rd_analysis_summary?.total_rd_mentions || 0}
                </div>
                <p className="text-xs text-muted-foreground">Across all filings</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  {(annualReports?.rd_analysis_summary?.avg_rd_tone || 0) >= 0 ? (
                    <TrendingUp className="h-4 w-4 text-purple-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-purple-500" />
                  )}
                  Avg R&D Tone
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${
                  (annualReports?.rd_analysis_summary?.avg_rd_tone || 0) >= 0 
                    ? 'text-emerald-400' 
                    : 'text-red-400'
                }`}>
                  {annualReports?.rd_analysis_summary?.avg_rd_tone?.toFixed(3) || "..."}
                </div>
                <p className="text-xs text-muted-foreground">Sentiment score</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-amber-500" />
                  R&D Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-400 capitalize">
                  {annualReports?.rd_analysis_summary?.trend || "..."}
                </div>
                <p className="text-xs text-muted-foreground">
                  {annualReports?.rd_analysis_summary?.years_with_rd_analysis || 0} years analyzed
                </p>
              </CardContent>
            </Card>
          </div>

          {/* R&D Mentions Chart */}
          {annualReports?.filings && annualReports.filings.some(f => f.rd_mentions) && (
            <Card>
              <CardHeader>
                <CardTitle>R&D Mentions by Year</CardTitle>
                <CardDescription>Number of R&D references in each annual report</CardDescription>
              </CardHeader>
              <CardContent>
                <SafeChart height={250} minHeight={250}>
                  <BarChart data={[...annualReports.filings].reverse().filter(f => f.rd_mentions)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="fiscal_year" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip
                      formatter={(value) => [value as number, "R&D Mentions"]}
                      contentStyle={{ backgroundColor: "hsl(222 47% 11%)", border: "1px solid hsl(215 20% 20%)", borderRadius: "8px" }}
                    />
                    <Bar dataKey="rd_mentions" radius={[4, 4, 0, 0]}>
                      {[...annualReports.filings].reverse().map((entry, index) => (
                        <Cell key={index} fill={entry.rd_tone_score && entry.rd_tone_score >= 0 ? "#22c55e" : "#ef4444"} />
                      ))}
                    </Bar>
                  </BarChart>
                </SafeChart>
              </CardContent>
            </Card>
          )}

          {/* Filings Table */}
          <Card>
            <CardHeader>
              <CardTitle>SEC 10-K Filing History</CardTitle>
              <CardDescription>
                Annual reports filed with the Securities and Exchange Commission
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Year</TableHead>
                    <TableHead>Filing Date</TableHead>
                    <TableHead>Form</TableHead>
                    <TableHead className="text-right">R&D Mentions</TableHead>
                    <TableHead className="text-right">Tone Score</TableHead>
                    <TableHead className="text-right">Size</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(annualReports?.filings || []).map((filing) => (
                    <TableRow key={filing.fiscal_year}>
                      <TableCell className="font-medium">{filing.fiscal_year}</TableCell>
                      <TableCell className="text-slate-500 dark:text-slate-400">
                        {filing.filing_date || "..."}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                          {filing.form_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {filing.rd_mentions ?? "..."}
                      </TableCell>
                      <TableCell className={`text-right font-mono ${
                        filing.rd_tone_score === null || filing.rd_tone_score === undefined
                          ? 'text-slate-500 dark:text-slate-400'
                          : filing.rd_tone_score >= 0 
                            ? 'text-emerald-600 dark:text-emerald-400' 
                            : 'text-red-600 dark:text-red-400'
                      }`}>
                        {filing.rd_tone_score?.toFixed(3) ?? "..."}
                      </TableCell>
                      <TableCell className="text-right text-slate-500 dark:text-slate-400">
                        {filing.file_size_mb ? `${filing.file_size_mb} MB` : "..."}
                      </TableCell>
                      <TableCell className="text-right">
                        {filing.sec_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                          >
                            <a 
                              href={filing.sec_url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              SEC
                            </a>
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
