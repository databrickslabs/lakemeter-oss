---
sidebar_position: 4
---

# Quick Reference

A concise reference for all 14 workload types in Lakemeter. Use this page to quickly identify which workload type to use and what configuration options are available.

## Workload types at a glance

| Workload | What it is | When to use it | Min. Tier |
|----------|-----------|----------------|-----------|
| **Jobs** | Batch compute for ETL, ML training, data processing | Scheduled or triggered pipelines that run and terminate | Standard |
| **All-Purpose** | Interactive compute for notebooks and development | Ad-hoc analysis, prototyping, development clusters | Standard |
| **DLT** | Delta Live Tables declarative data pipelines | Managed ETL with built-in data quality and monitoring | Standard |
| **DBSQL** | SQL analytics warehouses | BI dashboards, SQL queries, analyst workloads | Standard (Classic/Pro), Premium (Serverless) |
| **Model Serving** | Real-time ML model inference endpoints | Deploying custom ML models for online predictions | Premium |
| **Vector Search** | Managed vector database | Similarity search, RAG applications, embeddings | Premium |
| **FMAPI (Databricks)** | Foundation Model API for open-source models | Llama, DBRX, Mixtral via Databricks-hosted endpoints | Premium |
| **FMAPI (Proprietary)** | Foundation Model API for third-party models | GPT-4, Claude, Gemini via Databricks gateway | Premium |
| **Lakebase** | Managed PostgreSQL-compatible database | Transactional workloads, application backends | Premium |
| **Databricks Apps** | Managed app hosting on Databricks | Hosting web applications, dashboards, internal tools | Premium |
| **AI Parse (Document AI)** | AI-powered document parsing and extraction | Processing PDFs, invoices, contracts with AI | Premium |
| **Shutterstock ImageAI** | AI image generation via Shutterstock | Generating images for marketing, content, prototyping | Premium |

## Key terms

| Term | Meaning |
|------|---------|
| **DBU** | Databricks Unit -- the billing unit for Databricks services. Different workload types have different $/DBU rates. |
| **SKU** | Stock Keeping Unit -- identifies the specific product being priced (e.g., `JOBS_COMPUTE`, `SERVERLESS_SQL_COMPUTE`). |
| **Photon** | Hardware-accelerated query engine. Doubles the DBU rate but often halves runtime for compatible workloads. |
| **Serverless** | Databricks-managed infrastructure. No VM configuration needed; infrastructure cost is included in the DBU price. |
| **Classic** | Customer-managed infrastructure. You choose instance types and pay DBU + VM costs separately. |

## Configuration by workload type

### Compute workloads (Jobs, All-Purpose, DLT)

These workloads share a common configuration pattern:

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle on for Databricks-managed compute, off for classic | Off |
| **Serverless Mode** | Standard or Performance (Performance uses 2x DBU rate) | Standard |
| **Photon** | Hardware-accelerated engine (classic mode only) | Off |
| **Driver Instance Type** | VM instance for the driver (classic only) | -- |
| **Worker Instance Type** | VM instance for workers (classic only) | -- |
| **Worker Count** | Number of worker nodes (classic only) | 2 |
| **Driver Pricing Tier** | On-Demand, 1-Year Reserved, 3-Year Reserved | On-Demand |
| **Worker Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, 3-Year Reserved | Spot Instances |
| **Payment Option** | No upfront, partial upfront, all upfront (reserved only) | No upfront |

**DLT-specific (classic mode only):**

| Field | Description | Options |
|-------|-------------|---------|
| **SDP Edition** | Feature tier for the pipeline (Core, Pro, Advanced). Hidden when Serverless is enabled. | Core, Pro, Advanced |

**Usage fields (Jobs):**

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Number of job executions daily | 1 |
| **Avg Runtime (minutes)** | Average duration of each run | 30 |
| **Days Per Month** | Active days per month | 22 |

**Usage fields (All-Purpose, DLT):**

| Field | Description | Default |
|-------|-------------|---------|
| **Hours Per Month** | Total compute hours | -- |

### DBSQL

| Field | Description | Options |
|-------|-------------|---------|
| **Serverless** | Checkbox to enable Serverless SQL (Premium+ only). When off, choose Pro or Classic. | On (Serverless) |
| **Size** | Determines DBU/hr consumption | Small (12 DBU/hr) |
| **Number of Clusters** | Concurrent cluster count for scaling | 1+ |
| **Hours Per Month** | Warehouse uptime | -- |

**DBSQL warehouse sizes and DBU rates:**

| Size | DBU/hr |
|------|--------|
| 2X-Small | 4 |
| X-Small | 6 |
| Small | 12 |
| Medium | 24 |
| Large | 40 |
| X-Large | 80 |
| 2X-Large | 144 |
| 3X-Large | 272 |
| 4X-Large | 528 |

### Model Serving

| Field | Description | Options |
|-------|-------------|---------|
| **Endpoint Type** | Compute tier for the endpoint | CPU, GPU Small (T4), GPU Medium (A10G 1x), GPU Large (A10G 4x), etc. |
| **Number of Endpoints** | Concurrent endpoint instances | 1+ |
| **Hours Per Month** | Endpoint uptime | Default: 730 (24/7) |

### Vector Search

| Field | Description | Options |
|-------|-------------|---------|
| **Vector Search Type** | Standard (4 DBU/hr per 2M vectors) or Storage Optimized (18.29 DBU/hr per 64M vectors) | Standard |
| **Capacity (M vectors)** | Number of vectors in millions | 1 |
| **Storage (GB)** | Additional storage capacity (20 GB free per endpoint unit, $0.023/GB/mo above) | 0 |
| **Hours Per Month** | Service uptime | Default: 730 (24/7) |

### FMAPI (Databricks models)

| Field | Description |
|-------|-------------|
| **Model** | Databricks-hosted model (e.g., Llama, DBRX, Mixtral) — LLMs and Embedding models |
| **Rate Type** | Token-based (input token, output token) or Provisioned (provisioned scaling, provisioned entry) |
| **Quantity** | For token-based: millions of tokens/month. For provisioned: hours/month (730 = 24/7) |

### FMAPI (Proprietary models)

| Field | Description |
|-------|-------------|
| **Provider** | OpenAI, Anthropic, or Google |
| **Model** | Specific model (GPT-4, Claude, Gemini, etc.) |
| **Endpoint Type** | Global or In-Geo |
| **Context Length** | All, Short, or Long (affects pricing for some models) |
| **Rate Type** | Input Token, Output Token, Cache Read, Cache Write, Batch Inference, Provisioned Scaling (availability depends on model) |
| **Quantity (millions)** | Token volume |

### Lakebase

| Field | Description | Default |
|-------|-------------|---------|
| **Capacity Units (CU)** | Compute units: 1, 2, 4, or 8 CU | 1 |
| **Number of Nodes** | 1 = primary only, 2-3 = primary + read replicas (HA) | 1 |
| **Storage (GB)** | Database storage capacity (0-8192 GB) | 0 |
| **Hours Per Month** | Instance uptime | Default: 730 (24/7) |

### Databricks Apps

| Field | Description | Default |
|-------|-------------|---------|
| **App Size** | Medium or Large | Medium |
| **Hours Per Month** | App uptime | Default: 730 (24/7) |

### AI Parse (Document AI)

| Field | Description | Default |
|-------|-------------|---------|
| **Mode** | Pages-based or direct DBU | Pages |
| **Complexity** | Low (text), Low (images), Medium, High — affects DBU rate per 1000 pages | Medium |
| **Pages (thousands)** | Number of pages to process in thousands | -- |

### Shutterstock ImageAI

| Field | Description | Default |
|-------|-------------|---------|
| **Images Per Month** | Number of images to generate | -- |

## Cost formula summary

| Workload type | Cost formula |
|--------------|-------------|
| **Classic compute** (Jobs, All-Purpose, DLT) | (DBU/hr x hours/month x $/DBU) + (VM $/hr x hours/month) |
| **Serverless compute** (Jobs, All-Purpose, DLT, DBSQL) | DBU/hr x hours/month x $/DBU (VM cost included) |
| **DBSQL Classic/Pro** | (Warehouse DBU/hr x clusters x hours/month x $/DBU) + VM costs |
| **Model Serving** | Endpoint DBU/hr x endpoints x hours/month x $/DBU |
| **Vector Search** | Endpoint units x DBU/unit x hours/month x $/DBU |
| **FMAPI** | Token quantity (M) x DBU per M tokens x $/DBU |
| **Lakebase** | (CU x nodes x hours/month x $/DBU) + storage costs |
| **Databricks Apps** | App DBU/hr x hours/month x $/DBU |
| **AI Parse** | Pages (thousands) x DBU per 1000 pages x $/DBU |
| **Shutterstock ImageAI** | Images x fixed cost per image |
