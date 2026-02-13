/**
 * PATH: frontend/src/components/paper3/Paper3ResultsCharts.tsx
 * PURPOSE: Chart visualizations (Annual Premium, Quintile Returns, Cumulative) for Paper 3 Results
 * WHY: Extracted from Paper3.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SafeChart } from "@/components/SafeChart"
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
  ReferenceLine,
  ComposedChart,
  Bar,
} from "recharts"

interface Paper3ResultsChartsProps {
  premiumData: any[]
  rdPremiumStats: any
  cumulativeData: any[]
}

export function Paper3ResultsCharts({ premiumData, rdPremiumStats, cumulativeData }: Paper3ResultsChartsProps) {
  return (
    <>
      {/* Annual Premium Chart */}
      <Card>
        <CardHeader>
          <CardTitle>5.1 Annual R&D Return Premium</CardTitle>
          <CardDescription>Q5 (High R&D) minus Q1 (Low R&D) returns by year</CardDescription>
        </CardHeader>
        <CardContent className="h-96">
          <SafeChart height={384} minHeight={300}>
            <ComposedChart data={premiumData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${v}%`} domain={['auto', 'auto']} />
              <RechartsTooltip
                formatter={(value) => [`${(value as number)?.toFixed(1)}%`]}
                contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
              />
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
              {typeof rdPremiumStats?.mean === "number" && (
                <ReferenceLine
                  y={rdPremiumStats.mean}
                  stroke="#8b5cf6"
                  strokeDasharray="5 5"
                  label={{ value: "Mean", fill: "#8b5cf6", fontSize: 11 }}
                />
              )}
              <Bar dataKey="rdPremium" name="R&D Premium" radius={[4, 4, 0, 0]}>
                {premiumData.map((entry, index) => (
                  <Cell key={index} fill={(entry.rdPremium || 0) >= 0 ? "#22c55e" : "#ef4444"} />
                ))}
              </Bar>
            </ComposedChart>
          </SafeChart>
        </CardContent>
      </Card>

      {/* Q1 vs Q5 Returns */}
      <Card>
        <CardHeader>
          <CardTitle>5.2 Quintile Returns Comparison</CardTitle>
          <CardDescription>Annual returns for Q1 (Low R&D) vs Q5 (High R&D)</CardDescription>
        </CardHeader>
        <CardContent className="h-80">
          <SafeChart height={320} minHeight={300}>
            <LineChart data={premiumData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${v}%`} />
              <RechartsTooltip
                formatter={(value) => [`${(value as number)?.toFixed(1)}%`]}
                contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
              />
              <Legend />
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
              <Line type="monotone" dataKey="q1" name="Q1 (Low R&D)" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="q5" name="Q5 (High R&D)" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </SafeChart>
        </CardContent>
      </Card>

      {/* Cumulative Returns */}
      <Card>
        <CardHeader>
          <CardTitle>5.3 Cumulative Portfolio Performance</CardTitle>
          <CardDescription>Growth of $1 invested in each quintile portfolio</CardDescription>
        </CardHeader>
        <CardContent className="h-96">
          <SafeChart height={384} minHeight={300}>
            <AreaChart data={cumulativeData}>
              <defs>
                <linearGradient id="q5Gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="q1Gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                tickFormatter={(v) => `$${(v as number).toFixed(2)}`}
              />
              <RechartsTooltip
                formatter={(value, name) => [`$${(value as number)?.toFixed(2)}`, name as string]}
                contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
              />
              <Legend />
              <Area type="monotone" dataKey="q5Cumulative" name="Q5 (High R&D)" stroke="#22c55e" fill="url(#q5Gradient)" strokeWidth={2} />
              <Area type="monotone" dataKey="q1Cumulative" name="Q1 (Low R&D)" stroke="#ef4444" fill="url(#q1Gradient)" strokeWidth={2} />
            </AreaChart>
          </SafeChart>
        </CardContent>
      </Card>
    </>
  )
}
