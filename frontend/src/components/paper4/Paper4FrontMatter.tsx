/**
 * PATH: frontend/src/components/paper4/Paper4FrontMatter.tsx
 * PURPOSE: Header, Abstract, Introduction, and Literature Review sections for Paper 4
 * WHY: Extracted from Paper4.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - UI components (Card, Badge, Button, Tooltip): rendering
 * - lucide-react icons: section icons
 * - react-router-dom Link: navigation
 */

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Download, FileText, BookOpen } from "lucide-react"
import { Link } from "react-router-dom"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface Paper4FrontMatterProps {
  totalRdSpend: number
  cohortSummary: any
  trendData: any[]
  handleDownload: () => void
}

export function Paper4FrontMatter({ totalRdSpend, cohortSummary, trendData, handleDownload }: Paper4FrontMatterProps) {
  return (
    <>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-amber-50 dark:bg-zinc-900 border border-amber-200 dark:border-amber-600/50 p-8">
        <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
        <div className="relative z-10">
          <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
            <Link to="/documentation" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Papers
            </Link>
                </TooltipTrigger>
                <TooltipContent>
                  Return to the documentation and papers list
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Print this paper as a PDF document
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          <div className="flex flex-wrap gap-2 mb-4">
            <Badge variant="outline" className="text-amber-500 border-amber-500/30">
            Sub-Research 4
          </Badge>
            <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
              Pre-print
            </Badge>
          </div>
          
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-amber-500">Fundamental</span>{" "}
            <span className="text-foreground">Value Creation Through R&D</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl">
            R&D Investment Beyond Stock Price Returns: Operational Performance and Competitive Position
          </p>
          
          <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
            <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">1 January 2026</span></div>
            <div><span className="text-muted-foreground">Focus:</span> <span className="text-foreground">Operational Metrics</span></div>
            <div><span className="text-muted-foreground">Total R&D:</span> <span className="text-foreground">${(totalRdSpend / 1e12).toFixed(1)}T Analyzed</span></div>
          </div>
        </div>
      </div>

      {/* Abstract */}
      <section id="abstract" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">Abstract</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none">
            <p className="text-lg leading-relaxed text-muted-foreground">
              While previous papers in this series focus on stock price returns, this paper examines 
              the <strong className="text-foreground">fundamental value creation</strong> aspect of R&D investment. 
              We analyze how R&D intensity relates to operational performance metrics including revenue 
              growth, profit margins, and competitive positioning. Our analysis covers 
              ${(totalRdSpend / 1e12).toFixed(1)} trillion in cumulative R&D spending across 
              {cohortSummary?.total_companies || "..."} S&P 500 companies over {trendData.length} years.
            </p>
            <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <p className="text-sm text-amber-400 font-medium mb-2">Key Findings:</p>
              <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                <li>• R&D creates intangible assets that manifest in improved operational performance</li>
                <li>• Payoffs from R&D often arrive with multi-year lags (varying by industry and project type)</li>
                <li>
                  • Effect size strengthens with investment horizon (η² increases from shorter to longer horizons; see the Main Paper for snapshot-pinned values)
                </li>
                <li>• R&D investments satisfy the VRIN framework for sustainable competitive advantage</li>
              </ul>
            </div>
          </CardContent>
        </Card>
        
        {/* Tier-1 Data Disclaimer */}
        <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
          <p className="text-sm text-amber-600 dark:text-amber-300">
            This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API.
            <strong> Operational metrics</strong> (revenue growth, margins, FCF) are <strong>illustrative</strong> based on literature estimates-
            not directly computed from this dataset. R&D spend totals are computed from the sample.
          </p>
        </div>
      </section>

      {/* Introduction */}
      <section id="introduction" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">1. Introduction</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <p className="text-muted-foreground">
              Corporate R&D investment represents a commitment to future value creation. Unlike 
              capital expenditures that create tangible assets, R&D spending generates intangible 
              assets-knowledge, patents, processes-that are difficult to measure but critical for 
              long-term competitive advantage.
            </p>
            <p className="text-muted-foreground">
              This paper examines the fundamental mechanisms through which R&D investment is associated with value creation:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• <strong className="text-foreground">Innovation Pipeline:</strong> How R&D translates to new products and services</li>
              <li>• <strong className="text-foreground">Competitive Moat:</strong> The role of patents and proprietary knowledge</li>
              <li>• <strong className="text-foreground">Operational Efficiency:</strong> Process improvements and cost reduction</li>
              <li>• <strong className="text-foreground">Time Lag Effects:</strong> The delay between R&D spending and returns</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      {/* Literature Review */}
      <section id="literature" className="scroll-mt-24">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">2. Literature Review</h2>
        </div>
        <Card>
          <CardContent className="pt-6 prose prose-invert max-w-none space-y-4">
            <h3 className="text-lg font-semibold text-foreground">2.1 R&D Time Lags</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Griliches (1981)</strong> established that R&D investments have significant 
              lags before generating measurable productivity gains. Many empirical studies emphasize that these payoff
              horizons are multi-year and vary materially by sector and project type.
            </p>
            <p className="text-muted-foreground">
              This lag structure motivates long-horizon return tests. Consistent with that intuition, our return-sort
              effect sizes strengthen over longer horizons (η² rises with horizon; see the Main Paper for snapshot-pinned values).
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.2 The VRIN Framework for Sustainable Advantage</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Barney (1991)</strong> introduced the VRIN framework (also called VRIO) for 
              evaluating resources that create sustainable competitive advantage. R&D-generated assets 
              often fulfill these criteria:
            </p>
            <div className="grid gap-3 md:grid-cols-2 mt-4">
              <div className="p-3 bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 rounded-lg">
                <span className="font-semibold text-blue-700 dark:text-blue-400">Valuable:</span>
                <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                  R&D leads to new products, cost reductions, or differentiation advantages. Successful 
                  drugs or patented technology directly add value.
                </p>
              </div>
              <div className="p-3 bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800 rounded-lg">
                <span className="font-semibold text-purple-700 dark:text-purple-400">Rare:</span>
                <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                  Cutting-edge research output (patents, trade secrets) is unique to the firm. Not every 
                  firm can develop a given innovation-successful R&D outcomes are relatively rare.
                </p>
              </div>
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                <span className="font-semibold text-emerald-700 dark:text-emerald-400">Inimitable:</span>
                <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                  Intangible know-how, protected IP, and tacit knowledge are difficult to replicate. 
                  Rivals may take years and substantial expense to reverse-engineer complex products.
                </p>
              </div>
              <div className="p-3 bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 rounded-lg">
                <span className="font-semibold text-amber-700 dark:text-amber-400">Non-substitutable:</span>
                <p className="text-slate-600 dark:text-slate-300 text-sm mt-1">
                  Proprietary platforms, network effects, and ecosystem advantages are not easily 
                  replaced by alternative approaches.
                </p>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Strategic Implications</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Porter (1992)</strong> emphasized the strategic importance of sustained R&D 
              investment. Companies that underinvest in R&D during downturns often lose market position 
              permanently. <strong className="text-foreground">Lev and Sougiannis (1996)</strong> documented that capitalizing R&D 
              (treating it as an asset) resulted in significant explanatory power for future earnings and 
              stock prices, confirming that R&D builds economic assets not reflected in traditional accounting.
            </p>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
