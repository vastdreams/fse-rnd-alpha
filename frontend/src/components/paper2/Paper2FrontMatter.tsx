/**
 * PATH: frontend/src/components/paper2/Paper2FrontMatter.tsx
 * FILE_ID: PAPER2-FRONT-MATTER-001
 * PURPOSE: Header, Abstract, Introduction, and Literature Review for Paper2
 * WHY: Extracted from Paper2.tsx to keep files under 300 lines
 * DEPENDENCIES:
 * - @/components/ui/*: UI primitives
 * - lucide-react: icons
 * - react-router-dom: Link
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

interface Paper2FrontMatterProps {
  cohortSummary: any
  sectorData: any[]
  rdSampleYearRange: string | undefined
  handleDownload: () => void
}

export function Paper2FrontMatter({
  cohortSummary,
  sectorData,
  rdSampleYearRange,
  handleDownload,
}: Paper2FrontMatterProps) {
  return (
    <>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-blue-50 dark:bg-zinc-900 border border-blue-200 dark:border-blue-600/50 p-8">
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
            <Badge variant="outline" className="text-blue-500 border-blue-500/30">
              Sub-Research 2
            </Badge>
            <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
              Pre-print
            </Badge>
          </div>
          
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-blue-500">Industry-Specific</span>{" "}
            <span className="text-foreground">R&D Investment Patterns</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl">
            Cross-Sector Analysis of R&D Efficiency and Long-Term Value Creation
          </p>
          
          <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
            <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">1 January 2026</span></div>
            <div><span className="text-muted-foreground">Sample:</span> <span className="text-foreground">{cohortSummary?.total_companies || "..."} Companies</span></div>
            <div><span className="text-muted-foreground">Sectors:</span> <span className="text-foreground">{sectorData.length} Industries</span></div>
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
              This study examines industry-specific patterns in R&D investment across S&P 500 companies 
              over {rdSampleYearRange || "the sample period"}. Using GICS sector classifications, we analyze how R&D 
              intensity varies across 11 major industry sectors and identify sector-specific factors 
              that influence the relationship between R&D investment and firm performance. Our findings 
              reveal substantial heterogeneity in R&D practices, with <strong className="text-foreground">Healthcare</strong> and 
              <strong className="text-foreground"> Technology</strong> sectors demonstrating the highest R&D intensities 
              (averaging 15-20% of revenue), while asset-intensive sectors like Utilities and Real Estate 
              maintain minimal R&D expenditure (&lt;1%).
            </p>
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-2">Key Findings:</p>
              <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                <li>• {sectorData[0]?.sector || "Healthcare"} leads in R&D intensity at {sectorData[0]?.avg_rd_intensity?.toFixed(1) || "15"}%</li>
                <li>• Total S&P 500 R&D spend: ${sectorData.reduce((acc: number, s: any) => acc + s.totalRdB, 0).toFixed(0)}B cumulative ({rdSampleYearRange || "all years"})</li>
                <li>• R&D-return relationship holds within sectors</li>
                <li>• Sector context essential for cross-company comparisons</li>
              </ul>
            </div>
          </CardContent>
        </Card>
        
        {/* Tier-1 Data Disclaimer */}
        <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
          <p className="text-sm text-amber-600 dark:text-amber-300">
            This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API.
            Sector classifications follow GICS standards. R&D intensity ranges shown are illustrative of typical values.
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
              Research and Development (R&D) investment is a critical driver of corporate innovation 
              and long-term competitive advantage. However, the nature and intensity of R&D investment 
              varies dramatically across industries. A pharmaceutical company may invest 20% of revenue 
              in drug development, while a utility company may allocate less than 0.5% to R&D activities.
            </p>
            <p className="text-muted-foreground">
              This heterogeneity raises important questions for investors and corporate strategists:
            </p>
            <ul className="text-muted-foreground space-y-2">
              <li>• How should we benchmark R&D intensity across different sectors?</li>
              <li>• Does the R&D-return relationship hold within industry groups?</li>
              <li>• Which sectors demonstrate the most efficient R&D spending?</li>
            </ul>
            <p className="text-muted-foreground">
              This paper addresses these questions through comprehensive sector-level analysis 
              of R&D investment patterns among S&P 500 companies.
            </p>
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
            <h3 className="text-lg font-semibold text-foreground">2.1 Industry R&D Variation</h3>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Cohen and Klepper (1996)</strong> find that industry characteristics 
              such as technological opportunity and appropriability conditions influence optimal R&D intensity. 
              Industries with high knowledge spillovers (e.g., software) may have different R&D dynamics than 
              those with strong IP protection (e.g., pharmaceuticals).
            </p>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Hall, Jaffe, and Trajtenberg (2005)</strong> document that the 
              market value of R&D investments differs by sector, with technology-intensive industries showing 
              higher knowledge spillovers and stronger patent-value relationships.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.2 External Data Validation</h3>
            <p className="text-muted-foreground">
              According to <strong className="text-foreground">U.S. National Science Foundation (2023)</strong> statistics, 
              pharmaceutical and medicine manufacturers average about <strong className="text-foreground">16% R&D intensity</strong>, 
              and computer/electronic product manufacturers about <strong className="text-foreground">13%</strong>. Software 
              publishers and IT services firms typically invest 10-13% of revenue.
            </p>
            <p className="text-muted-foreground">
              <strong className="text-foreground">Vannelli (Knowledge Leaders Capital, 2022)</strong> found that 
              <strong className="text-foreground">339 of 500 S&P companies (68%)</strong> reported zero R&D expense in their 
              financials-largely in Financials, Utilities, Energy, and Retail. The remaining ~160 companies 
              that conduct R&D spent nearly <strong className="text-foreground">$479B on R&D</strong> versus $332B on capital 
              expenditures, underscoring how the innovation-intensive subset prioritizes intangibles over tangibles.
            </p>

            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-2">Research Focus:</p>
              <p className="text-sm text-slate-700 dark:text-slate-200">
                This study builds on this literature by examining whether the positive R&D-return 
                relationship documented at the aggregate level persists within industry sectors, and how 
                sector composition affects cross-sectional R&D factor performance.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
