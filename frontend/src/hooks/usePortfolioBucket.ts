/**
 * PATH: frontend/src/hooks/usePortfolioBucket.ts
 * PURPOSE: Shared My Book selection (MedTwin bulk-select analogue).
 */
import { useCallback, useSyncExternalStore } from "react"

const KEY = "saas_bucket"

function readBucket(): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "[]")
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : []
  } catch {
    return []
  }
}

let bucketSnapshot = typeof window === "undefined" ? [] : readBucket()
const listeners = new Set<() => void>()

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return bucketSnapshot
}

function updateBucket(next: string[]) {
  bucketSnapshot = [...new Set(next.map((ticker) => ticker.toUpperCase()))]
  try {
    localStorage.setItem(KEY, JSON.stringify(bucketSnapshot))
  } catch {
    // Keep the in-memory book usable when storage is blocked.
  }
  listeners.forEach((listener) => listener())
}

export function usePortfolioBucket() {
  const bucket = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  const toggle = useCallback((ticker: string) => {
    const t = ticker.toUpperCase()
    updateBucket(bucketSnapshot.includes(t) ? bucketSnapshot.filter((x) => x !== t) : [...bucketSnapshot, t])
  }, [])

  const addMany = useCallback((tickers: string[]) => {
    updateBucket([...bucketSnapshot, ...tickers])
  }, [])

  const removeMany = useCallback((tickers: string[]) => {
    const drop = new Set(tickers.map((t) => t.toUpperCase()))
    updateBucket(bucketSnapshot.filter((t) => !drop.has(t)))
  }, [])

  const clear = useCallback(() => updateBucket([]), [])

  const setExact = useCallback((tickers: string[]) => {
    updateBucket(tickers)
  }, [])

  const has = useCallback((ticker: string) => bucket.includes(ticker.toUpperCase()), [bucket])

  return { bucket, toggle, addMany, removeMany, clear, setExact, has }
}
