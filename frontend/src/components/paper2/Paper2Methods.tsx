/**
 * PATH: frontend/src/components/paper2/Paper2Methods.tsx
 * FILE_ID: PAPER2-METHODS-001
 * PURPOSE: Data & Sample and Methodology sections for Paper2
 * WHY: Extracted from Paper2.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - @/components/ui/*: UI primitives
 * - recharts: chart components
 * - @/components/SafeChart: chart wrapper
 * - @/components/Formula: formula rendering
 * - lucide-react: icons
 */

import { Card, CardContent, CardTitle } from "@/components/ui/card"
import { SafeChart } from "@/components/SafeChart"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts"
import { Database, FlaskConical } from "lucide-react"
import { Formulas } from "@/components/Formula"

interface Paper2MethodsProps {
  cohortSummary: any
  sectorData: any[]
  sectorCoverageData: any[]
  rdSampleYearRange: string | undefined
}

export function Paper2Methods({
  cohortSummary,
  sectorData,
  sectorCoverageData,
  rdSampleYearRange,
}: Paper2MethodsProps) {
  return (
    <>
      {/* Data & Sample */}
      <section id="data" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">3. Data & Sample</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground">
                Our sample comprises {cohortSummary?.total_companies || "..."} S&P 500 companies 
                classified into {sectorData.length} GICS sectors. We collect annual R&D expenditure 
                and revenue data from company financial statements for the period {rdSampleYearRange || "shown above"}.
              </p>
            </div>

            {/* Data Coverage Chart */}
            <div className="h-[400px]">
              <CardTitle className="text-lg mb-4">Long-Term Data Coverage by Sector</CardTitle>
              <SafeChart height={400} minHeight={300}>
                <BarChart data={sectorCoverageData.sort((a: any, b: any) => b.coverage_20yr - a.coverage_20yr)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} stroke="hsl(var(--muted-foreground))" />
                  <YAxis type="category" dataKey="sector" stroke="hsl(var(--muted-foreground))" width={130} tick={{ fontSize: 11 }} />
                  <RechartsTooltip
                    formatter={(value) => [`${value}%`, "Coverage"]}
                    contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                  />
                  <Legend />
                  <Bar dataKey="coverage_5yr" name="5-Year" fill="#3b82f6" radius={[0, 2, 2, 0]} />
                  <Bar dataKey="coverage_10yr" name="10-Year" fill="#8b5cf6" radius={[0, 2, 2, 0]} />
                  <Bar dataKey="coverage_20yr" name="20-Year" fill="#22c55e" radius={[0, 2, 2, 0]} />
                </BarChart>
              </SafeChart>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Methodology */}
      <section id="methodology" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <FlaskConical className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">4. Methodology</h2>
        </div>
        <Card>
          <CardContent className="pt-6 max-w-none space-y-6">
            <div>
              <h4 className="text-foreground font-semibold mb-2">4.1 Sector Classification</h4>
              <p className="text-muted-foreground">
                We use the Global Industry Classification Standard (GICS) to categorize companies 
                into 11 sectors. GICS is jointly developed by MSCI and S&P and is the industry 
                standard for sector classification.
              </p>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.2 R&D Intensity Calculation</h4>
              <p className="text-muted-foreground mb-2">R&D intensity is calculated as:</p>
              <Formulas.RDIntensity />
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.3 Sector-Level Aggregation</h4>
              <p className="text-muted-foreground">
                For each sector, we compute: (1) average R&D intensity weighted by company size,
                (2) total aggregate R&D spending, and (3) distribution of R&D intensities within 
                the sector.
              </p>
            </div>

            <div>
              <h4 className="text-foreground font-semibold mb-2">4.4 Within-Sector Analysis</h4>
              <p className="text-muted-foreground">
                To test whether the R&D-return relationship holds within sectors, we apply the 
                same quintile-based methodology used in our aggregate analysis, but constrain 
                quintile formation to within-sector rankings.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
