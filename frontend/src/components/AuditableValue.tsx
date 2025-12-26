/**
 * PATH: frontend/src/components/AuditableValue.tsx
 * PURPOSE: Wrapper component that makes any value auditable via right-click
 * 
 * Provides:
 * - Right-click context menu with audit options
 * - Hover indicator showing value is auditable
 * - Integration with AuditModal
 */

import { useState, useCallback, type ReactNode, type MouseEvent } from "react"
import { AuditModal, AuditContextMenu, type AuditData } from "./AuditModal"
import { getAuditData } from "@/data/auditData"
import { cn } from "@/lib/utils"

interface AuditableValueProps {
  /** The metric ID used to look up audit data */
  metricId: string
  /** Display label for the metric */
  metricLabel: string
  /** The actual displayed value */
  value: string | number
  /** Additional parameters for audit data generation */
  auditParams?: Record<string, unknown>
  /** Children to render (the value display) */
  children: ReactNode
  /** Additional class names */
  className?: string
  /** Whether to show hover indicator */
  showHoverIndicator?: boolean
}

export function AuditableValue({
  metricId,
  metricLabel,
  value,
  auditParams = {},
  children,
  className,
  showHoverIndicator = true,
}: AuditableValueProps) {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)
  const [auditModalOpen, setAuditModalOpen] = useState(false)
  const [auditData, setAuditData] = useState<AuditData | null>(null)

  const handleContextMenu = useCallback((e: MouseEvent) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const handleAudit = useCallback(() => {
    const data = getAuditData(metricId, { ...auditParams, value })
    if (data) {
      setAuditData(data)
      setAuditModalOpen(true)
    }
  }, [metricId, auditParams, value])

  const handleCopyValue = useCallback(async () => {
    await navigator.clipboard.writeText(String(value))
  }, [value])

  const handleCopyWithLabel = useCallback(async () => {
    await navigator.clipboard.writeText(`${metricLabel}: ${value}`)
  }, [metricLabel, value])

  return (
    <>
      <div
        onContextMenu={handleContextMenu}
        className={cn(
          "cursor-context-menu relative group",
          showHoverIndicator && "hover:ring-2 hover:ring-primary/20 hover:ring-offset-2 hover:ring-offset-background rounded transition-all",
          className
        )}
        title="Right-click to audit this value"
      >
        {children}
        
        {/* Hover indicator */}
        {showHoverIndicator && (
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-primary/80 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <span className="text-[10px] text-primary-foreground font-bold">i</span>
          </div>
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <AuditContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          onAudit={handleAudit}
          onCopyValue={handleCopyValue}
          onCopyWithLabel={handleCopyWithLabel}
          metricName={metricLabel}
          value={String(value)}
        />
      )}

      {/* Audit Modal */}
      <AuditModal
        isOpen={auditModalOpen}
        onClose={() => setAuditModalOpen(false)}
        data={auditData}
      />
    </>
  )
}

/**
 * Hook for managing audit state - use this if you need more control
 */
export function useAudit() {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)
  const [auditModalOpen, setAuditModalOpen] = useState(false)
  const [auditData, setAuditData] = useState<AuditData | null>(null)

  const openContextMenu = useCallback((e: MouseEvent) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const closeContextMenu = useCallback(() => {
    setContextMenu(null)
  }, [])

  const openAuditModal = useCallback((metricId: string, params: Record<string, unknown> = {}) => {
    const data = getAuditData(metricId, params)
    if (data) {
      setAuditData(data)
      setAuditModalOpen(true)
    }
    setContextMenu(null)
  }, [])

  const closeAuditModal = useCallback(() => {
    setAuditModalOpen(false)
  }, [])

  return {
    contextMenu,
    auditModalOpen,
    auditData,
    openContextMenu,
    closeContextMenu,
    openAuditModal,
    closeAuditModal,
  }
}

