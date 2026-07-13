#!/usr/bin/env bash
# Exercise the server-side GitLab package pull and atomic release selection
# without Docker, a network connection, or production credentials.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-release-agent-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

source_sha="$(printf 'a%.0s' {1..40})"
pipeline_id="4242"
release_version="${source_sha}-${pipeline_id}"
package_dir="${work_dir}/package"
payload_dir="${work_dir}/payload"
release_root="${work_dir}/release-root"
state_dir="${work_dir}/state"
agent_env="${work_dir}/release-agent.env"
deploy_env="${work_dir}/prod.env"
fake_bin="${work_dir}/fake-bin"
agent_log="${work_dir}/deploy.log"

mkdir -p "${package_dir}" "${payload_dir}/deploy" "${payload_dir}/scripts" "${fake_bin}"
printf 'services: {}\n' > "${payload_dir}/deploy/docker-compose.yml"
cat > "${payload_dir}/scripts/deploy_release.sh" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${RELEASE_SHA}" =~ ^a{40}$ ]]
[[ "${RELEASE_REF}" == "${RELEASE_SHA}-4242" ]]
[[ -f "${DEPLOY_ENV_FILE}" ]]
[[ -d "${BACKUP_DIR}" ]]
printf '%s\t%s\t%s\n' "${RELEASE_SHA}" "${BACKEND_IMAGE}" "${FRONTEND_IMAGE}" >> "${AGENT_TEST_LOG}"
SH
chmod +x "${payload_dir}/scripts/deploy_release.sh"
printf '#!/usr/bin/env bash\n# health fixture\n' > "${payload_dir}/scripts/check_release_health.sh"
chmod +x "${payload_dir}/scripts/check_release_health.sh"
printf '# create data manifest fixture\n' > "${payload_dir}/scripts/create_data_manifest.py"
printf '# verify data manifest fixture\n' > "${payload_dir}/scripts/verify_data_manifest.py"
printf '# research coverage fixture\n' > "${payload_dir}/scripts/research_coverage_report.py"
printf '#!/usr/bin/env bash\n# backup fixture\n' > "${payload_dir}/scripts/backup_postgres_offsite.sh"
printf '#!/usr/bin/env bash\n# restore fixture\n' > "${payload_dir}/scripts/restore_postgres_offsite.sh"
chmod +x "${payload_dir}/scripts/backup_postgres_offsite.sh" "${payload_dir}/scripts/restore_postgres_offsite.sh"
printf '# smoke fixture\n' > "${payload_dir}/scripts/smoke_public_release.py"
printf '#!/usr/bin/env bash\n# smoke fixture\n' > "${payload_dir}/scripts/run_authenticated_release_smoke.sh"
chmod +x "${payload_dir}/scripts/run_authenticated_release_smoke.sh"

tar -C "${payload_dir}" -czf "${package_dir}/release-bundle.tar.gz" deploy scripts
bundle_sha="$(
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${package_dir}/release-bundle.tar.gz" | awk '{print $1}'
  else
    shasum -a 256 "${package_dir}/release-bundle.tar.gz" | awk '{print $1}'
  fi
)"
SOURCE_SHA="${source_sha}" PIPELINE_ID="${pipeline_id}" BUNDLE_SHA="${bundle_sha}" python3 - <<'PY' \
  > "${package_dir}/release.json"
import json
import os

print(
    json.dumps(
        {
            "schema_version": 1,
            "source_sha": os.environ["SOURCE_SHA"],
            "pipeline_id": int(os.environ["PIPELINE_ID"]),
            "backend_image": "registry.example/backend@sha256:" + "b" * 64,
            "frontend_image": "registry.example/frontend@sha256:" + "c" * 64,
            "bundle_filename": "release-bundle.tar.gz",
            "bundle_sha256": os.environ["BUNDLE_SHA"],
            "migration_ledger_sha256": "d" * 64,
            "created_at": "2026-07-14T00:00:00Z",
        },
        sort_keys=True,
    )
)
PY

cat > "${fake_bin}/curl" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

output=""
url=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --output)
      output="$2"
      shift 2
      ;;
    *)
      url="$1"
      shift
      ;;
  esac
done
case "${url}" in
  */release.json) cp "${FAKE_PACKAGE_DIR}/release.json" "${output}" ;;
  */release-bundle.tar.gz) cp "${FAKE_PACKAGE_DIR}/release-bundle.tar.gz" "${output}" ;;
  */staging-proof.json) cp "${FAKE_PACKAGE_DIR}/staging-proof.json" "${output}" ;;
  *)
    echo "Unexpected release-agent curl URL: ${url}" >&2
    exit 2
    ;;
esac
SH
chmod +x "${fake_bin}/curl"
cat > "${fake_bin}/flock" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "${fake_bin}/flock"

printf 'POSTGRES_USER=postgres\nPOSTGRES_DB=rd_alpha\nDATA_RELEASE_URI=s3://fixture-bucket/investor-platform-data/univ/%s\n' \
  "$(printf 'd%.0s' {1..64})" > "${deploy_env}"
cat > "${agent_env}" <<EOF
RELEASE_BASE_URL=https://gitlab.example/api/v4/projects/123/packages/generic/investor-platform
RELEASE_TOKEN=fixture-token
RELEASE_AUTH_HEADER=PRIVATE-TOKEN
RELEASE_ROOT=${release_root}
STATE_DIR=${state_dir}
DEPLOY_ENV_FILE=${deploy_env}
BACKUP_DIR=${state_dir}/backups
EOF

PATH="${fake_bin}:${PATH}" \
FAKE_PACKAGE_DIR="${package_dir}" \
AGENT_TEST_LOG="${agent_log}" \
RD_ALPHA_RELEASE_AGENT_ENV="${agent_env}" \
  bash "${ROOT_DIR}/deploy/rd-alpha-release-agent.sh" "${release_version}"

test "$(readlink -f "${release_root}/current")" = "$(cd "${release_root}/releases/${release_version}" && pwd -P)"
test "$(wc -l < "${agent_log}")" -eq 1
python3 - "${state_dir}/release-records/${release_version}.json" "${source_sha}" <<'PY'
import json
import sys

record = json.load(open(sys.argv[1]))
assert record["source_sha"] == sys.argv[2]
assert record["release_version"] == sys.argv[2] + "-4242"
assert record["bundle_sha256"].isalnum()
PY

# The same version is idempotent only when the retained bundle checksum agrees.
PATH="${fake_bin}:${PATH}" \
FAKE_PACKAGE_DIR="${package_dir}" \
AGENT_TEST_LOG="${agent_log}" \
RD_ALPHA_RELEASE_AGENT_ENV="${agent_env}" \
  bash "${ROOT_DIR}/deploy/rd-alpha-release-agent.sh" "${release_version}"
test "$(wc -l < "${agent_log}")" -eq 2

SOURCE_SHA="${source_sha}" RELEASE_VERSION="${release_version}" PIPELINE_ID="${pipeline_id}" \
DATA_MANIFEST_SHA="$(printf 'd%.0s' {1..64})" python3 - <<'PY' \
  > "${package_dir}/staging-proof.json"
import json
import os

print(
    json.dumps(
        {
            "schema_version": 1,
            "status": "passed",
            "release_version": os.environ["RELEASE_VERSION"],
            "source_sha": os.environ["SOURCE_SHA"],
            "pipeline_id": int(os.environ["PIPELINE_ID"]),
            "data_manifest_sha256": os.environ["DATA_MANIFEST_SHA"],
            "staging_api_smoke_job_id": 101,
            "staging_browser_smoke_job_id": 102,
        }
    )
)
PY
cat >> "${agent_env}" <<'EOF'
REQUIRE_STAGING_PROOF=true
STAGING_PROOF_BASE_URL=https://gitlab.example/api/v4/projects/123/packages/generic/investor-platform-proofs
EOF
PATH="${fake_bin}:${PATH}" \
FAKE_PACKAGE_DIR="${package_dir}" \
AGENT_TEST_LOG="${agent_log}" \
RD_ALPHA_RELEASE_AGENT_ENV="${agent_env}" \
  bash "${ROOT_DIR}/deploy/rd-alpha-release-agent.sh" "${release_version}"
test "$(wc -l < "${agent_log}")" -eq 3

python3 - "${package_dir}/staging-proof.json" <<'PY'
import json
import sys

path = sys.argv[1]
proof = json.load(open(path))
proof["data_manifest_sha256"] = "e" * 64
open(path, "w").write(json.dumps(proof))
PY
if PATH="${fake_bin}:${PATH}" \
  FAKE_PACKAGE_DIR="${package_dir}" \
  AGENT_TEST_LOG="${agent_log}" \
  RD_ALPHA_RELEASE_AGENT_ENV="${agent_env}" \
  bash "${ROOT_DIR}/deploy/rd-alpha-release-agent.sh" "${release_version}"; then
  echo "Release agent unexpectedly accepted a staging proof for another data manifest." >&2
  exit 1
fi

echo "GitLab release-agent rehearsal passed."
