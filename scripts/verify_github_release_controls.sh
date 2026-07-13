#!/usr/bin/env bash
# Verify the GitHub-side controls that cannot be represented solely in a
# workflow file: protected main, separate release environments, approvals, and
# environment-scoped deployment inputs. This is read-only.

set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/verify_github_release_controls.sh [--repo OWNER/REPOSITORY]

Requires an authenticated GitHub CLI token with repository administration,
Actions variables/secrets read access, and environment read access.
USAGE
}

repository="${GITHUB_REPOSITORY:-}"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --repo)
      repository="${2:-}"
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

command -v gh >/dev/null 2>&1 || {
  echo "GitHub CLI (gh) is required." >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "jq is required." >&2
  exit 1
}

if [[ -z "${repository}" ]]; then
  repository="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi
[[ "${repository}" == */* ]] || {
  echo "--repo must be OWNER/REPOSITORY." >&2
  exit 2
}
gh auth status -h github.com >/dev/null

protection="$(gh api "repos/${repository}/branches/main/protection")"
jq -e '.required_status_checks.strict == true' <<< "${protection}" >/dev/null
jq -e '.required_pull_request_reviews.required_approving_review_count >= 1' \
  <<< "${protection}" >/dev/null

required_checks=(
  "Backend Tests"
  "Frontend Build"
  "Frontend Contract E2E"
  "Lint & Format Check"
  "Security Scan"
  "Docker Build"
  "Python Compile Check"
)
for check in "${required_checks[@]}"; do
  jq -e --arg check "${check}" '
    ((.required_status_checks.contexts // [])
      + ((.required_status_checks.checks // []) | map(.context)))
    | index($check) != null
  ' <<< "${protection}" >/dev/null || {
    echo "main branch protection does not require CI check: ${check}" >&2
    exit 1
  }
done

required_variables=(
  "DEPLOY_PATH"
  "PUBLIC_BASE_URL"
  "DATA_RELEASE_URI"
  "DATA_RELEASE_DESCRIPTOR_SHA256"
)
required_secrets=(
  "DEPLOY_HOST"
  "DEPLOY_USER"
  "DEPLOY_SSH_KEY"
  "SMOKE_TEST_EMAIL"
  "SMOKE_TEST_PASSWORD"
  "SMOKE_SECONDARY_EMAIL"
  "SMOKE_SECONDARY_PASSWORD"
)

environment_url() {
  local environment="$1"
  local variables
  variables="$(gh api "repos/${repository}/environments/${environment}/variables?per_page=100")"
  for name in "${required_variables[@]}"; do
    jq -e --arg name "${name}" '
      .variables[]? | select(.name == $name and (.value | length > 0))
    ' <<< "${variables}" >/dev/null || {
      echo "${environment} is missing required environment variable: ${name}" >&2
      exit 1
    }
  done
  jq -r '.variables[] | select(.name == "PUBLIC_BASE_URL") | .value' <<< "${variables}"
}

environment_secrets() {
  local environment="$1"
  local secrets
  secrets="$(gh api "repos/${repository}/environments/${environment}/secrets?per_page=100")"
  for name in "${required_secrets[@]}"; do
    jq -e --arg name "${name}" '.secrets[]? | select(.name == $name)' \
      <<< "${secrets}" >/dev/null || {
      echo "${environment} is missing required environment secret: ${name}" >&2
      exit 1
    }
  done
}

staging_url="$(environment_url staging)"
environment_secrets staging
production_url="$(environment_url production)"
environment_secrets production
[[ "${staging_url}" != "${production_url}" ]] || {
  echo "staging and production must use distinct PUBLIC_BASE_URL values." >&2
  exit 1
}

production_environment="$(gh api "repos/${repository}/environments/production")"
jq -e '
  [.protection_rules[]? | select(.type == "required_reviewers")] | length > 0
' <<< "${production_environment}" >/dev/null || {
  echo "production must require an environment reviewer approval." >&2
  exit 1
}

echo "GitHub release controls verified for ${repository}."
