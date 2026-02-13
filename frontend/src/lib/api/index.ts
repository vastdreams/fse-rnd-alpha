/**
 * PATH: src/lib/api/index.ts
 * PURPOSE: Barrel re-export for all API modules
 * WHY: Maintains backward compatibility — all consumers import from "@/lib/api"
 */

// Re-export all types
export type * from "./types"

// Re-export API objects
export { api } from "./general"
export { portfolioApi, companyApi, papersApi } from "./portfolio"

// Re-export base utilities (for advanced usage)
export { fetchApi, API_BASE } from "./base"
