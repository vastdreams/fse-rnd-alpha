#!/usr/bin/env bash
# Restore one verified pre-deploy database/data/image record produced by
# deploy_release.sh. This is intentionally explicit: validate with --dry-run,
# then rerun with --apply only after choosing the rollback record.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-${ROOT_DIR}/deploy}"
APPLY=false
ROLLBACK_RECORD=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/rollback_release.sh --record /path/to/rollback-<timestamp>.env --dry-run
  scripts/rollback_release.sh --record /path/to/rollback-<timestamp>.env --apply

The script verifies record syntax plus database/data backup checksums before it
changes anything. --apply restores the database and data tree, checks out the
recorded source SHA, restarts the recorded digest-pinned images, and requires
local /health and /ready to pass.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --record)
      ROLLBACK_RECORD="${2:-}"
      shift 2
      ;;
    --dry-run)
      APPLY=false
      shift
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown rollback option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "${ROLLBACK_RECORD}" ]] || {
  echo "--record is required." >&2
  usage >&2
  exit 2
}
[[ -f "${ROLLBACK_RECORD}" ]] || {
  echo "Rollback record does not exist: ${ROLLBACK_RECORD}" >&2
  exit 2
}

record_value() {
  local key="$1"
  python3 - "${ROLLBACK_RECORD}" "${key}" <<'PY'
import re
import shlex
import sys
from pathlib import Path

record, wanted = sys.argv[1:3]
allowed = {
    "BACKEND_IMAGE",
    "FRONTEND_IMAGE",
    "RELEASE_SHA",
    "FAILED_RELEASE_SHA",
    "DATABASE_BACKUP",
    "DATA_BACKUP",
    "DATA_BACKUP_SOURCE",
    "DATA_DIR",
    "DATA_RELEASE_URI",
}
if wanted not in allowed:
    raise SystemExit(f"Unsupported rollback key: {wanted}")

values = {}
for raw in Path(record).read_text().splitlines():
    if not raw or raw.startswith("#"):
        continue
    if "=" not in raw:
        raise SystemExit(f"Malformed rollback record line: {raw!r}")
    key, encoded = raw.split("=", 1)
    if key not in allowed:
        raise SystemExit(f"Unexpected rollback record key: {key}")
    parsed = shlex.split(encoded, posix=True)
    if len(parsed) != 1:
        raise SystemExit(f"Invalid shell-escaped rollback value for {key}")
    values[key] = parsed[0]

print(values.get(wanted, ""))
PY
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify_backup_checksum() {
  local backup="$1"
  local checksum_file="${backup}.sha256"
  [[ -f "${backup}" && -s "${backup}" ]] || {
    echo "Required rollback backup is missing or empty: ${backup}" >&2
    return 1
  }
  [[ -f "${checksum_file}" ]] || {
    echo "Rollback backup checksum is missing: ${checksum_file}" >&2
    return 1
  }
  local expected actual
  expected="$(awk 'NR == 1 { print $1 }' "${checksum_file}")"
  actual="$(sha256_of "${backup}")"
  [[ "${expected}" =~ ^[0-9a-f]{64}$ && "${expected}" == "${actual}" ]] || {
    echo "Rollback backup checksum mismatch: ${backup}" >&2
    return 1
  }
}

BACKEND_IMAGE="$(record_value BACKEND_IMAGE)"
FRONTEND_IMAGE="$(record_value FRONTEND_IMAGE)"
RELEASE_SHA="$(record_value RELEASE_SHA)"
DATABASE_BACKUP="$(record_value DATABASE_BACKUP)"
DATA_BACKUP="$(record_value DATA_BACKUP)"
DATA_DIR="$(record_value DATA_DIR)"
DATA_BACKUP_SOURCE="$(record_value DATA_BACKUP_SOURCE)"
recorded_backend_image="${BACKEND_IMAGE}"
recorded_frontend_image="${FRONTEND_IMAGE}"
recorded_release_sha="${RELEASE_SHA}"

[[ "${BACKEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "Rollback record has no digest-pinned BACKEND_IMAGE." >&2
  exit 1
}
[[ "${FRONTEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "Rollback record has no digest-pinned FRONTEND_IMAGE." >&2
  exit 1
}
[[ "${RELEASE_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  echo "Rollback record has no valid prior RELEASE_SHA." >&2
  exit 1
}
[[ -n "${DATABASE_BACKUP}" && -n "${DATA_BACKUP}" ]] || {
  echo "Rollback record has no complete database/data backup pair." >&2
  exit 1
}
[[ -n "${DATA_BACKUP_SOURCE}" ]] || DATA_BACKUP_SOURCE="${DATA_DIR}"
[[ "${DATA_BACKUP_SOURCE}" == /* ]] || {
  echo "Rollback record data path must be absolute." >&2
  exit 1
}

verify_backup_checksum "${DATABASE_BACKUP}"
verify_backup_checksum "${DATA_BACKUP}"

python3 - "${DATA_BACKUP}" "${DATA_BACKUP_SOURCE}" <<'PY'
import subprocess
import sys
from pathlib import PurePosixPath

archive, target = sys.argv[1:]
root = PurePosixPath(target).name
members = subprocess.check_output(["tar", "-tzf", archive], text=True).splitlines()
if not members:
    raise SystemExit("Rollback data archive is empty")
for member in members:
    path = PurePosixPath(member)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"Unsafe rollback archive member: {member}")
    if not path.parts or path.parts[0] != root:
        raise SystemExit(
            f"Rollback archive root {path.parts[0] if path.parts else member!r} "
            f"does not match expected data directory {root!r}"
        )
PY

if [[ "${APPLY}" != true ]]; then
  echo "Rollback record and backup checksums are valid. No changes applied."
  exit 0
fi

if git -C "${ROOT_DIR}" rev-parse HEAD >/dev/null 2>&1; then
  [[ -z "$(git -C "${ROOT_DIR}" status --porcelain)" ]] || {
    echo "Refusing rollback from a dirty source checkout." >&2
    exit 1
  }
  if ! git -C "${ROOT_DIR}" cat-file -e "${RELEASE_SHA}^{commit}" 2>/dev/null; then
    git -C "${ROOT_DIR}" fetch --prune origin
  fi
  git -C "${ROOT_DIR}" cat-file -e "${RELEASE_SHA}^{commit}" 2>/dev/null || {
    echo "Recorded rollback source SHA is not available from origin: ${RELEASE_SHA}" >&2
    exit 1
  }
  git -C "${ROOT_DIR}" checkout --detach "${RELEASE_SHA}"
else
  echo "Rollback requires a Git checkout to restore ${RELEASE_SHA}." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose (or docker-compose) is required" >&2
  exit 1
fi

[[ -f "${DEPLOY_DIR}/.env" ]] || {
  echo "Missing ${DEPLOY_DIR}/.env." >&2
  exit 1
}

while IFS= read -r line || [[ -n "${line}" ]]; do
  case "${line}" in
    ''|\#*) continue ;;
  esac
  [[ "${line}" == *"="* ]] || continue
  key="${line%%=*}"
  value="${line#*=}"
  case "${key}" in
    BACKEND_IMAGE|FRONTEND_IMAGE|RELEASE_SHA)
      echo "Reserved rollback input must not be set in ${DEPLOY_DIR}/.env: ${key}" >&2
      exit 1
      ;;
  esac
  value="${value%\"}"
  value="${value#\"}"
  export "${key}=${value}"
done < "${DEPLOY_DIR}/.env"

# Images and source SHA come from the verified rollback record, never from
# mutable host-local configuration loaded for PostgreSQL and TLS settings.
BACKEND_IMAGE="${recorded_backend_image}"
FRONTEND_IMAGE="${recorded_frontend_image}"
RELEASE_SHA="${recorded_release_sha}"
export BACKEND_IMAGE FRONTEND_IMAGE RELEASE_SHA

cd "${DEPLOY_DIR}"
"${COMPOSE[@]}" config -q
"${COMPOSE[@]}" up -d postgres redis

for _ in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T postgres \
    pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" >/dev/null; then
    break
  fi
  sleep 2
done
"${COMPOSE[@]}" exec -T postgres \
  pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" >/dev/null

"${COMPOSE[@]}" stop backend worker beat frontend >/dev/null 2>&1 || true
postgres_container="$("${COMPOSE[@]}" ps -q postgres)"
[[ -n "${postgres_container}" ]] || {
  echo "PostgreSQL container is unavailable for rollback." >&2
  exit 1
}
[[ "${POSTGRES_DB:-rd_alpha}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || {
  echo "POSTGRES_DB must be a simple PostgreSQL identifier for rollback." >&2
  exit 1
}
[[ "${POSTGRES_USER:-postgres}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || {
  echo "POSTGRES_USER must be a simple PostgreSQL identifier for rollback." >&2
  exit 1
}
# pg_restore --clean cannot remove objects that did not exist when the old
# dump was made. Recreate the database first so a failed release's schema,
# migrations, and tenant records cannot survive the rollback.
"${COMPOSE[@]}" exec -T postgres \
  psql -U "${POSTGRES_USER:-postgres}" -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB:-rd_alpha}' AND pid <> pg_backend_pid(); DROP DATABASE IF EXISTS \"${POSTGRES_DB:-rd_alpha}\"; CREATE DATABASE \"${POSTGRES_DB:-rd_alpha}\" OWNER \"${POSTGRES_USER:-postgres}\";"
docker cp "${DATABASE_BACKUP}" "${postgres_container}:/tmp/rollback.dump"
"${COMPOSE[@]}" exec -T postgres \
  pg_restore -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" \
  --no-owner --exit-on-error /tmp/rollback.dump
"${COMPOSE[@]}" exec -T postgres rm -f /tmp/rollback.dump

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -e "${DATA_BACKUP_SOURCE}" ]]; then
  mv "${DATA_BACKUP_SOURCE}" "${DATA_BACKUP_SOURCE}.failed-${timestamp}"
fi
mkdir -p "$(dirname "${DATA_BACKUP_SOURCE}")"
tar -C "$(dirname "${DATA_BACKUP_SOURCE}")" -xzf "${DATA_BACKUP}"

export BACKEND_IMAGE FRONTEND_IMAGE
export DATA_DIR="${DATA_BACKUP_SOURCE}"
env -u DATABASE_URL \
  MIGRATIONS_USE_COMPOSE=true \
  "${ROOT_DIR}/scripts/run_migrations.sh" --verify-only
"${COMPOSE[@]}" pull
"${COMPOSE[@]}" up -d --force-recreate --remove-orphans backend worker beat frontend

for _ in $(seq 1 30); do
  ready_json="$(curl -fsS http://localhost/ready || true)"
  if curl -fsS http://localhost/health >/dev/null \
    && grep -q '"ready":true' <<< "${ready_json}" \
    && curl -fsS http://localhost/ >/dev/null; then
    echo "Rollback restored ${RELEASE_SHA} and passed local readiness."
    exit 0
  fi
  sleep 2
done

echo "Rollback processes started but did not reach readiness; inspect compose logs." >&2
exit 1
