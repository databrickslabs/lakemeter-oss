# Claude AI Assistant - Project Context & Rules

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

### 1. **DO NOT Create Unnecessary Markdown Files**
- ❌ Don't create documentation files unless explicitly requested
- ❌ Don't create README files proactively
- ❌ Don't create summary files after completing tasks
- ✅ Only create markdown when user explicitly asks for it

### 2. **DO NOT Create Unnecessary Notebooks**
- ❌ If user asks for "SQL code", give SQL code directly - don't wrap it in a notebook
- ❌ Don't create notebooks for simple queries or checks
- ✅ Only create notebooks when explicitly requested or for complex operations
- ✅ For simple SQL queries, just provide the SQL code

### 3. **DO NOT Restart Databricks Apps**
- ❌ Don't suggest restarting the app
- ❌ Don't run commands to restart services
- ✅ Just redeploy when changes are made
- ✅ Use `databricks apps deploy` to apply updates

### 4. **Always Use Secret Scope for Credentials**
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
└── Lakebase_Setup/release_2/
```

---

## 🔐 Secrets Configuration

### Secret Scope: `lakemeter-credentials`
```
lakebase-password   → Stored securely (never print/expose)
lakebase-host       → instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com
lakebase-user       → lakemeter_sync_role
lakebase-database   → lakemeter_pricing
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
```bash
# Deploy updates (DO NOT RESTART)
databricks apps deploy <app-name> --profile lakemeter

# Check app status
databricks apps list --profile lakemeter
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

**Last Updated:** 2026-01-31  
**Project:** Lakemeter - Databricks Cost Estimation Tool
