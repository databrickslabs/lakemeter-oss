#!/bin/bash
# Lakemeter Deployment Script
# Builds frontend, syncs to workspace, and deploys to Databricks Apps
#
# Usage:
#   ./deploy.sh                          # Build only (no deploy)
#   DATABRICKS_HOST=... ./deploy.sh      # Build + local deploy from backend/
#   ./deploy.sh --workspace-deploy       # Build + sync to workspace + deploy
#
# Environment variables:
#   DATABRICKS_HOST          - Workspace host (required for deploy)
#   LAKEMETER_APP_NAME       - App name (default: lakemeter)
#   LAKEMETER_WORKSPACE_PATH - Workspace path (default: auto-detect from app config)
#   DATABRICKS_PROFILE       - CLI profile to use (optional)

set -e  # Exit on error

echo "Lakemeter Deployment Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="${LAKEMETER_APP_NAME:-lakemeter}"
WORKSPACE_HOST="${DATABRICKS_HOST:-}"
PROFILE_FLAG=""
if [ -n "$DATABRICKS_PROFILE" ]; then
    PROFILE_FLAG="--profile $DATABRICKS_PROFILE"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DEPLOY=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --workspace-deploy)
            WORKSPACE_DEPLOY=true
            shift
            ;;
    esac
done

cd "$SCRIPT_DIR"

# Step 1: Build Frontend
echo -e "\n${YELLOW}Step 1: Building frontend...${NC}"
cd frontend

# Update API URL for production (same origin, no CORS needed)
cat > .env.production << EOF
VITE_API_URL=
EOF

npm ci --silent 2>/dev/null || npm install --silent
npm run build

# Vite outputs directly to ../backend/static/ (configured in vite.config)
cd "$SCRIPT_DIR"
if [ ! -f "backend/static/index.html" ]; then
    echo -e "${RED}Error: Frontend build failed - backend/static/index.html not found${NC}"
    exit 1
fi
echo -e "${GREEN}OK Frontend built successfully${NC}"

# Step 2: Verify the bundle
echo -e "\n${YELLOW}Step 2: Verifying bundle...${NC}"
JS_COUNT=$(find backend/static/assets -name "*.js" 2>/dev/null | wc -l | xargs)
CSS_COUNT=$(find backend/static/assets -name "*.css" 2>/dev/null | wc -l | xargs)
echo -e "${GREEN}OK Assets: ${JS_COUNT} JS, ${CSS_COUNT} CSS files${NC}"

# Step 3: Deploy
if [ "$WORKSPACE_DEPLOY" = true ]; then
    # Workspace-based deployment: sync only necessary files, then deploy from workspace
    echo -e "\n${YELLOW}Step 3: Workspace deployment — syncing necessary files only...${NC}"

    if ! command -v databricks &> /dev/null; then
        echo -e "${RED}Error: Databricks CLI not installed${NC}"
        exit 1
    fi

    # Detect workspace path from app config
    WS_PATH="${LAKEMETER_WORKSPACE_PATH:-}"
    if [ -z "$WS_PATH" ]; then
        WS_PATH=$(databricks apps get ${APP_NAME} ${PROFILE_FLAG} 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('default_source_code_path',''))" 2>/dev/null || true)
    fi
    if [ -z "$WS_PATH" ]; then
        echo -e "${RED}Error: Cannot detect workspace path. Set LAKEMETER_WORKSPACE_PATH.${NC}"
        exit 1
    fi
    echo "Workspace path: $WS_PATH"

    # Sync ONLY the directories needed for the app to run
    # Excludes: tests/, etl/, docs-site/, harness/, .venv/, .git/, node_modules/
    echo "Syncing backend/..."
    databricks workspace import-dir ${PROFILE_FLAG} "backend" "${WS_PATH}/backend" --overwrite
    echo "Syncing frontend/ (source only)..."
    databricks workspace import-dir ${PROFILE_FLAG} "frontend/src" "${WS_PATH}/frontend/src" --overwrite
    databricks workspace import-dir ${PROFILE_FLAG} "frontend/public" "${WS_PATH}/frontend/public" --overwrite
    # Sync frontend config files individually
    for f in frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/.env.production; do
        if [ -f "$f" ]; then
            databricks workspace import ${PROFILE_FLAG} --file "$f" "${WS_PATH}/$f" --overwrite 2>/dev/null || true
        fi
    done
    echo "Syncing scripts/..."
    databricks workspace import-dir ${PROFILE_FLAG} "scripts" "${WS_PATH}/scripts" --overwrite
    # Sync top-level config files
    for f in app.yaml requirements.txt; do
        if [ -f "$f" ]; then
            databricks workspace import ${PROFILE_FLAG} --file "$f" "${WS_PATH}/$f" --overwrite 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}OK Files synced to workspace${NC}"

    # Clean up any stale artifacts that shouldn't be in the workspace
    for dir in .venv .git .claude .pytest_cache .databricks node_modules docs-site/node_modules docs-site/build docs-site/.docusaurus harness tests etl; do
        databricks workspace delete ${PROFILE_FLAG} "${WS_PATH}/${dir}" --recursive 2>/dev/null || true
    done

    # Deploy from workspace
    echo "Deploying app '${APP_NAME}' from workspace..."
    databricks apps deploy ${APP_NAME} ${PROFILE_FLAG} --source-code-path "${WS_PATH}"
    echo -e "${GREEN}OK Deployed from workspace${NC}"

elif [ -n "$WORKSPACE_HOST" ]; then
    # Local deployment: deploy directly from local backend/ directory
    echo -e "\n${YELLOW}Step 3: Local deployment to Databricks Apps...${NC}"

    if ! command -v databricks &> /dev/null; then
        echo -e "${RED}Error: Databricks CLI not installed${NC}"
        exit 1
    fi

    cd backend
    echo "Deploying app '${APP_NAME}' from local backend/..."
    databricks apps deploy ${APP_NAME} ${PROFILE_FLAG} --source-code-path .
    echo -e "${GREEN}OK Deployed to Databricks Apps${NC}"
    echo -e "App URL: ${BLUE}https://${WORKSPACE_HOST}/apps/${APP_NAME}${NC}"
else
    echo -e "\n${YELLOW}Step 3: Skipping deployment (DATABRICKS_HOST not set)${NC}"
    echo ""
    echo "To deploy:"
    echo -e "  ${BLUE}# Option A: Workspace deploy (recommended for production)${NC}"
    echo -e "  ${BLUE}LAKEMETER_APP_NAME=lakemeter ./deploy.sh --workspace-deploy${NC}"
    echo ""
    echo -e "  ${BLUE}# Option B: Local deploy${NC}"
    echo -e "  ${BLUE}DATABRICKS_HOST=your-workspace.cloud.databricks.com ./deploy.sh${NC}"
    echo -e "\n${GREEN}OK Build complete - ready for deployment${NC}"
fi

echo ""
echo "Bundle contents:"
du -sh backend/static/ 2>/dev/null || true
