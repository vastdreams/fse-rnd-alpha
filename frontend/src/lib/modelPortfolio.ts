/**
 * PATH: frontend/src/lib/modelPortfolio.ts
 * PURPOSE: Transparent 10-name research model portfolio, re-tiered by the
 * 2026-07-12 AI audit.
 *
 * The paper's full 12-condition Table-20 filter passes exactly four names
 * (FRSH, DOCU, PCTY, WDAY). At 2026-07-11 live prices WDAY's own kill
 * criterion has fired (margin of safety went negative), so it sits in an
 * "on hold" tier. The other six names each fail at least one real paper gate
 * and are labelled watchlist — kept visible for research, not implied buys.
 * Weights stay equal at 10% as a neutral research convention; the tiers are
 * the honest signal.
 */

export type ModelPortfolioTier = "paper_core" | "paper_on_hold" | "watchlist_candidate"

export type ModelPortfolioHolding = {
  ticker: string
  weight: number
  tier: ModelPortfolioTier
  basis: string
}

export const MODEL_PORTFOLIO_10: ModelPortfolioHolding[] = [
  {
    ticker: "FRSH",
    weight: 0.1,
    tier: "paper_core",
    basis: "Passes all 12 paper gates; widest margin of safety; 10-K claims verified verbatim.",
  },
  {
    ticker: "DOCU",
    weight: 0.1,
    tier: "paper_core",
    basis: "Passes the full paper filter; thin +6% cushion and an unverified low band (data bug).",
  },
  {
    ticker: "PCTY",
    weight: 0.1,
    tier: "paper_core",
    basis: "Passes the full paper filter; note ~1/3 of FCF is client-float interest.",
  },
  {
    ticker: "WDAY",
    weight: 0.1,
    tier: "paper_on_hold",
    basis: "Paper Tier 2, but its kill criterion fired: live margin of safety is negative. Hold off / trim per paper protocol.",
  },
  {
    ticker: "MNDY",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Fails the improving-margin gate (−4.5pp). Upside leans on a margin glide the trend contradicts.",
  },
  {
    ticker: "PAYC",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Fails the filing-quality gate (negative AI text stance). Fundamentals otherwise solid.",
  },
  {
    ticker: "NICE",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Closest miss: fails the improving-margin gate by −0.4pp; no filing overlay exists.",
  },
  {
    ticker: "DBX",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Fails the growth gate (0.4% CAGR vs ≥5%). Harvest/buyback story, not the paper thesis.",
  },
  {
    ticker: "APPF",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Fails the filing-quality gate and now trades above the model's median fair value.",
  },
  {
    ticker: "BILL",
    weight: 0.1,
    tier: "watchlist_candidate",
    basis: "Excluded by name in the paper's own code (payments/float carve-out).",
  },
]

export const MODEL_PORTFOLIO_TICKERS = MODEL_PORTFOLIO_10.map((holding) => holding.ticker)
/** Bump when the default book composition changes so empty/stale 4-name books re-seed. */
export const MODEL_PORTFOLIO_INITIALISED_KEY = "fse_model_portfolio_10_initialised_v2"

export function modelHolding(ticker: string) {
  return MODEL_PORTFOLIO_10.find((holding) => holding.ticker === ticker)
}

export function modelTierLabel(tier: ModelPortfolioTier) {
  if (tier === "paper_core") return "Paper core · audit pass"
  if (tier === "paper_on_hold") return "On hold · kill criterion triggered"
  return "Watchlist · fails a paper gate"
}
