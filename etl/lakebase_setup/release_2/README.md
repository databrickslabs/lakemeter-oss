# Release 2: Cost Calculation Response Storage + New Workload Types

## Overview

This release adds:
1. Full API calculation response storage for detailed cost analysis
2. Support for 8 new workload types (25 new columns)

## Database Configuration

- **Database:** `lakemeter_pricing`
- **Schema:** `lakemeter`
- **Line Items Tables:** 
  - Main: `lakemeter.line_items`
  - Backup: `lakemeter.line_items_backup_20260114`
- **Estimates Tables:**
  - Main: `lakemeter.estimates`
  - Backup: `lakemeter.estimates_backup_20260119`

**Important:** Notebooks automatically use the correct estimates table:
- When processing `line_items` → joins with `estimates`
- When processing `line_items_backup_20260114` → joins with `estimates_backup_20260119`

## Supported Workload Types

The notebooks support the following workload types:

### ✅ Included in Backfill:
- **JOBS** (Classic/Serverless)
- **ALL_PURPOSE** (Classic/Serverless)
- **DLT** (Classic/Serverless)
- **DBSQL** (Classic/Pro/Serverless)
- **FMAPI** (legacy - routes by provider)
- **FMAPI_DATABRICKS** (split type - direct routing)
- **LAKEBASE**
- **DATABRICKS_APPS** (medium/large sizes)
- **CLEAN_ROOM** (collaborator-based)
- **AI_PARSE** (DBU or pages+complexity)

### ⚠️ Excluded from Backfill (Validation Only):
- **VECTOR_SEARCH** (schema migration required - missing `vector_capacity_millions`)
- **MODEL_SERVING** (pending review)
- **FMAPI_PROPRIETARY** (schema migration required - missing `fmapi_rate_type`, `fmapi_quantity`)

### Required Fields by Workload Type

#### Important Notes on Optional Fields
- **LAKEBASE**: `lakebase_storage_gb` is optional (defaults to 0)
- **DLT Serverless**: `dlt_edition` is optional (API defaults to 'core')
- **DLT Classic**: `dlt_edition` is required

### Schema Version Compatibility

The validation notebook automatically detects which columns exist in your tables:

**If you have OLD schema (backup tables):**
- Missing: `vector_capacity_millions`, `fmapi_rate_type`, `fmapi_quantity`
- Validation will SKIP VECTOR_SEARCH and FMAPI workload types
- You'll need schema migration before backfilling these types

**If you have NEW schema (main table after Release 2):**
- All columns present
- Full validation for all 13 workload types

The notebook will show warnings for any skipped workload types.

#### New Workload Types (Release 2)
- **DATABRICKS_APPS**: `databricks_apps_size`, `databricks_apps_hours_per_month` (or `hours_per_month`)
- **CLEAN_ROOM**: `clean_room_num_collaborators`, `clean_room_days_per_month` (or `days_per_month`)
- **AI_PARSE**: Either:
  - Method 1: `ai_parse_dbu_quantity` (set `ai_parse_calculation_method` = 'dbu')
  - Method 2: `ai_parse_num_pages` + `ai_parse_complexity` (set `ai_parse_calculation_method` = 'pages')

## Notebooks

### 📓 00_Validate_Line_Items_For_Backfill ⭐ RUN THIS FIRST
- **What:** Validates line items before backfill (NO data modification)
- **Target:** Configurable (main or backup table)
- **Checks:** 
  - ✅ Join with estimates table (cloud, region, tier)
  - ✅ API endpoint mapping for each workload type
  - ✅ Required fields present
  - ✅ Summary by workload type
- **Use when:** BEFORE running backfill to ensure data quality
- **Output:** Detailed validation report with % ready for backfill

### 📓 01_Add_Cost_Calculation_Columns
- **What:** Adds cost calculation columns only
- **Target:** Both main and backup tables
- **Columns:** 2 (cost_calculation_response, calculation_completed_at)
- **Use when:** You only need cost calculation columns

### 📓 02_Backfill_Line_Item_Costs
- **What:** Calculates costs for existing line items
- **Target:** Configurable (main or backup table)
- **Use when:** After validation shows 100% ready
- **Features:** 
  - Widgets for testing, progress tracking, error handling
  - Databricks authentication (automatic token)
  - Configurable to exclude certain workload types
  - Status filtering (pending/error/all)

### 📓 03_Add_New_Workload_Columns ⭐ RECOMMENDED FOR NEW INSTALL
- **What:** Adds ALL new columns (workload + cost calculation)
- **Target:** Main table only (`lakemeter.line_items`)
- **Columns:** 27 total (25 workload + 2 cost calculation)
- **Use when:** Clean installation or adding everything at once
- **Benefit:** One-click installation of all Release 2 features

## What's New

### 1. New Columns Added

**Tables:**
- `lakemeter.line_items`
- `lakemeter.line_items_backup`

**Columns:**
- `cost_calculation_response` (JSONB): Full API response with detailed cost breakdown
- `calculation_completed_at` (TIMESTAMP): When the calculation was completed

### 2. Response Structure

```json
{
  "success": true,
  "data": {
    "cost_per_month": 5000.00,
    "dbu_per_month": 1000.0,
    "dbu_per_hour": 33.33,
    "hours_per_month": 160.0,
    "vm_costs": {
      "driver_vm_cost_per_hour": 0.5922,
      "worker_vm_cost_per_hour": 1.9992,
      "total_vm_cost_per_hour": 2.5914,
      "vm_cost_per_month": 414.62
    },
    "sku_breakdown": [
      {
        "sku_name": "PREMIUM_JOBS_COMPUTE",
        "quantity": 1000,
        "unit_price": 0.55,
        "total_cost": 550.00
      }
    ],
    "discount_summary": {
      "total_discount_amount": 100.00,
      "total_discount_percentage": 18.2
    }
  }
}
```

For errors:
```json
{
  "success": false,
  "error": {
    "message": "Invalid instance type",
    "code": "INVALID_INSTANCE_TYPE",
    "failed_at": "2026-01-25T10:30:00"
  }
}
```

## Installation Steps

### Option A: Combined Installation (Recommended for New Install)

**Step 1:** Run notebook `03_Add_New_Workload_Columns`
- Adds all 27 new columns at once
- Target: Main table only

**Step 2:** Run notebook `00_Validate_Line_Items_For_Backfill`
- Validates data before backfill
- Checks mapping and required fields
- **CRITICAL:** Must show 100% ready before proceeding

**Step 3:** Run notebook `02_Backfill_Line_Item_Costs`
- Test with backup table first (limit: 10)
- Then run on main table (limit: 0 for all)

### Option B: Separate Installation (For Existing Tables)

**Step 1:** Run notebook `01_Add_Cost_Calculation_Columns`
- Adds to both main and backup tables
- Creates indexes and comments

**Step 2:** Run notebook `00_Validate_Line_Items_For_Backfill` ⚠️ CRITICAL
- Validates ALL workload types (including excluded ones)
- Shows which items are ready for backfill
- Identifies data issues before processing

**Step 3:** Run notebook `02_Backfill_Line_Item_Costs`
- Start with backup table (test mode)
- Automatically EXCLUDES: VECTOR_SEARCH, MODEL_SERVING, FMAPI_PROPRIETARY
- Processes ~10 out of 13 workload types
- Then backfill main table

**⚠️ Important:** The backfill will skip 3 workload types that need schema migration.
These can be processed later after updating the table schema.

## Authentication Setup (M2M)

The backfill notebook uses **Machine-to-Machine (M2M) authentication** with a Databricks service principal to connect to the Lakemeter API app.

**Why M2M?** Databricks Apps require service principal authentication for external/notebook connections ([documentation](https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_external)).

### Setup Instructions:

#### Step 1: Create Service Principal

1. **Go to Databricks workspace** → **Settings** → **Identity and access**
2. **Click "Service principals"** → **"Add service principal"**
3. **Name:** `lakemeter-backfill-sp` (or any name)
4. **Click "Generate secret"**
5. **Copy:**
   - Client ID (Application ID): `abc123-xyz...`
   - Client Secret: `dapi...` (shown only once!)

#### Step 2: Grant Permissions on API App

1. **Go to "Apps"** → Find **"lakemeter-api"**
2. **Click "Permissions"** or **"Manage permissions"**
3. **Add service principal:** `lakemeter-backfill-sp`
4. **Grant:** `CAN USE` permission
5. **Save**

#### Step 3: Configure Notebook Widgets

Add credentials to the backfill notebook widgets:

```
5. Databricks Host: https://fe-vm-lakemeter.cloud.databricks.com
6. Service Principal Client ID: [paste client ID]
7. Service Principal Secret: [paste secret]
```

### How M2M Authentication Works:

```python
from databricks.sdk import WorkspaceClient

# Create authenticated client
wc = WorkspaceClient(
    host="https://fe-vm-lakemeter.cloud.databricks.com",
    client_id="<CLIENT_ID>",
    client_secret="<CLIENT_SECRET>"
)

# Get authentication headers (OAuth2 token)
headers = wc.config.authenticate()

# Use in API calls
response = requests.post(api_url, json=payload, headers=headers)
```

### Authentication Test

The notebook tests M2M authentication before backfill:
```
AUTHENTICATION SETUP (M2M)
===============================================
🔐 Authenticating with Service Principal (M2M)...
   Creating WorkspaceClient...
   Host: https://fe-vm-lakemeter.cloud.databricks.com
   Client ID: abc12345...
   Authenticating...

✅ AUTHENTICATION SUCCESSFUL
   Method: Service Principal (M2M)
   Headers configured: ['Authorization']
===============================================
```

### Troubleshooting

#### 401 Unauthorized

If you see `HTTP 401: Unauthorized`:
1. **Service Principal not configured** - Check widgets 6 & 7 are filled
2. **Missing app permission** - Grant service principal `CAN USE` on app
3. **Wrong credentials** - Verify client ID and secret are correct
4. **Wrong workspace** - Ensure host URL matches your workspace

#### Authentication Failed

If authentication fails during setup:
1. **Check service principal exists** - Go to Settings → Identity and access → Service principals
2. **Regenerate secret if needed** - Old secrets expire or get revoked
3. **Check workspace URL** - Must include `https://` and be exact match
4. **Install databricks-sdk** - Notebook auto-installs, but check if it works

#### Permission Denied

If service principal can't access app:
1. **Go to Apps** → **lakemeter-api** → **Permissions**
2. **Add your service principal**
3. **Grant `CAN USE` permission**
4. **Wait 1-2 minutes** for permissions to propagate

**Configuration Widgets:**
- **Table to Process**: `backup` or `main` (start with backup!)
- **Status Filter**: `pending`, `error`, or `all`
- **Limit**: Number of items to process (0 = all)
- **API Base URL**: `http://localhost:8000` (or your API endpoint)

**Recommended Testing Sequence:**
```
1. Test on backup with limit=5
2. Test on backup with limit=10
3. Run full backup (limit=0)
4. Test on main with limit=5
5. Run full main (limit=0)
```

## Query Examples

### Get Successful Calculations

```sql
SELECT 
    line_item_id,
    workload_name,
    workload_type,
    (cost_calculation_response->'data'->>'cost_per_month')::numeric as monthly_cost,
    calculation_completed_at
FROM lakemeter.line_items
WHERE cost_calculation_response->>'success' = 'true'
ORDER BY monthly_cost DESC;
```

### Get DBU and VM Cost Breakdown

```sql
SELECT 
    line_item_id,
    workload_name,
    cost_calculation_response->'data'->>'dbu_per_month' as dbu_per_month,
    cost_calculation_response->'data'->'vm_costs'->>'vm_cost_per_month' as vm_cost_per_month,
    cost_calculation_response->'data'->>'cost_per_month' as total_monthly_cost
FROM lakemeter.line_items
WHERE cost_calculation_response->>'success' = 'true'
  AND workload_type IN ('JOBS', 'ALL_PURPOSE');
```

### Check for Errors

```sql
SELECT 
    line_item_id,
    workload_name,
    workload_type,
    cost_calculation_response->'error'->>'message' as error_message,
    cost_calculation_response->'error'->>'code' as error_code,
    calculation_completed_at
FROM lakemeter.line_items
WHERE cost_calculation_response->>'success' = 'false'
ORDER BY calculation_completed_at DESC;
```

### Sum Costs by Estimate

```sql
SELECT 
    e.estimate_name,
    e.customer_name,
    COUNT(li.line_item_id) as line_item_count,
    SUM((li.cost_calculation_response->'data'->>'cost_per_month')::numeric) as total_monthly_cost,
    SUM((li.cost_calculation_response->'data'->>'dbu_per_month')::numeric) as total_dbu_per_month
FROM lakemeter.estimates e
JOIN lakemeter.line_items li ON e.estimate_id = li.estimate_id
WHERE li.cost_calculation_response->>'success' = 'true'
GROUP BY e.estimate_id, e.estimate_name, e.customer_name
ORDER BY total_monthly_cost DESC;
```

### Get SKU Breakdown for a Line Item

```sql
SELECT 
    line_item_id,
    workload_name,
    jsonb_array_elements(cost_calculation_response->'data'->'sku_breakdown') as sku
FROM lakemeter.line_items
WHERE line_item_id = '<your-line-item-id>'
  AND cost_calculation_response->>'success' = 'true';
```

### Check Calculation Status

```sql
SELECT 
    CASE 
        WHEN cost_calculation_response IS NULL THEN 'pending'
        WHEN cost_calculation_response->>'success' = 'true' THEN 'success'
        WHEN cost_calculation_response->>'success' = 'false' THEN 'error'
        ELSE 'unknown'
    END as status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM lakemeter.line_items
GROUP BY 1
ORDER BY count DESC;
```

## Benefits

### 1. Detailed Cost Analysis
- Full breakdown of DBU vs VM costs
- SKU-level details
- Discount information
- Hourly and monthly metrics

### 2. Historical Tracking
- Timestamp of each calculation
- Ability to recalculate and compare
- Audit trail of cost changes

### 3. Error Tracking
- Failed calculations are stored
- Error messages and codes preserved
- Easy to identify and fix issues

### 4. Flexible Querying
- JSONB allows complex queries
- GIN index for fast lookups
- No need to add new columns for new metrics

### 5. API-First Design
- Direct storage of API responses
- Consistent with API structure
- Easy to sync with API changes

## Maintenance

### Recalculate Costs

When line items change, recalculate costs:

```sql
-- Mark line items as needing recalculation
UPDATE lakemeter.line_items
SET cost_calculation_response = NULL
WHERE line_item_id = '<line-item-id>';

-- Then run backfill notebook with status_filter='pending'
```

### Bulk Recalculation

```sql
-- Recalculate all line items in an estimate
UPDATE lakemeter.line_items
SET cost_calculation_response = NULL
WHERE estimate_id = '<estimate-id>';

-- Recalculate all items for a specific workload type
UPDATE lakemeter.line_items
SET cost_calculation_response = NULL
WHERE workload_type = 'JOBS';
```

## Troubleshooting

### All calculations show as errors

**Check:**
1. API server is running and accessible
2. API base URL is correct in widget
3. Line items have all required fields
4. Estimates have valid cloud/region/tier

### Slow performance

**Solutions:**
1. Use `--limit` to process in smaller batches
2. Check API server logs for slow endpoints
3. Ensure indexes are created (GIN + B-tree)
4. Run backfill during off-hours

### Different workload types failing

**Check:**
1. Endpoint mapping is correct
2. Required fields are populated for that workload type
3. API endpoint is working (test with curl)

## Rollback

If needed, remove the columns:

```sql
ALTER TABLE lakemeter.line_items 
DROP COLUMN cost_calculation_response,
DROP COLUMN calculation_completed_at;

ALTER TABLE lakemeter.line_items_backup 
DROP COLUMN cost_calculation_response,
DROP COLUMN calculation_completed_at;
```

## Links

- **Databricks Workspace**: https://fe-vm-lakemeter.cloud.databricks.com
- **Notebook Path**: `/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/release_2/`
- **API Documentation**: `database_backend/API_Design/API_DESIGN_PLAN.md`

## Support

For issues or questions, contact the Lakemeter team.
