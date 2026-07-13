#!/usr/bin/env bash
# Pull and activate one immutable GitLab release from the production host.
#
# This runs on the host (or through its systemd unit), so promotion uses
# outbound HTTPS only. CI never receives production SSH access and the live
# service never needs a mutable Git checkout.

set -Eeuo pipefail

AGENT_ENV_FILE="${RD_ALPHA_RELEASE_AGENT_ENV:-/etc/rd-alpha/release-agent.env}"

usage() {
  cat <<'USAGE'
Usage: rd-alpha-release-agent.sh <40-character-source-sha>-<GitLab-pipeline-id>

The agent reads trusted host-local settings from
/etc/rd-alpha/release-agent.env by default:

  RELEASE_BASE_URL=https://gitlab.example/api/v4/projects/<id>/packages/generic/investor-platform
  RELEASE_TOKEN=<read-only-package-token>
  RELEASE_AUTH_HEADER=PRIVATE-TOKEN
  RELEASE_ROOT=/opt/rd-alpha
  STATE_DIR=/var/lib/rd-alpha
  DEPLOY_ENV_FILE=/etc/rd-alpha/prod.env
  BACKUP_DIR=/var/lib/rd-alpha/backups
  REQUIRE_STAGING_PROOF=true
  STAGING_PROOF_BASE_URL=https://gitlab.example/api/v4/projects/<id>/packages/generic/investor-platform-proofs

Each release is downloaded from <RELEASE_BASE_URL>/<release-version>/, verified,
extracted under <RELEASE_ROOT>/releases/, deployed from that immutable
directory, then atomically selected through <RELEASE_ROOT>/current.
USAGE
}

[[ "$#" -eq 1 ]] || {
  usage >&2
  exit 2
}

RELEASE_VERSION="$1"
[[ "${RELEASE_VERSION}" =~ ^([0-9a-f]{40})-([1-9][0-9]*)$ ]] || {
  echo "Release version must be <40-character-source-sha>-<GitLab-pipeline-id>." >&2
  exit 2
}
REQUESTED_SOURCE_SHA="${RELEASE_VERSION%%-*}"
REQUESTED_PIPELINE_ID="${RELEASE_VERSION##*-}"
[[ -f "${AGENT_ENV_FILE}" ]] || {
  echo "Missing release-agent environment file: ${AGENT_ENV_FILE}" >&2
  exit 1
}

# Do not source the file: deployment credentials may contain shell metacharacters.
# Only allow the small, explicit set of host-local configuration keys.
while IFS= read -r line || [[ -n "${line}" ]]; do
  case "${line}" in
    ''|\#*) continue ;;
  esac
  [[ "${line}" == *"="* ]] || {
    echo "Malformed release-agent environment line." >&2
    exit 1
  }
  key="${line%%=*}"
  value="${line#*=}"
  case "${key}" in
    RELEASE_BASE_URL|RELEASE_TOKEN|RELEASE_AUTH_HEADER|RELEASE_ROOT|STATE_DIR|DEPLOY_ENV_FILE|BACKUP_DIR|\
    REQUIRE_STAGING_PROOF|STAGING_PROOF_BASE_URL)
      value="${value%\"}"
      value="${value#\"}"
      export "${key}=${value}"
      ;;
    *)
      echo "Unsupported release-agent environment key: ${key}" >&2
      exit 1
      ;;
  esac
done < "${AGENT_ENV_FILE}"

: "${RELEASE_BASE_URL:?RELEASE_BASE_URL is required}"
: "${RELEASE_TOKEN:?RELEASE_TOKEN is required}"
RELEASE_AUTH_HEADER="${RELEASE_AUTH_HEADER:-PRIVATE-TOKEN}"
RELEASE_ROOT="${RELEASE_ROOT:-/opt/rd-alpha}"
STATE_DIR="${STATE_DIR:-/var/lib/rd-alpha}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-/etc/rd-alpha/prod.env}"
BACKUP_DIR="${BACKUP_DIR:-${STATE_DIR}/backups}"
REQUIRE_STAGING_PROOF="${REQUIRE_STAGING_PROOF:-false}"

[[ "${RELEASE_BASE_URL}" =~ ^https:// ]] || {
  echo "RELEASE_BASE_URL must use HTTPS." >&2
  exit 1
}
[[ "${REQUIRE_STAGING_PROOF}" == "true" || "${REQUIRE_STAGING_PROOF}" == "false" ]] || {
  echo "REQUIRE_STAGING_PROOF must be true or false." >&2
  exit 1
}
if [[ "${REQUIRE_STAGING_PROOF}" == "true" ]]; then
  : "${STAGING_PROOF_BASE_URL:?STAGING_PROOF_BASE_URL is required when staging proof is required}"
  [[ "${STAGING_PROOF_BASE_URL}" =~ ^https:// ]] || {
    echo "STAGING_PROOF_BASE_URL must use HTTPS." >&2
    exit 1
  }
fi
[[ -f "${DEPLOY_ENV_FILE}" ]] || {
  echo "Missing host deployment environment file: ${DEPLOY_ENV_FILE}" >&2
  exit 1
}
command -v curl >/dev/null
command -v tar >/dev/null
command -v python3 >/dev/null
command -v flock >/dev/null || {
  echo "flock is required to serialize releases." >&2
  exit 1
}

umask 077
mkdir -p "${RELEASE_ROOT}/releases" "${STATE_DIR}/release-records" "${BACKUP_DIR}"
chmod 0700 "${STATE_DIR}" "${STATE_DIR}/release-records" "${BACKUP_DIR}"
exec 9>"${STATE_DIR}/release.lock"
flock -n 9 || {
  echo "Another release activation is already running." >&2
  exit 1
}

work_dir="$(mktemp -d "${STATE_DIR}/release-download.XXXXXX")"
staging_dir=""
cleanup() {
  rm -rf "${work_dir}"
  if [[ -n "${staging_dir}" && -d "${staging_dir}" ]]; then
    rm -rf "${staging_dir}"
  fi
}
trap cleanup EXIT

release_url="${RELEASE_BASE_URL%/}/${RELEASE_VERSION}"
request_header="${RELEASE_AUTH_HEADER}: ${RELEASE_TOKEN}"
curl --fail --silent --show-error --location \
  --header "${request_header}" \
  "${release_url}/release.json" \
  --output "${work_dir}/release.json"

IFS=$'\t' read -r source_sha pipeline_id backend_image frontend_image bundle_filename bundle_sha256 <<EOF
$(python3 - "${work_dir}/release.json" "${REQUESTED_SOURCE_SHA}" "${REQUESTED_PIPELINE_ID}" <<'PY'
import json
import re
import sys

path, requested_source, requested_pipeline = sys.argv[1:4]
manifest = json.load(open(path))
required = {
    "schema_version",
    "source_sha",
    "backend_image",
    "frontend_image",
    "bundle_filename",
    "bundle_sha256",
    "pipeline_id",
    "created_at",
}
missing = required - set(manifest)
if missing:
    raise SystemExit(f"Release manifest missing: {', '.join(sorted(missing))}")
if manifest["schema_version"] != 1:
    raise SystemExit("Unsupported release manifest schema")
if manifest["source_sha"] != requested_source or not re.fullmatch(r"[0-9a-f]{40}", requested_source):
    raise SystemExit("Release manifest source SHA does not match requested release")
for name in ("backend_image", "frontend_image"):
    if not re.search(r"@sha256:[0-9a-f]{64}$", manifest[name]):
        raise SystemExit(f"Release manifest has invalid {name}")
if manifest["bundle_filename"] != "release-bundle.tar.gz":
    raise SystemExit("Unexpected release bundle filename")
if not re.fullmatch(r"[0-9a-f]{64}", manifest["bundle_sha256"]):
    raise SystemExit("Release manifest has invalid bundle checksum")
if (
    not isinstance(manifest["pipeline_id"], int)
    or manifest["pipeline_id"] < 1
    or manifest["pipeline_id"] != int(requested_pipeline)
):
    raise SystemExit("Release manifest has invalid pipeline ID")
print(
    "\t".join(
        (
            manifest["source_sha"],
            str(manifest["pipeline_id"]),
            manifest["backend_image"],
            manifest["frontend_image"],
            manifest["bundle_filename"],
            manifest["bundle_sha256"],
        )
    )
)
PY
)
EOF

if [[ "${REQUIRE_STAGING_PROOF}" == "true" ]]; then
  staging_proof_url="${STAGING_PROOF_BASE_URL%/}/${RELEASE_VERSION}/staging-proof.json"
  curl --fail --silent --show-error --location \
    --header "${request_header}" \
    "${staging_proof_url}" \
    --output "${work_dir}/staging-proof.json"
  python3 - "${work_dir}/staging-proof.json" "${RELEASE_VERSION}" "${source_sha}" "${pipeline_id}" "${DEPLOY_ENV_FILE}" <<'PY'
import json
import re
import sys

path, expected_version, expected_source_sha, expected_pipeline_id, env_path = sys.argv[1:]
proof = json.load(open(path))
if proof.get("schema_version") != 1 or proof.get("status") != "passed":
    raise SystemExit("Staging proof is not a passed schema-version-1 attestation")
if proof.get("release_version") != expected_version:
    raise SystemExit("Staging proof release version does not match requested production release")
if proof.get("source_sha") != expected_source_sha or not re.fullmatch(
    r"[0-9a-f]{40}", expected_source_sha
):
    raise SystemExit("Staging proof source SHA does not match requested production release")
if proof.get("pipeline_id") != int(expected_pipeline_id):
    raise SystemExit("Staging proof pipeline ID does not match requested production release")
for key in ("staging_api_smoke_job_id", "staging_browser_smoke_job_id"):
    if not isinstance(proof.get(key), int) or proof[key] < 1:
        raise SystemExit(f"Staging proof has no valid {key}")
staging_data_manifest = proof.get("data_manifest_sha256")
if not isinstance(staging_data_manifest, str) or not re.fullmatch(
    r"[0-9a-f]{64}", staging_data_manifest
):
    raise SystemExit("Staging proof has no valid data-manifest checksum")
target_data_uri = ""
for raw in open(env_path):
    line = raw.rstrip("\n")
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key == "DATA_RELEASE_URI":
        target_data_uri = value.strip('"')
        break
if not target_data_uri.startswith("s3://"):
    raise SystemExit("Target deploy environment has no immutable DATA_RELEASE_URI")
target_data_manifest = target_data_uri.rstrip("/").rsplit("/", 1)[-1]
if not re.fullmatch(r"[0-9a-f]{64}", target_data_manifest):
    raise SystemExit("Target DATA_RELEASE_URI does not end with a data-manifest checksum")
if staging_data_manifest != target_data_manifest:
    raise SystemExit("Target data manifest does not match the passed staging proof")
PY
fi

curl --fail --silent --show-error --location \
  --header "${request_header}" \
  "${release_url}/${bundle_filename}" \
  --output "${work_dir}/${bundle_filename}"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

actual_bundle_sha="$(sha256_of "${work_dir}/${bundle_filename}")"
[[ "${actual_bundle_sha}" == "${bundle_sha256}" ]] || {
  echo "Downloaded release bundle checksum does not match release.json." >&2
  exit 1
}

tar -tzf "${work_dir}/${bundle_filename}" > "${work_dir}/bundle.list"
python3 - "${work_dir}/bundle.list" <<'PY'
import pathlib
import sys

required = {
    "deploy/docker-compose.yml",
    "scripts/deploy_release.sh",
    "scripts/check_release_health.sh",
    "scripts/create_data_manifest.py",
    "scripts/verify_data_manifest.py",
    "scripts/research_coverage_report.py",
    "scripts/backup_postgres_offsite.sh",
    "scripts/restore_postgres_offsite.sh",
    "scripts/smoke_public_release.py",
    "scripts/run_authenticated_release_smoke.sh",
}
seen = set()
for raw in open(sys.argv[1]):
    name = raw.strip().rstrip("/")
    if not name:
        continue
    path = pathlib.PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"Unsafe archive path: {name}")
    seen.add(name)
missing = required - seen
if missing:
    raise SystemExit(f"Release bundle is missing: {', '.join(sorted(missing))}")
PY

release_dir="${RELEASE_ROOT}/releases/${RELEASE_VERSION}"
if [[ ! -d "${release_dir}" ]]; then
  staging_dir="$(mktemp -d "${RELEASE_ROOT}/releases/.${RELEASE_VERSION}.staging.XXXXXX")"
  tar -xzf "${work_dir}/${bundle_filename}" -C "${staging_dir}"
  cp "${work_dir}/release.json" "${staging_dir}/release.json"
  printf '%s  %s\n' "${bundle_sha256}" "${bundle_filename}" > "${staging_dir}/release-bundle.sha256"
  chmod -R go-w "${staging_dir}"
  mv "${staging_dir}" "${release_dir}"
  staging_dir=""
else
  existing_sha="$(
    python3 - "${release_dir}/release.json" <<'PY'
import json
import sys

print(json.load(open(sys.argv[1]))["bundle_sha256"])
PY
  )"
  [[ "${existing_sha}" == "${bundle_sha256}" ]] || {
    echo "Existing release directory has a different bundle checksum: ${release_dir}" >&2
    exit 1
  }
fi

previous_release_sha=""
previous_release_ref=""
current_link="${RELEASE_ROOT}/current"
if [[ -L "${current_link}" ]]; then
  previous_dir="$(readlink -f "${current_link}")"
  previous_release_ref="$(basename "${previous_dir}")"
  if [[ -f "${previous_dir}/release.json" ]]; then
    previous_release_sha="$(
      python3 - "${previous_dir}/release.json" <<'PY'
import json
import re
import sys

source_sha = json.load(open(sys.argv[1])).get("source_sha", "")
print(source_sha if re.fullmatch(r"[0-9a-f]{40}", source_sha) else "")
PY
    )"
  fi
fi

RELEASE_SHA="${source_sha}" \
RELEASE_REF="${RELEASE_VERSION}" \
PREVIOUS_RELEASE_SHA="${previous_release_sha}" \
PREVIOUS_RELEASE_REF="${previous_release_ref}" \
BACKEND_IMAGE="${backend_image}" \
FRONTEND_IMAGE="${frontend_image}" \
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE}" \
BACKUP_DIR="${BACKUP_DIR}" \
  bash "${release_dir}/scripts/deploy_release.sh"

next_link="${RELEASE_ROOT}/.current.${RELEASE_VERSION}.$RANDOM"
ln -s "${release_dir}" "${next_link}"
python3 - "${next_link}" "${current_link}" <<'PY'
import os
import sys

os.replace(sys.argv[1], sys.argv[2])
PY

SOURCE_SHA="${source_sha}" \
RELEASE_VERSION="${RELEASE_VERSION}" \
BACKEND_IMAGE="${backend_image}" \
FRONTEND_IMAGE="${frontend_image}" \
BUNDLE_SHA256="${bundle_sha256}" \
RELEASE_URL="${release_url}" \
RELEASE_ACTIVATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
python3 - <<'PY' > "${STATE_DIR}/release-records/${RELEASE_VERSION}.json"
import json
import os

print(
    json.dumps(
        {
            "source_sha": os.environ["SOURCE_SHA"],
            "release_version": os.environ["RELEASE_VERSION"],
            "backend_image": os.environ["BACKEND_IMAGE"],
            "frontend_image": os.environ["FRONTEND_IMAGE"],
            "bundle_sha256": os.environ["BUNDLE_SHA256"],
            "release_url": os.environ["RELEASE_URL"],
            "activated_at": os.environ["RELEASE_ACTIVATED_AT"],
        },
        indent=2,
        sort_keys=True,
    )
)
PY

echo "Activated immutable release ${RELEASE_VERSION} (${source_sha}) from ${release_url}."
