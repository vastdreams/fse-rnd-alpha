import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { API_BASE } from "@/lib/api/base"
import { withDashboardNext } from "@/lib/authRedirect"

export function ResetPassword() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState(params.get("email") || "")
  const [token, setToken] = useState(params.get("token") || "")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const requestLink = async () => {
    if (!email) {
      setError("Enter your account email.")
      return
    }
    setBusy(true)
    setError("")
    const response = await fetch(`${API_BASE}/api/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    })
    const body = await response.json().catch(() => ({}))
    setBusy(false)
    if (!response.ok) {
      setError(body.detail || "Could not request a reset link")
      return
    }
    setMessage("If an active account exists, a reset link has been sent.")
  }

  const reset = async () => {
    if (!email || !token || password.length < 8) {
      setError("Enter your email, reset token, and a password of at least 8 characters.")
      return
    }
    setBusy(true)
    setError("")
    const response = await fetch(`${API_BASE}/api/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, token, password }),
    })
    const body = await response.json().catch(() => ({}))
    setBusy(false)
    if (!response.ok) {
      setError(body.detail || "Could not reset password")
      return
    }
    navigate(withDashboardNext("/login", params.get("next")))
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-white p-6">
        <h1 className="text-xl font-semibold text-black">Reset password</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Request a one-time link, then use the token from that link to choose a new password.
        </p>
        {message && <p className="mt-3 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
        {error && <p className="mt-3 rounded-md bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
        <label className="mt-4 block text-sm font-medium text-neutral-800">
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 h-10 w-full rounded-md border border-border px-3 text-sm"
            autoComplete="email"
          />
        </label>
        <button
          type="button"
          onClick={() => void requestLink()}
          disabled={busy}
          className="mt-2 text-sm font-medium text-emerald-700 underline disabled:opacity-50"
        >
          Send reset link
        </button>
        <div className="mt-5 border-t border-border pt-4">
          <label className="block text-sm font-medium text-neutral-800">
            Reset token
            <input
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-border px-3 text-sm"
              autoComplete="one-time-code"
            />
          </label>
          <label className="mt-3 block text-sm font-medium text-neutral-800">
            New password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-border px-3 text-sm"
              autoComplete="new-password"
            />
          </label>
          <button
            type="button"
            onClick={() => void reset()}
            disabled={busy}
            className="mt-4 w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Working…" : "Set new password"}
          </button>
        </div>
        <p className="mt-5 text-sm text-neutral-600">
          <Link
            to={withDashboardNext("/login", params.get("next"))}
            className="font-medium text-emerald-700 underline"
          >
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
