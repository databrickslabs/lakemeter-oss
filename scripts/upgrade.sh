#!/usr/bin/env bash
# Lakemeter version-aware upgrade utility.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PAYLOAD_DIR="$SCRIPT_DIR/upgrade_payload"

COMMAND="${1:-plan}"
if [[ "$COMMAND" != "status" && "$COMMAND" != "plan" && "$COMMAND" != "doctor" && "$COMMAND" != "apply" && "$COMMAND" != "rollback" ]]; then
    COMMAND="plan"
else
    shift || true
fi

PROFILE=""
APP_NAME="lakemeter"
ASSUME_YES=false
ALLOW_DIRTY=false
BUILD_FRONTEND=false

usage() {
    echo "Usage: ./scripts/upgrade.sh COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status       Show the installed version and latest upgrade run"
    echo "  plan         Validate and display the upgrade plan (default)"
    echo "  doctor       Run upgrade prerequisites without changing anything"
    echo "  apply        Apply the checked-out release"
    echo "  rollback     Roll back the latest recorded upgrade"
    echo ""
    echo "Options:"
    echo "  --profile NAME       Databricks CLI profile"
    echo "  --app-name NAME      Existing Databricks App name (default: lakemeter)"
    echo "  --yes                Skip apply confirmation"
    echo "  --allow-dirty        Allow a dirty git checkout (development only)"
    echo "  --build-frontend     Rebuild frontend assets before staging"
    echo "  -h, --help           Show this help"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="${2:?--profile requires a value}"
            shift 2
            ;;
        --app-name)
            APP_NAME="${2:?--app-name requires a value}"
            shift 2
            ;;
        --yes)
            ASSUME_YES=true
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY=true
            shift
            ;;
        --build-frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 2
            ;;
    esac
done

for required in databricks python3 rsync; do
    if ! command -v "$required" >/dev/null 2>&1; then
        echo -e "${RED}Missing required command: $required${NC}"
        exit 1
    fi
done

PROFILE_ARGS=()
if [[ -n "$PROFILE" ]]; then
    PROFILE_ARGS=(--profile "$PROFILE")
fi

echo -e "${BOLD}Lakemeter Upgrade Utility${NC}"
echo "================================"
echo -e "  Command: ${CYAN}${COMMAND}${NC}"
echo -e "  App:     ${CYAN}${APP_NAME}${NC}"

if ! databricks current-user me "${PROFILE_ARGS[@]}" >/dev/null 2>&1; then
    echo -e "${RED}Cannot connect to the Databricks workspace.${NC}"
    exit 1
fi

LOCAL_ARGS=(--app-name "$APP_NAME" --payload-root "$PAYLOAD_DIR")
if [[ -n "$PROFILE" ]]; then
    LOCAL_ARGS+=(--profile "$PROFILE")
fi
if [[ "$COMMAND" == "status" || "$COMMAND" == "rollback" ]]; then
    PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/run_upgrade_command.py" \
        "$COMMAND" "${LOCAL_ARGS[@]}"
    exit 0
fi

VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"
MANIFEST_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$SCRIPT_DIR/upgrades/release.json")"
if [[ "$VERSION" != "$MANIFEST_VERSION" ]]; then
    echo -e "${RED}VERSION ($VERSION) does not match release manifest ($MANIFEST_VERSION).${NC}"
    exit 1
fi
echo -e "  Target:  ${CYAN}${VERSION}${NC}"

if [[ "$COMMAND" == "apply" && "$ALLOW_DIRTY" == false ]] && command -v git >/dev/null 2>&1; then
    if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
        echo -e "${RED}The repository has uncommitted changes.${NC}"
        echo "Use a clean release checkout, or pass --allow-dirty for development."
        exit 1
    fi
fi

if [[ "$BUILD_FRONTEND" == true ]]; then
    if ! command -v npm >/dev/null 2>&1; then
        echo -e "${RED}--build-frontend requires npm.${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Building frontend assets...${NC}"
    (
        cd "$REPO_ROOT/frontend"
        npm ci --silent
        npm run build
    )
fi

if [[ ! -f "$REPO_ROOT/backend/static/index.html" ]]; then
    echo -e "${RED}Missing backend/static/index.html.${NC}"
    echo "Use a release archive with pre-built assets or pass --build-frontend."
    exit 1
fi

rm -rf "$PAYLOAD_DIR"
mkdir -p "$PAYLOAD_DIR/app_source" "$PAYLOAD_DIR/scripts/upgrades"
trap 'rm -rf "$PAYLOAD_DIR"' EXIT

cp "$REPO_ROOT/VERSION" "$PAYLOAD_DIR/VERSION"
rsync -a --delete "$SCRIPT_DIR/upgrades/" "$PAYLOAD_DIR/scripts/upgrades/"
PYTHONPATH="$SCRIPT_DIR" python3 - "$REPO_ROOT" "$PAYLOAD_DIR/app_source" <<'PY'
import sys
from pathlib import Path
from upgrader.payload import build_runtime_payload

build_runtime_payload(Path(sys.argv[1]), Path(sys.argv[2]))
PY

if [[ "$COMMAND" == "plan" || "$COMMAND" == "doctor" ]]; then
    PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/run_upgrade_command.py" \
        "$COMMAND" "${LOCAL_ARGS[@]}"
    exit 0
fi

if [[ "$ASSUME_YES" == false ]]; then
    echo ""
    echo -e "${YELLOW}This will apply Lakemeter ${VERSION} to app '${APP_NAME}'.${NC}"
    read -r -p "Continue? [y/N]: " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Upgrade cancelled."
        exit 0
    fi
fi

echo -e "${YELLOW}Deploying upgrade workflow...${NC}"
(
    cd "$SCRIPT_DIR"
    databricks bundle deploy "${PROFILE_ARGS[@]}" --auto-approve
)

echo -e "${YELLOW}Running ${COMMAND}...${NC}"
(
    cd "$SCRIPT_DIR"
    databricks bundle run lakemeter_upgrade \
        "${PROFILE_ARGS[@]}" \
        --params "command=${COMMAND},app_name=${APP_NAME}"
)

echo -e "${GREEN}${COMMAND} completed.${NC}"

