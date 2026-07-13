#!/usr/bin/env bash
# Exercise periodic release health evidence and worker-alert failure behavior.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/rd-alpha-health-test.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

fake_bin="${work_dir}/bin"
release_root="${work_dir}/releases"
state_dir="${work_dir}/state"
env_file="${work_dir}/prod.env"
release_dir="${release_root}/releases/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-42"
mkdir -p "${fake_bin}" "${release_dir}/deploy" "${state_dir}"
ln -s "${release_dir}" "${release_root}/current"
touch "${release_dir}/deploy/docker-compose.yml"
cat > "${release_dir}/release.json" <<'JSON'
{
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pipeline_id": 42,
  "backend_image": "registry.example/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "frontend_image": "registry.example/frontend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
JSON
cat > "${env_file}" <<'EOF'
PUBLIC_HOSTNAME=research.example.test
EOF

cat > "${fake_bin}/docker" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "compose" && "${2:-}" == "version" ]]; then
  exit 0
fi
if [[ "${1:-}" == "compose" ]]; then
  service="${!#}"
  [[ "${service}" != "ps" ]] || exit 2
  printf 'container-%s\n' "${service}"
  exit 0
fi
if [[ "${1:-}" == "inspect" ]]; then
  format="${3:-}"
  if [[ "${format}" == *"State.Status"* ]]; then
    printf 'running\n'
  else
    printf '%s\n' "${HEALTH_STATE:-healthy}"
  fi
  exit 0
fi
exit 2
SH
chmod +x "${fake_bin}/docker"

cat > "${fake_bin}/curl" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
source_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
if [[ "${HEALTH_BAD_ID:-}" == "1" ]]; then
  source_sha="cccccccccccccccccccccccccccccccccccccccc"
fi
printf '{"ready":true,"release":{"source_sha":"%s","runtime":{"source_sha":"%s","release_ref":"%s-42","backend_image":"registry.example/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","frontend_image":"registry.example/frontend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}}\n' \
  "${source_sha}" "${source_sha}" "${source_sha}"
SH
chmod +x "${fake_bin}/curl"

evidence="${work_dir}/passed.json"
PATH="${fake_bin}:${PATH}" \
  bash "${ROOT_DIR}/scripts/check_release_health.sh" \
  --release-root "${release_root}" \
  --deploy-env-file "${env_file}" \
  --state-dir "${state_dir}" \
  --evidence-file "${evidence}"

python3 - "${evidence}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
assert payload["status"] == "passed"
assert payload["release"]["release_version"].endswith("-42")
assert {item["service"] for item in payload["services"]} == {
    "postgres", "redis", "backend", "worker", "beat", "frontend"
}
PY

failed_evidence="${work_dir}/failed.json"
if PATH="${fake_bin}:${PATH}" HEALTH_STATE=unhealthy \
  bash "${ROOT_DIR}/scripts/check_release_health.sh" \
  --release-root "${release_root}" \
  --deploy-env-file "${env_file}" \
  --state-dir "${state_dir}" \
  --evidence-file "${failed_evidence}"; then
  echo "Health check unexpectedly accepted unhealthy containers." >&2
  exit 1
fi
python3 - "${failed_evidence}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
assert payload["status"] == "failed"
assert any("worker: health=unhealthy" == item for item in payload["failures"])
PY

bad_identity_evidence="${work_dir}/bad-identity.json"
if PATH="${fake_bin}:${PATH}" HEALTH_BAD_ID=1 \
  bash "${ROOT_DIR}/scripts/check_release_health.sh" \
  --release-root "${release_root}" \
  --deploy-env-file "${env_file}" \
  --state-dir "${state_dir}" \
  --evidence-file "${bad_identity_evidence}"; then
  echo "Health check unexpectedly accepted a mismatched runtime release." >&2
  exit 1
fi
python3 - "${bad_identity_evidence}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
assert payload["status"] == "failed"
assert "public /ready did not attest the active immutable release identity" in payload["failures"]
PY

echo "Release health evidence rehearsal passed."
