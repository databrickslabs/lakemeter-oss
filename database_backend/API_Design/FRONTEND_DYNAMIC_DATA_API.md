# Frontend Dynamic Data API - Detailed Plan

## 1. Overview

**Purpose:** Provide APIs for frontend to dynamically populate dropdowns, show instance specs, and filter options based on user selections.

**Key Challenge:** Different clouds have different instance types in different regions, with varying specs (vCPU, memory) and pricing.

---

## 2. Required Data for Frontend

### 2.1 Instance Type Metadata

**What Frontend Needs:**
```json
{
  "instance_type": "i3.2xlarge",
  "cloud": "AWS",
  "region": "us-east-1",
  "vcpu": 8,
  "memory_gb": 61,
  "storage": "1 x 1,900 NVMe SSD",
  "network": "Up to 10 Gigabit",
  "dbu_per_hour": 1.5,
  "price_per_hour_on_demand": 0.624,
  "available": true
}
```

**Where to Get This Data:**

#### Option A: Add Metadata to Existing Tables ✅ **RECOMMENDED**

Add columns to `sync_ref_instance_dbu_rates`:

```sql
ALTER TABLE lakemeter.sync_ref_instance_dbu_rates
ADD COLUMN vcpu INT,
ADD COLUMN memory_gb DECIMAL(10,2),
ADD COLUMN storage_type VARCHAR(50),
ADD COLUMN network_performance VARCHAR(50),
ADD COLUMN instance_family VARCHAR(20);
```

**Pros:**
- Single source of truth
- Easy to query
- Consistent with existing design

**Cons:**
- Need to populate historical data
- Requires data sync from cloud providers

#### Option B: Separate Instance Metadata Table

Create new table: `sync_ref_instance_metadata`

```sql
CREATE TABLE lakemeter.sync_ref_instance_metadata (
    cloud VARCHAR(20),
    instance_type VARCHAR(100),
    vcpu INT,
    memory_gb DECIMAL(10,2),
    storage_type VARCHAR(50),
    storage_capacity_gb INT,
    network_performance VARCHAR(50),
    instance_family VARCHAR(20),
    gpu_type VARCHAR(50),
    gpu_count INT,
    architecture VARCHAR(20),  -- x86, ARM
    PRIMARY KEY (cloud, instance_type)
);
```

**Pros:**
- Clean separation of concerns
- Can be populated independently

**Cons:**
- Additional join in queries
- More tables to maintain

**DECISION: Option A - Extend sync_ref_instance_dbu_rates**

---

## 3. API Endpoints for Frontend Dynamic Data

### 3.1 Instance Types API

#### **GET /api/v1/instance-types**

Get available instance types with specs, filtered by cloud/region/workload.

**Query Parameters:**
- `cloud` (required): AWS, AZURE, GCP
- `region` (optional): Filter by region
- `workload_type` (optional): Filter by workload compatibility
- `min_vcpu` (optional): Minimum vCPU
- `max_vcpu` (optional): Maximum vCPU
- `min_memory_gb` (optional): Minimum memory
- `sort_by` (optional): vcpu, memory_gb, price (default: instance_type)

**Example Request:**
```
GET /api/v1/instance-types?cloud=AWS&region=us-east-1&workload_type=JOBS&sort_by=vcpu
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "region": "us-east-1",
    "count": 45,
    "instance_types": [
      {
        "instance_type": "i3.xlarge",
        "vcpu": 4,
        "memory_gb": 30.5,
        "storage": "1 x 950 NVMe SSD",
        "network": "Up to 10 Gigabit",
        "instance_family": "i3",
        "architecture": "x86_64",
        "dbu_per_hour": 0.75,
        "pricing": {
          "on_demand": 0.312,
          "spot": 0.0936,
          "reserved_1y_no_upfront": 0.186,
          "reserved_3y_all_upfront": 0.124
        },
        "label": "i3.xlarge (4 vCPU, 30.5 GB RAM) - $0.312/hr"
      },
      {
        "instance_type": "i3.2xlarge",
        "vcpu": 8,
        "memory_gb": 61,
        "storage": "1 x 1,900 NVMe SSD",
        "network": "Up to 10 Gigabit",
        "instance_family": "i3",
        "architecture": "x86_64",
        "dbu_per_hour": 1.5,
        "pricing": {
          "on_demand": 0.624,
          "spot": 0.187,
          "reserved_1y_no_upfront": 0.372,
          "reserved_3y_all_upfront": 0.248
        },
        "label": "i3.2xlarge (8 vCPU, 61 GB RAM) - $0.624/hr"
      }
      // ... more instance types
    ]
  }
}
```

**Backend Query:**
```sql
SELECT 
    i.instance_type,
    i.vcpu,
    i.memory_gb,
    i.storage_type || ' (' || i.storage_capacity_gb || ' GB)' as storage,
    i.network_performance as network,
    i.instance_family,
    i.architecture,
    i.dbu_per_hour,
    -- Pricing for each payment option
    MAX(CASE WHEN v.pricing_tier = 'on_demand' THEN v.price_per_hour END) as price_on_demand,
    MAX(CASE WHEN v.pricing_tier = 'spot' THEN v.price_per_hour END) as price_spot,
    MAX(CASE WHEN v.payment_option = 'no_upfront' AND v.pricing_tier LIKE '%1y%' THEN v.price_per_hour END) as price_reserved_1y,
    MAX(CASE WHEN v.payment_option = 'all_upfront' AND v.pricing_tier LIKE '%3y%' THEN v.price_per_hour END) as price_reserved_3y
FROM lakemeter.sync_ref_instance_dbu_rates i
LEFT JOIN lakemeter.sync_pricing_vm_costs v 
    ON i.cloud = v.cloud 
    AND i.instance_type = v.instance_type
    AND v.region_code = :region
WHERE i.cloud = :cloud
GROUP BY i.instance_type, i.vcpu, i.memory_gb, i.storage_type, 
         i.storage_capacity_gb, i.network_performance, i.instance_family, 
         i.architecture, i.dbu_per_hour
ORDER BY i.vcpu, i.memory_gb;
```

---

### 3.2 Payment Options API

#### **GET /api/v1/payment-options**

Get available payment options for a specific cloud/region.

**Query Parameters:**
- `cloud` (required): AWS, AZURE, GCP
- `region` (optional): Filter by region
- `node_type` (optional): driver or worker (driver cannot be spot)

**Example Request:**
```
GET /api/v1/payment-options?cloud=AWS&node_type=worker
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "payment_options": [
      {
        "value": "on_demand",
        "label": "On-Demand",
        "description": "Pay by the hour with no commitment",
        "typical_savings": "0%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "spot",
        "label": "Spot Instances",
        "description": "Up to 90% discount, may be interrupted",
        "typical_savings": "70-90%",
        "available_for": ["worker"]
      },
      {
        "value": "reserved_1y_no_upfront",
        "label": "Reserved 1 Year (No Upfront)",
        "description": "1 year commitment, no upfront payment",
        "typical_savings": "40%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_1y_partial_upfront",
        "label": "Reserved 1 Year (Partial Upfront)",
        "description": "1 year commitment, partial upfront payment",
        "typical_savings": "42%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_1y_all_upfront",
        "label": "Reserved 1 Year (All Upfront)",
        "description": "1 year commitment, full upfront payment",
        "typical_savings": "44%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_3y_no_upfront",
        "label": "Reserved 3 Years (No Upfront)",
        "description": "3 year commitment, no upfront payment",
        "typical_savings": "56%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_3y_partial_upfront",
        "label": "Reserved 3 Years (Partial Upfront)",
        "description": "3 year commitment, partial upfront payment",
        "typical_savings": "58%",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_3y_all_upfront",
        "label": "Reserved 3 Years (All Upfront)",
        "description": "3 year commitment, full upfront payment",
        "typical_savings": "60%",
        "available_for": ["driver", "worker"]
      }
    ]
  }
}
```

**For Azure/GCP (Simpler):**
```json
{
  "success": true,
  "data": {
    "cloud": "AZURE",
    "payment_options": [
      {
        "value": "on_demand",
        "label": "On-Demand",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "spot",
        "label": "Spot",
        "available_for": ["worker"]
      },
      {
        "value": "reserved_1y",
        "label": "Reserved 1 Year",
        "available_for": ["driver", "worker"]
      },
      {
        "value": "reserved_3y",
        "label": "Reserved 3 Years",
        "available_for": ["driver", "worker"]
      }
    ]
  }
}
```

---

### 3.3 DBSQL Warehouse Config API

#### **GET /api/v1/dbsql/warehouse-configs**

Get DBSQL warehouse configurations (type, size, instance types).

**Query Parameters:**
- `cloud` (required): AWS, AZURE, GCP
- `warehouse_type` (optional): classic, pro, serverless

**Example Request:**
```
GET /api/v1/dbsql/warehouse-configs?cloud=AWS&warehouse_type=classic
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "warehouse_type": "classic",
    "configurations": [
      {
        "warehouse_size": "X-Small",
        "dbu_per_hour": 1,
        "driver_instance": "i3.xlarge",
        "worker_instance": "i3.xlarge",
        "worker_count": 1,
        "vcpu_total": 8,
        "memory_gb_total": 61,
        "label": "X-Small (1 DBU/hr, 8 vCPU, 61 GB RAM)"
      },
      {
        "warehouse_size": "Small",
        "dbu_per_hour": 2,
        "driver_instance": "i3.xlarge",
        "worker_instance": "i3.xlarge",
        "worker_count": 2,
        "vcpu_total": 12,
        "memory_gb_total": 91.5,
        "label": "Small (2 DBU/hr, 12 vCPU, 91.5 GB RAM)"
      },
      {
        "warehouse_size": "Medium",
        "dbu_per_hour": 4,
        "driver_instance": "i3.xlarge",
        "worker_instance": "i3.xlarge",
        "worker_count": 4,
        "vcpu_total": 20,
        "memory_gb_total": 152.5,
        "label": "Medium (4 DBU/hr, 20 vCPU, 152.5 GB RAM)"
      }
      // ... more sizes
    ]
  }
}
```

**Backend Query:**
```sql
SELECT 
    w.warehouse_type,
    w.warehouse_size,
    w.dbu_per_hour,
    w.driver_instance_type,
    w.worker_instance_type,
    w.num_workers,
    -- Calculate total resources
    (d.vcpu + w.num_workers * wk.vcpu) as vcpu_total,
    (d.memory_gb + w.num_workers * wk.memory_gb) as memory_gb_total
FROM lakemeter.sync_ref_dbsql_warehouse_config w
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates d 
    ON w.cloud = d.cloud AND w.driver_instance_type = d.instance_type
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates wk 
    ON w.cloud = wk.cloud AND w.worker_instance_type = wk.instance_type
WHERE w.cloud = :cloud
  AND w.warehouse_type = :warehouse_type
ORDER BY w.dbu_per_hour;
```

---

### 3.4 Model Serving GPU Types API

#### **GET /api/v1/model-serving/gpu-types**

Get available GPU types for Model Serving by cloud.

**Query Parameters:**
- `cloud` (required): AWS, AZURE, GCP

**Example Request:**
```
GET /api/v1/model-serving/gpu-types?cloud=AWS
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "gpu_types": [
      {
        "value": "cpu_small_1x",
        "label": "CPU Small (1x)",
        "specs": "4 vCPU, 16 GB RAM",
        "dbu_per_hour": 0.07,
        "use_case": "Small models, testing"
      },
      {
        "value": "cpu_medium_2x",
        "label": "CPU Medium (2x)",
        "specs": "8 vCPU, 32 GB RAM",
        "dbu_per_hour": 0.14,
        "use_case": "Medium models, moderate load"
      },
      {
        "value": "gpu_small_g4dn_1x",
        "label": "GPU Small - T4 (1x)",
        "specs": "NVIDIA T4, 16 GB GPU RAM",
        "dbu_per_hour": 3.40,
        "use_case": "Small LLMs, embeddings"
      },
      {
        "value": "gpu_medium_a10g_1x",
        "label": "GPU Medium - A10G (1x)",
        "specs": "NVIDIA A10G, 24 GB GPU RAM",
        "dbu_per_hour": 10.20,
        "use_case": "Medium LLMs, real-time inference"
      },
      {
        "value": "gpu_large_a100_1x",
        "label": "GPU Large - A100 (1x)",
        "specs": "NVIDIA A100, 40 GB GPU RAM",
        "dbu_per_hour": 40.80,
        "use_case": "Large LLMs, high throughput"
      }
    ]
  }
}
```

**Backend Query:**
```sql
SELECT 
    size_or_model as gpu_type,
    dbu_rate as dbu_per_hour,
    description
FROM lakemeter.sync_product_serverless_rates
WHERE cloud = :cloud
  AND product = 'model_serving'
ORDER BY dbu_rate;
```

---

### 3.5 FMAPI Models API

#### **GET /api/v1/fmapi/models**

Get available FMAPI models (Databricks and Proprietary).

**Query Parameters:**
- `type` (required): databricks or proprietary
- `provider` (optional): openai, anthropic, google (for proprietary)
- `cloud` (optional): Filter by cloud availability

**Example Request:**
```
GET /api/v1/fmapi/models?type=proprietary&provider=anthropic
```

**Response:**
```json
{
  "success": true,
  "data": {
    "type": "proprietary",
    "provider": "anthropic",
    "models": [
      {
        "value": "claude-haiku-4-5",
        "label": "Claude 3.5 Haiku",
        "description": "Fast, affordable model for simple tasks",
        "context_lengths": ["all"],
        "endpoint_types": ["global", "in_geo"],
        "rate_types": ["input_token", "output_token", "cache_read", "cache_write"],
        "pricing": {
          "input_token": {
            "dbu_per_million": 1.429,
            "global": 0.10,
            "in_geo": 0.11
          },
          "output_token": {
            "dbu_per_million": 7.143,
            "global": 0.50,
            "in_geo": 0.55
          },
          "cache_read": {
            "dbu_per_million": 0.143,
            "global": 0.01,
            "in_geo": 0.011
          },
          "cache_write": {
            "dbu_per_million": 1.786,
            "global": 0.125,
            "in_geo": 0.138
          }
        }
      },
      {
        "value": "claude-sonnet-4-5",
        "label": "Claude 3.5 Sonnet",
        "description": "Balanced performance and speed",
        "context_lengths": ["all"],
        "endpoint_types": ["global", "in_geo"],
        "rate_types": ["input_token", "output_token", "cache_read", "cache_write"],
        "pricing": {
          "input_token": {
            "dbu_per_million": 42.857,
            "global": 3.00,
            "in_geo": 3.30
          },
          "output_token": {
            "dbu_per_million": 214.286,
            "global": 15.00,
            "in_geo": 16.50
          }
        }
      }
    ]
  }
}
```

---

### 3.6 Regions API

#### **GET /api/v1/regions**

Get available regions for a cloud.

**Query Parameters:**
- `cloud` (required): AWS, AZURE, GCP
- `tier` (optional): Filter by tier availability

**Example Request:**
```
GET /api/v1/regions?cloud=AWS&tier=PREMIUM
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "tier": "PREMIUM",
    "count": 20,
    "regions": [
      {
        "value": "us-east-1",
        "label": "US East (N. Virginia)",
        "location": "North America",
        "available_tiers": ["STANDARD", "PREMIUM", "ENTERPRISE"]
      },
      {
        "value": "us-west-2",
        "label": "US West (Oregon)",
        "location": "North America",
        "available_tiers": ["STANDARD", "PREMIUM", "ENTERPRISE"]
      },
      {
        "value": "eu-west-1",
        "label": "Europe (Ireland)",
        "location": "Europe",
        "available_tiers": ["STANDARD", "PREMIUM", "ENTERPRISE"]
      },
      {
        "value": "ap-southeast-1",
        "label": "Asia Pacific (Singapore)",
        "location": "Asia Pacific",
        "available_tiers": ["STANDARD", "PREMIUM", "ENTERPRISE"]
      }
    ]
  }
}
```

**Backend Query:**
```sql
SELECT DISTINCT
    region_code as value,
    region_name as label,
    tier
FROM lakemeter.sync_ref_sku_region_map
WHERE cloud = :cloud
  AND (:tier IS NULL OR tier = :tier)
ORDER BY region_name;
```

---

## 4. Frontend Usage Flows

### 4.1 Classic Jobs Configuration

**User Flow:**
1. User selects workload type: **JOBS**
2. User selects cloud: **AWS**
3. User selects region: **us-east-1**
4. User selects tier: **PREMIUM**
5. User toggles **serverless_enabled = OFF** (Classic)

**Frontend API Calls:**

```javascript
// Step 1: Get available instance types for driver
const driverInstances = await fetch(
  '/api/v1/instance-types?cloud=AWS&region=us-east-1&workload_type=JOBS&sort_by=vcpu'
);

// Step 2: Populate driver dropdown
<select name="driver_node_type">
  <option value="i3.xlarge">i3.xlarge (4 vCPU, 30.5 GB RAM) - $0.312/hr</option>
  <option value="i3.2xlarge">i3.2xlarge (8 vCPU, 61 GB RAM) - $0.624/hr</option>
  ...
</select>

// Step 3: Get payment options for driver (no spot allowed)
const driverPaymentOptions = await fetch(
  '/api/v1/payment-options?cloud=AWS&node_type=driver'
);

// Step 4: Populate driver payment option dropdown
<select name="driver_pricing_tier">
  <option value="on_demand">On-Demand</option>
  <option value="reserved_1y_no_upfront">Reserved 1Y (No Upfront) - 40% savings</option>
  ...
</select>

// Step 5: Get payment options for worker (spot allowed)
const workerPaymentOptions = await fetch(
  '/api/v1/payment-options?cloud=AWS&node_type=worker'
);

// Step 6: Populate worker payment option dropdown
<select name="worker_pricing_tier">
  <option value="on_demand">On-Demand</option>
  <option value="spot">Spot - 70-90% savings</option>
  <option value="reserved_1y_no_upfront">Reserved 1Y (No Upfront) - 40% savings</option>
  ...
</select>
```

---

### 4.2 DBSQL Serverless Configuration

**User Flow:**
1. User selects workload type: **DBSQL**
2. User selects cloud: **AWS**
3. User selects region: **us-east-1**
4. User selects tier: **PREMIUM**
5. User selects warehouse type: **serverless**

**Frontend API Calls:**

```javascript
// Step 1: Get DBSQL warehouse sizes
const warehouseSizes = await fetch(
  '/api/v1/dbsql/warehouse-configs?cloud=AWS&warehouse_type=serverless'
);

// Step 2: Populate warehouse size dropdown
<select name="dbsql_warehouse_size">
  <option value="X-Small">X-Small (1 DBU/hr) - $0.07/hr</option>
  <option value="Small">Small (2 DBU/hr) - $0.14/hr</option>
  <option value="Medium">Medium (4 DBU/hr) - $0.28/hr</option>
  <option value="Large">Large (8 DBU/hr) - $0.56/hr</option>
  ...
</select>

// Step 3: Show estimated cost as user types hours
const estimatedCost = dbu_per_hour * hours_per_month * dbu_price;
<div>Estimated cost: ${estimatedCost.toFixed(2)}/month</div>
```

---

### 4.3 Model Serving Configuration

**User Flow:**
1. User selects workload type: **MODEL_SERVING**
2. User selects cloud: **AWS**
3. User selects region: **us-east-1**
4. User selects tier: **PREMIUM**

**Frontend API Calls:**

```javascript
// Step 1: Get GPU types for AWS
const gpuTypes = await fetch(
  '/api/v1/model-serving/gpu-types?cloud=AWS'
);

// Step 2: Populate GPU type dropdown with specs
<select name="model_serving_gpu_type">
  <option value="cpu_small_1x">CPU Small (4 vCPU, 16 GB RAM) - $0.07 DBU/hr</option>
  <option value="gpu_small_g4dn_1x">GPU Small - T4 (16 GB GPU RAM) - $3.40 DBU/hr</option>
  <option value="gpu_medium_a10g_1x">GPU Medium - A10G (24 GB GPU RAM) - $10.20 DBU/hr</option>
  ...
</select>
```

---

## 5. Data Requirements

### 5.1 Missing Data: Instance Metadata

**Current State:**
- `sync_ref_instance_dbu_rates` has instance_type and dbu_per_hour
- Does NOT have vCPU, memory, storage specs

**Required Action:**
Add columns to `sync_ref_instance_dbu_rates`:

```sql
ALTER TABLE lakemeter.sync_ref_instance_dbu_rates
ADD COLUMN IF NOT EXISTS vcpu INT,
ADD COLUMN IF NOT EXISTS memory_gb DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS storage_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS storage_capacity_gb INT,
ADD COLUMN IF NOT EXISTS network_performance VARCHAR(50),
ADD COLUMN IF NOT EXISTS instance_family VARCHAR(20),
ADD COLUMN IF NOT EXISTS gpu_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS gpu_count INT,
ADD COLUMN IF NOT EXISTS architecture VARCHAR(20);
```

**Data Population Strategy:**

Option 1: Manual CSV Import (Quick Start)
- Create CSV with instance specs from AWS/Azure/GCP documentation
- Import into table

Option 2: Automated Sync (Long-term)
- Python script to fetch specs from cloud provider APIs
- AWS: boto3 `describe_instance_types()`
- Azure: Azure SDK
- GCP: Compute Engine API

**Example Data Source:**

**AWS Instance Types CSV:**
```csv
cloud,instance_type,vcpu,memory_gb,storage_type,storage_capacity_gb,network_performance,instance_family,architecture
AWS,i3.xlarge,4,30.5,NVMe SSD,950,Up to 10 Gigabit,i3,x86_64
AWS,i3.2xlarge,8,61,NVMe SSD,1900,Up to 10 Gigabit,i3,x86_64
AWS,i3.4xlarge,16,122,NVMe SSD,3800,Up to 10 Gigabit,i3,x86_64
```

---

### 5.2 Payment Option Metadata

**Create Reference Table:**

```sql
CREATE TABLE lakemeter.ref_payment_options (
    cloud VARCHAR(20),
    payment_option VARCHAR(50),
    label VARCHAR(100),
    description TEXT,
    typical_savings_pct INT,
    available_for_driver BOOLEAN,
    available_for_worker BOOLEAN,
    PRIMARY KEY (cloud, payment_option)
);

INSERT INTO lakemeter.ref_payment_options VALUES
('AWS', 'on_demand', 'On-Demand', 'Pay by the hour with no commitment', 0, true, true),
('AWS', 'spot', 'Spot Instances', 'Up to 90% discount, may be interrupted', 80, false, true),
('AWS', 'reserved_1y_no_upfront', 'Reserved 1 Year (No Upfront)', '1 year commitment, no upfront payment', 40, true, true),
('AWS', 'reserved_1y_partial_upfront', 'Reserved 1 Year (Partial Upfront)', '1 year commitment, partial upfront payment', 42, true, true),
('AWS', 'reserved_1y_all_upfront', 'Reserved 1 Year (All Upfront)', '1 year commitment, full upfront payment', 44, true, true),
('AWS', 'reserved_3y_no_upfront', 'Reserved 3 Years (No Upfront)', '3 year commitment, no upfront payment', 56, true, true),
('AWS', 'reserved_3y_partial_upfront', 'Reserved 3 Years (Partial Upfront)', '3 year commitment, partial upfront payment', 58, true, true),
('AWS', 'reserved_3y_all_upfront', 'Reserved 3 Years (All Upfront)', '3 year commitment, full upfront payment', 60, true, true),
('AZURE', 'on_demand', 'On-Demand', 'Pay as you go', 0, true, true),
('AZURE', 'spot', 'Spot', 'Low priority VMs with discounts', 70, false, true),
('AZURE', 'reserved_1y', 'Reserved 1 Year', '1 year commitment', 40, true, true),
('AZURE', 'reserved_3y', 'Reserved 3 Years', '3 year commitment', 60, true, true),
('GCP', 'on_demand', 'On-Demand', 'Pay as you go', 0, true, true),
('GCP', 'spot', 'Spot (Preemptible)', 'Up to 80% discount', 70, false, true),
('GCP', 'reserved_1y', 'Committed Use 1 Year', '1 year commitment', 37, true, true),
('GCP', 'reserved_3y', 'Committed Use 3 Years', '3 year commitment', 55, true, true);
```

---

## 6. Implementation Checklist

### Phase 1: Database Schema Updates
- [ ] Add metadata columns to `sync_ref_instance_dbu_rates`
- [ ] Create `ref_payment_options` table
- [ ] Populate instance metadata (CSV import or API sync)
- [ ] Populate payment options reference data

### Phase 2: API Endpoints
- [ ] GET /api/v1/instance-types
- [ ] GET /api/v1/payment-options
- [ ] GET /api/v1/dbsql/warehouse-configs
- [ ] GET /api/v1/model-serving/gpu-types
- [ ] GET /api/v1/fmapi/models
- [ ] GET /api/v1/regions

### Phase 3: Caching
- [ ] Cache instance metadata (TTL: 24 hours)
- [ ] Cache payment options (TTL: 24 hours)
- [ ] Cache DBSQL configs (TTL: 1 hour)
- [ ] Cache regions (TTL: 24 hours)

### Phase 4: Frontend Integration
- [ ] Build dynamic dropdown components
- [ ] Implement cascading filters (cloud → region → instance)
- [ ] Add instance spec tooltips/cards
- [ ] Add cost estimator widget

---

## 7. Next Steps

1. **Approve API Design**
   - Review endpoints and response formats
   - Confirm data requirements

2. **Populate Instance Metadata**
   - Create CSV with AWS/Azure/GCP instance specs
   - OR: Build automated sync script

3. **Implement Phase 2 Endpoints**
   - Start with `/instance-types` and `/payment-options`
   - Test with frontend mockups

---

**Status:** 📋 Detailed Planning Complete - Awaiting Approval & Data Population

**Blockers:** Need instance metadata (vCPU, memory) to be populated in database


