#!/bin/bash
# PATH: deploy/deploy.sh
# PURPOSE: One-click deployment to EC2
# USAGE: ./deploy.sh [--create-infra] [--upload-data] [--deploy]

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
REPO_DIR="${REPO_DIR:-/home/ubuntu/fse-rnd-alpha}"

# Check requirements
check_requirements() {
    command -v aws >/dev/null 2>&1 || error "AWS CLI not installed"
    command -v ssh >/dev/null 2>&1 || error "SSH not installed"
    command -v docker >/dev/null 2>&1 || warn "Docker not installed locally (not required for remote deploy)"
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

# Upload data to S3
upload_data() {
    log "Uploading data to S3..."
    cd "$(dirname "$0")/.."
    python3 deploy/setup_aws.py --upload
    log "Data uploaded successfully"
}

# Deploy to EC2
deploy_to_ec2() {
    [ -z "$EC2_HOST" ] && error "EC2_HOST not set. Run with --create-infra first."
    [ ! -f "$KEY_PATH" ] && error "SSH key not found at $KEY_PATH"
    
    log "Deploying to EC2 ($EC2_HOST)..."
    
    # Wait for SSH to be available
    log "Waiting for SSH..."
    for i in {1..30}; do
        if ssh -q -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" exit 2>/dev/null; then
            break
        fi
        sleep 10
    done
    
    # Copy project files
    log "Copying project files..."
    rsync -avz --progress \
        --exclude 'venv' \
        --exclude '.venv' \
        --exclude 'node_modules' \
        --exclude '__pycache__' \
        --exclude '.git' \
        --exclude 'data' \
        -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
        "$(dirname "$0")/../" "$EC2_USER@$EC2_HOST:$REPO_DIR/"
    
    # SSH and start services
    log "Starting services on EC2..."
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
set -e
cd ~/fse-rnd-alpha/deploy

# Ensure nginx has the latest built frontend assets.
# NOTE: frontend/dist is built locally before rsync; this copies it into the deploy-mounted path.
mkdir -p frontend
rm -rf frontend/dist
mkdir -p frontend/dist
if [ -d ../frontend/dist ]; then
  cp -R ../frontend/dist/. frontend/dist/
else
  echo "WARN: ../frontend/dist not found. Frontend may not update."
fi

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || touch .env
fi

# Build and start containers
docker-compose pull
docker-compose build
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Apply DB migrations needed for publication snapshot + result versioning.
echo "Running DB migrations..."
docker-compose exec -T postgres psql -U postgres -d rd_alpha < ../scripts/migrations/001_add_result_versioning.sql
docker-compose exec -T postgres psql -U postgres -d rd_alpha < ../scripts/migrations/003_publication_snapshots.sql

# Build a fresh publication snapshot (pins the new Main Paper exhibits).
echo "Building publication snapshot..."
curl -s -o /dev/null -w "Snapshot build HTTP %{http_code}\n" \
  -X POST http://localhost/api/research/publication-snapshot/build \
  -H "Content-Type: application/json" \
  -d '{"label":"Publication Snapshot (Main Paper)","return_convention":"july_june","data_tier":"tier1","set_active":true}' \
  || echo "Snapshot build request failed"

# Check health
curl -s -o /dev/null -w "Backend health HTTP %{http_code}\n" http://localhost/health || echo "Backend not ready yet"
curl -s http://localhost/ > /dev/null && echo "Frontend is up" || echo "Frontend not ready yet"

echo "Deployment complete!"
REMOTE_SCRIPT
    
    log "Deployment complete!"
    echo ""
    echo "=================================================="
    echo "  Application deployed successfully!"
    echo "=================================================="
    echo ""
    echo "  Frontend: http://$EC2_HOST"
    echo "  API:      http://$EC2_HOST:8000"
    echo "  API Docs: http://$EC2_HOST:8000/docs"
    echo ""
    echo "  SSH: ssh -i $KEY_PATH $EC2_USER@$EC2_HOST"
    echo ""
}

# Run concurrent crawl
run_crawl() {
    [ -z "$EC2_HOST" ] && error "EC2_HOST not set"
    
    log "Starting concurrent SEC crawl..."
    ssh -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd ~/fse-rnd-alpha/deploy

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
    check_requirements
    
    case "${1:-}" in
        --create-infra)
            create_infrastructure
            ;;
        --upload-data)
            upload_data
            ;;
        --deploy)
            deploy_to_ec2
            ;;
        --crawl)
            run_crawl
            ;;
        --cleanup-local)
            cleanup_local
            ;;
        --full)
            create_infrastructure
            upload_data
            deploy_to_ec2
            ;;
        *)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --create-infra   Create EC2 + S3 infrastructure"
            echo "  --upload-data    Upload local data to S3"
            echo "  --deploy         Deploy application to EC2"
            echo "  --crawl          Start concurrent SEC crawl"
            echo "  --cleanup-local  Remove local raw data"
            echo "  --full           Run all steps (infra + upload + deploy)"
            ;;
    esac
}

main "$@"
