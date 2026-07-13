/**
 * PATH: src/pages/CompanyDetail.tsx
 * PURPOSE: Company detail page — data fetching + tab shell.
 * WHY: Orchestrates sub-components; keeps hooks in parent per project convention.
 */

import { useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api, companyApi } from "@/lib/api"
import type { PnlEfficiencyScore } from "@/lib/api/types"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText, BarChart3 } from "lucide-react"
import {
  CompanyHeader,
  FinancialsTab,
  RDTab,
  ReturnsTab,
  PriceChartTab,
  AnnualReportsTab,
} from "@/components/company-detail"

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

  const { data: pnlScores } = useQuery({
    queryKey: ["pnlScore", ticker],
    queryFn: () => api.getPnlScores(undefined, 500),
    enabled: !!ticker,
  })

  const pnlScore = (pnlScores || []).find((s: PnlEfficiencyScore) => s.symbol === ticker)

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
      <CompanyHeader
        company={company}
        latestIncome={latestIncome}
        latestBalance={latestBalance}
        formatNumber={formatNumber}
      />

      <Tabs defaultValue="financials" className="space-y-4">
        <TabsList className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
          <TabsTrigger value="financials">Financials</TabsTrigger>
          <TabsTrigger value="rd">R&D Analysis</TabsTrigger>
          <TabsTrigger value="returns">Returns</TabsTrigger>
          <TabsTrigger value="prices">Price Chart</TabsTrigger>
          <TabsTrigger value="pnl-efficiency">
            <BarChart3 className="h-4 w-4 mr-1" />
            PNL Efficiency
          </TabsTrigger>
          <TabsTrigger value="annual-reports">
            <FileText className="h-4 w-4 mr-1" />
            Annual Reports
          </TabsTrigger>
        </TabsList>

        <TabsContent value="financials">
          <FinancialsTab company={company} formatNumber={formatNumber} />
        </TabsContent>

        <TabsContent value="rd">
          <RDTab company={company} formatNumber={formatNumber} />
        </TabsContent>

        <TabsContent value="returns">
          <ReturnsTab company={company} formatPercent={formatPercent} />
        </TabsContent>

        <TabsContent value="prices">
          <PriceChartTab prices={prices} />
        </TabsContent>

        <TabsContent value="pnl-efficiency">
          {pnlScore ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Gross Efficiency</p>
                  <p className="text-2xl font-bold">{(pnlScore.gross_efficiency * 100).toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Z-score: {pnlScore.gross_efficiency_z.toFixed(2)}</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Overhead Efficiency</p>
                  <p className="text-2xl font-bold">{(pnlScore.overhead_efficiency * 100).toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Z-score: {pnlScore.overhead_efficiency_z.toFixed(2)}</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Operating Efficiency</p>
                  <p className="text-2xl font-bold">{(pnlScore.operating_efficiency * 100).toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Z-score: {pnlScore.operating_efficiency_z.toFixed(2)}</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Profit Conversion</p>
                  <p className="text-2xl font-bold">{(pnlScore.profit_conversion * 100).toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Z-score: {pnlScore.profit_conversion_z.toFixed(2)}</p>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/5">
                  <p className="text-sm text-muted-foreground">Composite Score</p>
                  <p className={`text-3xl font-bold ${pnlScore.composite_z > 0 ? "text-green-500" : "text-red-500"}`}>{pnlScore.composite_z.toFixed(3)}</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Sector Percentile</p>
                  <p className="text-3xl font-bold">{pnlScore.sector_percentile.toFixed(0)}%</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Cross-Section Rank</p>
                  <p className="text-3xl font-bold">#{pnlScore.selection_rank}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground p-8 text-center">PNL efficiency data not available for this company.</p>
          )}
        </TabsContent>

        <TabsContent value="annual-reports">
          <AnnualReportsTab company={company} annualReports={annualReports} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
