#!/usr/bin/env bash
# Package a reproducible investor-data release and publish it to versioned S3.
#
# Usage:
#   DATA_RELEASE_BUCKET=my-bucket DATABASE_URL=postgresql://... \
#     ./scripts/stage_data_release.sh --universe-version univ_...
#
# The resulting URI is immutable: publishing refuses to overwrite an existing
# manifest hash. Secrets are read only by the AWS CLI's configured credentials.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-${ROOT_DIR}/data}"
DATA_RELEASE_PREFIX="${DATA_RELEASE_PREFIX:-investor-platform-data}"

: "${DATA_RELEASE_BUCKET:?DATA_RELEASE_BUCKET must name the versioned S3 bucket}"
: "${DATABASE_URL:?DATABASE_URL must identify the sealed research database}"
# SQLAlchemy's async dialect URL is valid for app services but not for psql.
# Keep DATABASE_URL unchanged for the Python release tooling and use this
# normalized value only for the shell's direct PostgreSQL commands.
PSQL_DATABASE_URL="${DATABASE_URL}"
if [[ "${PSQL_DATABASE_URL}" == postgresql+asyncpg://* ]]; then
  PSQL_DATABASE_URL="postgresql://${PSQL_DATABASE_URL#postgresql+asyncpg://}"
fi
command -v aws >/dev/null 2>&1 || {
  echo "aws CLI is required to stage a data release" >&2
  exit 1
}
command -v psql >/dev/null 2>&1 || {
  echo "psql is required to verify the sealed research build" >&2
  exit 1
}

checksum() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

sql_literal() {
  printf '%s' "$1" | sed "s/'/''/g"
}

universe_version=""
release_source_sha="${RELEASE_SOURCE_SHA:-$(git -C "${ROOT_DIR}" rev-parse HEAD)}"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --universe-version)
      universe_version="${2:-}"
      shift 2
      ;;
    --source-sha)
      release_source_sha="${2:-}"
      shift 2
      ;;
    *)
      echo "Usage: $0 --universe-version <immutable-universe-version> [--source-sha <git-sha>]" >&2
      exit 2
      ;;
  esac
done
[[ -n "${universe_version}" ]] || {
  echo "--universe-version is required" >&2
  exit 2
}
[[ "${release_source_sha}" =~ ^[0-9a-f]{40}$ ]] || {
  echo "--source-sha must be a full 40-character Git SHA" >&2
  exit 2
}
checked_out_source_sha="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
[[ "${release_source_sha}" == "${checked_out_source_sha}" ]] || {
  echo "--source-sha must match the committed source checkout being staged." >&2
  exit 1
}
[[ -d "${DATA_DIR}" ]] || {
  echo "Data directory not found: ${DATA_DIR}" >&2
  exit 1
}
if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
  echo "Refusing to stage data from a dirty source checkout; commit or isolate the release first." >&2
  exit 1
fi

# A release artifact is meaningful only when its cache tree, source revision,
# and research records all name the same sealed universe. The source SHA is
# recorded by the immutable universe builder and must not be inferred from a
# mutable active-version pointer.
build_metadata="$(
  psql "${PSQL_DATABASE_URL}" -X -A -t -v ON_ERROR_STOP=1 -F $'\t' \
    -c "
      SELECT status,
             COALESCE(source_sha, ''),
             COALESCE(
               to_char(sealed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'),
               ''
             )
        FROM universe_builds
       WHERE universe_version = '$(sql_literal "${universe_version}")';
    "
)"
IFS=$'\t' read -r build_status build_source_sha sealed_at <<< "${build_metadata}"
[[ "${build_status:-}" == "sealed" ]] || {
  echo "Universe ${universe_version} is not a sealed build." >&2
  exit 1
}
[[ -n "${sealed_at:-}" ]] || {
  echo "Sealed universe ${universe_version} has no seal timestamp." >&2
  exit 1
}
[[ "${build_source_sha:-}" == "${release_source_sha}" ]] || {
  echo "Universe ${universe_version} was built from ${build_source_sha:-<none>}, not ${release_source_sha}." >&2
  exit 1
}

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-data-release.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT
manifest="${work_dir}/manifest.json"
archive="${work_dir}/data.tar.gz"
release="${work_dir}/release.json"
research_snapshot="${work_dir}/research_snapshot.json"
research_records="${work_dir}/research_records.json"
data_snapshot_dir="${work_dir}/data"

# Do not bind a manifest from a live tree and archive it later: a concurrent
# cache writer could make those two artifacts describe different data. Copy
# only regular files into a private snapshot and reject a file that changes
# while it is copied.
python3 - "${DATA_DIR}" "${data_snapshot_dir}" <<'PY'
import os
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2])
excluded = {
    "release_manifest.json",
    "release_metadata.json",
    "research_snapshot.json",
    "research_records.json",
}

for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
    relative = path.relative_to(source)
    relative_name = relative.as_posix()
    if relative_name in excluded:
        continue
    if path.is_symlink():
        raise SystemExit(f"Refusing to stage symbolic link: {relative_name}")
    destination = target / relative
    if path.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        continue
    if not path.is_file():
        raise SystemExit(f"Refusing to stage non-regular file: {relative_name}")
    before = path.stat()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise SystemExit(f"Data file changed while staging: {relative_name}")
    os.chmod(destination, 0o755 if before.st_mode & 0o111 else 0o644)
PY

coverage_report_rel="coverage_reports/${universe_version}.json"
coverage_report="${data_snapshot_dir}/${coverage_report_rel}"
[[ -f "${coverage_report}" ]] || {
  echo "Missing immutable coverage report for sealed universe ${universe_version}: ${coverage_report_rel}" >&2
  exit 1
}
python3 "${ROOT_DIR}/scripts/research_coverage_report.py" \
  --verify-report "${coverage_report}" \
  --universe-version "${universe_version}" \
  --expected-source-sha "${release_source_sha}" \
  --database-url "${DATABASE_URL}" \
  --data-dir "${data_snapshot_dir}" >/dev/null
coverage_report_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["report_sha256"])' "${coverage_report}")"

python3 "${ROOT_DIR}/scripts/create_data_manifest.py" \
  --data-dir "${data_snapshot_dir}" \
  --universe-version "${universe_version}" \
  --created-at "${sealed_at}" \
  --output "${manifest}" >/dev/null

manifest_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["manifest_sha256"])' "${manifest}")"
# A byte-stable archive is required for a resumable content-addressed release:
# ordinary tar/gzip records filesystem mtimes (and often the gzip timestamp),
# which would make an identical staged data tree appear to be a new artifact.
python3 - "${data_snapshot_dir}" "${archive}" <<'PY'
import gzip
import sys
import tarfile
from pathlib import Path

data_dir = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2])
paths = sorted(data_dir.rglob("*"), key=lambda path: path.relative_to(data_dir).as_posix())

with output.open("wb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as artifact:
            for path in paths:
                relative = path.relative_to(data_dir).as_posix()
                info = artifact.gettarinfo(str(path), arcname=relative)
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                if info.isdir():
                    info.mode = 0o755
                    artifact.addfile(info)
                else:
                    info.mode = 0o755 if (path.stat().st_mode & 0o111) else 0o644
                    with path.open("rb") as source:
                        artifact.addfile(info, source)
PY
archive_sha="$(checksum "${archive}")"

# Binding the data manifest is the one permitted post-seal metadata update.
# Re-staging exactly the same data is safe; changing its manifest is not.
bound_manifest_sha="$(
  psql "${PSQL_DATABASE_URL}" -X -A -t -v ON_ERROR_STOP=1 \
    -c "
      UPDATE universe_builds
         SET data_manifest_sha256 = '$(sql_literal "${manifest_sha}")'
       WHERE universe_version = '$(sql_literal "${universe_version}")'
         AND status = 'sealed'
         AND (
           data_manifest_sha256 IS NULL
           OR data_manifest_sha256 = '$(sql_literal "${manifest_sha}")'
         )
      RETURNING data_manifest_sha256;
    "
)"
[[ "${bound_manifest_sha}" == "${manifest_sha}" ]] || {
  echo "Universe ${universe_version} is already bound to a different data manifest." >&2
  exit 1
}
python3 "${ROOT_DIR}/scripts/research_snapshot.py" \
  --database-url "${DATABASE_URL}" \
  --universe-version "${universe_version}" \
  --output "${research_snapshot}" >/dev/null
database_snapshot_sha="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["snapshot_sha256"])' \
    "${research_snapshot}"
)"
python3 "${ROOT_DIR}/scripts/research_release.py" export \
  --database-url "${DATABASE_URL}" \
  --universe-version "${universe_version}" \
  --output "${research_records}" >/dev/null
research_records_sha="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["payload_sha256"])' \
    "${research_records}"
)"
release_uri="s3://${DATA_RELEASE_BUCKET}/${DATA_RELEASE_PREFIX}/${universe_version}/${manifest_sha}"

publish_immutable_file() {
  local source="$1"
  local key="$2"
  local source_sha existing_sha put_response retention
  source_sha="$(checksum "${source}")"
  PUBLISHED_OBJECT_VERSION_ID=""

  # Conditional creation eliminates the HEAD-then-PUT race. Object Lock on the
  # release bucket retains the resulting version; the checksum metadata makes
  # an interrupted publish safely resumable only when its bytes are identical.
  if put_response="$(aws s3api put-object \
    --bucket "${DATA_RELEASE_BUCKET}" \
    --key "${key}" \
    --body "${source}" \
    --if-none-match '*' \
    --server-side-encryption AES256 \
    --metadata "sha256=${source_sha}" \
    --output json)"; then
    PUBLISHED_OBJECT_VERSION_ID="$(
      printf '%s' "${put_response}" |
        python3 -c 'import json,sys; print(json.load(sys.stdin).get("VersionId", ""))'
    )"
  else
    existing_sha="$(
      aws s3api head-object \
        --bucket "${DATA_RELEASE_BUCKET}" \
        --key "${key}" \
        --query 'Metadata.sha256' \
        --output text 2>/dev/null || true
    )"
    if [[ "${existing_sha}" == "${source_sha}" ]]; then
      echo "Verified existing immutable object: s3://${DATA_RELEASE_BUCKET}/${key}"
      PUBLISHED_OBJECT_VERSION_ID="$(
        aws s3api head-object \
          --bucket "${DATA_RELEASE_BUCKET}" \
          --key "${key}" \
          --query 'VersionId' \
          --output text
      )"
    else
      echo "Refusing to replace immutable object: s3://${DATA_RELEASE_BUCKET}/${key}" >&2
      exit 1
    fi
  fi
  [[ -n "${PUBLISHED_OBJECT_VERSION_ID}" &&
    "${PUBLISHED_OBJECT_VERSION_ID}" != "None" &&
    "${PUBLISHED_OBJECT_VERSION_ID}" != "null" ]] || {
    echo "Release bucket did not return an S3 VersionId for ${key}." >&2
    exit 1
  }
  retention="$(
    aws s3api get-object-retention \
      --bucket "${DATA_RELEASE_BUCKET}" \
      --key "${key}" \
      --version-id "${PUBLISHED_OBJECT_VERSION_ID}" \
      --output json
  )"
  python3 - "${key}" "${retention}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[2])
retention = payload.get("Retention") or {}
if retention.get("Mode") != "COMPLIANCE" or not retention.get("RetainUntilDate"):
    raise SystemExit(
        f"Release object {sys.argv[1]} is not protected by COMPLIANCE Object Lock retention"
    )
PY
}

# Publish version-pinned payloads first. The descriptor is published only
# after it can name the immutable S3 version of every object it attests.
release_key_prefix="${DATA_RELEASE_PREFIX}/${universe_version}/${manifest_sha}"
publish_immutable_file "${archive}" "${release_key_prefix}/data.tar.gz"
archive_version_id="${PUBLISHED_OBJECT_VERSION_ID}"
publish_immutable_file "${research_snapshot}" "${release_key_prefix}/research_snapshot.json"
research_snapshot_version_id="${PUBLISHED_OBJECT_VERSION_ID}"
publish_immutable_file "${research_records}" "${release_key_prefix}/research_records.json"
research_records_version_id="${PUBLISHED_OBJECT_VERSION_ID}"
publish_immutable_file "${manifest}" "${release_key_prefix}/manifest.json"
manifest_version_id="${PUBLISHED_OBJECT_VERSION_ID}"

RELEASE_MANIFEST_SHA="${manifest_sha}" RELEASE_ARCHIVE_SHA="${archive_sha}" \
RELEASE_DATABASE_SNAPSHOT_SHA="${database_snapshot_sha}" \
RELEASE_RESEARCH_RECORDS_SHA="${research_records_sha}" \
RELEASE_UNIVERSE_VERSION="${universe_version}" RELEASE_SOURCE_SHA="${release_source_sha}" \
RELEASE_COVERAGE_REPORT_PATH="${coverage_report_rel}" \
RELEASE_COVERAGE_REPORT_SHA="${coverage_report_sha}" \
RELEASE_ARCHIVE_VERSION_ID="${archive_version_id}" \
RELEASE_RESEARCH_SNAPSHOT_VERSION_ID="${research_snapshot_version_id}" \
RELEASE_RESEARCH_RECORDS_VERSION_ID="${research_records_version_id}" \
RELEASE_MANIFEST_VERSION_ID="${manifest_version_id}" \
python3 - <<'PY' > "${release}"
import json
import os

print(json.dumps(
    {
        "schema_version": 3,
        "universe_version": os.environ["RELEASE_UNIVERSE_VERSION"],
        "manifest_sha256": os.environ["RELEASE_MANIFEST_SHA"],
        "archive_sha256": os.environ["RELEASE_ARCHIVE_SHA"],
        "database_snapshot_sha256": os.environ["RELEASE_DATABASE_SNAPSHOT_SHA"],
        "research_records_sha256": os.environ["RELEASE_RESEARCH_RECORDS_SHA"],
        "source_sha": os.environ["RELEASE_SOURCE_SHA"],
        "coverage_report": {
            "path": os.environ["RELEASE_COVERAGE_REPORT_PATH"],
            "sha256": os.environ["RELEASE_COVERAGE_REPORT_SHA"],
        },
        "object_versions": {
            "data.tar.gz": os.environ["RELEASE_ARCHIVE_VERSION_ID"],
            "research_snapshot.json": os.environ["RELEASE_RESEARCH_SNAPSHOT_VERSION_ID"],
            "research_records.json": os.environ["RELEASE_RESEARCH_RECORDS_VERSION_ID"],
            "manifest.json": os.environ["RELEASE_MANIFEST_VERSION_ID"],
        },
    },
    indent=2,
    sort_keys=True,
))
PY
release_descriptor_sha="$(checksum "${release}")"
publish_immutable_file "${release}" "${release_key_prefix}/release.json"
release_descriptor_version_id="${PUBLISHED_OBJECT_VERSION_ID}"

printf 'Staged immutable data release: %s\n' "${release_uri}"
printf 'DATA_RELEASE_DESCRIPTOR_SHA256=%s\n' "${release_descriptor_sha}"
printf 'DATA_RELEASE_DESCRIPTOR_VERSION_ID=%s\n' "${release_descriptor_version_id}"
printf 'DATA_RELEASE_COVERAGE_REPORT_SHA256=%s\n' "${coverage_report_sha}"
