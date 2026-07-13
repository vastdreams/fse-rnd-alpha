#!/usr/bin/env bash
# Rehearse encrypted off-host backup verification and explicit restore controls.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-offsite-backup-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

fake_bin="${work_dir}/bin"
fake_s3="${work_dir}/s3"
release_root="${work_dir}/release-root"
state_dir="${work_dir}/state"
release_ref="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-42"
release_dir="${release_root}/releases/${release_ref}"
env_file="${work_dir}/prod.env"
restore_marker="${work_dir}/restore-marker"
mkdir -p "${fake_bin}" "${fake_s3}" "${state_dir}" "${release_dir}/deploy"
ln -s "${release_dir}" "${release_root}/current"
touch "${release_dir}/deploy/docker-compose.yml"
cat > "${release_dir}/release.json" <<'JSON'
{
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pipeline_id": 42
}
JSON
cat > "${env_file}" <<'EOF'
POSTGRES_USER=postgres
POSTGRES_DB=rd_alpha
BACKUP_S3_BUCKET=fixture-bucket
BACKUP_S3_PREFIX=investor-backups
BACKUP_KMS_KEY_ID=alias/fixture-backups
BACKUP_RETENTION_DAYS=35
EOF

cat > "${fake_bin}/docker" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "compose" && "${2:-}" == "version" ]]; then
  exit 0
fi
if [[ "${1:-}" == "compose" ]]; then
  if [[ " $* " == *" ps -q postgres "* ]]; then
    printf 'fixture-postgres\n'
    exit 0
  fi
  if [[ " $* " == *" pg_dump "* ]]; then
    printf 'postgres dump fixture\n'
    exit 0
  fi
  if [[ " $* " == *" pg_restore "* ]]; then
    : > "${RESTORE_MARKER:?}"
    exit 0
  fi
  exit 0
fi
if [[ "${1:-}" == "cp" ]]; then
  [[ -f "${2:-}" ]]
  exit 0
fi
exit 2
SH
chmod +x "${fake_bin}/docker"

cat > "${fake_bin}/aws" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

root="${FAKE_S3_ROOT:?}"
arg_value() {
  local expected="$1"
  shift
  while [[ "$#" -gt 0 ]]; do
    if [[ "$1" == "${expected}" ]]; then
      printf '%s' "$2"
      return
    fi
    shift
  done
}
if [[ "${1:-}" == "s3api" ]]; then
  command="$2"
  shift 2
  bucket="$(arg_value --bucket "$@")"
  key="$(arg_value --key "$@")"
  case "${command}" in
    put-object)
      body="$(arg_value --body "$@")"
      if command -v sha256sum >/dev/null 2>&1; then
        version="version-$(printf '%s/%s' "${bucket}" "${key}" | sha256sum | awk '{print substr($1, 1, 12)}')"
      else
        version="version-$(printf '%s/%s' "${bucket}" "${key}" | shasum -a 256 | awk '{print substr($1, 1, 12)}')"
      fi
      mkdir -p "${root}/${bucket}/$(dirname "${key}")" "${root}/versions/${bucket}/${key}"
      cp "${body}" "${root}/${bucket}/${key}"
      cp "${body}" "${root}/versions/${bucket}/${key}/${version}"
      printf '{"VersionId":"%s"}\n' "${version}"
      ;;
    head-object)
      printf '{"ServerSideEncryption":"aws:kms"}\n'
      ;;
    get-object-retention)
      if [[ "${FAKE_BAD_RETENTION:-}" == "true" ]]; then
        printf '{"Retention":{"Mode":"GOVERNANCE","RetainUntilDate":"2030-01-01T00:00:00Z"}}\n'
      else
        printf '{"Retention":{"Mode":"COMPLIANCE","RetainUntilDate":"2030-01-01T00:00:00Z"}}\n'
      fi
      ;;
    get-object)
      version="$(arg_value --version-id "$@")"
      destination=""
      for value in "$@"; do
        if [[ "${value}" != --* && "${value}" != "${bucket}" && "${value}" != "${key}" && "${value}" != "${version}" && "${value}" != "json" ]]; then
          destination="${value}"
        fi
      done
      [[ -n "${destination}" ]]
      cp "${root}/versions/${bucket}/${key}/${version}" "${destination}"
      ;;
    *) exit 2 ;;
  esac
  exit 0
fi
if [[ "${1:-}" == "s3" && "${2:-}" == "cp" ]]; then
  source="$3"
  destination="$4"
  [[ "${source}" == s3://* ]]
  cp "${root}/${source#s3://}" "${destination}"
  exit 0
fi
exit 2
SH
chmod +x "${fake_bin}/aws"

backup_output="$(
  PATH="${fake_bin}:${PATH}" \
  FAKE_S3_ROOT="${fake_s3}" \
  RESTORE_MARKER="${restore_marker}" \
  bash "${ROOT_DIR}/scripts/backup_postgres_offsite.sh" \
    --release-root "${release_root}" \
    --deploy-env-file "${env_file}" \
    --state-dir "${state_dir}"
)"
manifest_uri="$(printf '%s\n' "${backup_output}" | awk -F= '/^BACKUP_MANIFEST_URI=/ {print $2}')"
manifest_sha="$(printf '%s\n' "${backup_output}" | awk -F= '/^BACKUP_MANIFEST_SHA256=/ {print $2}')"
[[ "${manifest_uri}" == s3://fixture-bucket/* ]]
[[ "${manifest_sha}" =~ ^[0-9a-f]{64}$ ]]

PATH="${fake_bin}:${PATH}" \
FAKE_S3_ROOT="${fake_s3}" \
RESTORE_MARKER="${restore_marker}" \
  bash "${ROOT_DIR}/scripts/restore_postgres_offsite.sh" \
    --release-root "${release_root}" \
    --deploy-env-file "${env_file}" \
    --manifest-uri "${manifest_uri}" \
    --expected-manifest-sha256 "${manifest_sha}" \
    --confirm-release-ref "${release_ref}"
[[ ! -e "${restore_marker}" ]]

PATH="${fake_bin}:${PATH}" \
FAKE_S3_ROOT="${fake_s3}" \
RESTORE_MARKER="${restore_marker}" \
  bash "${ROOT_DIR}/scripts/restore_postgres_offsite.sh" \
    --release-root "${release_root}" \
    --deploy-env-file "${env_file}" \
    --manifest-uri "${manifest_uri}" \
    --expected-manifest-sha256 "${manifest_sha}" \
    --confirm-release-ref "${release_ref}" \
    --apply
[[ -e "${restore_marker}" ]]

if PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  bash "${ROOT_DIR}/scripts/restore_postgres_offsite.sh" \
    --release-root "${release_root}" \
    --deploy-env-file "${env_file}" \
    --manifest-uri "${manifest_uri}" \
    --expected-manifest-sha256 "${manifest_sha}" \
    --confirm-release-ref "wrong-release"; then
  echo "Restore unexpectedly accepted the wrong active release confirmation." >&2
  exit 1
fi

if PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" FAKE_BAD_RETENTION=true \
  bash "${ROOT_DIR}/scripts/restore_postgres_offsite.sh" \
    --release-root "${release_root}" \
    --deploy-env-file "${env_file}" \
    --manifest-uri "${manifest_uri}" \
    --expected-manifest-sha256 "${manifest_sha}" \
    --confirm-release-ref "${release_ref}"; then
  echo "Restore unexpectedly accepted an object without Compliance retention." >&2
  exit 1
fi

echo "Off-host encrypted backup and restore rehearsal passed."
