# Instance Types API - Detailed Implementation Plan

## 1. API Endpoint Design

### **GET /api/v1/instance-types**

**Purpose:** Return available instance types with specifications and pricing for a given cloud/region.

---

## 2. Database Tables Analysis

### 2.1 Current Tables Available

#### **Table 1: `sync_ref_instance_dbu_rates`**

**Columns:**
```sql
cloud             VARCHAR(20)    -- AWS, AZURE, GCP
instance_type     VARCHAR(100)   -- i3.xlarge, Standard_E8s_v5, n2-standard-8
dbu_per_hour      DECIMAL(18,4)  -- DBU rate per hour for this instance
```

**Sample Data:**
```
cloud  | instance_type      | dbu_per_hour
-------|--------------------|--------------
AWS    | i3.xlarge          | 0.7500
AWS    | i3.2xlarge         | 1.5000
AWS    | i3.4xlarge         | 3.0000
AZURE  | Standard_E8s_v5    | 1.0000
GCP    | n2-standard-8      | 1.0000
```

**What We Have:** ✅ Instance type, DBU rate per cloud
**What We're Missing:** ❌ vCPU, memory, storage specs, instance family

---

#### **Table 2: `sync_pricing_vm_costs`**

**Columns:**
```sql
cloud             VARCHAR(20)    -- AWS, AZURE, GCP
region_code       VARCHAR(50)    -- us-east-1, eastus, us-central1
instance_type     VARCHAR(100)   -- i3.xlarge
pricing_tier      VARCHAR(20)    -- on_demand, spot, reserved_1y, reserved_3y
payment_option    VARCHAR(20)    -- NA, no_upfront, partial_upfront, all_upfront
price_per_hour    DECIMAL(18,6)  -- VM cost per hour
```

**Sample Data:**
```
cloud | region_code | instance_type | pricing_tier | payment_option      | price_per_hour
------|-------------|---------------|--------------|---------------------|----------------
AWS   | us-east-1   | i3.xlarge     | on_demand    | NA                  | 0.312000
AWS   | us-east-1   | i3.xlarge     | spot         | NA                  | 0.093600
AWS   | us-east-1   | i3.xlarge     | reserved_1y  | no_upfront          | 0.186000
AWS   | us-east-1   | i3.xlarge     | reserved_1y  | partial_upfront     | 0.178000
AWS   | us-east-1   | i3.xlarge     | reserved_1y  | all_upfront         | 0.172000
AWS   | us-east-1   | i3.xlarge     | reserved_3y  | no_upfront          | 0.124000
```

**What We Have:** ✅ Instance pricing by region, tier, payment option
**What We're Missing:** ❌ vCPU, memory specs

---

#### **Table 3: `sync_ref_sku_region_map`**

**Columns:**
```sql
cloud             VARCHAR(20)
region_code       VARCHAR(50)
region_name       VARCHAR(100)  -- "US East (N. Virginia)"
tier              VARCHAR(20)   -- STANDARD, PREMIUM, ENTERPRISE
```

**What We Have:** ✅ Region codes and display names
**What We're Missing:** Nothing (this table is complete)

---

### 2.2 Missing Data: Instance Specifications

**Critical Missing Columns in `sync_ref_instance_dbu_rates`:**

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `vcpu` | INT | Number of virtual CPUs | AWS/Azure/GCP docs |
| `memory_gb` | DECIMAL(10,2) | RAM in GB | AWS/Azure/GCP docs |
| `storage_type` | VARCHAR(50) | "NVMe SSD", "Local SSD", "EBS only" | AWS/Azure/GCP docs |
| `storage_gb` | INT | Local storage capacity | AWS/Azure/GCP docs |
| `network_gbps` | VARCHAR(20) | Network bandwidth | AWS/Azure/GCP docs |
| `instance_family` | VARCHAR(20) | "i3", "E8s_v5", "n2" | Parse from instance_type |
| `processor` | VARCHAR(50) | CPU model | AWS/Azure/GCP docs |

**Why This Data is Critical:**
- Frontend needs to show "i3.xlarge (4 vCPU, 30.5 GB RAM)" in dropdown
- Users need specs to make informed decisions
- Different instance types have very different performance characteristics

---

## 3. Data Population Strategy

### Option A: CSV Import (Fastest - Recommended for MVP) ✅

**Step 1:** Create CSV files with instance metadata

**AWS Instance Metadata CSV:**
```csv
cloud,instance_type,vcpu,memory_gb,storage_type,storage_gb,network_gbps,instance_family,processor
AWS,i3.xlarge,4,30.5,NVMe SSD,950,10,i3,Intel Xeon E5-2686 v4
AWS,i3.2xlarge,8,61,NVMe SSD,1900,10,i3,Intel Xeon E5-2686 v4
AWS,i3.4xlarge,16,122,NVMe SSD,3800,10,i3,Intel Xeon E5-2686 v4
AWS,i3.8xlarge,32,244,NVMe SSD,7600,10,i3,Intel Xeon E5-2686 v4
AWS,i3.16xlarge,64,488,NVMe SSD,15200,25,i3,Intel Xeon E5-2686 v4
AWS,m5.xlarge,4,16,EBS only,0,10,m5,Intel Xeon Platinum 8175M
AWS,m5.2xlarge,8,32,EBS only,0,10,m5,Intel Xeon Platinum 8175M
AWS,r5.xlarge,4,32,EBS only,0,10,r5,Intel Xeon Platinum 8175M
AWS,c5.xlarge,4,8,EBS only,0,10,c5,Intel Xeon Platinum 8124M
```

**Azure Instance Metadata CSV:**
```csv
cloud,instance_type,vcpu,memory_gb,storage_type,storage_gb,network_gbps,instance_family,processor
AZURE,Standard_E4s_v5,4,32,Local SSD,150,12.5,E_v5,Intel Ice Lake / AMD EPYC Milan
AZURE,Standard_E8s_v5,8,64,Local SSD,300,12.5,E_v5,Intel Ice Lake / AMD EPYC Milan
AZURE,Standard_E16s_v5,16,128,Local SSD,600,12.5,E_v5,Intel Ice Lake / AMD EPYC Milan
AZURE,Standard_D4s_v5,4,16,Local SSD,150,12.5,D_v5,Intel Ice Lake / AMD EPYC Milan
AZURE,Standard_D8s_v5,8,32,Local SSD,300,12.5,D_v5,Intel Ice Lake / AMD EPYC Milan
```

**GCP Instance Metadata CSV:**
```csv
cloud,instance_type,vcpu,memory_gb,storage_type,storage_gb,network_gbps,instance_family,processor
GCP,n2-standard-4,4,16,Local SSD (optional),375,10,n2,Intel Cascade Lake / Ice Lake
GCP,n2-standard-8,8,32,Local SSD (optional),375,16,n2,Intel Cascade Lake / Ice Lake
GCP,n2-standard-16,16,64,Local SSD (optional),375,32,n2,Intel Cascade Lake / Ice Lake
GCP,n2-highmem-4,4,32,Local SSD (optional),375,10,n2,Intel Cascade Lake / Ice Lake
GCP,n2-highmem-8,8,64,Local SSD (optional),375,16,n2,Intel Cascade Lake / Ice Lake
```

**Step 2:** Alter table to add columns

```sql
ALTER TABLE lakemeter.sync_ref_instance_dbu_rates
ADD COLUMN vcpu INT,
ADD COLUMN memory_gb DECIMAL(10,2),
ADD COLUMN storage_type VARCHAR(50),
ADD COLUMN storage_gb INT,
ADD COLUMN network_gbps VARCHAR(20),
ADD COLUMN instance_family VARCHAR(20),
ADD COLUMN processor VARCHAR(50);
```

**Step 3:** Import CSV data

```sql
-- For each instance type, update metadata
UPDATE lakemeter.sync_ref_instance_dbu_rates
SET 
    vcpu = staging.vcpu,
    memory_gb = staging.memory_gb,
    storage_type = staging.storage_type,
    storage_gb = staging.storage_gb,
    network_gbps = staging.network_gbps,
    instance_family = staging.instance_family,
    processor = staging.processor
FROM staging_instance_metadata staging
WHERE sync_ref_instance_dbu_rates.cloud = staging.cloud
  AND sync_ref_instance_dbu_rates.instance_type = staging.instance_type;
```

---

### Option B: Automated API Sync (Long-term)

**Python Script to Fetch Instance Specs:**

```python
# AWS - Use boto3
import boto3

ec2 = boto3.client('ec2', region_name='us-east-1')
response = ec2.describe_instance_types()

for instance in response['InstanceTypes']:
    instance_type = instance['InstanceType']
    vcpu = instance['VCpuInfo']['DefaultVCpus']
    memory_mb = instance['MemoryInfo']['SizeInMiB']
    memory_gb = memory_mb / 1024
    # ... extract other specs
```

**Azure - Use Azure SDK:**
```python
from azure.mgmt.compute import ComputeManagementClient

compute_client = ComputeManagementClient(credential, subscription_id)
vm_sizes = compute_client.virtual_machine_sizes.list(location='eastus')

for size in vm_sizes:
    instance_type = size.name
    vcpu = size.number_of_cores
    memory_gb = size.memory_in_mb / 1024
    # ... extract other specs
```

**For MVP: Use Option A (CSV Import)**

---

## 4. API Parameters Design

### 4.1 Query Parameters

| Parameter | Type | Required | Description | Default | Example |
|-----------|------|----------|-------------|---------|---------|
| `cloud` | string | **Yes** | Cloud provider | - | `AWS`, `AZURE`, `GCP` |
| `region` | string | No | Filter by region | All regions | `us-east-1`, `eastus` |
| `workload_type` | string | No | Filter by workload compatibility | All | `JOBS`, `DBSQL` |
| `min_vcpu` | int | No | Minimum vCPU | 0 | `4` |
| `max_vcpu` | int | No | Maximum vCPU | 9999 | `16` |
| `min_memory_gb` | decimal | No | Minimum memory (GB) | 0 | `16` |
| `max_memory_gb` | decimal | No | Maximum memory (GB) | 9999 | `128` |
| `sort_by` | string | No | Sort field | `instance_type` | `vcpu`, `memory_gb`, `price_on_demand` |
| `sort_order` | string | No | Sort direction | `asc` | `asc`, `desc` |
| `limit` | int | No | Max results | 100 | `20` |

### 4.2 Parameter Validation Rules

```python
from pydantic import BaseModel, Field, validator
from enum import Enum

class Cloud(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"

class SortBy(str, Enum):
    instance_type = "instance_type"
    vcpu = "vcpu"
    memory_gb = "memory_gb"
    price_on_demand = "price_on_demand"
    dbu_per_hour = "dbu_per_hour"

class InstanceTypesRequest(BaseModel):
    cloud: Cloud
    region: str | None = None
    workload_type: str | None = None
    min_vcpu: int = Field(default=0, ge=0, le=1000)
    max_vcpu: int = Field(default=9999, ge=0, le=1000)
    min_memory_gb: float = Field(default=0, ge=0, le=10000)
    max_memory_gb: float = Field(default=9999, ge=0, le=10000)
    sort_by: SortBy = SortBy.instance_type
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    limit: int = Field(default=100, ge=1, le=500)
    
    @validator('max_vcpu')
    def validate_vcpu_range(cls, v, values):
        if 'min_vcpu' in values and v < values['min_vcpu']:
            raise ValueError('max_vcpu must be >= min_vcpu')
        return v
```

---

## 5. SQL Query Design

### 5.1 Base Query (No Region Filter)

```sql
SELECT 
    i.cloud,
    i.instance_type,
    i.vcpu,
    i.memory_gb,
    i.storage_type,
    i.storage_gb,
    i.network_gbps,
    i.instance_family,
    i.processor,
    i.dbu_per_hour,
    
    -- Aggregate pricing across all regions for this cloud
    -- (User hasn't selected region yet, so show "typical" pricing)
    AVG(CASE WHEN v.pricing_tier = 'on_demand' AND v.payment_option = 'NA' 
             THEN v.price_per_hour END) as price_on_demand_avg,
    AVG(CASE WHEN v.pricing_tier = 'spot' AND v.payment_option = 'NA' 
             THEN v.price_per_hour END) as price_spot_avg,
    
    -- Count how many regions this instance is available in
    COUNT(DISTINCT v.region_code) as available_regions_count,
    
    -- Label for frontend dropdown
    CONCAT(
        i.instance_type, 
        ' (', i.vcpu, ' vCPU, ', i.memory_gb, ' GB RAM) - $',
        ROUND(AVG(CASE WHEN v.pricing_tier = 'on_demand' AND v.payment_option = 'NA' 
                       THEN v.price_per_hour END), 3),
        '/hr'
    ) as label

FROM lakemeter.sync_ref_instance_dbu_rates i

LEFT JOIN lakemeter.sync_pricing_vm_costs v
    ON i.cloud = v.cloud
    AND i.instance_type = v.instance_type

WHERE i.cloud = :cloud
  AND (:min_vcpu IS NULL OR i.vcpu >= :min_vcpu)
  AND (:max_vcpu IS NULL OR i.vcpu <= :max_vcpu)
  AND (:min_memory_gb IS NULL OR i.memory_gb >= :min_memory_gb)
  AND (:max_memory_gb IS NULL OR i.memory_gb <= :max_memory_gb)

GROUP BY 
    i.cloud, i.instance_type, i.vcpu, i.memory_gb, 
    i.storage_type, i.storage_gb, i.network_gbps, 
    i.instance_family, i.processor, i.dbu_per_hour

ORDER BY 
    CASE WHEN :sort_by = 'vcpu' THEN i.vcpu END,
    CASE WHEN :sort_by = 'memory_gb' THEN i.memory_gb END,
    CASE WHEN :sort_by = 'instance_type' THEN i.instance_type END,
    CASE WHEN :sort_by = 'dbu_per_hour' THEN i.dbu_per_hour END

LIMIT :limit;
```

---

### 5.2 Query with Region Filter (User Selected Region)

```sql
SELECT 
    i.cloud,
    i.instance_type,
    i.vcpu,
    i.memory_gb,
    i.storage_type,
    i.storage_gb,
    i.network_gbps,
    i.instance_family,
    i.processor,
    i.dbu_per_hour,
    
    -- Pricing for SPECIFIC region
    MAX(CASE WHEN v.pricing_tier = 'on_demand' AND v.payment_option = 'NA' 
             THEN v.price_per_hour END) as price_on_demand,
    MAX(CASE WHEN v.pricing_tier = 'spot' AND v.payment_option = 'NA' 
             THEN v.price_per_hour END) as price_spot,
    MAX(CASE WHEN v.pricing_tier = 'reserved_1y' AND v.payment_option = 'no_upfront' 
             THEN v.price_per_hour END) as price_reserved_1y_no_upfront,
    MAX(CASE WHEN v.pricing_tier = 'reserved_1y' AND v.payment_option = 'partial_upfront' 
             THEN v.price_per_hour END) as price_reserved_1y_partial_upfront,
    MAX(CASE WHEN v.pricing_tier = 'reserved_1y' AND v.payment_option = 'all_upfront' 
             THEN v.price_per_hour END) as price_reserved_1y_all_upfront,
    MAX(CASE WHEN v.pricing_tier = 'reserved_3y' AND v.payment_option = 'no_upfront' 
             THEN v.price_per_hour END) as price_reserved_3y_no_upfront,
    MAX(CASE WHEN v.pricing_tier = 'reserved_3y' AND v.payment_option = 'partial_upfront' 
             THEN v.price_per_hour END) as price_reserved_3y_partial_upfront,
    MAX(CASE WHEN v.pricing_tier = 'reserved_3y' AND v.payment_option = 'all_upfront' 
             THEN v.price_per_hour END) as price_reserved_3y_all_upfront,
    
    -- Region info
    r.region_name,
    
    -- Label with ACTUAL region pricing
    CONCAT(
        i.instance_type, 
        ' (', i.vcpu, ' vCPU, ', i.memory_gb, ' GB RAM) - $',
        ROUND(MAX(CASE WHEN v.pricing_tier = 'on_demand' AND v.payment_option = 'NA' 
                       THEN v.price_per_hour END), 3),
        '/hr'
    ) as label

FROM lakemeter.sync_ref_instance_dbu_rates i

INNER JOIN lakemeter.sync_pricing_vm_costs v
    ON i.cloud = v.cloud
    AND i.instance_type = v.instance_type
    AND v.region_code = :region

LEFT JOIN lakemeter.sync_ref_sku_region_map r
    ON v.cloud = r.cloud
    AND v.region_code = r.region_code
    AND r.tier = 'PREMIUM'  -- Use PREMIUM as default for region name lookup

WHERE i.cloud = :cloud
  AND (:min_vcpu IS NULL OR i.vcpu >= :min_vcpu)
  AND (:max_vcpu IS NULL OR i.vcpu <= :max_vcpu)
  AND (:min_memory_gb IS NULL OR i.memory_gb >= :min_memory_gb)
  AND (:max_memory_gb IS NULL OR i.memory_gb <= :max_memory_gb)

GROUP BY 
    i.cloud, i.instance_type, i.vcpu, i.memory_gb, 
    i.storage_type, i.storage_gb, i.network_gbps, 
    i.instance_family, i.processor, i.dbu_per_hour,
    r.region_name

ORDER BY 
    CASE WHEN :sort_by = 'vcpu' THEN i.vcpu END ASC,
    CASE WHEN :sort_by = 'memory_gb' THEN i.memory_gb END ASC,
    CASE WHEN :sort_by = 'instance_type' THEN i.instance_type END ASC

LIMIT :limit;
```

---

## 6. Response Format

### 6.1 Success Response (With Region)

```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "region": "us-east-1",
    "region_name": "US East (N. Virginia)",
    "count": 15,
    "instance_types": [
      {
        "instance_type": "i3.xlarge",
        "vcpu": 4,
        "memory_gb": 30.5,
        "storage": {
          "type": "NVMe SSD",
          "capacity_gb": 950
        },
        "network_gbps": "Up to 10",
        "instance_family": "i3",
        "processor": "Intel Xeon E5-2686 v4",
        "dbu_per_hour": 0.75,
        "pricing": {
          "on_demand": 0.312,
          "spot": 0.0936,
          "reserved_1y_no_upfront": 0.186,
          "reserved_1y_partial_upfront": 0.178,
          "reserved_1y_all_upfront": 0.172,
          "reserved_3y_no_upfront": 0.132,
          "reserved_3y_partial_upfront": 0.128,
          "reserved_3y_all_upfront": 0.124
        },
        "savings": {
          "spot": "70%",
          "reserved_1y_all_upfront": "45%",
          "reserved_3y_all_upfront": "60%"
        },
        "label": "i3.xlarge (4 vCPU, 30.5 GB RAM) - $0.312/hr"
      },
      {
        "instance_type": "i3.2xlarge",
        "vcpu": 8,
        "memory_gb": 61,
        "storage": {
          "type": "NVMe SSD",
          "capacity_gb": 1900
        },
        "network_gbps": "Up to 10",
        "instance_family": "i3",
        "processor": "Intel Xeon E5-2686 v4",
        "dbu_per_hour": 1.5,
        "pricing": {
          "on_demand": 0.624,
          "spot": 0.187,
          "reserved_1y_no_upfront": 0.372,
          "reserved_3y_all_upfront": 0.248
        },
        "savings": {
          "spot": "70%",
          "reserved_1y_no_upfront": "40%",
          "reserved_3y_all_upfront": "60%"
        },
        "label": "i3.2xlarge (8 vCPU, 61 GB RAM) - $0.624/hr"
      }
    ]
  },
  "metadata": {
    "query_time_ms": 45,
    "cache_hit": false,
    "timestamp": "2025-01-20T10:30:00Z"
  }
}
```

---

### 6.2 Success Response (No Region - Aggregated)

```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "region": null,
    "region_name": null,
    "count": 45,
    "note": "Pricing shown is average across all regions. Select a region for exact pricing.",
    "instance_types": [
      {
        "instance_type": "i3.xlarge",
        "vcpu": 4,
        "memory_gb": 30.5,
        "storage": {
          "type": "NVMe SSD",
          "capacity_gb": 950
        },
        "network_gbps": "Up to 10",
        "instance_family": "i3",
        "processor": "Intel Xeon E5-2686 v4",
        "dbu_per_hour": 0.75,
        "pricing": {
          "on_demand_avg": 0.315,
          "spot_avg": 0.095
        },
        "available_regions_count": 20,
        "label": "i3.xlarge (4 vCPU, 30.5 GB RAM) - ~$0.315/hr"
      }
    ]
  }
}
```

---

### 6.3 Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_CLOUD",
    "message": "Invalid cloud provider. Must be one of: AWS, AZURE, GCP",
    "field": "cloud",
    "provided_value": "ALIBABA"
  },
  "timestamp": "2025-01-20T10:30:00Z",
  "request_id": "req_abc123"
}
```

---

## 7. Python Implementation (FastAPI)

### 7.1 Service Layer

```python
# services/instance_types.py

from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal

class InstanceTypesService:
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def get_instance_types(
        self,
        cloud: str,
        region: Optional[str] = None,
        min_vcpu: Optional[int] = None,
        max_vcpu: Optional[int] = None,
        min_memory_gb: Optional[float] = None,
        max_memory_gb: Optional[float] = None,
        sort_by: str = "instance_type",
        sort_order: str = "asc",
        limit: int = 100
    ):
        """Get instance types with specs and pricing"""
        
        if region:
            query = self._build_query_with_region()
        else:
            query = self._build_query_without_region()
        
        params = {
            "cloud": cloud,
            "region": region,
            "min_vcpu": min_vcpu,
            "max_vcpu": max_vcpu,
            "min_memory_gb": min_memory_gb,
            "max_memory_gb": max_memory_gb,
            "sort_by": sort_by,
            "limit": limit
        }
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Transform results into response format
        instance_types = []
        for row in results:
            instance_types.append({
                "instance_type": row["instance_type"],
                "vcpu": row["vcpu"],
                "memory_gb": float(row["memory_gb"]),
                "storage": {
                    "type": row["storage_type"],
                    "capacity_gb": row["storage_gb"]
                },
                "network_gbps": row["network_gbps"],
                "instance_family": row["instance_family"],
                "processor": row["processor"],
                "dbu_per_hour": float(row["dbu_per_hour"]),
                "pricing": self._extract_pricing(row, region),
                "savings": self._calculate_savings(row, region),
                "label": row["label"]
            })
        
        return {
            "cloud": cloud,
            "region": region,
            "region_name": results[0]["region_name"] if results and region else None,
            "count": len(instance_types),
            "instance_types": instance_types
        }
    
    def _extract_pricing(self, row, region):
        """Extract pricing from row based on whether region is specified"""
        if region:
            return {
                "on_demand": float(row["price_on_demand"]) if row["price_on_demand"] else None,
                "spot": float(row["price_spot"]) if row["price_spot"] else None,
                "reserved_1y_no_upfront": float(row["price_reserved_1y_no_upfront"]) if row.get("price_reserved_1y_no_upfront") else None,
                "reserved_3y_all_upfront": float(row["price_reserved_3y_all_upfront"]) if row.get("price_reserved_3y_all_upfront") else None
            }
        else:
            return {
                "on_demand_avg": float(row["price_on_demand_avg"]) if row["price_on_demand_avg"] else None,
                "spot_avg": float(row["price_spot_avg"]) if row["price_spot_avg"] else None
            }
    
    def _calculate_savings(self, row, region):
        """Calculate savings percentages"""
        if not region or not row["price_on_demand"]:
            return {}
        
        on_demand = float(row["price_on_demand"])
        savings = {}
        
        if row["price_spot"]:
            savings["spot"] = f"{int((1 - float(row['price_spot']) / on_demand) * 100)}%"
        
        if row.get("price_reserved_3y_all_upfront"):
            savings["reserved_3y_all_upfront"] = f"{int((1 - float(row['price_reserved_3y_all_upfront']) / on_demand) * 100)}%"
        
        return savings
```

---

### 7.2 Route Handler

```python
# routes/instance_types.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from models.response import InstanceTypesResponse
from services.instance_types import InstanceTypesService
from services.database import get_db_connection

router = APIRouter(prefix="/api/v1", tags=["instance-types"])

@router.get("/instance-types", response_model=InstanceTypesResponse)
async def get_instance_types(
    cloud: str = Query(..., description="Cloud provider (AWS, AZURE, GCP)"),
    region: Optional[str] = Query(None, description="Cloud region"),
    min_vcpu: Optional[int] = Query(None, ge=0, description="Minimum vCPU"),
    max_vcpu: Optional[int] = Query(None, ge=0, description="Maximum vCPU"),
    min_memory_gb: Optional[float] = Query(None, ge=0, description="Minimum memory (GB)"),
    max_memory_gb: Optional[float] = Query(None, ge=0, description="Maximum memory (GB)"),
    sort_by: str = Query("instance_type", description="Sort field"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get available instance types with specifications and pricing"""
    
    # Validate cloud
    if cloud.upper() not in ["AWS", "AZURE", "GCP"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_CLOUD",
                "message": "Invalid cloud provider",
                "field": "cloud",
                "allowed_values": ["AWS", "AZURE", "GCP"]
            }
        )
    
    try:
        conn = get_db_connection()
        service = InstanceTypesService(conn)
        
        data = service.get_instance_types(
            cloud=cloud.upper(),
            region=region,
            min_vcpu=min_vcpu,
            max_vcpu=max_vcpu,
            min_memory_gb=min_memory_gb,
            max_memory_gb=max_memory_gb,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )
        
        return {
            "success": True,
            "data": data,
            "metadata": {
                "query_time_ms": 45,  # Add actual timing
                "cache_hit": False
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "QUERY_ERROR",
                "message": str(e)
            }
        )
    finally:
        conn.close()
```

---

## 8. Caching Strategy

### 8.1 Cache Key Design

```python
cache_key = f"instance_types:{cloud}:{region}:{min_vcpu}:{max_vcpu}:{sort_by}:{limit}"
```

### 8.2 Cache Implementation (Redis)

```python
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_instance_types(ttl_seconds=3600):  # 1 hour TTL
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from parameters
            cache_key = f"instance_types:{kwargs.get('cloud')}:{kwargs.get('region')}:{kwargs.get('sort_by')}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute query
            result = func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator
```

---

## 9. Implementation Checklist

### Phase 1: Database Preparation
- [ ] Create instance metadata CSV files (AWS, Azure, GCP)
- [ ] Alter `sync_ref_instance_dbu_rates` table to add metadata columns
- [ ] Import CSV data into table
- [ ] Verify data quality (check for NULL values, validate specs)

### Phase 2: API Implementation
- [ ] Create `services/instance_types.py`
- [ ] Create `routes/instance_types.py`
- [ ] Implement SQL queries (with/without region)
- [ ] Add request validation (Pydantic models)
- [ ] Add error handling

### Phase 3: Testing
- [ ] Test with AWS, us-east-1, no filters
- [ ] Test with AZURE, no region (aggregated pricing)
- [ ] Test with min/max vCPU filters
- [ ] Test with invalid cloud (error case)
- [ ] Test with non-existent region (error case)

### Phase 4: Optimization
- [ ] Add Redis caching
- [ ] Add query performance monitoring
- [ ] Add database connection pooling

---

## 10. Open Questions

1. **Instance Type Coverage:**
   - Should we include ALL instance types or just common ones?
   - Top 20 most used? Or comprehensive list?

2. **Pricing Availability:**
   - What if pricing data is missing for some payment options?
   - Should we show "N/A" or hide the instance?

3. **Workload Type Filtering:**
   - You mentioned `workload_type` parameter - how does this filter instances?
   - Are certain instance types incompatible with certain workloads?

4. **Region Availability:**
   - Should we indicate if an instance is NOT available in a selected region?
   - Or only return instances that ARE available?

---

## 11. Next Steps

1. **Create Instance Metadata CSV**
   - Focus on AWS first (top 20 instance types)
   - Get vCPU, memory, storage specs from AWS docs

2. **Test SQL Query**
   - Run query against current database
   - Verify joins work correctly

3. **Implement API Endpoint**
   - Start with basic version (no caching)
   - Test with Postman/curl

---

**Status:** 📋 Detailed Plan Complete - Ready for CSV Creation & Implementation

**Next Action:** Create instance metadata CSV for AWS, then implement endpoint


