/**
 * PATH: src/lib/api/base.ts
 * PURPOSE: API base configuration and fetch helper (attaches user JWT when present).
 */

import { AUTH_TOKEN_KEY, AUTH_USER_KEY, getStoredToken } from "@/lib/authToken"

// In production (Docker), nginx proxies /api to backend. In dev, use localhost:8000
export const API_BASE = import.meta.env.VITE_API_URL || ""

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown
  readonly retryable: boolean

  constructor(
    status: number,
    detail: unknown,
    statusText = ""
  ) {
    const rendered =
      typeof detail === "string"
        ? detail
        : detail == null
          ? statusText
          : JSON.stringify(detail)
    super(`API Error: ${status}${rendered ? ` — ${rendered}` : ""}`)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
    this.retryable = status === 408 || status === 429 || status >= 500
  }
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    try {
      localStorage.removeItem(AUTH_TOKEN_KEY)
      localStorage.removeItem(AUTH_USER_KEY)
      invalidateApiCache()
    } catch {
      /* ignore */
    }
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      const next = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.assign(`/login?next=${next}`)
    }
    throw new ApiError(401, "Unauthorized", response.statusText)
  }

  if (!response.ok) {
    let detail: unknown = null
    try {
      const body = await response.json()
      if (body?.detail != null) {
        detail = body.detail
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, detail, response.statusText)
  }

  const data = (await response.json()) as T
  if ((options?.method || "GET").toUpperCase() !== "GET") {
    invalidateApiCache()
  }
  return data
}

// ---------------------------------------------------------------------------
// Session-scoped GET cache. Research data (ranks, vectors, audit trails) only
// changes when a builder runs, so re-fetching on every tab switch wastes both
// latency and backend work. TTL-bounded; any non-GET call clears the cache so
// mutations (book saves, memos, DCF runs) are never served stale reads.
// ---------------------------------------------------------------------------

const _getCache = new Map<string, { at: number; data: unknown }>()
const GET_CACHE_TTL_MS = 120_000

export function invalidateApiCache(prefix?: string): void {
  if (!prefix) {
    _getCache.clear()
    return
  }
  for (const key of _getCache.keys()) {
    if (key.startsWith(prefix)) _getCache.delete(key)
  }
}

export async function fetchApiCached<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const hit = _getCache.get(endpoint)
  if (hit && Date.now() - hit.at < GET_CACHE_TTL_MS) {
    return hit.data as T
  }
  const data = await fetchApi<T>(endpoint, options)
  // An aborted navigation must not populate the cache with a response that
  // belonged to a route the user has already left.
  if (!options?.signal?.aborted) {
    _getCache.set(endpoint, { at: Date.now(), data })
  }
  return data
}
