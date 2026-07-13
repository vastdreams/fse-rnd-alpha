/**
 * PATH: frontend/src/pages/portfolio/BookPage.tsx
 * PURPOSE: Server-persisted book with risk constraints, lock/ack gate, empty CTA.
 * STARTS EMPTY by contract — there is no auto-seed path (kill criterion).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorBanner } from "@/components/research/ErrorBanner"
import { notifyBookChanged } from "@/hooks/useServerBookCount"
import { equalWeightHoldings, MAX_POSITION_WEIGHT_PCT } from "@/lib/bookOps"
import {
  createBook,
  getBookAuditPack,
  listBooks,
  lockBook,
  saveBook,
  setPrimaryBook,
  unlockBook,
  type BookHolding,
  type Breach,
  type SavedBookRecord,
} from "@/lib/api/universe"

export function BookPage() {
  const [books, setBooks] = useState<SavedBookRecord[]>([])
  const [bookId, setBookId] = useState<string | null>(null)
  const [holdings, setHoldings] = useState<BookHolding[]>([])
  const [breaches, setBreaches] = useState<Breach[]>([])
  const [newTicker, setNewTicker] = useState("")
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [acknowledgements, setAcknowledgements] = useState<Set<string>>(() => new Set())
  const bookIdRef = useRef<string | null>(null)
  const reloadGenerationRef = useRef(0)

  useEffect(() => {
    bookIdRef.current = bookId
  }, [bookId])

  const reload = useCallback(async () => {
    const generation = ++reloadGenerationRef.current
    try {
      const response = await listBooks()
      if (generation !== reloadGenerationRef.current) return
      setBooks(response.books)
      const selectedId = bookIdRef.current
      if (response.books.length > 0 && !selectedId) {
        const primary = response.books.find((candidate) => candidate.is_primary) || response.books[0]
        bookIdRef.current = primary.book_id
        setBookId(primary.book_id)
        setHoldings(primary.holdings)
        setAcknowledgements(new Set(primary.lock_acknowledgements || []))
      } else if (selectedId) {
        const selectedBook = response.books.find((candidate) => candidate.book_id === selectedId)
        if (selectedBook) {
          setHoldings(selectedBook.holdings)
          setAcknowledgements(new Set(selectedBook.lock_acknowledgements || []))
        } else {
          bookIdRef.current = null
          setBookId(null)
          setHoldings([])
          setAcknowledgements(new Set())
        }
      }
      setError(null)
      notifyBookChanged()
    } catch (e) {
      if (generation === reloadGenerationRef.current) setError(String(e))
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const book = useMemo(() => books.find((b) => b.book_id === bookId) || null, [books, bookId])
  const totalWeight = holdings.reduce((s, h) => s + (h.weight_pct || 0), 0)
  const isDirty = useMemo(() => {
    if (!book) return false
    const canonical = (items: BookHolding[]) =>
      [...items]
        .map((holding) => ({
          ticker: holding.ticker.toUpperCase(),
          weight_pct: holding.weight_pct,
          added_at: holding.added_at,
          override_reason: holding.override_reason || null,
        }))
        .sort((left, right) => left.ticker.localeCompare(right.ticker))
    return JSON.stringify(canonical(holdings)) !== JSON.stringify(canonical(book.holdings))
  }, [book, holdings])
  const allAcknowledged =
    holdings.length === 0 || holdings.every((h) => acknowledgements.has(h.ticker.toUpperCase()))
  const pendingAcknowledgements = holdings.filter((h) => !acknowledgements.has(h.ticker.toUpperCase())).length

  const create = async () => {
    const name = prompt("Book name?", "My research book")
    if (!name) return
    setError(null)
    try {
      const r = await createBook(name)
      await reload()
      bookIdRef.current = r.book_id
      setBookId(r.book_id)
      setHoldings([])
      setAcknowledgements(new Set())
    } catch (e) {
      setError(String(e))
    }
  }

  const selectBook = (id: string, h: BookHolding[]) => {
    bookIdRef.current = id
    setBookId(id)
    setHoldings(h)
    setBreaches([])
    const selectedBook = books.find((candidate) => candidate.book_id === id)
    setAcknowledgements(new Set(selectedBook?.lock_acknowledgements || []))
  }

  const toggleAcknowledgement = (ticker: string) => {
    if (!bookId || book?.locked_at) return
    const t = ticker.toUpperCase()
    setAcknowledgements((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  const add = () => {
    if (book?.locked_at) return
    const t = newTicker.trim().toUpperCase()
    if (!t || holdings.some((h) => h.ticker === t)) return
    setHoldings((prev) => [
      ...prev,
      { ticker: t, weight_pct: 0, added_at: new Date().toISOString().slice(0, 19) },
    ])
    setNewTicker("")
  }

  const equalWeight = () => {
    if (book?.locked_at) return
    if (holdings.length === 0) return
    setHoldings((prev) => equalWeightHoldings([], prev))
  }

  const save = async () => {
    if (!bookId || book?.locked_at) return
    setStatus(null)
    setError(null)
    setBreaches([])
    try {
      const res = await saveBook(bookId, holdings, undefined, book?.revision)
      if ("breaches" in res) {
        setBreaches(res.breaches)
      } else {
        setStatus("Saved.")
        notifyBookChanged()
        reload()
      }
    } catch (e) {
      setError(String(e))
    }
  }

  const exportPack = async () => {
    if (!bookId) return
    if (isDirty) {
      setError("Save the current holdings before locking or exporting an audit pack.")
      return
    }
    if (!allAcknowledged) {
      setError(`Acknowledge the current research for all holdings first (${pendingAcknowledgements} remaining).`)
      return
    }
    try {
      if (!book?.locked_at) {
        await lockBook(bookId, [...acknowledgements], book?.revision)
        await reload()
      }
      const pack = await getBookAuditPack(bookId)
      const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" })
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = `book_${bookId.slice(0, 8)}_audit_pack.json`
      a.click()
    } catch (e) {
      setError(String(e))
    }
  }

  const makePrimary = async () => {
    if (!bookId) return
    try {
      await setPrimaryBook(bookId)
      await reload()
      setStatus("Primary Book updated.")
    } catch (e) {
      setError(String(e))
    }
  }

  const unlock = async () => {
    if (!bookId) return
    try {
      await unlockBook(bookId)
      setAcknowledgements(new Set())
      await reload()
      setStatus("Book unlocked. Review acknowledgements again before exporting.")
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-950">My Book</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-700">
            Books start empty and are yours to build from Universe (select → Add to Book). Constraint
            breaches block saving — that is deliberate. Research only, not investment advice.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/app/universe?mode=buy"
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-black hover:bg-muted"
          >
            ← Universe (What to Buy)
          </Link>
          <button
            type="button"
            onClick={create}
            className="rounded-lg bg-black px-3 py-2 text-sm font-medium text-white"
          >
            New book
          </button>
        </div>
      </div>

      {books.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          {books.map((b) => (
            <button
              key={b.book_id}
              type="button"
              onClick={() => selectBook(b.book_id, b.holdings)}
              className={`rounded-full border px-3 py-1 text-xs ${
                bookId === b.book_id ? "border-black bg-black text-white" : "border-border bg-white text-black"
              }`}
            >
              {b.name} ({b.holdings.length})
            </button>
          ))}
        </div>
      )}

      {error && <ErrorBanner>{error}</ErrorBanner>}
      {!book && !error && (
        <div className="rounded-xl border border-dashed border-border bg-white p-10 text-center">
          <p className="text-sm text-neutral-700">
            No book yet. Create one — it starts empty — or select cleared BUYs on Universe and use{" "}
            <b>Add to Book</b>.
          </p>
          <Link
            to="/app/universe?mode=buy"
            className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white"
          >
            Open What to Buy →
          </Link>
        </div>
      )}

      {book && (
        <>
          <div className="rounded-xl border border-border bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-black">{book.name}</h2>
                <p className="text-[11px] text-neutral-600">
                  Universe {book.lock_version || book.universe_version || "pending"} ·{" "}
                  {book.locked_at ? `locked ${String(book.locked_at).slice(0, 10)}` : "editable"} · revision {book.revision}
                </p>
              </div>
              <div className="flex gap-2">
                {!book.is_primary && (
                  <button
                    type="button"
                    onClick={() => void makePrimary()}
                    className="rounded-md border border-border px-2 py-1 text-xs font-medium text-black hover:bg-muted"
                  >
                    Make primary
                  </button>
                )}
                {book.locked_at && (
                  <button
                    type="button"
                    onClick={() => void unlock()}
                    className="rounded-md border border-border px-2 py-1 text-xs font-medium text-black hover:bg-muted"
                  >
                    Unlock to edit
                  </button>
                )}
                {book.is_primary && (
                  <span className="rounded-md bg-neutral-900 px-2 py-1 text-xs font-medium text-white">Primary Book</span>
                )}
              </div>
            </div>
            <h3 className="mt-3 text-sm font-semibold text-black">Constraints (server-enforced)</h3>
            <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-neutral-700">
              {book.constraints.map((c, i) => (
                <span key={i} className="rounded border border-border bg-neutral-50 px-2 py-0.5">
                  {c.kind}
                  {c.limit !== null ? ` ≤ ${c.limit}%` : ""}
                </span>
              ))}
              <span className="rounded border border-border bg-neutral-50 px-2 py-0.5">
                stale names need override
              </span>
            </div>
          </div>

          {breaches.length > 0 && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 p-4">
              <h3 className="text-sm font-semibold text-rose-900">Breach wall — save blocked</h3>
              <ul className="mt-1 list-inside list-disc text-xs text-rose-800">
                {breaches.map((b, i) => (
                  <li key={i}>{b.detail}</li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-rose-700">
                Fix the weights, or type an override reason on the breaching holdings below.
              </p>
            </div>
          )}

          {holdings.length > 0 && !allAcknowledged && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
              Review acknowledgement required before locking/export: acknowledge each holding ({pendingAcknowledgements} remaining).
              Acknowledgements are persisted with the server-side lock and the pinned research version.
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <input
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && add()}
              placeholder="Add ticker…"
              disabled={Boolean(book.locked_at)}
              className="h-11 w-32 rounded-lg border border-border px-3 text-sm text-black"
            />
            <button
              type="button"
              onClick={add}
              disabled={Boolean(book.locked_at)}
              className="min-h-11 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-black hover:bg-muted"
            >
              Add
            </button>
            <button
              type="button"
              onClick={equalWeight}
              disabled={Boolean(book.locked_at)}
              className="min-h-11 rounded-lg border border-border px-3 py-1.5 text-xs text-black hover:bg-muted"
            >
              Rebalance equally
            </button>
            <span
              className={`text-xs font-medium ${
                Math.abs(totalWeight - 100) < 0.02 || holdings.length === 0
                  ? "text-neutral-600"
                  : "text-amber-800"
              }`}
            >
              Σ {totalWeight.toFixed(1)}%
            </span>
            {holdings.length > 0 && holdings.length < 7 && (
              <span className="text-[11px] text-neutral-600">
                Rebalance caps each name at {MAX_POSITION_WEIGHT_PCT}% and leaves the remainder unallocated.
              </span>
            )}
            <div className="flex-1" />
            <button
              type="button"
              onClick={exportPack}
              disabled={!allAcknowledged || holdings.length === 0 || isDirty}
              title={
                !allAcknowledged
                  ? "Acknowledge every holding before locking/exporting"
                  : isDirty
                    ? "Save current holdings before locking/exporting"
                    : undefined
              }
              className="min-h-11 rounded-lg border border-border px-3 py-1.5 text-xs text-black hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
            >
              {book.locked_at ? "Export audit pack" : isDirty ? "Save before lock/export" : "Lock / Export audit pack"}
            </button>
            <button
              type="button"
              onClick={save}
              disabled={Boolean(book.locked_at)}
              className="min-h-11 rounded-lg bg-black px-4 py-1.5 text-xs font-medium text-white"
            >
              {book.locked_at ? "Book locked" : "Save book"}
            </button>
          </div>
          {status && <p className="text-xs text-emerald-700">{status}</p>}

          {holdings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-white p-8 text-center text-sm text-neutral-600">
              Empty. Select names on{" "}
              <Link to="/app/universe?mode=buy" className="font-medium text-black underline">
                What to Buy
              </Link>{" "}
              and use <b>Add to Book</b> — then return here to weight and export.
            </div>
          ) : (
            <div className="overflow-auto rounded-xl border border-border bg-white">
              <table className="min-w-full text-sm">
                <thead className="bg-muted/50 text-[11px] uppercase text-foreground/60">
                  <tr>
                    <th className="px-3 py-2 text-left">Ticker</th>
                    <th className="px-3 py-2 text-right">Weight %</th>
                    <th className="px-3 py-2 text-left">Research reviewed</th>
                    <th className="px-3 py-2 text-left">Override reason (if breaching)</th>
                    <th className="px-3 py-2 text-right" />
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.ticker} className="border-t border-border/70">
                      <td className="px-3 py-2">
                        <Link
                          to={
                            book.lock_version || book.universe_version
                              ? `/app/company/${h.ticker}?universe_version=${encodeURIComponent(
                                  book.lock_version || book.universe_version || ""
                                )}`
                              : `/app/company/${h.ticker}`
                          }
                          className="!text-black font-bold hover:underline"
                        >
                          {h.ticker}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <input
                          type="number"
                          step="0.5"
                          min={0}
                          max={100}
                          value={h.weight_pct}
                          disabled={Boolean(book.locked_at)}
                          onChange={(e) =>
                            setHoldings((prev) =>
                              prev.map((x) =>
                                x.ticker === h.ticker
                                  ? { ...x, weight_pct: Number(e.target.value) }
                                  : x
                              )
                            )
                          }
                          className="h-8 w-20 rounded-md border border-border px-2 text-right text-sm text-black"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <label className="inline-flex min-h-11 items-center gap-2 text-xs text-neutral-800">
                          <input
                            type="checkbox"
                            className="h-5 w-5"
                            checked={acknowledgements.has(h.ticker.toUpperCase())}
                            disabled={Boolean(book.locked_at)}
                            onChange={() => toggleAcknowledgement(h.ticker)}
                          />
                          Ack
                        </label>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          value={h.override_reason || ""}
                          disabled={Boolean(book.locked_at)}
                          onChange={(e) =>
                            setHoldings((prev) =>
                              prev.map((x) =>
                                x.ticker === h.ticker
                                  ? { ...x, override_reason: e.target.value || null }
                                  : x
                              )
                            )
                          }
                          placeholder="required to bypass a breach"
                          className="h-8 w-full max-w-xs rounded-md border border-border px-2 text-xs text-black"
                        />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          disabled={Boolean(book.locked_at)}
                          onClick={() =>
                            setHoldings((prev) => prev.filter((x) => x.ticker !== h.ticker))
                          }
                          className="text-xs text-neutral-600 hover:text-rose-700"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <p className="text-[11px] text-neutral-500">
        RESEARCH ONLY — NOT INVESTMENT ADVICE. Exports are watermarked with your account identity.
      </p>
    </div>
  )
}
