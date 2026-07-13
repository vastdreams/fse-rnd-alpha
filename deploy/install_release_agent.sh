#!/usr/bin/env bash
# Install the host-side GitLab release pull agent outside any release bundle.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_ROOT="/opt/rd-alpha"
STATE_DIR="/var/lib/rd-alpha"
DEPLOY_ENV_FILE="/etc/rd-alpha/prod.env"
AGENT_ENV_FILE="/etc/rd-alpha/release-agent.env"

usage() {
  cat <<'USAGE'
Usage: sudo deploy/install_release_agent.sh [options]

Options:
  --release-root <path>     Immutable release root (default: /opt/rd-alpha)
  --state-dir <path>        Agent state/backup root (default: /var/lib/rd-alpha)
  --deploy-env-file <path>  Root-owned production Compose environment file
                             (default: /etc/rd-alpha/prod.env)
  --agent-env-file <path>   Root-owned GitLab package credentials/config file
                             (default: /etc/rd-alpha/release-agent.env)

After installation, populate the two environment files, then promote a
specific GitLab release by SHA:

  sudo systemctl start rd-alpha-promote@<40-character-source-sha>-<GitLab-pipeline-id>
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --release-root)
      RELEASE_ROOT="${2:-}"
      shift 2
      ;;
    --state-dir)
      STATE_DIR="${2:-}"
      shift 2
      ;;
    --deploy-env-file)
      DEPLOY_ENV_FILE="${2:-}"
      shift 2
      ;;
    --agent-env-file)
      AGENT_ENV_FILE="${2:-}"
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

[[ "${EUID}" -eq 0 ]] || {
  echo "Run this installer as root." >&2
  exit 1
}

install -d -m 0755 "${RELEASE_ROOT}/releases"
install -d -m 0700 "${STATE_DIR}/release-records" "${STATE_DIR}/backups"
install -d -m 0700 "$(dirname "${AGENT_ENV_FILE}")" "$(dirname "${DEPLOY_ENV_FILE}")"
install -o root -g root -m 0750 \
  "${ROOT_DIR}/deploy/rd-alpha-release-agent.sh" \
  /usr/local/sbin/rd-alpha-release-agent

if [[ ! -f "${AGENT_ENV_FILE}" ]]; then
  cat > "${AGENT_ENV_FILE}" <<EOF
# Root-owned host-local GitLab package access. Do not commit this file.
RELEASE_BASE_URL=https://gitlab.com/api/v4/projects/REPLACE_PROJECT_ID/packages/generic/investor-platform
RELEASE_TOKEN=REPLACE_WITH_READ_ONLY_PACKAGE_TOKEN
RELEASE_AUTH_HEADER=PRIVATE-TOKEN
RELEASE_ROOT=${RELEASE_ROOT}
STATE_DIR=${STATE_DIR}
DEPLOY_ENV_FILE=${DEPLOY_ENV_FILE}
BACKUP_DIR=${STATE_DIR}/backups
# Set true on production only after configuring the immutable staging-proof URL.
REQUIRE_STAGING_PROOF=false
STAGING_PROOF_BASE_URL=https://gitlab.com/api/v4/projects/REPLACE_PROJECT_ID/packages/generic/investor-platform-proofs
EOF
  chmod 0600 "${AGENT_ENV_FILE}"
  chown root:root "${AGENT_ENV_FILE}"
fi

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  cat > "${DEPLOY_ENV_FILE}" <<'EOF'
# Root-owned target configuration. Copy the reviewed deploy/.env.example values
# here and fill target-specific secrets, URLs, DATA_DIR, CERTS_DIR, and
# CERTBOT_WEBROOT. Do not place release image references in this file.
EOF
  chmod 0600 "${DEPLOY_ENV_FILE}"
  chown root:root "${DEPLOY_ENV_FILE}"
fi

cat > /etc/systemd/system/rd-alpha-promote@.service <<EOF
[Unit]
Description=Promote immutable R&D Alpha release %i
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
Environment=RD_ALPHA_RELEASE_AGENT_ENV=${AGENT_ENV_FILE}
ExecStart=/usr/local/sbin/rd-alpha-release-agent %i
EOF

cat > /etc/systemd/system/rd-alpha-healthcheck.service <<EOF
[Unit]
Description=Verify investor platform release health and worker liveness
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=${RELEASE_ROOT}/current/scripts/check_release_health.sh --release-root ${RELEASE_ROOT} --deploy-env-file ${DEPLOY_ENV_FILE} --state-dir ${STATE_DIR}
EOF

cat > /etc/systemd/system/rd-alpha-healthcheck.timer <<'EOF'
[Unit]
Description=Run investor platform release health check every five minutes

[Timer]
OnBootSec=3m
OnUnitActiveSec=5m
RandomizedDelaySec=30s
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/rd-alpha-offsite-backup.service <<EOF
[Unit]
Description=Create encrypted off-host investor platform PostgreSQL backup
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=${RELEASE_ROOT}/current/scripts/backup_postgres_offsite.sh --release-root ${RELEASE_ROOT} --deploy-env-file ${DEPLOY_ENV_FILE} --state-dir ${STATE_DIR}
EOF

cat > /etc/systemd/system/rd-alpha-offsite-backup.timer <<'EOF'
[Unit]
Description=Run encrypted investor platform PostgreSQL backup daily

[Timer]
OnCalendar=*-*-* 02:35:00 UTC
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now rd-alpha-healthcheck.timer
systemctl enable --now rd-alpha-offsite-backup.timer

echo "Installed rd-alpha release agent."
echo "Populate ${AGENT_ENV_FILE} and ${DEPLOY_ENV_FILE}, then start rd-alpha-promote@<sha>-<pipeline-id>."
