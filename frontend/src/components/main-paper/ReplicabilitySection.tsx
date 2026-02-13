/**
 * PATH: frontend/src/components/main-paper/ReplicabilitySection.tsx
 * PURPOSE: Section 11 – Replicability with snapshot meta and open-source links.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react: Database, Github, ExternalLink icons
 *  - ui/card: Card + CardContent wrappers
 */

import { Database, Github, ExternalLink } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

export interface ReplicabilitySectionProps {
  snapshot: { meta?: { id?: string; git_commit?: string } } | undefined
  snapshotBuiltAtLabel: string | undefined
}

export function ReplicabilitySection({ snapshot, snapshotBuiltAtLabel }: ReplicabilitySectionProps) {
  return (
    <section id="replicability" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <Database className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">11. Replicability</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-4">
          <p className="text-muted-foreground">
            All tables and figures on this page are rendered from a frozen publication snapshot. The snapshot is built from a single computation run and
            is pinned to a specific code version for consistency.
          </p>
          <div className="not-prose grid gap-2 text-sm">
            <div className="p-3 rounded border bg-muted/30">
              <span className="text-muted-foreground">Snapshot ID:</span>{" "}
              <span className="font-mono">{snapshot?.meta?.id || "..."}</span>
            </div>
            <div className="p-3 rounded border bg-muted/30">
              <span className="text-muted-foreground">Built at:</span>{" "}
              <span className="font-mono">{snapshotBuiltAtLabel || "..."}</span>
            </div>
            <div className="p-3 rounded border bg-muted/30">
              <span className="text-muted-foreground">Git commit:</span>{" "}
              <span className="font-mono">{snapshot?.meta?.git_commit ? snapshot.meta.git_commit.slice(0, 12) : "..."}</span>
            </div>
          </div>
          <ul className="text-muted-foreground list-disc list-inside">
            <li>
              <code>./scripts/reproduce_publication.sh</code> (rebuilds core tables and snapshot inputs)
            </li>
            <li>
              <code>/api/research/publication-snapshot</code> (frozen dataset served to the paper pages)
            </li>
            <li>
              <code>DATA_AVAILABILITY.md</code> (licensing + replication)
            </li>
            <li>Snapshot meta (ID + commit hash) is the canonical anchor for all displayed numbers.</li>
          </ul>
          <div className="not-prose mt-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/30">
            <div className="flex items-center gap-3 mb-2">
              <Github className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              <span className="font-semibold text-foreground">Open Source</span>
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              The core research code is open source under MIT license. Clone the repository to replicate results or build upon this work.
            </p>
            <a
              href="https://github.com/vastdreams/fse-rnd-alpha"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium transition-colors"
            >
              <Github className="h-4 w-4" />
              github.com/vastdreams/fse-rnd-alpha
              <ExternalLink className="h-3 w-3 opacity-70" />
            </a>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
