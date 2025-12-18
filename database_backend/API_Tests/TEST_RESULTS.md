# Lakemeter API - Test Results & Status

## ✅ SUCCESS: OAuth Authentication Working!

**Date:** December 17, 2025  
**Reference:** [Databricks Apps Cookbook - Local Connections](https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_local)

---

## Authentication Setup (Complete ✅)

### What We Did

1. **Created OAuth Profile:**
   ```bash
   databricks auth login \
     --host https://fe-vm-lakemeter.cloud.databricks.com \
     --profile lakemeter-oauth
   ```
   ✅ Result: `Profile lakemeter-oauth was successfully saved`

2. **Got OAuth Token:**
   ```bash
   databricks auth token --profile lakemeter-oauth
   ```
   ✅ Result: JWT token starting with `eyJ...` (expires in 1 hour, auto-refreshed)

3. **Tested API Endpoints:**
   - ✅ `/health` → **200 OK** (database healthy)
   - ✅ `/api/v1/regions?cloud=AWS` → **200 OK** (17 regions returned)
   - ❌ `/api/v1/calculate/jobs-classic` → **500 Internal Server Error**

---

## Test Results Summary

| Endpoint | Method | Status | Result |
|----------|--------|--------|--------|
| `/health` | GET | ✅ 200 | `{"status": "healthy", "database_exists": true, "database_healthy": true}` |
| `/api/v1/regions` | GET | ✅ 200 | Returns AWS regions list |
| `/api/v1/calculate/jobs-classic` | POST | ❌ 500 | Internal Server Error |

### Authentication Confirmation

All requests included proper authentication headers:
```
gap-auth: steven.tan@databricks.com
```
✅ **OAuth authentication is working correctly!**

---

## Issue Found: 500 Error on Calculate Endpoint

**Problem:** The `/api/v1/calculate/jobs-classic` endpoint returns `500 Internal Server Error`

**Not an authentication issue** - auth headers are correct (`gap-auth` shows user)

**Possible Causes:**
1. Database function `lakemeter.calculate_line_item_costs()` might have an error
2. Parameter mismatch between API and database function
3. Missing data in database tables (e.g., VM costs, DBU rates)
4. Database permissions issue

---

## How to Test Locally

### ✅ Working Method (OAuth)

```bash
# 1. Set up OAuth (one-time)
databricks auth login \
  --host https://fe-vm-lakemeter.cloud.databricks.com \
  --profile lakemeter-oauth

# 2. Test with Python
python3 test_api_local.py
```

**Result:**
- Health check: ✅ Works
- Regions API: ✅ Works  
- Calculate API: ❌ 500 error (not auth related)

### ❌ What Doesn't Work

```bash
# PAT tokens don't work with Databricks Apps
# Your existing profile uses PAT (dapi...), not OAuth
databricks auth token --profile lakemeter  # ❌ PAT token
```

**Why:** Databricks Apps require OAuth tokens, not PAT tokens.

---

## Testing from Databricks Notebooks

### Setup (Already Complete ✅)

The test notebooks are ready at:
```
/Users/steven.tan@databricks.com/lakemeter/API_Tests/
├── 00_API_Config.py           # Configuration & helper functions
├── Test_API_01_JOBS_Classic.py  # 12 comprehensive tests
├── AUTH_GUIDE.md               # Authentication documentation
└── TEST_RESULTS.md             # This file
```

### How to Run

1. Open `/lakemeter/API_Tests/Test_API_01_JOBS_Classic` in Databricks
2. Run all cells
3. OAuth token is retrieved automatically via `dbutils`

**Expected Results:**
- ✅ Connection test should work (if you get 401, see troubleshooting)
- ❌ Calculate tests will fail with 500 error (not an auth issue)

---

## Next Steps: Debugging the 500 Error

### Option 1: Test Database Function Directly (Recommended)

Run this in a Databricks SQL notebook:

```sql
SELECT * FROM lakemeter.calculate_line_item_costs(
    'JOBS',           -- workload_type
    'AWS',            -- cloud
    'us-east-1',      -- region  
    'PREMIUM',        -- tier
    FALSE,            -- serverless_enabled
    FALSE,            -- photon_enabled
    NULL,             -- dlt_edition
    'm5.xlarge',      -- driver_node_type
    'm5.xlarge',      -- worker_node_type
    10,               -- num_workers
    'on_demand',      -- driver_pricing_tier
    'on_demand',      -- worker_pricing_tier
    8,                -- runs_per_day
    60,               -- avg_runtime_minutes
    30,               -- days_per_month
    NULL,             -- hours_per_month
    'standard',       -- serverless_mode
    NULL,             -- dbsql_warehouse_type
    NULL,             -- dbsql_warehouse_size
    1,                -- dbsql_num_clusters
    'on_demand',      -- dbsql_vm_pricing_tier
    NULL,             -- vector_search_mode
    0,                -- vector_search_capacity_millions
    NULL,             -- model_serving_gpu_type
    NULL,             -- fmapi_model
    NULL,             -- fmapi_provider
    'global',         -- fmapi_endpoint_type
    'all',            -- fmapi_context_length
    'input_token',    -- fmapi_rate_type
    0,                -- fmapi_quantity
    0,                -- lakebase_cu
    1,                -- lakebase_ha_nodes
    'NA',             -- driver_payment_option
    'NA',             -- worker_payment_option
    'NA'              -- dbsql_vm_payment_option
);
```

**If this works:** The issue is in the API code  
**If this fails:** The issue is in the database function or data

### Option 2: Check Required Data

Verify these tables have data for AWS/us-east-1:

```sql
-- Check DBU rates
SELECT * FROM lakemeter.sync_pricing_dbu_rates 
WHERE cloud = 'AWS' AND region = 'us-east-1' AND sku_name LIKE '%JOBS%';

-- Check VM costs
SELECT * FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'AWS' AND region = 'us-east-1' AND instance_type = 'm5.xlarge';

-- Check instance DBU rates
SELECT * FROM lakemeter.sync_ref_instance_dbu_rates 
WHERE cloud = 'AWS' AND instance_type = 'm5.xlarge';
```

### Option 3: Add Error Logging to API

Update `app.py` to catch and log the specific error:

```python
try:
    result = await db.execute(query, {...})
    # ... rest of code
except Exception as e:
    print(f"❌ Database error: {str(e)}")
    print(f"   Type: {type(e)}")
    raise HTTPException(status_code=500, detail=str(e))
```

Then redeploy and test again.

---

## Summary

### ✅ What's Working
1. **OAuth Authentication** - Local machine can authenticate to Databricks Apps
2. **API Infrastructure** - App is deployed and running
3. **Database Connection** - Health check confirms DB is connected
4. **Data APIs** - Regions, tiers, instance types all work

### ❌ What's Not Working
1. **Calculate Endpoint** - Returns 500 error (not auth-related)
2. **Root Cause Unknown** - Need to test database function directly

### 🎯 Recommended Action
**Test the database function directly in Databricks SQL** to see if it returns results or errors. This will immediately tell us if the issue is:
- In the database function code
- In the database data (missing records)
- In the API parameter mapping

---

## Local Testing Commands

```bash
# Get OAuth token and test
python3 test_api_local.py

# Or manual curl test
OAUTH_TOKEN=$(databricks auth token --profile lakemeter-oauth 2>&1 | grep '"access_token"' | cut -d'"' -f4)

curl -H "Authorization: Bearer $OAUTH_TOKEN" \
  "https://lakemeter-api-335310294452632.aws.databricksapps.com/health"
```

---

## Questions?

1. **Where are the test notebooks?**  
   `/Users/steven.tan@databricks.com/lakemeter/API_Tests/`

2. **How do I set up OAuth locally?**  
   `databricks auth login --host <workspace-url> --profile lakemeter-oauth`

3. **Why doesn't my PAT token work?**  
   Databricks Apps only accept OAuth tokens, not PAT tokens

4. **Can I test without OAuth setup?**  
   Yes! Use the Databricks notebooks - OAuth is automatic there

5. **What's causing the 500 error?**  
   Unknown - need to test the database function directly (see "Next Steps" above)

---

**Created:** December 17, 2025  
**Status:** OAuth authentication ✅ Working | Calculate endpoint ❌ Needs debugging  
**Next:** Test database function directly in SQL

