/**
 * PATH: src/components/research/StaticTabs.tsx
 * PURPOSE: Papers and Methodology tab contents (static / link-only — grouped because both are small)
 * WHY: Extracted from Research.tsx to keep each file under 300 lines
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Link } from "react-router-dom"

/* ── Papers Tab ──────────────────────────────────────────────────────────── */

export function PapersTab() {
  return (
    <Card>
      <CardHeader>
          <CardTitle>Main Paper & Sub-Research</CardTitle>
          <CardDescription>Website manuscript plus supporting deep dives (all results sourced from the API)</CardDescription>
      </CardHeader>
      <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <Link to="/papers/main">
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                <CardHeader>
                  <CardTitle className="text-lg">Main Paper: R&D Investment Intensity and Long-Term Stock Returns</CardTitle>
                  <CardDescription>Consolidated manuscript + investable strategy + frozen publication snapshot</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link to="/papers/1">
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                <CardHeader>
                  <CardTitle className="text-lg">Sub-Research 1: Returns & Inference</CardTitle>
                  <CardDescription>Core return premium results and inference visuals</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link to="/papers/2">
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                <CardHeader>
                  <CardTitle className="text-lg">Sub-Research 2: Sector Patterns</CardTitle>
                  <CardDescription>Cross-sector analysis of R&D investment patterns</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link to="/papers/3">
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                <CardHeader>
                  <CardTitle className="text-lg">Sub-Research 3: Factor Tests</CardTitle>
                  <CardDescription>Multi-factor analysis and portfolio construction</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link to="/papers/4">
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors">
                <CardHeader>
                  <CardTitle className="text-lg">Sub-Research 4: Mechanisms (Qualitative)</CardTitle>
                  <CardDescription>R&D investment beyond stock price returns</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          </div>
      </CardContent>
    </Card>
  )
}

/* ── Methodology Tab ─────────────────────────────────────────────────────── */

export function MethodologyTab() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Methodology</CardTitle>
        <CardDescription>Bias mitigation, data tier disclosure, and replication guidance</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>
          The platform's publication-grade methodology is documented on the dedicated Methodology page and in the
          Papers & Documentation hub.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/methodology" className="underline hover:no-underline">
            Open Methodology →
          </Link>
          <Link to="/documentation" className="underline hover:no-underline">
            Papers & Documentation →
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
