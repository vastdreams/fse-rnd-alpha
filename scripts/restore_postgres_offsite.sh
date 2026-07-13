#!/usr/bin/env bash
# Verify an off-host encrypted PostgreSQL backup, then restore it only on
# explicit confirmation of the currently selected immutable release.

set -Eeuo pipefail

RELEASE_ROOT="${RELEASE_ROOT:-/opt/rd-alpha}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-/etc/rd-alpha/prod.env}"
MANIFEST_URI=""
EXPECTED_MANIFEST_SHA256=""
CONFIRM_RELEASE_REF=""
APPLY=false

usage() {
  cat <<'USAGE'
Usage:
  restore_postgres_offsite.sh \
    --manifest-uri s3://bucket/path/manifest.json \
    --expected-manifest-sha256 <sha256> \
    --confirm-release-ref <active-release-ref> [--apply]

Without --apply, the command only downloads and verifies the immutable backup.
--apply stops application writers and replaces the active PostgreSQL database.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --deploy-env-file) DEPLOY_ENV_FILE="${2:-}"; shift 2 ;;
    --manifest-uri) MANIFEST_URI="${2:-}"; shift 2 ;;
    --expected-manifest-sha256) EXPECTED_MANIFEST_SHA256="${2:-}"; shift 2 ;;
    --confirm-release-ref) CONFIRM_RELEASE_REF="${2:-}"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "${MANIFEST_URI}" =~ ^s3://[^/]+/.+ ]] || {
  echo "--manifest-uri must identify an S3 manifest object." >&2
  exit 2
}
[[ "${EXPECTED_MANIFEST_SHA256}" =~ ^[0-9a-f]{64}$ ]] || {
  echo "--expected-manifest-sha256 must be a SHA-256 checksum." >&2
  exit 2
}
[[ -n "${CONFIRM_RELEASE_REF}" ]] || {
  echo "--confirm-release-ref is required." >&2
  exit 2
}
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
active_release_ref="$(basename "${release_dir}")"
[[ "${CONFIRM_RELEASE_REF}" == "${active_release_ref}" ]] || {
  echo "--confirm-release-ref does not match the active immutable release." >&2
  exit 1
}
[[ -f "${release_dir}/deploy/docker-compose.yml" ]] || {
  echo "No active immutable release is available for restore." >&2
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

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-offsite-restore.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT
chmod 0700 "${work_dir}"
manifest="${work_dir}/manifest.json"
dump="${work_dir}/postgres.dump"
manifest_location="${MANIFEST_URI#s3://}"
manifest_bucket="${manifest_location%%/*}"
manifest_key="${manifest_location#*/}"

verify_remote_locked_object() {
  local bucket="$1"
  local key="$2"
  local version_id="${3:-}"
  local details retention
  if [[ -n "${version_id}" ]]; then
    details="$(aws s3api head-object \
      --bucket "${bucket}" \
      --key "${key}" \
      --version-id "${version_id}" \
      --output json)"
    retention="$(aws s3api get-object-retention \
      --bucket "${bucket}" \
      --key "${key}" \
      --version-id "${version_id}" \
      --output json)"
  else
    details="$(aws s3api head-object \
      --bucket "${bucket}" \
      --key "${key}" \
      --output json)"
    retention="$(aws s3api get-object-retention \
      --bucket "${bucket}" \
      --key "${key}" \
      --output json)"
  fi
  python3 - "${details}" "${retention}" <<'PY'
import json
import sys

details = json.loads(sys.argv[1])
retention = json.loads(sys.argv[2]).get("Retention") or {}
if details.get("ServerSideEncryption") != "aws:kms":
    raise SystemExit("Remote backup object is not encrypted with SSE-KMS")
if retention.get("Mode") != "COMPLIANCE" or not retention.get("RetainUntilDate"):
    raise SystemExit("Remote backup object has no Compliance Object Lock retention")
PY
}

verify_remote_locked_object "${manifest_bucket}" "${manifest_key}"
aws s3 cp "${MANIFEST_URI}" "${manifest}" --only-show-errors
[[ "$(sha256 "${manifest}")" == "${EXPECTED_MANIFEST_SHA256}" ]] || {
  echo "Backup manifest checksum does not match the explicit operator confirmation." >&2
  exit 1
}

IFS=$'\t' read -r bucket key version_id expected_dump_sha database_name <<EOF
$(python3 - "${manifest}" <<'PY'
import hashlib
import json
import re
import sys

document = json.load(open(sys.argv[1]))
recorded = document.get("manifest_sha256")
content = dict(document)
content.pop("manifest_sha256", None)
actual = hashlib.sha256(
    json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
if document.get("schema_version") != 1 or recorded != actual:
    raise SystemExit("Backup manifest checksum does not match its contents")
dump = document.get("dump")
if not isinstance(dump, dict):
    raise SystemExit("Backup manifest has no dump binding")
for field in ("bucket", "key", "version_id", "sha256"):
    if not isinstance(dump.get(field), str) or not dump[field]:
        raise SystemExit(f"Backup manifest has no valid dump {field}")
if not re.fullmatch(r"[0-9a-f]{64}", dump["sha256"]):
    raise SystemExit("Backup manifest has an invalid dump checksum")
if dump.get("sse") != "aws:kms" or dump.get("retention_mode") != "COMPLIANCE":
    raise SystemExit("Backup manifest is not an encrypted Compliance-retained backup")
database = document.get("database")
if not isinstance(database, str) or not database:
    raise SystemExit("Backup manifest has no database name")
print("\t".join((dump["bucket"], dump["key"], dump["version_id"], dump["sha256"], database)))
PY
)
EOF

verify_remote_locked_object "${bucket}" "${key}" "${version_id}"
aws s3api get-object \
  --bucket "${bucket}" \
  --key "${key}" \
  --version-id "${version_id}" \
  "${dump}" \
  --output json >/dev/null
[[ "$(sha256 "${dump}")" == "${expected_dump_sha}" ]] || {
  echo "Downloaded PostgreSQL backup checksum does not match its manifest." >&2
  exit 1
}

if [[ "${APPLY}" != true ]]; then
  echo "Verified off-host backup; rerun with --apply to replace ${database_name}."
  exit 0
fi

postgres_user="$(env_value POSTGRES_USER)"
postgres_user="${postgres_user:-postgres}"
target_database="$(env_value POSTGRES_DB)"
target_database="${target_database:-rd_alpha}"
[[ "${target_database}" == "${database_name}" ]] || {
  echo "Backup database ${database_name} does not match target database ${target_database}." >&2
  exit 1
}
compose_file="${release_dir}/deploy/docker-compose.yml"
"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" \
  stop backend worker beat frontend
postgres_container="$("${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" ps -q postgres)"
[[ -n "${postgres_container}" ]] || { echo "PostgreSQL container is unavailable." >&2; exit 1; }
docker cp "${dump}" "${postgres_container}:/tmp/offsite-restore.dump"
"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" \
  exec -T postgres pg_restore --clean --if-exists -U "${postgres_user}" -d "${database_name}" \
  /tmp/offsite-restore.dump
"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" \
  exec -T postgres rm -f /tmp/offsite-restore.dump
"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" \
  exec -T postgres psql -U "${postgres_user}" -d "${database_name}" -c "SELECT 1" >/dev/null
"${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" \
  up -d backend worker beat frontend

echo "Restored verified off-host PostgreSQL backup to ${database_name}."
