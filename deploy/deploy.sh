#!/bin/bash
# PATH: deploy/deploy.sh
# PURPOSE: Local infrastructure/data helper. Production promotion is a
# GitLab-published immutable bundle pulled by the target's release agent.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Load environment (robust parsing: preserves spaces and special chars in values)
# NOTE: We avoid `export $(cat .env | xargs)` because it breaks on spaces.
if [ -f .env ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        case "$line" in
            ''|\#*) continue ;;
        esac
        # Require KEY=VALUE
        if [[ "$line" != *"="* ]]; then
            continue
        fi
        key="${line%%=*}"
        value="${line#*=}"
        # Trim surrounding quotes (optional)
        value="${value%\"}"
        value="${value#\"}"
        export "$key=$value"
    done < .env
fi

# Configuration - Set these in your environment or .env file
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-}"
KEY_PATH="${KEY_PATH:-$HOME/.ssh/your-key.pem}"
# Target-specific paths and URLs are intentionally required so a staging
# invocation can never fall through to a production host/domain.
REPO_DIR="${REPO_DIR:?REPO_DIR must identify the target host checkout}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:?PUBLIC_BASE_URL must identify the target URL}"

# Check requirements
check_requirements() {
    command -v aws >/dev/null 2>&1 || error "AWS CLI not installed"
    command -v ssh >/dev/null 2>&1 || error "SSH not installed"
}

check_deploy_requirements() {
    command -v ssh >/dev/null 2>&1 || error "SSH not installed"
    [ -n "${BACKEND_IMAGE:-}" ] || error "BACKEND_IMAGE must name the immutable CI image to deploy"
    [ -n "${FRONTEND_IMAGE:-}" ] || error "FRONTEND_IMAGE must name the immutable CI image to deploy"
    local root
    root="$(cd "$(dirname "$0")/.." && pwd)"
    git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
        error "Deployment source must be a Git checkout"
    test -z "$(git -C "$root" status --porcelain)" ||
        error "Refusing to deploy a dirty working tree; commit or discard local changes first"
}

# Create AWS infrastructure
create_infrastructure() {
    log "Creating AWS infrastructure..."
    cd "$(dirname "$0")/.."
    python3 deploy/setup_aws.py --create
    
    # Get EC2 host from AWS
    EC2_HOST=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=fse-rnd-alpha-server" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    log "EC2 instance running at: $EC2_HOST"
    echo "EC2_HOST=$EC2_HOST" >> .env
}

# Stage an immutable data artifact for the matching universe version.
upload_data() {
    [ -n "${UNIVERSE_VERSION:-}" ] || error "UNIVERSE_VERSION must identify the immutable data build"
    [ -n "${DATA_RELEASE_BUCKET:-}" ] || error "DATA_RELEASE_BUCKET must name the versioned data bucket"
    log "Staging immutable data release..."
    cd "$(dirname "$0")/.."
    DATA_RELEASE_BUCKET="$DATA_RELEASE_BUCKET" \
        DATA_RELEASE_PREFIX="${DATA_RELEASE_PREFIX:-investor-platform-data}" \
        ./scripts/stage_data_release.sh --universe-version "$UNIVERSE_VERSION"
}

# Deploy to EC2
deploy_to_ec2() {
    error "Local SSH/rsync deployment is retired. Publish GitLab main, then run rd-alpha-promote@<sha>-<pipeline-id> on the target host."
}

# Run concurrent crawl
run_crawl() {
    [ -z "$EC2_HOST" ] && error "EC2_HOST not set"
    
    log "Starting concurrent SEC crawl..."
    ssh -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd /opt/rd-alpha/deploy

# Trigger batch crawl via Celery
docker-compose exec -T worker celery -A app.workers.celery_app call app.workers.tasks.batch_crawl_companies \
    --args='[{"ticker":"AAPL","cik":"0000320193"},{"ticker":"MSFT","cik":"0000789019"}]' \
    --kwargs='{"years":20}'

echo "Crawl tasks dispatched. Monitor with: docker-compose logs -f worker"
REMOTE_SCRIPT
}

# Cleanup local data
cleanup_local() {
    warn "This will delete local raw data. Are you sure? (y/N)"
    read -r confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        log "Removing local data..."
        rm -rf "$(dirname "$0")/../data/raw/annual_reports"
        rm -rf "$(dirname "$0")/../data/raw/xbrl"
        log "Local data cleaned up"
    else
        warn "Cleanup cancelled"
    fi
}

# Main
main() {
    case "${1:-}" in
        --create-infra)
            check_requirements
            create_infrastructure
            ;;
        --upload-data)
            check_requirements
            upload_data
            ;;
        --deploy)
            deploy_to_ec2
            ;;
        --crawl)
            check_requirements
            run_crawl
            ;;
        --cleanup-local)
            cleanup_local
            ;;
        --full)
            error "--full is retired because it implied an SSH/rsync deployment. Stage data separately and promote through the target release agent."
            ;;
        *)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --create-infra   Create EC2 + S3 infrastructure"
            echo "  --upload-data    Stage immutable data artifact (requires UNIVERSE_VERSION and DATA_RELEASE_BUCKET)"
            echo "  --deploy         Disabled; promote a published GitLab release on the target host"
            echo "  --crawl          Start concurrent SEC crawl"
            echo "  --cleanup-local  Remove local raw data"
            echo "  --full           Disabled because it includes the retired SSH deployment path"
            ;;
    esac
}

main "$@"
