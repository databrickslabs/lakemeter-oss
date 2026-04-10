#!/bin/bash
# Lakemeter Installer
# Prompts for configuration, then runs a DABs workflow on serverless compute.
#
# Prerequisites: Databricks CLI (https://docs.databricks.com/en/dev-tools/cli/install.html)
#
# Usage:
#   ./scripts/install.sh                              # Interactive (prompts for config)
#   ./scripts/install.sh --non-interactive             # Use all defaults
#   ./scripts/install.sh --profile my-profile          # Specify CLI profile
#   ./scripts/install.sh --non-interactive --profile p  # CI/CD mode

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
PROFILE=""
NON_INTERACTIVE=false
INSTANCE_NAME="lakemeter-customer"
DB_NAME="lakemeter_pricing"
APP_NAME="lakemeter"
SECRETS_SCOPE="lakemeter-secrets"
CLAUDE_ENDPOINT="databricks-claude-opus-4-6"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        --instance-name)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        --db-name)
            DB_NAME="$2"
            shift 2
            ;;
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --secrets-scope)
            SECRETS_SCOPE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --profile NAME         Databricks CLI profile (required if not DEFAULT)"
            echo "  --non-interactive      Use all defaults, no prompts"
            echo "  --instance-name NAME   Lakebase instance name (default: lakemeter-customer)"
            echo "  --db-name NAME         Database name (default: lakemeter_pricing)"
            echo "  --app-name NAME        Databricks App name (default: lakemeter)"
            echo "  --secrets-scope NAME   Secret scope name (default: lakemeter-secrets)"
            echo "  -h, --help             Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check Databricks CLI
if ! command -v databricks &> /dev/null; then
    echo -e "${RED}Error: Databricks CLI not found.${NC}"
    echo "Install it: https://docs.databricks.com/en/dev-tools/cli/install.html"
    exit 1
fi

# Build profile flag
PROFILE_FLAG=""
if [ -n "$PROFILE" ]; then
    PROFILE_FLAG="--profile $PROFILE"
fi

# Verify workspace connectivity
echo -e "${BOLD}Lakemeter Installer${NC}"
echo "================================"
echo ""
echo -e "${YELLOW}Checking workspace connectivity...${NC}"
WHOAMI=$(databricks current-user me $PROFILE_FLAG 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('userName',''))" 2>/dev/null || true)
if [ -z "$WHOAMI" ]; then
    echo -e "${RED}Error: Cannot connect to workspace. Check your CLI profile.${NC}"
    if [ -n "$PROFILE" ]; then
        echo "  Profile: $PROFILE"
    else
        echo "  No --profile specified. Run: databricks configure"
    fi
    exit 1
fi
echo -e "${GREEN}Connected as: ${WHOAMI}${NC}"

# Interactive prompts (unless --non-interactive)
if [ "$NON_INTERACTIVE" = false ]; then
    echo ""
    echo -e "${BOLD}Configuration${NC} (press Enter to accept defaults)"
    echo ""

    read -p "  Lakebase instance name [$INSTANCE_NAME]: " input
    INSTANCE_NAME="${input:-$INSTANCE_NAME}"

    read -p "  Database name [$DB_NAME]: " input
    DB_NAME="${input:-$DB_NAME}"

    read -p "  App name [$APP_NAME]: " input
    APP_NAME="${input:-$APP_NAME}"

    read -p "  Secrets scope [$SECRETS_SCOPE]: " input
    SECRETS_SCOPE="${input:-$SECRETS_SCOPE}"
fi

# Show configuration
echo ""
echo -e "${BOLD}Configuration:${NC}"
echo -e "  Instance name:  ${CYAN}${INSTANCE_NAME}${NC}"
echo -e "  Database:       ${CYAN}${DB_NAME}${NC}"
echo -e "  App name:       ${CYAN}${APP_NAME}${NC}"
echo -e "  Secrets scope:  ${CYAN}${SECRETS_SCOPE}${NC}"
echo -e "  Claude endpoint: ${CYAN}${CLAUDE_ENDPOINT}${NC}"
echo ""

# Prepare bundle: copy pricing CSVs and app source into scripts/ for DABs sync
echo -e "${YELLOW}Preparing bundle...${NC}"

# Pricing data (CSVs only)
PRICING_SRC="$REPO_ROOT/backend/static/pricing"
PRICING_DST="$SCRIPT_DIR/pricing_data"
rm -rf "$PRICING_DST"
mkdir -p "$PRICING_DST"
MAX_FILE_SIZE=$((9 * 1024 * 1024))  # 9MB (workspace import limit is ~10MB)
for csv_file in "$PRICING_SRC"/*.csv; do
    [ -f "$csv_file" ] || continue
    file_size=$(wc -c < "$csv_file" | xargs)
    if [ "$file_size" -le "$MAX_FILE_SIZE" ]; then
        cp "$csv_file" "$PRICING_DST/"
    else
        # Split large CSV into parts using Python (handles header correctly)
        base_name=$(basename "$csv_file" .csv)
        echo -e "  ${YELLOW}Splitting ${base_name}.csv ($(( file_size / 1024 / 1024 ))MB)...${NC}"
        python3 -c "
import csv, os, sys
max_size = $MAX_FILE_SIZE
src = '$csv_file'
dst_dir = '$PRICING_DST'
stem = '$base_name'
with open(src, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    header_line = ','.join(header) + '\n'
    part_num = 0
    current_size = max_size + 1  # force new file on first row
    out = None
    for row in reader:
        line = ','.join(row) + '\n'
        if current_size + len(line.encode()) > max_size:
            if out: out.close()
            part_num += 1
            out = open(os.path.join(dst_dir, f'{stem}_part{part_num}.csv'), 'w')
            out.write(header_line)
            current_size = len(header_line.encode())
        out.write(line)
        current_size += len(line.encode())
    if out: out.close()
    print(f'  Split into {part_num} parts')
"
    fi
done
CSV_COUNT=$(ls -1 "$PRICING_DST"/*.csv 2>/dev/null | wc -l | xargs)
echo -e "  ${GREEN}Pricing data: ${CSV_COUNT} CSV files${NC}"

# App source (backend + static assets, excluding CSVs and unnecessary files)
APP_SRC_DST="$SCRIPT_DIR/app_source"
rm -rf "$APP_SRC_DST"
mkdir -p "$APP_SRC_DST/backend"
rsync -a --exclude='__pycache__' --exclude='.pytest_cache' \
    "$REPO_ROOT/backend/app/" "$APP_SRC_DST/backend/app/"
rsync -a --exclude='*.csv' --exclude='manifest.json' \
    "$REPO_ROOT/backend/static/" "$APP_SRC_DST/backend/static/"
cp "$REPO_ROOT/requirements.txt" "$APP_SRC_DST/" 2>/dev/null || true
echo -e "  ${GREEN}App source prepared${NC}"

# Deploy bundle
echo ""
echo -e "${YELLOW}Deploying bundle to workspace...${NC}"
cd "$SCRIPT_DIR"
databricks bundle deploy $PROFILE_FLAG --auto-approve
echo -e "${GREEN}Bundle deployed${NC}"

# Run installer workflow
echo ""
echo -e "${YELLOW}Running installer workflow on serverless compute...${NC}"
echo -e "  This will provision Lakebase, create tables, load pricing data,"
echo -e "  configure the app, and deploy it."
echo ""
databricks bundle run lakemeter_installer $PROFILE_FLAG \
    --params "instance_name=$INSTANCE_NAME,db_name=$DB_NAME,app_name=$APP_NAME,secrets_scope=$SECRETS_SCOPE,claude_endpoint=$CLAUDE_ENDPOINT"

# Cleanup temporary directories
rm -rf "$PRICING_DST" "$APP_SRC_DST"

echo ""
echo -e "${BOLD}${GREEN}Installation complete!${NC}"
echo ""
echo -e "  Verify: databricks apps get ${APP_NAME} ${PROFILE_FLAG}"
echo ""
