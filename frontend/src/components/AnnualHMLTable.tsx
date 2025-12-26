/**
 * PATH: frontend/src/components/AnnualHMLTable.tsx
 * PURPOSE:
 *   - Display annual non-overlapping HML (High-Minus-Low) R&D premium
 *   - Primary inference table for publication (no HAC adjustment needed)
 *   - Shows year-by-year Q5-Q1 return premium
 *
 * PUBLICATION FIX (Dec 2025):
 *   - This is the PRIMARY result table for academic papers
 *   - Non-overlapping observations = standard inference is valid
 *   - Backend reports Newey-West (lag=1) as a conservative default for the annual series
 *   - Rolling windows should be presented as DESCRIPTIVE only
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TrendingUp, TrendingDown, Minus, AlertCircle, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

// Match the actual API response type from api.ts
interface AnnualPremiumRow {
  year: string
  formation_year?: number
  q1_return: number
  q5_return: number
  hml_premium: number
}

interface AnnualHMLTableProps {
  data?: {
    annual_premiums: AnnualPremiumRow[]
    n_years: number
    mean_premium: number
    std_dev: number
    min_premium: number
    max_premium: number
    positive_years: number
    win_rate: number
    hac_adjusted?: {
      mean: number
      nw_std_error: number
      t_statistic: number
      p_value: number
    }
  }
  isLoading?: boolean
  /** Optional override for the main header title (useful when embedding inside numbered manuscripts). */
  title?: string
  /** Optional override for the header description. */
  description?: string
}

export function AnnualHMLTable({ data, isLoading, title, description }: AnnualHMLTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title ? `Loading: ${title}` : "Loading Annual HML Premium..."}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-pulse text-muted-foreground">Loading data...</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title || "Annual HML Premium"}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  const { annual_premiums } = data
  const t_statistic =
    data.hac_adjusted?.t_statistic ??
    (data.n_years > 1 ? data.mean_premium / (data.std_dev / Math.sqrt(data.n_years)) : undefined)
  const p_value = data.hac_adjusted?.p_value
  const isSignificant = p_value !== undefined ? p_value < 0.05 : false

  return (
    <div className="space-y-6">
      {/* Header Card with Key Statistics */}
      <Card className="border-2 border-primary/20 bg-primary/5">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                {title || "Primary Result: Annual HML R&D Premium"}
              </CardTitle>
              <CardDescription className="mt-1">
                {description || "Non-overlapping annual observations (standard inference valid)"}
              </CardDescription>
            </div>
            <Badge variant={isSignificant ? "default" : "secondary"} className="text-sm">
              {isSignificant ? "Statistically Significant" : "Not Significant"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-background border">
              <div className="text-sm text-muted-foreground">Mean Annual Premium</div>
              <div className={cn(
                "text-2xl font-bold",
                data.mean_premium > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
              )}>
                {data.mean_premium > 0 ? "+" : ""}{data.mean_premium?.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 rounded-lg bg-background border">
              <div className="text-sm text-muted-foreground">t-Statistic</div>
              <div className="text-2xl font-bold">
                {t_statistic !== undefined ? t_statistic.toFixed(2) : "..."}
              </div>
              <div className="text-xs text-muted-foreground">
                {data.hac_adjusted ? "Newey-West (lag=1)" : "Non-overlapping"}
              </div>
            </div>
            <div className="p-4 rounded-lg bg-background border">
              <div className="text-sm text-muted-foreground">p-Value</div>
              <div className={cn(
                "text-2xl font-bold",
                p_value !== undefined && p_value < 0.05 ? "text-emerald-600 dark:text-emerald-400" : "text-orange-600"
              )}>
                {p_value === undefined ? "..." : p_value < 0.001 ? "<0.001" : p_value.toFixed(4)}
              </div>
            </div>
            <div className="p-4 rounded-lg bg-background border">
              <div className="text-sm text-muted-foreground">Win Rate</div>
              <div className="text-2xl font-bold">
                {((data.win_rate || 0) * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted-foreground">
                ({data.positive_years}/{data.n_years} years positive)
              </div>
            </div>
          </div>

          {/* Methodology Note */}
          <div className="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 text-blue-600 dark:text-blue-400" />
              <div className="text-sm text-blue-800 dark:text-blue-300">
                <strong>Note on Inference:</strong> This table uses non-overlapping annual observations 
                (one premium per year). The backend reports Newey-West (lag=1) for the annual series as a conservative default.
                Rolling window results are descriptive; overlapping windows require HAC adjustments for inference.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Year-by-Year Table */}
      <Card>
        <CardHeader>
          <CardTitle>Year-by-Year Premium (Q5 - Q1)</CardTitle>
          <CardDescription>
            Annual return premium for high R&D quintile vs low R&D quintile
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-44">Return Period</TableHead>
                  <TableHead className="text-right">Q5 Return</TableHead>
                  <TableHead className="text-right">Q1 Return</TableHead>
                  <TableHead className="text-right">Premium</TableHead>
                  <TableHead className="text-center w-16">Direction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {annual_premiums?.slice().reverse().map((row) => (
                  <TableRow key={row.year}>
                    <TableCell className="font-medium">
                      <div className="space-y-0.5">
                        <div>{row.year}</div>
                        {row.formation_year !== undefined && (
                          <div className="text-[10px] text-muted-foreground">
                            Formation FY: {row.formation_year}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className={cn(
                      "text-right",
                      row.q5_return > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                    )}>
                      {row.q5_return > 0 ? "+" : ""}{row.q5_return?.toFixed(2)}%
                    </TableCell>
                    <TableCell className={cn(
                      "text-right",
                      row.q1_return > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                    )}>
                      {row.q1_return > 0 ? "+" : ""}{row.q1_return?.toFixed(2)}%
                    </TableCell>
                    <TableCell className={cn(
                      "text-right font-semibold",
                      row.hml_premium > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                    )}>
                      {row.hml_premium > 0 ? "+" : ""}{row.hml_premium?.toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-center">
                      {row.hml_premium > 1 ? (
                        <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mx-auto" />
                      ) : row.hml_premium < -1 ? (
                        <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400 mx-auto" />
                      ) : (
                        <Minus className="h-4 w-4 text-muted-foreground mx-auto" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

