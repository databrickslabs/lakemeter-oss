# Lakemeter API Layer - Design Plan

## 1. Overview

**Purpose:** Expose PostgreSQL cost calculation functions via REST API for consumption by AI agents and frontend applications.

**Backend:** PostgreSQL (Lakebase) with 14 workload-specific cost calculation functions + 1 main orchestrator function.

**Consumers:**
- Frontend web application (React/Next.js)
- AI agents (Claude, GPT, etc.)
- Internal tools and scripts

---

## 2. Technology Stack Options

### Option A: FastAPI (Python) ✅ **RECOMMENDED**
**Pros:**
- Fast, modern, async support
- Automatic OpenAPI/Swagger documentation
- Built-in request validation (Pydantic)
- Easy to deploy (Docker, Cloud Run, Databricks)
- Python ecosystem (psycopg2 already in use)
- Great for AI agent integration

**Cons:**
- Requires separate deployment (not native to Databricks)

### Option B: Databricks SQL Endpoints
**Pros:**
- Native Databricks integration
- No separate deployment needed
- SQL-based

**Cons:**
- Limited to SQL queries
- Less flexible for complex logic
- Not REST API (requires JDBC/ODBC drivers)

### Option C: Flask (Python)
**Pros:**
- Lightweight
- Simple to understand

**Cons:**
- Less modern than FastAPI
- Manual API documentation
- No built-in async support
- Manual request validation

**DECISION: FastAPI (Option A)**

---

## 3. API Endpoints Design

### 3.1 Core Endpoints

#### **POST /api/v1/calculate**
Calculate cost for a single line item using the orchestrator function.

**Request Body:**
```json
{
  "workload_type": "JOBS",
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "serverless_enabled": false,
  "photon_enabled": true,
  "driver_node_type": "i3.xlarge",
  "worker_node_type": "i3.2xlarge",
  "num_workers": 4,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30,
  "hours_per_month": null,
  // ... (35 total parameters)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dbu_per_hour": 2.5,
    "hours_per_month": 240,
    "dbu_per_month": 600,
    "dbu_price": 0.07,
    "dbu_cost_per_month": 42.00,
    "driver_vm_cost_per_hour": 0.312,
    "worker_vm_cost_per_hour": 0.624,
    "total_vm_cost_per_hour": 2.808,
    "driver_vm_cost_per_month": 74.88,
    "total_worker_vm_cost_per_month": 149.76,
    "vm_cost_per_month": 224.64,
    "cost_per_month": 266.64
  },
  "metadata": {
    "calculation_time_ms": 45,
    "function_used": "calculate_line_item_costs",
    "timestamp": "2025-01-20T10:30:00Z"
  }
}
```

---

#### **POST /api/v1/validate**
Validate input parameters before calculation (frontend validation helper).

**Request Body:**
```json
{
  "workload_type": "JOBS",
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "i3.xlarge",
  "worker_node_type": "i3.2xlarge",
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "serverless_enabled": false
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "warnings": [
    "Spot instances may have interruptions. Consider reserved for production workloads."
  ],
  "suggestions": [
    "Photon is recommended for this workload type (15-30% performance improvement)"
  ]
}
```

**Or (if invalid):**
```json
{
  "success": true,
  "valid": false,
  "errors": [
    {
      "field": "worker_pricing_tier",
      "message": "Azure does not support 'partial_upfront' payment option",
      "code": "INVALID_PAYMENT_OPTION"
    },
    {
      "field": "driver_pricing_tier",
      "message": "Driver node cannot use 'spot' pricing (must be on_demand or reserved)",
      "code": "INVALID_DRIVER_PRICING"
    }
  ]
}
```

---

#### **GET /api/v1/options/{workload_type}**
Get available dropdown options for a specific workload type (dynamic filtering).

**Example:** `GET /api/v1/options/JOBS?cloud=AWS&region=us-east-1&tier=PREMIUM`

**Response:**
```json
{
  "success": true,
  "data": {
    "instance_types": [
      {"value": "i3.xlarge", "label": "i3.xlarge (4 vCPU, 30.5 GB RAM)", "dbu_per_hour": 0.75},
      {"value": "i3.2xlarge", "label": "i3.2xlarge (8 vCPU, 61 GB RAM)", "dbu_per_hour": 1.5}
    ],
    "payment_options": [
      {"value": "on_demand", "label": "On-Demand"},
      {"value": "spot", "label": "Spot"},
      {"value": "reserved_1y_no_upfront", "label": "Reserved 1Y (No Upfront)"},
      {"value": "reserved_1y_partial_upfront", "label": "Reserved 1Y (Partial Upfront)"},
      {"value": "reserved_1y_all_upfront", "label": "Reserved 1Y (All Upfront)"},
      {"value": "reserved_3y_no_upfront", "label": "Reserved 3Y (No Upfront)"},
      {"value": "reserved_3y_partial_upfront", "label": "Reserved 3Y (Partial Upfront)"},
      {"value": "reserved_3y_all_upfront", "label": "Reserved 3Y (All Upfront)"}
    ],
    "serverless_available": true,
    "photon_available": true,
    "dlt_editions": null,
    "dbsql_warehouse_types": null
  }
}
```

---

#### **GET /api/v1/pricing/dbu**
Get DBU pricing for a specific cloud/region/tier/product_type.

**Example:** `GET /api/v1/pricing/dbu?cloud=AWS&region=us-east-1&tier=PREMIUM&product_type=JOBS_COMPUTE`

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "product_type": "JOBS_COMPUTE",
    "dbu_price": 0.07,
    "currency": "USD",
    "updated_at": "2025-01-15T00:00:00Z"
  }
}
```

---

#### **GET /api/v1/pricing/vm**
Get VM pricing for a specific instance type.

**Example:** `GET /api/v1/pricing/vm?cloud=AWS&region=us-east-1&instance_type=i3.xlarge&pricing_tier=on_demand&payment_option=NA`

**Response:**
```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "region": "us-east-1",
    "instance_type": "i3.xlarge",
    "pricing_tier": "on_demand",
    "payment_option": "NA",
    "price_per_hour": 0.312,
    "currency": "USD",
    "updated_at": "2025-01-15T00:00:00Z"
  }
}
```

---

#### **POST /api/v1/batch-calculate**
Calculate costs for multiple line items in a single request (for estimates with multiple workloads).

**Request Body:**
```json
{
  "line_items": [
    {
      "workload_type": "JOBS",
      "cloud": "AWS",
      // ... 35 parameters
    },
    {
      "workload_type": "DBSQL",
      "cloud": "AWS",
      // ... 35 parameters
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "line_items": [
      {
        "index": 0,
        "cost_per_month": 266.64,
        "dbu_cost_per_month": 42.00,
        "vm_cost_per_month": 224.64
      },
      {
        "index": 1,
        "cost_per_month": 150.00,
        "dbu_cost_per_month": 150.00,
        "vm_cost_per_month": 0
      }
    ],
    "totals": {
      "total_cost_per_month": 416.64,
      "total_dbu_cost_per_month": 192.00,
      "total_vm_cost_per_month": 224.64
    }
  },
  "metadata": {
    "calculation_time_ms": 120,
    "line_item_count": 2
  }
}
```

---

### 3.2 Health & Metadata Endpoints

#### **GET /health**
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "timestamp": "2025-01-20T10:30:00Z"
}
```

---

#### **GET /api/v1/workload-types**
List all available workload types.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "value": "JOBS",
      "label": "Jobs (Data Processing)",
      "description": "Scheduled or triggered data processing jobs",
      "supports_serverless": true,
      "supports_classic": true
    },
    {
      "value": "ALL_PURPOSE",
      "label": "All-Purpose Compute",
      "description": "Interactive notebooks and ad-hoc analysis",
      "supports_serverless": true,
      "supports_classic": true
    },
    // ... 12 more workload types
  ]
}
```

---

#### **GET /api/v1/clouds**
List all supported clouds.

**Response:**
```json
{
  "success": true,
  "data": [
    {"value": "AWS", "label": "Amazon Web Services", "regions": 20},
    {"value": "AZURE", "label": "Microsoft Azure", "regions": 18},
    {"value": "GCP", "label": "Google Cloud Platform", "regions": 15}
  ]
}
```

---

#### **GET /api/v1/regions**
List all regions for a cloud.

**Example:** `GET /api/v1/regions?cloud=AWS`

**Response:**
```json
{
  "success": true,
  "data": [
    {"value": "us-east-1", "label": "US East (N. Virginia)"},
    {"value": "us-west-2", "label": "US West (Oregon)"},
    {"value": "eu-west-1", "label": "Europe (Ireland)"},
    // ... more regions
  ]
}
```

---

## 4. Request Validation

### 4.1 Pydantic Models (Input Validation)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum

class WorkloadType(str, Enum):
    JOBS = "JOBS"
    ALL_PURPOSE = "ALL_PURPOSE"
    DLT = "DLT"
    DBSQL = "DBSQL"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    MODEL_SERVING = "MODEL_SERVING"
    FMAPI_DATABRICKS = "FMAPI_DATABRICKS"
    FMAPI_PROPRIETARY = "FMAPI_PROPRIETARY"
    LAKEBASE = "LAKEBASE"

class Cloud(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"

class Tier(str, Enum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

class CostCalculationRequest(BaseModel):
    # Core identifiers
    workload_type: WorkloadType
    cloud: Cloud
    region: str
    tier: Tier
    
    # Compute options
    serverless_enabled: bool = False
    photon_enabled: bool = False
    
    # Classic compute
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: int = Field(default=0, ge=0, le=1000)
    driver_pricing_tier: str = "on_demand"
    worker_pricing_tier: str = "on_demand"
    
    # Usage pattern
    runs_per_day: int = Field(default=1, ge=0, le=1000)
    avg_runtime_minutes: int = Field(default=60, ge=0, le=1440)
    days_per_month: int = Field(default=30, ge=1, le=31)
    hours_per_month: Optional[int] = Field(default=None, ge=0, le=744)
    
    # Serverless
    serverless_mode: Optional[str] = None
    
    # DBSQL
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    dbsql_num_clusters: int = Field(default=1, ge=1, le=100)
    dbsql_vm_pricing_tier: str = "on_demand"
    dbsql_vm_payment_option: str = "NA"
    
    # Vector Search
    vector_search_mode: Optional[str] = None
    vector_search_capacity_millions: float = Field(default=0, ge=0)
    
    # Model Serving
    model_serving_gpu_type: Optional[str] = None
    
    # FMAPI
    fmapi_model: Optional[str] = None
    fmapi_provider: Optional[str] = None
    fmapi_endpoint_type: str = "global"
    fmapi_context_length: str = "all"
    fmapi_rate_type: Optional[str] = None
    fmapi_quantity: int = Field(default=0, ge=0)
    
    # Lakebase
    lakebase_cu: int = Field(default=0, ge=0, le=8)
    lakebase_ha_nodes: int = Field(default=1, ge=1, le=3)
    
    # Payment options
    driver_payment_option: str = "NA"
    worker_payment_option: str = "NA"
    
    # DLT
    dlt_edition: Optional[str] = None
    
    @validator('hours_per_month')
    def validate_hours(cls, v, values):
        if v is not None and v > 744:
            raise ValueError('hours_per_month cannot exceed 744 (31 days × 24 hours)')
        return v
    
    @validator('driver_pricing_tier')
    def validate_driver_no_spot(cls, v):
        if v == 'spot':
            raise ValueError('Driver node cannot use spot pricing')
        return v
```

---

## 5. Error Handling

### 5.1 Standard Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "worker_pricing_tier",
        "message": "Azure does not support 'partial_upfront' payment option"
      }
    ]
  },
  "timestamp": "2025-01-20T10:30:00Z",
  "request_id": "req_abc123"
}
```

### 5.2 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INVALID_WORKLOAD_TYPE` | 400 | Unsupported workload type |
| `INVALID_CLOUD_REGION` | 400 | Cloud/region combination not supported |
| `PRICING_DATA_NOT_FOUND` | 404 | Pricing data not available for specified parameters |
| `DATABASE_ERROR` | 500 | Database connection or query error |
| `CALCULATION_ERROR` | 500 | Error during cost calculation |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

---

## 6. Authentication & Security

### Option A: No Authentication (Internal Use Only)
- API runs in private network
- Only accessible within Databricks workspace or VPC
- No external access

### Option B: API Key Authentication
- Simple API key in header: `X-API-Key: your-api-key`
- Key stored in environment variable
- Good for AI agents and internal tools

### Option C: OAuth 2.0 (Future)
- Full OAuth 2.0 with Databricks SSO
- User-level permissions
- For production public-facing API

**DECISION: Start with Option B (API Key), plan for Option C in future**

---

## 7. Deployment Options

### Option A: Databricks Serverless (Recommended for PoC)
- Run FastAPI in Databricks notebook/job
- Use Databricks serverless compute
- Easy access to Lakebase (same network)
- No separate infrastructure

**Pros:**
- Fastest to deploy
- No external infrastructure
- Close to database

**Cons:**
- Not optimized for REST API hosting
- Limited scalability
- Not standard practice

### Option B: Docker + Cloud Run / Cloud Functions
- Package FastAPI app in Docker
- Deploy to Google Cloud Run / AWS Lambda / Azure Functions
- Auto-scaling, managed service

**Pros:**
- Standard approach
- Auto-scaling
- Pay-per-request pricing

**Cons:**
- Network latency to Lakebase
- Need to manage secrets (DB credentials)

### Option C: Kubernetes (Overkill for now)
- Full Kubernetes deployment
- Maximum control and scalability

**Pros:**
- Production-grade
- Full control

**Cons:**
- Complex setup
- Overkill for initial version

**DECISION: Start with Option A (Databricks), migrate to Option B (Cloud Run) for production**

---

## 8. Project Structure

```
vpn/
├── api_backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Configuration (DB connection, secrets)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── request.py             # Pydantic request models
│   │   │   └── response.py            # Pydantic response models
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── calculate.py           # /calculate endpoint
│   │   │   ├── validate.py            # /validate endpoint
│   │   │   ├── options.py             # /options endpoint
│   │   │   └── pricing.py             # /pricing endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # DB connection & queries
│   │   │   ├── calculator.py          # Cost calculation logic
│   │   │   └── validator.py           # Input validation logic
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── error_handler.py       # Error handling utilities
│   ├── tests/
│   │   ├── test_calculate.py
│   │   ├── test_validate.py
│   │   └── test_options.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
└── database_backend/
    └── (existing Lakebase setup)
```

---

## 9. API Documentation

### Auto-Generated (OpenAPI/Swagger)
- FastAPI automatically generates:
  - OpenAPI 3.0 spec
  - Interactive Swagger UI at `/docs`
  - ReDoc at `/redoc`

### Example Swagger UI Features:
- Try out API calls directly in browser
- See request/response schemas
- View validation rules
- Copy cURL commands

---

## 10. Performance Considerations

### 10.1 Caching Strategy

**Level 1: Pricing Data Cache**
- Cache DBU prices, VM costs (change infrequently)
- TTL: 24 hours
- Reduces DB queries by ~70%

**Level 2: Options Cache**
- Cache dropdown options for cloud/region/workload combinations
- TTL: 1 hour
- Reduces DB queries by ~50%

**Level 3: Calculation Results Cache (Optional)**
- Cache calculation results for identical inputs
- TTL: 5 minutes
- Useful for repeated queries

### 10.2 Database Connection Pooling
- Use connection pool (min: 5, max: 20)
- Reuse connections across requests
- Automatic retry on connection failure

### 10.3 Async Execution
- FastAPI async support
- Parallel batch calculations
- Non-blocking DB queries

---

## 11. Monitoring & Logging

### 11.1 Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Include request_id for tracing

### 11.2 Metrics
- Request count
- Request duration (p50, p95, p99)
- Error rate
- Database query time
- Cache hit rate

### 11.3 Alerting
- Database connection failures
- High error rate (>5%)
- Slow response time (>2s p95)

---

## 12. Implementation Phases

### Phase 1: Core API (Week 1)
- [ ] FastAPI setup
- [ ] Database connection
- [ ] POST /api/v1/calculate endpoint
- [ ] Basic error handling
- [ ] Manual testing

### Phase 2: Validation & Options (Week 2)
- [ ] POST /api/v1/validate endpoint
- [ ] GET /api/v1/options/{workload_type}
- [ ] Input validation with Pydantic
- [ ] Dropdown options from DB

### Phase 3: Pricing Endpoints (Week 3)
- [ ] GET /api/v1/pricing/dbu
- [ ] GET /api/v1/pricing/vm
- [ ] Caching layer for pricing data

### Phase 4: Batch & Metadata (Week 4)
- [ ] POST /api/v1/batch-calculate
- [ ] GET /api/v1/workload-types
- [ ] GET /api/v1/clouds
- [ ] GET /api/v1/regions

### Phase 5: Production Ready (Week 5)
- [ ] API key authentication
- [ ] Rate limiting
- [ ] Comprehensive tests
- [ ] Docker deployment
- [ ] API documentation

---

## 13. Open Questions

1. **Authentication:** Do we need user-level auth or just API key?
2. **Rate Limiting:** Should we limit requests per user/key?
3. **Versioning:** Should we support multiple API versions (v1, v2)?
4. **Webhooks:** Do we need webhooks for async calculations?
5. **Batch Size:** What's the max line items for batch-calculate? (suggest: 100)
6. **CORS:** What domains should be allowed for frontend?
7. **Timeout:** What's acceptable timeout for calculate endpoint? (suggest: 10s)
8. **Deployment:** Databricks or Cloud Run for MVP?

---

## 14. Next Steps

1. **Review & Approve Plan**
   - [ ] User reviews API design
   - [ ] Confirm endpoint structure
   - [ ] Confirm deployment strategy

2. **Environment Setup**
   - [ ] Create api_backend/ folder structure
   - [ ] Set up FastAPI project
   - [ ] Install dependencies

3. **Start Phase 1 Implementation**
   - [ ] Implement POST /calculate
   - [ ] Test with 14 workload types
   - [ ] Validate against usage examples

---

**Status:** 📋 Planning Phase - Awaiting User Approval

**Next Action:** User to review plan and provide feedback/approvals


