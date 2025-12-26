/**
 * PATH: frontend/src/components/SafeChart.tsx
 * PURPOSE: Wrapper for Recharts ResponsiveContainer that prevents -1 dimension errors
 * ROLE IN ARCHITECTURE: UI utility component
 * 
 * NOTES FOR FUTURE AI:
 * - The issue is ResponsiveContainer tries to render before parent has dimensions
 * - This wrapper delays rendering until the container has valid dimensions
 * - Use this instead of ResponsiveContainer directly
 */

import { cloneElement, useEffect, useMemo, useRef, useState, type ReactElement } from "react"

interface SafeChartProps {
  /**
   * Must be a single Recharts chart element (e.g., <AreaChart />, <BarChart />).
   * We clone it and inject measured numeric width/height to avoid ResponsiveContainer (-1) errors.
   */
  children: ReactElement<any>
  width?: number | `${number}%` | "auto"
  height?: number
  minHeight?: number
  className?: string
  debounce?: number
}

export function SafeChart({ 
  children, 
  width = "100%", 
  height = 300,
  minHeight,
  className = "",
  debounce = 100
}: SafeChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    let t: number | undefined

    const measure = () => {
      // Prefer getBoundingClientRect over clientWidth/Height for subpixel + transforms.
      const rect = el.getBoundingClientRect()
      const w = Math.floor(rect.width)
      const h = Math.floor(rect.height)

      if (w > 0 && h > 0) {
        setDims((prev) => (prev?.width === w && prev?.height === h ? prev : { width: w, height: h }))
      }
    }

    const scheduleMeasure = () => {
      if (t) window.clearTimeout(t)
      t = window.setTimeout(measure, debounce)
    }

    // Initial measure (and a second pass shortly after mount).
    scheduleMeasure()
    window.setTimeout(measure, Math.max(0, Math.min(250, debounce)))

    const ro = new ResizeObserver(() => scheduleMeasure())
    ro.observe(el)

    return () => {
      if (t) window.clearTimeout(t)
      ro.disconnect()
    }
  }, [debounce])

  const chartEl = useMemo(() => {
    if (!dims) return null
    // Inject explicit dimensions into the Recharts chart component so it never sees -1.
    // We intentionally DO NOT use ResponsiveContainer here.
    return cloneElement(children, { width: dims.width, height: dims.height })
  }, [children, dims?.height, dims?.width])

  return (
    <div 
      ref={containerRef} 
      className={className}
      style={{
        width: width === "auto" ? undefined : width,
        height: height,
        minHeight: minHeight || height,
      }}
    >
      {chartEl ? (
        chartEl
      ) : (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <div className="animate-pulse">Loading chart...</div>
        </div>
      )}
    </div>
  )
}

export default SafeChart

