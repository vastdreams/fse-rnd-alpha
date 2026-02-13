/**
 * PATH: src/components/research/FactorPremiumTab.tsx
 * PURPOSE: Annual R&D factor premium line chart and quintile-returns-over-time line chart
 * WHY: Extracted from Research.tsx to keep each file under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts"
import { SafeChart } from "@/components/SafeChart"
import { QUINTILE_COLORS } from "@/hooks/useResearchData"
import type { FactorPremiumItem } from "@/lib/api"

interface FactorPremiumTabProps {
  chartsReady: boolean
  factorPremiums: FactorPremiumItem[]
}

export function FactorPremiumTab({ chartsReady, factorPremiums }: FactorPremiumTabProps) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Annual R&D Factor Premium</CardTitle>
          <CardDescription>
            Year-over-year premium of high R&D stocks over low R&D stocks
          </CardDescription>
        </CardHeader>
        <CardContent style={{ height: 384, minHeight: 384 }}>
          {chartsReady && factorPremiums && factorPremiums.length > 0 ? (
            <SafeChart height={384} minHeight={360} debounce={50}>
              <LineChart data={factorPremiums || []}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="year" className="text-xs" />
                <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                <Tooltip
                  formatter={(value, name) => [`${(value as number)?.toFixed(2)}%`, name as string]}
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                />
                <Legend />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" />
                <Line type="monotone" dataKey="rd_premium" name="R&D Premium (Annual %)" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="q5_return" name="Q5 High R&D (Annual %)" stroke="#22c55e" strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="q1_return" name="Q1 Low R&D (Annual %)" stroke="#ef4444" strokeWidth={1} dot={false} />
              </LineChart>
            </SafeChart>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
          )}
        </CardContent>
      </Card>

      {/* Quintile Returns Over Time */}
      <Card>
        <CardHeader>
          <CardTitle>Quintile Returns by Year</CardTitle>
        </CardHeader>
        <CardContent style={{ height: 320, minHeight: 320 }}>
          {chartsReady && factorPremiums && factorPremiums.length > 0 ? (
            <SafeChart height={320} minHeight={300} debounce={50}>
              <LineChart data={factorPremiums || []}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="year" className="text-xs" />
                <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                <Tooltip
                  formatter={(value, name) => [`${(value as number)?.toFixed(2)}%`, name as string]}
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                />
                <Legend />
                <Line type="monotone" dataKey="q1_return" name="Q1 (Annual %)" stroke={QUINTILE_COLORS[0]} strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="q2_return" name="Q2 (Annual %)" stroke={QUINTILE_COLORS[1]} strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="q3_return" name="Q3 (Annual %)" stroke={QUINTILE_COLORS[2]} strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="q4_return" name="Q4 (Annual %)" stroke={QUINTILE_COLORS[3]} strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="q5_return" name="Q5 (Annual %)" stroke={QUINTILE_COLORS[4]} strokeWidth={1} dot={false} />
              </LineChart>
            </SafeChart>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">Loading...</div>
          )}
        </CardContent>
      </Card>
    </>
  )
}
