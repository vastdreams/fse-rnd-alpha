/**
 * PATH: src/pages/Unsubscribe.tsx
 * PURPOSE: Handle newsletter unsubscription with secure token verification
 * 
 * FLOW:
 *   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
 *   │ Parse URL   │───▶│ Verify Token │───▶│ Unsubscribe │
 *   │ Params      │    │ with API     │    │ & Confirm   │
 *   └─────────────┘    └──────────────┘    └─────────────┘
 */

import { useState, useEffect } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MailX, CheckCircle, AlertCircle, Loader2, ArrowLeft } from "lucide-react"

type UnsubscribeState = "loading" | "confirm" | "success" | "error" | "invalid"

export function Unsubscribe() {
  const [searchParams] = useSearchParams()
  const [state, setState] = useState<UnsubscribeState>("loading")
  const [email, setEmail] = useState<string>("")
  const [message, setMessage] = useState<string>("")
  const [isUnsubscribing, setIsUnsubscribing] = useState(false)

  const encodedEmail = searchParams.get("e")
  const token = searchParams.get("t")

  useEffect(() => {
    // Verify the unsubscribe link on mount
    if (!encodedEmail || !token) {
      setState("invalid")
      setMessage("Invalid unsubscribe link. Please use the link from your email.")
      return
    }

    // Verify with backend
    fetch(`/api/unsubscribe/verify?e=${encodedEmail}&t=${token}`)
      .then(res => res.json())
      .then(data => {
        if (data.valid && data.email) {
          setEmail(data.email)
          setState("confirm")
        } else {
          setState("invalid")
          setMessage("This unsubscribe link is invalid or has expired.")
        }
      })
      .catch(() => {
        setState("invalid")
        setMessage("Unable to verify unsubscribe link. Please try again.")
      })
  }, [encodedEmail, token])

  const handleUnsubscribe = async () => {
    if (!encodedEmail || !token) return

    setIsUnsubscribing(true)
    try {
      const response = await fetch("/api/unsubscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: encodedEmail, token })
      })
      const data = await response.json()

      if (data.success) {
        setState("success")
        setMessage(data.message)
      } else {
        setState("error")
        setMessage(data.message || "Failed to unsubscribe. Please try again.")
      }
    } catch {
      setState("error")
      setMessage("An error occurred. Please try again later.")
    } finally {
      setIsUnsubscribing(false)
    }
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center py-12 px-4">
      <Card className="w-full max-w-md">
        {state === "loading" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <Loader2 className="h-12 w-12 text-muted-foreground animate-spin" />
              </div>
              <CardTitle>Verifying...</CardTitle>
              <CardDescription>Please wait while we verify your request.</CardDescription>
            </CardHeader>
          </>
        )}

        {state === "confirm" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-full bg-amber-100 dark:bg-amber-900/30">
                  <MailX className="h-10 w-10 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
              <CardTitle>Unsubscribe from R&D Alpha</CardTitle>
              <CardDescription className="mt-2">
                Are you sure you want to unsubscribe <strong className="text-foreground">{email}</strong> from our newsletter?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                You will no longer receive research updates, market insights, or early access notifications.
              </p>
              <div className="flex flex-col gap-2">
                <Button
                  variant="destructive"
                  onClick={handleUnsubscribe}
                  disabled={isUnsubscribing}
                  className="w-full"
                >
                  {isUnsubscribing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Unsubscribing...
                    </>
                  ) : (
                    "Yes, Unsubscribe Me"
                  )}
                </Button>
                <Button variant="outline" asChild className="w-full">
                  <Link to="/">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Cancel & Return to Research
                  </Link>
                </Button>
              </div>
            </CardContent>
          </>
        )}

        {state === "success" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
                  <CheckCircle className="h-10 w-10 text-green-600 dark:text-green-400" />
                </div>
              </div>
              <CardTitle>Successfully Unsubscribed</CardTitle>
              <CardDescription className="mt-2">
                {message}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                Changed your mind? You can always resubscribe from our website.
              </p>
              <Button asChild className="w-full">
                <Link to="/subscribe">Resubscribe</Link>
              </Button>
              <Button variant="outline" asChild className="w-full">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Research
                </Link>
              </Button>
            </CardContent>
          </>
        )}

        {(state === "error" || state === "invalid") && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-full bg-red-100 dark:bg-red-900/30">
                  <AlertCircle className="h-10 w-10 text-red-600 dark:text-red-400" />
                </div>
              </div>
              <CardTitle>{state === "invalid" ? "Invalid Link" : "Something Went Wrong"}</CardTitle>
              <CardDescription className="mt-2">
                {message}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Research
                </Link>
              </Button>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  )
}

