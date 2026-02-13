/** Paper1BackMatter — Discussion + Conclusion + Replicability + References */
import { Card, CardContent } from "@/components/ui/card"
import { BookOpen, CheckCircle, Database, FlaskConical, ExternalLink } from "lucide-react"
import { ReferencesList } from "@/components/Citation"

interface Paper1BackMatterProps {
  rdPremium5yr: number | undefined
  rdPremium10yr: number | undefined
  rdPremium20yr: number | undefined
  etaSquared5yr: number | undefined
  etaSquared20yr: number | undefined
  annualMeanPremium: number | undefined
  annualTStat: number | undefined
  annualPValue: number | undefined
  annualNYears: number | undefined
}

export function Paper1BackMatter({
  rdPremium5yr,
  rdPremium10yr,
  rdPremium20yr,
  etaSquared5yr,
  etaSquared20yr,
  annualMeanPremium,
  annualTStat,
  annualPValue,
  annualNYears,
}: Paper1BackMatterProps) {
  return (
    <>
      {/* Discussion */}
      <section id="discussion" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">6. Discussion</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <p className="text-muted-foreground leading-relaxed">
              Our findings demonstrate that R&D investment intensity is a statistically significant predictor 
              of long-term shareholder returns. Monthly factor spanning tests show a statistically significant alpha (FF5), 
              and Fama-MacBeth cross-sectional regressions confirm the relationship after controlling for size and book-to-market. 
              The monotonic relationship between R&D quintiles and returns, combined with the increasing effect sizes over longer horizons, 
              indicates that R&D investments create durable competitive advantages that compound over time.
            </p>

            <h3 className="text-lg font-semibold text-foreground">6.1 Economic Interpretation</h3>
            <p className="text-muted-foreground leading-relaxed">
              The horizon-dependent annualized premium for high-R&amp;D companies is economically meaningful. In our snapshot, the rolling-window
              Q5--Q1 premium is approximately{" "}
              <strong className="text-foreground">
                {typeof rdPremium5yr === "number" ? `${rdPremium5yr >= 0 ? "+" : ""}${rdPremium5yr.toFixed(1)}%` : "..."}
              </strong>{" "}
              (5yr) versus{" "}
              <strong className="text-foreground">
                {typeof rdPremium20yr === "number" ? `${rdPremium20yr >= 0 ? "+" : ""}${rdPremium20yr.toFixed(1)}%` : "..."}
              </strong>{" "}
              (20yr). Over long horizons, even a smaller annual premium can translate to significant cumulative 
              outperformance. The magnitude suggests that R&D investment contributes to competitive advantages.
            </p>

            <h3 className="text-lg font-semibold text-foreground">6.2 Time Horizon Effects</h3>
            <p className="text-muted-foreground leading-relaxed">
              The strengthening of effect sizes over longer horizons (η² rises from{" "}
              <strong className="text-foreground">{typeof etaSquared5yr === "number" ? etaSquared5yr.toFixed(3) : "..."}</strong>{" "}
              to{" "}
              <strong className="text-foreground">{typeof etaSquared20yr === "number" ? etaSquared20yr.toFixed(3) : "..."}</strong>
              ) suggests that 
              R&D benefits compound over time. This is consistent with the innovation literature suggesting 
              that R&D investments have long gestation periods before yielding commercial returns.
            </p>

            <h3 className="text-lg font-semibold text-foreground">6.3 Limitations and Biases</h3>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong>Survivorship bias:</strong> Point-in-time membership is enforced where constituent spans are available, but Tier-1 coverage is not CRSP/Compustat-grade. Delisting uncertainty is addressed via sensitivity analysis.</li>
              <li>• <strong>Look-ahead bias:</strong> While we use July-June returns (Fama-French convention) to mitigate timing issues, fiscal year-end variations create imperfect alignment.</li>
              <li>• <strong>Overlapping windows:</strong> Rolling 5/10/20-year windows are not independent observations. We apply Newey-West HAC standard errors, but overlapping-window p-values should be interpreted with caution. Annual non-overlapping HML premium is the preferred inference approach.</li>
              <li>• <strong>Sector concentration:</strong> High-R&amp;D portfolios are concentrated in R&amp;D-intensive sectors (notably Tech/Healthcare), so sector exposures can influence results. We report sector composition; sector-neutral testing is treated as a robustness extension.</li>
              <li>• <strong>Factor spanning:</strong> Formal tests against FF3/FF5/Momentum factors are required before claiming R&D as a distinct "pricing factor."</li>
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
            <p className="text-muted-foreground leading-relaxed">
              This study demonstrates a robust and economically significant positive relationship between 
              R&D investment intensity and long-term shareholder returns among S&P 500 companies. Our 
              quintile-based analysis shows a positive Q5-Q1 premium across horizons (rolling-window annualized premiums:{" "}
              {typeof rdPremium5yr === "number" ? `${rdPremium5yr >= 0 ? "+" : ""}${rdPremium5yr.toFixed(1)}%` : "..."}{" "}
              for 5yr,{" "}
              {typeof rdPremium10yr === "number" ? `${rdPremium10yr >= 0 ? "+" : ""}${rdPremium10yr.toFixed(1)}%` : "..."}{" "}
              for 10yr, and{" "}
              {typeof rdPremium20yr === "number" ? `${rdPremium20yr >= 0 ? "+" : ""}${rdPremium20yr.toFixed(1)}%` : "..."}{" "}
              for 20yr; descriptive due to overlap). Primary inference uses the non-overlapping annual July-June premium series (mean{" "}
              {typeof annualMeanPremium === "number" ? `${annualMeanPremium.toFixed(2)}%` : "..."}
              {typeof annualTStat === "number" && typeof annualPValue === "number"
                ? `, Newey-West t=${annualTStat.toFixed(2)}, p=${annualPValue < 0.001 ? "<0.001" : annualPValue.toFixed(3)}`
                : ""}
              {typeof annualNYears === "number" ? `; N=${annualNYears}` : ""}).
            </p>
            <p className="text-muted-foreground leading-relaxed">
              These findings have important implications for investors, corporate managers, and policymakers. 
              For investors, our results suggest that tilting portfolios toward R&D-intensive companies may 
              generate superior long-term returns. For managers, the evidence supports sustained investment 
              in R&D as a value-creating strategy. For policymakers, the results underscore the economic 
              importance of supporting innovation through favorable R&D tax treatment and research funding.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Replicability */}
      <section id="replicability" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">8. Replicability & Data Access</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground leading-relaxed">
                In the interest of scientific transparency and reproducibility, we provide complete access to 
                our data extraction pipeline, statistical methods, and underlying code.
              </p>
            </div>

            <h4 className="font-semibold text-foreground flex items-center gap-2">
              <Database className="h-4 w-4" />
              Data Sources & Extraction
            </h4>
            <div className="p-4 bg-muted/50 rounded-lg border border-border space-y-4">
              <div>
                <p className="text-sm font-semibold text-foreground">1. Financial Modeling Prep (Tier-1)</p>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                  <li>Income statements: R&amp;D expense and revenue</li>
                  <li>Daily prices: split-adjusted close + dividend events (reinvested) for the total-return proxy used in publication returns</li>
                  <li>Historical constituents: point-in-time S&amp;P 500 membership (Tier-1 proxy)</li>
                  <li>
                    Replication requires an <code>FMP_API_KEY</code> (data cannot be redistributed)
                  </li>
                </ul>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">2. Ken French Data Library</p>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                  <li>Fama-French factors and risk-free rate (for robustness / factor diagnostics)</li>
                </ul>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">3. Delisting Returns (Tier-1 estimate)</p>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1 list-disc list-inside">
                  <li>Price-based estimation when possible; conservative heuristics otherwise</li>
                  <li>See repository docs: <code>DATA_PROVENANCE.md</code> and <code>DATA_AVAILABILITY.md</code></li>
                </ul>
              </div>
            </div>

            <h4 className="font-semibold text-foreground flex items-center gap-2">
              <FlaskConical className="h-4 w-4" />
              Exact Calculation Steps
            </h4>
            <div className="p-4 bg-muted/50 rounded-lg border border-border text-sm space-y-2">
              <p className="text-muted-foreground">
                Reproduction is automated via <code>./scripts/reproduce_publication.sh</code>. At a high level, the pipeline:
              </p>
              <ol className="text-muted-foreground list-decimal list-inside space-y-1">
                <li>Ingests Tier-1 data (FMP, factors, constituents, delisting estimates)</li>
                <li>Computes July-June returns (look-ahead mitigation)</li>
                <li>Computes rolling-window quintile results + ANOVA/t-tests</li>
                <li>Exports frozen publication tables</li>
              </ol>
            </div>

            <h4 className="font-semibold text-foreground flex items-center gap-2">
              <ExternalLink className="h-4 w-4" />
              Code Repository
            </h4>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
              <p className="text-sm text-muted-foreground mb-3">
                Full analysis code available on GitHub: <a href="https://github.com/vastdreams/fse-rnd-alpha" className="text-primary hover:underline">github.com/vastdreams/fse-rnd-alpha</a>
              </p>
              <div className="space-y-2 text-sm font-mono">
                <p className="text-slate-600 dark:text-slate-400"># Clone and setup</p>
                <p className="text-foreground">git clone https://github.com/vastdreams/fse-rnd-alpha.git</p>
                <p className="text-foreground">cd fse-rnd-alpha && pip install -r requirements.txt</p>
                <p className="text-slate-600 dark:text-slate-400 mt-3"># Run data pipeline</p>
                <p className="text-foreground">./scripts/reproduce_publication.sh</p>
                <p className="text-slate-600 dark:text-slate-400 mt-3"># Key scripts:</p>
                <ul className="text-muted-foreground space-y-1">
                  <li>• <code>scripts/ingest_fmp_ultimate.py</code> - Tier-1 ingestion</li>
                  <li>• <code>scripts/compute_july_june_returns.py</code> - July-June returns</li>
                  <li>• <code>scripts/compute_research_metrics.py</code> - recompute pipeline</li>
                  <li>• <code>scripts/reproduce_all_tables.py</code> - table export</li>
                </ul>
              </div>
            </div>

            <h4 className="font-semibold text-foreground">Verification Checklist</h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
                <p className="text-sm font-semibold text-green-600 dark:text-emerald-400 mb-2">✓ Independently Verifiable</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• All calculations use standard statistical methods</li>
                  <li>• Code is fully open source</li>
                  <li>• Canonical values are pinned by the publication snapshot (see <code>/api/research/publication-snapshot</code>)</li>
                </ul>
              </div>
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                <p className="text-sm font-semibold text-amber-400 mb-2">⚠ Limitations</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• FMP API requires subscription for full data</li>
                  <li>• Tier-1 survivorship mitigation is not CRSP/Compustat-grade</li>
                  <li>• R&D reporting standards evolved over time</li>
                </ul>
              </div>
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
              "cai_cooper_he_2023",
              "chan_lakonishok_sougiannis_2001",
              "eberhart_maxwell_siddique_2004",
              "fama_french_1993",
              "fama_french_2015",
              "gu_2005",
              "hirshleifer_hsu_li_2013",
              "hou_mo_xue_zhang_2022",
              "lev_sougiannis_1996",
              "li_2011"
            ]} />
          </CardContent>
        </Card>
      </section>
    </>
  )
}
