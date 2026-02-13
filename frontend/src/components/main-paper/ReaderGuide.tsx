/**
 * PATH: frontend/src/components/main-paper/ReaderGuide.tsx
 * PURPOSE: Reader Guide callout box with three reading-depth options.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - react-router-dom Link: internal navigation
 *  - lucide-react BookOpen: section icon
 */

import { Link } from "react-router-dom"
import { BookOpen } from "lucide-react"

export function ReaderGuide() {
  return (
    <div className="rounded-xl bg-gradient-to-br from-emerald-50 via-white to-blue-50 dark:from-emerald-950/30 dark:via-slate-950/20 dark:to-blue-950/30 border border-slate-200/70 dark:border-slate-800 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-emerald-100/70 dark:bg-emerald-900/40">
          <BookOpen className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-foreground leading-none">Reader Guide</h3>
          <p className="text-sm text-muted-foreground mt-1">Pick the depth that matches your time.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-emerald-200/70 dark:border-emerald-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
            Quick overview
          </div>
          <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
            Start with the{" "}
            <Link to="/whitepaper" className="text-emerald-700 dark:text-emerald-400 hover:underline font-semibold">
              Whitepaper slide deck
            </Link>{" "}
            (11 slides, ~5 min).
          </p>
        </div>

        <div className="rounded-lg border border-blue-200/70 dark:border-blue-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
            Full methods
          </div>
          <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
            You're in the right place. This Main Paper contains full methodology, all tables, and references.
          </p>
        </div>

        <div className="rounded-lg border border-purple-200/70 dark:border-purple-800/60 bg-white/70 dark:bg-slate-950/30 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-purple-700 dark:text-purple-400">
            Deep dives
          </div>
          <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
            Jump to{" "}
            <a href="#appendix" className="text-purple-700 dark:text-purple-400 hover:underline font-semibold">
              Supporting Notes
            </a>{" "}
            for sector analysis, factor tests, and robustness checks.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href="#sector"
              className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
            >
              Sector
            </a>
            <a
              href="#robustness"
              className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
            >
              Factor tests
            </a>
            <a
              href="#appendix"
              className="text-xs px-2 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-800/60"
            >
              Appendix
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
