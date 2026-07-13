#!/usr/bin/env bash
# Check a named immutable release's process, readiness, TLS, and release ID.
#
# Intended for the host-side systemd timer. It writes a secret-free evidence
# record and can notify an operator webhook when a required service is unhealthy.

set -Eeuo pipefail

RELEASE_ROOT="${RELEASE_ROOT:-/opt/rd-alpha}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-/etc/rd-alpha/prod.env}"
STATE_DIR="${STATE_DIR:-/var/lib/rd-alpha}"
EVIDENCE_FILE=""

usage() {
  cat <<'USAGE'
Usage: check_release_health.sh [options]

Options:
  --release-root <path>     Immutable release root (default: /opt/rd-alpha)
  --deploy-env-file <path>  Root-owned Compose environment file
  --state-dir <path>        Host state directory (default: /var/lib/rd-alpha)
  --evidence-file <path>    Override secret-free JSON evidence output path
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --deploy-env-file) DEPLOY_ENV_FILE="${2:-}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --evidence-file) EVIDENCE_FILE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "${DEPLOY_ENV_FILE}" ]] || {
  echo "Missing deployment environment file: ${DEPLOY_ENV_FILE}" >&2
  exit 1
}
release_dir="$(python3 - "${RELEASE_ROOT}/current" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).resolve())
PY
)"
[[ -d "${release_dir}" && -f "${release_dir}/deploy/docker-compose.yml" ]] || {
  echo "No active immutable release under ${RELEASE_ROOT}/current" >&2
  exit 1
}

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose (or docker-compose) is required" >&2
  exit 1
fi

env_value() {
  python3 - "${DEPLOY_ENV_FILE}" "$1" <<'PY'
import sys

path, expected = sys.argv[1:]
for raw in open(path):
    line = raw.rstrip("\n")
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key != expected:
        continue
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    print(value)
    break
PY
}

public_hostname="$(env_value PUBLIC_HOSTNAME)"
alert_webhook_url="$(env_value OPS_ALERT_WEBHOOK_URL)"
compose_file="${release_dir}/deploy/docker-compose.yml"
release_metadata="$(python3 - "${release_dir}/release.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
print(json.dumps({
    "release_version": f"{payload.get('source_sha', '')}-{payload.get('pipeline_id', '')}",
    "source_sha": payload.get("source_sha"),
    "pipeline_id": payload.get("pipeline_id"),
    "backend_image": payload.get("backend_image"),
    "frontend_image": payload.get("frontend_image"),
}, sort_keys=True))
PY
)"
evidence_dir="${STATE_DIR}/health-evidence"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_FILE="${EVIDENCE_FILE:-${evidence_dir}/${timestamp}.json}"
mkdir -p "${evidence_dir}"
chmod 0700 "${evidence_dir}"

failures_file="$(mktemp "${TMPDIR:-/tmp}/rd-alpha-health-failures.XXXXXX")"
services_file="$(mktemp "${TMPDIR:-/tmp}/rd-alpha-health-services.XXXXXX")"
trap 'rm -f "${failures_file}" "${services_file}"' EXIT

fail() {
  printf '%s\n' "$1" >> "${failures_file}"
}

check_service() {
  local service="$1"
  local needs_health="$2"
  local container state health
  container="$("${COMPOSE[@]}" --env-file "${DEPLOY_ENV_FILE}" -f "${compose_file}" ps -q "${service}" 2>/dev/null || true)"
  if [[ -z "${container}" ]]; then
    fail "${service}: no running container"
    printf '{"service":"%s","state":"missing","health":"missing"}\n' "${service}" >> "${services_file}"
    return
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${container}" 2>/dev/null || true)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container}" 2>/dev/null || true)"
  printf '{"service":"%s","state":"%s","health":"%s"}\n' \
    "${service}" "${state:-unknown}" "${health:-unknown}" >> "${services_file}"
  [[ "${state}" == "running" ]] || fail "${service}: state=${state:-unknown}"
  if [[ "${needs_health}" == "true" && "${health}" != "healthy" ]]; then
    fail "${service}: health=${health:-unknown}"
  elif [[ "${health}" == "unhealthy" ]]; then
    fail "${service}: health=unhealthy"
  fi
}

check_service postgres true
check_service redis true
check_service backend true
check_service worker true
check_service beat true
check_service frontend false

ready_json=""
if [[ -z "${public_hostname}" ]]; then
  fail "PUBLIC_HOSTNAME is missing"
else
  ready_json="$(curl --fail --silent --show-error --max-time 15 \
    "https://${public_hostname}/ready" 2>/dev/null || true)"
  if [[ -z "${ready_json}" ]]; then
    fail "public /ready request failed"
  elif ! python3 - "${ready_json}" "${release_metadata}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected = json.loads(sys.argv[2])
release = payload.get("release") or {}
runtime = release.get("runtime") or {}
expected_ref = f"{expected['source_sha']}-{expected['pipeline_id']}"
healthy = (
    payload.get("ready") is True
    and release.get("source_sha") == expected["source_sha"]
    and runtime.get("source_sha") == expected["source_sha"]
    and runtime.get("release_ref") == expected_ref
    and runtime.get("backend_image") == expected["backend_image"]
    and runtime.get("frontend_image") == expected["frontend_image"]
)
raise SystemExit(0 if healthy else 1)
PY
  then
    fail "public /ready did not attest the active immutable release identity"
  fi
fi

status="passed"
[[ -s "${failures_file}" ]] && status="failed"
python3 - "${EVIDENCE_FILE}" "${status}" "${release_metadata}" "${services_file}" "${failures_file}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

output, status, release, services_path, failures_path = sys.argv[1:]
services = [json.loads(line) for line in Path(services_path).read_text().splitlines() if line]
failures = [line for line in Path(failures_path).read_text().splitlines() if line]
payload = {
    "schema_version": 1,
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "release": json.loads(release),
    "services": services,
    "failures": failures,
}
target = Path(output)
target.parent.mkdir(parents=True, exist_ok=True)
temporary = target.with_name(f".{target.name}.tmp")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
temporary.replace(target)
PY

if [[ "${status}" == "failed" ]]; then
  if [[ -n "${alert_webhook_url}" ]]; then
    curl --fail --silent --show-error --max-time 15 \
      -H "Content-Type: application/json" \
      --data "{\"text\":\"Investor platform health check failed; inspect ${EVIDENCE_FILE}\"}" \
      "${alert_webhook_url}" >/dev/null || true
  fi
  echo "Release health check failed; evidence: ${EVIDENCE_FILE}" >&2
  exit 1
fi

echo "Release health check passed; evidence: ${EVIDENCE_FILE}"
