# 📊 Lakemeter Calculation API Endpoints

**Base URL:** `https://lakemeter-api-335310294452632.aws.databricksapps.com`

**Swagger UI:** https://lakemeter-api-335310294452632.aws.databricksapps.com/docs

---

## 🎯 Complete Calculation Endpoints

### 1. **All-Purpose Compute** ✅
`POST /api/v1/calculate/all-purpose`

For interactive notebooks, ad-hoc queries, and development workloads.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `driver_node_type`, `worker_node_type`, `num_workers` (required)
- `photon_enabled` (optional, default: false)
- `driver_pricing_tier`, `worker_pricing_tier` (optional, default: on_demand)
- `driver_payment_option`, `worker_payment_option` (optional, default: NA)
- `hours_per_month` (optional, default: 730)

**Returns:** DBU costs + VM costs

**Test Result:** $647.15/month (AWS, us-east-1, PREMIUM, m5.xlarge, 2 workers, 730 hours)

---

### 2. **JOBS Classic** ✅
`POST /api/v1/calculate/jobs-classic`

For scheduled/automated batch processing workloads.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `driver_node_type`, `worker_node_type`, `num_workers` (required)
- `photon_enabled` (optional, default: false)
- `driver_pricing_tier`, `worker_pricing_tier` (optional, default: on_demand)
- `driver_payment_option`, `worker_payment_option` (optional, default: NA)
- `runs_per_day`, `avg_runtime_minutes`, `days_per_month` (required)

**Returns:** DBU costs + VM costs

**Test Result:** $17.73/month (AWS, us-east-1, PREMIUM, m5.xlarge, 1 worker, 1 run/day, 60 min/run, 30 days)

---

### 3. **JOBS Serverless** ✅ *(Fixed!)*
`POST /api/v1/calculate/jobs-serverless`

For serverless batch processing with automatic scaling.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `driver_node_type`, `worker_node_type`, `num_workers` (required for DBU calculation)
- `photon_enabled` (optional, default: false)
- `serverless_mode` (optional, default: standard; options: standard, performance)
- `runs_per_day`, `avg_runtime_minutes`, `days_per_month` (required)

**Returns:** DBU costs only (no VM costs)

**Test Result:** $315.16/month (AWS, us-east-1, PREMIUM, m5.xlarge, 2 workers, 10 runs/day, 30 min/run, 30 days)

**Note:** Even though serverless, node types are required for DBU rate calculation.

---

### 4. **DBSQL (SQL Warehouses)** ✅
`POST /api/v1/calculate/dbsql`

For SQL analytics with Classic, Pro, or Serverless warehouses.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `warehouse_type` (required: CLASSIC, PRO, or SERVERLESS)
- `warehouse_size` (required: X-Small, Small, Medium, Large, etc.)
- `num_clusters` (optional, default: 1)
- `vm_pricing_tier`, `vm_payment_option` (optional for Classic/Pro, ignored for Serverless)
- `hours_per_month` (required)

**Returns:** DBU costs + VM costs (Classic/Pro) or DBU costs only (Serverless)

---

### 5. **DLT (Delta Live Tables)** ✅
`POST /api/v1/calculate/dlt`

For data pipeline workloads with Core, Pro, or Advanced editions.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `dlt_edition` (required: CORE, PRO, or ADVANCED)
- `driver_node_type`, `worker_node_type`, `num_workers` (required)
- `photon_enabled` (optional, default: false)
- `driver_pricing_tier`, `worker_pricing_tier` (optional, default: on_demand)
- `driver_payment_option`, `worker_payment_option` (optional, default: NA)
- `hours_per_month` (required)

**Returns:** DBU costs + VM costs

---

### 6. **Vector Search** ✅
`POST /api/v1/calculate/vector-search`

For vector database and similarity search workloads.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `mode` (required: delta_sync or direct_access)
- `vector_capacity_millions` (required)
- `hours_per_month` (optional, default: 730)

**Returns:** DBU costs only (serverless, no VM costs)

---

### 7. **Model Serving** ✅
`POST /api/v1/calculate/model-serving`

For serving ML models with GPU acceleration.

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `gpu_type` (required: cpu, gpu_small_t4, gpu_medium_a10g_1x, gpu_xlarge_a100_80gb_8x, etc.)
- `hours_per_month` (optional, default: 730)

**Returns:** DBU costs only (serverless, no VM costs)

---

### 8. **FMAPI (Foundation Model API)** ✅
`POST /api/v1/calculate/fmapi`

For using foundation models (OpenAI, Anthropic, Google, Databricks).

**Parameters:**
- `cloud`, `region`, `tier` (required)
- `provider` (required: databricks, openai, anthropic, google)
- `model` (required: e.g., claude-sonnet-4-5, gpt-4o, gemini-2-0-flash)
- `endpoint_type` (optional, default: global)
- `context_length` (optional, default: all)
- `rate_type` (required: input_token, output_token, provisioned_scaling, etc.)
- `quantity` (required: number of tokens or hours)

**Returns:** Token or provisioned costs

---

### 9. **Lakebase (Managed PostgreSQL)** ✅
`POST /api/v1/calculate/lakebase`

For managed PostgreSQL database instances.

**Parameters:**
- `cu_size` (required: 1, 2, 4, or 8)
- `num_nodes` (required: 1-3 for high availability)
- `hours_per_month` (optional, default: 730)

**Returns:** DBU costs only (cloud-agnostic, no VM costs)

**Note:** Lakebase pricing is the same across AWS, Azure, and GCP.

---

## 📋 Common Response Structure

All endpoints return:

```json
{
  "success": true,
  "data": {
    "workload_type": "...",
    "configuration": { ... },
    "usage": { ... },
    "dbu_calculation": {
      "dbu_per_hour": 0.0,
      "dbu_per_month": 0.0,
      "dbu_price": 0.0,
      "dbu_cost_per_month": 0.0
    },
    "vm_costs": { ... },  // Only for non-serverless workloads
    "total_cost": {
      "cost_per_month": 0.0,
      "breakdown": { ... }
    }
  }
}
```

---

## 🔐 Authentication

All endpoints require OAuth authentication:

```bash
curl -X POST \
  -H "Authorization: Bearer $YOUR_DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}' \
  "https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/..."
```

**In Databricks Notebooks:** Token is automatically retrieved via `dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()`

**Locally:** Use `databricks auth token --profile <profile-name>`

---

## ✅ Status Summary

| Endpoint | Status | DBU Calculation | VM Costs |
|----------|--------|-----------------|----------|
| All-Purpose | ✅ Tested | ✅ | ✅ |
| JOBS Classic | ✅ Tested | ✅ | ✅ |
| JOBS Serverless | ✅ Fixed | ✅ | ❌ (Serverless) |
| DBSQL | ✅ Created | ✅ | ✅ (Classic/Pro) |
| DLT | ✅ Created | ✅ | ✅ |
| Vector Search | ✅ Created | ✅ | ❌ (Serverless) |
| Model Serving | ✅ Created | ✅ | ❌ (Serverless) |
| FMAPI | ✅ Created | ✅ | ❌ (Serverless) |
| Lakebase | ✅ Created | ✅ | ❌ (Cloud-agnostic) |

---

## 🧪 Test Notebooks

Location: `/lakemeter/API_Tests/`

- `00_API_Config.py` - OAuth configuration
- `Test_API_01_JOBS_Classic.py` - Automated tests
- `Debug_API_Error.py` - Debug helper

---

## 🎯 Next Steps

1. ✅ All calculation endpoints created and deployed
2. ✅ JOBS Serverless fixed (node types required for DBU calculation)
3. 🔄 Test remaining endpoints (DBSQL, DLT, Vector, Model Serving, FMAPI, Lakebase)
4. 📝 Create comprehensive test suite
5. 📊 Build frontend integration

---

**Last Updated:** December 18, 2025
**API Version:** v1
**Deployment:** SUCCEEDED (deployment_id: 01f0dba4fb421166866cb64d2c560af8)

