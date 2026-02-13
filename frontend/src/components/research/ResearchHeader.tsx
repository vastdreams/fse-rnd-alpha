/**
 * PATH: src/components/research/ResearchHeader.tsx
 * PURPOSE: Page header, data-quality warning banner, and cohort summary cards
 * WHY: Extracted from Research.tsx to keep each file under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Building2, TrendingUp, FlaskConical, Calculator } from "lucide-react"
import { Link } from "react-router-dom"
import type { CohortSummary } from "@/lib/api"

interface ResearchHeaderProps {
  selectedWindow: string
  setSelectedWindow: (val: string) => void
  cohortSummary: CohortSummary | undefined
}

export function ResearchHeader({ selectedWindow, setSelectedWindow, cohortSummary }: ResearchHeaderProps) {
  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Research Analysis</h1>
          <p className="text-muted-foreground">
            {cohortSummary?.total_companies || "~500"}-Company Cohort • Rolling Window Analysis • Statistical Tests
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            <span className="font-medium">Sample:</span> 1995-{new Date().getFullYear() - 1} •{" "}
            <span className="font-medium">Methodology:</span> July-June returns (Fama-French convention) • cash-after-exit + delisting sensitivity • HAC standard errors
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
                <strong>Data tier:</strong> Tier-1 (FMP). Survivorship bias is substantially mitigated via historical constituents (where spans are available),
                cash-after-exit return construction, and delisting sensitivity scenarios; Tier-2 CRSP/Compustat remains the gold standard. 
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
    </>
  )
}
