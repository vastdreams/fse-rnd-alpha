/**
 * PATH: frontend/src/components/auth/RequireAuth.tsx
 * PURPOSE: Gate Portfolio Lab routes behind end-user login.
 */
import { useEffect, type ReactNode } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuthStore } from "@/stores/authStore"

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { token, hydrated, hydrate } = useAuthStore()

  useEffect(() => {
    if (!hydrated) hydrate()
  }, [hydrated, hydrate])

  if (!hydrated) {
    return (
      <div className="min-h-[40vh] flex items-center justify-center text-sm text-muted-foreground">
        Checking session…
      </div>
    )
  }

  if (!token) {
    const next = `${location.pathname}${location.search}`
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  }

  return <>{children}</>
}
