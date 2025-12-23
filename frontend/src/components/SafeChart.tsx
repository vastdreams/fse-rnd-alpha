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

import { useState, useEffect, useRef, type ReactNode } from "react"
import { ResponsiveContainer } from "recharts"

interface SafeChartProps {
  children: ReactNode
  width?: number | `${number}%`
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
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // Delay initial render to allow container to calculate dimensions
    const timer = setTimeout(() => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current
        if (clientWidth > 0 && clientHeight > 0) {
          setIsReady(true)
        }
      }
    }, debounce)

    return () => clearTimeout(timer)
  }, [debounce])

  // Also check on resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current
        if (clientWidth > 0 && clientHeight > 0 && !isReady) {
          setIsReady(true)
        }
      }
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [isReady])

  return (
    <div 
      ref={containerRef} 
      className={className}
      style={{ height: height, minHeight: minHeight || height }}
    >
      {isReady ? (
        <ResponsiveContainer 
          width={width} 
          height="100%" 
          minHeight={minHeight || height}
          debounce={debounce}
        >
          {children}
        </ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <div className="animate-pulse">Loading chart...</div>
        </div>
      )}
    </div>
  )
}

export default SafeChart

