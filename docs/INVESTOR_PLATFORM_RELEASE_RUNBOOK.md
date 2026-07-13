# Investor platform release runbook

This runbook releases an immutable application image and an immutable data
artifact together. Do not deploy from a dirty checkout, a local cache, or a
mutable image tag.

## 1. Prepare and freeze the research data

1. Run tracked backfill jobs against the staging database and mounted data
   volume. Build a new content-addressed universe with
   `scripts/build_universe.py`; enrich it only through an explicit derived
   version using `scripts/fill_layer0.py --version <source> --output-version <derived>`.
   Set `RELEASE_SHA` to the full committed source SHA before every build,
   derived fill, or kill-state patch; unversioned builds cannot be promoted or
   staged.
2. Apply reviewed kill states only with
   `scripts/patch_kill_active.py --version <source> --output-version <reviewed>`.
   Unknown states remain `NULL` and are not investable.
3. Keep the candidate build inactive while staging. A build becomes active
   only after its data manifest and exported research-record payload have both
   been verified on the target database. Do not use the build scripts'
   deprecated `--activate` flag.
4. Stage the artifact, not the working `data/` tree:

   ```sh
   RELEASE_SHA=<full-40-character-source-sha> \
   DATABASE_URL=<staging-postgres-url> \
   DATA_RELEASE_BUCKET=<versioned-bucket> \
     ./scripts/stage_data_release.sh \
       --universe-version <immutable-universe-version> \
       --source-sha <full-40-character-source-sha>
   ```

   Record the emitted `s3://…` URI,
   `DATA_RELEASE_DESCRIPTOR_SHA256=…`, and
   `DATA_RELEASE_DESCRIPTOR_VERSION_ID=…`. The command requires a sealed build
   whose recorded source SHA matches the checked-out source, binds the data
   manifest once, fingerprints and exports the sealed database research
   records, and uploads the tarball, manifest, research snapshot,
   research-record payload, and release metadata. It snapshots the source
   tree before manifest/archive generation, pins every payload to its S3
   VersionId in `release.json`, and rejects objects without Compliance Object
   Lock retention. Conditional S3 writes accept a retry only when every
   existing object has the same checksum.

## 2. Configure each target

On staging and production hosts, set these values in `deploy/.env`:

- strong unique `POSTGRES_PASSWORD` and `SECRET_KEY` (at least 32 characters)
- `BACKEND_DATABASE_URL`, an internal `postgresql+asyncpg://` URL containing
  the percent-encoded PostgreSQL password; do not interpolate the raw password
  into a URL
- a valid `SEC_USER_AGENT`
- `DATA_DIR=/opt/rd-alpha-data` (created by infrastructure setup and kept
  outside `/opt/rd-alpha` so restores never dirty the source checkout)
- `CERTS_DIR=/opt/rd-alpha-certs` and
  `CERTBOT_WEBROOT=/opt/rd-alpha-certbot-webroot`, also outside the checkout
  so certificate renewal cannot dirty the deploy source
- `DATA_RELEASE_URI` from the staging command
- `DATA_RELEASE_DESCRIPTOR_SHA256` emitted by the staging command; it is the
  SHA-256 of `release.json` and binds the archive, database snapshot, and
  research-record checksums as one promoted artifact
- target-specific `PUBLIC_HOSTNAME`, `AUTH_RESET_URL`, `AUTH_VERIFY_URL`,
  `STRIPE_SUCCESS_URL`, and `STRIPE_CANCEL_URL` — no production URL is used
  as a fallback
- `AUTH_REQUIRE_EMAIL_VERIFICATION=true`, `AUTH_EMAIL_FROM`, and
  `RESEND_API_KEY` for public registration
- two verified, non-admin smoke accounts whose credentials are stored as
  environment-scoped GitHub secrets:
  `SMOKE_TEST_EMAIL`, `SMOKE_TEST_PASSWORD`, `SMOKE_SECONDARY_EMAIL`, and
  `SMOKE_SECONDARY_PASSWORD`

On a blank host, set `AUTH_SEED_EMAIL`/`AUTH_SEED_PASSWORD` and the distinct
`AUTH_SECONDARY_SEED_EMAIL`/`AUTH_SECONDARY_SEED_PASSWORD` to those smoke
credentials. Bootstrap creates them idempotently and never rotates an existing
password hash.

The target needs Docker Compose, `aws`, `tar`, `s3:GetObjectVersion` permission
for the staged payloads, and a persistent Docker login with pull access to the
repository's backend and frontend images. The staging publisher also needs
`s3:GetObjectRetention` so it can prove Compliance Object Lock retention.
`deploy/setup_aws.py --create` provisions an EC2 role with read-only access
only to the configured release prefix; do not place AWS access keys in
`deploy/.env`.
`DATA_RELEASE_URI` is intentionally required by `scripts/deploy_release.sh`.

Create separate GitHub `staging` and `production` environments. Each must set
its own `DEPLOY_PATH`, `PUBLIC_BASE_URL`, `DATA_RELEASE_URI`, and
`DATA_RELEASE_DESCRIPTOR_SHA256` variables; its
own `DEPLOY_HOST`, `DEPLOY_USER`, and `DEPLOY_SSH_KEY` secrets; and separate
two-user smoke credentials. The production environment must require reviewer
approval. The production `DATA_RELEASE_URI` must identify artifact content
with the exact manifest SHA that passed staging. When staging and production
use separate buckets, copy every immutable artifact object unchanged and retain
both the final manifest-SHA path component and `release.json` checksum.

Before the first staging release, run this read-only platform check with a
GitHub CLI token authorized to inspect repository settings:

```sh
./scripts/verify_github_release_controls.sh --repo OWNER/REPOSITORY
```

It verifies protected `main` checks/reviews, separate staging/production URLs,
required environment variables and smoke secrets, and required production
environment approval. It intentionally does not print secret values.

### One-time legacy host migration

If an older host still stores mutable `data/` inside `/opt/rd-alpha`, take a
verified archive first, move that tree outside the checkout, and restore the
Git-tracked source files before enabling deployment. The CI workflow refuses a
dirty checkout by design. Stage the moved data as a release artifact, then use
`DATA_DIR=/opt/rd-alpha-data`; never add a symlink back into the Git tree.

## 3. Staging release

1. Merge the candidate commit only after CI is green. CI must pass backend
   tests (including PostgreSQL account/isolation tests), frontend lint/Vitest,
   production-image builds, migration-ledger replay, and Playwright.
2. From the successful main-branch **CI Pipeline** run, record the numeric run
   ID and its `immutable-release` artifact. CI has already pushed the exact
   backend/frontend image digests it rehearsed and attached signed GitHub
   provenance attestations to those digest-pinned images.
3. Run **Promote Investor Platform** manually with `target=staging` and that
   `ci_run_id`. The staging environment must supply its own host, base URL,
   SSH credentials, smoke users, and the staged `DATA_RELEASE_URI`. The
   workflow refuses missing values and never falls back to production.
4. The host deployment script:
   - starts PostgreSQL/Redis;
   - records current image references and creates verified database/data
     backups outside the Git checkout;
   - stops app processes, restores and verifies `DATA_RELEASE_URI` atomically;
   - creates the ORM baseline schema on a blank host, then applies the
     checksum-backed migration ledger;
   - imports the checksummed, version-scoped research-record payload through
     the normal `building → sealed → active` database lifecycle; and
   - recreates backend/worker/beat/frontend; and
   - requires proxied `/health`, JSON `/ready` (including migration-ledger,
     immutable-record trigger, and mounted-data inventory checksum
     attestations), and the frontend root to pass.
5. The workflow then runs `scripts/smoke_public_release.py` and an authenticated
   Playwright What-to-Buy smoke. It verifies auth, rank/stance/company,
   financials/price, DCF, cited memo save/reload, Book lock/export, two-user
   Book isolation, private DCF/memo visibility checks, and public admin
   denial.
6. On success, retain the GitHub staging run ID and its
   `staging-promotion-candidate` artifact, plus the release JSON in
   `/opt/rd-alpha-backups`. The host record contains
   the source SHA, both image digests, data URI/manifest hash,
   research-snapshot checksum, research-record checksum, sealed universe
   version, and applied migration ledger.

Do not promote staging if any smoke fails, readiness reports a missing
investor schema/data volume/email delivery, or the UI reports stale/error
state.

## 4. Production release

Run **Promote Investor Platform** again with `target=production`, the same
`ci_run_id`, and the successful `staging_promotion_run_id`. GitHub environment
approval is required for production. The workflow downloads the staging
   candidate and rejects any source SHA, image digest, data-manifest, or full
   release-descriptor difference, so production can only receive the
   already-tested artifact content.

Confirm the production SHA, backend image digest, frontend image digest,
migration ledger, data-manifest SHA, full release-descriptor checksum,
research-snapshot checksum, and universe version in the release record. Keep
the GitHub deployment log and generated rollback record.

During the first 30 minutes, monitor:

```sh
cd /opt/rd-alpha/deploy
docker compose logs --since 30m backend worker beat frontend redis postgres
curl -fsS "${PUBLIC_BASE_URL}/ready"
```

Alert on 5xx responses, failed background jobs, Redis disconnects, migration
checksum errors, readiness failures, and registration-email failures.

## 5. Rollback

Each deployment writes a timestamped rollback environment file and verified
database/data backups to `/opt/rd-alpha-backups` by default. The rollback
record carries the prior source SHA, digest-pinned images, and checksummed
database/data backups. First verify it without mutation:

```sh
cd /opt/rd-alpha
./scripts/rollback_release.sh \
  --record /opt/rd-alpha-backups/rollback-<timestamp>.env \
  --dry-run
```

After confirming the record is the intended prior release, apply it explicitly:

```sh
./scripts/rollback_release.sh \
  --record /opt/rd-alpha-backups/rollback-<timestamp>.env \
  --apply
```

The script verifies both backup checksums, recreates the target database before
restoring it (so failed-release schema objects cannot survive), verifies the
prior source revision's migration ledger, restores the data tree, checks out
the recorded source SHA, starts the recorded immutable images, and requires
local `/health` and `/ready`. It preserves the failed data tree beside the
restored one. Then re-run the authenticated API/browser smoke
against the public URL before announcing rollback completion. CI exercises the
record parser, checksum rejection, and a disposable apply rehearsal with
`scripts/test_rollback_release.sh`. Run a full Docker/PostgreSQL rollback drill
in staging before the first public production promotion.

Never edit an applied SQL migration to repair a release. Add a forward
migration, or restore the backup and deploy the prior immutable artifact.

## 6. One-time AWS host bootstrap

Set explicit environment values for `AWS_REGION`, `DATA_RELEASE_BUCKET` (or
`S3_BUCKET` when the release bucket is shared),
`DATA_RELEASE_PREFIX`, `EC2_INSTANCE_NAME`, `EC2_SG_NAME`, `EC2_AMI_ID`,
`EC2_KEY_NAME`, `ALLOWED_SSH_CIDR`, and (optionally)
`S3_OBJECT_LOCK_RETENTION_DAYS`, then run:

```sh
python deploy/setup_aws.py --create
```

The release bucket must be newly created with S3 Object Lock enabled:
`setup_aws.py` configures Compliance retention and denies delete operations
under `DATA_RELEASE_PREFIX`. S3 cannot add Object Lock to an existing bucket,
so replace an existing non-Object-Lock bucket rather than treating versioning
alone as immutable storage. The security group permits only HTTP/HTTPS publicly
and SSH from `ALLOWED_SSH_CIDR`; port 8000 is never exposed. Once the DNS A record has
propagated, set `PUBLIC_HOSTNAME`, `ROUTE53_HOSTED_ZONE_ID`, repository and
SSH bootstrap values, a read-only `GHCR_READ_TOKEN`, and `LETSENCRYPT_EMAIL`.
Then run `--configure-dns` and `--bootstrap` with the returned public host.
Bootstrap performs the initial checkout, registry login, and certificate
issuance over SSH rather than embedding credentials in EC2 user data.
The root EBS volume is encrypted (optionally with `EBS_KMS_KEY_ID`), and
bootstrap installs a daily systemd renewal timer that briefly stops the
frontend for Certbot's standalone renewal, copies renewed certificates with
safe permissions, and restarts the frontend.
