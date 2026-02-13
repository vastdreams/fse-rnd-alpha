/**
 * PATH: frontend/src/components/main-paper/PaperHeader.tsx
 * PURPOSE: Hero header of the Main Paper with title, badges, author, and action buttons.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - react-router-dom Link: navigation
 *  - lucide-react: ArrowLeft, Download, Layers, Github icons
 *  - ui/badge + ui/button: styled primitives
 */

import { Link } from "react-router-dom"
import { ArrowLeft, Download, Layers, Github } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

export interface PaperHeaderProps {
  cohortSummary: { total_companies?: number } | undefined
  sampleYearRange: string | undefined
  returnConventionLabel: string
  snapshotBuiltAtLabel: string | undefined
  onDownloadPDF: () => void
}

export function PaperHeader({
  cohortSummary,
  sampleYearRange,
  returnConventionLabel,
  snapshotBuiltAtLabel,
  onDownloadPDF,
}: PaperHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-100 via-white to-slate-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 border border-slate-200 dark:border-slate-600 p-8">
      <div className="absolute inset-0 bg-grid-slate-100/[0.04] dark:bg-grid-slate-500/[0.03]" />
      <div className="relative z-10">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-6 no-print" data-pdf-hide="true">
          <Link
            to="/documentation"
            className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-primary"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Papers
          </Link>
          <div className="flex gap-2">
            <Link to="/whitepaper">
              <Button variant="default" size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                <Layers className="mr-2 h-4 w-4" />
                View Slide Deck
              </Button>
            </Link>
            <Button variant="outline" size="sm" onClick={onDownloadPDF}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
            <a
              href="https://github.com/vastdreams/fse-rnd-alpha"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="sm">
                <Github className="mr-2 h-4 w-4" />
                View Code
              </Button>
            </a>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          <Badge variant="outline" className="border-slate-400/40 dark:border-slate-500/50 dark:text-slate-300">
            Main Paper
          </Badge>
          <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-500/30 bg-amber-500/10">
            Frozen snapshot
          </Badge>
          <Badge variant="outline" className="text-blue-500 dark:text-blue-400 border-blue-500/30 bg-blue-500/10">
            Tier-1 data (FMP)
          </Badge>
        </div>

        <h1 className="text-4xl font-bold mb-4 text-slate-900 dark:text-white">
          R&D Investment Intensity and Long-Term Stock Returns
        </h1>
        <p className="text-xl text-slate-600 dark:text-slate-300 max-w-3xl">
          Empirical evidence on the relation between R&D intensity and subsequent stock returns.
        </p>

        <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-slate-200 dark:border-slate-600 text-sm">
          <div>
            <span className="text-slate-500 dark:text-slate-400">Author:</span>{" "}
            <span className="text-slate-900 dark:text-white">Abhishek Sehgal</span>
          </div>
          <div>
            <span className="text-slate-500 dark:text-slate-400">Sample:</span>{" "}
            <span className="text-slate-900 dark:text-white">{cohortSummary?.total_companies || "..."} companies</span>
          </div>
          <div>
            <span className="text-slate-500 dark:text-slate-400">Period:</span>{" "}
            <span className="text-slate-900 dark:text-white">{sampleYearRange || "..."}</span>
          </div>
          <div>
            <span className="text-slate-500 dark:text-slate-400">Return Convention:</span>{" "}
            <span className="text-slate-900 dark:text-white">{returnConventionLabel}</span>
          </div>
          <div>
            <span className="text-slate-500 dark:text-slate-400">Snapshot built:</span>{" "}
            <span className="text-slate-900 dark:text-white">{snapshotBuiltAtLabel || "..."}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
