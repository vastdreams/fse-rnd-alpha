/**
 * PATH: src/components/company-detail/CompanyHeader.tsx
 * PURPOSE: Company header with name/sector badge + 4 key metric cards.
 * WHY: Extracted from CompanyDetail.tsx to keep files under 300 lines.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Building2, TrendingUp, FlaskConical, DollarSign } from "lucide-react"

interface CompanyHeaderProps {
  company: any
  latestIncome: any
  latestBalance: any
  formatNumber: (num: number | null | undefined) => string
}

export function CompanyHeader({ company, latestIncome, latestBalance, formatNumber }: CompanyHeaderProps) {
  return (
    <>
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
    </>
  )
}
