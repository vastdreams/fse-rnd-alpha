#!/usr/bin/env bash
# Restore a staged investor-data release atomically and retain the prior tree.
#
# Usage:
#   DATA_RELEASE_URI=s3://bucket/investor-platform-data/univ/hash \
#   EXPECTED_SOURCE_SHA=<checked-out-release-sha> \
#     ./scripts/restore_data_release.sh

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-${ROOT_DIR}/../rd-alpha-data}"
: "${DATA_RELEASE_URI:?DATA_RELEASE_URI must point at a staged immutable release prefix}"
: "${EXPECTED_SOURCE_SHA:?EXPECTED_SOURCE_SHA must match the checked-out release source SHA}"

command -v aws >/dev/null 2>&1 || {
  echo "aws CLI is required to restore a data release" >&2
  exit 1
}
[[ "${EXPECTED_SOURCE_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  echo "EXPECTED_SOURCE_SHA must be a full 40-character Git SHA" >&2
  exit 2
}
if [[ -n "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256:-}" &&
  ! "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256 must be a SHA-256 checksum" >&2
  exit 2
fi

checksum() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

parent_dir="$(dirname "${DATA_DIR}")"
mkdir -p "${parent_dir}"
stage_dir="$(mktemp -d "${parent_dir}/.rd-alpha-data-stage.XXXXXX")"
trap 'rm -rf "${stage_dir}"' EXIT
manifest="${stage_dir}/manifest.json"
archive="${stage_dir}/data.tar.gz"
release="${stage_dir}/release.json"
research_snapshot="${stage_dir}/research_snapshot.json"
research_records="${stage_dir}/research_records.json"

# Fetch the small descriptor first. Releases staged with schema v2 pin every
# payload fetch to its exact S3 VersionId; a later overwrite of an unversioned
# key cannot change what gets restored.
aws s3 cp "${DATA_RELEASE_URI%/}/release.json" "${release}" --only-show-errors

release_descriptor_sha="$(checksum "${release}")"
if [[ -n "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256:-}" &&
  "${release_descriptor_sha}" != "${EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256}" ]]; then
  echo "Release descriptor checksum does not match the approved data release." >&2
  exit 1
fi

IFS=$'\t' read -r release_schema archive_version_id manifest_version_id \
  research_snapshot_version_id research_records_version_id <<< "$(
  python3 - "${release}" <<'PY'
import json
import sys

release = json.load(open(sys.argv[1]))
schema = release.get("schema_version")
if schema == 1:
    print("1\t\t\t\t")
    raise SystemExit
if schema not in (2, 3):
    raise SystemExit(f"Unsupported release schema: {schema!r}")
versions = release.get("object_versions")
expected = {
    "data.tar.gz",
    "manifest.json",
    "research_snapshot.json",
    "research_records.json",
}
if not isinstance(versions, dict) or set(versions) != expected:
    raise SystemExit("Release record has invalid object-version bindings")
for name in sorted(expected):
    value = versions[name]
    if not isinstance(value, str) or not value or value in {"None", "null"}:
        raise SystemExit(f"Release record has no S3 VersionId for {name}")
print(
    "\t".join(
        (
            str(schema),
            versions["data.tar.gz"],
            versions["manifest.json"],
            versions["research_snapshot.json"],
            versions["research_records.json"],
        )
    )
)
PY
)"

release_location="${DATA_RELEASE_URI#s3://}"
release_bucket="${release_location%%/*}"
release_key_prefix="${release_location#*/}"
[[ -n "${release_bucket}" && "${release_key_prefix}" != "${release_location}" ]] || {
  echo "DATA_RELEASE_URI must include an S3 bucket and release prefix." >&2
  exit 2
}

download_release_object() {
  local object_name="$1"
  local destination="$2"
  local version_id="$3"
  if [[ "${release_schema}" != "1" ]]; then
    aws s3api get-object \
      --bucket "${release_bucket}" \
      --key "${release_key_prefix%/}/${object_name}" \
      --version-id "${version_id}" \
      "${destination}" \
      --output json >/dev/null
  else
    aws s3 cp "${DATA_RELEASE_URI%/}/${object_name}" "${destination}" --only-show-errors
  fi
}

download_release_object "manifest.json" "${manifest}" "${manifest_version_id}"
download_release_object "data.tar.gz" "${archive}" "${archive_version_id}"
download_release_object "research_snapshot.json" "${research_snapshot}" "${research_snapshot_version_id}"
download_release_object "research_records.json" "${research_records}" "${research_records_version_id}"

release_metadata="$(
  python3 - "${release}" "${manifest}" "${research_snapshot}" "${research_records}" <<'PY'
import hashlib
import json
import sys

release_path, manifest_path, snapshot_path, records_path = sys.argv[1:]
release = json.load(open(release_path))
manifest = json.load(open(manifest_path))
snapshot = json.load(open(snapshot_path))
records = json.load(open(records_path))

required = (
    "universe_version",
    "manifest_sha256",
    "archive_sha256",
    "database_snapshot_sha256",
    "research_records_sha256",
    "source_sha",
)
for name in required:
    value = release.get(name)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Release record is missing {name}")

if release.get("schema_version") not in (1, 2, 3):
    raise SystemExit(f"Unsupported release schema: {release.get('schema_version')!r}")
if manifest.get("manifest_sha256") != release["manifest_sha256"]:
    raise SystemExit("Data manifest reference does not match the release record")
if manifest.get("universe_version") != release["universe_version"]:
    raise SystemExit("Data manifest universe version does not match the release record")
if snapshot.get("schema_version") != 1:
    raise SystemExit(f"Unsupported research snapshot schema: {snapshot.get('schema_version')!r}")
if snapshot.get("universe_version") != release["universe_version"]:
    raise SystemExit("Research snapshot universe version does not match the release record")
expected_snapshot_sha = snapshot.get("snapshot_sha256")
if not isinstance(expected_snapshot_sha, str):
    raise SystemExit("Research snapshot has no checksum")
snapshot_without_checksum = dict(snapshot)
snapshot_without_checksum.pop("snapshot_sha256", None)
actual_snapshot_sha = hashlib.sha256(
    json.dumps(snapshot_without_checksum, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
if actual_snapshot_sha != expected_snapshot_sha:
    raise SystemExit("Research snapshot checksum does not match its contents")
if expected_snapshot_sha != release["database_snapshot_sha256"]:
    raise SystemExit("Research snapshot checksum does not match the release record")
records_sha = records.get("payload_sha256")
records_without_checksum = dict(records)
records_without_checksum.pop("payload_sha256", None)
actual_records_sha = hashlib.sha256(
    json.dumps(records_without_checksum, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
if not isinstance(records_sha, str) or records_sha != actual_records_sha:
    raise SystemExit("Research record checksum does not match its contents")
if records_sha != release["research_records_sha256"]:
    raise SystemExit("Research record checksum does not match the release record")
if records.get("universe_version") != release["universe_version"]:
    raise SystemExit("Research records universe version does not match the release record")
if records.get("source_sha") != release["source_sha"]:
    raise SystemExit("Research records source SHA does not match the release record")
if records.get("data_manifest_sha256") != release["manifest_sha256"]:
    raise SystemExit("Research records data manifest does not match the release record")
if records.get("database_snapshot_sha256") != release["database_snapshot_sha256"]:
    raise SystemExit("Research records database snapshot does not match the release record")

print(
    "\t".join(
        (
            release["archive_sha256"],
            release["manifest_sha256"],
            release["source_sha"],
            release["universe_version"],
            release["database_snapshot_sha256"],
            release["research_records_sha256"],
        )
    )
)
PY
)"
IFS=$'\t' read -r expected_archive_sha expected_manifest_sha release_source_sha \
  release_universe_version release_database_snapshot_sha release_research_records_sha <<< "${release_metadata}"
[[ "${release_source_sha}" == "${EXPECTED_SOURCE_SHA}" ]] || {
  echo "Data release source SHA ${release_source_sha} does not match ${EXPECTED_SOURCE_SHA}" >&2
  exit 1
}
if [[ -n "${EXPECTED_UNIVERSE_VERSION:-}" && "${release_universe_version}" != "${EXPECTED_UNIVERSE_VERSION}" ]]; then
  echo "Data release universe ${release_universe_version} does not match ${EXPECTED_UNIVERSE_VERSION}" >&2
  exit 1
fi
if [[ -n "${EXPECTED_DATA_MANIFEST_SHA256:-}" && "${expected_manifest_sha}" != "${EXPECTED_DATA_MANIFEST_SHA256}" ]]; then
  echo "Data manifest ${expected_manifest_sha} does not match ${EXPECTED_DATA_MANIFEST_SHA256}" >&2
  exit 1
fi
if [[ -n "${EXPECTED_DATABASE_SNAPSHOT_SHA256:-}" &&
  "${release_database_snapshot_sha}" != "${EXPECTED_DATABASE_SNAPSHOT_SHA256}" ]]; then
  echo "Research snapshot checksum does not match the expected release metadata" >&2
  exit 1
fi
actual_archive_sha="$(checksum "${archive}")"
[[ "${actual_archive_sha}" == "${expected_archive_sha}" ]] || {
  echo "Data archive checksum mismatch" >&2
  exit 1
}

restore_tree="${stage_dir}/data"
mkdir -p "${restore_tree}"
python3 - "${archive}" <<'PY'
import sys
import tarfile
from pathlib import PurePosixPath

with tarfile.open(sys.argv[1], "r:gz") as artifact:
    for member in artifact.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"Unsafe path in data archive: {member.name}")
        if member.issym() or member.islnk():
            raise SystemExit(f"Links are not allowed in data archives: {member.name}")
PY
tar -C "${restore_tree}" -xzf "${archive}"
python3 "${ROOT_DIR}/scripts/verify_data_manifest.py" \
  --manifest "${manifest}" \
  --data-dir "${restore_tree}"
if [[ "${release_schema}" == "3" ]]; then
  python3 - "${release}" "${restore_tree}" "${ROOT_DIR}/scripts" <<'PY'
import json
import sys
from pathlib import Path, PurePosixPath

release = json.load(open(sys.argv[1]))
data_root = Path(sys.argv[2]).resolve()
sys.path.insert(0, sys.argv[3])
from research_coverage_report import validate_report

coverage = release.get("coverage_report")
if not isinstance(coverage, dict):
    raise SystemExit("Schema-v3 release has no coverage report binding")
relative = coverage.get("path")
expected_sha = coverage.get("sha256")
if not isinstance(relative, str) or not isinstance(expected_sha, str):
    raise SystemExit("Schema-v3 release has an invalid coverage report binding")
path = PurePosixPath(relative)
if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("coverage_reports",):
    raise SystemExit("Schema-v3 release has an unsafe coverage report path")
report_path = (data_root / Path(*path.parts)).resolve()
if data_root not in report_path.parents or not report_path.is_file():
    raise SystemExit("Restored data has no bound coverage report")
report = json.load(open(report_path))
validate_report(
    report,
    expected_universe_version=str(release.get("universe_version") or ""),
    expected_source_sha=str(release.get("source_sha") or ""),
)
if expected_sha != report["report_sha256"]:
    raise SystemExit("Coverage report checksum does not match the release record")
PY
fi
cp "${manifest}" "${restore_tree}/release_manifest.json"
cp "${release}" "${restore_tree}/release_metadata.json"
cp "${research_snapshot}" "${restore_tree}/research_snapshot.json"
cp "${research_records}" "${restore_tree}/research_records.json"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
previous_dir=""
if [[ -e "${DATA_DIR}" ]]; then
  previous_dir="${DATA_DIR}.previous-${timestamp}"
  mv "${DATA_DIR}" "${previous_dir}"
fi
if ! mv "${restore_tree}" "${DATA_DIR}"; then
  if [[ -n "${previous_dir}" && -e "${previous_dir}" ]]; then
    mv "${previous_dir}" "${DATA_DIR}"
  fi
  echo "Atomic data swap failed; restored the previous data directory." >&2
  exit 1
fi
trap - EXIT
rm -rf "${stage_dir}"

printf 'Restored data release to %s\n' "${DATA_DIR}"
printf 'Release source SHA: %s\n' "${release_source_sha}"
printf 'Sealed universe version: %s\n' "${release_universe_version}"
printf 'Research snapshot checksum: %s\n' "${release_database_snapshot_sha}"
printf 'Research records checksum: %s\n' "${release_research_records_sha}"
printf 'Release descriptor checksum: %s\n' "${release_descriptor_sha}"
if [[ -n "${previous_dir}" ]]; then
  printf 'Previous data retained at %s\n' "${previous_dir}"
fi
