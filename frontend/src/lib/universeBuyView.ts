/**
 * What-to-Buy view resolution.
 *
 * Default is ranked R3 candidates (a usable table). Cleared-BUY shortlist is
 * opt-in — the waterfall often yields zero BUYs when catalysts are unknown,
 * and that must not blank the whole Universe page for investors.
 */

export type BuyViewMode = "candidates" | "cleared"

/** Resolve buy sub-view from URL search params (mode=buy assumed). */
export function resolveBuyViewMode(params: URLSearchParams): BuyViewMode {
  if (params.get("cleared") === "1" || params.get("review") === "0") {
    return "cleared"
  }
  // review=1, cleared=0, or no explicit cleared flag → candidates (default)
  return "candidates"
}
