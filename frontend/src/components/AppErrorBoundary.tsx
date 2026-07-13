import { Component, type ErrorInfo, type ReactNode } from "react"

type Props = { children: ReactNode }
type State = { error: Error | null }

/** Keep a render-time failure from replacing the entire investor workspace. */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Application render failed", error, info)
  }

  private retry = () => {
    this.setState({ error: null })
  }

  render() {
    if (this.state.error) {
      return (
        <main className="mx-auto flex min-h-screen max-w-xl items-center p-6">
          <section className="w-full rounded-xl border border-rose-200 bg-white p-6 shadow-sm">
            <h1 className="text-lg font-semibold text-neutral-950">This screen could not be rendered</h1>
            <p className="mt-2 text-sm text-neutral-700">
              Your saved research remains on the server. Retry the screen, or return to the Universe if the problem
              continues.
            </p>
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={this.retry}
                className="rounded-lg bg-black px-3 py-2 text-sm font-medium text-white"
              >
                Retry
              </button>
              <a
                href="/app/universe?mode=buy"
                className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-black"
              >
                Open Universe
              </a>
            </div>
          </section>
        </main>
      )
    }
    return this.props.children
  }
}
