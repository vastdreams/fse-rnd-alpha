/**
 * PATH: frontend/src/stores/authStore.ts
 * PURPOSE: End-user JWT session (MedTwin-style email/password).
 */
import { create } from "zustand"
import { API_BASE, invalidateApiCache } from "@/lib/api/base"
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "@/lib/authToken"

export type AuthUser = {
  id: string
  email: string
  full_name?: string | null
  is_active?: boolean
  role?: "user" | "operator" | "admin"
  email_verified?: boolean
}

type AuthState = {
  token: string | null
  user: AuthUser | null
  isLoading: boolean
  hydrated: boolean
  hydrate: () => Promise<void>
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string }>
  register: (
    email: string,
    password: string,
    fullName?: string
  ) => Promise<{ success: boolean; message?: string; verificationRequired?: boolean }>
  verifyEmail: (token: string) => Promise<{ success: boolean; message?: string }>
  logout: () => Promise<void>
}

type AuthResponse = {
  access_token?: string
  user?: AuthUser
  verification_required?: boolean
  message?: string
}

async function authPost(
  path: string,
  body: Record<string, unknown>
): Promise<{ ok: true; data: AuthResponse } | { ok: false; message: string }> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      const detail = (data as { detail?: string | Array<{ msg?: string }> }).detail
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
            : `Request failed (${res.status})`
      return { ok: false, message }
    }
    return { ok: true, data: data as AuthResponse }
  } catch (e) {
    return { ok: false, message: e instanceof Error ? e.message : "Network error" }
  }
}

function persist(token: string, user: AuthUser) {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isLoading: false,
  hydrated: false,

  hydrate: async () => {
    try {
      const token = localStorage.getItem(AUTH_TOKEN_KEY)
      const raw = localStorage.getItem(AUTH_USER_KEY)
      const user = raw ? (JSON.parse(raw) as AuthUser) : null
      if (!token || !user) {
        invalidateApiCache()
        set({ token: null, user: null, hydrated: true })
        return
      }
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        localStorage.removeItem(AUTH_TOKEN_KEY)
        localStorage.removeItem(AUTH_USER_KEY)
        invalidateApiCache()
        set({ token: null, user: null, hydrated: true })
        return
      }
      const verifiedUser = (await response.json()) as AuthUser
      persist(token, verifiedUser)
      set({ token, user: verifiedUser, hydrated: true })
    } catch {
      invalidateApiCache()
      set({ token: null, user: null, hydrated: true })
    }
  },

  login: async (email, password) => {
    set({ isLoading: true })
    const result = await authPost("/api/auth/login", { email, password })
    set({ isLoading: false })
    if (!result.ok) return { success: false, message: result.message }
    if (!result.data.access_token || !result.data.user) {
      return { success: false, message: "Login response was incomplete" }
    }
    invalidateApiCache()
    persist(result.data.access_token, result.data.user)
    set({ token: result.data.access_token, user: result.data.user })
    return { success: true }
  },

  register: async (email, password, fullName) => {
    set({ isLoading: true })
    const result = await authPost("/api/auth/register", {
      email,
      password,
      full_name: fullName || null,
    })
    set({ isLoading: false })
    if (!result.ok) return { success: false, message: result.message }
    if (!result.data.user) return { success: false, message: "Registration response was incomplete" }
    if (result.data.verification_required) {
      invalidateApiCache()
      localStorage.removeItem(AUTH_TOKEN_KEY)
      localStorage.removeItem(AUTH_USER_KEY)
      set({ token: null, user: null })
      return {
        success: true,
        verificationRequired: true,
        message: result.data.message || "Check your email to verify your account.",
      }
    }
    if (!result.data.access_token) return { success: false, message: "Registration response was incomplete" }
    invalidateApiCache()
    persist(result.data.access_token, result.data.user)
    set({ token: result.data.access_token, user: result.data.user })
    return { success: true, message: result.data.message }
  },

  verifyEmail: async (token) => {
    set({ isLoading: true })
    const result = await authPost("/api/auth/verify-email", { token })
    set({ isLoading: false })
    if (!result.ok) return { success: false, message: result.message }
    if (!result.data.access_token || !result.data.user) {
      return { success: false, message: "Verification response was incomplete" }
    }
    invalidateApiCache()
    persist(result.data.access_token, result.data.user)
    set({ token: result.data.access_token, user: result.data.user })
    return { success: true }
  },

  logout: async () => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    if (token) {
      try {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch {
        // Clear this device even if the network is unavailable. The backend
        // token version check still protects normal online logout flows.
      }
    }
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
    invalidateApiCache()
    set({ token: null, user: null })
  },
}))
