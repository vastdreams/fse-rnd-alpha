/**
 * PATH: src/components/company-detail/FinancialsTab.tsx
 * PURPOSE: Financials tab with Revenue/Income chart, Balance Sheet chart, and Income Statement table.
 * WHY: Extracted from CompanyDetail.tsx to keep files under 300 lines.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area, BarChart, Bar } from "recharts"
import { SafeChart } from "@/components/SafeChart"

interface FinancialsTabProps {
  company: any
  formatNumber: (num: number | null | undefined) => string
}

export function FinancialsTab({ company, formatNumber }: FinancialsTabProps) {
  return (
    <div className="space-y-4">
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
              {company.income_statements.slice(0, 10).map((row: any) => (
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
    </div>
  )
}
