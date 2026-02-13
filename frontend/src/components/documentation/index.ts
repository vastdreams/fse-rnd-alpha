/**
 * PATH: src/components/documentation/index.ts
 * PURPOSE: Barrel export for all documentation tab sub-components
 * WHY: Single import point for the parent Documentation page
 */

export { PapersTab } from "./PapersTab"
export { OverviewTab } from "./OverviewTab"
export { MetricsTab } from "./MetricsTab"
export { DashboardsTab } from "./DashboardsTab"
export { AnalysisTab } from "./AnalysisTab"
export { PortfolioTab } from "./PortfolioTab"
export { InterpretationTab } from "./InterpretationTab"

export type { PapersTabProps } from "./PapersTab"
export type { OverviewTabProps } from "./OverviewTab"
export type { AnalysisTabProps } from "./AnalysisTab"
export type { InterpretationTabProps } from "./InterpretationTab"
