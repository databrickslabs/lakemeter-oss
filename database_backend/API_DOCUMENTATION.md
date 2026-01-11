# Lakemeter API Documentation

**Base URL**: `https://lakemeter-api-335310294452632.aws.databricksapps.com`  
**Authentication**: OAuth Bearer Token (Databricks user token)  
**API Version**: v1  
**Last Updated**: December 18, 2024

---

## 🔐 Authentication

All API requests require a Databricks OAuth token in the Authorization header:

```bash
Authorization: Bearer <your_databricks_token>
```

### Getting Your Token (for testing in Databricks notebooks):
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
headers = {"Authorization": f"Bearer {token}"}
```

---

## 📚 API Endpoints Summary

### Dropdown/Reference Data APIs
- **Salesforce**: Accounts, Opportunities, Use Cases
- **Geography**: Clouds, Regions, Pricing Tiers
- **Compute**: Instance Types, Instance Families, VM Pricing Options
- **DBSQL**: Warehouse Types, Sizes, Hardware Specs
- **Model Serving**: GPU Types
- **FMAPI**: Databricks Models, Proprietary Models
- **Vector Search**: Modes
- **Lakebase**: CU Sizes
- **Photon**: Multipliers by SKU Type
- **Serverless**: Mode Multipliers
- **DBU Pricing**: Base rates by SKU

### Cost Calculation APIs
- **JOBS**: Classic, Serverless
- **All-Purpose**: Classic, Serverless
- **DBSQL**: Classic/Pro, Serverless
- **DLT**: Classic, Serverless
- **Model Serving**: GPU-based
- **FMAPI**: Databricks, Proprietary
- **Vector Search**: By mode
- **Lakebase**: PostgreSQL

---

## 🚀 Quick Start Examples

### 1. Get Available Clouds
```bash
GET /api/v1/clouds
```

**Response:**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "clouds": ["AWS", "AZURE", "GCP"]
  }
}
```

### 2. Get Regions for a Cloud
```bash
GET /api/v1/regions?cloud=AWS
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "count": 24,
    "regions": [
      {"region_code": "us-east-1", "sku_region": "US_EAST_N_VIRGINIA"},
      {"region_code": "us-west-2", "sku_region": "US_WEST_OREGON"}
    ]
  }
}
```

### 3. Calculate JOBS Classic Cost
```bash
POST /api/v1/calculate/jobs-classic
Content-Type: application/json

{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "driver_payment_option": "NA",
  "worker_payment_option": "NA",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "JOBS_CLASSIC",
    "configuration": {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM"
    },
    "usage": {
      "hours_per_month": 240.0
    },
    "dbu_costs": {
      "dbu_per_hour": 10.5,
      "dbu_cost_per_month": 1764.0
    },
    "vm_costs": {
      "vm_cost_per_month": 850.32
    },
    "total_cost": {
      "cost_per_month": 2614.32
    }
  }
}
```

---

## 📖 Detailed Endpoint Documentation

### Cost Calculation Endpoints

All calculation endpoints follow this pattern:
- **Method**: `POST`
- **Authentication**: Required
- **Content-Type**: `application/json`
- **Response Format**: Consistent structure with `success`, `data`, and optional `error`

---

## 1️⃣ JOBS Classic

**Endpoint**: `POST /api/v1/calculate/jobs-classic`

**Description**: Calculate cost for classic JOBS workloads with VM instances.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string (e.g., us-east-1)",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "driver_node_type": "string (e.g., m5.xlarge)",
  "worker_node_type": "string (e.g., m5.xlarge)",
  "num_workers": "integer (≥0)",
  "photon_enabled": "boolean",
  "driver_pricing_tier": "on_demand | spot | reserved_1y | reserved_3y",
  "worker_pricing_tier": "on_demand | spot | reserved_1y | reserved_3y",
  "driver_payment_option": "NA | no_upfront | partial_upfront | all_upfront",
  "worker_payment_option": "NA | no_upfront | partial_upfront | all_upfront",
  
  // EITHER provide run-based parameters:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional, default: 30)",
  
  // OR provide direct hours:
  "hours_per_month": "float (optional)"
}
```

**Important Validation Rules:**
- **Driver cannot be spot**: `driver_pricing_tier` cannot be `"spot"`
- **Payment options are cloud-specific**:
  - **AWS**: 
    - `on_demand` and `spot` → use `"NA"`
    - `reserved_1y` and `reserved_3y` → use `"no_upfront"`, `"partial_upfront"`, or `"all_upfront"`
  - **Azure/GCP**: Always use `"NA"` for all pricing tiers

**Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "JOBS_CLASSIC",
    "configuration": { ... },
    "usage": {
      "hours_per_month": 240.0
    },
    "dbu_costs": {
      "dbu_per_hour": 10.5,
      "dbu_per_month": 2520.0,
      "dbu_price": 0.07,
      "dbu_cost_per_month": 176.4
    },
    "vm_costs": {
      "driver_vm_cost_per_hour": 0.192,
      "worker_vm_cost_per_hour": 1.92,
      "total_vm_cost_per_hour": 2.112,
      "vm_cost_per_month": 506.88
    },
    "total_cost": {
      "cost_per_month": 683.28,
      "breakdown": {
        "dbu_cost": 176.4,
        "vm_cost": 506.88
      }
    }
  }
}
```

---

## 2️⃣ JOBS Serverless

**Endpoint**: `POST /api/v1/calculate/jobs-serverless`

**Description**: Calculate cost for serverless JOBS (no VM costs, only DBU).

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "driver_node_type": "string (required for DBU calculation)",
  "worker_node_type": "string (required for DBU calculation)",
  "num_workers": "integer (≥0)",
  "serverless_mode": "standard | performance",
  
  // EITHER run-based OR direct hours:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional)",
  "hours_per_month": "float (optional)"
}
```

**Note**: Photon is always enabled for serverless (not a parameter).

---

## 3️⃣ All-Purpose Classic

**Endpoint**: `POST /api/v1/calculate/all-purpose-classic`

**Description**: Calculate cost for classic All-Purpose (interactive) workloads.

**Request Body**: Same as JOBS Classic (including pricing options and flexible hours).

**Key Difference**: Different SKU rates and Photon multipliers than JOBS.

---

## 4️⃣ All-Purpose Serverless

**Endpoint**: `POST /api/v1/calculate/all-purpose-serverless`

**Description**: Calculate cost for serverless All-Purpose workloads.

**Request Body**: Same as JOBS Serverless.

---

## 5️⃣ DBSQL Classic/Pro

**Endpoint**: `POST /api/v1/calculate/dbsql-classic-pro`

**Description**: Calculate cost for DBSQL warehouses (CLASSIC or PRO) with VM costs.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "warehouse_type": "CLASSIC | PRO",
  "warehouse_size": "X-Small | Small | Medium | Large | X-Large | 2X-Large | 3X-Large | 4X-Large",
  "num_clusters": "integer (1-30)",
  "vm_pricing_tier": "on_demand | spot | reserved_1y | reserved_3y",
  "vm_payment_option": "NA | no_upfront | partial_upfront | all_upfront",
  
  // EITHER run-based OR direct hours:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional)",
  "hours_per_month": "float (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "DBSQL_CLASSIC_PRO",
    "configuration": { ... },
    "usage": { "hours_per_month": 165.0 },
    "dbu_costs": {
      "dbu_per_hour": 48.0,
      "dbu_cost_per_month": 5860.8
    },
    "vm_costs": {
      "driver_vm_cost_per_hour": 1.646,
      "worker_vm_cost_per_hour": 3.293,
      "total_vm_cost_per_hour": 9.878,
      "vm_cost_per_month": 1629.9
    },
    "total_cost": {
      "cost_per_month": 7490.7,
      "breakdown": {
        "dbu_cost": 5860.8,
        "vm_cost": 1629.9
      }
    }
  }
}
```

---

## 6️⃣ DBSQL Serverless

**Endpoint**: `POST /api/v1/calculate/dbsql-serverless`

**Description**: Calculate cost for serverless DBSQL warehouses (DBU only, no VM costs).

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "warehouse_size": "X-Small | Small | Medium | Large | X-Large | 2X-Large | 3X-Large | 4X-Large",
  "num_clusters": "integer (1-30)",
  
  // EITHER run-based OR direct hours:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional)",
  "hours_per_month": "float (optional)"
}
```

**Note**: No `warehouse_type` (always SERVERLESS), no VM pricing parameters.

---

## 7️⃣ DLT Classic

**Endpoint**: `POST /api/v1/calculate/dlt-classic`

**Description**: Calculate cost for Delta Live Tables (classic).

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "dlt_edition": "CORE | PRO | ADVANCED",
  "photon_enabled": "boolean",
  "driver_node_type": "string",
  "worker_node_type": "string",
  "num_workers": "integer (≥0)",
  "driver_pricing_tier": "on_demand | reserved_1y | reserved_3y (not spot)",
  "worker_pricing_tier": "on_demand | spot | reserved_1y | reserved_3y",
  "driver_payment_option": "NA | no_upfront | partial_upfront | all_upfront",
  "worker_payment_option": "NA | no_upfront | partial_upfront | all_upfront",
  
  // EITHER run-based OR direct hours:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional)",
  "hours_per_month": "float (optional)"
}
```

---

## 8️⃣ DLT Serverless

**Endpoint**: `POST /api/v1/calculate/dlt-serverless`

**Description**: Calculate cost for serverless Delta Live Tables.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "driver_node_type": "string",
  "worker_node_type": "string",
  "num_workers": "integer (≥0)",
  "serverless_mode": "standard | performance",
  
  // EITHER run-based OR direct hours:
  "runs_per_day": "integer (optional)",
  "avg_runtime_minutes": "integer (optional)",
  "days_per_month": "integer (optional)",
  "hours_per_month": "float (optional)"
}
```

**Note**: No `dlt_edition` for serverless.

---

## 9️⃣ Model Serving

**Endpoint**: `POST /api/v1/calculate/model-serving`

**Description**: Calculate cost for Model Serving with GPU instances.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "gpu_type": "string (e.g., gpu_small_t4, gpu_medium_a10g_1x)",
  "hours_per_month": "float (≥0)"
}
```

**Available GPU Types** (cloud-specific):
- **AWS**: `cpu`, `gpu_small_t4`, `gpu_medium_a10g_1x`, `gpu_medium_a10g_4x`, `gpu_medium_a10g_8x`, `gpu_xlarge_a100_40gb_8x`, `gpu_xlarge_a100_80gb_8x`
- **Azure**: `cpu`, `gpu_small_t4`, `gpu_xlarge_a100_80gb_1x`, `gpu_2xlarge_a100_80gb_2x`, `gpu_4xlarge_a100_80gb_4x`
- **GCP**: `cpu`, `gpu_medium_g2_standard_8`

---

## 🔟 FMAPI Databricks

**Endpoint**: `POST /api/v1/calculate/fmapi-databricks`

**Description**: Calculate cost for Databricks-hosted FMAPI models.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "model": "string (e.g., llama-3-3-70b, gpt-oss-120b)",
  "rate_type": "input_token | output_token | provisioned_scaling | provisioned_entry",
  "quantity": "integer (tokens or hours depending on rate_type)"
}
```

**Available Models**: `bge-large`, `gemma-3-12b`, `gpt-oss-120b`, `gpt-oss-20b`, `gte`, `llama-3-1-8b`, `llama-3-2-1b`, `llama-3-2-3b`, `llama-3-3-70b`, `llama-4-maverick`

**Examples:**
- Token-based: `rate_type="input_token"`, `quantity=1000000` (1M tokens)
- Provisioned: `rate_type="provisioned_scaling"`, `quantity=730` (hours)

---

## 1️⃣1️⃣ FMAPI Proprietary

**Endpoint**: `POST /api/v1/calculate/fmapi-proprietary`

**Description**: Calculate cost for proprietary FMAPI models (OpenAI, Anthropic, Google).

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "provider": "openai | anthropic | google",
  "model": "string (e.g., claude-sonnet-4-5, gpt-4o, gemini-2-0-flash)",
  "endpoint_type": "global | in_geo (provider-specific)",
  "context_length": "all | short | long (model-specific)",
  "rate_type": "input_token | output_token | cache_read | cache_write | batch_inference",
  "quantity": "integer (tokens or hours)"
}
```

**Example Providers & Models:**
- **openai**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **anthropic**: `claude-sonnet-4-5`, `claude-opus-4`, `claude-haiku-4`
- **google**: `gemini-2-0-flash`, `gemini-1-5-pro`, `gemini-1-5-flash`

---

## 1️⃣2️⃣ Vector Search

**Endpoint**: `POST /api/v1/calculate/vector-search`

**Description**: Calculate cost for Vector Search including storage costs.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "mode": "standard | storage_optimized",
  "vector_capacity_millions": "float (≥0)",
  "hours_per_month": "float (≥0, default: 730)",
  "storage_gb": "float (≥0, default: 0)"
}
```

**Units Calculation:**
- **standard**: 2M vectors per unit → `units_used = CEILING(vector_capacity_millions / 2)`
- **storage_optimized**: 64M vectors per unit → `units_used = CEILING(vector_capacity_millions / 64)`

**Storage Calculation:**
- Free storage: 20 GB per unit
- Billable storage: `MAX(0, storage_gb - (units_used × 20))`
- Storage cost: `billable_storage_gb × price_per_gb_per_month`

**Example Request:**
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "mode": "standard",
  "vector_capacity_millions": 10,
  "hours_per_month": 730,
  "storage_gb": 200
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "VECTOR_SEARCH",
    "sku_type": "VECTOR_SEARCH_ENDPOINT",
    "configuration": {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "mode": "standard",
      "vector_capacity_millions": 10,
      "storage_gb": 200
    },
    "usage": {
      "hours_per_month": 730,
      "units_used": 5
    },
    "dbu_calculation": {
      "dbu_per_hour": 2.5,
      "dbu_per_month": 1825,
      "dbu_price": 0.07,
      "dbu_cost_per_month": 127.75
    },
    "storage_calculation": {
      "total_storage_gb": 200,
      "free_storage_per_unit_gb": 20,
      "free_storage_gb": 100,
      "billable_storage_gb": 100,
      "price_per_gb_per_month": 0.023,
      "storage_cost_per_month": 2.30
    },
    "total_cost": {
      "cost_per_month": 130.05,
      "breakdown": {
        "dbu_cost": 127.75,
        "storage_cost": 2.30
      },
      "note": "Vector Search is serverless - no VM costs"
    }
  }
}
```

---

## 1️⃣3️⃣ Lakebase

**Endpoint**: `POST /api/v1/calculate/lakebase`

**Description**: Calculate cost for Lakebase (managed PostgreSQL) including storage costs.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "cu_size": "integer (1, 2, 4, or 8)",
  "num_nodes": "integer (1-3 for HA)",
  "hours_per_month": "float (≥0, default: 730)",
  "storage_gb": "float (0-8192, default: 0)"
}
```

**Formula:**
```
DBU/Hour = cu_size × num_nodes
DBU Cost = DBU/Hour × hours_per_month × dbu_price

Storage (no free tier):
Total DSU = storage_gb × 15 (each GB consumes 15 DSU)
Storage Cost = Total DSU × price_per_dsu

Total Cost = DBU Cost + Storage Cost
```

**Example Request:**
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "cu_size": 4,
  "num_nodes": 2,
  "hours_per_month": 730,
  "storage_gb": 500
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "LAKEBASE",
    "sku_type": "DATABASE_SERVERLESS_COMPUTE",
    "configuration": {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "cu_size": 4,
      "num_nodes": 2,
      "storage_gb": 500
    },
    "usage": {
      "hours_per_month": 730
    },
    "dbu_calculation": {
      "dbu_per_hour": 8,
      "dbu_per_month": 5840,
      "dbu_price": 0.07,
      "dbu_cost_per_month": 408.80
    },
    "storage_calculation": {
      "storage_gb": 500,
      "max_storage_gb": 8192,
      "dsu_per_gb": 15,
      "total_dsu": 7500,
      "price_per_dsu": 0.023,
      "storage_cost_per_month": 172.50
    },
    "total_cost": {
      "cost_per_month": 581.30,
      "breakdown": {
        "dbu_cost": 408.80,
        "storage_cost": 172.50
      },
      "note": "Lakebase is serverless - no VM costs"
    }
  }
}
```

---

## 1️⃣4️⃣ Databricks Apps

**Endpoint**: `POST /api/v1/calculate/databricks-apps`

**Description**: Calculate cost for Databricks Apps.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "size": "medium | large",
  "hours_per_month": "float (≥0, default: 730)"
}
```

**Sizes:**
| Size | DBU/Hour |
|------|----------|
| medium | 0.5 |
| large | 1.0 |

**Formula:**
```
DBU/Hour = 0.5 (medium) or 1.0 (large)
DBU Cost = DBU/Hour × hours_per_month × dbu_price
```

**Example Request:**
```json
{
  "cloud": "AZURE",
  "region": "southeastasia",
  "tier": "PREMIUM",
  "size": "medium",
  "hours_per_month": 730
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "DATABRICKS_APPS",
    "configuration": {
      "cloud": "AZURE",
      "region": "southeastasia",
      "tier": "PREMIUM",
      "size": "medium"
    },
    "usage": {
      "hours_per_month": 730
    },
    "dbu_calculation": {
      "dbu_per_hour": 0.5,
      "dbu_per_month": 365,
      "dbu_price": 0.55,
      "dbu_cost_per_month": 200.75
    },
    "total_cost": {
      "cost_per_month": 200.75,
      "note": "Databricks Apps is serverless - no VM costs"
    }
  }
}
```

---

## 1️⃣5️⃣ Clean Room

**Endpoint**: `POST /api/v1/calculate/clean-room`

**Description**: Calculate cost for Clean Room collaborators.

**Request Body:**
```json
{
  "cloud": "AWS | AZURE | GCP",
  "region": "string",
  "tier": "STANDARD | PREMIUM | ENTERPRISE",
  "num_collaborators": "integer (1-10)",
  "days_per_month": "integer (1-31, default: 30)"
}
```

**Note:** Number of collaborators excludes the organization that sets up the clean room. Minimum is 1, maximum is 10.

**Formula:**
```
Cost = num_collaborators × days_per_month × rate_per_collaborator_per_day
```

**Example Request:**
```json
{
  "cloud": "AZURE",
  "region": "southeastasia",
  "tier": "PREMIUM",
  "num_collaborators": 3,
  "days_per_month": 30
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "CLEAN_ROOM",
    "configuration": {
      "cloud": "AZURE",
      "region": "southeastasia",
      "tier": "PREMIUM",
      "num_collaborators": 3,
      "days_per_month": 30
    },
    "calculation": {
      "rate_per_collaborator_per_day": 5.00,
      "total_collaborator_days": 90,
      "cost_per_month": 450.00
    },
    "total_cost": {
      "cost_per_month": 450.00,
      "note": "Excludes the organization that sets up the clean room"
    }
  }
}
```

**Reference Endpoint:** `GET /api/v1/clean-room/info` - Returns min/max collaborators

---

## 1️⃣6️⃣ AI Parse

**Endpoint**: `POST /api/v1/calculate/ai-parse`

**Description**: Calculate cost for AI Parse document processing.

**Two Calculation Methods:**

### Method 1: Direct DBU
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "dbu_quantity": 500
}
```

### Method 2: Pages + Complexity
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "num_pages": 10000,
  "complexity": "medium"
}
```

**Complexity Levels:**
| Complexity | Description | DBU/1k pages |
|------------|-------------|--------------|
| `low_text` | Simple text (Receipts, W2s) | 12.5 |
| `low_images` | Simple images + captions | 22.5 |
| `medium` | Text + tables + images (Company 10Ks) | 62.5 |
| `high` | Complex diagrams (Engineering diagrams) | 87.5 |

**Formula (Pages-based):**
```
DBU = (num_pages / 1000) × dbu_per_1k_pages
Cost = DBU × dbu_rate
```

**Example Response (Pages-based):**
```json
{
  "success": true,
  "data": {
    "workload_type": "AI_PARSE",
    "configuration": {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "calculation_method": "pages_based",
      "num_pages": 10000,
      "complexity": "medium"
    },
    "calculation": {
      "dbu_per_1k_pages": 62.5,
      "total_dbu": 625,
      "dbu_rate": 0.07,
      "cost": 43.75
    },
    "total_cost": {
      "cost": 43.75
    }
  }
}
```

**Reference Endpoint:** `GET /api/v1/ai-parse/complexities` - Returns complexity levels with DBU estimates

---

## ⚠️ Error Handling

All endpoints return consistent error format:

```json
{
  "success": false,
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "field": "parameter_name (if applicable)",
    "allowed_values": ["value1", "value2"] 
  }
}
```

**Common Error Codes:**
- `INVALID_CLOUD`: Cloud must be AWS, AZURE, or GCP
- `INVALID_REGION`: Region not found for specified cloud
- `INVALID_TIER`: Tier not available (Azure has no ENTERPRISE)
- `INVALID_INSTANCE_TYPE`: Instance type not found
- `INVALID_PRICING_TIER`: Invalid pricing tier
- `INVALID_PAYMENT_OPTION_FOR_PRICING_TIER`: Wrong payment option for pricing tier (AWS reserved requires no_upfront/partial_upfront/all_upfront)
- `INVALID_PAYMENT_OPTION_FOR_CLOUD`: Azure/GCP must use NA for all tiers
- `INVALID_WAREHOUSE_SIZE`: Warehouse size not found
- `INVALID_GPU_TYPE`: GPU type not available for cloud
- `MISSING_USAGE_PARAMETERS`: Must provide either run-based OR hours_per_month
- `CONFLICTING_USAGE_PARAMETERS`: Cannot provide both run-based AND hours_per_month

---

## 🔍 Reference Data Endpoints

### Get Available Clouds
```bash
GET /api/v1/clouds
```

### Get Regions
```bash
GET /api/v1/regions?cloud=AWS
```

### Get Pricing Tiers
```bash
GET /api/v1/pricing-tiers?cloud=AWS
```

### Get Instance Types
```bash
GET /api/v1/instances/types?cloud=AWS&region=us-east-1&min_vcpus=4&max_vcpus=16
```

### Get Instance Families
```bash
GET /api/v1/instances/families
```

### Get VM Pricing Options
```bash
GET /api/v1/instances/vm-pricing-options?cloud=AWS
```

### Get DBSQL Warehouse Types
```bash
GET /api/v1/dbsql/warehouse-types
```

### Get DBSQL Warehouse Sizes
```bash
GET /api/v1/dbsql/warehouse-sizes
```

### Get GPU Types for Model Serving
```bash
GET /api/v1/model-serving/gpu-types?cloud=AWS
```

### Get FMAPI Databricks Models
```bash
GET /api/v1/fmapi/databricks-models/list
```

### Get FMAPI Proprietary Models
```bash
GET /api/v1/fmapi/proprietary-models/list?provider=anthropic
```

### Get Vector Search Modes
```bash
GET /api/v1/vector-search/list
```

### Get Lakebase CU Sizes
```bash
GET /api/v1/lakebase/list
```

### Get Photon Multipliers
```bash
GET /api/v1/photon/multipliers?cloud=AWS&sku_type=JOBS
```

### Get Serverless Mode Multipliers
```bash
GET /api/v1/serverless/modes
```

---

## 🎯 Important Notes for Frontend Development

### 1. **Payment Options are Cloud-Specific**
When building forms for reserved pricing:
- For **AWS**: Show dropdown with `no_upfront`, `partial_upfront`, `all_upfront`
- For **Azure/GCP**: Hide the dropdown or disable it (always use `NA`)

### 2. **Driver Cannot Be Spot**
For classic workloads, disable "spot" option for `driver_pricing_tier`.

### 3. **Flexible Usage Input**
For most calculation endpoints, allow users to input EITHER:
- Run-based: `runs_per_day` + `avg_runtime_minutes` + `days_per_month`
- OR Direct: `hours_per_month`

Do not allow both simultaneously.

### 4. **Serverless Always Has Photon**
For serverless endpoints, do not show a Photon toggle - it's always enabled.

### 5. **DBSQL Warehouse Size Validation**
Warehouse sizes are validated against the warehouse type:
- CLASSIC/PRO: Check against `sync_ref_dbsql_warehouse_config`
- SERVERLESS: Check against `sync_product_dbsql_rates`

### 6. **Error Messages Include Allowed Values**
When validation fails, the API returns `allowed_values` array - use this to show users what options are valid.

### 7. **Rate Limiting**
No rate limits currently, but avoid making excessive parallel requests.

---

## 📞 Support

For issues or questions:
- Check Swagger UI: `https://lakemeter-api-335310294452632.aws.databricksapps.com/docs`
- Review error messages carefully - they include helpful hints
- Validate required parameters before sending requests

---

## 📝 Changelog

**December 18, 2024**:
- ✅ Fixed FMAPI endpoints returning $0 costs
- ✅ Fixed DBSQL Serverless validation
- ✅ Split DBSQL into Classic/Pro and Serverless endpoints
- ✅ Added cloud-aware payment option validation
- ✅ Fixed Azure reserved VM pricing (divided by hours)
- ✅ All calculation endpoints verified and working

