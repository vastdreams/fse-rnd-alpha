/** Preserve only internal dashboard destinations through the auth lifecycle. */
export function dashboardNextPath(candidate: string | null): string {
  if (!candidate || !candidate.startsWith("/app") || candidate.startsWith("//")) {
    return "/app"
  }
  return candidate
}

export function withDashboardNext(path: string, candidate: string | null): string {
  const next = dashboardNextPath(candidate)
  return `${path}?next=${encodeURIComponent(next)}`
}
