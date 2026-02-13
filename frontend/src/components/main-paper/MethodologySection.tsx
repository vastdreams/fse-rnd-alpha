/** PATH: main-paper/MethodologySection.tsx — Section 4: Methodology */
import { FlaskConical } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Formulas } from "@/components/Formula"
export function MethodologySection({ methodologyParameters, snapshot }: { methodologyParameters: any; snapshot: any }) {
  return (
    <section id="methodology" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <FlaskConical className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">4. Methodology</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <h3 className="text-lg font-semibold text-foreground">4.1 Portfolio formation (signal and weights)</h3>
          <p className="text-muted-foreground mb-3">
            We construct portfolios using a standard academic approach that prioritizes transparency and replicability.
            Each step is designed to minimize biases while remaining implementable by practitioners.
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-2">
            <li>
              <strong className="text-foreground">Universe:</strong> S&amp;P 500 point-in-time constituents{" "}
              <InfoTooltip term="point_in_time" size={12} />.{" "}
              <span className="text-sm">
                Where historical membership spans are available, we include only stocks that were actually in the index at each formation date,
                reducing survivorship bias (coverage limitations are disclosed via snapshot diagnostics).
              </span>
            </li>
            <li>
              <strong className="text-foreground">Signal:</strong> prior fiscal-year R&amp;D intensity (R&amp;D expense / revenue).{" "}
              <span className="text-sm">Using the prior year ensures data was publicly available before portfolio formation.</span>
            </li>
            <li>
              <strong className="text-foreground">Sorting:</strong> equal-count quintiles (Q1 = lowest R&amp;D intensity, Q5 = highest).{" "}
              <span className="text-sm">Equal-count sorting ensures each quintile has roughly the same number of stocks, making comparisons fair.</span>
            </li>
          </ul>

          <div className="not-prose p-4 rounded-lg bg-muted/30 border my-4">
            <p className="font-semibold text-foreground mb-2 flex items-center gap-2">
              Understanding quintiles
              <InfoTooltip term="quintile" size={14} />
            </p>
            <p className="text-sm text-muted-foreground mb-2">
              Each year, stocks are sorted by R&amp;D intensity and divided into 5 equal-count groups (quintiles):
            </p>
            <div className="grid grid-cols-5 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-red-500/10 border border-red-500/20">
                <div className="font-bold text-foreground">Q1</div>
                <div className="text-muted-foreground">Lowest 20%</div>
                <div className="text-muted-foreground">R&amp;D intensity</div>
              </div>
              <div className="p-2 rounded bg-orange-500/10 border border-orange-500/20">
                <div className="font-bold text-foreground">Q2</div>
                <div className="text-muted-foreground">20-40%</div>
              </div>
              <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/20">
                <div className="font-bold text-foreground">Q3</div>
                <div className="text-muted-foreground">40-60%</div>
              </div>
              <div className="p-2 rounded bg-lime-500/10 border border-lime-500/20">
                <div className="font-bold text-foreground">Q4</div>
                <div className="text-muted-foreground">60-80%</div>
              </div>
              <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
                <div className="font-bold text-foreground">Q5</div>
                <div className="text-muted-foreground">Highest 20%</div>
                <div className="text-muted-foreground">R&amp;D intensity</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              The <strong>HML premium</strong> (High-Minus-Low) is Q5 return minus Q1 return. A positive premium means high-R&amp;D stocks outperformed low-R&amp;D stocks.
            </p>
            <div className="mt-3">
              <Formulas.HMLPremium />
            </div>
          </div>

          <ul className="text-muted-foreground list-disc list-inside space-y-2">
            <li>
              <strong className="text-foreground">Weights:</strong> equal-weight within each portfolio{" "}
              <InfoTooltip term="equal_weight" size={12} />.{" "}
              <span className="text-sm">Equal-weighted returns are computed each year and compounded. This gives smaller firms equal influence
              with larger firms, which can increase the premium but also increases volatility.</span>
            </li>
            <li>
              <strong className="text-foreground">Inclusion:</strong> firms with R&amp;D reported as zero are retained (typically in Q1).
              <span className="text-sm"> A minimum-revenue filter is applied to avoid extreme ratios from very small denominators.
              Zero-R&amp;D firms are legitimate members of Q1 (they simply don't invest in R&amp;D).</span>
            </li>
          </ul>

          <div className="not-prose mt-4">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Parameter</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Min revenue threshold
                        <InfoTooltip title="Minimum Revenue Threshold" size={12}>
                          Firms with revenue below this threshold are excluded to avoid extreme R&amp;D intensity ratios from very small denominators.
                          A firm with $1M revenue and $500K R&amp;D would show 50% intensity, which may not be comparable to larger firms.
                          This filter ensures meaningful comparisons across the universe.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {typeof (methodologyParameters as any)?.filters?.min_revenue_threshold_usd === "number"
                        ? `$${((methodologyParameters as any).filters.min_revenue_threshold_usd / 1e6).toFixed(0)}M`
                        : "..."}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        R&amp;D intensity cap (default)
                        <InfoTooltip title="R&D Intensity Cap (Default)" size={12}>
                          Maximum R&amp;D intensity allowed for most sectors. Values above this cap are winsorized (set to the cap value) to prevent
                          outliers from distorting quintile assignments. For example, a biotech firm with 150% R&amp;D/revenue would be capped at 100%.
                          This is a conservative default that works for most industries.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.default_cap_pct === "number"
                        ? `${(methodologyParameters as any).filters.rd_intensity_capping.default_cap_pct.toFixed(0)}%`
                        : "..."}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        R&amp;D intensity cap (high-R&amp;D sectors)
                        <InfoTooltip title="R&D Intensity Cap (High-R&D Sectors)" size={12}>
                          Higher cap for sectors where extreme R&amp;D intensity is common and meaningful (e.g., Biotech, Pharma).
                          These sectors routinely have firms spending more than 100% of revenue on R&amp;D (funded by capital raises).
                          A higher cap preserves the signal while still limiting extreme outliers.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {typeof (methodologyParameters as any)?.filters?.rd_intensity_capping?.high_rd_sector_cap_pct === "number"
                        ? `${(methodologyParameters as any).filters.rd_intensity_capping.high_rd_sector_cap_pct.toFixed(0)}%`
                        : "..."}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Return definition
                        <InfoTooltip title="Return Definition" size={12}>
                          Publication returns are computed as a dividend-reinvested total-return proxy built from <strong>split-adjusted close</strong> prices plus <strong>ex-dividend cashflows</strong>.
                          In Tier-1, prices come from the provider’s stable EOD feed (split-adjusted close) and dividends come from the provider’s stable dividends feed (adjDividend).
                          We incorporate dividends on ex-dividend dates when computing daily returns, so dividends are included exactly once.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">Close + dividends (publication)</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Universe membership
                        <InfoTooltip title="Point-in-time Membership" size={12}>
                          We use historical S&amp;P 500 constituent data to include only stocks that were actually in the index at each formation date.
                          This prevents survivorship bias: we don't just look at today's S&amp;P 500 members (which excludes failed companies).
                          When historical membership data is unavailable, we note this limitation.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">Point-in-time (when available)</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Delisting returns
                        <InfoTooltip title="Delisting Return Treatment" size={12}>
                          We do not inject a separate “delisting return” into the annual return series. If a firm’s price history ends before the July-June window ends
                          (e.g., merger/delisting), we compute the holding-period return to the last observed trading day and treat cash as earning 0% thereafter for the remainder of the window.
                          We also report a literature-calibrated sensitivity analysis for delisting uncertainty.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">Cash-after-exit + sensitivity</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Return convention
                        <InfoTooltip title="Return Convention (July-June)" size={12}>
                          We use July-June return periods following Fama-French methodology. Fiscal year data for year T is used to form portfolios
                          in July of year T+1, with returns measured through June T+2. This 6+ month lag ensures all accounting data is publicly
                          available before we "trade" on it, preventing look-ahead bias.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{snapshot?.meta?.return_convention || "july_june"}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-1">
                        Data tier
                        <InfoTooltip title="Data Tier" size={12}>
                          Tier 1 uses Financial Modeling Prep (FMP) data, which is accessible and cost-effective but may have coverage gaps.
                          Tier 2 would use CRSP/Compustat (the academic gold standard) for higher coverage and quality.
                          We document the tier to set appropriate expectations for data limitations.
                        </InfoTooltip>
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{snapshot?.meta?.data_tier || "tier1"}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>

          <h3 className="text-lg font-semibold text-foreground mt-6">4.2 Return timing (look-ahead mitigation)</h3>
          <p className="text-muted-foreground">
            The default convention uses July-June returns (Fama-French): fiscal-year accounting information for year <span className="font-mono">T</span>{" "}
            is mapped to subsequent returns from July <span className="font-mono">T+1</span> through June <span className="font-mono">T+2</span>.
            This timing reduces look-ahead bias from filing lags that can contaminate calendar-year sorts.
          </p>
          <div className="not-prose">
            <Formulas.TSR />
          </div>

          <h3 className="text-lg font-semibold text-foreground mt-6 flex items-center gap-2">
            4.3 Rolling windows, annual series, and monthly inference (what each object means)
          </h3>
          <p className="text-muted-foreground">
            <strong className="text-foreground">This distinction is critical for interpreting our results.</strong> We report three complementary objects, each with a specific interpretation:
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-2">
            <li>
              <strong className="text-foreground">Annual series (economic context){" "}
                <InfoTooltip term="non_overlapping" size={12} />
              :</strong> each year, we form R&amp;D quintiles using the prior fiscal
              year and measure the next July-June return. This produces one observation per year, which is the cleanest basis for inference because
              <em> the series is non-overlapping (reduces mechanical overlap)</em>. We still use Newey-West standard errors{" "}
              <InfoTooltip term="newey_west" size={12} />{" "}
              to account for any residual autocorrelation, but inference is inherently limited by the small number of annual observations.
            </li>
            <li>
              <strong className="text-foreground">Monthly tests (primary inference):</strong> we assess statistical significance using monthly factor spanning tests
              (does the premium have a statistically significant alpha after controlling for standard factors?) and monthly Fama-MacBeth regressions (does R&amp;D
              intensity predict returns after controlling for size and book-to-market?).
            </li>
            <li>
              <strong className="text-foreground">Rolling windows (descriptive only){" "}
                <InfoTooltip term="overlapping_windows" size={12} />
              :</strong> for a given window start, we assign quintiles once (based on
              that start-year signal) and then summarize outcomes over 5/10/20 years. <strong>Important:</strong> these overlapping windows are autocorrelated
              by construction (a 2000-2004 window shares 4 years with a 2001-2005 window). We use them to visualize regime dependence and horizon behavior,
              <em> not as standalone p-values</em>.
            </li>
          </ul>
          <div className="not-prose mt-3 p-3 rounded-lg border bg-amber-500/5 border-amber-500/20">
            <p className="text-sm text-muted-foreground">
              <strong className="text-foreground">Rationale:</strong> Rolling-window statistics are autocorrelated because adjacent windows share data, so treating them as independent
              observations can overstate significance. We explicitly separate descriptive (rolling) from inferential (monthly) evidence to avoid this pitfall.
            </p>
          </div>

          <h4 className="text-md font-semibold text-foreground mt-6">Statistical formulas used in this paper</h4>
          <p className="text-sm text-muted-foreground mb-3">
            Each formula box below includes a description explaining what it measures and how to interpret typical values.
          </p>
          <div className="not-prose grid md:grid-cols-2 gap-4">
            <Formulas.ANOVA />
            <Formulas.EtaSquared />
            <Formulas.CohensD />
            <Formulas.SharpeRatio />
            <Formulas.NeweyWest />
            <Formulas.MaxDrawdown />
          </div>

          <div className="not-prose mt-4 p-4 rounded-lg border bg-muted/30">
            <p className="font-semibold text-foreground mb-2">Bias controls and data integrity (summary)</p>
            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
              <li>Look-ahead mitigation via July-June timing (default).</li>
              <li>Point-in-time index membership used where historical constituent spans are available.</li>
              <li>Exits are handled via cash-after-exit return construction; delisting sensitivity is reported separately.</li>
              <li>Outlier controls: minimum revenue threshold and sector-aware R&amp;D-intensity caps.</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
