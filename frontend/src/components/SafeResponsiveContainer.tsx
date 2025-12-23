import { useRef, useState, useEffect, type ReactNode } from "react"
import { ResponsiveContainer, type ResponsiveContainerProps } from "recharts"

interface SafeResponsiveContainerProps extends ResponsiveContainerProps {
  children: ReactNode
}

/**
 * A wrapper around ResponsiveContainer that prevents the "width(-1) and height(-1)" error
 * by only rendering the chart when the container has valid dimensions.
 */
export function SafeResponsiveContainer({ children, ...props }: SafeResponsiveContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [hasValidDimensions, setHasValidDimensions] = useState(false)

  useEffect(() => {
    if (!containerRef.current) return

    const checkDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        if (width > 0 && height > 0) {
          setHasValidDimensions(true)
        }
      }
    }

    // Check immediately
    checkDimensions()

    // Also check after a short delay in case the container is being animated
    const timer = setTimeout(checkDimensions, 100)

    // Observe resize changes
    const resizeObserver = new ResizeObserver(checkDimensions)
    resizeObserver.observe(containerRef.current)

    return () => {
      clearTimeout(timer)
      resizeObserver.disconnect()
    }
  }, [])

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%" }}>
      {hasValidDimensions ? (
        <ResponsiveContainer {...props}>{children}</ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          Loading chart...
        </div>
      )}
    </div>
  )
}

