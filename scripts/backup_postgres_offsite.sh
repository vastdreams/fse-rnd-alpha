#!/usr/bin/env bash
# Create an encrypted, Object-Locked PostgreSQL backup outside the release host.

set -Eeuo pipefail

RELEASE_ROOT="${RELEASE_ROOT:-/opt/rd-alpha}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-/etc/rd-alpha/prod.env}"
STATE_DIR="${STATE_DIR:-/var/lib/rd-alpha}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX:-}"
BACKUP_KMS_KEY_ID="${BACKUP_KMS_KEY_ID:-}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-}"

usage() {
  cat <<'USAGE'
Usage: backup_postgres_offsite.sh [options]

Options:
  --release-root <path>     Immutable release root (default: /opt/rd-alpha)
  --deploy-env-file <path>  Root-owned Compose environment file
  --state-dir <path>        Host state directory (default: /var/lib/rd-alpha)
  --bucket <name>           Object-Lock-enabled backup bucket
  --prefix <path>           Backup key prefix
  --kms-key-id <id-or-arn>  KMS key used for SSE-KMS encryption
  --retention-days <n>      Compliance retention days (default: 35)
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --deploy-env-file) DEPLOY_ENV_FILE="${2:-}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --bucket) BACKUP_S3_BUCKET="${2:-}"; shift 2 ;;
    --prefix) BACKUP_S3_PREFIX="${2:-}"; shift 2 ;;
    --kms-key-id) BACKUP_KMS_KEY_ID="${2:-}"; shift 2 ;;
    --retention-days) BACKUP_RETENTION_DAYS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "${DEPLOY_ENV_FILE}" ]] || {
  echo "Missing deployment environment file: ${DEPLOY_ENV_FILE}" >&2
  exit 1
}
command -v aws >/dev/null 2>&1 || { echo "aws CLI is required" >&2; exit 1; }

release_dir="$(python3 - "${RELEASE_ROOT}/current" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).resolve())
PY
)"
[[ -f "${release_dir}/deploy/docker-compose.yml" && -f "${release_dir}/release.json" ]] || {
  echo "No active immutable release is available for backup." >&2
  exit 1
}

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose (or docker-compose) is required" >&2
  exit 1
fi

env_value() {
  python3 - "${DEPLOY_ENV_FILE}" "$1" <<'PY'
import sys

path, expected = sys.argv[1:]
for raw in open(path):
    line = raw.rstrip("\n")
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key != expected:
        continue
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    print(value)
    break
PY
}

if [[ -z "${BACKUP_S3_BUCKET}" ]]; then
  BACKUP_S3_BUCKET="$(env_value BACKUP_S3_BUCKET)"
fi
if [[ -z "${BACKUP_S3_PREFIX}" ]]; then
  BACKUP_S3_PREFIX="$(env_value BACKUP_S3_PREFIX)"
fi
if [[ -z "${BACKUP_KMS_KEY_ID}" ]]; then
  BACKUP_KMS_KEY_ID="$(env_value BACKUP_KMS_KEY_ID)"
fi
if [[ -z "${BACKUP_RETENTION_DAYS}" ]]; then
  BACKUP_RETENTION_DAYS="$(env_value BACKUP_RETENTION_DAYS)"
fi
BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX:-investor-platform-postgres-backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-35}"

: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET or --bucket is required}"
: "${BACKUP_KMS_KEY_ID:?BACKUP_KMS_KEY_ID or --kms-key-id is required}"
[[ "${BACKUP_RETENTION_DAYS}" =~ ^[1-9][0-9]*$ ]] || {
  echo "BACKUP_RETENTION_DAYS must be a positive integer." >&2
  exit 2
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

postgres_user="$(env_value POSTGRES_USER)"
postgres_database="$(env_value POSTGRES_DB)"
postgres_user="${postgres_user:-postgres}"
postgres_database="${postgres_database:-rd_alpha}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
retain_until="$(python3 - "${BACKUP_RETENTION_DAYS}" <<'PY'
import sys
from datetime import datetime, timedelta, timezone

print((datetime.now(timezone.utc) + timedelta(days=int(sys.argv[1]))).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"
release_ref="$(basename "${release_dir}")"
work_dir="$(mktemp -d "${STATE_DIR}/offsite-backup.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT
chmod 0700 "${work_dir}"
dump="${work_dir}/postgres.dump"
manifest="${work_dir}/manifest.json"

"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${release_dir}/deploy/docker-compose.yml" \
  exec -T postgres pg_dump -U "${postgres_user}" -Fc "${postgres_database}" > "${dump}"
[[ -s "${dump}" ]] || { echo "PostgreSQL backup is empty." >&2; exit 1; }

dump_sha="$(sha256 "${dump}")"
dump_bytes="$(python3 - "${dump}" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).stat().st_size)
PY
)"
key_prefix="${BACKUP_S3_PREFIX#/}"
key_prefix="${key_prefix%/}"
dump_key="${key_prefix}/${release_ref}/${timestamp}/postgres.dump"
manifest_key="${key_prefix}/${release_ref}/${timestamp}/manifest.json"

put_object() {
  local source="$1"
  local key="$2"
  local response
  response="$(aws s3api put-object \
    --bucket "${BACKUP_S3_BUCKET}" \
    --key "${key}" \
    --body "${source}" \
    --if-none-match '*' \
    --server-side-encryption aws:kms \
    --ssekms-key-id "${BACKUP_KMS_KEY_ID}" \
    --object-lock-mode COMPLIANCE \
    --object-lock-retain-until-date "${retain_until}" \
    --metadata "sha256=$(sha256 "${source}")" \
    --output json)"
  python3 - "${response}" <<'PY'
import json
import sys

version_id = json.loads(sys.argv[1]).get("VersionId")
if not isinstance(version_id, str) or not version_id:
    raise SystemExit("S3 backup upload did not return an immutable VersionId")
print(version_id)
PY
}

verify_remote_object() {
  local key="$1"
  local version_id="$2"
  local details retention
  details="$(aws s3api head-object \
    --bucket "${BACKUP_S3_BUCKET}" \
    --key "${key}" \
    --version-id "${version_id}" \
    --output json)"
  retention="$(aws s3api get-object-retention \
    --bucket "${BACKUP_S3_BUCKET}" \
    --key "${key}" \
    --version-id "${version_id}" \
    --output json)"
  python3 - "${details}" "${retention}" <<'PY'
import json
import sys

details = json.loads(sys.argv[1])
retention = json.loads(sys.argv[2]).get("Retention") or {}
if details.get("ServerSideEncryption") != "aws:kms":
    raise SystemExit("Remote backup is not encrypted with SSE-KMS")
if retention.get("Mode") != "COMPLIANCE" or not retention.get("RetainUntilDate"):
    raise SystemExit("Remote backup has no Compliance Object Lock retention")
PY
}

dump_version_id="$(put_object "${dump}" "${dump_key}")"
verify_remote_object "${dump_key}" "${dump_version_id}"

RELEASE_DIR="${release_dir}" RELEASE_REF="${release_ref}" DUMP_KEY="${dump_key}" \
DUMP_VERSION_ID="${dump_version_id}" DUMP_SHA="${dump_sha}" DUMP_BYTES="${dump_bytes}" \
POSTGRES_DATABASE="${postgres_database}" BACKUP_BUCKET="${BACKUP_S3_BUCKET}" \
RETAIN_UNTIL="${retain_until}" KMS_KEY_ID="${BACKUP_KMS_KEY_ID}" \
python3 - <<'PY' > "${manifest}"
import json
import os
from datetime import datetime, timezone

release = json.load(open(f"{os.environ['RELEASE_DIR']}/release.json"))
document = {
    "schema_version": 1,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "release": {
        "release_ref": os.environ["RELEASE_REF"],
        "source_sha": release.get("source_sha"),
        "pipeline_id": release.get("pipeline_id"),
    },
    "database": os.environ["POSTGRES_DATABASE"],
    "dump": {
        "bucket": os.environ["BACKUP_BUCKET"],
        "key": os.environ["DUMP_KEY"],
        "version_id": os.environ["DUMP_VERSION_ID"],
        "sha256": os.environ["DUMP_SHA"],
        "bytes": int(os.environ["DUMP_BYTES"]),
        "sse": "aws:kms",
        "kms_key_id": os.environ["KMS_KEY_ID"],
        "retention_mode": "COMPLIANCE",
        "retain_until": os.environ["RETAIN_UNTIL"],
    },
}
document["manifest_sha256"] = __import__("hashlib").sha256(
    json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
print(json.dumps(document, indent=2, sort_keys=True))
PY

manifest_sha="$(sha256 "${manifest}")"
manifest_version_id="$(put_object "${manifest}" "${manifest_key}")"
verify_remote_object "${manifest_key}" "${manifest_version_id}"

printf 'BACKUP_MANIFEST_URI=s3://%s/%s\n' "${BACKUP_S3_BUCKET}" "${manifest_key}"
printf 'BACKUP_MANIFEST_SHA256=%s\n' "${manifest_sha}"
printf 'BACKUP_MANIFEST_VERSION_ID=%s\n' "${manifest_version_id}"
printf 'BACKUP_DUMP_VERSION_ID=%s\n' "${dump_version_id}"
