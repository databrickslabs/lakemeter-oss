---
sidebar_position: 4
---

# API Reference

Lakemeter exposes a REST API at `/api/v1/`. All endpoints require authentication through Databricks Apps SSO.

![API Reference documentation page](/img/guides/admin-api-reference-guide.png)
*The API Reference — all REST endpoints organized by resource with request/response details.*

## Base URL

```
https://<your-app-name>-<workspace-id>.<cloud>.databricksapps.com/api/v1
```

:::tip
Interactive Swagger API docs are available at `/api/docs` and `/api/redoc` on your deployed app.
:::

---

## Estimates

**Router prefix:** `/api/v1/estimates`

### List Estimates

```
GET /api/v1/estimates
```

Returns all estimates for the authenticated user (excludes soft-deleted).

**Response:** `EstimateListResponse[]`

```json
[
  {
    "estimate_id": "uuid",
    "estimate_name": "My Estimate",
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "status": "draft",
    "version": 3,
    "line_item_count": 5,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-16T14:20:00Z"
  }
]
```

### Create Estimate

```
POST /api/v1/estimates/
```

**Request Body:**

```json
{
  "estimate_name": "Q4 Data Platform",
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM"
}
```

**Response:** `201 Created` with `EstimateResponse`

### Get Current User's Estimate Info

```
GET /api/v1/estimates/me/info
```

Returns summary info (estimate count, recent activity) for the authenticated user.

### Get Estimate

```
GET /api/v1/estimates/{estimate_id}
```

**Response:** `EstimateResponse` with full details.

### Get Estimate with Line Items

```
GET /api/v1/estimates/{estimate_id}/full
```

Optimized single-query response with estimate and all line items.

```json
{
  "estimate": { ... },
  "line_items": [ ... ]
}
```

### Update Estimate

```
PUT /api/v1/estimates/{estimate_id}
```

**Request Body:** (all fields optional)

```json
{
  "estimate_name": "Updated Name",
  "region": "us-west-2",
  "tier": "ENTERPRISE",
  "status": "approved"
}
```

### Delete Estimate

```
DELETE /api/v1/estimates/{estimate_id}
```

**Response:** `204 No Content` (soft delete)

### Duplicate Estimate

```
POST /api/v1/estimates/{estimate_id}/duplicate
```

Creates a full copy with all workloads. Name gets "(Copy)" suffix.

### Clone Estimate

```
POST /api/v1/estimates/{estimate_id}/clone
```

**Request Body:** (optional)

```json
{
  "new_name": "Custom Clone Name"
}
```

---

## Line Items (Workloads)

**Router prefix:** `/api/v1/line-items`

### List Line Items for Estimate

```
GET /api/v1/line-items/estimate/{estimate_id}
```

**Response:** `LineItemResponse[]`

### Create Line Item

```
POST /api/v1/line-items/
```

**Request Body:**

```json
{
  "estimate_id": "uuid",
  "workload_name": "ETL Pipeline",
  "workload_type": "JOBS",
  "serverless_enabled": false,
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.2xlarge",
  "num_workers": 4,
  "photon_enabled": true,
  "runs_per_day": 3,
  "avg_runtime_minutes": 45,
  "days_per_month": 30
}
```

**Response:** `201 Created` with `LineItemResponse`

### Get Line Item

```
GET /api/v1/line-items/{line_item_id}
```

### Update Line Item

```
PUT /api/v1/line-items/{line_item_id}
```

All fields are optional — only include fields you want to change.

### Delete Line Item

```
DELETE /api/v1/line-items/{line_item_id}
```

**Response:** `204 No Content`

### Reorder Line Items

```
POST /api/v1/line-items/reorder
```

```json
{
  "line_item_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Clone Line Item

```
POST /api/v1/line-items/{line_item_id}/clone
```

**Response:** `201 Created` with cloned `LineItemResponse`

---

## Calculations

**Router prefix:** `/api/v1/calculate`

All calculation endpoints accept workload parameters and return cost breakdowns.

| Endpoint | Workload Type |
|----------|--------------|
| `POST /api/v1/calculate/jobs-classic` | Jobs (Classic) |
| `POST /api/v1/calculate/jobs-serverless` | Jobs (Serverless) |
| `POST /api/v1/calculate/all-purpose-classic` | All-Purpose (Classic) |
| `POST /api/v1/calculate/all-purpose-serverless` | All-Purpose (Serverless) |
| `POST /api/v1/calculate/dbsql-classic-pro` | DBSQL (Classic/Pro) |
| `POST /api/v1/calculate/dbsql-serverless` | DBSQL (Serverless) |
| `POST /api/v1/calculate/dlt-classic` | DLT (Classic) |
| `POST /api/v1/calculate/dlt-serverless` | DLT (Serverless) |
| `POST /api/v1/calculate/model-serving` | Model Serving |
| `POST /api/v1/calculate/fmapi-databricks` | FMAPI (Databricks-hosted) |
| `POST /api/v1/calculate/fmapi-proprietary` | FMAPI (Proprietary) |
| `POST /api/v1/calculate/vector-search` | Vector Search |
| `POST /api/v1/calculate/lakebase` | Lakebase |
| `POST /api/v1/calculate/databricks-apps` | Databricks Apps |
| `POST /api/v1/calculate/ai-parse` | AI Parse (Document AI) |
| `POST /api/v1/calculate/shutterstock-imageai` | Shutterstock ImageAI |

### Example: Jobs Classic

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.2xlarge",
  "num_workers": 4,
  "photon_enabled": false,
  "runs_per_day": 3,
  "avg_runtime_minutes": 45,
  "days_per_month": 30
}
```

### Example: Lakebase

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "cu_size": 4,
  "num_nodes": 2,
  "storage_gb": 100,
  "hours_per_month": 730
}
```

### Example: Databricks Apps

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "size": "medium",
  "hours_per_month": 730
}
```

### Example: AI Parse

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "mode": "pages",
  "complexity": "medium",
  "pages_thousands": 10
}
```

### Example: Shutterstock ImageAI

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "images_per_month": 500
}
```

---

## Export

**Router prefix:** `/api/v1/export`

### Export Estimate to Excel

```
GET /api/v1/export/estimate/{estimate_id}/excel
```

**Response:** Binary Excel file download (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

### Export All Estimates to Excel

```
GET /api/v1/export/estimates/excel
```

Exports all of the authenticated user's estimates into a single Excel file.

---

## AI Chat

**Router prefix:** `/api/v1/chat`

### Send Message

```
POST /api/v1/chat/
```

```json
{
  "message": "What would a DBSQL serverless warehouse cost?",
  "conversation_id": "uuid",
  "mode": "estimate",
  "estimate_context": { ... },
  "workloads_context": [ ... ]
}
```

**Response:**

```json
{
  "content": "A DBSQL Serverless warehouse...",
  "conversation_id": "uuid",
  "tool_results": [],
  "proposed_workload": null
}
```

### Send Message (Streaming)

```
POST /api/v1/chat/stream
```

Same request body. Response is Server-Sent Events (SSE):

```
event: start
data: {"conversation_id": "uuid"}

event: content
data: {"text": "A DBSQL"}

event: content
data: {"text": " Serverless warehouse..."}

event: done
data: {"final_state": {...}}
```

### Clear Conversation

```
DELETE /api/v1/chat/{conversation_id}
```

### Apply AI-Generated Estimate

```
POST /api/v1/chat/{conversation_id}/apply
```

Creates database records from the AI agent's draft estimate.

### Get Conversation State

```
GET /api/v1/chat/{conversation_id}/state
```

Returns the current state of a conversation including any pending proposed workloads.

### Confirm Proposed Workload

```
POST /api/v1/chat/{conversation_id}/confirm-workload
```

Accepts or rejects a workload proposed by the AI assistant.

---

## Users

**Router prefix:** `/api/v1/users`

### Get Current User

```
GET /api/v1/users/me
```

### List Users

```
GET /api/v1/users?skip=0&limit=100
```

### Create User

```
POST /api/v1/users/
```

### Get User by ID

```
GET /api/v1/users/{user_id}
```

### Get User by Email

```
GET /api/v1/users/email/{email}
```

### Update User

```
PUT /api/v1/users/{user_id}
```

---

## Workload Types

**Router prefix:** `/api/v1/workload-types`

### List Workload Types

```
GET /api/v1/workload-types
```

Returns all 14 workload types with their UI configuration flags.

### Get Workload Type

```
GET /api/v1/workload-types/{workload_type}
```

---

## Reference Data

**Router prefix:** `/api/v1/reference`

### Regions

```
GET /api/v1/reference/regions
```

### Pricing Tiers

```
GET /api/v1/reference/pricing-tiers
```

### Instance Types

```
GET /api/v1/reference/instances/types?cloud=AWS&region=us-east-1
```

### Instance Families

```
GET /api/v1/reference/instances/families
```

### VM Costs

```
GET /api/v1/reference/instances/vm-costs
```

### DBSQL Warehouse Sizes

```
GET /api/v1/reference/dbsql/warehouse-sizes
```

### Model Serving GPU Types

```
GET /api/v1/reference/model-serving/gpu-types
```

### FMAPI Databricks Models

```
GET /api/v1/reference/fmapi/databricks-models
```

### FMAPI Proprietary Models

```
GET /api/v1/reference/fmapi/proprietary-models
```

### DBU Rates

```
GET /api/v1/reference/dbu-rates
```

### Pricing Bundle Status

```
GET /api/v1/reference/pricing-bundle/status
```

### Regenerate Pricing Bundle

```
POST /api/v1/reference/pricing-bundle/regenerate
```

---

## VM Pricing

**Router prefix:** `/api/v1/vm-pricing`

### List VM Pricing

```
GET /api/v1/vm-pricing
```

### Instance Types

```
GET /api/v1/vm-pricing/instance-types
```

### Regions

```
GET /api/v1/vm-pricing/regions
```

### Get Price

```
GET /api/v1/vm-pricing/price
```

### Pricing Tiers

```
GET /api/v1/vm-pricing/tiers
```

### Payment Options

```
GET /api/v1/vm-pricing/payment-options
```

---

## Debug Endpoints

These endpoints are available for diagnosing configuration issues:

### Debug Headers

```
GET /api/v1/debug/headers
```

Returns all HTTP headers received by the app (useful for verifying SSO headers from Databricks Apps proxy).

### Debug External API

```
GET /api/v1/debug/external-api
```

Tests external API authentication. Returns token availability status and attempts a test calculation.

### Debug Database

```
GET /api/v1/debug/database
```

Returns database connection status, environment variable values (passwords redacted), token manager status, and connectivity test result.

### Refresh Database Connection

```
POST /api/v1/debug/database/refresh
```

Forces a database engine refresh with a new OAuth token.

---

## Frontend Data Endpoints

These convenience endpoints are defined directly in `main.py` and provide reference data used by the frontend store. Many overlap with the router-based `/api/v1/reference/*` endpoints but return data in formats optimized for the frontend UI.

### API Root

```
GET /api
```

Returns API name, version, and description.

### Cloud Providers with Regions

```
GET /api/v1/reference/clouds
```

Returns cloud providers (AWS, Azure, GCP) with their available regions, queried from the `sync_ref_sku_region_map` table. Falls back to hardcoded defaults if the database is unavailable.

### Regions by Cloud

```
GET /api/v1/regions?cloud=AWS
```

Returns all regions for a specific cloud provider from the SKU region map.

### Pricing Tiers

```
GET /api/v1/reference/tiers
```

Returns Standard, Premium, and Enterprise tier options.

### Instance Types

```
GET /api/v1/instances/types?cloud=AWS
GET /api/v1/reference/instance-types/{cloud}
```

Both return instance types with vCPU, memory, DBU rate, and family info. The `/reference/` variant uses a path parameter. Queries `sync_ref_instance_dbu_rates` with fallback to hardcoded lists.

### Instance Families

```
GET /api/v1/instances/families
```

Returns: `["General Purpose", "Compute Optimized", "Memory Optimized", "Storage Optimized", "GPU"]`

### VM Costs

```
GET /api/v1/instances/vm-costs?cloud=AWS&region=us-east-1&instance_type=m5.xlarge
```

Proxies to the external Lakemeter pricing API. Optional query params: `pricing_tier`, `payment_option`.

### DBSQL Warehouse Sizes

```
GET /api/v1/dbsql/warehouse-sizes
GET /api/v1/reference/dbsql-sizes
```

Both return the 9 DBSQL warehouse sizes (2X-Small through 4X-Large) with DBU/hour rates.

### DBSQL Warehouse Types

```
GET /api/v1/dbsql/warehouse-types
```

Returns: `["CLASSIC", "PRO", "SERVERLESS"]`

### DLT Editions

```
GET /api/v1/dlt/editions
GET /api/v1/reference/dlt-editions
```

Both return Core, Pro, and Advanced editions. The `/reference/` variant also includes `dbu_multiplier`.

### Serverless Modes

```
GET /api/v1/serverless/modes
```

Returns standard (1.0x) and performance (1.3x) modes.

### Model Serving GPU Types (by cloud)

```
GET /api/v1/model-serving/gpu-types?cloud=AWS
GET /api/v1/reference/model-serving-gpu-types/{cloud}
```

Returns GPU types with DBU/hour rates. Available types vary by cloud.

### Photon Multipliers

```
GET /api/v1/photon/multipliers?cloud=AWS&sku_type=JOBS
```

Returns Photon multipliers by SKU type. Optional `sku_type` filter.

### FMAPI Model Lists

```
GET /api/v1/fmapi/databricks-models/list
GET /api/v1/reference/fmapi-models
GET /api/v1/reference/fmapi-databricks
GET /api/v1/reference/fmapi-proprietary
```

Various views of available foundation models. `/reference/fmapi-databricks` includes model types, inference types, and per-type model lists. `/reference/fmapi-proprietary` includes providers, endpoint types, and context lengths.

### Pricing Data

```
GET /api/v1/pricing/dbu-rates?cloud=AWS&region=us-east-1&tier=PREMIUM
GET /api/v1/pricing/product-types?cloud=AWS&region=us-east-1&tier=PREMIUM
```

`/dbu-rates` returns DBU prices per product type for a cloud/region/tier combination. Optional `product_type` filter returns a single rate. `/product-types` returns the list of available product type strings.

---

## Health Check

```
GET /health
```

**Response:** `{"status": "healthy"}`
