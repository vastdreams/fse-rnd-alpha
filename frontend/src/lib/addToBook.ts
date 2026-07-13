/**
 * PATH: frontend/src/lib/addToBook.ts
 * PURPOSE: Ensure primary research book exists and merge tickers (server SoT).
 */
import {
  createBook,
  listBooks,
  saveBook,
  type BookHolding,
  type Breach,
} from "@/lib/api/universe"
import { appendUnallocatedHoldings } from "@/lib/bookOps"
import { notifyBookChanged } from "@/hooks/useServerBookCount"

export type AddToBookResult =
  | { ok: true; bookId: string; holdings: BookHolding[]; added: number }
  | { ok: false; breaches: Breach[] }
  | { ok: false; error: string }

export async function addTickersToPrimaryBook(
  tickers: string[],
  universeVersion?: string
): Promise<AddToBookResult> {
  const unique = [...new Set(tickers.map((t) => t.toUpperCase()).filter(Boolean))]
  if (!unique.length) return { ok: false, error: "No tickers selected." }
  try {
    let { books } = await listBooks()
    const primary = books.find((book) => book.is_primary) || books[0]
    let bookId = primary?.book_id
    let existing: BookHolding[] = primary?.holdings ?? []
    let revision: number | undefined = primary?.revision
    if (primary?.locked_at) {
      return { ok: false, error: "Your primary Book is locked. Unlock it before adding holdings." }
    }
    if (primary?.universe_version && universeVersion && primary.universe_version !== universeVersion) {
      return {
        ok: false,
        error: `Your primary Book is pinned to ${primary.universe_version}, but these names use ${universeVersion}. Create or select a matching Book first.`,
      }
    }
    if (!bookId) {
      const created = await createBook("Research book", undefined, universeVersion)
      bookId = created.book_id
      const again = await listBooks()
      books = again.books
      const createdBook = books.find((book) => book.book_id === bookId)
      existing = createdBook?.holdings ?? []
      revision = createdBook?.revision
    }
    const before = new Set(existing.map((h) => h.ticker.toUpperCase()))
    // Adds are research candidates, not an implicit rebalance. This keeps a
    // custom allocation intact and makes 1–6-name drafts actionable under the
    // 15% per-name limit until the owner explicitly allocates them.
    const holdings = appendUnallocatedHoldings(unique, existing)
    const res = await saveBook(bookId, holdings, undefined, revision)
    if ("breaches" in res) return { ok: false, breaches: res.breaches }
    notifyBookChanged()
    const added = unique.filter((t) => !before.has(t)).length
    return { ok: true, bookId, holdings, added }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}
