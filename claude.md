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
- ❌ Never hardcode: `Lak3m3t3r_Sync_2024!` (old password)

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

## 🚀 Deployment

### Databricks App Deployment

**App Name:** `lakemeter-api`  
**App URL:** `https://lakemeter-api-335310294452632.aws.databricksapps.com`  
**Workspace Path:** `/Workspace/Users/steven.tan@databricks.com/lakemeter/steven_api_backend`

**Deployment Workflow (3 Steps):**
```bash
# Step 1: Modify local files
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/database_backend/steven_api_backend"
# Edit app.py, validators.py, etc.

# Step 2: Sync to workspace
databricks workspace import --profile lakemeter \
  --file app.py \
  /Workspace/Users/steven.tan@databricks.com/lakemeter/steven_api_backend/app.py \
  --overwrite

databricks workspace import --profile lakemeter \
  --file validators.py \
  /Workspace/Users/steven.tan@databricks.com/lakemeter/steven_api_backend/validators.py \
  --overwrite

# Step 3: Redeploy app (DO NOT RESTART)
databricks apps deploy lakemeter-api --profile lakemeter
```

**Check app status:**
```bash
databricks apps list --profile lakemeter
databricks apps get lakemeter-api --profile lakemeter
```

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
