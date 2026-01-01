/**
 * Subscribe Popup
 * 
 * Auto-subscribe popup that appears after 20 seconds of session time.
 * Collects email with optional name and profession fields.
 * 
 * Publication: https://research.finsoeasy.com
 */

import { useEffect, useState } from "react"
import { useLocation } from "react-router-dom"
import { X, Mail, User, Briefcase } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const POPUP_DELAY_SECONDS = 20
const COOLDOWN_DAYS = 7

export function SubscribePopup() {
  const [isOpen, setIsOpen] = useState(false)
  const [email, setEmail] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [profession, setProfession] = useState("")
  const [message, setMessage] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const location = useLocation()

  useEffect(() => {
    // Check if user has recently dismissed the popup
    const lastDismissed = localStorage.getItem("subscribePopupDismissed")
    if (lastDismissed) {
      const dismissDate = new Date(lastDismissed)
      const now = new Date()
      const diffTime = Math.abs(now.getTime() - dismissDate.getTime())
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      if (diffDays < COOLDOWN_DAYS) {
        return // Still in cooldown period
      }
    }

    // Check if already subscribed
    if (localStorage.getItem("isSubscribed") === "true") {
      return
    }

    const timer = setTimeout(() => {
      setIsOpen(true)
    }, POPUP_DELAY_SECONDS * 1000)

    return () => clearTimeout(timer)
  }, [location.pathname])

  const handleClose = () => {
    setIsOpen(false)
    localStorage.setItem("subscribePopupDismissed", new Date().toISOString())
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      setMessage("Please enter your email.")
      return
    }
    setIsSubmitting(true)
    setMessage("")

    try {
      const response = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          email, 
          source: "rnd_alpha_popup",
          first_name: firstName || undefined,
          last_name: lastName || undefined,
          profession: profession || undefined
        }),
      })
      const data = await response.json()
      
      if (data.success) {
        setMessage("Thank you for subscribing!")
        setEmail("")
        setFirstName("")
        setLastName("")
        setProfession("")
        localStorage.setItem("isSubscribed", "true")
        setTimeout(handleClose, 2000)
      } else {
        setMessage(data.message || "Failed to subscribe. Please try again.")
      }
    } catch (error) {
      console.error("Subscription error:", error)
      setMessage("Failed to subscribe. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
      <Card className="w-full max-w-md relative bg-card text-card-foreground shadow-2xl border border-border/60">
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 text-muted-foreground hover:text-foreground"
          onClick={handleClose}
        >
          <X className="h-4 w-4" />
        </Button>
        <CardHeader className="text-center pb-4">
          <Mail className="h-10 w-10 text-emerald-500 mx-auto mb-4" />
          <CardTitle className="text-2xl">Stay ahead with R&D Alpha insights</CardTitle>
          <CardDescription className="text-foreground/80">
            Get exclusive updates on our latest research, ETF performance, and market insights.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="list-disc list-inside text-sm text-foreground/80 space-y-1">
            <li>R&D is expensed, not capitalized, creating hidden value.</li>
            <li>Rigorous point-in-time testing avoids survivorship bias.</li>
            <li>Implementable ETF structure for real-world investment.</li>
          </ul>
          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Email (required) */}
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="email"
                placeholder="Your email address *"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="pl-10"
              />
            </div>
            
            {/* First Name & Last Name (optional) */}
            <div className="grid grid-cols-2 gap-2">
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="First name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="relative">
                <Input
                  type="text"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>
            
            {/* Profession (optional) */}
            <div className="relative">
              <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Your profession (optional)"
                value={profession}
                onChange={(e) => setProfession(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Button 
              type="submit" 
              disabled={isSubmitting} 
              className="w-full bg-emerald-600 hover:bg-emerald-700"
            >
              {isSubmitting ? "Subscribing..." : "Subscribe"}
            </Button>
          </form>
          {message && (
            <p className={message.includes("Thank you") ? "text-green-500 text-sm text-center" : "text-red-500 text-sm text-center"}>
              {message}
            </p>
          )}
          <div className="text-center">
            <Button variant="link" onClick={handleClose} className="text-foreground/70 hover:text-foreground">
              Not now
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
