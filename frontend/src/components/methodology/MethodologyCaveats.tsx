/**
 * PATH: frontend/src/components/methodology/MethodologyCaveats.tsx
 * PURPOSE: Fiscal Year Handling, Sector Bias, and Limitations sections
 * WHY: Split from Methodology.tsx to stay under 300-line limit
 * DEPENDENCIES:
 *   - ui/card: layout primitives
 *   - lucide-react: section icons
 */

import { Card, CardContent } from "@/components/ui/card"
import { FileText, AlertTriangle } from "lucide-react"

export function MethodologyCaveats() {
  return (
    <>
      {/* Fiscal Year Handling */}
      <section id="fiscal-year-handling" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">6. Fiscal Year Handling</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">Critical Consideration</p>
              <p className="text-sm text-muted-foreground">
                U.S. companies have different fiscal year end dates. This affects data availability and timing.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Common Fiscal Year Ends</h3>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>December 31:</strong> ~65% of S&P 500 (e.g., Alphabet, JPMorgan)</li>
              <li>• <strong>January 31:</strong> Retail (e.g., Walmart, Costco)</li>
              <li>• <strong>June 30:</strong> Microsoft, Nike</li>
              <li>• <strong>September 30:</strong> Apple (until 2020)</li>
            </ul>

            <h3 className="text-lg font-semibold text-foreground">Our Approach</h3>
            <p className="text-muted-foreground leading-relaxed">
              When constructing portfolios for calendar year t, we use the most recent available 
              fiscal year data. For a company with a December fiscal year end, this means:
            </p>
            <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-sm">
              <p className="text-muted-foreground"># For calendar year 2024 portfolio:</p>
              <p className="text-emerald-500">fiscal_data = get_most_recent_fy(company, before='2024-01-01')</p>
              <p className="text-emerald-500"># → Returns FY2023 data (filed in Q1 2024)</p>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">July-June Returns (Fama-French Convention)</h3>
            <p className="text-muted-foreground leading-relaxed">
              To eliminate look-ahead bias, we implement the Fama-French July-June return convention:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>Portfolio Formation:</strong> July 1 each year (after 10-K filings are public)</li>
              <li>• <strong>Holding Period:</strong> July 1 to June 30 of the following year</li>
              <li>• <strong>Example:</strong> FY 2022 data (filed by March 2023) → portfolio formed July 2023 → returns measured July 2023 to June 2024</li>
            </ul>
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
              <p className="text-sm font-semibold text-emerald-500 mb-2">✓ Implementation Status</p>
              <p className="text-sm text-muted-foreground">
                July-June returns are implemented via the <code>JulyJuneReturn</code> table and 
                <code>JulyJuneReturnCalculator</code> service. The <code>RollingWindowAnalyzer</code> uses 
                <code>use_july_june=True</code> by default for research-grade analysis.
              </p>
            </div>

            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">⚠️ Current Year ({new Date().getFullYear()}) Data</p>
              <p className="text-sm text-muted-foreground">
                Data for the current calendar year is always incomplete because many companies 
                haven't filed yet. We mark current year data as "Preliminary" in all visualizations.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Sector Bias */}
      <section id="sector-bias" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h2 className="text-2xl font-bold">7. Sector Bias Acknowledgment</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm font-semibold text-amber-500 mb-2">Important Caveat</p>
              <p className="text-sm text-muted-foreground">
                High R&D intensity is concentrated in specific sectors. Our results may partially 
                reflect sector performance rather than R&D alone.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Sector Distribution by Quintile</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 text-foreground">Quintile</th>
                    <th className="text-left py-3 text-foreground">Dominant Sectors</th>
                    <th className="text-left py-3 text-foreground">% of Quintile</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  <tr className="border-b border-border/50"><td className="py-2">Q5 (High R&D)</td><td>Technology, Healthcare/Biotech</td><td>~70%</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Q4</td><td>Tech Hardware, Pharma</td><td>~55%</td></tr>
                  <tr className="border-b border-border/50"><td className="py-2">Q1-Q2 (Low R&D)</td><td>Financials, Utilities, REITs</td><td>~60%</td></tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Mitigation Approaches</h3>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>Within-sector quintiles:</strong> We provide sector-neutral analysis in Paper 2</li>
              <li>• <strong>Sector controls:</strong> Regression analysis with sector dummy variables</li>
              <li>• <strong>Transparency:</strong> We always report sector composition of each quintile</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      {/* Limitations */}
      <section id="limitations" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">8. Limitations</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Key Limitations (what reviewers should focus on)</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm font-semibold text-red-500 mb-2">Membership coverage (survivorship risk)</p>
                <p className="text-xs text-muted-foreground">
                  Where historical constituent spans are available, we enforce point-in-time S&amp;P 500 membership at formation dates.
                  In Tier-1, membership coverage can still be incomplete, and we disclose coverage diagnostics in the frozen publication snapshot.
                </p>
              </div>
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm font-semibold text-red-500 mb-2">Look-ahead bias (calendar-year risk)</p>
                <p className="text-xs text-muted-foreground">
                  Calendar-year (Jan-Dec) sorts can inadvertently use accounting data that wasn't public at the start of the return window.
                  Our primary analysis uses the July-June convention to mitigate this.
                </p>
              </div>
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm font-semibold text-red-500 mb-2">Overlapping Windows</p>
                <p className="text-xs text-muted-foreground">
                  Rolling k-year windows overlap by k-1 years, violating the independence assumption of 
                  standard statistical tests. We treat rolling windows as descriptive context; primary inference uses monthly spanning tests and
                  cross-sectional regressions, with the annual non-overlapping series reported for economic context (Newey-West adjusted).
                </p>
              </div>
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">Sector Concentration</p>
                <p className="text-xs text-muted-foreground">
                  High R&D quintiles (Q4, Q5) are ~70% Tech/Healthcare. The "R&D premium" may partially 
                  reflect sector performance, not R&D specifically. We provide within-sector analysis 
                  to address this, but it remains a key caveat.
                </p>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">Other Methodological Notes</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">R&D Accounting Differences</p>
                <p className="text-xs text-muted-foreground">
                  GAAP requires R&D to be expensed, but definitions vary. Software capitalization 
                  rules changed in 2018, affecting comparability. Some companies may expense R&D 
                  differently or have missing data (assigned to Q1).
                </p>
              </div>
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">Transaction costs are modeled (but model-based)</p>
                <p className="text-xs text-muted-foreground">
                  We report net-of-cost results using literature-calibrated cost parameters and realized turnover from the investable backtest.
                  These are still estimates (not an execution simulation), so cost results should be interpreted as approximations.
                </p>
              </div>
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-sm font-semibold text-amber-500 mb-2">No Guarantee of Future Returns</p>
                <p className="text-xs text-muted-foreground">
                  Historical patterns may not persist. The R&D premium has shown weakness in certain 
                  periods (e.g., 2008-2018 per Cai et al. 2023). Market conditions, interest rates, 
                  and sector dynamics all affect future R&D premium.
                </p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <p className="text-sm font-semibold text-blue-500 mb-2">Rebalancing Assumption</p>
                <p className="text-xs text-muted-foreground">
                  We use <strong>annual formation/reconstitution in July</strong> (Fama-French convention) with equal-weight portfolios.
                  Rolling windows are reported as descriptive and do not re-sort annually by design.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
