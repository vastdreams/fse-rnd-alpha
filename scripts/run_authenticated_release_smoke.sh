#!/usr/bin/env bash
# Run and retain a secret-free, two-user smoke proof from the deployed target.
#
# Intended for a protected staging/production runner that is local to (or has
# private access to) the target. CI never receives an SSH key or a command
# channel into the host.

set -Eeuo pipefail

RELEASE_ROOT="${RELEASE_ROOT:-/opt/rd-alpha}"
SMOKE_EVIDENCE_DIR="${SMOKE_EVIDENCE_DIR:-/var/lib/rd-alpha/smoke-evidence}"
TARGET="${RELEASE_SMOKE_TARGET:?RELEASE_SMOKE_TARGET is required}"
RELEASE_VERSION="${RELEASE_SMOKE_RELEASE_VERSION:?RELEASE_SMOKE_RELEASE_VERSION is required}"
BASE_URL="${RELEASE_SMOKE_BASE_URL:?RELEASE_SMOKE_BASE_URL is required}"
EMAIL="${RELEASE_SMOKE_EMAIL:?RELEASE_SMOKE_EMAIL is required}"
PASSWORD="${RELEASE_SMOKE_PASSWORD:?RELEASE_SMOKE_PASSWORD is required}"
SECOND_EMAIL="${RELEASE_SMOKE_SECOND_EMAIL:?RELEASE_SMOKE_SECOND_EMAIL is required}"
SECOND_PASSWORD="${RELEASE_SMOKE_SECOND_PASSWORD:?RELEASE_SMOKE_SECOND_PASSWORD is required}"
EXPECTED_DATA_MANIFEST_SHA256="${RELEASE_SMOKE_EXPECTED_DATA_MANIFEST_SHA256:?RELEASE_SMOKE_EXPECTED_DATA_MANIFEST_SHA256 is required}"
ARTIFACT_DIR="${RELEASE_SMOKE_ARTIFACT_DIR:-}"

[[ "${TARGET}" =~ ^(staging|production)$ ]] || {
  echo "RELEASE_SMOKE_TARGET must be staging or production." >&2
  exit 2
}
[[ "${RELEASE_VERSION}" =~ ^([0-9a-f]{40})-([1-9][0-9]*)$ ]] || {
  echo "RELEASE_SMOKE_RELEASE_VERSION must be <source-sha>-<pipeline-id>." >&2
  exit 2
}
[[ "${EXPECTED_DATA_MANIFEST_SHA256}" =~ ^[0-9a-f]{64}$ ]] || {
  echo "RELEASE_SMOKE_EXPECTED_DATA_MANIFEST_SHA256 must be a SHA-256 checksum." >&2
  exit 2
}
[[ "${BASE_URL}" =~ ^https:// ]] || {
  echo "RELEASE_SMOKE_BASE_URL must be an HTTPS origin." >&2
  exit 2
}

expected_source_sha="${RELEASE_VERSION%%-*}"
current_manifest="${RELEASE_ROOT}/current/release.json"
[[ -f "${current_manifest}" ]] || {
  echo "Current immutable release manifest is unavailable: ${current_manifest}" >&2
  exit 1
}

python3 - "${current_manifest}" "${RELEASE_VERSION}" "${expected_source_sha}" <<'PY'
import json
import sys
from pathlib import Path

path, expected_version, expected_source_sha = sys.argv[1:]
manifest = json.loads(Path(path).read_text())
if manifest.get("source_sha") != expected_source_sha:
    raise SystemExit("Current release source SHA does not match requested smoke version")
if manifest.get("pipeline_id") != int(expected_version.rsplit("-", 1)[1]):
    raise SystemExit("Current release pipeline ID does not match requested smoke version")
PY

current_dir="$(python3 - "${RELEASE_ROOT}/current" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)"
[[ "$(basename "${current_dir}")" == "${RELEASE_VERSION}" ]] || {
  echo "Current release directory does not match requested smoke version." >&2
  exit 1
}

smoke_script="${current_dir}/scripts/smoke_public_release.py"
[[ -f "${smoke_script}" ]] || {
  echo "Current release does not contain the authenticated smoke script." >&2
  exit 1
}

umask 077
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_dir="${SMOKE_EVIDENCE_DIR}/${TARGET}/${RELEASE_VERSION}/${timestamp}"
mkdir -p "${evidence_dir}"
chmod 0700 "${evidence_dir}"
cp "${current_manifest}" "${evidence_dir}/release.json"
chmod 0600 "${evidence_dir}/release.json"

write_summary() {
  local status="$1"
  SMOKE_STATUS="${status}" \
  SMOKE_TARGET="${TARGET}" \
  SMOKE_RELEASE_VERSION="${RELEASE_VERSION}" \
  SMOKE_BASE_URL="${BASE_URL}" \
  SMOKE_RECORDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  python3 - "${evidence_dir}/summary.json" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "status": os.environ["SMOKE_STATUS"],
    "target": os.environ["SMOKE_TARGET"],
    "release_version": os.environ["SMOKE_RELEASE_VERSION"],
    "base_url": os.environ["SMOKE_BASE_URL"],
    "recorded_at": os.environ["SMOKE_RECORDED_AT"],
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
os.chmod(sys.argv[1], 0o600)
PY
}

smoke_args=(
  --base-url "${BASE_URL}"
  --expected-source-sha "${expected_source_sha}"
  --expected-data-manifest-sha256 "${EXPECTED_DATA_MANIFEST_SHA256}"
  --evidence-file "${evidence_dir}/api-smoke.json"
)

set +e
RELEASE_SMOKE_EMAIL="${EMAIL}" \
RELEASE_SMOKE_PASSWORD="${PASSWORD}" \
RELEASE_SMOKE_SECOND_EMAIL="${SECOND_EMAIL}" \
RELEASE_SMOKE_SECOND_PASSWORD="${SECOND_PASSWORD}" \
  python3 "${smoke_script}" "${smoke_args[@]}" \
  > "${evidence_dir}/api-smoke.stdout.json" \
  2> "${evidence_dir}/api-smoke.stderr.log"
smoke_status=$?
set -e

if [[ "${smoke_status}" -eq 0 ]]; then
  write_summary "passed"
else
  write_summary "failed"
fi

if [[ -n "${ARTIFACT_DIR}" ]]; then
  mkdir -p "${ARTIFACT_DIR}"
  chmod 0700 "${ARTIFACT_DIR}"
  cp -R "${evidence_dir}" "${ARTIFACT_DIR}/"
fi

if [[ "${smoke_status}" -ne 0 ]]; then
  echo "Authenticated ${TARGET} smoke failed; evidence retained at ${evidence_dir}." >&2
  exit "${smoke_status}"
fi

echo "Authenticated ${TARGET} smoke passed; evidence retained at ${evidence_dir}."
