/** 7.3 + 7.5: Factor spanning tests + Mispricing diagnostics. */

import { InfoTooltip } from "@/components/InfoTooltip"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Formulas } from "@/components/Formula"

export function RobustnessFactorTests({ spanningTests, mispricingTests }: { publicationStats: any; factorPremiumSeries: any[]; growthOf1: any[]; spanningTests: any; annualHmlData: any; snapshotPayload: any; mispricingTests: any; doubleSortTableRows: any[]; delistingSensitivity: any }) {
  return (
    <>
      <Card className="bg-card">
        <CardHeader>
          <CardTitle>7.3 Factor Spanning Tests</CardTitle>
          <CardDescription>Regression tests of whether the premium is explained by standard factor models.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 p-3 rounded-lg border bg-muted/30 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">What are factor spanning tests?</p>
            <p className="mb-2">
              We regress the R&amp;D premium (HML-RD) on standard academic factors to test whether it's explained by known risk exposures.
              If the alpha (intercept) is significant after controlling for factors, the R&amp;D premium is "distinct" and not just a combination
              of existing factors.
            </p>
            <Formulas.FactorAlpha />
            <p className="mt-2 text-xs">
              <strong>Models tested:</strong> FF3 (Market, Size, Value), FF5 (adds Profitability, Investment), FF6 (adds Momentum).
            </p>
          </div>
          {(spanningTests as any)?.models ? (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 font-semibold text-foreground">Model</th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">
                        <span className="flex items-center justify-end gap-1">
                          Alpha (%)
                          <InfoTooltip term="alpha" size={12} />
                        </span>
                      </th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">
                        <span className="flex items-center justify-end gap-1">
                          t-stat
                          <InfoTooltip term="t_statistic" size={12} />
                        </span>
                      </th>
                      <th className="text-right py-2 px-3 font-semibold text-foreground">
                        <span className="flex items-center justify-end gap-1">
                          R²
                          <InfoTooltip term="r_squared" size={12} />
                        </span>
                      </th>
                      <th className="text-center py-2 px-3 font-semibold text-foreground">
                        <span className="flex items-center justify-center gap-1">
                          Spanned?
                          <InfoTooltip term="spanned" size={12} />
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries((spanningTests as any).models).map(([model, data]: any) => (
                      <tr key={model} className="border-b border-border/50">
                        <td className="py-2 px-3 font-medium text-foreground">{model}</td>
                        <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha === "number" ? `${(data.alpha * 100).toFixed(2)}%` : "..."}</td>
                        <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.alpha_t === "number" ? data.alpha_t.toFixed(2) : "..."}</td>
                        <td className="py-2 px-3 text-right font-mono text-muted-foreground">{typeof data.r_squared === "number" ? `${(data.r_squared * 100).toFixed(1)}%` : "..."}</td>
                        <td className="py-2 px-3 text-center">
                          {data.is_spanned ? (
                            <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400">Yes</Badge>
                          ) : (
                            <Badge className="bg-green-600 text-white">No</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(spanningTests as any)?.interpretation?.summary && (
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <p className="text-sm text-muted-foreground">
                    <strong className="text-foreground">Interpretation:</strong> {(spanningTests as any).interpretation.summary}
                  </p>
                </div>
              )}
              <div className="p-4 rounded-lg bg-muted/30 border">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">How to read this:</strong> the key statistic is the regression alpha for the R&amp;D premium after
                  controlling for standard factors. A positive and statistically meaningful alpha is consistent with the premium not being fully explained
                  by those factor exposures. Factor alignment and availability are snapshot-dependent; when inputs are missing, we report the test as
                  unavailable rather than imputing it.
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p>Spanning tests are not available in this snapshot (factor inputs may be missing).</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; spanning tests).
          </p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>7.5 Mispricing vs Risk Diagnostics</CardTitle>
          <CardDescription>Stratification tests to distinguish mispricing from risk-based explanations.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="not-prose p-4 rounded-lg bg-muted/30 border text-sm">
            <p className="font-semibold text-foreground mb-2">How to interpret these tests</p>
            <p className="text-muted-foreground mb-2">
              If the premium is due to <strong>mispricing</strong>, it should be larger in stocks that are hard to arbitrage
              (small, volatile, low analyst coverage). If the premium is <strong>risk compensation</strong>, it should be
              similar across arbitrage-cost groups or larger in low-cost stocks.
            </p>
            <ul className="text-muted-foreground list-disc list-inside space-y-1">
              <li><strong>By Size:</strong> Small stocks are harder to arbitrage due to liquidity and short-sale costs.</li>
              <li><strong>By Volatility:</strong> High-volatility stocks carry more arbitrage risk (noise trader risk).</li>
              <li><strong>By Coverage:</strong> Low-coverage stocks have more information asymmetry.</li>
            </ul>
          </div>

          {(mispricingTests as any)?.tests ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                    By Size
                    <InfoTooltip title="Size stratification" size={14}>
                      Firms sorted into terciles by market cap. Mispricing theory predicts higher premium in small stocks.
                    </InfoTooltip>
                  </h4>
                  {Object.entries((mispricingTests as any).tests.by_size || {}).map(([k, v]: any) => (
                    <div key={k} className="flex justify-between text-sm py-1">
                      <span className="text-muted-foreground">{k}</span>
                      <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                    </div>
                  ))}
                </div>
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                    By Volatility
                    <InfoTooltip title="Volatility stratification" size={14}>
                      Firms sorted into terciles by return volatility. Mispricing theory predicts higher premium in volatile stocks.
                    </InfoTooltip>
                  </h4>
                  {Object.entries((mispricingTests as any).tests.by_volatility || {}).map(([k, v]: any) => (
                    <div key={k} className="flex justify-between text-sm py-1">
                      <span className="text-muted-foreground">{k}</span>
                      <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                    </div>
                  ))}
                </div>
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                    By Coverage
                    <InfoTooltip title="Analyst coverage stratification" size={14}>
                      Firms sorted into terciles by analyst coverage. Mispricing theory predicts higher premium in low-coverage stocks.
                      Note: "High" coverage may show n/a if insufficient data exists for that stratum.
                    </InfoTooltip>
                  </h4>
                  {Object.entries((mispricingTests as any).tests.by_coverage || {}).map(([k, v]: any) => (
                    <div key={k} className="flex justify-between text-sm py-1">
                      <span className="text-muted-foreground">{k}</span>
                      <span className="font-mono">{v?.premium !== null && v?.premium !== undefined ? `${v.premium.toFixed(1)}%` : "n/a"}</span>
                    </div>
                  ))}
                </div>
              </div>

              {(mispricingTests as any)?.interpretation?.likely_explanation && (
                <div className="p-4 rounded-lg bg-muted/30 border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={(mispricingTests as any).interpretation.likely_explanation === "MISPRICING" ? "bg-amber-600" : "bg-blue-600"}>
                      {(mispricingTests as any).interpretation.likely_explanation}
                    </Badge>
                    <InfoTooltip
                      term={(mispricingTests as any).interpretation.likely_explanation === "MISPRICING" ? "mispricing" : "risk_compensation"}
                      size={14}
                    />
                    <span className="text-sm text-muted-foreground">
                      ({(mispricingTests as any).interpretation.confidence} Confidence)
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{(mispricingTests as any).interpretation.explanation}</p>
                </div>
              )}

              <div className="p-3 rounded border bg-yellow-500/5 border-yellow-500/20 text-sm">
                <p className="text-muted-foreground">
                  <strong className="text-foreground">Interpretation caveat:</strong> These tests are suggestive, not definitive.
                  A risk-based interpretation does not preclude mispricing (and vice versa). The pattern here is that the premium
                  is present across size groups and is larger in high-volatility stocks, which is more consistent with risk compensation
                  but does not rule out partial mispricing.
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p>Mispricing diagnostics are not available in this snapshot.</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            Source: <code>/api/research/publication-snapshot</code> (frozen; mispricing diagnostics).
          </p>
        </CardContent>
      </Card>
    </>
  )
}
