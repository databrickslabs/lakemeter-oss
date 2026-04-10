---
sidebar_position: 1
---

# Deployment

Lakemeter is deployed as a **Databricks App** — a managed web application running on the Databricks platform with built-in SSO authentication.

![Deployment guide documentation page](/img/guides/admin-deployment-guide.png)
*The Deployment guide — architecture diagram, deploy.sh workflow, and app.yaml configuration.*

## Architecture

```
┌─────────────────────────────────────────┐
│           Databricks Apps               │
│  ┌───────────────────────────────────┐  │
│  │  FastAPI Backend (Python)         │  │
│  │  ├── REST API (/api/v1/*)         │  │
│  │  ├── Static Files (React SPA)     │  │
│  │  └── AI Agent (FMAPI)            │  │
│  └──────────┬────────────────────────┘  │
│             │                            │
│  ┌──────────▼────────────────────────┐  │
│  │  Lakebase (PostgreSQL)            │  │
│  │  ├── Estimates & Line Items       │  │
│  │  ├── Users & Sharing              │  │
│  │  └── Pricing Reference Data       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Prerequisites

- **Databricks Workspace** with Apps and Lakebase enabled
- **Databricks CLI** installed and configured with a workspace profile
- **Node.js 22+** and **npm** (for local frontend builds — the Databricks Apps runtime includes Node.js 22.16)
- **Service Principal** registered in your workspace (client ID and secret)

:::tip Automated provisioning
The [Installer](./installer) automatically provisions the Lakebase instance, creates the secret scope, stores SP credentials, sets up database schema, and configures all permissions. The only manual prerequisite is having a Service Principal created in your workspace.
:::

## Automated Installation

The fastest way to deploy Lakemeter is with the zero-click installer:

```bash
python scripts/install_lakemeter.py --profile your-profile
```

This provisions the Lakebase instance, creates database schema, loads pricing data, configures SP access, and generates `app.yaml`. See the [Installer Guide](./installer) for the full walkthrough.

## App Configuration (app.yaml)

Two `app.yaml` files exist in the repository:

- **Root `app.yaml`** — for full-repo deployment (references `backend/` subdirectory)
- **`backend/app.yaml`** — for backend-only deployment

Both use `valueFrom` resource references for sensitive configuration. Here is the root-level `app.yaml`:

```yaml
command:
  - "/bin/bash"
  - "-c"
  - "cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

env:
  - name: ENVIRONMENT
    value: "production"
  - name: CORS_ORIGINS
    value: ""
  - name: DATABRICKS_HOST
    value: "{{databricks_host}}"

  # Secrets scope containing SP credentials
  - name: DATABRICKS_SECRETS_SCOPE
    valueFrom: "lakemeter-secrets-scope"
  - name: SP_CLIENT_ID_KEY
    value: "sp_clientid"
  - name: SP_SECRET_KEY
    value: "sp_secret"

  # Lakebase database configuration (resolved at runtime)
  - name: LAKEBASE_INSTANCE_NAME
    valueFrom: "lakemeter-lakebase-instance"
  - name: DB_HOST
    valueFrom: "lakemeter-db-host"
  - name: DB_USER
    valueFrom: "lakemeter-db-user"
  - name: DB_NAME
    valueFrom: "lakemeter-db-name"
  - name: DB_PORT
    value: "5432"
  - name: DB_SSLMODE
    value: "require"
```

The `valueFrom` pattern references Databricks App resources that are resolved at runtime, keeping database hostnames and credentials out of the YAML file. Hardcoded values are limited to non-sensitive defaults (`DB_PORT=5432`, `DB_SSLMODE=require`, SP key names).

:::note
The `backend/app.yaml` (for backend-only deployment) omits `DB_PORT` and `DB_SSLMODE` — these fall back to defaults in `config.py` (`5432` and `require`). The root `app.yaml` sets them explicitly for clarity. Both configurations produce the same runtime behavior.
:::

:::info
In production, the Swagger API docs (`/docs` and `/redoc`) are automatically disabled. The Docusaurus documentation site at `/docs/` is unaffected. Set `ENVIRONMENT=development` to re-enable Swagger.
:::

## Deployment with deploy.sh

The `deploy.sh` script automates the full build-and-deploy process:

```bash
./deploy.sh
```

It runs these steps:

1. **Build frontend** — runs `npm ci && npm run build` in `frontend/`. Vite outputs directly to `backend/static/`.
2. **Build documentation site** — runs `npm ci && npm run build` in `docs-site/`, then copies output to `backend/static/docs/`.
3. **Verify bundle** — checks that `backend/static/index.html` and `backend/static/assets/` exist with JS and CSS files.
4. **Deploy to Databricks Apps** — if `DATABRICKS_HOST` is set, runs `databricks apps deploy <app-name> --source-code-path .` from the `backend/` directory.

### Environment Variables for deploy.sh

| Variable | Default | Description |
|----------|---------|-------------|
| `LAKEMETER_APP_NAME` | `lakemeter` | Databricks App name |
| `DATABRICKS_HOST` | (none) | Workspace URL — if set, auto-deploys; if unset, build-only |

### Build-Only Mode

If `DATABRICKS_HOST` is not set, `deploy.sh` builds the frontend and docs but skips deployment. You can then deploy manually:

```bash
cd backend && databricks apps deploy lakemeter --source-code-path . -p your-profile
```

## Manual Deployment Steps

If you prefer not to use `deploy.sh`:

### 1. Build the Frontend

```bash
cd frontend
npm ci
npm run build
```

Vite outputs directly to `../backend/static/` (configured in `vite.config.ts`).

### 2. Build the Documentation Site (Optional)

```bash
cd docs-site
npm ci
npm run build
cp -r build/* ../backend/static/docs/
```

### 3. Deploy the App

```bash
cd backend
databricks apps deploy lakemeter --source-code-path . -p your-profile
```

### 4. Verify

```bash
databricks apps get lakemeter -p your-profile
```

The app URL will be in the output (e.g., `https://lakemeter-xxxxx.aws.databricksapps.com`).

## Updating the App

To deploy changes:

1. Modify local files
2. Run `./deploy.sh` (or build manually and redeploy)

:::tip
Do not restart the app — just redeploy. Databricks Apps handles the restart automatically during deployment.
:::

## Authentication

Lakemeter uses **Databricks Apps SSO** for user authentication. Users are automatically authenticated when they access the app through their Databricks workspace. The user's email and identity are passed via HTTP headers (`X-Forwarded-Email`, `X-Forwarded-User`) by the Databricks Apps proxy.

No additional authentication configuration is required for end users.

For database access, the app uses **Service Principal OAuth M2M** authentication to connect to Lakebase. See the [Permissions Guide](./permissions) for details on SP role configuration.
