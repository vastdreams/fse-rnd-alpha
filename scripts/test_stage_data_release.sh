#!/usr/bin/env bash
# Exercise sealed-source/data binding in stage_data_release.sh without AWS.

set -Eeuo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-stage-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

repo="${work_dir}/repo"
fake_bin="${work_dir}/bin"
fake_s3="${work_dir}/s3"
mkdir -p "${repo}/scripts" "${repo}/data/saas_ai_repricing" "${fake_bin}" "${fake_s3}"
cp \
  "${SOURCE_ROOT}/scripts/stage_data_release.sh" \
  "${SOURCE_ROOT}/scripts/create_data_manifest.py" \
  "${SOURCE_ROOT}/scripts/research_snapshot.py" \
  "${SOURCE_ROOT}/scripts/research_release.py" \
  "${repo}/scripts/"
chmod +x "${repo}/scripts/stage_data_release.sh"

printf 'fundamental fixture\n' > "${repo}/data/saas_ai_repricing/fundamental_value_run.csv"
printf 'overlay fixture\n' > "${repo}/data/saas_ai_repricing/first_principles_overlay.csv"
printf 'cache fixture\n' > "${repo}/data/price-cache.json"

git -C "${repo}" init -q
git -C "${repo}" add .
git -C "${repo}" -c user.name=release-test -c user.email=release-test@example.test \
  commit -qm "fixture"
source_sha="$(git -C "${repo}" rev-parse HEAD)"
universe_version="univ_stage_fixture"

cat > "${fake_bin}/psql" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

command_text=""
for ((index = 1; index <= $#; index += 1)); do
  if [[ "${!index}" == "-c" ]]; then
    next=$((index + 1))
    command_text="${!next}"
    break
  fi
done

if [[ -z "${command_text}" ]]; then
  # research_snapshot.py supplies its SQL on stdin.
  cat >/dev/null
  printf '{"universe_build":{"universe_version":"%s","status":"sealed","source_sha":"%s"},"tables":{}}\n' \
    "${FAKE_UNIVERSE_VERSION}" "${FAKE_BUILD_SOURCE_SHA}"
elif [[ "${command_text}" == *"SELECT status"* ]]; then
  printf 'sealed\t%s\t2026-07-13T00:00:00.000000Z\n' "${FAKE_BUILD_SOURCE_SHA}"
elif [[ "${command_text}" == *"UPDATE universe_builds"* ]]; then
  manifest_sha="$(
    printf '%s' "${command_text}" |
      tr '\n' ' ' |
      sed -nE "s/.*data_manifest_sha256 = '([0-9a-f]{64})'.*/\\1/p"
  )"
  [[ "${manifest_sha}" =~ ^[0-9a-f]{64}$ ]]
  printf '%s\n' "${manifest_sha}"
else
  echo "Unexpected fake psql query: ${command_text}" >&2
  exit 2
fi
SH
chmod +x "${fake_bin}/psql"

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
    body=""
    metadata=""
    query=""
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --bucket) bucket="$2"; shift 2 ;;
        --key) key="$2"; shift 2 ;;
        --body) body="$2"; shift 2 ;;
        --metadata) metadata="$2"; shift 2 ;;
        --query) query="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    target="${root}/${bucket}/${key}"
    case "${command}" in
      put-object)
        [[ -n "${body}" && -f "${body}" ]]
        [[ ! -e "${target}" ]] || exit 1
        mkdir -p "$(dirname "${target}")"
        cp "${body}" "${target}"
        printf '%s\n' "${metadata#sha256=}" > "${target}.sha256meta"
        version="fixture-$(printf '%s' "${key}" | shasum -a 256 | awk '{print substr($1, 1, 16)}')"
        printf '%s\n' "${version}" > "${target}.version"
        printf '{"VersionId":"%s"}\n' "${version}"
        ;;
      head-object)
        [[ -f "${target}" ]]
        if [[ "${query}" == "Metadata.sha256" ]]; then
          cat "${target}.sha256meta"
        elif [[ "${query}" == "VersionId" ]]; then
          cat "${target}.version"
        fi
        ;;
      get-object-retention)
        [[ -f "${target}" ]]
        printf '{"Retention":{"Mode":"%s","RetainUntilDate":"2030-01-01T00:00:00Z"}}\n' \
          "${FAKE_OBJECT_LOCK_MODE:-COMPLIANCE}"
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

real_python3="$(command -v python3)"
cat > "${fake_bin}/python3" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == */research_release.py && "${2:-}" == "export" ]]; then
  output=""
  shift 2
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --output) output="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  [[ -n "${output}" ]]
  printf '{"schema_version":1,"payload_sha256":"%s"}\n' \
    "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" > "${output}"
  exit 0
fi

exec "${REAL_PYTHON3:?}" "$@"
SH
chmod +x "${fake_bin}/python3"

stage_output="$(
  cd "${repo}"
  PATH="${fake_bin}:${PATH}" \
    FAKE_S3_ROOT="${fake_s3}" \
    FAKE_UNIVERSE_VERSION="${universe_version}" \
    FAKE_BUILD_SOURCE_SHA="${source_sha}" \
    REAL_PYTHON3="${real_python3}" \
    DATABASE_URL="postgresql://fixture" \
    DATA_RELEASE_BUCKET="fixture-bucket" \
    ./scripts/stage_data_release.sh --universe-version "${universe_version}"
)"
release_uri="$(printf '%s\n' "${stage_output}" | awk '/^Staged immutable data release:/ {print $NF}')"
[[ "${release_uri}" == s3://fixture-bucket/* ]]
release_path="${fake_s3}/${release_uri#s3://}"
[[ -f "${release_path}/manifest.json" ]]
[[ -f "${release_path}/data.tar.gz" ]]
[[ -f "${release_path}/research_snapshot.json" ]]
[[ -f "${release_path}/research_records.json" ]]
[[ -f "${release_path}/release.json" ]]
release_descriptor_sha="$(shasum -a 256 "${release_path}/release.json" | awk '{print $1}')"
[[ "${stage_output}" == *"DATA_RELEASE_DESCRIPTOR_SHA256=${release_descriptor_sha}"* ]]

python3 - "${release_path}/release.json" "${source_sha}" "${universe_version}" <<'PY'
import json
import sys

release = json.load(open(sys.argv[1]))
assert release["source_sha"] == sys.argv[2]
assert release["universe_version"] == sys.argv[3]
assert len(release["manifest_sha256"]) == 64
assert len(release["database_snapshot_sha256"]) == 64
assert len(release["research_records_sha256"]) == 64
assert release["schema_version"] == 2
assert set(release["object_versions"]) == {
    "data.tar.gz",
    "manifest.json",
    "research_records.json",
    "research_snapshot.json",
}
assert all(release["object_versions"].values())
PY

# A retry must use conditional puts and accept only the already-staged exact
# bytes, not replace an object after a HEAD/PUT race.
retry_output="$(
  cd "${repo}"
  PATH="${fake_bin}:${PATH}" \
    FAKE_S3_ROOT="${fake_s3}" \
    FAKE_UNIVERSE_VERSION="${universe_version}" \
    FAKE_BUILD_SOURCE_SHA="${source_sha}" \
    REAL_PYTHON3="${real_python3}" \
    DATABASE_URL="postgresql://fixture" \
    DATA_RELEASE_BUCKET="fixture-bucket" \
    ./scripts/stage_data_release.sh --universe-version "${universe_version}"
)"
[[ "${retry_output}" == *"Verified existing immutable object:"* ]]

if (
  cd "${repo}"
  PATH="${fake_bin}:${PATH}" \
    FAKE_S3_ROOT="${fake_s3}" \
    FAKE_UNIVERSE_VERSION="${universe_version}" \
    FAKE_BUILD_SOURCE_SHA="${source_sha}" \
    FAKE_OBJECT_LOCK_MODE="GOVERNANCE" \
    REAL_PYTHON3="${real_python3}" \
    DATABASE_URL="postgresql://fixture" \
    DATA_RELEASE_BUCKET="fixture-bucket" \
    ./scripts/stage_data_release.sh --universe-version "${universe_version}"
); then
  echo "Stage unexpectedly accepted non-COMPLIANCE Object Lock retention." >&2
  exit 1
fi

printf '%s\n' "$(printf '0%.0s' {1..64})" > "${release_path}/release.json.sha256meta"
if (
  cd "${repo}"
  PATH="${fake_bin}:${PATH}" \
    FAKE_S3_ROOT="${fake_s3}" \
    FAKE_UNIVERSE_VERSION="${universe_version}" \
    FAKE_BUILD_SOURCE_SHA="${source_sha}" \
    REAL_PYTHON3="${real_python3}" \
    DATABASE_URL="postgresql://fixture" \
    DATA_RELEASE_BUCKET="fixture-bucket" \
    ./scripts/stage_data_release.sh --universe-version "${universe_version}"
); then
  echo "Stage unexpectedly replaced an existing immutable release object." >&2
  exit 1
fi

if (
  cd "${repo}"
  PATH="${fake_bin}:${PATH}" \
    FAKE_S3_ROOT="${fake_s3}" \
    FAKE_UNIVERSE_VERSION="${universe_version}" \
    FAKE_BUILD_SOURCE_SHA="${source_sha}" \
    REAL_PYTHON3="${real_python3}" \
    DATABASE_URL="postgresql://fixture" \
    DATA_RELEASE_BUCKET="fixture-bucket" \
    ./scripts/stage_data_release.sh \
      --universe-version "${universe_version}" \
      --source-sha "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
); then
  echo "Stage unexpectedly accepted a mismatched source SHA." >&2
  exit 1
fi

echo "Immutable data staging rehearsal passed."
