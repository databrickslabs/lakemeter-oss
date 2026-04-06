#!/usr/bin/env bash
set -euo pipefail

# Lakemeter App — Local Development Installer
# Usage: ./install.sh
#
# Prerequisites: Python 3.10+, Node.js 18+ (for frontend dev)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Step 1: Check Python ─────────────────────────────────────────────────────
info "Checking Python version..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)')
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            info "Found $cmd ($ver)"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    error "Python 3.10+ required but not found. Install it first."
    exit 1
fi

# ── Step 2: Create virtual environment ────────────────────────────────────────
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    info "Creating Python virtual environment..."
    "$PYTHON" -m venv "$SCRIPT_DIR/.venv"
else
    info "Virtual environment already exists (.venv/)"
fi

source "$SCRIPT_DIR/.venv/bin/activate"
info "Activated virtual environment"

# ── Step 3: Install backend dependencies ──────────────────────────────────────
info "Installing backend dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
info "Backend dependencies installed"

# ── Step 4: Set up .env if missing ────────────────────────────────────────────
if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$BACKEND_DIR/.env"
        warn "Created backend/.env from .env.example — edit it with your credentials"
    else
        warn "No .env file found. Set DATABASE_URL or Databricks credentials before running."
    fi
else
    info "backend/.env already exists"
fi

# ── Step 5: Install frontend dependencies (optional) ──────────────────────────
if command -v node &>/dev/null && command -v npm &>/dev/null; then
    if [ -f "$FRONTEND_DIR/package.json" ]; then
        info "Installing frontend dependencies..."
        (cd "$FRONTEND_DIR" && npm install --silent 2>/dev/null) || warn "Frontend npm install had warnings"
        info "Frontend dependencies installed"
    fi
else
    warn "Node.js not found — skipping frontend install (optional for backend-only dev)"
fi

# ── Step 6: Run tests ────────────────────────────────────────────────────────
info "Running structural tests..."
PYTHONPATH="$BACKEND_DIR:$SCRIPT_DIR" "$PYTHON" -m pytest tests/harness/test_v_installer.py -q 2>/dev/null && \
    info "Structural tests: PASS" || warn "Some structural tests failed"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
info "Installation complete!"
echo ""
echo "  To start the backend:"
echo "    source .venv/bin/activate"
echo "    cd backend && uvicorn app.main:app --reload --port 8000"
echo ""
echo "  To start the frontend (separate terminal):"
echo "    cd frontend && npm run dev"
echo ""
echo "  API docs (local dev only): http://localhost:8000/docs"
echo ""
