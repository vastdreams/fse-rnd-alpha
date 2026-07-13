/**
 * PATH: frontend/src/lib/authToken.ts
 * PURPOSE: Shared JWT localStorage key (avoids circular import with api/base).
 */

export const AUTH_TOKEN_KEY = "fse_research_token"
export const AUTH_USER_KEY = "fse_research_user"

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    return null
  }
}
