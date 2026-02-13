/**
 * PATH: src/lib/api/base.ts
 * PURPOSE: API base configuration and fetch helper
 */

// In production (Docker), nginx proxies /api to backend. In dev, use localhost:8000
export const API_BASE = import.meta.env.VITE_API_URL || ""

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}
