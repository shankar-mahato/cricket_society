#!/bin/bash
# Deployment script to run ON PythonAnywhere
# This script should be uploaded to PythonAnywhere and run there
# Usage: bash deploy_on_pythonanywhere.sh

set -e  # Exit on error

echo "🚀 Starting deployment on PythonAnywhere..."

# Configuration
REPO_DIR="$HOME/cricket_society"
VENV_DIR="$HOME/cricket_society/venv"
PROJECT_DIR="$HOME/cricket_society/mycricket"
USERNAME="cricketsociety"
API_TOKEN="dec6d26a6576c80ce27cfda4160413d88e57f787"
WEBAPP_NAME="cricketsociety"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Navigate to repository
echo -e "${YELLOW}📂 Step 1: Navigating to repository...${NC}"
cd "$REPO_DIR" || {
    echo -e "${RED}❌ Error: Repository directory not found: $REPO_DIR${NC}"
    echo "   Make sure you've cloned the repository to this location"
    exit 1
}

# Step 2: Pull latest code
echo -e "${YELLOW}📥 Step 2: Pulling latest code from GitHub...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Code pulled successfully${NC}"
else
    echo -e "${RED}❌ Error: Failed to pull code${NC}"
    echo "   Make sure you're connected to the internet and have access to GitHub"
    exit 1
fi

# Step 3: Activate virtual environment
echo -e "${YELLOW}🐍 Step 3: Activating virtual environment...${NC}"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found at $VENV_DIR${NC}"
    echo "   Create it with: python3.10 -m venv venv"
    exit 1
fi
source "$VENV_DIR/bin/activate"

# Step 4: Install/update dependencies
echo -e "${YELLOW}📦 Step 4: Installing/updating dependencies...${NC}"
cd "$PROJECT_DIR"
pip install --quiet --upgrade pip
pip install --quiet -r "$REPO_DIR/requirements.txt"

# Step 5: Run migrations
echo -e "${YELLOW}🗄️  Step 5: Running database migrations...${NC}"
python manage.py migrate --noinput

# Step 6: Collect static files (IMPORTANT for UI updates!)
echo -e "${YELLOW}📁 Step 6: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✅ Static files collected${NC}"

# Step 7: Reload web app via API
echo -e "${YELLOW}🔄 Step 7: Reloading web app...${NC}"
RELOAD_URL="https://www.pythonanywhere.com/api/v0/user/${USERNAME}/webapps/${WEBAPP_NAME}/reload/"
RELOAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RELOAD_URL" \
    -H "Authorization: Token ${API_TOKEN}")

HTTP_CODE=$(echo "$RELOAD_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RELOAD_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Web app reloaded successfully!${NC}"
else
    echo -e "${RED}❌ Error reloading web app (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $RESPONSE_BODY"
    echo "   You may need to reload manually from the PythonAnywhere dashboard"
fi

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🌐 Your site: https://${USERNAME}.pythonanywhere.com"
echo ""
echo "💡 If UI changes aren't showing:"
echo "   1. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)"
echo "   2. Clear browser cache"
echo "   3. Check that static files are properly configured in Web tab"
echo ""

