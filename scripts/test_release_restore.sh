#!/usr/bin/env bash
# Exercise the immutable-release restore path without AWS credentials.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-release-restore-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

fake_bin="${work_dir}/bin"
fake_s3="${work_dir}/s3"
artifact_dir="${work_dir}/artifact"
source_data="${work_dir}/source-data"
target_data="${work_dir}/target-data"
mkdir -p "${fake_bin}" "${fake_s3}" "${artifact_dir}" \
  "${source_data}/saas_ai_repricing" "${target_data}"

cat > "${fake_bin}/aws" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

root="${FAKE_S3_ROOT:?}"
case "${1:-}" in
  s3api)
    command="${2:-}"
    shift 2
    bucket=""
    key=""
    version_id=""
    destination=""
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --bucket) bucket="$2"; shift 2 ;;
        --key) key="$2"; shift 2 ;;
        --version-id) version_id="$2"; shift 2 ;;
        --output) shift 2 ;;
        *) destination="$1"; shift ;;
      esac
    done
    case "${command}" in
      head-object)
        [[ -f "${root}/${bucket}/${key}" ]]
        ;;
      get-object)
        [[ -n "${version_id}" && -n "${destination}" ]]
        source="${root}/versions/${bucket}/${key}/${version_id}"
        [[ -f "${source}" ]]
        mkdir -p "$(dirname "${destination}")"
        cp "${source}" "${destination}"
        ;;
      *)
        exit 2
        ;;
    esac
    ;;
  s3)
    [[ "${2:-}" == "cp" ]] || exit 2
    source="$3"
    destination="$4"
    map_uri() {
      local value="$1"
      if [[ "${value}" == s3://* ]]; then
        printf '%s/%s' "${root}" "${value#s3://}"
      else
        printf '%s' "${value}"
      fi
    }
    source="$(map_uri "${source}")"
    destination="$(map_uri "${destination}")"
    mkdir -p "$(dirname "${destination}")"
    cp "${source}" "${destination}"
    ;;
  *)
    exit 2
    ;;
esac
SH
chmod +x "${fake_bin}/aws"

printf 'fundamental fixture\n' > "${source_data}/saas_ai_repricing/fundamental_value_run.csv"
printf 'overlay fixture\n' > "${source_data}/saas_ai_repricing/first_principles_overlay.csv"
printf 'new cache payload\n' > "${source_data}/price-cache.json"
printf 'prior release\n' > "${target_data}/prior.txt"

universe_version="univ_restore_fixture"
source_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
manifest="${artifact_dir}/manifest.json"
archive="${artifact_dir}/data.tar.gz"
snapshot="${artifact_dir}/research_snapshot.json"
records="${artifact_dir}/research_records.json"
release="${artifact_dir}/release.json"

python3 "${ROOT_DIR}/scripts/create_data_manifest.py" \
  --data-dir "${source_data}" \
  --universe-version "${universe_version}" \
  --created-at "2026-07-13T00:00:00.000000Z" \
  --output "${manifest}" >/dev/null
tar -C "${source_data}" -czf "${archive}" .

UNIVERSE_VERSION="${universe_version}" SOURCE_SHA="${source_sha}" \
python3 - <<'PY' > "${snapshot}"
import hashlib
import json
import os

document = {
    "schema_version": 1,
    "universe_version": os.environ["UNIVERSE_VERSION"],
    "snapshot": {
        "universe_build": {
            "universe_version": os.environ["UNIVERSE_VERSION"],
            "status": "sealed",
            "source_sha": os.environ["SOURCE_SHA"],
        },
        "tables": {},
    },
}
document["snapshot_sha256"] = hashlib.sha256(
    json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
print(json.dumps(document, sort_keys=True))
PY

MANIFEST="${manifest}" SNAPSHOT="${snapshot}" UNIVERSE_VERSION="${universe_version}" \
SOURCE_SHA="${source_sha}" python3 - <<'PY' > "${records}"
import hashlib
import json
import os
from pathlib import Path

manifest = json.loads(Path(os.environ["MANIFEST"]).read_text())
snapshot = json.loads(Path(os.environ["SNAPSHOT"]).read_text())
document = {
    "schema_version": 1,
    "universe_version": os.environ["UNIVERSE_VERSION"],
    "source_sha": os.environ["SOURCE_SHA"],
    "data_manifest_sha256": manifest["manifest_sha256"],
    "database_snapshot_sha256": snapshot["snapshot_sha256"],
    "builds": [],
    "tables": {},
}
document["payload_sha256"] = hashlib.sha256(
    json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
print(json.dumps(document, sort_keys=True))
PY

MANIFEST="${manifest}" ARCHIVE="${archive}" SNAPSHOT="${snapshot}" RECORDS="${records}" \
UNIVERSE_VERSION="${universe_version}" SOURCE_SHA="${source_sha}" \
python3 - <<'PY' > "${release}"
import hashlib
import json
import os
from pathlib import Path

manifest = json.loads(Path(os.environ["MANIFEST"]).read_text())
snapshot = json.loads(Path(os.environ["SNAPSHOT"]).read_text())
records = json.loads(Path(os.environ["RECORDS"]).read_text())
print(json.dumps(
    {
        "schema_version": 1,
        "universe_version": os.environ["UNIVERSE_VERSION"],
        "manifest_sha256": manifest["manifest_sha256"],
        "archive_sha256": hashlib.sha256(Path(os.environ["ARCHIVE"]).read_bytes()).hexdigest(),
        "database_snapshot_sha256": snapshot["snapshot_sha256"],
        "research_records_sha256": records["payload_sha256"],
        "source_sha": os.environ["SOURCE_SHA"],
    },
    sort_keys=True,
))
PY

bucket="fixture-bucket"
prefix="investor-platform-data/${universe_version}/$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["manifest_sha256"])' "${manifest}")"
mkdir -p "${fake_s3}/${bucket}/${prefix}"
cp "${manifest}" "${archive}" "${snapshot}" "${records}" "${release}" "${fake_s3}/${bucket}/${prefix}/"
release_descriptor_sha="$(shasum -a 256 "${release}" | awk '{print $1}')"

PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  DATA_RELEASE_URI="s3://${bucket}/${prefix}" \
  EXPECTED_SOURCE_SHA="${source_sha}" \
  EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="${release_descriptor_sha}" \
  DATA_DIR="${target_data}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"

[[ -f "${target_data}/price-cache.json" ]]
[[ -f "${target_data}/research_records.json" ]]
[[ ! -f "${target_data}/prior.txt" ]]
compgen -G "${target_data}.previous-*/prior.txt" >/dev/null

# Schema-v2 descriptors bind each payload to its S3 VersionId. Prove that an
# unversioned object overwrite cannot alter the restored tree.
versioned_target="${work_dir}/versioned-target"
versioned_prefix="investor-platform-data/${universe_version}/versioned-fixture"
versioned_release="${artifact_dir}/release-v2.json"
archive_version="archive-v1"
manifest_version="manifest-v1"
snapshot_version="snapshot-v1"
records_version="records-v1"
MANIFEST="${manifest}" ARCHIVE="${archive}" SNAPSHOT="${snapshot}" RECORDS="${records}" \
UNIVERSE_VERSION="${universe_version}" SOURCE_SHA="${source_sha}" \
ARCHIVE_VERSION="${archive_version}" MANIFEST_VERSION="${manifest_version}" \
SNAPSHOT_VERSION="${snapshot_version}" RECORDS_VERSION="${records_version}" \
python3 - <<'PY' > "${versioned_release}"
import hashlib
import json
import os
from pathlib import Path

manifest = json.loads(Path(os.environ["MANIFEST"]).read_text())
snapshot = json.loads(Path(os.environ["SNAPSHOT"]).read_text())
records = json.loads(Path(os.environ["RECORDS"]).read_text())
print(json.dumps(
    {
        "schema_version": 2,
        "universe_version": os.environ["UNIVERSE_VERSION"],
        "manifest_sha256": manifest["manifest_sha256"],
        "archive_sha256": hashlib.sha256(Path(os.environ["ARCHIVE"]).read_bytes()).hexdigest(),
        "database_snapshot_sha256": snapshot["snapshot_sha256"],
        "research_records_sha256": records["payload_sha256"],
        "source_sha": os.environ["SOURCE_SHA"],
        "object_versions": {
            "data.tar.gz": os.environ["ARCHIVE_VERSION"],
            "manifest.json": os.environ["MANIFEST_VERSION"],
            "research_snapshot.json": os.environ["SNAPSHOT_VERSION"],
            "research_records.json": os.environ["RECORDS_VERSION"],
        },
    },
    sort_keys=True,
))
PY
mkdir -p "${fake_s3}/${bucket}/${versioned_prefix}"
cp "${versioned_release}" "${fake_s3}/${bucket}/${versioned_prefix}/release.json"
for spec in \
  "data.tar.gz:${archive}:${archive_version}" \
  "manifest.json:${manifest}:${manifest_version}" \
  "research_snapshot.json:${snapshot}:${snapshot_version}" \
  "research_records.json:${records}:${records_version}"; do
  IFS=: read -r name source version <<< "${spec}"
  mkdir -p "${fake_s3}/versions/${bucket}/${versioned_prefix}/${name}"
  cp "${source}" "${fake_s3}/versions/${bucket}/${versioned_prefix}/${name}/${version}"
  printf 'unversioned replacement\n' > "${fake_s3}/${bucket}/${versioned_prefix}/${name}"
done
versioned_descriptor_sha="$(shasum -a 256 "${versioned_release}" | awk '{print $1}')"
PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  DATA_RELEASE_URI="s3://${bucket}/${versioned_prefix}" \
  EXPECTED_SOURCE_SHA="${source_sha}" \
  EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="${versioned_descriptor_sha}" \
  DATA_DIR="${versioned_target}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"
[[ -f "${versioned_target}/price-cache.json" ]]
[[ -f "${versioned_target}/research_records.json" ]]

if PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  DATA_RELEASE_URI="s3://${bucket}/${prefix}" \
  EXPECTED_SOURCE_SHA="${source_sha}" \
  EXPECTED_DATA_RELEASE_DESCRIPTOR_SHA256="$(printf '0%.0s' {1..64})" \
  DATA_DIR="${target_data}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"; then
  echo "Restore unexpectedly accepted a mismatched release descriptor." >&2
  exit 1
fi
[[ -f "${target_data}/price-cache.json" ]]

if PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  DATA_RELEASE_URI="s3://${bucket}/${prefix}" \
  EXPECTED_SOURCE_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" \
  DATA_DIR="${target_data}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"; then
  echo "Restore unexpectedly accepted a mismatched source SHA." >&2
  exit 1
fi
[[ -f "${target_data}/price-cache.json" ]]

python3 - "${fake_s3}/${bucket}/${prefix}/research_snapshot.json" <<'PY'
import json
import sys

path = sys.argv[1]
payload = json.load(open(path))
payload["snapshot"]["tables"]["tampered"] = {"rows": 1}
open(path, "w").write(json.dumps(payload))
PY
if PATH="${fake_bin}:${PATH}" FAKE_S3_ROOT="${fake_s3}" \
  DATA_RELEASE_URI="s3://${bucket}/${prefix}" \
  EXPECTED_SOURCE_SHA="${source_sha}" \
  DATA_DIR="${target_data}" \
  "${ROOT_DIR}/scripts/restore_data_release.sh"; then
  echo "Restore unexpectedly accepted tampered release metadata." >&2
  exit 1
fi
[[ -f "${target_data}/price-cache.json" ]]

echo "Immutable release restore rehearsal passed."
