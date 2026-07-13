/**
 * PATH: frontend/src/hooks/useServerBookCount.ts
 * PURPOSE: Shell badge = primary server book holdings (not localStorage bucket).
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { listBooks } from "@/lib/api/universe"
import { primaryBookHoldingsCount } from "@/lib/bookOps"

export function useServerBookCount(enabled = true) {
  const [count, setCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const refreshGenerationRef = useRef(0)

  const refresh = useCallback(() => {
    if (!enabled) return
    const generation = ++refreshGenerationRef.current
    const controller = new AbortController()
    listBooks(controller.signal)
      .then((r) => {
        if (controller.signal.aborted || generation !== refreshGenerationRef.current) return
        setCount(primaryBookHoldingsCount(r.books))
        setError(null)
      })
      .catch((e) => {
        if (controller.signal.aborted || generation !== refreshGenerationRef.current) return
        setError(String(e))
        setCount(0)
      })
    return () => controller.abort()
  }, [enabled])

  useEffect(() => {
    if (!enabled) {
      refreshGenerationRef.current += 1
      setCount(0)
      setError(null)
      return
    }
    const cancelInitial = refresh()
    const onFocus = () => {
      refresh()
    }
    window.addEventListener("focus", onFocus)
    window.addEventListener("fse-book-changed", onFocus)
    return () => {
      cancelInitial?.()
      refreshGenerationRef.current += 1
      window.removeEventListener("focus", onFocus)
      window.removeEventListener("fse-book-changed", onFocus)
    }
  }, [enabled, refresh])

  return { count, error, refresh }
}

export function notifyBookChanged() {
  window.dispatchEvent(new Event("fse-book-changed"))
}
