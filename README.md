# Lakemeter - Databricks Pricing Calculator

A full-stack application for creating, managing, and exporting Databricks pricing estimates. Built with React + Tailwind CSS frontend and FastAPI backend, connected to a Databricks Lakebase database with OAuth authentication.

## Features

### Authentication & Security
- **Databricks Apps SSO**: Automatic user authentication via Databricks Apps headers
- **User-scoped Estimates**: Users can only see estimates they own or have been shared with
- **OAuth Token Management**: Automatic token refresh for Lakebase database connections

### Workload Types (from Lakebase)
The workload types are dynamically loaded from the `lakemeter.ref_workload_types` table:

| Workload Type | Display Name | SKU (Standard) | SKU (Photon) | SKU (Serverless) |
|---------------|--------------|----------------|--------------|------------------|
| JOBS | Jobs Compute | JOBS_COMPUTE | JOBS_COMPUTE_(PHOTON) | JOBS_SERVERLESS_COMPUTE |
| ALL_PURPOSE | All-Purpose Compute | ALL_PURPOSE_COMPUTE | ALL_PURPOSE_COMPUTE_(PHOTON) | INTERACTIVE_SERVERLESS_COMPUTE |
| DLT | Delta Live Tables | DLT_CORE_COMPUTE | DLT_CORE_COMPUTE_(PHOTON) | DELTA_LIVE_TABLES_SERVERLESS |
| DBSQL | Databricks SQL | SQL_COMPUTE | SQL_PRO_COMPUTE | SERVERLESS_SQL_COMPUTE |
| VECTOR_SEARCH | Vector Search | - | - | VECTOR_SEARCH_ENDPOINT |
| MODEL_SERVING | Model Serving | - | - | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_DATABRICKS | Foundation Models (Databricks) | - | - | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_PROPRIETARY | Foundation Models (Proprietary) | - | - | Various (Anthropic, OpenAI, Google) |
| LAKEBASE | Lakebase | - | - | DATABASE_SERVERLESS_COMPUTE |

### Compute Configuration
- **Driver/Worker Node Selection**: Choose from available instance types per cloud
- **Pricing Tiers**: On-Demand, 1-Year Reserved, 3-Year Reserved
- **Worker Pricing**: Spot Instances, On-Demand, Reserved options
- **Payment Options**: No Upfront, Partial Upfront, All Upfront (AWS)

### Serverless & Photon
- **Serverless Toggle**: Switch between classic and serverless compute
- **Photon Acceleration**: Enable/disable Photon for compatible workloads
- **Performance Mode**: Standard or Performance modes for serverless

### Foundation Models (Databricks)
- **LLMs**: Llama 4 Maverick, Llama 3.3 70B, GPT OSS 120B, Gemma 3 12B, etc.
- **Embedding Models**: GTE, BGE Large
- **Rate Types**: Input Token, Output Token
- **Quantity**: Tokens per million/month

### Foundation Models (Proprietary)
- **Providers**: Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- **Endpoint Types**: Global, In-Geo (Regional)
- **Context Lengths**: All, Short, Long
- **Rate Types**: Input Token, Output Token, Cache Read, Cache Write
- **Quantity**: Tokens per million/month

### Model Serving
- **CPU Endpoints**: 1 DBU/hr per concurrent request
- **GPU Options**: T4, A10G, A100 variants with different DBU rates
- **Cloud-specific**: Different GPU options per cloud provider

### Vector Search
- **Standard**: 4 DBU/hr per 2M vectors
- **Storage Optimized**: 18.29 DBU/hr per 64M vectors

### Export & Management
- **Export to Excel**: Download estimates with detailed worksheets
- **Estimate Management**: Create, duplicate, and delete estimates
- **Version Tracking**: Automatic versioning of estimates

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React + Vite   │────▶│    FastAPI      │────▶│   Lakebase      │
│  Tailwind CSS   │     │    Python       │     │   PostgreSQL    │
│  Zustand        │     │  OAuth/SSO      │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     Frontend               Backend                Database
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Databricks CLI (authenticated)
- Access to Lakebase database

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
LAKEBASE_INSTANCE=lakemeter-db
LAKEBASE_SECRETS_SCOPE=lakemeter-secrets
LOCAL_DEV_EMAIL=your.email@databricks.com  # For local development
EOF

# Run server
LOCAL_DEV_EMAIL="your.email@databricks.com" uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

## Database Schema

### Estimates Table: `lakemeter.estimates`

```sql
CREATE TABLE lakemeter.estimates (
    estimate_id UUID PRIMARY KEY,
    estimate_name VARCHAR(255) NOT NULL,
    owner_user_id UUID,
    customer_name VARCHAR(255),
    cloud VARCHAR(50),
    region VARCHAR(100),
    tier VARCHAR(50),
    status VARCHAR(50) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    template_id UUID,
    original_prompt TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by UUID
);
```

### Line Items Table: `lakemeter.line_items`

```sql
CREATE TABLE lakemeter.line_items (
    line_item_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
    display_order INTEGER DEFAULT 0,
    workload_name VARCHAR(255) NOT NULL,
    workload_type VARCHAR(50),
    cloud VARCHAR(50),
    
    -- Serverless Configuration
    serverless_enabled BOOLEAN DEFAULT FALSE,
    serverless_mode VARCHAR(20),
    
    -- Compute Configuration
    photon_enabled BOOLEAN DEFAULT FALSE,
    driver_node_type VARCHAR(100),
    worker_node_type VARCHAR(100),
    num_workers INTEGER DEFAULT 1,
    
    -- DLT Configuration
    dlt_edition VARCHAR(20),
    
    -- DBSQL Configuration
    dbsql_warehouse_type VARCHAR(20),
    dbsql_warehouse_size VARCHAR(20),
    dbsql_num_clusters INTEGER DEFAULT 1,
    dbsql_vm_pricing_tier VARCHAR(20),
    dbsql_vm_payment_option VARCHAR(20),
    
    -- Vector Search Configuration
    vector_search_mode VARCHAR(20),
    vector_capacity_millions INTEGER,
    
    -- Model Serving Configuration
    model_serving_gpu_type VARCHAR(50),
    
    -- Foundation Model API Configuration
    fmapi_provider VARCHAR(50),
    fmapi_model VARCHAR(100),
    fmapi_endpoint_type VARCHAR(20),
    fmapi_context_length VARCHAR(20),
    fmapi_rate_type VARCHAR(20),      -- input_token, output_token, cache_read, cache_write
    fmapi_quantity NUMERIC(18,2),      -- quantity in millions
    
    -- Lakebase Configuration
    lakebase_cu INTEGER,
    lakebase_storage_gb INTEGER,
    lakebase_ha_nodes INTEGER,
    lakebase_backup_retention_days INTEGER,
    
    -- Usage Configuration
    runs_per_day INTEGER,
    avg_runtime_minutes INTEGER,
    days_per_month INTEGER DEFAULT 22,
    hours_per_month INTEGER,
    
    -- Pricing Configuration
    driver_pricing_tier VARCHAR(20),
    worker_pricing_tier VARCHAR(20),
    driver_payment_option VARCHAR(20),
    worker_payment_option VARCHAR(20),
    
    -- Additional
    workload_config JSONB,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### Authentication
- `GET /api/v1/estimates/me/info` - Get current user info

### Workload Types
- `GET /api/v1/workload-types/` - List all workload types from database

### Estimates
- `GET /api/v1/estimates/` - List estimates (filtered by user ownership/sharing)
- `POST /api/v1/estimates/` - Create estimate
- `GET /api/v1/estimates/{id}` - Get estimate
- `PUT /api/v1/estimates/{id}` - Update estimate
- `DELETE /api/v1/estimates/{id}` - Delete estimate
- `POST /api/v1/estimates/{id}/duplicate` - Duplicate estimate

### Line Items
- `GET /api/v1/line-items/estimate/{id}` - List line items
- `POST /api/v1/line-items/` - Create line item
- `PUT /api/v1/line-items/{id}` - Update line item
- `DELETE /api/v1/line-items/{id}` - Delete line item

### Export
- `GET /api/v1/export/estimate/{id}/excel` - Export to Excel

### Reference Data
- `GET /api/v1/reference/clouds` - Cloud providers and regions
- `GET /api/v1/reference/instance-types/{cloud}` - Instance types per cloud
- `GET /api/v1/reference/dbsql-sizes` - SQL Warehouse sizes
- `GET /api/v1/reference/dlt-editions` - DLT editions
- `GET /api/v1/reference/fmapi-databricks` - Databricks Foundation Models config
- `GET /api/v1/reference/fmapi-proprietary` - Proprietary Foundation Models config
- `GET /api/v1/reference/model-serving-gpu-types/{cloud}` - Model Serving GPU types

### VM Pricing
- `GET /api/v1/vm-pricing/` - Get VM pricing data
- `GET /api/v1/vm-pricing/tiers` - Pricing tier options
- `GET /api/v1/vm-pricing/payment-options` - Payment options

## Tech Stack

**Frontend**
- React 18 + TypeScript
- Tailwind CSS
- Vite
- Zustand (state management)
- Framer Motion (animations)
- React Hot Toast (notifications)
- Axios (HTTP client)

**Backend**
- FastAPI
- SQLAlchemy
- PostgreSQL (Lakebase)
- Databricks SDK (OAuth)
- XlsxWriter (Excel export)
- Pydantic (validation)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Databricks workspace URL |
| `LAKEBASE_INSTANCE` | Lakebase database instance name |
| `LAKEBASE_SECRETS_SCOPE` | Databricks secrets scope for SP credentials |
| `LOCAL_DEV_EMAIL` | Email for local development authentication |

## Deployment

The application is designed to be deployed on **Databricks Apps**:
- Frontend and backend can be deployed as separate apps
- SSO authentication is handled automatically via Databricks Apps headers
- OAuth tokens are managed via Databricks SDK

## License

MIT
