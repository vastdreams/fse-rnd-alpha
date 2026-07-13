#!/usr/bin/env bash
# Package the host-side immutable-release inputs published by GitLab CI.
#
# Application code belongs in digest-pinned images. This archive holds only the
# deployment contract needed by a host to restore data, replay migrations, and
# activate those already-built images.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR=""
SOURCE_SHA=""
BACKEND_IMAGE=""
FRONTEND_IMAGE=""
PIPELINE_ID=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/create_release_bundle.sh \
    --source-sha <40-character-sha> \
    --backend-image <registry/image@sha256:...> \
    --frontend-image <registry/image@sha256:...> \
    --pipeline-id <numeric-gitlab-pipeline-id> \
    --output-dir <directory>

Writes release-bundle.tar.gz, release.json, and release-bundle.sha256. The
release.json checksum binds the exact source, image digests, and host-side
bundle that a server-side release agent must verify before activation.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --source-sha)
      SOURCE_SHA="${2:-}"
      shift 2
      ;;
    --backend-image)
      BACKEND_IMAGE="${2:-}"
      shift 2
      ;;
    --frontend-image)
      FRONTEND_IMAGE="${2:-}"
      shift 2
      ;;
    --pipeline-id)
      PIPELINE_ID="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ "${SOURCE_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  echo "--source-sha must be a lowercase 40-character Git SHA." >&2
  exit 2
}
[[ "${BACKEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "--backend-image must end in a SHA-256 digest." >&2
  exit 2
}
[[ "${FRONTEND_IMAGE}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "--frontend-image must end in a SHA-256 digest." >&2
  exit 2
}
[[ "${PIPELINE_ID}" =~ ^[1-9][0-9]*$ ]] || {
  echo "--pipeline-id must be a positive numeric GitLab pipeline ID." >&2
  exit 2
}
[[ -n "${OUTPUT_DIR}" ]] || {
  echo "--output-dir is required." >&2
  exit 2
}

release_paths=(
  "deploy/docker-compose.yml"
  "deploy/.env.example"
  "deploy/init.sql"
  "scripts/deploy_release.sh"
  "scripts/restore_data_release.sh"
  "scripts/create_data_manifest.py"
  "scripts/verify_data_manifest.py"
  "scripts/backup_postgres_offsite.sh"
  "scripts/restore_postgres_offsite.sh"
  "scripts/run_migrations.sh"
  "scripts/rollback_release.sh"
  "scripts/research_snapshot.py"
  "scripts/research_release.py"
  "scripts/research_coverage_report.py"
  "scripts/check_release_health.sh"
  "scripts/smoke_public_release.py"
  "scripts/run_authenticated_release_smoke.sh"
  "scripts/migrations"
  "papers"
)

for release_path in "${release_paths[@]}"; do
  [[ -e "${ROOT_DIR}/${release_path}" ]] || {
    echo "Release bundle input is missing: ${release_path}" >&2
    exit 1
  }
done

mkdir -p "${OUTPUT_DIR}"
bundle_path="${OUTPUT_DIR}/release-bundle.tar.gz"
manifest_path="${OUTPUT_DIR}/release.json"
checksum_path="${OUTPUT_DIR}/release-bundle.sha256"
[[ ! -e "${bundle_path}" && ! -e "${manifest_path}" && ! -e "${checksum_path}" ]] || {
  echo "Output directory already contains release output; use a new directory." >&2
  exit 1
}

tar -C "${ROOT_DIR}" -czf "${bundle_path}" "${release_paths[@]}"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

bundle_sha256="$(sha256_of "${bundle_path}")"
printf '%s  %s\n' "${bundle_sha256}" "release-bundle.tar.gz" > "${checksum_path}"

migration_ledger_sha256="$(
  ROOT_DIR="${ROOT_DIR}" python3 - <<'PY'
import hashlib
import os
from pathlib import Path

root = Path(os.environ["ROOT_DIR"]) / "scripts" / "migrations"
digest = hashlib.sha256()
for path in sorted(p for p in root.rglob("*") if p.is_file()):
    rel = path.relative_to(root).as_posix().encode()
    digest.update(rel)
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest())
PY
)"

SOURCE_SHA="${SOURCE_SHA}" \
BACKEND_IMAGE="${BACKEND_IMAGE}" \
FRONTEND_IMAGE="${FRONTEND_IMAGE}" \
PIPELINE_ID="${PIPELINE_ID}" \
BUNDLE_SHA256="${bundle_sha256}" \
MIGRATION_LEDGER_SHA256="${migration_ledger_sha256}" \
RELEASE_CREATED_AT="${RELEASE_CREATED_AT:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" \
python3 - <<'PY' > "${manifest_path}"
import json
import os

print(
    json.dumps(
        {
            "schema_version": 1,
            "source_sha": os.environ["SOURCE_SHA"],
            "pipeline_id": int(os.environ["PIPELINE_ID"]),
            "backend_image": os.environ["BACKEND_IMAGE"],
            "frontend_image": os.environ["FRONTEND_IMAGE"],
            "bundle_filename": "release-bundle.tar.gz",
            "bundle_sha256": os.environ["BUNDLE_SHA256"],
            "migration_ledger_sha256": os.environ["MIGRATION_LEDGER_SHA256"],
            "created_at": os.environ["RELEASE_CREATED_AT"],
        },
        indent=2,
        sort_keys=True,
    )
)
PY

python3 - "${manifest_path}" <<'PY'
import json
import re
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["schema_version"] == 1
assert re.fullmatch(r"[0-9a-f]{40}", manifest["source_sha"])
assert re.search(r"@sha256:[0-9a-f]{64}$", manifest["backend_image"])
assert re.search(r"@sha256:[0-9a-f]{64}$", manifest["frontend_image"])
assert re.fullmatch(r"[0-9a-f]{64}", manifest["bundle_sha256"])
assert re.fullmatch(r"[0-9a-f]{64}", manifest["migration_ledger_sha256"])
PY

echo "Created release bundle for ${SOURCE_SHA}: ${bundle_path}"
