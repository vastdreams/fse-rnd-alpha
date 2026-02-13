/**
 * PATH: src/components/company-detail/AnnualReportsTab.tsx
 * PURPOSE: Annual Reports tab with empty state, summary cards, R&D mentions chart, and filings table.
 * WHY: Extracted from CompanyDetail.tsx to keep files under 300 lines.
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { FileText, ExternalLink, MessageSquare, TrendingUp, TrendingDown } from "lucide-react"
import { XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, Cell } from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { Button } from "@/components/ui/button"

interface AnnualReportsTabProps {
  company: any
  annualReports: any
  formatNumber: (num: number | null | undefined) => string
}

export function AnnualReportsTab({ company, annualReports, formatNumber }: AnnualReportsTabProps) {
  if (!annualReports?.filings || annualReports.filings.length === 0) {
    return (
      <div className="space-y-4">
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
      </div>
    )
  }

  return (
    <div className="space-y-4">
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
      {annualReports?.filings && annualReports.filings.some((f: any) => f.rd_mentions) && (
        <Card>
          <CardHeader>
            <CardTitle>R&D Mentions by Year</CardTitle>
            <CardDescription>Number of R&D references in each annual report</CardDescription>
          </CardHeader>
          <CardContent>
            <SafeChart height={250} minHeight={250}>
              <BarChart data={[...annualReports.filings].reverse().filter((f: any) => f.rd_mentions)}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="fiscal_year" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  formatter={(value) => [value as number, "R&D Mentions"]}
                  contentStyle={{ backgroundColor: "hsl(222 47% 11%)", border: "1px solid hsl(215 20% 20%)", borderRadius: "8px" }}
                />
                <Bar dataKey="rd_mentions" radius={[4, 4, 0, 0]}>
                  {[...annualReports.filings].reverse().map((entry: any, index: number) => (
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
              {(annualReports?.filings || []).map((filing: any) => (
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
    </div>
  )
}
