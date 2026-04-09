# Claude AI Assistant - Project Context & Rules

## 🔗 Source of Truth

**GitHub Repository:** `https://github.com/steven-tan_data/lakemeter-opensource`

- All code changes must be committed and pushed to this repo (remote: `origin`)
- The `lakemeter_app/` directory contains the full-stack app (frontend + backend + docs)
- **NEVER** reference or sync to `junyi.tiong` workspace paths — all workspace operations use `steven.tan@databricks.com`

## 📋 Quick Reference

### Databricks CLI Profile
```bash
# Always use this profile for this project
--profile lakemeter

# Workspace URL
https://fe-vm-lakemeter.cloud.databricks.com

# Common commands
databricks workspace list --profile lakemeter "/Workspace/Users/steven.tan@databricks.com"
databricks workspace import --profile lakemeter --language PYTHON --format SOURCE --file <local> <remote> --overwrite
databricks secrets list-secrets --profile lakemeter lakemeter-credentials
```

---

## ⚠️ Important Rules

### 1. **Always Commit After Making Changes**
- ✅ After completing code changes, always commit and push to `origin`
- ✅ Never leave working changes uncommitted — commit before ending a session
- ❌ Don't ask "want me to commit?" — just do it

### 2. **DO NOT Create Unnecessary Markdown Files**
- ❌ Don't create documentation files unless explicitly requested
- ❌ Don't create README files proactively
- ❌ Don't create summary files after completing tasks
- ✅ Only create markdown when user explicitly asks for it

### 3. **DO NOT Create Unnecessary Notebooks**
- ❌ If user asks for "SQL code", give SQL code directly - don't wrap it in a notebook
- ❌ Don't create notebooks for simple queries or checks
- ✅ Only create notebooks when explicitly requested or for complex operations
- ✅ For simple SQL queries, just provide the SQL code

### 4. **DO NOT Restart Databricks Apps**
- ❌ Don't suggest restarting the app
- ❌ Don't run commands to restart services
- ✅ Just redeploy when changes are made
- ✅ Use `databricks apps deploy` to apply updates

### 5. **Always Use Secret Scope for Credentials**
- ✅ Scope: `lakemeter-credentials`
- ✅ Key: `lakebase-password`
- ✅ Usage: `dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")`
- ❌ Never hardcode: `***REMOVED_DATABASE_CREDENTIAL***` (old password)

---

## 🗂️ Project Structure

### Main Folders
```
database_backend/
├── Lakebase_Setup/
│   ├── 00_Lakebase_Config.py          # Main config (imports this for credentials)
│   ├── 1_Setup/                       # Setup scripts
│   ├── 2_Tests/                       # Test notebooks
│   ├── 3_Debug/                       # Debug scripts
│   └── release_2/                     # Backfill & API integration
├── Salesforce_Sync/                   # Salesforce integration
└── steven_api_backend/                # FastAPI backend
```

### Databricks Workspace Paths
```
/Workspace/Users/steven.tan@databricks.com/lakemeter/
├── database_backend/Lakebase_Setup/
├── Lakebase_Setup/release_2/
├── Salesforce_Sync/
└── steven_api_backend/                  # FastAPI backend app source
```

---

## 🔐 Secrets Configuration

### Secret Scope: `lakemeter-credentials`
```
lakebase-password      → Stored securely (never print/expose)
lakebase-host          → instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com
lakebase-user          → lakemeter_sync_role
lakebase-database      → lakemeter_pricing
azure-storage-key      → Azure Storage access key for Salesforce sync
```

### How Notebooks Access Credentials
```python
# Method 1: Import config (recommended)
%run ./00_Lakebase_Config

# Method 2: Direct access
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")
```

---

## 🖥️ Databricks Apps Runtime Environment

Docs: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env

| Component | Version |
|-----------|---------|
| OS | Ubuntu 22.04 LTS |
| Python | 3.11 (dedicated venv) |
| Node.js | 22.16 |
| npm | Available (no libraries pre-installed) |
| uv | 0.10.2 |
| Resources | 2 vCPUs, 6 GB RAM (default, configurable) |

**Auto-set env vars**: `DATABRICKS_HOST`, `DATABRICKS_APP_PORT`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, `DATABRICKS_APP_NAME`, `DATABRICKS_WORKSPACE_ID`

**Key implication**: `app.yaml` command can run `cd frontend && npm ci && npm run build` before starting uvicorn — no need to sync pre-built static assets. Frontend builds from source during app startup.

---

## 🚀 Deployment

### Lakemeter OSS App (Primary)

**App Name:** `lakemeter-oss`  
**App URL:** `https://lakemeter-oss-335310294452632.aws.databricksapps.com`  
**Workspace Source Path:** `/Workspace/Users/steven.tan@databricks.com/lakemeter_app`  
**Local Source:** `lakemeter_app/`

**CRITICAL: Use the `lakemeter-deploy` skill for ALL deployments.**  
The skill ensures only essential files (backend/ + app.yaml) are in the workspace source path.  
Having non-essential files (frontend/node_modules, docs, tests, ETL) causes 20-30min snapshot times or timeout failures.

**Quick deploy commands:**
```bash
# 1. Build frontend (if frontend changed)
cd lakemeter_app/frontend && npm run build

# 2. Upload backend + app.yaml ONLY
databricks workspace import-dir --profile lakemeter \
  lakemeter_app/backend \
  /Workspace/Users/steven.tan@databricks.com/lakemeter_app/backend \
  --overwrite

# 2b. Force-upload index.html (import-dir sometimes skips it)
databricks workspace import --profile lakemeter --format AUTO \
  --file lakemeter_app/backend/static/index.html \
  /Workspace/Users/steven.tan@databricks.com/lakemeter_app/backend/static/index.html \
  --overwrite

# 3. Deploy
databricks apps deploy lakemeter-oss --profile lakemeter
```

**Workspace must ONLY contain:** `backend/` and `app.yaml`. Nothing else.  
ETL notebooks go to: `/Workspace/Users/steven.tan@databricks.com/lakemeter/etl`

### Legacy App (lakemeter-api)

**App Name:** `lakemeter-api`  
**App URL:** `https://lakemeter-api-335310294452632.aws.databricksapps.com`  
**Workspace Path:** `/Workspace/Users/steven.tan@databricks.com/lakemeter/steven_api_backend`

### Upload Notebooks
```bash
# Upload single notebook
databricks workspace import --profile lakemeter \
  --language PYTHON --format SOURCE \
  --file "/local/path/notebook.py" \
  "/Workspace/Users/steven.tan@databricks.com/lakemeter/path/notebook" \
  --overwrite

# Create folders first if needed
databricks workspace mkdirs --profile lakemeter "/Workspace/path/to/folder"
```

---

## 🎯 Common Tasks

### Task: Update Notebooks
1. ✅ Make changes to local files
2. ✅ Upload to workspace using CLI
3. ✅ User tests in workspace
4. ❌ DO NOT create summary markdown files

### Task: Update API (app.py / validators.py)
1. ✅ Modify local files in `database_backend/steven_api_backend/`
2. ✅ Sync to workspace: `/Workspace/Users/steven.tan@databricks.com/lakemeter/steven_api_backend/`
3. ✅ Redeploy app: `databricks apps deploy lakemeter-api --profile lakemeter`
4. ✅ Test endpoint at `https://lakemeter-api-335310294452632.aws.databricksapps.com`
5. ❌ DO NOT restart app, just redeploy

### Task: Fix Credentials
1. ✅ Use `dbutils.secrets.get()` 
2. ✅ Never hardcode passwords
3. ✅ Use `printf` (not `echo`) when adding secrets via CLI

### Task: Database Schema Changes
1. ✅ Create SQL or Python notebook
2. ✅ Test locally if possible
3. ✅ Upload to workspace for execution
4. ❌ DO NOT create migration documentation unless requested

---

## 💡 Tips

- Always check existing files before creating new ones
- Prefer editing over creating
- Use `--overwrite` flag when uploading notebooks
- Keep responses concise - user knows what they want
- Only ask clarifying questions when truly necessary

---

**Last Updated:** 2026-04-05  
**Project:** Lakemeter - Databricks Cost Estimation Tool  
**GitHub:** `https://github.com/steven-tan_data/lakemeter-opensource`
