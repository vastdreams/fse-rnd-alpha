# Investor platform boundaries

The investor product, site administration, and production operations are
separate surfaces with separate authority.

## Investor

- The only supported portfolio routes are `/app`, `/app/universe`,
  `/app/company/:ticker`, and `/app/book`.
- A durable `user` account can see only its own Books, DCF runs, memos, audit
  exports, and session state.
- Research data is shared only through sealed universe versions and
  evidence-backed records. Missing evidence stays `UNKNOWN` or incomplete.
- Historical `/app/legacy/*`, `/app/investigate`, and `/portfolio*` bookmarks
  redirect to the supported routes and preserve query context; they cannot
  reactivate legacy local Book state.

## Administrator

- `/admin` is a separate console authenticated by a durable `admin` account.
  The API enforces the role on every admin endpoint; a normal investor token
  receives `403`.
- The console may manage research-site metadata and analytics but never returns
  client portal credentials. Those credentials remain target-side secrets and
  are rotated through the approved access-control process.
- Administration is not a shortcut into a user's private investor records.

## Operator

- Operators publish GitLab `main` artifacts and activate a named release from
  the target through `rd-alpha-promote@<source-sha>-<pipeline-id>`.
- Operators own release approval, data sealing, backup/restore, TLS, worker
  health, and the retained staging/production proof chain.
- CI has no production SSH credential. Neither an investor nor an admin
  browser session can invoke deployment, worker, backup, or data-backfill
  controls.
