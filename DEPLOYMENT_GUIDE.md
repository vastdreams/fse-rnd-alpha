# Deployment Guide

## Local Docker

```bash
cd deploy
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend
- React frontend (via nginx)

This is for local development only. It requires a populated `deploy/.env` and
does not create a production release artifact.

## Environment Variables

Copy `.env.example` to `.env` and set:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rd_alpha
FMP_API_KEY=your_fmp_api_key
```

## Production deployment

Production is an immutable release, not a source-tree or frontend-dist copy:

```bash
1. Merge a commit after CI passes.
2. Build and seal a versioned universe with RELEASE_SHA=<full commit SHA>.
3. Run scripts/stage_data_release.sh for that sealed universe.
4. Use the Promote Investor Platform GitHub workflow:
   - target=staging with the successful CI run ID;
   - target=production with that same CI run ID and the successful staging run ID.
```

The workflow deploys CI-published digest-pinned backend and frontend images,
restores the content-addressed data artifact, imports the checksummed
version-scoped research records, and verifies `/health`, `/ready`, and
authenticated smoke tests. See `docs/INVESTOR_PLATFORM_RELEASE_RUNBOOK.md` for
the required environment variables, staging approval, and rollback procedure.

Do not use `deploy/deploy.sh`, rsync, mutable image tags, or manually copied
frontend assets for staging or production.

## Health Checks

- Backend: `GET /health`
- Release attestation: `GET /ready`
- API docs: `GET /docs`
