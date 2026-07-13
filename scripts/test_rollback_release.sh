#!/usr/bin/env bash
# Validate rollback-record integrity and the full apply orchestration with
# disposable Git/data fixtures and a deterministic Compose/HTTP harness.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-rollback-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

data_dir="${work_dir}/rd-alpha-data"
database_backup="${work_dir}/postgres.dump"
data_backup="${work_dir}/data.tar.gz"
record="${work_dir}/rollback.env"
mkdir -p "${data_dir}"
printf 'database fixture\n' > "${database_backup}"
printf 'release data fixture\n' > "${data_dir}/fixture.txt"
tar -C "${work_dir}" -czf "${data_backup}" "$(basename "${data_dir}")"

checksum() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

printf '%s  %s\n' "$(checksum "${database_backup}")" "${database_backup}" > "${database_backup}.sha256"
printf '%s  %s\n' "$(checksum "${data_backup}")" "${data_backup}" > "${data_backup}.sha256"
{
  printf 'BACKEND_IMAGE=%q\n' "ghcr.io/example/backend@sha256:$(printf 'a%.0s' {1..64})"
  printf 'FRONTEND_IMAGE=%q\n' "ghcr.io/example/frontend@sha256:$(printf 'b%.0s' {1..64})"
  printf 'RELEASE_SHA=%q\n' "$(printf 'c%.0s' {1..40})"
  printf 'FAILED_RELEASE_SHA=%q\n' "$(printf 'd%.0s' {1..40})"
  printf 'DATABASE_BACKUP=%q\n' "${database_backup}"
  printf 'DATA_BACKUP=%q\n' "${data_backup}"
  printf 'DATA_BACKUP_SOURCE=%q\n' "${data_dir}"
  printf 'DATA_DIR=%q\n' "${data_dir}"
  printf 'DATA_RELEASE_URI=%q\n' "s3://fixture/release"
} > "${record}"

"${ROOT_DIR}/scripts/rollback_release.sh" --record "${record}" --dry-run

printf 'tampered\n' >> "${database_backup}"
if "${ROOT_DIR}/scripts/rollback_release.sh" --record "${record}" --dry-run; then
  echo "Rollback dry-run unexpectedly accepted a tampered database backup." >&2
  exit 1
fi

apply_root="${work_dir}/apply-root"
apply_data="${work_dir}/restored-data"
apply_database_backup="${work_dir}/apply-postgres.dump"
apply_data_backup="${work_dir}/apply-data.tar.gz"
apply_record="${work_dir}/apply-rollback.env"
fake_bin="${work_dir}/fake-bin"
fake_log="${work_dir}/rollback-apply.log"
mkdir -p "${apply_root}/scripts" "${apply_root}/deploy" "${apply_data}" "${fake_bin}"
cp "${ROOT_DIR}/scripts/rollback_release.sh" "${apply_root}/scripts/"
cat > "${apply_root}/scripts/run_migrations.sh" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${1:-}" == "--verify-only" ]]
printf 'migration-ledger-verify %s\n' "$*" >> "${ROLLBACK_FAKE_LOG}"
SH
chmod +x "${apply_root}/scripts/run_migrations.sh"
printf 'POSTGRES_USER=postgres\nPOSTGRES_DB=rd_alpha\n' > "${apply_root}/deploy/.env"
printf 'restored database fixture\n' > "${apply_database_backup}"
printf 'previous release data\n' > "${apply_data}/fixture.txt"
tar -C "${work_dir}" -czf "${apply_data_backup}" "$(basename "${apply_data}")"
printf 'failed release data\n' > "${apply_data}/fixture.txt"

git -C "${apply_root}" init -q
printf 'deploy/.env\n' > "${apply_root}/.gitignore"
git -C "${apply_root}" add .
GIT_AUTHOR_NAME=rollback-test GIT_AUTHOR_EMAIL=rollback-test@example.com \
GIT_COMMITTER_NAME=rollback-test GIT_COMMITTER_EMAIL=rollback-test@example.com \
  git -C "${apply_root}" commit --no-gpg-sign -qm "rollback fixture"
apply_sha="$(git -C "${apply_root}" rev-parse HEAD)"

printf '%s  %s\n' "$(checksum "${apply_database_backup}")" "${apply_database_backup}" \
  > "${apply_database_backup}.sha256"
printf '%s  %s\n' "$(checksum "${apply_data_backup}")" "${apply_data_backup}" \
  > "${apply_data_backup}.sha256"
{
  printf 'BACKEND_IMAGE=%q\n' "ghcr.io/example/backend@sha256:$(printf 'e%.0s' {1..64})"
  printf 'FRONTEND_IMAGE=%q\n' "ghcr.io/example/frontend@sha256:$(printf 'f%.0s' {1..64})"
  printf 'RELEASE_SHA=%q\n' "${apply_sha}"
  printf 'FAILED_RELEASE_SHA=%q\n' "$(printf 'd%.0s' {1..40})"
  printf 'DATABASE_BACKUP=%q\n' "${apply_database_backup}"
  printf 'DATA_BACKUP=%q\n' "${apply_data_backup}"
  printf 'DATA_BACKUP_SOURCE=%q\n' "${apply_data}"
  printf 'DATA_DIR=%q\n' "${apply_data}"
  printf 'DATA_RELEASE_URI=%q\n' "s3://fixture/release"
} > "${apply_record}"

cat > "${fake_bin}/docker" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${ROLLBACK_FAKE_LOG}"
case "${1:-}" in
  compose)
    shift
    case "${1:-}" in
      version|config|up|stop|pull|exec) exit 0 ;;
      ps) printf 'fake-postgres\n'; exit 0 ;;
    esac
    ;;
  cp) exit 0 ;;
esac
exit 0
SH
cat > "${fake_bin}/curl" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
url=""
for argument in "$@"; do
  url="${argument}"
done
if [[ "${url}" == */ready ]]; then
  printf '{"ready":true}\n'
fi
SH
chmod +x "${fake_bin}/docker" "${fake_bin}/curl"

# Host-local configuration must not be able to replace digest-pinned rollback
# images from the verified record.
printf 'POSTGRES_USER=postgres\nPOSTGRES_DB=rd_alpha\nBACKEND_IMAGE=mutable:latest\n' \
  > "${apply_root}/deploy/.env"
if PATH="${fake_bin}:${PATH}" ROLLBACK_FAKE_LOG="${fake_log}" \
  "${apply_root}/scripts/rollback_release.sh" --record "${apply_record}" --apply; then
  echo "Rollback unexpectedly accepted a host-local image override." >&2
  exit 1
fi
printf 'POSTGRES_USER=postgres\nPOSTGRES_DB=rd_alpha\n' > "${apply_root}/deploy/.env"

PATH="${fake_bin}:${PATH}" ROLLBACK_FAKE_LOG="${fake_log}" \
  "${apply_root}/scripts/rollback_release.sh" --record "${apply_record}" --apply

test "$(git -C "${apply_root}" rev-parse HEAD)" = "${apply_sha}"
test "$(cat "${apply_data}/fixture.txt")" = "previous release data"
compgen -G "${apply_data}.failed-*/fixture.txt" >/dev/null
rg -q 'exec -T postgres pg_restore .*--exit-on-error' "${fake_log}"
rg -q 'DROP DATABASE IF EXISTS "rd_alpha"' "${fake_log}"
rg -q 'migration-ledger-verify --verify-only' "${fake_log}"
rg -q 'pull' "${fake_log}"
rg -q 'up -d --force-recreate --remove-orphans backend worker beat frontend' "${fake_log}"

echo "Rollback apply rehearsal passed."
