# Portfolio Lab Auth (research.finsoeasy.com)

## What shipped
- End-user **register / verify-email / login / me / password reset** at
  `/api/auth/*` (JWT Bearer, bcrypt passwords).
- **Portfolio Lab** UI (`/portfolio`, `/portfolio/saas/:ticker`) gated by `RequireAuth`.
- All `/api/portfolio/*` routes require a valid user JWT.
- Public static `saas_portfolio_bundle.json` removed from `frontend/public` (API-only).
- Accounts, password hashes, verification/reset-token hashes, roles, and
  reset-session invalidation live in PostgreSQL `user_accounts`.
- The legacy JSON account file is migration input only; it is not the
  production source of truth.
- Optional bootstrap user is idempotent and fully explicit:
  `AUTH_SEED_EMAIL`, `AUTH_SEED_PASSWORD`, and `AUTH_SEED_ROLE`.
- Public registration may require verified email. Configure
  `RESEND_API_KEY` and `AUTH_EMAIL_FROM`; readiness fails closed if public
  verification is enabled without email delivery.
- Public users cannot access investor admin KPIs; only durable `operator` and
  `admin` roles can.

## Local verify
```bash
cd backend && DEBUG=true .venv/bin/uvicorn app.main:app --port 8000
cd frontend && npm run dev
# open http://127.0.0.1:5173/register → verify in DEBUG response → /app
```

## Override seed
```bash
export AUTH_SEED_EMAIL=abhishek@finsoeasy.com
export AUTH_SEED_PASSWORD='…'
```

## Release verification

Run the isolated PostgreSQL integration tests with
`RUN_POSTGRES_INTEGRATION=1`; CI does this after replaying the migration
ledger. The test covers registration, verification, password reset/session
invalidation, restart-safe login, and two-user Book/memo isolation.

For staging/production data artifact, migration, smoke, monitoring, and
rollback procedures, use
[`INVESTOR_PLATFORM_RELEASE_RUNBOOK.md`](INVESTOR_PLATFORM_RELEASE_RUNBOOK.md).
