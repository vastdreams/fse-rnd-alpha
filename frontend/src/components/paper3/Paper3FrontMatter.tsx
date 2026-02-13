/**
 * PATH: frontend/src/components/paper3/Paper3FrontMatter.tsx
 * PURPOSE: Header, Abstract, Introduction, and Literature Review for Paper 3
 * WHY: Extracted from Paper3.tsx to keep files under 300 lines
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

interface Paper3FrontMatterProps {
  premiumData: any[]
  rdPremiumStats: any
  handleDownload: () => void
}

export function Paper3FrontMatter({ premiumData, rdPremiumStats, handleDownload }: Paper3FrontMatterProps) {
  return (
    <>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-purple-50 dark:bg-zinc-900 border border-purple-200 dark:border-purple-600/50 p-8">
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
            <Badge variant="outline" className="text-purple-500 border-purple-500/30">
              Sub-Research 3
            </Badge>
            <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
              Pre-print
            </Badge>
          </div>
          
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-purple-500">R&D</span>{" "}
            <span className="text-foreground">Return Premium Analysis</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl">
            High-Minus-Low R&D Portfolio Returns and Preliminary Factor Analysis
          </p>
          
          <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
            <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">1 January 2026</span></div>
            <div><span className="text-muted-foreground">Factor Model:</span> <span className="text-foreground">Fama-French + R&D</span></div>
            <div><span className="text-muted-foreground">Years:</span> <span className="text-foreground">{premiumData.length} Annual Observations</span></div>
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
              This paper examines the R&D-sorted return premium and whether it may represent a distinct 
              pricing factor. <strong className="text-amber-500">Note: Factor spanning tests require Fama-French
              factor inputs; when those inputs are unavailable, this page documents the premium but does not
              claim distinct factor status.</strong> 
              We construct a long-short portfolio (Q5 minus Q1 based on R&D intensity) and analyze 
              its performance characteristics over the full sample period. Our findings reveal a 
              statistically significant <strong className="text-foreground">mean annual R&D premium of
              {typeof rdPremiumStats?.mean === "number" ? ` ${rdPremiumStats.mean.toFixed(1)}%` : " -"} </strong>,
              with a t-statistic of {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}
              {typeof rdPremiumStats?.p_value === "number" ? ` (p = ${rdPremiumStats.p_value.toFixed(4)})` : ""}.
            </p>
            <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
              <p className="text-sm text-purple-400 font-medium mb-2">Key Findings:</p>
              <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                <li>• Mean annual R&D premium: {typeof rdPremiumStats?.mean === "number" ? `${rdPremiumStats.mean.toFixed(1)}%` : "..."}</li>
                <li>• Premium positive in {rdPremiumStats ? `${rdPremiumStats.positive_years} of ${rdPremiumStats.n_years}` : "..."} ({rdPremiumStats ? `${Math.round((rdPremiumStats.positive_years / rdPremiumStats.n_years) * 100)}%` : "..."} win rate)</li>
                <li>• t-statistic: {typeof rdPremiumStats?.t_statistic === "number" ? rdPremiumStats.t_statistic.toFixed(2) : "..."}</li>
                <li>• Factor spanning tests are shown below when factor inputs are available</li>
              </ul>
            </div>
          </CardContent>
        </Card>
        
        {/* Tier-1 Data Disclaimer */}
        <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
          <p className="text-sm text-amber-600 dark:text-amber-300">
            This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API with July-June return convention.
            Formal factor spanning tests against CRSP/FF factors are preliminary. See Online Appendix for robustness details.
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
              The relationship between R&D investment and stock returns has been extensively 
              documented. However, the question of whether R&D intensity constitutes a distinct 
              pricing factor-separate from the market, size, value, and momentum factors-remains 
              an active area of research.
            </p>
            <p className="text-muted-foreground">
              This paper contributes to the literature by:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• Constructing and analyzing an R&D-sorted portfolio (long Q5, short Q1)</li>
              <li>• Testing whether the R&D premium persists after controlling for known factors</li>
              <li>• Examining the time-series properties of the R&D premium</li>
              <li>• Providing practical implications for portfolio construction</li>
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
            <h3 className="text-lg font-semibold text-foreground">2.1 Evolution of Factor Models</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Fama and French (1993)</strong> established that market, size (SMB), 
              and value (HML) factors explain a substantial portion of cross-sectional return variation. 
              <strong className="text-foreground">Carhart (1997)</strong> added momentum as a fourth factor. 
              <strong className="text-foreground">Fama and French (2015)</strong> introduced profitability (RMW) 
              and investment (CMA) as fifth and sixth factors.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.2 The R&D Return Premium in Academic Literature</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Leung et al. (2020)</strong> found that the highest R&D decile 
              earned statistically significant abnormal performance in multi-factor models, and discuss whether the
              R&D-sorted return premium is distinct from standard factor exposures.
            </p>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Cai et al. (2023)</strong> found the R&D portfolio had persistently 
              significant positive abnormal performance in factor regressions. Notably, high-R&D firms tend to load
              negatively on value (HML), consistent with a growth tilt.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Independence from Standard Factors</h3>
            <p className="text-muted-foreground">
              The key finding across studies is that the R&D premium is <strong className="text-foreground">not subsumed</strong> by 
              market, size, value, momentum, investment, or profitability factors. This makes R&D intensity 
              a candidate for a new factor (or anomaly) in asset pricing models.
            </p>

            <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
              <p className="text-sm text-purple-400 font-medium mb-2">Our Contribution:</p>
              <p className="text-sm text-slate-700 dark:text-slate-200">
                We explicitly construct and test an R&D-sorted return premium (Q5-Q1) using S&P 500 data, examining its 
                time-series properties, persistence, and relationship to market conditions. All numeric results on this page
                are rendered directly from the platform's API endpoints.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
