#!/usr/bin/env bash
# Apply tracked PostgreSQL migrations exactly once and record their checksum.
#
# Usage from a checked-out release on the target host:
#   BACKEND_IMAGE=... FRONTEND_IMAGE=... ./scripts/run_migrations.sh
#
# CI may supply DATABASE_URL to apply and replay the same ledger against an
# ephemeral PostgreSQL instance without requiring Docker Compose.
#
# The script intentionally fails on a missing or mismatched ledger entry. Do
# not mark an old schema as applied without first inspecting the database and
# recording that decision in the release notes.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/deploy/docker-compose.yml}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"
MIGRATIONS_USE_COMPOSE="${MIGRATIONS_USE_COMPOSE:-false}"
MIGRATIONS_DIR="${ROOT_DIR}/scripts/migrations"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-rd_alpha}"
VERIFY_ONLY=false

[[ "${MIGRATIONS_USE_COMPOSE}" == "true" || "${MIGRATIONS_USE_COMPOSE}" == "false" ]] || {
  echo "MIGRATIONS_USE_COMPOSE must be true or false." >&2
  exit 2
}

for arg in "$@"; do
  case "${arg}" in
    --verify-only)
      VERIFY_ONLY=true
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${DATABASE_URL:-}" || "${MIGRATIONS_USE_COMPOSE}" == "true" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required when DATABASE_URL is not set" >&2
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
    if [[ -n "${COMPOSE_PROJECT_NAME}" ]]; then
      COMPOSE+=(--project-name "${COMPOSE_PROJECT_NAME}")
    fi
    if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
      COMPOSE+=(--env-file "${COMPOSE_ENV_FILE}")
    fi
    COMPOSE+=(-f "${COMPOSE_FILE}")
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
    if [[ -n "${COMPOSE_PROJECT_NAME}" ]]; then
      COMPOSE+=(-p "${COMPOSE_PROJECT_NAME}")
    fi
    if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
      COMPOSE+=(--env-file "${COMPOSE_ENV_FILE}")
    fi
    COMPOSE+=(-f "${COMPOSE_FILE}")
  else
    echo "docker compose (or docker-compose) is required when DATABASE_URL is not set" >&2
    exit 1
  fi
fi

if [[ ! -d "${MIGRATIONS_DIR}" ]]; then
  echo "Migration directory not found: ${MIGRATIONS_DIR}" >&2
  exit 1
fi

checksum() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

psql_exec() {
  if [[ -n "${DATABASE_URL:-}" && "${MIGRATIONS_USE_COMPOSE}" != "true" ]]; then
    # SQLAlchemy's async dialect URL is valid for the application but not for
    # the PostgreSQL CLI. Keep the caller's environment intact and adapt only
    # the connection string passed to psql.
    local psql_database_url="${DATABASE_URL}"
    if [[ "${psql_database_url}" == postgresql+asyncpg://* ]]; then
      psql_database_url="postgresql://${psql_database_url#postgresql+asyncpg://}"
    fi
    psql "${psql_database_url}" -v ON_ERROR_STOP=1 "$@"
  else
    "${COMPOSE[@]}" exec -T postgres \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" "$@"
  fi
}

sql_literal() {
  # All values passed through this helper are generated locally from the
  # tracked migrations directory. Escaping them still keeps the runner safe if
  # someone later changes a migration filename convention.
  printf "%s" "$1" | sed "s/'/''/g"
}

emit_historical_compatibility_prelude() {
  # 001 and 004 are historical, checksummed files. Current ORM bootstrap
  # schemas can already contain the replacement constraints those files add.
  # Remove only the same-named replacement constraint inside the migration
  # transaction, then run the original bytes unchanged. This preserves the
  # historical checksum while making a fresh current-schema bootstrap converge
  # on exactly the intended constraint definition.
  case "$1" in
    001_add_result_versioning.sql)
      cat <<'SQL'
DO $$
BEGIN
  IF to_regclass('public.rolling_window_results') IS NOT NULL THEN
    ALTER TABLE rolling_window_results
      DROP CONSTRAINT IF EXISTS uq_window_quintile_convention;
  END IF;
  IF to_regclass('public.anova_results') IS NOT NULL THEN
    ALTER TABLE anova_results
      DROP CONSTRAINT IF EXISTS uq_anova_period_convention;
  END IF;
  IF to_regclass('public.factor_premiums') IS NOT NULL THEN
    ALTER TABLE factor_premiums
      DROP CONSTRAINT IF EXISTS uq_factor_year_convention;
  END IF;
END $$;
SQL
      ;;
    004_research_contracts.sql)
      cat <<'SQL'
DO $$
BEGIN
  IF to_regclass('public.ranked_rows') IS NOT NULL THEN
    ALTER TABLE ranked_rows
      DROP CONSTRAINT IF EXISTS fk_ranked_rows_review;
  END IF;
END $$;
SQL
      ;;
  esac
}

shopt -s nullglob
migrations=("${MIGRATIONS_DIR}"/*.sql)
if [[ "${#migrations[@]}" -eq 0 ]]; then
  echo "No migrations found in ${MIGRATIONS_DIR}" >&2
  exit 1
fi

expected_ledger="$(mktemp)"
database_ledger="$(mktemp)"
database_filenames="$(mktemp)"
expected_filenames="$(mktemp)"
cleanup_ledger_files() {
  rm -f "${expected_ledger}" "${database_ledger}" \
    "${database_filenames}" "${expected_filenames}"
}
trap cleanup_ledger_files EXIT

for migration in "${migrations[@]}"; do
  filename="$(basename "${migration}")"
  if [[ ! "${filename}" =~ ^[0-9]{3}_[A-Za-z0-9_]+\.sql$ ]]; then
    echo "Refusing unexpected migration filename: ${filename}" >&2
    exit 1
  fi
  printf '%s\t%s\n' "${filename}" "$(checksum "${migration}")" >> "${expected_ledger}"
done
sort -o "${expected_ledger}" "${expected_ledger}"
cut -f1 "${expected_ledger}" > "${expected_filenames}"

verify_complete_ledger() {
  psql_exec -Atq -F $'\t' \
    -c "SELECT filename, checksum FROM schema_migrations ORDER BY filename;" \
    > "${database_ledger}"
  sort -o "${database_ledger}" "${database_ledger}"
  if ! diff -u "${expected_ledger}" "${database_ledger}"; then
    echo "Database migration ledger does not exactly match the checked-out migrations." >&2
    exit 1
  fi
}

if [[ "${VERIFY_ONLY}" == true ]]; then
  verify_complete_ledger
  echo "Migration ledger exactly matches the checked-out release."
  exit 0
fi

psql_exec -c "
  CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    checksum CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
"

psql_exec -Atq -c "SELECT filename FROM schema_migrations ORDER BY filename;" \
  > "${database_filenames}"
if [[ -n "$(comm -23 "${database_filenames}" "${expected_filenames}")" ]]; then
  echo "Database migration ledger contains migrations absent from this checkout." >&2
  comm -23 "${database_filenames}" "${expected_filenames}" >&2
  exit 1
fi

for migration in "${migrations[@]}"; do
  filename="$(basename "${migration}")"
  current_checksum="$(checksum "${migration}")"
  recorded_checksum="$(
    psql_exec -Atq \
      -c "SELECT checksum FROM schema_migrations WHERE filename = '$(sql_literal "${filename}")';"
  )"

  if [[ -n "${recorded_checksum}" ]]; then
    if [[ "${recorded_checksum}" != "${current_checksum}" ]]; then
      echo "Checksum mismatch for already-applied migration ${filename}." >&2
      echo "Refusing to continue: migrations are immutable once recorded." >&2
      exit 1
    fi
    echo "Migration already recorded: ${filename}"
    continue
  fi

  echo "Applying migration: ${filename}"
  # Apply a file and its ledger entry in one transaction. The table lock plus
  # a transaction-scoped advisory lock serialize concurrent release attempts;
  # the recheck inside the lock turns a race into a clean failure rather than
  # running an already-applied migration twice.
  {
    printf '%s\n' "BEGIN;"
    printf '%s\n' "SET LOCAL lock_timeout = '30s';"
    printf '%s\n' "SET LOCAL statement_timeout = '10min';"
    printf '%s\n' "SELECT pg_advisory_xact_lock(842183001);"
    printf '%s\n' "LOCK TABLE schema_migrations IN EXCLUSIVE MODE;"
    printf '%s\n' "DO \$\$"
    printf '%s\n' "DECLARE recorded TEXT;"
    printf '%s\n' "BEGIN"
    printf '%s\n' "  SELECT checksum INTO recorded FROM schema_migrations WHERE filename = '$(sql_literal "${filename}")';"
    printf '%s\n' "  IF recorded IS NOT NULL THEN"
    printf '%s\n' "    IF recorded = '${current_checksum}' THEN"
    printf '%s\n' "      RAISE EXCEPTION 'migration ${filename} was applied concurrently';"
    printf '%s\n' "    END IF;"
    printf '%s\n' "    RAISE EXCEPTION 'checksum mismatch for migration ${filename}';"
    printf '%s\n' "  END IF;"
    printf '%s\n' "END \$\$;"
    emit_historical_compatibility_prelude "${filename}"
    cat "${migration}"
    printf '%s\n' "INSERT INTO schema_migrations (filename, checksum) VALUES ('$(sql_literal "${filename}")', '${current_checksum}');"
    printf '%s\n' "COMMIT;"
  } | psql_exec
done

verify_complete_ledger
echo "All migrations are recorded and current."
