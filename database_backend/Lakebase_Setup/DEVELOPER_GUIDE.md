# Lakemeter Developer Guide

**Author:** Steven Tan  
**Last Updated:** December 2025

A practical guide for API and Frontend developers.

> 📋 **Full Schema:** See [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) for complete column definitions  
> 📊 **ERD:** See [LAKEMETER_ERD.md](./LAKEMETER_ERD.md) for visual diagram

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      YOUR APP MANAGES                            │
│  ┌──────────┐   ┌───────────┐   ┌─────────────┐                 │
│  │  users   │──►│ estimates │──►│ line_items  │                 │
│  └──────────┘   └───────────┘   └─────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ JOINs (via views)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   READ-ONLY PRICING DATA                         │
│  sync_pricing_*  │  sync_product_*  │  sync_ref_*               │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Examples

### Create Estimate
```json
POST /api/estimates
{
  "estimate_name": "Acme Corp - Data Platform",
  "customer_name": "Acme Corporation",
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM"
}
```

### Add Line Item (Jobs Classic)
```json
POST /api/estimates/:id/line-items
{
  "workload_type": "JOBS_CLASSIC",
  "workload_name": "ETL Pipeline",
  "driver_node_type": "i3.xlarge",
  "worker_node_type": "i3.2xlarge",
  "num_workers": 4,
  "photon_enabled": true,
  "runs_per_day": 3,
  "avg_runtime_minutes": 45,
  "days_per_month": 30
}
```

### Add Line Item (DBSQL)
```json
POST /api/estimates/:id/line-items
{
  "workload_type": "DBSQL",
  "workload_name": "Analytics Warehouse",
  "dbsql_warehouse_type": "SERVERLESS",
  "dbsql_warehouse_size": "Medium",
  "hours_per_day": 8,
  "days_per_month": 22
}
```

### Add Line Item (FMAPI)
```json
POST /api/estimates/:id/line-items
{
  "workload_type": "FMAPI_DATABRICKS",
  "workload_name": "LLM Chatbot",
  "fmapi_model": "llama-3.1-70b-instruct",
  "fmapi_input_tokens_per_month": 10000000,
  "fmapi_output_tokens_per_month": 2000000
}
```

---

## Cost Calculation

**Don't calculate costs manually!** Use the pre-built views.

### Get Line Items with Costs
```sql
SELECT line_item_id, workload_name, workload_type,
       dbu_per_month, dbu_cost_per_month, vm_cost_per_month, cost_per_month
FROM v_line_items_with_costs 
WHERE estimate_id = :estimate_id;
```

### Get Estimate Totals
```sql
SELECT estimate_id, estimate_name, customer_name,
       total_dbu_per_month, total_cost_per_month, line_item_count
FROM v_estimates_with_totals 
WHERE owner_user_id = :user_id;
```

---

## Dropdown Data (Read-Only)

### Instance Types
```sql
SELECT instance_type, vcpus, memory_gb, dbu_rate 
FROM sync_ref_instance_dbu_rates 
WHERE cloud = :cloud ORDER BY dbu_rate;
```

### DBSQL Sizes
```sql
SELECT warehouse_type, warehouse_size, dbu_per_hour 
FROM sync_product_dbsql_rates 
WHERE cloud = :cloud;
```

### Workload Types (for form config)
```sql
SELECT workload_type, display_name, 
       show_classic_compute, show_dbsql_config, show_fmapi_config,
       show_usage_hours, show_usage_runs
FROM ref_workload_types 
ORDER BY display_order;
```

---

## Frontend: Dynamic Form

```javascript
// When user selects workload type
function onWorkloadTypeChange(selectedType) {
  const config = workloadTypes.find(w => w.workload_type === selectedType);
  
  showSection('classicCompute', config.show_classic_compute);
  showSection('dbsqlConfig', config.show_dbsql_config);
  showSection('fmapiConfig', config.show_fmapi_config);
  showSection('usageHours', config.show_usage_hours);
  showSection('usageRuns', config.show_usage_runs);
}
```

### Form Fields by Workload Type

| Workload Type | Fields |
|---------------|--------|
| `ALL_PURPOSE` | driver, workers, photon, hours_per_day |
| `JOBS_CLASSIC` | driver, workers, photon, runs_per_day, avg_runtime |
| `JOBS_SERVERLESS` | runs_per_day, avg_runtime |
| `DLT` | driver, workers, photon, dlt_edition, hours_per_day |
| `DBSQL` | warehouse_type, warehouse_size, hours_per_day |
| `VECTOR_SEARCH` | serverless_size, hours_per_day |
| `MODEL_SERVING` | serverless_size, hours_per_day |
| `FMAPI_DATABRICKS` | fmapi_model, input_tokens, output_tokens |
| `FMAPI_PROPRIETARY` | fmapi_provider, fmapi_model, input_tokens, output_tokens |

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/estimates` | List user's estimates (uses `v_estimates_with_totals`) |
| POST | `/api/estimates` | Create estimate |
| GET | `/api/estimates/:id` | Get estimate with totals |
| PUT | `/api/estimates/:id` | Update estimate |
| DELETE | `/api/estimates/:id` | Soft delete |
| GET | `/api/estimates/:id/line-items` | List line items (uses `v_line_items_with_costs`) |
| POST | `/api/estimates/:id/line-items` | Add line item |
| PUT | `/api/line-items/:id` | Update line item |
| DELETE | `/api/line-items/:id` | Delete line item |
| GET | `/api/workload-types` | Form config (from `ref_workload_types`) |
| GET | `/api/instances?cloud=AWS` | Instance dropdown |
| GET | `/api/dbsql-sizes?cloud=AWS` | DBSQL size dropdown |

---

## Quick Reference

| Category | Tables |
|----------|--------|
| **Write (CRUD)** | `users`, `estimates`, `line_items`, `sharing` |
| **Write (Create only)** | `conversation_messages`, `decision_records` |
| **Read (App config)** | `ref_workload_types` |
| **Read (Synced data)** | `sync_pricing_*`, `sync_product_*`, `sync_ref_*` |
| **Query (Views)** | `v_line_items_with_costs`, `v_estimates_with_totals` |
