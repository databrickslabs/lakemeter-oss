---
sidebar_position: 4
---

# Which Workload Type Do I Need?

Lakemeter supports 14 workload types covering the full Databricks platform. This page helps you choose the right one for your use case.

![All workloads in a Lakemeter estimate](/img/all-workloads-overview.png)
*A Lakemeter estimate showing multiple workload types with their individual costs and configuration summaries.*

![Adding a workload — select type, configure parameters, and save](/img/gifs/adding-workload.gif)
*Animated: adding a new workload to an estimate — choose the workload type, configure compute and usage, then save.*

## Quick decision guide

| I need to... | Use this workload | Guide |
|-------------|-------------------|-------|
| Run scheduled ETL/data pipelines | **Jobs** | [Jobs Compute](/user-guide/jobs-compute) |
| Work interactively in notebooks | **All-Purpose Compute** | [All-Purpose Compute](/user-guide/all-purpose-compute) |
| Build declarative data pipelines with quality checks | **DLT** | [Delta Live Tables](/user-guide/dlt-pipelines) |
| Run SQL queries, dashboards, BI tools | **DBSQL** | [DBSQL Warehouses](/user-guide/dbsql-warehouses) |
| Deploy a custom ML model as an API | **Model Serving** | [Model Serving](/user-guide/model-serving) |
| Store and query vector embeddings (RAG) | **Vector Search** | [Vector Search](/user-guide/vector-search) |
| Call open-source LLMs (Llama, DBRX, Gemma) | **FMAPI Databricks** | [FMAPI — Databricks](/user-guide/fmapi-databricks) |
| Call commercial LLMs (Claude, GPT, Gemini) | **FMAPI Proprietary** | [FMAPI — Proprietary](/user-guide/fmapi-proprietary) |
| Use a managed PostgreSQL database | **Lakebase** | [Lakebase](/user-guide/lakebase) |
| Host a web app on Databricks | **Databricks Apps** | — |
| Parse documents with AI | **AI Parse (Document AI)** | — |
| Generate images with AI | **Shutterstock ImageAI** | — |

## Workload categories

### Compute Workloads

These workloads run Spark clusters or SQL warehouses. Costs are based on **instance types**, **cluster size**, and **hours of usage**.

| Workload | Pricing model | Supports Classic | Supports Serverless | VM costs |
|----------|--------------|:----------------:|:-------------------:|:--------:|
| **Jobs** | DBU/hr x hours | Yes | Yes | Classic only |
| **All-Purpose** | DBU/hr x hours | Yes | Yes | Classic only |
| **DLT** | DBU/hr x hours | Yes | Yes | Classic only |
| **DBSQL** | DBU/hr x hours | Yes (Classic/Pro) | Yes | Classic/Pro only |

### AI/ML & Data Services

These workloads are always serverless with no VM costs. Pricing is based on **GPU type**, **token volume**, or **provisioned capacity**.

| Workload | Pricing model | Unit | VM costs |
|----------|--------------|------|:--------:|
| **Model Serving** | DBU/hr by GPU type | Hours | Never |
| **Vector Search** | DBU/hr by endpoint units | Hours + storage | Never |
| **FMAPI Databricks** | DBU per million tokens or DBU/hr (provisioned) | Tokens or hours | Never |
| **FMAPI Proprietary** | DBU per million tokens | Tokens | Never |
| **Lakebase** | DBU/hr (compute) + DSU (storage) | Hours + GB | Never |
| **Databricks Apps** | DBU/hr by app size | Hours | Never |
| **AI Parse** | DBU per 1000 pages | Pages | Never |
| **Shutterstock ImageAI** | Fixed per image | Images | Never |

## Common fields

All workloads share these base fields:

| Field | Description |
|-------|-------------|
| **Workload Name** | A descriptive label (e.g., "ETL Pipeline", "Analytics Warehouse") |
| **Workload Type** | The Databricks service type from the dropdown |
| **Display Order** | Sort position in the estimate (drag to reorder) |

## Usage input modes

Compute workloads (**Jobs**, **All-Purpose**, **DLT**, **DBSQL**) support two ways to specify usage:

**Run-Based** (default): Specify runs per day, average runtime, and days per month. The formula is:
```
Hours/Month = (Runs Per Day x Avg Runtime Minutes / 60) x Days Per Month
```

**Direct Hours**: Enter total hours per month directly. Common values:
- 730 = 24/7 (always-on)
- 176 = 8 hours x 22 business days
- 44 = 2 hours x 22 business days

**Model Serving**, **Vector Search**, and **Lakebase** use direct hours only. **FMAPI** workloads use token volume (millions/month) or provisioned hours instead of either mode.

## Pricing tier restrictions

Some workloads require a **Premium** pricing tier or above:

| Workload | Standard tier | Premium tier |
|----------|:------------:|:------------:|
| Jobs (Classic) | Yes | Yes |
| Jobs (Serverless) | No | Yes |
| All-Purpose (Classic) | Yes | Yes |
| All-Purpose (Serverless) | No | Yes |
| DLT | Yes | Yes |
| DBSQL (Classic/Pro) | Yes | Yes |
| DBSQL (Serverless) | No | Yes |
| Model Serving | No | Yes |
| Vector Search | No | Yes |
| FMAPI Databricks | No | Yes |
| FMAPI Proprietary | No | Yes |
| Lakebase | No | Yes |
| Databricks Apps | No | Yes |
| AI Parse | No | Yes |
| Shutterstock ImageAI | No | Yes |

If you select Standard tier for your estimate, workloads that require Premium will not be available.

## Cost components

Depending on the workload type, your total cost may include one or more of:

- **DBU Cost** -- Databricks Units consumed, multiplied by the $/DBU rate for your SKU
- **VM Cost** -- Cloud infrastructure costs for driver and worker VMs (Classic compute only)
- **Storage Cost** -- Provisioned storage (Lakebase DSU, Vector Search overflow)
- **Token Cost** -- For FMAPI workloads, based on millions of tokens processed

The total monthly cost for each workload is displayed in the estimate summary. All workloads sum to the estimate total.
