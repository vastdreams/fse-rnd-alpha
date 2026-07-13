#!/usr/bin/env bash
# Deploy an already-built immutable release on the target host.
#
# The caller must check out the matching source SHA first, then supply:
#   BACKEND_IMAGE=ghcr.io/...@sha256:...
#   FRONTEND_IMAGE=ghcr.io/...@sha256:...

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-${ROOT_DIR}/deploy}"
# Keep backups outside the Git checkout so they cannot make the next deploy
# look dirty or be removed by a source checkout cleanup.
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/../rd-alpha-backups}"
# Production data is intentionally outside the source checkout. A first
# migration from a legacy ../data mount is backed up below before restore.
DATA_DIR="${DATA_DIR:-${ROOT_DIR}/../rd-alpha-data}"
RELEASE_TIMESTAMP="${RELEASE_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
COMPOSE_NETWORK_NAME="${COMPOSE_NETWORK_NAME:-rd_alpha_network}"

: "${BACKEND_IMAGE:?BACKEND_IMAGE must be set to a pinned backend image}"
: "${FRONTEND_IMAGE:?FRONTEND_IMAGE must be set to a pinned frontend image}"
approved_backend_image="${BACKEND_IMAGE}"
approved_frontend_image="${FRONTEND_IMAGE}"
approved_release_sha="${RELEASE_SHA:-}"
approved_previous_release_sha="${PREVIOUS_RELEASE_SHA:-}"
approved_expected_manifest_sha="${EXPECTED_DATA_MANIFEST_SHA256:-}"
approved_expected_release_uri="${EXPECTED_DATA_RELEASE_URI:-}"
approved_expected_descriptor_sha="${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256:-}"
approved_expected_public_hostname="${EXPECTED_PUBLIC_HOSTNAME:-}"
[[ "${BACKEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "BACKEND_IMAGE must end in a SHA-256 image digest." >&2
  exit 2
}
[[ "${FRONTEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "FRONTEND_IMAGE must end in a SHA-256 image digest." >&2
  exit 2
}

if [[ ! -f "${DEPLOY_DIR}/.env" ]]; then
  echo "Missing ${DEPLOY_DIR}/.env; copy .env.example and populate production secrets." >&2
  exit 1
fi

# Compose reads .env itself, but this shell also needs the data-release URI and
# backup database variables. Parse KEY=VALUE without evaluating the contents.
while IFS= read -r line || [[ -n "${line}" ]]; do
  case "${line}" in
    ''|\#*) continue ;;
  esac
  [[ "${line}" == *"="* ]] || continue
  key="${line%%=*}"
  value="${line#*=}"
  case "${key}" in
    BACKEND_IMAGE|FRONTEND_IMAGE|RELEASE_SHA|PREVIOUS_RELEASE_SHA|\
    EXPECTED_DATA_MANIFEST_SHA256|EXPECTED_DATA_RELEASE_URI|\
    EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256|EXPECTED_PUBLIC_HOSTNAME)
      echo "Reserved deployment input must not be set in ${DEPLOY_DIR}/.env: ${key}" >&2
      exit 1
      ;;
  esac
  value="${value%\"}"
  value="${value#\"}"
  export "${key}=${value}"
done < "${DEPLOY_DIR}/.env"

# The dispatch workflow supplies these values after resolving a successful CI
# artifact. Never let host-local configuration replace that reviewed binding.
BACKEND_IMAGE="${approved_backend_image}"
FRONTEND_IMAGE="${approved_frontend_image}"
RELEASE_SHA="${approved_release_sha}"
PREVIOUS_RELEASE_SHA="${approved_previous_release_sha}"
EXPECTED_DATA_MANIFEST_SHA256="${approved_expected_manifest_sha}"
EXPECTED_DATA_RELEASE_URI="${approved_expected_release_uri}"
EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="${approved_expected_descriptor_sha}"
EXPECTED_PUBLIC_HOSTNAME="${approved_expected_public_hostname}"
export BACKEND_IMAGE FRONTEND_IMAGE RELEASE_SHA PREVIOUS_RELEASE_SHA
export EXPECTED_DATA_MANIFEST_SHA256 EXPECTED_DATA_RELEASE_URI
export EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256 EXPECTED_PUBLIC_HOSTNAME

: "${DATA_RELEASE_URI:?DATA_RELEASE_URI must identify a staged immutable data release}"
: "${BACKEND_DATABASE_URL:?BACKEND_DATABASE_URL must contain the internal database DSN}"
[[ "${BACKEND_DATABASE_URL}" == postgresql+asyncpg://* ]] || {
  echo "BACKEND_DATABASE_URL must be a postgresql+asyncpg URL." >&2
  exit 1
}
if [[ -n "${EXPECTED_PUBLIC_HOSTNAME}" ]]; then
  [[ "${PUBLIC_HOSTNAME:-}" == "${EXPECTED_PUBLIC_HOSTNAME}" ]] || {
    echo "Target deploy/.env PUBLIC_HOSTNAME does not match the approved public URL host." >&2
    exit 1
  }
fi
for seed_name in AUTH_SEED AUTH_SECONDARY_SEED; do
  seed_email_var="${seed_name}_EMAIL"
  seed_password_var="${seed_name}_PASSWORD"
  seed_email="${!seed_email_var:-}"
  seed_password="${!seed_password_var:-}"
  if [[ -n "${seed_email}" || -n "${seed_password}" ]]; then
    [[ -n "${seed_email}" && -n "${seed_password}" ]] || {
      echo "${seed_email_var} and ${seed_password_var} must be set together." >&2
      exit 1
    }
  fi
done
if [[ -n "${AUTH_SEED_EMAIL:-}" &&
  "${AUTH_SEED_EMAIL}" == "${AUTH_SECONDARY_SEED_EMAIL:-}" ]]; then
  echo "AUTH_SEED_EMAIL and AUTH_SECONDARY_SEED_EMAIL must differ." >&2
  exit 1
fi
if [[ -n "${EXPECTED_DATA_MANIFEST_SHA256:-}" ]]; then
  actual_manifest_sha="${DATA_RELEASE_URI%/}"
  actual_manifest_sha="${actual_manifest_sha##*/}"
  if [[ "${actual_manifest_sha}" != "${EXPECTED_DATA_MANIFEST_SHA256}" ]]; then
    echo "Target deploy/.env DATA_RELEASE_URI does not match the approved data manifest." >&2
    exit 1
  fi
fi
if [[ -n "${EXPECTED_DATA_RELEASE_URI:-}" && "${DATA_RELEASE_URI}" != "${EXPECTED_DATA_RELEASE_URI}" ]]; then
  echo "Target deploy/.env DATA_RELEASE_URI does not match the approved release artifact." >&2
  exit 1
fi
if [[ -z "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256:-}" ]]; then
  EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="${DATA_RELEASE_DESCRIPTOR_SHA256:-}"
fi
[[ "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] || {
  echo "An approved DATA_RELEASE_DESCRIPTOR_SHA256 is required for deployment." >&2
  exit 1
}
export DATA_DIR

if git -C "${ROOT_DIR}" rev-parse HEAD >/dev/null 2>&1; then
  if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
    echo "Refusing to deploy from a dirty source checkout." >&2
    exit 1
  fi
  RELEASE_SHA="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
elif [[ -z "${RELEASE_SHA:-}" ]]; then
  echo "RELEASE_SHA is required when the deployment directory is not a Git checkout" >&2
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

cd "${DEPLOY_DIR}"
"${COMPOSE[@]}" config -q

sql_literal() {
  printf '%s' "$1" | sed "s/'/''/g"
}

backend_healthy() {
  "${COMPOSE[@]}" exec -T backend curl -fsS http://localhost:8000/health >/dev/null
}

postgres_healthy() {
  "${COMPOSE[@]}" exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" >/dev/null
}

bootstrap_schema() {
  # The historical migration ledger starts by altering research tables that
  # predate it. A blank host must therefore create the current ORM base schema
  # before the ledger runs; this is the same explicit order exercised in CI.
  "${COMPOSE[@]}" run --rm --no-deps backend \
    python -c "import asyncio; from app.db.session import create_tables; asyncio.run(create_tables())"
}

release_metadata_values() {
  python3 - "${DATA_DIR}/release_metadata.json" <<'PY'
import json
import sys

metadata = json.load(open(sys.argv[1]))
required = (
    "universe_version",
    "source_sha",
    "manifest_sha256",
    "database_snapshot_sha256",
    "research_records_sha256",
)
values = []
for name in required:
    value = metadata.get(name)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Release metadata is missing {name}")
    values.append(value)
print("\t".join(values))
PY
}

verify_release_database_binding() {
  local universe_version source_sha manifest_sha snapshot_sha records_sha database_binding
  IFS=$'\t' read -r universe_version source_sha manifest_sha snapshot_sha records_sha <<< "$(release_metadata_values)"
  [[ "${source_sha}" == "${RELEASE_SHA}" ]] || {
    echo "Restored data was staged from ${source_sha}, not deployed source ${RELEASE_SHA}." >&2
    return 1
  }

  database_binding="$(
    "${COMPOSE[@]}" exec -T postgres \
      psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" \
        -X -A -t -v ON_ERROR_STOP=1 -F $'\t' \
        -c "
          SELECT status, COALESCE(source_sha, ''), COALESCE(data_manifest_sha256, '')
            FROM universe_builds
           WHERE universe_version = '$(sql_literal "${universe_version}")';
        "
  )"
  local database_status database_source_sha database_manifest_sha
  IFS=$'\t' read -r database_status database_source_sha database_manifest_sha <<< "${database_binding}"
  [[ "${database_status:-}" == "sealed" ]] || {
    echo "Release universe ${universe_version} is not sealed on the target database." >&2
    return 1
  }
  [[ "${database_source_sha:-}" == "${source_sha}" ]] || {
    echo "Target database source SHA does not match staged data metadata." >&2
    return 1
  }
  [[ "${database_manifest_sha:-}" == "${manifest_sha}" ]] || {
    echo "Target database data-manifest binding does not match restored data." >&2
    return 1
  }
  [[ "${snapshot_sha}" =~ ^[0-9a-f]{64}$ ]] || {
    echo "Staged research snapshot checksum is malformed." >&2
    return 1
  }
  [[ "${records_sha}" =~ ^[0-9a-f]{64}$ ]] || {
    echo "Staged research-record checksum is malformed." >&2
    return 1
  }
  local computed_snapshot_sha
  computed_snapshot_sha="$(
    docker run --rm \
      --network "${COMPOSE_NETWORK_NAME}" \
      -e "DATABASE_URL=${BACKEND_DATABASE_URL}" \
      -v "${ROOT_DIR}/scripts:/release-scripts:ro" \
      "${BACKEND_IMAGE}" \
      python /release-scripts/research_snapshot.py \
        --universe-version "${universe_version}" |
      python3 -c 'import json,sys; print(json.load(sys.stdin)["snapshot_sha256"])'
  )"
  [[ "${computed_snapshot_sha}" == "${snapshot_sha}" ]] || {
    echo "Target database research snapshot does not match the staged artifact." >&2
    return 1
  }
  echo "Verified sealed database build ${universe_version} matches the restored artifact."
}

import_release_research_records() {
  local universe_version source_sha manifest_sha snapshot_sha records_sha actual_records_sha
  IFS=$'\t' read -r universe_version source_sha manifest_sha snapshot_sha records_sha \
    <<< "$(release_metadata_values)"
  [[ -f "${DATA_DIR}/research_records.json" ]] || {
    echo "Restored data artifact has no research_records.json." >&2
    return 1
  }
  actual_records_sha="$(
    python3 - "${DATA_DIR}/research_records.json" <<'PY'
import hashlib
import json
import sys

document = json.load(open(sys.argv[1]))
document.pop("payload_sha256", None)
print(hashlib.sha256(
    json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
).hexdigest())
PY
  )"
  [[ "${actual_records_sha}" == "${records_sha}" ]] || {
    echo "Restored research records do not match their release checksum." >&2
    return 1
  }
  docker run --rm \
    --network "${COMPOSE_NETWORK_NAME}" \
    -e "DATABASE_URL=${BACKEND_DATABASE_URL}" \
    -v "${ROOT_DIR}/scripts:/release-scripts:ro" \
    -v "${DATA_DIR}:/release-data:ro" \
    "${BACKEND_IMAGE}" \
    python /release-scripts/research_release.py import \
      --input /release-data/research_records.json \
      --expected-source-sha "${RELEASE_SHA}" \
      --expected-data-manifest-sha256 "${manifest_sha}"
}

backup_release_state() {
  local database_backup rollback_record data_backup postgres_container backend_container frontend_container
  local prior_record prior_release_sha prior_data_uri
  # Database dumps and data archives contain user-owned research. Keep both
  # the directory and newly-created files private to the deployment account.
  umask 077
  mkdir -p "${BACKUP_DIR}"
  chmod 0700 "${BACKUP_DIR}"
  database_backup="${BACKUP_DIR}/postgres-${RELEASE_TIMESTAMP}.dump"
  rollback_record="${BACKUP_DIR}/rollback-${RELEASE_TIMESTAMP}.env"
  prior_record="$(ls -t "${BACKUP_DIR}"/release-*.json 2>/dev/null | awk 'NR==1' || true)"
  prior_release_sha="${PREVIOUS_RELEASE_SHA:-}"
  prior_data_uri="${PREVIOUS_DATA_RELEASE_URI:-}"
  if [[ -n "${prior_record}" ]]; then
    if [[ -z "${prior_release_sha}" ]]; then
      prior_release_sha="$(
        python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("release_sha", ""))' \
          "${prior_record}"
      )"
    fi
    if [[ -z "${prior_data_uri}" ]]; then
      prior_data_uri="$(
        python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("data_release_uri", ""))' \
          "${prior_record}"
      )"
    fi
  fi

  # Capture the currently running immutable image references before replacing
  # them, plus the prior source/data record needed for a true rollback. Empty
  # values are valid on a first install.
  backend_container="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  frontend_container="$("${COMPOSE[@]}" ps -q frontend 2>/dev/null || true)"
  {
    printf 'BACKEND_IMAGE=%q\n' "$(
      [[ -n "${backend_container}" ]] &&
        docker inspect --format '{{.Config.Image}}' "${backend_container}" 2>/dev/null || true
    )"
    printf 'FRONTEND_IMAGE=%q\n' "$(
      [[ -n "${frontend_container}" ]] &&
        docker inspect --format '{{.Config.Image}}' "${frontend_container}" 2>/dev/null || true
    )"
    printf 'RELEASE_SHA=%q\n' "${prior_release_sha}"
    printf 'FAILED_RELEASE_SHA=%q\n' "${RELEASE_SHA}"
    printf 'DATABASE_BACKUP=%q\n' "${database_backup}"
    printf 'DATA_RELEASE_URI=%q\n' "${prior_data_uri}"
    printf 'DATA_DIR=%q\n' "${DATA_DIR}"
  } > "${rollback_record}"

  "${COMPOSE[@]}" exec -T postgres pg_dump -U "${POSTGRES_USER:-postgres}" -Fc "${POSTGRES_DB:-rd_alpha}" > "${database_backup}"
  test -s "${database_backup}"
  (sha256sum "${database_backup}" 2>/dev/null || shasum -a 256 "${database_backup}") > "${database_backup}.sha256"
  postgres_container="$("${COMPOSE[@]}" ps -q postgres)"
  test -n "${postgres_container}"
  docker cp "${database_backup}" "${postgres_container}:/tmp/release-backup.dump"
  "${COMPOSE[@]}" exec -T postgres pg_restore --list /tmp/release-backup.dump >/dev/null
  "${COMPOSE[@]}" exec -T postgres rm -f /tmp/release-backup.dump

  local data_source="${DATA_DIR}"
  if [[ ! -d "${data_source}" && -d "${ROOT_DIR}/data" ]]; then
    data_source="${ROOT_DIR}/data"
  fi
  if [[ -d "${data_source}" ]]; then
    data_backup="${BACKUP_DIR}/data-${RELEASE_TIMESTAMP}.tar.gz"
    tar -C "$(dirname "${data_source}")" -czf "${data_backup}" "$(basename "${data_source}")"
    test -s "${data_backup}"
    tar -tzf "${data_backup}" >/dev/null
    (sha256sum "${data_backup}" 2>/dev/null || shasum -a 256 "${data_backup}") > "${data_backup}.sha256"
    printf 'DATA_BACKUP=%q\n' "${data_backup}" >> "${rollback_record}"
    printf 'DATA_BACKUP_SOURCE=%q\n' "${data_source}" >> "${rollback_record}"
  fi

  echo "Recorded rollback artifact: ${rollback_record}"
}

record_release() {
  local manifest_sha migration_ledger release_record universe_version database_snapshot_sha research_records_sha
  local data_descriptor_sha
  local metadata_source_sha metadata_manifest_sha
  manifest_sha="$(
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["manifest_sha256"])' \
      "${DATA_DIR}/release_manifest.json"
  )"
  IFS=$'\t' read -r universe_version metadata_source_sha metadata_manifest_sha database_snapshot_sha research_records_sha \
    <<< "$(release_metadata_values)"
  data_descriptor_sha="$(
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum "${DATA_DIR}/release_metadata.json" | awk '{print $1}'
    else
      shasum -a 256 "${DATA_DIR}/release_metadata.json" | awk '{print $1}'
    fi
  )"
  migration_ledger="$(
    "${COMPOSE[@]}" exec -T postgres \
      psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-rd_alpha}" -At \
      -c "SELECT COALESCE(json_agg(json_build_object('filename', filename, 'checksum', checksum) ORDER BY filename)::text, '[]') FROM schema_migrations;"
  )"
  release_record="${BACKUP_DIR}/release-${RELEASE_TIMESTAMP}.json"
  RELEASE_RECORD_SHA="${RELEASE_SHA}" \
  RELEASE_RECORD_BACKEND="${BACKEND_IMAGE}" \
  RELEASE_RECORD_FRONTEND="${FRONTEND_IMAGE}" \
  RELEASE_RECORD_DATA_URI="${DATA_RELEASE_URI}" \
  RELEASE_RECORD_DATA_MANIFEST="${manifest_sha}" \
  RELEASE_RECORD_UNIVERSE_VERSION="${universe_version}" \
  RELEASE_RECORD_DATABASE_SNAPSHOT="${database_snapshot_sha}" \
  RELEASE_RECORD_RESEARCH_RECORDS="${research_records_sha}" \
  RELEASE_RECORD_DATA_DESCRIPTOR="${data_descriptor_sha}" \
  RELEASE_RECORD_MIGRATIONS="${migration_ledger}" \
  RELEASE_RECORD_AT="${RELEASE_TIMESTAMP}" \
  python3 - <<'PY' > "${release_record}"
import json
import os

print(json.dumps(
    {
        "released_at": os.environ["RELEASE_RECORD_AT"],
        "release_sha": os.environ["RELEASE_RECORD_SHA"],
        "backend_image": os.environ["RELEASE_RECORD_BACKEND"],
        "frontend_image": os.environ["RELEASE_RECORD_FRONTEND"],
        "data_release_uri": os.environ["RELEASE_RECORD_DATA_URI"],
        "data_manifest_sha256": os.environ["RELEASE_RECORD_DATA_MANIFEST"],
        "universe_version": os.environ["RELEASE_RECORD_UNIVERSE_VERSION"],
        "database_snapshot_sha256": os.environ["RELEASE_RECORD_DATABASE_SNAPSHOT"],
        "research_records_sha256": os.environ["RELEASE_RECORD_RESEARCH_RECORDS"],
        "data_release_descriptor_sha256": os.environ["RELEASE_RECORD_DATA_DESCRIPTOR"],
        "migration_ledger": json.loads(os.environ["RELEASE_RECORD_MIGRATIONS"]),
    },
    indent=2,
    sort_keys=True,
))
PY
  echo "Recorded deployed release: ${release_record}"
}

"${COMPOSE[@]}" up -d postgres redis
for _ in $(seq 1 30); do
  if postgres_healthy; then
    break
  fi
  sleep 2
done
postgres_healthy

# Quiesce all writers before capturing the database/data rollback state. This
# also prevents the old frontend from proxying to a new backend before its
# migrations have been applied.
"${COMPOSE[@]}" stop backend worker beat frontend >/dev/null 2>&1 || true

# A backup and rollback record are mandatory before changing either the
# database or the mounted research-data tree.
backup_release_state

# Restore the verified release artifact while application processes are stopped.
DATA_DIR="${DATA_DIR}" DATA_RELEASE_URI="${DATA_RELEASE_URI}" \
  EXPECTED_SOURCE_SHA="${RELEASE_SHA}" \
  EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"

"${COMPOSE[@]}" pull
bootstrap_schema
env -u DATABASE_URL \
  MIGRATIONS_USE_COMPOSE=true \
  COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml" \
  "${ROOT_DIR}/scripts/run_migrations.sh"
import_release_research_records
verify_release_database_binding

# Restart the app after migrations so account bootstrap runs against the newly
# created durable account table rather than falling back to image-local state.
"${COMPOSE[@]}" up -d --force-recreate --remove-orphans backend worker beat frontend

for _ in $(seq 1 30); do
  ready_json="$(curl -fsS http://localhost/ready || true)"
  if curl -fsS http://localhost/health >/dev/null \
    && grep -q '"ready":true' <<< "${ready_json}" \
    && curl -fsS http://localhost/ >/dev/null; then
    record_release
    echo "Release is healthy and ready."
    exit 0
  fi
  sleep 2
done

echo "Release did not reach readiness; inspect compose logs before rollback." >&2
exit 1
