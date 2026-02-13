/**
 * PATH: src/components/research/CompaniesTab.tsx
 * PURPOSE: Cohort companies table (with export) and sector distribution grid
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
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom"
import type { CohortCompany, CohortSummary } from "@/lib/api"

interface CompaniesTabProps {
  selectedWindow: string
  cohortCompanies: CohortCompany[] | undefined
  loadingCompanies: boolean
  cohortSummary: CohortSummary | undefined
  handleExportCohort: () => void
}

export function CompaniesTab({
  selectedWindow,
  cohortCompanies,
  loadingCompanies,
  cohortSummary,
  handleExportCohort,
}: CompaniesTabProps) {
  return (
    <>
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
    </>
  )
}
