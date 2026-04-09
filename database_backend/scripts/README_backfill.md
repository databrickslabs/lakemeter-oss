# Backfill Line Item Cost Calculation Responses

## Overview

This script calculates costs for all line items by calling the appropriate calculation API endpoints and storing the full response in the `cost_calculation_response` JSONB column.

## Setup

### 1. Add Columns to Database

First, run the SQL script to add the new columns:

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d lakemeter

# Run the SQL file
\i database_backend/Lakebase_Setup/1_Setup/01d_Add_Cost_Calculation_Columns.sql
```

Or run from Databricks notebook if you have the Lakebase connection setup.

### 2. Install Python Dependencies

```bash
cd /Users/steven.tan/Desktop/Ent\ 1\ -\ Q4\ FY\ 2026\ Team\ Project/database_backend

# Install if not already installed
pip install httpx sqlalchemy asyncpg
```

## Usage

### Test on Backup Table First (Recommended)

```bash
# Test with 5 items on backup table
python scripts/backfill_line_item_costs.py pending --table backup --limit 5

# Test with 10 items
python scripts/backfill_line_item_costs.py pending --table backup --limit 10

# Test ALL pending items on backup
python scripts/backfill_line_item_costs.py pending --table backup
```

### Run on Main Table

```bash
# Process all pending items
python scripts/backfill_line_item_costs.py pending --table main

# Re-process all error items
python scripts/backfill_line_item_costs.py error --table main

# Re-process stale items (line items that changed after calculation)
python scripts/backfill_line_item_costs.py stale --table main

# Re-calculate EVERYTHING (including success)
python scripts/backfill_line_item_costs.py all --table main
```

## Status Values

- **`pending`**: Line item has not been calculated yet (default)
- **`success`**: Calculation completed successfully, response stored
- **`error`**: Calculation failed, error message stored
- **`stale`**: Line item was modified after calculation, needs recalculation

## Query Examples

### Get Cost from Response

```sql
-- Get total monthly cost
SELECT 
    line_item_id,
    workload_name,
    workload_type,
    (cost_calculation_response->'data'->>'cost_per_month')::numeric as monthly_cost,
    calculation_completed_at
FROM lakemeter.line_items
WHERE calculation_status = 'success'
ORDER BY monthly_cost DESC;
```

### Get Full Breakdown

```sql
-- Get detailed breakdown for JOBS workload
SELECT 
    line_item_id,
    workload_name,
    cost_calculation_response->'data'->'dbu_per_month' as dbu_per_month,
    cost_calculation_response->'data'->'vm_costs' as vm_costs,
    cost_calculation_response->'data'->'sku_breakdown' as sku_breakdown
FROM lakemeter.line_items
WHERE workload_type = 'JOBS'
  AND calculation_status = 'success';
```

### Sum Costs by Estimate

```sql
-- Total cost per estimate
SELECT 
    e.estimate_name,
    e.customer_name,
    COUNT(li.line_item_id) as line_item_count,
    SUM((li.cost_calculation_response->'data'->>'cost_per_month')::numeric) as total_monthly_cost
FROM lakemeter.estimates e
LEFT JOIN lakemeter.line_items li ON e.estimate_id = li.estimate_id
WHERE li.calculation_status = 'success'
GROUP BY e.estimate_id, e.estimate_name, e.customer_name
ORDER BY total_monthly_cost DESC;
```

### Check Calculation Status

```sql
-- Status summary
SELECT 
    calculation_status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM lakemeter.line_items
GROUP BY calculation_status
ORDER BY count DESC;
```

### Find Errors

```sql
-- Line items with errors
SELECT 
    line_item_id,
    workload_name,
    workload_type,
    cost_calculation_response->>'error' as error_message,
    calculation_completed_at
FROM lakemeter.line_items
WHERE calculation_status = 'error'
ORDER BY calculation_completed_at DESC;
```

## API Endpoint Mapping

The script automatically maps workload types to the correct API endpoint:

| Workload Type | Serverless | Warehouse Type | Endpoint |
|---------------|-----------|----------------|----------|
| JOBS | No | - | `/api/v1/calculate/jobs-classic` |
| JOBS | Yes | - | `/api/v1/calculate/jobs-serverless` |
| ALL_PURPOSE | No | - | `/api/v1/calculate/all-purpose-classic` |
| ALL_PURPOSE | Yes | - | `/api/v1/calculate/all-purpose-serverless` |
| DLT | No | - | `/api/v1/calculate/dlt-classic` |
| DLT | Yes | - | `/api/v1/calculate/dlt-serverless` |
| DBSQL | - | classic | `/api/v1/calculate/dbsql-classic` |
| DBSQL | - | pro | `/api/v1/calculate/dbsql-pro` |
| DBSQL | - | serverless | `/api/v1/calculate/dbsql-serverless` |
| VECTOR_SEARCH | - | - | `/api/v1/calculate/vector-search` |
| MODEL_SERVING | - | - | `/api/v1/calculate/model-serving` |
| FMAPI | - | - | `/api/v1/calculate/fmapi-databricks` or `fmapi-proprietary` |
| LAKEBASE | - | - | `/api/v1/calculate/lakebase` |

## Troubleshooting

### Script hangs or errors

Make sure:
1. API server is running: `http://localhost:8000`
2. Database is accessible: `localhost:5432`
3. Credentials are correct in the script

### All items show as errors

Check:
1. Line items have all required fields for their workload type
2. Estimates have valid cloud/region/tier
3. API endpoints are working (test manually with curl)

### Performance is slow

- Use `--limit` to process in batches
- Check API server logs for slow queries
- Ensure database indexes are created

## Next Steps

After successful backfill on backup table:
1. Verify results look correct
2. Run on main table with small limit first
3. Then run full backfill on main table
4. Set up automatic recalculation trigger (optional)
