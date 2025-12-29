#!/bin/bash
#
# PATH: research/scripts/deploy-ga4-main-site.sh
# PURPOSE: Deploy unified GA4 tracking to finsoeasy.com
#
# PREREQUISITES:
#   - SSH key: ~/.ssh/finsoeasy-key.pem
#   - Server access: ubuntu@13.210.239.75
#
# USAGE:
#   chmod +x deploy-ga4-main-site.sh
#   ./deploy-ga4-main-site.sh
#

set -e

# Configuration
SERVER_IP="13.210.239.75"
SSH_KEY="$HOME/.ssh/finsoeasy-key.pem"
SSH_USER="ubuntu"
GA4_PROPERTY="G-3RYSL77PJF"

echo "=================================================="
echo "  Deploying GA4 Tracking to finsoeasy.com"
echo "  Property: $GA4_PROPERTY"
echo "=================================================="

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo ""
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo ""
    echo "Please download the 'finsoeasy-key' from AWS EC2 console:"
    echo "  1. Go to EC2 → Key Pairs"
    echo "  2. Download 'finsoeasy-key.pem'"
    echo "  3. Save to ~/.ssh/finsoeasy-key.pem"
    echo "  4. Run: chmod 400 ~/.ssh/finsoeasy-key.pem"
    echo ""
    exit 1
fi

echo ""
echo "Connecting to server..."

# Create GA4 snippet file
GA4_SNIPPET='<!-- Google Analytics - Unified Finsoeasy Property -->
<script async src="https://www.googletagmanager.com/gtag/js?id='$GA4_PROPERTY'"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag("js", new Date());
  gtag("config", "'$GA4_PROPERTY'", {
    "cookie_domain": ".finsoeasy.com",
    "cookie_flags": "SameSite=None;Secure"
  });
</script>'

# SSH into server and find HTML files to update
ssh -i "$SSH_KEY" "$SSH_USER@$SERVER_IP" << 'ENDSSH'
echo "Connected to finsoeasy.com server"
echo ""

# Find the web root
echo "Looking for web root..."
WEB_ROOTS="/var/www/html /var/www/finsoeasy /home/ubuntu/finsoeasy /app"
for dir in $WEB_ROOTS; do
    if [ -d "$dir" ]; then
        echo "Found: $dir"
        ls -la "$dir" | head -10
    fi
done

echo ""
echo "Checking running processes..."
ps aux | grep -E 'nginx|apache|gunicorn|uvicorn|python|node' | head -10

echo ""
echo "Checking Docker containers..."
docker ps 2>/dev/null || echo "Docker not running or not installed"

ENDSSH

echo ""
echo "=================================================="
echo "  Manual Steps Required"
echo "=================================================="
echo ""
echo "1. SSH into the server:"
echo "   ssh -i $SSH_KEY $SSH_USER@$SERVER_IP"
echo ""
echo "2. Locate the HTML template file (usually base.html or index.html)"
echo ""
echo "3. Add this GA4 snippet to the <head> section:"
echo ""
echo "$GA4_SNIPPET"
echo ""
echo "4. Restart the web server:"
echo "   sudo systemctl restart nginx"
echo "   # or"
echo "   docker-compose restart"
echo ""
echo "5. Verify tracking at: https://finsoeasy.com"
echo "   Check browser DevTools → Network → filter 'gtag'"
echo ""
echo "=================================================="

