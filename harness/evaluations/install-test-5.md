# Installation Test 5 — Lakemeter (Re-run)

**Date**: 2026-04-04
**Sprints covered**: 1-5 (cumulative)
**Verdict**: **PASS**

---

## 1. Clean Install Test

### Environment
- Python 3.12.5 (pyenv)
- Node.js + npm (frontend/docs-site)
- macOS Darwin 25.3.0

### Clean State
- Deleted `.venv/`, `frontend/node_modules/`, all `__pycache__/` directories
- Verified all removed before proceeding

### Python Dependencies
- Created fresh venv: `python3 -m venv .venv` — **OK**
- `requirements.txt` (root): 14 packages — all resolve and import correctly
- `backend/requirements.txt`: 12 packages — subset of root, all resolve
- **Note**: `python-jose`, `passlib`, `aiofiles` are in root `requirements.txt` but not imported anywhere in the codebase — dead dependencies (non-blocking)
- **Note**: `pytest`, `pytest-cov`, `pytest-asyncio` needed for tests but not in requirements — should be in `requirements-dev.txt`

### Frontend Dependencies
- `npm install` in `frontend/` — **432 packages installed in 3s** — no errors
- Deprecation warnings only (eslint 8.x, inflight, glob@7) — non-blocking
- TypeScript compilation: `tsc --noEmit` — **PASS** (zero errors)
- Frontend build: `npm run build` — **PASS**
  - Output: `backend/static/index.html` (1.40 KB), JS bundle (887.77 KB), CSS (56.96 KB)
  - Warning: JS chunk >500KB — consider code-splitting (non-blocking)

### Documentation Site
- `npm install` + `npm run build` in `docs-site/` — **PASS**
- Docusaurus built successfully, static files generated in `build/`

---

## 2. Test Results After Clean Install

```
2628 passed, 2 skipped, 1 warning in 150.27s (2:30)
```

**Zero failures.** All tests pass after clean install:
- Pricing/calculation tests for all 9 workload types
- Export tests (Excel, CSV, PDF generation)
- Cross-workload combined scenarios
- SKU alignment tests
- AI assistant workload tests
- Regression tests (jobs, DLT, DBSQL, FMAPI, vector search, model serving, lakebase)
- Integration validation (suite completeness, workload coverage)
- Documentation build tests
- Lakebase permissions tests (token generation, DB connection, CRUD)
- Health endpoint test

**2 skipped**: AI assistant tests requiring live FMAPI (expected — gated by marker)
**1 warning**: `PytestUnknownMarkWarning` for `@pytest.mark.slow` — cosmetic

---

## 3. Application Startup Verification

### Backend (FastAPI)
- Started on port 8177 via `uvicorn app.main:app --host 0.0.0.0 --port 8177`
- **Health check** (`/health`): `{"status":"healthy"}` — **200 OK**
- **Root** (`/`): **200 OK** — SPA served correctly
- **index.html**: **200 OK**
- **API docs** (`/docs`): **200 OK** — Swagger UI accessible
- DB initialization gracefully fails without credentials: "Token manager not initialized" — **no crash**
- Pricing bundle detected and loaded
- Documentation site mounted at `/docs/`

### Frontend (Static SPA)
- React SPA served from `backend/static/`
- All static assets (JS, CSS) accessible
- SPA routing via catch-all works correctly

### Documentation Site
- Docusaurus renders under `/docs/` path
- Built successfully from `docs-site/`

---

## 4. Deploy Artifacts Validation

### app.yaml (Root — full-repo deployment)
- **Command**: `cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` — correct
- **Env vars**: 11 defined, 5 use `valueFrom` (secrets) — properly configured
- **Secrets**: `lakemeter-secrets-scope`, `lakemeter-lakebase-instance`, `lakemeter-db-host`, `lakemeter-db-user`, `lakemeter-db-name`
- Host uses `{{databricks_host}}` placeholder — correct for templated deployment
- DB port and SSL mode explicitly set

### app.yaml (Backend — backend-only deployment)
- **Command**: `PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000` — correct
- **Env vars**: Same secrets via `valueFrom`
- **Minor issue**: `DATABRICKS_HOST` hardcoded to `https://fe-vm-lakemeter.cloud.databricks.com` — should use template variable like root `app.yaml`

### deploy.sh
- **Executable**: Yes (`chmod +x`)
- **Steps**: Build frontend → build docs → verify bundle → optional deploy
- **Error handling**: `set -e`, validates `index.html` and `assets/` exist
- **Conditional deploy**: Only deploys if `DATABRICKS_HOST` is set
- **No hardcoded secrets or tokens**

### .env.example
- **MISSING** — No `.env.example` file for local development reference
- Env vars are documented in `app.yaml` files and `scripts/install_lakemeter.py`

### install.sh
- **MISSING** — No standalone `install.sh` for local development
- `deploy.sh` covers build+deploy; `scripts/install_lakemeter.py` covers provisioning
- This means new developers must manually know to: create venv → pip install → cd frontend → npm install → npm run build

### Security Scan
- No hardcoded passwords in Python source
- No API tokens or secrets in code
- `LAKEMETER_API_BASE` hardcoded in `backend/app/external_api.py:23` — acceptable (app's own URL)
- `DATABRICKS_HOST` fallback hardcoded in `backend/app/services/ai_client.py:28` — minor (should prefer env-only)

### Port Usage
- Port 8000 hardcoded in both `app.yaml` files — acceptable for Databricks Apps (uses `DATABRICKS_APP_PORT` in production)
- No hardcoded ports in Python source

---

## 5. Issues Summary

### Blocking (0)
None — the application installs, tests pass, app starts and serves correctly.

### Non-blocking (5)

| # | Issue | Severity | Notes |
|---|-------|----------|-------|
| 1 | No `install.sh` for local development | Medium | New devs have no single-command setup |
| 2 | No `.env.example` file | Low | Env vars documented in app.yaml and installer script |
| 3 | Dead deps in `requirements.txt` (`python-jose`, `passlib`, `aiofiles`) | Low | Not imported; safe to remove |
| 4 | `backend/app.yaml` hardcodes `DATABRICKS_HOST` | Low | Root app.yaml uses template correctly |
| 5 | `ai_client.py` hardcodes DATABRICKS_HOST fallback | Low | Works but should be env-only |

---

## 6. Verdict

**PASS**

The application installs cleanly from a fresh state. All **2628 tests pass** (0 failures) after removing `.venv/`, `node_modules/`, and `__pycache__/`. Frontend builds successfully (TypeScript + Vite), documentation site builds (Docusaurus), and the application starts and serves health checks, SPA frontend, API docs, and documentation site. Deploy artifacts (`app.yaml`, `deploy.sh`) are properly configured with secrets managed via `valueFrom`. No hardcoded credentials found.

The only notable gaps are the missing `install.sh` and `.env.example` files, which would improve the onboarding experience for new developers but do not affect production deployment.
