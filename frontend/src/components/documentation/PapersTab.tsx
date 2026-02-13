/**
 * PATH: src/components/documentation/PapersTab.tsx
 * PURPOSE: Renders the "Papers" tab content for the Documentation page
 * WHY: Extracted from Documentation.tsx to keep files under 300 lines
 * FLOW:
 * ┌───────────────────┐   ┌──────────────────┐   ┌─────────────┐
 * │ Numeric props from │ → │ Renders paper     │ → │ JSX output  │
 * │ parent queries     │   │ cards + summary   │   │             │
 * └───────────────────┘   └──────────────────┘   └─────────────┘
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  TrendingUp, BarChart3, Layers, Award, FileText,
  Presentation, ArrowRight, Clock,
} from "lucide-react"
import { Link } from "react-router-dom"

const PAPERS: Array<{
  id: string
  title: string
  subtitle: string
  icon: typeof FileText
  color: keyof typeof COLOR_CLASSES
  route: string
  badgeLabel: string
}> = [
  {
    id: "main",
    title: "Main Paper",
    subtitle: "Consolidated manuscript + investable strategy + frozen publication snapshot",
    icon: FileText,
    color: "slate",
    route: "/papers/main",
    badgeLabel: "Main Paper",
  },
  {
    id: "1",
    title: "Sub-Research 1: Returns & Inference",
    subtitle: "Core returns results, annual HML series, and rolling-window context",
    icon: TrendingUp,
    color: "emerald",
    route: "/papers/1",
    badgeLabel: "Sub-Research 1",
  },
  {
    id: "2",
    title: "Sub-Research 2: Sector Patterns",
    subtitle: "Cross-sector R&D intensity and data coverage",
    icon: Layers,
    color: "blue",
    route: "/papers/2",
    badgeLabel: "Sub-Research 2",
  },
  {
    id: "3",
    title: "Sub-Research 3: Factor Tests",
    subtitle: "Robustness suite and factor-model diagnostics",
    icon: BarChart3,
    color: "purple",
    route: "/papers/3",
    badgeLabel: "Sub-Research 3",
  },
  {
    id: "4",
    title: "Sub-Research 4: Mechanisms (Qualitative)",
    subtitle: "Interpretation and mechanism discussion (no computed operational metrics)",
    icon: Award,
    color: "amber",
    route: "/papers/4",
    badgeLabel: "Sub-Research 4",
  },
]

const COLOR_CLASSES = {
  slate: {
    card: "from-slate-500/10 to-slate-600/5 border-slate-500/20 hover:border-slate-500/40",
    icon: "text-slate-500",
    badge: "bg-slate-500/10 text-slate-400",
  },
  emerald: {
    card: "from-emerald-500/10 to-emerald-600/5 border-emerald-500/20 hover:border-emerald-500/40",
    icon: "text-emerald-500",
    badge: "bg-emerald-500/10 text-emerald-400",
  },
  blue: {
    card: "from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40",
    icon: "text-blue-500",
    badge: "bg-blue-500/10 text-blue-400",
  },
  purple: {
    card: "from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40",
    icon: "text-purple-500",
    badge: "bg-purple-500/10 text-purple-400",
  },
  amber: {
    card: "from-amber-500/10 to-amber-600/5 border-amber-500/20 hover:border-amber-500/40",
    icon: "text-amber-500",
    badge: "bg-amber-500/10 text-amber-400",
  },
} as const

export interface PapersTabProps {
  premium5yr: number | undefined
  premium10yr: number | undefined
  premium20yr: number | undefined
  eta5yr: number | undefined
  eta20yr: number | undefined
  topSector: { sector: string; avg_rd_intensity: number } | undefined
}

export function PapersTab({ premium5yr, premium10yr, premium20yr, eta5yr, eta20yr, topSector }: PapersTabProps) {
  return (
    <div className="space-y-6">
      {/* Start Here: Whitepaper */}
      <div className="rounded-xl bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-blue-500/10 border-2 border-emerald-500/30 p-6">
        <div className="flex flex-col md:flex-row gap-6 items-start">
          <div className="p-3 rounded-xl bg-emerald-500/20">
            <Presentation className="h-8 w-8 text-emerald-500" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Start Here</Badge>
              <Badge variant="outline" className="text-muted-foreground">
                <Clock className="h-3 w-3 mr-1" />
                ~5 min read
              </Badge>
            </div>
            <h3 className="text-2xl font-bold mb-2">Whitepaper Slide Deck</h3>
            <p className="text-muted-foreground mb-4">
              A practitioner-friendly 12-slide deck covering key findings, definitions, methodology, and implementation guidance. 
              Perfect for getting up to speed quickly or sharing with colleagues.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/whitepaper">
                <Button className="bg-emerald-600 hover:bg-emerald-700">
                  View Slide Deck
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/papers/main">
                <Button variant="outline">
                  Or read the full Main Paper
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Reading Path Guide */}
      <Card className="border-slate-700/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Reading Path</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
              <span className="font-bold text-emerald-500">1</span>
              <div>
                <p className="font-medium text-sm">Quick Overview</p>
                <p className="text-xs text-muted-foreground">Whitepaper (12 slides)</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
              <span className="font-bold text-blue-500">2</span>
              <div>
                <p className="font-medium text-sm">Full Methods & Results</p>
                <p className="text-xs text-muted-foreground">Main Paper</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
              <span className="font-bold text-purple-500">3</span>
              <div>
                <p className="font-medium text-sm">Deep Dives</p>
                <p className="text-xs text-muted-foreground">Sub-Research 1-4</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Paper Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {PAPERS.map((paper) => {
          const Icon = paper.icon
          const colorClass = COLOR_CLASSES[paper.color]
          
          return (
            <Link key={paper.id} to={paper.route}>
              <Card className={`cursor-pointer transition-all bg-gradient-to-br ${colorClass.card} h-full`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className={`p-2 rounded-lg ${colorClass.badge}`}>
                      <Icon className={`h-5 w-5 ${colorClass.icon}`} />
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {paper.badgeLabel}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl mt-3">{paper.title}</CardTitle>
                  <CardDescription className="text-base">{paper.subtitle}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Click to view interactive charts and full analysis →
                  </p>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      {/* Research Summary */}
      <Card className="border-slate-700/50">
        <CardHeader>
          <CardTitle>Research Summary</CardTitle>
          <CardDescription>Key findings from our R&D investment analysis</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 border rounded-lg bg-emerald-500/5 border-emerald-500/20">
              <h4 className="font-semibold mb-2 text-emerald-400">Key Finding #1</h4>
              <p className="text-sm text-muted-foreground">
                High-R&D (Q5) outperforms low-R&D (Q1) by{" "}
                <strong>
                  {premium5yr !== undefined ? `${premium5yr >= 0 ? "+" : ""}${premium5yr.toFixed(2)}%` : "..."} (5yr)
                  {" "}to{" "}
                  {premium20yr !== undefined ? `${premium20yr >= 0 ? "+" : ""}${premium20yr.toFixed(2)}%` : "..."} (20yr)
                </strong>
                {" "}per year (rolling-window averages).
              </p>
            </div>
            <div className="p-4 border rounded-lg bg-blue-500/5 border-blue-500/20">
              <h4 className="font-semibold mb-2 text-blue-400">Key Finding #2</h4>
              <p className="text-sm text-muted-foreground">
                Premium magnitude declines with horizon:{" "}
                <strong>
                  {premium5yr !== undefined ? `${premium5yr.toFixed(2)}%` : "..."} (5yr),{" "}
                  {premium10yr !== undefined ? `${premium10yr.toFixed(2)}%` : "..."} (10yr),{" "}
                  {premium20yr !== undefined ? `${premium20yr.toFixed(2)}%` : "..."} (20yr)
                </strong>.
              </p>
            </div>
            <div className="p-4 border rounded-lg bg-purple-500/5 border-purple-500/20">
              <h4 className="font-semibold mb-2 text-purple-400">Key Finding #3</h4>
              <p className="text-sm text-muted-foreground">
                Top sector by average R&D intensity:{" "}
                <strong>
                  {topSector ? `${topSector.sector} (${topSector.avg_rd_intensity.toFixed(2)}%)` : "..."}
                </strong>.
              </p>
            </div>
            <div className="p-4 border rounded-lg bg-amber-500/5 border-amber-500/20">
              <h4 className="font-semibold mb-2 text-amber-400">Key Finding #4</h4>
              <p className="text-sm text-muted-foreground">
                Statistical inference rejects equal means across quintiles (ANOVA), with large effect sizes:
                <strong>
                  {" "}η² {eta5yr !== undefined ? eta5yr.toFixed(3) : "..."} (5yr) → {eta20yr !== undefined ? eta20yr.toFixed(3) : "..."} (20yr)
                </strong>.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
