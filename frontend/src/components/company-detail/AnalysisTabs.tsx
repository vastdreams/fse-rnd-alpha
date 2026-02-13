/**
 * PATH: src/components/company-detail/AnalysisTabs.tsx
 * PURPOSE: R&D Analysis tab, Returns tab, and Price Chart tab content.
 * WHY: Extracted from CompanyDetail.tsx — three small tabs combined into one file.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area, BarChart, Bar } from "recharts"
import { SafeChart } from "@/components/SafeChart"

interface RDTabProps {
  company: any
  formatNumber: (num: number | null | undefined) => string
}

export function RDTab({ company, formatNumber }: RDTabProps) {
  return (
    <div className="space-y-4">
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
    </div>
  )
}

interface ReturnsTabProps {
  company: any
  formatPercent: (num: number | null | undefined) => string
}

export function ReturnsTab({ company, formatPercent }: ReturnsTabProps) {
  return (
    <div className="space-y-4">
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
              {company.annual_returns.slice(0, 15).map((row: any) => (
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
    </div>
  )
}

interface PriceChartTabProps {
  prices: any
}

export function PriceChartTab({ prices }: PriceChartTabProps) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Stock Price (5 Years, split-adjusted close)</CardTitle>
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
              <Area type="monotone" dataKey="close" stroke="#3b82f6" fill="url(#priceGradient)" strokeWidth={2} />
            </AreaChart>
          </SafeChart>
        </CardContent>
      </Card>
    </div>
  )
}
