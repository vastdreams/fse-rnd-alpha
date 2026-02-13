/**
 * PATH: frontend/src/components/paper3/Paper3ResultsTables.tsx
 * PURPOSE: Summary statistics, spanning tests, mispricing, and double-sort for Paper 3 Results
 * WHY: Extracted from Paper3.tsx to keep files under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface Paper3ResultsTablesProps {
  rdPremiumStats: any
  spanningTests: any
  mispricingTests: any
  doubleSortData: any
}

export function Paper3ResultsTables({ rdPremiumStats, spanningTests, mispricingTests, doubleSortData }: Paper3ResultsTablesProps) {
  return (
    <>
      {/* Statistics Summary */}
      <Card>
        <CardHeader>
          <CardTitle>5.4 Summary Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
              <h4 className="font-semibold text-slate-900 dark:text-white">Premium Statistics</h4>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Mean</span>
                <span className="font-mono text-green-600 dark:text-emerald-400">{typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(2)}%` : "..."}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Std Dev</span>
                <span className="font-mono text-slate-900 dark:text-slate-200">{typeof rdPremiumStats?.std === "number" ? `${rdPremiumStats.std.toFixed(2)}%` : "..."}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Sharpe Ratio</span>
                <span className="font-mono text-blue-600 dark:text-blue-400">{rdPremiumStats?.mean && rdPremiumStats?.std ? (rdPremiumStats.mean / rdPremiumStats.std).toFixed(2) : "..."}</span>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
              <h4 className="font-semibold text-slate-900 dark:text-white">Range</h4>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Minimum</span>
                <span className="font-mono text-red-600 dark:text-red-400">{typeof rdPremiumStats?.min === "number" ? `${rdPremiumStats.min.toFixed(1)}%` : "..."}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Maximum</span>
                <span className="font-mono text-green-600 dark:text-emerald-400">{typeof rdPremiumStats?.max === "number" ? `${rdPremiumStats.max.toFixed(1)}%` : "..."}</span>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
              <h4 className="font-semibold text-slate-900 dark:text-white">Significance</h4>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">t-Statistic</span>
                <span className="font-mono text-blue-600 dark:text-blue-400">{typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(3) : "..."}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">p-Value</span>
                <span className="font-mono text-purple-400">{typeof rdPremiumStats?.p_value === "number" ? rdPremiumStats.p_value.toFixed(4) : "..."}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Factor Spanning Tests */}
      <Card>
        <CardHeader>
          <CardTitle>5.4 Factor Spanning Tests</CardTitle>
          <CardDescription>
            Testing if R&D premium is explained by standard factor models (FF3, FF5, FF6)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {spanningTests?.models ? (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left py-2 px-3 font-semibold">Model</th>
                      <th className="text-right py-2 px-3 font-semibold">Alpha (%)</th>
                      <th className="text-right py-2 px-3 font-semibold">t-stat</th>
                      <th className="text-right py-2 px-3 font-semibold">R²</th>
                      <th className="text-center py-2 px-3 font-semibold">Spanned?</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(spanningTests.models).map(([model, data]: [string, any]) => (
                      <tr key={model} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 px-3 font-medium">{model}</td>
                        <td className="py-2 px-3 text-right font-mono">
                          {(data.alpha * 100).toFixed(2)}%
                        </td>
                        <td className="py-2 px-3 text-right font-mono">
                          {data.alpha_t.toFixed(2)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono">
                          {(data.r_squared * 100).toFixed(1)}%
                        </td>
                        <td className="py-2 px-3 text-center">
                          {data.is_spanned ? (
                            <Badge variant="outline" className="text-yellow-600">Yes</Badge>
                          ) : (
                            <Badge className="bg-green-600">No ✓</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800">
                <p className="text-sm text-purple-700 dark:text-purple-300">
                  <strong>Interpretation:</strong> {spanningTests.interpretation?.summary || "If alpha is significant, R&D premium represents a distinct return source."}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <p>Factor spanning tests require Fama-French factor data.</p>
              <p className="text-sm mt-2">See /api/research/spanning-tests-full for details.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mispricing vs Risk Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>5.5 Mispricing vs Risk Analysis</CardTitle>
          <CardDescription>
            Testing whether R&D premium is due to behavioral mispricing or rational risk compensation
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mispricingTests?.tests ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                {/* By Size */}
                <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Size</h4>
                  {Object.entries(mispricingTests.tests.by_size).map(([size, data]: [string, any]) => (
                    <div key={size} className="flex justify-between text-sm py-1">
                      <span className="text-slate-600 dark:text-slate-400">{size}</span>
                      <span className="font-mono text-slate-900 dark:text-white">
                        {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                      </span>
                    </div>
                  ))}
                </div>
                {/* By Volatility */}
                <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Volatility</h4>
                  {Object.entries(mispricingTests.tests.by_volatility).map(([vol, data]: [string, any]) => (
                    <div key={vol} className="flex justify-between text-sm py-1">
                      <span className="text-slate-600 dark:text-slate-400">{vol}</span>
                      <span className="font-mono text-slate-900 dark:text-white">
                        {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                      </span>
                    </div>
                  ))}
                </div>
                {/* By Coverage */}
                <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <h4 className="font-semibold mb-3 text-slate-900 dark:text-white">By Coverage</h4>
                  {Object.entries(mispricingTests.tests.by_coverage).map(([cov, data]: [string, any]) => (
                    <div key={cov} className="flex justify-between text-sm py-1">
                      <span className="text-slate-600 dark:text-slate-400">{cov}</span>
                      <span className="font-mono text-slate-900 dark:text-white">
                        {data.premium !== null ? `${data.premium.toFixed(1)}%` : "..."}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className={cn(
                "p-4 rounded-lg border",
                mispricingTests.interpretation.likely_explanation === "MISPRICING"
                  ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800"
                  : "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800"
              )}>
                <div className="flex items-center gap-2 mb-2">
                  <Badge className={
                    mispricingTests.interpretation.likely_explanation === "MISPRICING"
                      ? "bg-amber-600"
                      : "bg-blue-600"
                  }>
                    {mispricingTests.interpretation.likely_explanation}
                  </Badge>
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    ({mispricingTests.interpretation.confidence} Confidence)
                  </span>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {mispricingTests.interpretation.explanation}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <p>Loading mispricing analysis...</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Double-Sort Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>5.6 Size × R&D Double-Sort Analysis</CardTitle>
          <CardDescription>
            R&D premium within size groups (proves R&D is not just a size effect)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {doubleSortData?.rd_spreads_by_size ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(doubleSortData.rd_spreads_by_size).map(([size, data]: [string, any]) => (
                  <div key={size} className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-center">
                    <h4 className="font-semibold mb-2 text-slate-900 dark:text-white">{size} Caps</h4>
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {data.high_minus_low > 0 ? "+" : ""}{data.high_minus_low.toFixed(1)}%
                    </div>
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      t = {data.t_stat.toFixed(2)}
                    </div>
                    <Badge className={data.significant ? "bg-green-600 mt-2" : "bg-slate-500 mt-2"}>
                      {data.significant ? "Significant" : "Not Sig."}
                    </Badge>
                  </div>
                ))}
              </div>
              {doubleSortData.key_findings && (
                <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                  <p className="text-sm text-green-700 dark:text-green-300">
                    <strong>Key Finding:</strong>{" "}
                    {doubleSortData.key_findings.rd_is_not_just_size_effect
                      ? "R&D premium exists independently of size effect ✓"
                      : "Further analysis needed to separate R&D from size effect"}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <p>Loading double-sort analysis...</p>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  )
}
