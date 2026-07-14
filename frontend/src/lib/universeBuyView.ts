/**
 * What-to-Buy view resolution.
 *
 * Plain /app (no explicit params) lands on the three-strata decision surface:
 * cleared theses → near-misses → weave-ranked. `review=1` keeps the classic
 * ranked candidates table; `cleared=1` keeps the cleared-only shortlist.
 * Deep links are preserved exactly.
 */

export type BuyViewMode = "strata" | "candidates" | "cleared"

/** Resolve buy sub-view from URL search params (mode=buy assumed). */
export function resolveBuyViewMode(params: URLSearchParams): BuyViewMode {
  if (params.get("cleared") === "1" || params.get("review") === "0") {
    return "cleared"
  }
  if (params.get("review") === "1") {
    return "candidates"
  }
  // Plain /app: the strata decision surface, never a silent fallback.
  return "strata"
}
