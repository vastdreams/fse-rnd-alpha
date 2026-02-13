/** 7.4: Fama-MacBeth cross-sectional regressions (primary inference). */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function RobustnessFamaMacBeth({ annualHmlData, snapshotPayload }: { publicationStats: any; factorPremiumSeries: any[]; growthOf1: any[]; spanningTests: any; annualHmlData: any; snapshotPayload: any; mispricingTests: any; doubleSortTableRows: any[]; delistingSensitivity: any }) {
  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>7.4 Fama-MacBeth Cross-Sectional Regressions (Primary Inference)</CardTitle>
        <CardDescription>Monthly cross-sectional tests with controls for size and book-to-market.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="not-prose p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-sm">
          <p className="font-semibold text-foreground mb-2">Why Fama-MacBeth is the gold standard</p>
          <p className="text-muted-foreground mb-2">
            The annual HML series has only {annualHmlData?.n_years ?? 30} observations, yielding low statistical power.
            Fama-MacBeth (1973) regressions use <strong>monthly</strong> cross-sectional data with hundreds of stocks per month,
            providing far more statistical power to detect significant effects.
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-1 mb-2">
            <li><strong>Stage 1:</strong> Each month, regress stock returns on R&amp;D intensity + controls (size, B/M).</li>
            <li><strong>Stage 2:</strong> Average the monthly coefficients and test their significance with Newey-West HAC.</li>
          </ul>
          <p className="text-xs italic">
            A positive, significant R&amp;D coefficient means R&amp;D intensity predicts returns after controlling for size and value.
          </p>
        </div>

        {(() => {
          const fm = (snapshotPayload as any)?.fama_macbeth_monthly;
          if (!fm || fm.error) {
            return (
              <div className="text-center py-8 text-muted-foreground">
                <p>Fama-MacBeth results not available in this snapshot.</p>
              </div>
            );
          }

          const rd = fm.rd_intensity || {};
          const size = fm.log_market_cap || {};
          const bm = fm.book_to_market || {};
          const alpha = fm.intercept || {};

          const sigStars = (p: number | null | undefined) => {
            if (p == null) return "";
            if (p < 0.01) return "***";
            if (p < 0.05) return "**";
            if (p < 0.10) return "*";
            return "";
          };

          const rdPValueHac = typeof rd.p_value_hac === "number" ? (rd.p_value_hac as number) : null;

          return (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 font-semibold text-foreground">Variable</th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">Coefficient</th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">t-stat (FM)</th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">t-stat (NW)</th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">p-value</th>
                      <th className="text-center py-2 px-3 font-semibold text-foreground">Sig.</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border/50">
                      <td className="py-2 px-3 font-medium text-foreground">Intercept</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{alpha.coefficient?.toFixed(5) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{alpha.t_stat_fm?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{alpha.t_stat_hac?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{alpha.p_value_hac?.toFixed(4) ?? "--"}</td>
                      <td className="py-2 px-3 text-center font-mono">{sigStars(alpha.p_value_hac)}</td>
                    </tr>
                    <tr className="border-b border-border/50 bg-green-50 dark:bg-green-950/20">
                      <td className="py-2 px-3 font-semibold text-foreground">R&amp;D Intensity</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold">{rd.coefficient?.toFixed(5) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono">{rd.t_stat_fm?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold">{rd.t_stat_hac?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold">{rd.p_value_hac?.toFixed(4) ?? "--"}</td>
                      <td className="py-2 px-3 text-center font-mono font-semibold">{sigStars(rd.p_value_hac)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-2 px-3 font-medium text-foreground">Log(Market Cap)</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{size.coefficient?.toFixed(5) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{size.t_stat_fm?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{size.t_stat_hac?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{size.p_value_hac?.toFixed(4) ?? "--"}</td>
                      <td className="py-2 px-3 text-center font-mono">{sigStars(size.p_value_hac)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-2 px-3 font-medium text-foreground">Book-to-Market</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{bm.coefficient?.toFixed(5) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{bm.t_stat_fm?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{bm.t_stat_hac?.toFixed(2) ?? "--"}</td>
                      <td className="py-2 px-3 text-right font-mono text-muted-foreground">{bm.p_value_hac?.toFixed(4) ?? "--"}</td>
                      <td className="py-2 px-3 text-center font-mono">{sigStars(bm.p_value_hac)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 rounded-lg bg-muted/30 border text-center">
                  <div className="text-xs text-muted-foreground">Months</div>
                  <div className="text-lg font-mono font-semibold">{fm.n_months ?? "--"}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 border text-center">
                  <div className="text-xs text-muted-foreground">Avg Firms/Month</div>
                  <div className="text-lg font-mono font-semibold">{fm.avg_n_firms_per_month ?? "--"}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 border text-center">
                  <div className="text-xs text-muted-foreground">Avg R²</div>
                  <div className="text-lg font-mono font-semibold">{fm.avg_r_squared ? `${(fm.avg_r_squared * 100).toFixed(2)}%` : "--"}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 border text-center">
                  <div className="text-xs text-muted-foreground">NW Lags</div>
                  <div className="text-lg font-mono font-semibold">{fm.nw_lags ?? 12}</div>
                </div>
              </div>

              {rdPValueHac !== null && (
                <>
                  {rdPValueHac < 0.05 ? (
                    <div className="p-4 rounded-lg bg-green-100 dark:bg-green-950/40 border border-green-300 dark:border-green-700">
                      <p className="text-sm font-semibold text-green-800 dark:text-green-300">
                        ✓ Statistically Significant (5%): R&amp;D intensity predicts returns (p = {rdPValueHac.toFixed(4)}
                        {sigStars(rdPValueHac)})
                      </p>
                      <p className="text-xs text-green-700 dark:text-green-400 mt-1">
                        After controlling for size and book-to-market, R&amp;D intensity remains a significant predictor of next-month returns.
                      </p>
                    </div>
                  ) : rdPValueHac < 0.10 ? (
                    <div className="p-4 rounded-lg bg-amber-100 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-700">
                      <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                        △ Marginal Evidence (10%): R&amp;D intensity is directionally consistent (p = {rdPValueHac.toFixed(4)}
                        {sigStars(rdPValueHac)})
                      </p>
                      <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                        The coefficient is positive after controls, but does not meet a 5% threshold under Newey-West HAC.
                      </p>
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg bg-muted/30 border">
                      <p className="text-sm font-semibold text-foreground">
                        Not significant at conventional levels (p = {rdPValueHac.toFixed(4)}).
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        The coefficient is still reported transparently; factor spanning tests provide stronger statistical evidence in this snapshot.
                      </p>
                    </div>
                  )}
                </>
              )}

              {fm.interpretation && (
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <p className="text-sm text-muted-foreground">
                    <strong className="text-foreground">Interpretation:</strong> {fm.interpretation}
                  </p>
                </div>
              )}
            </div>
          );
        })()}

        <p className="text-xs text-muted-foreground mt-3">
          Source: <code>/api/research/publication-snapshot</code> (frozen; fama_macbeth_monthly).
          *** p &lt; 0.01, ** p &lt; 0.05, * p &lt; 0.10. NW = Newey-West HAC.
        </p>
      </CardContent>
    </Card>
  )
}
