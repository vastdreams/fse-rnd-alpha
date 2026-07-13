import { useEffect, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { API_BASE } from "@/lib/api/base"
import { useAuthStore } from "@/stores/authStore"

export function VerifyEmail() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { verifyEmail, isLoading } = useAuthStore()
  const [token, setToken] = useState(params.get("token") || "")
  const [email, setEmail] = useState(params.get("email") || "")
  const [message, setMessage] = useState("Check your inbox for a verification link.")
  const [error, setError] = useState("")

  const submit = async (candidate = token) => {
    if (!candidate) {
      setError("Paste the verification token from your email.")
      return
    }
    setError("")
    const result = await verifyEmail(candidate)
    if (!result.success) {
      setError(result.message || "Verification failed")
      return
    }
    navigate("/app")
  }

  useEffect(() => {
    if (params.get("token")) void submit(params.get("token") || "")
    // The URL token is immutable for this page visit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resend = async () => {
    if (!email) {
      setError("Enter the email address used to register.")
      return
    }
    setError("")
    const response = await fetch(`${API_BASE}/api/auth/resend-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      setError(body.detail || "Could not resend verification email")
      return
    }
    setMessage("If the account needs verification, a new link has been sent.")
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-white p-6">
        <h1 className="text-xl font-semibold text-black">Verify your email</h1>
        <p className="mt-2 text-sm text-neutral-600">{message}</p>
        {error && <p className="mt-3 rounded-md bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
        <label className="mt-4 block text-sm font-medium text-neutral-800">
          Verification token
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            className="mt-1 h-10 w-full rounded-md border border-border px-3 text-sm"
            autoComplete="one-time-code"
          />
        </label>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={isLoading}
          className="mt-3 w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isLoading ? "Verifying…" : "Verify and continue"}
        </button>
        <div className="mt-6 border-t border-border pt-4">
          <label className="block text-sm font-medium text-neutral-800">
            Need another link?
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
            onClick={() => void resend()}
            className="mt-2 text-sm font-medium text-emerald-700 underline"
          >
            Resend verification email
          </button>
        </div>
        <p className="mt-5 text-sm text-neutral-600">
          <Link to="/login" className="font-medium text-emerald-700 underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
