/**
 * PATH: frontend/src/components/methodology/MethodologyReplication.tsx
 * PURPOSE: Replication Guide and Verification Checklist sections
 * WHY: Split from Methodology.tsx to stay under 300-line limit
 * DEPENDENCIES:
 *   - ui/card: layout primitives
 *   - lucide-react: section icons
 */

import { Card, CardContent } from "@/components/ui/card"
import {
  CheckCircle,
  AlertTriangle,
  ExternalLink,
  Code,
  GitBranch,
} from "lucide-react"

export function MethodologyReplication() {
  return (
    <>
      {/* Replication Guide */}
      <section id="replication" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <GitBranch className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">9. Replication Guide</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Code className="h-4 w-4" />
              Code Repository
            </h3>
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm text-muted-foreground mb-3">
                Full analysis code available on GitHub:
              </p>
              <a href="https://github.com/vastdreams/fse-rnd-alpha" className="text-primary hover:underline flex items-center gap-2">
                github.com/vastdreams/fse-rnd-alpha
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Quick Start</h3>
            <div className="p-4 bg-muted/50 rounded-lg border border-border font-mono text-xs space-y-2">
              <p className="text-muted-foreground"># Clone repository</p>
              <p className="text-foreground">git clone https://github.com/vastdreams/fse-rnd-alpha.git</p>
              <p className="text-foreground">cd fse-rnd-alpha</p>
              <p className="text-muted-foreground mt-2"># Install dependencies</p>
              <p className="text-foreground">pip install -r requirements.txt</p>
              <p className="text-muted-foreground mt-2"># Run full pipeline</p>
              <p className="text-foreground">python scripts/run_full_pipeline.py</p>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Key Scripts</h3>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• <code className="bg-muted px-1 rounded">scripts/ingest_fmp_data.py</code> - Data collection from FMP API</li>
              <li>• <code className="bg-muted px-1 rounded">scripts/compute_rd_factors.py</code> - R&D intensity calculation</li>
              <li>• <code className="bg-muted px-1 rounded">src/factors/quintile_analysis.py</code> - Quintile portfolio construction</li>
              <li>• <code className="bg-muted px-1 rounded">src/factors/anova_analysis.py</code> - Statistical tests</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      {/* Verification Checklist */}
      <section id="verification" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <CheckCircle className="h-5 w-5 text-emerald-500" />
          <h2 className="text-2xl font-bold">10. Verification Checklist</h2>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <p className="text-muted-foreground leading-relaxed">
              Use this checklist to verify results independently:
            </p>

            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Data Sources Accessible</p>
                  <p className="text-xs text-muted-foreground">SEC EDGAR is free; FMP requires API key (free tier available)</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">R&D Intensity Formula Correct</p>
                  <p className="text-xs text-muted-foreground">rd_expense / revenue × 100 matches GAAP reporting</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Quintile Assignment Uses pd.qcut</p>
                  <p className="text-xs text-muted-foreground">Equal-sized groups (not equal-spaced bins)</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Returns Are Total Shareholder Return</p>
                  <p className="text-xs text-muted-foreground">Approximated via split-adjusted close + dividend events (reinvested)</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Statistical Tests Use scipy.stats</p>
                  <p className="text-xs text-muted-foreground">f_oneway for ANOVA; standard effect size formulas</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Sector Bias Acknowledged</p>
                  <p className="text-xs text-muted-foreground">Results may partly reflect Tech/Healthcare performance</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground">Survivorship Bias Acknowledged</p>
                  <p className="text-xs text-muted-foreground">Point-in-time membership is enforced where spans exist; remaining coverage gaps are disclosed</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
