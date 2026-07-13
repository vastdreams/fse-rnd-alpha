/**
 * PATH: frontend/src/components/research/ErrorBanner.tsx
 * PURPOSE: Shared amber error surface — never silent-fail research fetches.
 */
export function ErrorBanner({ children }: { children: string }) {
  if (!children) return null
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="alert">
      {children}
    </div>
  )
}
