/**
 * PATH: src/pages/CompanyDetail.tsx
 * PURPOSE: Company detail page — data fetching + tab shell.
 * WHY: Orchestrates sub-components; keeps hooks in parent per project convention.
 */

import { useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api, companyApi } from "@/lib/api"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText } from "lucide-react"
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

        <TabsContent value="annual-reports">
          <AnnualReportsTab company={company} annualReports={annualReports} formatNumber={formatNumber} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
