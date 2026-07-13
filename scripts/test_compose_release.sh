#!/usr/bin/env bash
# Rehearse the production Compose/Nginx boundary with immutable local images.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/deploy/docker-compose.yml"
BACKEND_IMAGE="${BACKEND_IMAGE:-rd-alpha-backend:release-gate}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-rd-alpha-frontend:release-gate}"
project_name="rd-alpha-release-gate-${RANDOM}${RANDOM}"
# GitLab's Docker-in-Docker daemon can bind-mount only paths shared with the
# job service. CI sets RELEASE_GATE_WORK_DIR to its checkout; local runs keep
# isolated fixtures under /tmp.
work_parent="${RELEASE_GATE_WORK_DIR:-${TMPDIR:-/tmp}}"
mkdir -p "${work_parent}"
work_dir="$(mktemp -d "${work_parent%/}/rd-alpha-compose-gate.XXXXXX")"
env_file="${work_dir}/compose.env"
data_dir="${work_dir}/data"
cert_dir="${work_dir}/certs"
acme_dir="${work_dir}/certbot-webroot"

compose() {
  docker compose --project-name "${project_name}" --env-file "${env_file}" -f "${COMPOSE_FILE}" "$@"
}

cleanup() {
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf "${work_dir}"
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || {
  echo "docker is required for the Compose release rehearsal" >&2
  exit 1
}
docker info >/dev/null

if ! docker image inspect "${BACKEND_IMAGE}" >/dev/null 2>&1; then
  docker build -t "${BACKEND_IMAGE}" "${ROOT_DIR}/backend"
fi
if ! docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1; then
  docker build -f "${ROOT_DIR}/deploy/Dockerfile.frontend" -t "${FRONTEND_IMAGE}" "${ROOT_DIR}"
fi

release_gate_host="release-gate.test"
release_gate_universe="release_gate_universe"
release_gate_source_sha="$(printf 'b%.0s' {1..40})"
# Docker-in-Docker publishes ports on the daemon service rather than the CI
# job container. Local Docker continues to use loopback by default.
release_gate_connect_host="${RELEASE_GATE_CONNECT_HOST:-127.0.0.1}"

gate_curl() {
  local port="$1"
  shift
  curl --connect-to "${release_gate_host}:${port}:${release_gate_connect_host}:${port}" "$@"
}

mkdir -p "${data_dir}/saas_ai_repricing" "${cert_dir}" "${acme_dir}"
chmod 0777 "${data_dir}"
printf 'fundamental release gate fixture\n' > "${data_dir}/saas_ai_repricing/fundamental_value_run.csv"
printf 'overlay release gate fixture\n' > "${data_dir}/saas_ai_repricing/first_principles_overlay.csv"
python3 "${ROOT_DIR}/scripts/create_data_manifest.py" \
  --data-dir "${data_dir}" \
  --universe-version "${release_gate_universe}" \
  --created-at "2026-07-13T00:00:00.000000Z" \
  --output "${data_dir}/release_manifest.json" >/dev/null
release_gate_manifest_sha="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["manifest_sha256"])' \
    "${data_dir}/release_manifest.json"
)"
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "${cert_dir}/privkey.pem" \
  -out "${cert_dir}/fullchain.pem" \
  -subj "/CN=${release_gate_host}" \
  -days 1 >/dev/null 2>&1

cat > "${env_file}" <<EOF
BACKEND_IMAGE=${BACKEND_IMAGE}
FRONTEND_IMAGE=${FRONTEND_IMAGE}
POSTGRES_PASSWORD=release-gate-postgres-password
BACKEND_DATABASE_URL=postgresql+asyncpg://postgres:release-gate-postgres-password@postgres:5432/rd_alpha
SECRET_KEY=release-gate-secret-key-at-least-32-characters
SEC_USER_AGENT="Release Gate release-gate@example.test"
DATA_DIR=${data_dir}
CERTS_DIR=${cert_dir}
CERTBOT_WEBROOT=${acme_dir}
PUBLIC_HOSTNAME=${release_gate_host}
AUTH_PUBLIC_REGISTRATION=false
AUTH_REQUIRE_EMAIL_VERIFICATION=false
AUTH_RESET_URL=https://${release_gate_host}:18443/reset-password
AUTH_VERIFY_URL=https://${release_gate_host}:18443/verify-email
STRIPE_SUCCESS_URL=https://${release_gate_host}:18443/donate?success=true
STRIPE_CANCEL_URL=https://${release_gate_host}:18443/donate?canceled=true
RELEASE_SHA=${release_gate_source_sha}
RELEASE_REF=${release_gate_source_sha}-release-gate
HTTP_PORT=18080
HTTPS_PORT=18443
EOF

# Export exactly the generated non-secret rehearsal environment rather than
# relying on a local deploy/.env.
set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a

compose config -q
compose up -d postgres redis

for _ in $(seq 1 45); do
  if compose exec -T postgres pg_isready -U postgres -d rd_alpha >/dev/null; then
    break
  fi
  sleep 2
done
compose exec -T postgres pg_isready -U postgres -d rd_alpha >/dev/null

# Match deploy_release.sh: baseline schema first, then the checksum-verified
# migration ledger, and only then start application processes.
compose run --rm --no-deps backend \
  python -c "import asyncio; from app.db.session import create_tables; asyncio.run(create_tables())"
COMPOSE_FILE="${COMPOSE_FILE}" \
  COMPOSE_ENV_FILE="${env_file}" \
  COMPOSE_PROJECT_NAME="${project_name}" \
  "${ROOT_DIR}/scripts/run_migrations.sh"
compose exec -T postgres psql -U postgres -d rd_alpha -v ON_ERROR_STOP=1 <<SQL
INSERT INTO universe_builds (
    universe_version, input_sha256, manifest, engine_version, status, sealed_at, is_active,
    source_sha, data_manifest_sha256
) VALUES (
    '${release_gate_universe}',
    repeat('a', 64),
    '{}'::jsonb,
    'release-gate',
    'building',
    NULL,
    false,
    repeat('b', 40),
    NULL
);
INSERT INTO metric_vectors (
    ticker, universe_version, vector, completeness_grade, kill_active, stale
) VALUES (
    'GATE',
    '${release_gate_universe}',
    '{}'::jsonb,
    'Incomplete',
    false,
    false
);
SELECT materialize_universe_evidence_refs('${release_gate_universe}');
UPDATE universe_builds
   SET status = 'sealed',
       sealed_at = CURRENT_TIMESTAMP,
       data_manifest_sha256 = '${release_gate_manifest_sha}',
       is_active = true
 WHERE universe_version = '${release_gate_universe}';
SQL

compose up -d backend worker beat frontend

for _ in $(seq 1 45); do
  ready="$(
    gate_curl 18443 -k -fsS "https://${release_gate_host}:18443/ready" || true
  )"
  if rg -q '"ready":true' <<< "${ready}"; then
    break
  fi
  sleep 2
done
if ! rg -q '"ready":true' <<< "${ready}"; then
  echo "Gateway did not become ready; retaining container diagnostics in the CI log." >&2
  compose ps >&2 || true
  compose logs --no-color backend frontend worker beat >&2 || true
  exit 1
fi

redirect_headers="$(
  gate_curl 18080 -sSI "http://${release_gate_host}:18080/ready"
)"
rg -q '^HTTP/.* 301' <<< "${redirect_headers}"
rg -q "^location: https://${release_gate_host}/ready" <<< "$(tr '[:upper:]' '[:lower:]' <<< "${redirect_headers}")"
https_headers="$(
  gate_curl 18443 -k -sSI "https://${release_gate_host}:18443/ready"
)"
rg -qi '^strict-transport-security:' <<< "${https_headers}"
rg -qi '^content-security-policy:' <<< "${https_headers}"
legacy_headers="$(
  gate_curl 18443 -k -sSI \
    "https://${release_gate_host}:18443/portfolio/saas/GATE?universe_version=${release_gate_universe}"
)"
rg -q '^HTTP/.* 308' <<< "${legacy_headers}"
rg -q "^location: /app/company/gate?universe_version=${release_gate_universe}" \
  <<< "$(tr '[:upper:]' '[:lower:]' <<< "${legacy_headers}")"

admin_login_statuses=()
for _ in $(seq 1 12); do
  admin_login_statuses+=("$(
    gate_curl 18443 -k \
      -o /dev/null -sS -w '%{http_code}' \
      -H 'Content-Type: application/json' \
      --data '{"email":"admin@example.test","password":"invalid"}' \
      "https://${release_gate_host}:18443/api/admin/login"
  )")
done
[[ " ${admin_login_statuses[*]} " == *" 429 "* ]] || {
  echo "Admin login did not receive the credential rate limit." >&2
  exit 1
}

gate_curl 18443 -k -fsS "https://${release_gate_host}:18443/health" |
  python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "healthy"'
gate_curl 18443 -k -fsS "https://${release_gate_host}:18443/ready" |
  python3 -c 'import json,sys; payload=json.load(sys.stdin); assert payload["ready"] is True; assert payload["checks"]["database"] == "ok"; assert payload["checks"]["investor_schema"] == "ok"; assert payload["checks"]["migration_ledger"] == "ok"; assert payload["checks"]["research_integrity_triggers"] == "ok"; assert payload["checks"]["runtime_release"] == "ok"; assert payload["release"]["runtime"]["source_sha"] == sys.argv[1]' "${release_gate_source_sha}"
gate_curl 18443 -k -fsS "https://${release_gate_host}:18443/api/health" |
  python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "healthy"'
compose exec -T frontend nginx -t

for service in worker beat; do
  for _ in $(seq 1 45); do
    container_id="$(compose ps -q "${service}")"
    if [[ -n "${container_id}" ]] &&
      [[ "$(docker inspect --format '{{.State.Health.Status}}' "${container_id}")" == "healthy" ]]; then
      break
    fi
    sleep 2
  done
  container_id="$(compose ps -q "${service}")"
  test -n "${container_id}"
  test "$(docker inspect --format '{{.State.Health.Status}}' "${container_id}")" = "healthy"
done

echo "Compose/Nginx release rehearsal passed."
