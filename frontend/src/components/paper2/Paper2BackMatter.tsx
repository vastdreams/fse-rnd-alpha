/**
 * PATH: frontend/src/components/paper2/Paper2BackMatter.tsx
 * FILE_ID: PAPER2-BACK-MATTER-001
 * PURPOSE: Discussion, Conclusion, Replicability, and References for Paper2
 * WHY: Extracted from Paper2.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - @/components/ui/*: UI primitives
 * - @/components/Citation: references list
 * - lucide-react: icons
 */

import { Card, CardContent } from "@/components/ui/card"
import { Layers, CheckCircle, Database, BookOpen } from "lucide-react"
import { ReferencesList } from "@/components/Citation"

export function Paper2BackMatter() {
  return (
    <>
      {/* Discussion */}
      <section id="discussion" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Layers className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">6. Discussion</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-6">
            <p className="text-muted-foreground leading-relaxed">
              Our sector-level analysis reveals that while R&D intensity varies significantly across 11 GICS 
              sectors, the fundamental relationship between R&D investment and long-term performance remains 
              robust within innovation-intensive industries.
            </p>

            <h3 className="text-lg font-semibold text-foreground">6.1 Sector-Specific Dynamics</h3>
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                <h4 className="text-blue-600 dark:text-blue-400 font-semibold mb-2">Healthcare & Technology Dominance</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  These sectors consistently lead in R&D intensity, reflecting the innovation-driven 
                  nature of their competitive dynamics. Drug development and software innovation 
                  require substantial ongoing R&D investment.
                </p>
              </div>

              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <h4 className="text-amber-700 dark:text-amber-400 font-semibold mb-2">Asset-Intensive Sectors</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Utilities and Real Estate show minimal R&D spending. These sectors compete on 
                  asset efficiency and regulatory positioning rather than product innovation.
                </p>
              </div>
              </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">6.2 The Within-Sector Premium</h3>
            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
              <h4 className="text-green-600 dark:text-emerald-400 font-semibold mb-2">Isolating the R&D Signal</h4>
              <p className="text-sm text-slate-700 dark:text-slate-200">
                  Importantly, the positive relationship between R&D intensity and returns holds 
                  within sectors. High-R&D companies outperform low-R&D peers even when controlling 
                for industry effects, suggesting the R&D premium is not merely a sector proxy.
                </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">6.3 Limitations and Sector Biases</h3>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>Survivorship Bias (Addressed):</strong> Our analysis now incorporates historical S&P 500 constituents to ensure that the sector-level outperformance of high-R&D firms is not merely an artifact of surviving companies.</li>
              <li>• <strong>Look-Ahead Bias (Addressed):</strong> We employ the Fama-French July-June return convention, ensuring that financial information used to classify sector leaders was fully available to the market.</li>
              <li>• <strong>GICS reclassification:</strong> Changes in GICS structure (e.g., the 2018 creation of Communication Services) can affect historical sector benchmarking.</li>
              <li>• <strong>Accounting heterogeneity:</strong> R&D reporting standards and tax treatment vary by industry, potentially affecting cross-sector comparability of intensity metrics.</li>
              <li>• <strong>Overlapping windows:</strong> Dependency between rolling analysis periods requires caution when interpreting the persistence of sector-specific premiums.</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      {/* Conclusion */}
      <section id="conclusion" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <CheckCircle className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">7. Conclusion</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <p className="text-muted-foreground">
              This study documents substantial heterogeneity in R&D investment patterns across 
              industry sectors. Key conclusions include:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• R&D intensity ranges from &lt;1% in Utilities to &gt;15% in Healthcare</li>
              <li>• Sector context is essential for meaningful R&D benchmarking</li>
              <li>• The R&D-return relationship persists within industry groups</li>
              <li>• Investors should consider sector-adjusted R&D metrics</li>
            </ul>
            <p className="text-muted-foreground">
              These findings have important implications for investors, corporate strategists, 
              and policymakers seeking to understand the role of R&D in value creation.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Replicability */}
      <section id="replicability" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">8. Replicability</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <p className="text-muted-foreground">
              To replicate this analysis:
            </p>
            <ol className="text-muted-foreground space-y-2">
              <li>1. <strong className="text-foreground">Data Source:</strong> Obtain S&P 500 constituent data with GICS sector classifications</li>
              <li>2. <strong className="text-foreground">Financial Data:</strong> Collect annual R&D expense and revenue from 10-K filings</li>
              <li>3. <strong className="text-foreground">Calculation:</strong> Compute R&D intensity = R&D / Revenue for each firm-year</li>
              <li>4. <strong className="text-foreground">Aggregation:</strong> Calculate sector averages using market-cap weighting</li>
              <li>5. <strong className="text-foreground">Analysis:</strong> Apply within-sector quintile methodology</li>
            </ol>
            <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
              <p className="text-sm text-muted-foreground">
                <strong className="text-foreground">Data Access:</strong> All underlying data is available 
                through the dashboard's API endpoints. Export functionality provides CSV downloads 
                of sector-level aggregates.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">Sector Bias Acknowledgment</h3>
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">&#x26A0;&#xFE0F; Critical Caveat</p>
              <p className="text-sm text-muted-foreground">
                This analysis reveals significant sector concentration in R&D investment. Technology and Healthcare 
                sectors dominate high-R&D quintiles (Q4, Q5), while Financials and Utilities dominate low-R&D 
                quintiles (Q1, Q2). Therefore:
              </p>
              <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                <li>• Cross-sector R&D comparisons may conflate R&D effects with sector effects</li>
                <li>• Tech/Healthcare outperformance in recent decades can amplify the observed R&D premium</li>
                <li>• Within-sector analysis (provided) offers more reliable R&D signal</li>
              </ul>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">Verification Checklist</h3>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm font-semibold text-emerald-500 mb-2">&#x2713; Independently Verifiable</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• GICS sector classifications are public</li>
                  <li>• R&D data from SEC filings is authoritative</li>
                  <li>• Quintile methodology is standard</li>
                </ul>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* References */}
      <section id="references" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">References</h2>
        </div>
        <Card>
          <CardContent className="pt-6">
            <ReferencesList ids={[
              "cohen_klepper_1996",
              "hall_jaffe_trajtenberg_2005",
              "hirshleifer_hsu_li_2013",
              "lev_sougiannis_1996"
            ]} />
          </CardContent>
        </Card>
      </section>
    </>
  )
}
