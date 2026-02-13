/**
 * PATH: frontend/src/components/paper4/Paper4BackMatter.tsx
 * PURPOSE: Discussion, Conclusion, Replicability, and References sections for Paper 4
 * WHY: Extracted from Paper4.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - UI components (Card): layout
 * - lucide-react icons: section icons
 * - ReferencesList: academic references
 */

import { Card, CardContent } from "@/components/ui/card"
import { BookOpen, CheckCircle, Building2, Database } from "lucide-react"
import { ReferencesList } from "@/components/Citation"

export function Paper4BackMatter() {
  return (
    <>
      {/* Discussion */}
      <section id="discussion" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Building2 className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">6. Discussion</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-6">
            <p className="text-muted-foreground">
              Our analysis reveals that R&D investment is associated with value creation through multiple channels:
            </p>
            
            <div className="grid gap-6 md:grid-cols-3">
              <div className="p-6 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700">
                <h4 className="text-blue-700 dark:text-blue-400 font-semibold mb-3">Innovation Pipeline</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  R&D spending funds new product development, process improvements, and 
                  intellectual property creation.
                </p>
              </div>
              
              <div className="p-6 rounded-xl bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
                <h4 className="text-purple-700 dark:text-purple-400 font-semibold mb-3">Competitive Moat</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Patents, proprietary technology, and know-how create barriers to entry 
                  and pricing power.
                </p>
              </div>
              
              <div className="p-6 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700">
                <h4 className="text-emerald-700 dark:text-emerald-400 font-semibold mb-3">Financial Returns</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Superior products lead to revenue growth, margin expansion, and 
                  ultimately stock price appreciation.
                </p>
              </div>
            </div>

            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <h4 className="text-amber-700 dark:text-amber-400 font-semibold mb-2">Time Lag Effect</h4>
              <p className="text-sm text-slate-700 dark:text-slate-200">
                Long-horizon measurement matters. In our return-sort results, effect size (η²) increases with horizon.
                This pattern is consistent with the intuition that R&D payoffs can be multi-year, but we do not estimate
                causal lag lengths directly in this dataset.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">6.2 Intangible Capital and Market Value</h3>
            <p className="text-muted-foreground">
              There is growing recognition that intangible assets now drive a large share of corporate value. 
              Practitioner and academic work often notes that capitalizing R&D can materially change reported earnings
              and valuation multiples for R&D-intensive firms versus standard accounting (which expenses R&D).
            </p>
            <p className="text-muted-foreground">
              This indicates that high-R&D firms are creating real economic assets not immediately reflected 
              on financial statements. Investors who appreciate this "invisible capital" can benefit from the 
              eventual recognition of innovation value in earnings and stock prices.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">6.3 Limitations and Caveats</h3>
            <ul className="text-muted-foreground space-y-2">
              <li>
                • <strong>Survivorship Bias (Tier-1 mitigation):</strong> Point-in-time S&amp;P 500 membership is enforced where constituent spans are available.
                Exits are handled via return construction (cash-after-exit) and robustness via delisting sensitivity. Tier-1 still has coverage limitations versus CRSP/Compustat-grade data.
              </li>
              <li>• <strong>Look-Ahead Bias (Mitigated):</strong> We utilize the Fama-French July-June return convention to align fiscal-year R&D data with subsequent returns.</li>
              <li>• <strong>Overlapping windows:</strong> Dependency between rolling 5/10/20-year analysis periods requires caution when interpreting the strengthening of effect sizes over time.</li>
              <li>• <strong>Causation vs. Correlation:</strong> While R&D correlates with long-term performance, successful firms may simply have more excess cash to invest in R&D (reverse causality).</li>
              <li>• <strong>Qualitative Framework:</strong> The VRIN analysis is a qualitative strategic framework and has not been empirically mapped to specific patent or IP metrics in this study.</li>
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
              This sub-research note complements the Main Paper by discussing plausible mechanisms for why
              R&D intensity can be associated with long-run returns. Key takeaways:
            </p>
            
            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700">
                <h4 className="text-emerald-700 dark:text-emerald-700 dark:text-emerald-400 font-semibold">Finding 1</h4>
                <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">
                  Return-sort results show high-R&amp;D companies outperform low-R&amp;D on average across horizons (see the Main Paper for snapshot-pinned estimates)
                </p>
              </div>
              <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700">
                <h4 className="text-blue-700 dark:text-blue-700 dark:text-blue-400 font-semibold">Finding 2</h4>
                <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">
                  Effect size increases with horizon (η² rises), even as premium magnitude declines
                </p>
              </div>
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
                <h4 className="text-purple-700 dark:text-purple-700 dark:text-purple-400 font-semibold">Finding 3</h4>
                <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">R&D premium is statistically significant</p>
              </div>
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
                <h4 className="text-amber-700 dark:text-amber-700 dark:text-amber-400 font-semibold">Finding 4</h4>
                <p className="text-sm text-slate-700 dark:text-slate-700 dark:text-slate-200 mt-2">R&D satisfies VRIN framework criteria</p>
              </div>
            </div>

            <p className="text-muted-foreground mt-4">
              <strong className="text-foreground">Investment Implications:</strong> Incorporating R&D 
              intensity into portfolio construction can enhance long-term returns. The R&D Alpha ETF 
              strategy provides a practical implementation of these insights.
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
              To replicate this fundamental analysis:
            </p>
            <ol className="text-muted-foreground space-y-2">
              <li>1. <strong className="text-foreground">Data Collection:</strong> Obtain annual R&D expense and revenue from 10-K filings</li>
              <li>2. <strong className="text-foreground">Intensity Calculation:</strong> Compute R&D/Revenue for each firm-year</li>
              <li>3. <strong className="text-foreground">Trend Analysis:</strong> Aggregate by year and sector</li>
              <li>4. <strong className="text-foreground">VRIN Evaluation:</strong> Assess qualitative factors for competitive advantage</li>
              <li>5. <strong className="text-foreground">Time Lag Testing:</strong> Correlate R&D with returns at various horizons</li>
            </ol>
            <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
              <p className="text-sm text-muted-foreground">
                <strong className="text-foreground">Data Access:</strong> All R&D data and calculated 
                metrics are available through the dashboard API. Use the /api/research/rd-trends 
                endpoint for time-series data.
              </p>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">Sector Bias Acknowledgment</h3>
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <p className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-2">⚠️ Sector Concentration</p>
              <p className="text-sm text-muted-foreground">
                R&D-intensive companies are heavily concentrated in Technology, Healthcare, and Biotech sectors. 
                This concentration affects our findings:
              </p>
              <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                <li>• Top R&D spenders are predominantly tech giants (Apple, Alphabet, Meta, Microsoft)</li>
                <li>• R&D intensity trends partly reflect tech sector growth</li>
                <li>• VRIN framework may apply differently across industries</li>
                <li>• Value creation mechanisms vary (software IP vs. pharma patents)</li>
              </ul>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">Verification Checklist</h3>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
              <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">✓ Independently Verifiable</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• R&D expense from SEC 10-K (GAAP-mandated)</li>
                  <li>• Revenue figures are audited</li>
                  <li>• All calculations use standard formulas</li>
                  <li>• Time-series data is publicly accessible</li>
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
              "barney_1991",
              "griliches_1981",
              "gu_2005",
              "hall_jaffe_trajtenberg_2005",
              "lev_sougiannis_1996",
              "porter_1992"
            ]} />
          </CardContent>
        </Card>
      </section>
    </>
  )
}
