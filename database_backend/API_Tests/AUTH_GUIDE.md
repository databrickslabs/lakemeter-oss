# Authentication Guide for Lakemeter API

## Problem: 401 Unauthorized

The Lakemeter API is deployed as a **Databricks App**, which requires **OAuth authentication**, not Personal Access Tokens (PAT).

### Why PAT Tokens Don't Work

According to the [Databricks Apps Cookbook](https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_local):

> "While the FastAPI application running locally on http://127.0.0.1:8000 does not require a valid bearer token, this token is required for accessing Databricks Apps via the secured HTTPS URL with `/api` endpoints."

**Databricks Apps use OAuth**, not PAT tokens.

---

## Solution 1: Use Databricks Notebooks (Recommended)

✅ **This is the easiest and recommended approach!**

Databricks notebooks automatically have OAuth tokens available.

**Steps:**
1. Open: `/Users/steven.tan@databricks.com/lakemeter/API_Tests/`
2. Run: `00_API_Config`
3. Run: `Test_API_01_JOBS_Classic`

**Why this works:**
- Databricks notebooks run inside the workspace
- OAuth token is automatically available via `dbutils`
- No manual authentication needed

---

## Solution 2: Set Up OAuth Authentication for Local Testing

If you want to test from your local machine, you need to configure OAuth authentication.

### Step 1: Configure OAuth Profile

```bash
# Create an OAuth-based profile
databricks auth login \
  --host https://fe-vm-lakemeter.cloud.databricks.com \
  --profile lakemeter-oauth

# This will open a browser for OAuth authentication
```

### Step 2: Update Test Script

The test script will automatically use the OAuth token:

```python
from databricks.sdk.core import Config

config = Config(profile="lakemeter-oauth")
token = config.oauth_token().access_token  # This gets OAuth token
```

### Step 3: Run Tests

```bash
python3 test_api_local.py
```

---

## Solution 3: Test via Swagger UI (in Browser)

If you're already logged into Databricks in your browser:

1. **Open:** `https://lakemeter-api-335310294452632.aws.databricksapps.com/docs`
2. **You'll be redirected to login** if not authenticated
3. **After login:** You can use "Try it out" to test endpoints
4. **OAuth is handled automatically** by the browser session

---

## Current Configuration Status

### Your CLI Profile (`lakemeter`)
```ini
[lakemeter]
host  = https://fe-vm-lakemeter.cloud.databricks.com
token = dapi...  # ❌ PAT token - doesn't work with Databricks Apps
```

### What You Need
```ini
[lakemeter-oauth]
host  = https://fe-vm-lakemeter.cloud.databricks.com
# OAuth credentials stored securely by Databricks CLI
# ✅ OAuth authentication - works with Databricks Apps
```

---

## Comparison: PAT vs OAuth

| Feature | PAT Token | OAuth Token |
|---------|-----------|-------------|
| **Works with Databricks API** | ✅ Yes | ✅ Yes |
| **Works with Databricks Apps** | ❌ No | ✅ Yes |
| **Format** | `dapi...` | JWT token |
| **Expires** | Configurable | Auto-refreshed |
| **Setup** | Manual creation | CLI login |

---

## Recommended Workflow

### For Development & Testing
**Use Databricks Notebooks** - no setup needed, OAuth automatic

### For CI/CD & Automation
**Use OAuth authentication** with service principals

### For Quick Manual Testing
**Use Swagger UI** in browser - OAuth handled by browser session

---

## Testing Checklist

- [ ] **Option A:** Test in Databricks Notebook (easiest)
  - Open `/lakemeter/API_Tests/Test_API_01_JOBS_Classic`
  - Run all cells
  - OAuth handled automatically

- [ ] **Option B:** Set up OAuth locally
  - Run `databricks auth login --host ... --profile lakemeter-oauth`
  - Update test script to use `lakemeter-oauth` profile
  - Run `python3 test_api_local.py`

- [ ] **Option C:** Test in browser
  - Open API Swagger UI
  - Login with Databricks credentials
  - Use "Try it out" feature

---

## Why This Matters

**Databricks Apps** are designed to be secure, workspace-integrated applications. They:
- Run inside your Databricks workspace
- Use workspace authentication (OAuth)
- Respect workspace permissions
- Cannot be accessed with PAT tokens from outside

This is a **security feature**, not a bug!

---

## Next Steps

✅ **Easiest:** Just use the Databricks notebooks we created
- No authentication setup needed
- Works immediately
- Full test suite available

🔧 **For local testing:** Set up OAuth authentication
- One-time setup
- More flexible for development
- Requires CLI configuration

📊 **For quick tests:** Use Swagger UI in browser
- No setup at all
- Limited to manual testing
- Good for quick checks

---

## Questions?

If you're still having issues:

1. **Check permissions:** Does your user have `CAN_USE` on the app?
   ```bash
   databricks apps get lakemeter-api --profile lakemeter
   ```

2. **Verify app is running:**
   ```bash
   databricks apps list --profile lakemeter | grep lakemeter-api
   ```

3. **Test with OAuth:** Follow Solution 2 above to set up OAuth authentication

---

**Remember:** The Databricks notebooks are the easiest way to test - they handle all authentication automatically! 🎯

