/**
 * PATH: frontend/src/components/methodology/MethodologyDataSources.tsx
 * PURPOSE: Overview, Data Sources, and R&D Intensity sections of the Methodology page
 * WHY: Split from Methodology.tsx to stay under 300-line limit
 * DEPENDENCIES:
 *   - ui/card, ui/badge: layout primitives
 *   - lucide-react: section icons
 *   - Formula: R&D intensity formula rendering
 */

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Database, Calculator, Boxes, Scale, FlaskConical } from "lucide-react"
import { Formulas } from "@/components/Formula"

export function MethodologyDataSources() {
  return (
    <>
      {/* Overview */}
      <section id="overview" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Boxes className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">Overview</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <p className="text-muted-foreground leading-relaxed">
              This document provides a rigorous, first-principles explanation of how we analyze the relationship 
              between R&D investment intensity and long-term shareholder returns. Every calculation, data source, 
              and methodological choice is documented to enable independent verification and replication.
            </p>
            
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm font-semibold text-blue-500 mb-2">Core Hypothesis</p>
              <p className="text-sm text-muted-foreground">
                Companies that invest more heavily in R&D (as a percentage of revenue) generate higher 
                long-term shareholder returns than companies with lower R&D investment. This effect 
                strengthens over longer time horizons.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Analysis Pipeline</h3>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                <Database className="h-6 w-6 text-blue-500 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">1. Data Collection</p>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                <Calculator className="h-6 w-6 text-emerald-500 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">2. R&D Intensity Calculation</p>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                <Scale className="h-6 w-6 text-purple-500 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">3. Quintile Assignment</p>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg border border-border text-center">
                <FlaskConical className="h-6 w-6 text-amber-500 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">4. Statistical Analysis</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Data Sources */}
      <section id="data-sources" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">1. Data Sources</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <p className="text-muted-foreground leading-relaxed">
              We use three primary data sources, each serving a specific purpose in the analysis:
            </p>

            <div className="space-y-4">
              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="text-blue-500 border-blue-500/30">Primary</Badge>
                  <h4 className="font-semibold text-foreground">SEC EDGAR</h4>
                </div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• <strong>What:</strong> 10-K annual reports (official SEC filings)</li>
                  <li>• <strong>Why:</strong> Authoritative source for R&D expenses under GAAP (ASC 730)</li>
                  <li>• <strong>API:</strong> <code className="bg-muted px-1 rounded">{"https://data.sec.gov/submissions/CIK{cik}.json"}</code></li>
                  <li>• <strong>Fields:</strong> R&D Expense, Total Revenue, Filing Date, Fiscal Year End</li>
                </ul>
              </div>

              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">Secondary</Badge>
                  <h4 className="font-semibold text-foreground">Financial Modeling Prep (FMP)</h4>
                </div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• <strong>What:</strong> Standardized financial data API</li>
                  <li>• <strong>Why:</strong> Provides clean, normalized financial statements and price data</li>
                  <li>• <strong>Endpoints:</strong></li>
                  <li className="ml-4"><code className="bg-muted px-1 rounded text-xs">/api/v3/income-statement/{"{"}ticker{"}"}</code> → R&D, Revenue</li>
                  <li className="ml-4"><code className="bg-muted px-1 rounded text-xs">/api/v3/historical-price-full/{"{"}ticker{"}"}</code> → Prices</li>
                </ul>
              </div>

              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="text-purple-500 border-purple-500/30">Reference</Badge>
                  <h4 className="font-semibold text-foreground">S&P 500 Historical Constituents</h4>
                </div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• <strong>What:</strong> List of companies in the S&P 500 over time</li>
                  <li>• <strong>Why:</strong> Enables point-in-time membership (include only names actually in the index at formation dates)</li>
                  <li>• <strong>Source:</strong> Historical membership spans (added/removed dates) ingested into our database</li>
                  <li>
                    • <strong>Caveat:</strong> Coverage can be incomplete in Tier-1; when spans are missing, some analyses fall back to an
                    "available-data" universe and we disclose this via diagnostics in the publication snapshot.
                  </li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* R&D Intensity Calculation */}
      <section id="rd-intensity" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Calculator className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">2. R&D Intensity Calculation</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="flex flex-wrap items-center gap-4">
              <h3 className="text-lg font-semibold text-foreground">Definition:</h3>
              <Formulas.RDIntensity />
            </div>

            <h3 className="text-lg font-semibold text-foreground">Why This Formula?</h3>
            <p className="text-muted-foreground leading-relaxed">
              <strong>First-principles reasoning:</strong> We want to measure a company's commitment to innovation 
              relative to its scale. Using absolute R&D dollars would favor large companies (Apple's $30B vs. a 
              biotech's $500M). Normalizing by revenue creates a fair comparison:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>Apple:</strong> $30B R&D / $394B revenue = 7.6% intensity</li>
              <li>• <strong>Biotech Co:</strong> $500M R&D / $2B revenue = 25% intensity</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed">
              The biotech is making a larger proportional bet on R&D-our hypothesis is this matters for returns.
            </p>

            <h3 className="text-lg font-semibold text-foreground">Data Extraction</h3>
            <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm space-y-2">
              <p className="text-muted-foreground"># From SEC 10-K or FMP API:</p>
              <p className="text-emerald-500">rd_expense = income_statement['researchAndDevelopmentExpenses']</p>
              <p className="text-emerald-500">revenue = income_statement['revenue']  # or 'totalRevenue'</p>
              <p className="text-muted-foreground mt-3"># Calculate intensity:</p>
              <p className="text-emerald-500">rd_intensity = (rd_expense / revenue) * 100</p>
            </div>

            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ Edge Cases</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• <strong>Zero R&D:</strong> Many companies (utilities, REITs) report $0 R&D. These are assigned to Q1 (lowest quintile).</li>
                <li>• <strong>Negative Revenue:</strong> Excluded from analysis (rare, usually data errors).</li>
                <li>• <strong>R&D {">"} Revenue:</strong> Valid for pre-revenue biotechs; intensity capped at 100% for quintile assignment.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
