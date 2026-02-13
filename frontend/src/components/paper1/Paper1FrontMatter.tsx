/** Paper1FrontMatter — Header + Abstract + Introduction + Literature Review */
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

interface Paper1FrontMatterProps {
  sampleYearRange: string | undefined
  cohortSummary: any
  aggregateAnova: any
  handlePrintPDF: () => void
}

export function Paper1FrontMatter({ sampleYearRange, cohortSummary, aggregateAnova, handlePrintPDF }: Paper1FrontMatterProps) {
  return (
    <>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-emerald-50 dark:bg-zinc-900 border border-emerald-200 dark:border-emerald-600/50 p-8">
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
                  <Button variant="outline" size="sm" onClick={handlePrintPDF}>
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
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">
              Sub-Research 1
            </Badge>
            <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10">
              Pre-print
            </Badge>
          </div>
          
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-emerald-500">R&D</span>{" "}
            <span className="text-foreground">Investment Intensity and Long-Term Shareholder Returns</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl">
            Evidence from S&amp;P 500 Companies ({sampleYearRange || "the sample period"})
          </p>
          
          <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
            <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            <div><span className="text-muted-foreground">Date:</span> <span className="text-foreground">1 January 2026</span></div>
            <div><span className="text-muted-foreground">Sample:</span> <span className="text-foreground">{cohortSummary?.total_companies || "..."} Companies</span></div>
            <div><span className="text-muted-foreground">Period:</span> <span className="text-foreground">{sampleYearRange || "..."}</span></div>
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
              This study examines the relationship between Research & Development (R&D) investment intensity 
              and long-term shareholder returns among S&amp;P 500 companies over {sampleYearRange || "the sample period"}. 
              Using a quintile-based portfolio approach, we find that companies in the highest R&amp;D intensity 
              quintile (Q5) consistently outperform those in the lowest quintile (Q1). The horizon-by-horizon
              magnitudes and effect sizes are reported from the research endpoints rendered on this page.
              Our findings suggest that 
              sustained R&D investment creates durable competitive advantages that translate into superior 
              long-term shareholder returns.
            </p>
            <div className="mt-4 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
              <p className="text-sm text-green-600 dark:text-emerald-400 font-medium mb-2">Key Findings:</p>
              <ul className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
                <li>
                  • Q5 (High R&amp;D) outperforms Q1 (Low R&amp;D) by{" "}
                  <strong className="text-foreground">
                    {typeof aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference === "number"
                      ? `${aggregateAnova["5yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["5yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                      : "..."}
                  </strong>{" "}
                  (5yr),{" "}
                  <strong className="text-foreground">
                    {typeof aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference === "number"
                      ? `${aggregateAnova["10yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["10yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                      : "..."}
                  </strong>{" "}
                  (10yr),{" "}
                  <strong className="text-foreground">
                    {typeof aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference === "number"
                      ? `${aggregateAnova["20yr"].ttest_high_vs_low.mean_difference >= 0 ? "+" : ""}${aggregateAnova["20yr"].ttest_high_vs_low.mean_difference.toFixed(2)}%`
                      : "..."}
                  </strong>{" "}
                  (20yr) in annualized returns (Q5 − Q1).
                </li>
                <li>
                  • Effect size (Cohen's d, 20yr):{" "}
                  <strong className="text-foreground">
                    {typeof aggregateAnova?.["20yr"]?.ttest_high_vs_low?.cohens_d === "number"
                      ? aggregateAnova["20yr"].ttest_high_vs_low.cohens_d.toFixed(3)
                      : "..."}
                  </strong>
                </li>
                <li>• Statistical significance is assessed per horizon using ANOVA and high-vs-low t-tests (see Results).</li>
                <li>• The R&amp;D premium persists through multiple market cycles (descriptive).</li>
              </ul>
            </div>
          </CardContent>
        </Card>
        
        {/* Tier-1 Data Disclaimer */}
        <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">Data Tier Disclosure</p>
          <p className="text-sm text-amber-600 dark:text-amber-300">
            This analysis uses <strong>Tier-1 data</strong> from Financial Modeling Prep (FMP) API. 
            Survivorship bias is mitigated via point-in-time constituent spans (where available) and explicit exit handling (cash-after-exit), with delisting uncertainty addressed via sensitivity analysis (we do not inject a single CRSP-style delisting-return field).
            For top-tier academic journals, Tier-2 data (CRSP/Compustat) would be required. 
            See{" "}
            <Link to="/documentation" className="underline hover:no-underline">
              Papers & Documentation
            </Link>{" "}
            for the repository's <code>DATA_AVAILABILITY.md</code> and full provenance.
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
            <p className="text-muted-foreground leading-relaxed">
              The role of Research and Development (R&D) investment in creating firm value has been a 
              central question in finance and economics literature. While R&D expenditures are often 
              viewed as risky investments with uncertain outcomes, they also represent a firm's commitment 
              to innovation and future growth potential.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              This paper investigates whether companies with higher R&D intensity-measured as R&D expenditure 
              as a percentage of revenue-deliver superior long-term returns to shareholders. We analyze 
              all S&amp;P 500 constituents over {sampleYearRange || "the sample period"}, creating quintile portfolios based on R&amp;D 
              intensity and tracking their performance across multiple time horizons.
            </p>
            <h3 className="text-lg font-semibold text-foreground mt-6">Research Questions</h3>
            <ol className="text-muted-foreground space-y-2 list-decimal list-inside">
              <li>Do high-R&D companies generate higher long-term shareholder returns?</li>
              <li>How does the R&D-return relationship vary across different investment horizons?</li>
              <li>Is the R&D premium economically meaningful, and how is statistical significance assessed?</li>
              <li>Does the effect persist across different market conditions?</li>
            </ol>
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
            <h3 className="text-lg font-semibold text-foreground">2.1 Early Evidence of R&D Undervaluation</h3>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Lev and Sougiannis (1996)</strong> demonstrated 
              that R&D capital is associated with subsequent stock returns, suggesting markets systematically 
              undervalue intangible investments due to accounting rules that expense R&D immediately.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Chan, Lakonishok, and Sougiannis (2001)</strong> found that 
              firms with high R&D-to-market value earned significant positive abnormal returns. They labeled 
              this the "R&D undervaluation anomaly"-the market appears slow to recognize the value of innovation.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Eberhart, Maxwell, and Siddique (2004)</strong> examined firms 
              that substantially increased R&D spending and found significantly positive long-term abnormal 
              returns in the years following the increase, concluding that R&D increases are beneficial 
              investments that the market is slow to recognize.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.2 Recent Quantitative Evidence</h3>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Cai, Cooper, and He (2023)</strong> provide a practitioner-facing synthesis
              of the ``R\&D premium'' and discuss portfolio construction considerations (horizon choice, sector structure,
              and implementability) alongside empirical evidence.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Hou et al. (2022)</strong> demonstrated that this R&D phenomenon 
              is not necessarily confined to a single market. Cross-market results vary by sample construction and
              measurement choices, motivating careful replication and transparent disclosure of data sources.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Cai, Cooper, and He (2023)</strong> in The Journal of Investing 
              discuss practitioner-facing portfolio construction considerations for R&D-related signals, including
              risk, sector exposure, and implementability.
            </p>

            <h3 className="text-lg font-semibold text-foreground mt-6">2.3 Interpretations: Mispricing vs. Risk</h3>
            <div className="grid gap-4 md:grid-cols-2 mt-4">
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                <h4 className="text-purple-700 dark:text-purple-400 font-semibold mb-2">Mispricing Hypothesis</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Markets systematically undervalue intangibles because accounting rules expense R&D, 
                  depressing reported earnings. Investors anchoring on near-term metrics underweight 
                  long-term innovation value.
                </p>
              </div>
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                <h4 className="text-blue-600 dark:text-blue-400 font-semibold mb-2">Risk Hypothesis</h4>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  High R&D firms carry unique systematic risks (technological disruption, project failure) 
                  that investors require extra return for bearing. The R&D factor correlates with state 
                  variables like default spreads and dividend yield shocks.
                </p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg">
              <p className="text-sm text-green-600 dark:text-emerald-400 font-medium mb-2">Our Contribution:</p>
              <p className="text-sm text-slate-700 dark:text-slate-200">
                This study extends prior literature by examining the R&D-return relationship over an 
                extended sample period ({sampleYearRange || "see header"}) using a comprehensive S&amp;P 500 sample, with particular attention to 
                how the relationship varies across investment horizons. We report horizon-specific Q5-Q1 premiums, p-values, and effect sizes for
                5/10/20-year windows using the platform's research endpoints (rather than hardcoding static values in the prose).
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
