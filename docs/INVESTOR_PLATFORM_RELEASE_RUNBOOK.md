# Investor platform release runbook

This runbook releases an immutable application image and an immutable data
artifact together. Do not deploy from a mutable source tree, a local cache, or a
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
4. Produce the write-once evidence coverage report from the sealed version
   before staging. It lists financial-cache, filing-text, filing-map,
   text-stance, explicit kill-state, and fair-value-band coverage without
   inferring missing research:

   ```sh
   DATABASE_URL=<staging-postgres-url> \
     python3 ./scripts/research_coverage_report.py \
       --universe-version <immutable-universe-version> \
       --data-dir <mounted-data-volume>
   ```

   The report is stored at
   `<data-dir>/coverage_reports/<universe-version>.json`. It cannot be
   overwritten with a different result. After a verified source-evidence
   cohort, rebuild and seal a new universe version; do not rewrite an old
   report to make its coverage appear better.
   Run this staging-only evidence cycle at least weekly and after any provider
   repair: inspect the prior report, backfill only primary source material,
   rebuild/seal, generate the new report, then stage the new immutable artifact.
   Never run cache or filing backfills against production's restored data tree.
5. Stage the artifact, not the working `data/` tree:

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
   records, recomputes the coverage report over the sealed rows and staged data
   snapshot before validating/binding it, and uploads the tarball,
   manifest, research snapshot,
   research-record payload, and release metadata. It snapshots the source
   tree before manifest/archive generation, pins every payload to its S3
   VersionId in `release.json`, and rejects objects without Compliance Object
   Lock retention. Conditional S3 writes accept a retry only when every
   existing object has the same checksum.

## 2. Configure each target and its release agent

On staging and production hosts, keep these values in the root-owned,
non-release file `/etc/rd-alpha/prod.env`:

- strong unique `POSTGRES_PASSWORD` and `SECRET_KEY` (at least 32 characters)
- `BACKEND_DATABASE_URL`, an internal `postgresql+asyncpg://` URL containing
  the percent-encoded PostgreSQL password; do not interpolate the raw password
  into a URL
- a valid `SEC_USER_AGENT`
- `DATA_DIR=/opt/rd-alpha-data` (created by infrastructure setup and kept
  outside `/opt/rd-alpha` so restores never dirty a release directory)
- `CERTS_DIR=/opt/rd-alpha-certs` and
  `CERTBOT_WEBROOT=/opt/rd-alpha-certbot-webroot`, also outside the release
  root so certificate renewal cannot alter a deploy artifact
- `DATA_RELEASE_URI` from the staging command
- `DATA_RELEASE_DESCRIPTOR_SHA256` emitted by the staging command; it is the
  SHA-256 of `release.json` and binds the archive, database snapshot, and
  research-record checksums as one promoted artifact
- `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`, `BACKUP_KMS_KEY_ID`, and
  `BACKUP_RETENTION_DAYS` for the distinct Object-Lock-enabled off-host
  PostgreSQL backup bucket. The instance role needs only the configured backup
  prefix and the listed KMS key; its KMS key policy must also trust that role.
- optional `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, and
  `SENTRY_TRACES_SAMPLE_RATE`. The application removes authorization headers,
  cookies, request bodies, query strings, user fields, transaction URL values,
  and span payloads before sending error or performance events.
- optional `OPS_ALERT_WEBHOOK_URL`, which receives only failed periodic health
  notifications and never receives user, request, or secret data.
- target-specific `PUBLIC_HOSTNAME`, `AUTH_RESET_URL`, `AUTH_VERIFY_URL`,
  `STRIPE_SUCCESS_URL`, and `STRIPE_CANCEL_URL` — no production URL is used
  as a fallback
- `AUTH_REQUIRE_EMAIL_VERIFICATION=true`, `AUTH_EMAIL_FROM`, and
  `RESEND_API_KEY` for public registration
- two verified, non-admin smoke accounts whose credentials are stored as
  target-local secret-manager entries:
  `SMOKE_TEST_EMAIL`, `SMOKE_TEST_PASSWORD`, `SMOKE_SECONDARY_EMAIL`, and
  `SMOKE_SECONDARY_PASSWORD`

On a blank host, set `AUTH_SEED_EMAIL`/`AUTH_SEED_PASSWORD` and the distinct
`AUTH_SECONDARY_SEED_EMAIL`/`AUTH_SECONDARY_SEED_PASSWORD` to those smoke
credentials. Bootstrap creates them idempotently and never rotates an existing
password hash.

The target needs Docker Compose, `aws`, `tar`, `curl`, `flock`,
`s3:GetObjectVersion` permission for the staged payloads, and a persistent
Docker login with pull access to the GitLab registry backend and frontend
images. The staging publisher also needs
`s3:GetObjectRetention` so it can prove Compliance Object Lock retention.
`deploy/setup_aws.py --create` provisions an EC2 role with read-only access
only to the configured release prefix and, when backup variables are supplied,
only the configured encrypted-backup prefix; do not place AWS access keys in
`/etc/rd-alpha/prod.env`.
`DATA_RELEASE_URI` is intentionally required by `scripts/deploy_release.sh`.

Install the release agent once from a reviewed local release bundle:

```sh
sudo bash deploy/install_release_agent.sh
```

Set `/etc/rd-alpha/release-agent.env` to a least-privilege GitLab Generic
Package Registry token and the project package URL:

```sh
RELEASE_BASE_URL=https://gitlab.com/api/v4/projects/<project-id>/packages/generic/investor-platform
RELEASE_TOKEN=<read-only-package-token>
RELEASE_AUTH_HEADER=PRIVATE-TOKEN
RELEASE_ROOT=/opt/rd-alpha
STATE_DIR=/var/lib/rd-alpha
DEPLOY_ENV_FILE=/etc/rd-alpha/prod.env
BACKUP_DIR=/var/lib/rd-alpha/backups
```

Protect both files as `root:root` mode `0600`. The production target has no CI
SSH key and no Git remote. The release agent performs a host-initiated HTTPS
pull only after an operator selects a specific version. When staging and
production use separate buckets, copy every immutable artifact object unchanged
and retain both the final manifest-SHA path component and `release.json`
checksum.

On production only, require the immutable staging browser proof before an
activation:

```sh
REQUIRE_STAGING_PROOF=true
STAGING_PROOF_BASE_URL=https://gitlab.com/api/v4/projects/<project-id>/packages/generic/investor-platform-proofs
```

The agent reads `staging-proof.json` with the same read-only package token and
rejects the activation unless its source SHA, pipeline ID, release version, and
passed staging API/browser job IDs match the requested release. It also rejects
the activation unless the production `DATA_RELEASE_URI` ends in the same
immutable data-manifest SHA that the staging API/browser proof attested.

### One-time legacy host migration

If an older host still stores mutable `data/` inside `/opt/rd-alpha`, take a
verified archive first and move that tree outside the release root. Stage the
moved data as a release artifact, then use `DATA_DIR=/opt/rd-alpha-data`;
never add a symlink back into an immutable release directory.

## 3. Staging release

1. Merge the candidate only after GitLab `main` has a green pipeline. It must
   pass PostgreSQL integration, lint/type-check, frontend unit tests,
   Playwright, migration replay, immutable data-artifact tests, and the
   Docker/Compose rehearsal. No job is allowed to continue after a failed gate.
2. Record the GitLab pipeline ID and the source SHA emitted by
   `publish_release_bundle`. The immutable release version is:

   ```text
   <40-character-source-sha>-<GitLab-pipeline-id>
   ```

   GitLab publishes that version's `release.json`, bundle checksum, and host
   deployment bundle to the Generic Package Registry. The manifest names the
   exact GitLab Container Registry image digests.
3. On the staging host, fetch and activate that exact version:

   ```sh
   sudo systemctl start rd-alpha-promote@<source-sha>-<pipeline-id>
   sudo journalctl -u rd-alpha-promote@<source-sha>-<pipeline-id> --no-pager
   ```

   The agent verifies the manifest source SHA/pipeline ID, bundle checksum, and
   both image digests before it extracts into
   `/opt/rd-alpha/releases/<source-sha>-<pipeline-id>`.
4. The host deployment script then:
   - starts PostgreSQL/Redis;
   - records current image references and creates verified database/data
     backups outside the release root;
   - stops app processes, restores and verifies `DATA_RELEASE_URI` atomically;
   - creates the ORM baseline schema on a blank host, then applies the
     checksum-backed migration ledger;
   - imports the checksummed, version-scoped research-record payload through
     the normal `building → sealed → active` database lifecycle; and
   - recreates backend/worker/beat/frontend; and
   - requires proxied `/health`, JSON `/ready` (including migration-ledger,
     immutable-record trigger, and mounted-data inventory checksum
     attestations), and the frontend root to pass.
5. Run the target's authenticated staging smoke suite and retain its evidence.
   It must verify auth, rank/stance/company, financials/price, DCF, cited memo
   save/reload, Book lock/export, two-user Book isolation, private DCF/memo
   visibility checks, public admin denial, and the authenticated
   `/app/universe?mode=buy` render.
6. On success, retain the GitLab pipeline URL, the exact release version,
   `release.json`, target smoke output, and the record in
   `/var/lib/rd-alpha/backups`. The host record contains
   the source SHA, both image digests, data URI/manifest hash,
   research-snapshot checksum, research-record checksum, sealed universe
   version, and applied migration ledger.

Do not promote staging if any smoke fails, readiness reports a missing
investor schema/data volume/email delivery, or the UI reports stale/error
state.

### Retained release-proof gates

GitLab `main` publishes four protected manual proof jobs after the release
bundle exists:

1. `staging_api_smoke` runs the current release's
   `run_authenticated_release_smoke.sh` from an
   `investor-platform-staging` runner. It verifies the local release version,
   then records API evidence under
   `/var/lib/rd-alpha/smoke-evidence/staging/<version>/…` and uploads a
   secret-free copy as a one-year GitLab artifact.
2. `staging_browser_smoke` runs the real login, What-to-Buy BUY row, and
   sell-ceiling browser check with `RELEASE_SMOKE_EXPECTED_BUY_TICKER`.
3. `production_api_smoke` remains unavailable until the staging browser proof
   succeeds, and makes the same immutable source/data checks on the production
   host.
4. `production_browser_smoke` completes the production proof chain and
   retains the Playwright trace/report.

Register the staging and production runners as protected runners with the
matching tags. Store `RELEASE_SMOKE_BASE_URL`,
`RELEASE_SMOKE_EMAIL`, `RELEASE_SMOKE_PASSWORD`,
`RELEASE_SMOKE_SECOND_EMAIL`, `RELEASE_SMOKE_SECOND_PASSWORD`, and
`RELEASE_SMOKE_EXPECTED_BUY_TICKER` as protected environment-scoped variables.
Never place them in a release bundle, artifact, or checked-in environment
file. Set `RELEASE_SMOKE_EXPECTED_DATA_MANIFEST_SHA256` for every proof job;
the API and browser checks reject a target whose mounted data manifest is not
the explicitly approved staged artifact.

## 4. Production release

Only promote the same release version and the same immutable data descriptor
that passed staging. Record the staging smoke evidence and obtain the required
production approval outside CI before starting the target-local unit:

```sh
sudo systemctl start rd-alpha-promote@<source-sha>-<pipeline-id>
sudo journalctl -u rd-alpha-promote@<source-sha>-<pipeline-id> --no-pager
```

The agent will reject a source SHA, pipeline ID, package checksum, or image
digest mismatch. It never receives a mutable source checkout or accepts a
runner-provided command.

Confirm the production SHA, backend image digest, frontend image digest,
migration ledger, data-manifest SHA, full release-descriptor checksum,
research-snapshot checksum, and universe version in the release record. Keep
the GitLab pipeline link, target journal evidence, and generated rollback
record.

During the first 30 minutes, monitor:

```sh
cd /opt/rd-alpha/current/deploy
docker compose logs --since 30m backend worker beat frontend redis postgres
curl -fsS "${PUBLIC_BASE_URL}/ready"
```

Alert on 5xx responses, failed background jobs, Redis disconnects, migration
checksum errors, readiness failures, and registration-email failures.

### Continuous health and recovery controls

`deploy/setup_aws.py --bootstrap` installs the TLS renewal timer, while
`deploy/install_release_agent.sh` and the bootstrap path install the health and
backup timers:

- `rd-alpha-tls-renew.timer` renews the certificate and safely restarts the
  frontend only when required.
- `rd-alpha-healthcheck.timer` runs every five minutes. It records a
  secret-free release ID, service state, worker/beat health, and public
  `/ready` evidence under `/var/lib/rd-alpha/health-evidence/`; it also
  verifies that the running container's source SHA, release reference, and
  image digests match the active immutable release manifest. It calls the
  optional operator webhook only on failure.
- `rd-alpha-offsite-backup.timer` creates a daily SSE-KMS encrypted,
  Compliance-Object-Locked PostgreSQL dump in the designated off-host bucket.

Check timers and the latest release evidence after promotion:

```sh
systemctl list-timers 'rd-alpha-*'
ls -lt /var/lib/rd-alpha/health-evidence/ | head
```

Run a restore drill against a staging host before public production promotion.
The default verifies the operator-confirmed manifest checksum, dump checksum,
SSE-KMS encryption, and Compliance Object Lock retention without mutation;
mutation needs both `--apply` and the exact currently active release reference:

```sh
/opt/rd-alpha/current/scripts/restore_postgres_offsite.sh \
  --manifest-uri s3://<backup-bucket>/<prefix>/.../manifest.json \
  --expected-manifest-sha256 <recorded-file-sha256> \
  --confirm-release-ref <active-source-sha>-<pipeline-id>

/opt/rd-alpha/current/scripts/restore_postgres_offsite.sh \
  --manifest-uri s3://<backup-bucket>/<prefix>/.../manifest.json \
  --expected-manifest-sha256 <recorded-file-sha256> \
  --confirm-release-ref <active-source-sha>-<pipeline-id> \
  --apply
```

## 5. Rollback

Each deployment writes a timestamped rollback environment file and verified
database/data backups to `/var/lib/rd-alpha/backups` by default. The rollback
record carries the prior source SHA, retained immutable release version,
digest-pinned images, and checksummed database/data backups. First verify it
without mutation:

```sh
RELEASE_ROOT=/opt/rd-alpha \
DEPLOY_ENV_FILE=/etc/rd-alpha/prod.env \
  /opt/rd-alpha/current/scripts/rollback_release.sh \
  --record /var/lib/rd-alpha/backups/rollback-<timestamp>.env \
  --dry-run
```

After confirming the record is the intended prior release, apply it explicitly:

```sh
RELEASE_ROOT=/opt/rd-alpha \
DEPLOY_ENV_FILE=/etc/rd-alpha/prod.env \
  /opt/rd-alpha/current/scripts/rollback_release.sh \
  --record /var/lib/rd-alpha/backups/rollback-<timestamp>.env \
  --apply
```

The script verifies both backup checksums, recreates the target database before
restoring it (so failed-release schema objects cannot survive), verifies the
prior release's migration ledger, restores the data tree, reselects the
retained immutable release directory, starts the recorded immutable images,
and requires local `/health` and `/ready`. It preserves the failed data tree
beside the restored one. Then re-run the authenticated API/browser smoke
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
`S3_OBJECT_LOCK_RETENTION_DAYS`, plus `BACKUP_S3_BUCKET`,
`BACKUP_S3_PREFIX`, and `BACKUP_KMS_KEY_ARN` when enabling off-host recovery,
then run:

```sh
python deploy/setup_aws.py --create
```

The release bucket must be newly created with S3 Object Lock enabled:
`setup_aws.py` configures Compliance retention and denies delete operations
under `DATA_RELEASE_PREFIX`. S3 cannot add Object Lock to an existing bucket,
so replace an existing non-Object-Lock bucket rather than treating versioning
alone as immutable storage. The security group permits only HTTP/HTTPS publicly
and SSH from `ALLOWED_SSH_CIDR`; port 8000 is never exposed. Once the DNS A record has
propagated, set `PUBLIC_HOSTNAME`, `ROUTE53_HOSTED_ZONE_ID`, a read-only
GitLab Container Registry token, a read-only GitLab Generic Package Registry
token, and `LETSENCRYPT_EMAIL`. Then run `--configure-dns` and `--bootstrap`
with the returned public host. Bootstrap creates the external state
directories, configures registry login and certificate issuance, and installs
the release agent without creating a production Git checkout.
The root EBS volume is encrypted (optionally with `EBS_KMS_KEY_ID`), and
bootstrap installs a daily systemd renewal timer that briefly stops the
frontend for Certbot's standalone renewal, copies renewed certificates with
safe permissions, and restarts the frontend.
