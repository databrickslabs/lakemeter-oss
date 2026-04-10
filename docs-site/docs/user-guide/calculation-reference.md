---
sidebar_position: 9
---

# Calculation Reference

This page documents the exact cost calculation formulas Lakemeter uses for each workload type, along with fully worked examples using real pricing data.

![Calculation Reference documentation page](/img/guides/calculation-reference-guide.png)
*The Calculation Reference — general cost pattern and formula structure for all 14 workload types.*

![Worked cost example](/img/guides/calculation-worked-example.png)
*Step-by-step worked example with real pricing data showing Jobs Classic with Photon.*

## General Pattern

All Databricks workload costs follow a common structure:

```
Monthly Cost = DBU Cost + VM Cost (Classic only)
DBU Cost     = Monthly DBUs × $/DBU
VM Cost      = (Driver $/hr + Worker $/hr × Workers) × Hours/Month
```

Serverless workloads have **no VM cost** — the infrastructure is included in the DBU price.

## Hours Calculation

How Lakemeter determines monthly hours depends on the workload's usage mode:

| Usage Mode | Formula | Default |
|-----------|---------|---------|
| **Run-based** (Jobs, DLT) | Runs/Day × Avg Runtime (min) ÷ 60 × Days/Month | 22 business days |
| **Continuous** (DBSQL, Model Serving, etc.) | Hours/Month entered directly | 730 hrs (24/7) |

---

## Worked Example 1: Jobs Classic with Photon

**Scenario:** An ETL pipeline running 5 times per business day, 45 minutes per run, using 4 `i3.xlarge` workers on AWS us-east-1 (Premium tier) with Photon enabled.

### Step 1: Calculate monthly hours

```
Hours/Month = (Runs/Day × Avg Runtime Minutes ÷ 60) × Days/Month
            = (5 × 45 ÷ 60) × 22
            = 3.75 × 22
            = 82.5 hours
```

### Step 2: Calculate DBU/Hour

The `i3.xlarge` instance has a DBU rate of **1.0 DBU/hr** per instance.

```
DBU/Hour = (Driver DBU + Worker DBU × Num Workers) × Photon Multiplier
         = (1.0 + 1.0 × 4) × 2.9
         = 5.0 × 2.9
         = 14.5 DBU/hr
```

The Photon multiplier varies by workload type and cloud. For Jobs on AWS it is **2.9** (All-Purpose uses 2.0). The multiplier is 1.0 when Photon is disabled.

### Step 3: Calculate monthly DBUs and DBU cost

The `JOBS_COMPUTE_(PHOTON)` SKU on AWS us-east-1 Premium costs **$0.15/DBU**.

```
Monthly DBUs = DBU/Hour × Hours/Month
             = 14.5 × 82.5
             = 1,196.25 DBUs

DBU Cost     = 1,196.25 × $0.15
             = $179.44/month
```

### Step 4: Calculate VM cost

The `i3.xlarge` on-demand rate is **$0.312/hr** per instance.

```
VM Cost = (Driver $/hr + Worker $/hr × Workers) × Hours/Month
        = ($0.312 + $0.312 × 4) × 82.5
        = $1.56 × 82.5
        = $128.70/month
```

### Step 5: Total cost

```
Monthly Cost = DBU Cost + VM Cost
             = $179.44 + $128.70
             = $308.14/month

Annual Cost  = $308.14 × 12 = $3,697.65/year
```

---

## Worked Example 2: DBSQL Serverless Warehouse

**Scenario:** A Medium Serverless SQL warehouse running 8 hours per business day (22 days/month) on AWS us-east-1 (Premium tier).

### Step 1: Calculate monthly hours

```
Hours/Month = 8 hours/day × 22 days
            = 176 hours
```

### Step 2: Look up DBU/Hour from size mapping

| Size | DBU/Hour |
|------|----------|
| 2X-Small | 4 |
| X-Small | 6 |
| Small | 12 |
| **Medium** | **24** |
| Large | 40 |
| X-Large | 80 |
| 2X-Large | 144 |
| 3X-Large | 272 |
| 4X-Large | 528 |

For a single cluster:

```
DBU/Hour = Size DBU × Number of Clusters
         = 24 × 1
         = 24 DBU/hr
```

### Step 3: Calculate cost

The `SERVERLESS_SQL_COMPUTE` SKU on AWS us-east-1 Premium costs **$0.70/DBU**.

```
Monthly DBUs = 24 × 176 = 4,224 DBUs
DBU Cost     = 4,224 × $0.70 = $2,956.80/month
VM Cost      = $0 (Serverless — no separate VM charges)

Monthly Cost = $2,956.80
Annual Cost  = $2,956.80 × 12 = $35,481.60/year
```

---

## Worked Example 3: FMAPI Token-Based Pricing

**Scenario:** Using Llama 3.1 8B on Databricks (AWS) with 50 million input tokens and 10 million output tokens per month.

### Step 1: Look up token rates

For Llama 3.1 8B on AWS:

| Rate Type | DBU per 1M Tokens |
|-----------|-------------------|
| Input tokens | 2.143 |
| Output tokens | 6.429 |

### Step 2: Calculate monthly DBUs for each rate type

```
Input DBUs  = 50M tokens × 2.143 DBU/1M = 107.15 DBUs
Output DBUs = 10M tokens × 6.429 DBU/1M =  64.29 DBUs
```

### Step 3: Calculate cost

The `SERVERLESS_REAL_TIME_INFERENCE` SKU on AWS us-east-1 Premium costs **$0.07/DBU**.

```
Input Cost   = 107.15 × $0.07 = $7.50/month
Output Cost  =  64.29 × $0.07 = $4.50/month

Monthly Cost = $7.50 + $4.50 = $12.00/month
Annual Cost  = $12.00 × 12 = $144.00/year
```

:::tip
Output tokens are typically more expensive than input tokens. For Llama 3.1 8B, output rates are 3x the input rate. Budget accordingly if your use case generates long responses.
:::

---

## Worked Example 4: Classic vs Serverless Comparison

**Scenario:** The same Jobs workload configured both ways — 4 `i3.xlarge` workers, 10 runs/day at 30 minutes each, on AWS us-east-1 Premium, Photon enabled.

### Common: Monthly hours

```
Hours/Month = (10 × 30 ÷ 60) × 22 = 110 hours
```

### Classic Calculation

The Photon multiplier for Jobs on AWS is **2.9**. The SKU is `JOBS_COMPUTE_(PHOTON)` at **$0.15/DBU**.

```
DBU/Hour     = (1.0 + 1.0 × 4) × 2.9 = 14.5 DBU/hr
Monthly DBUs = 14.5 × 110 = 1,595 DBUs
DBU Cost     = 1,595 × $0.15 = $239.25
VM Cost      = ($0.312 + $0.312 × 4) × 110 = $171.60
Monthly Cost = $239.25 + $171.60 = $410.85
```

### Serverless Calculation

Jobs Serverless always applies the Photon multiplier (2.9 on AWS) and a Serverless mode multiplier (1x Standard, 2x Performance). Using Standard mode. The SKU is `JOBS_SERVERLESS_COMPUTE` at **$0.35/DBU**.

```
DBU/Hour     = (1.0 + 1.0 × 4) × 2.9 × 1.0 = 14.5 DBU/hr
Monthly DBUs = 14.5 × 110 = 1,595 DBUs
DBU Cost     = 1,595 × $0.35 = $558.25
VM Cost      = $0 (Serverless — no separate VM charges)
Monthly Cost = $558.25
```

### Side-by-Side

| | Classic | Serverless (Standard) |
|--|---------|----------------------|
| DBU/Hour | 14.5 | 14.5 |
| Monthly DBUs | 1,595 | 1,595 |
| $/DBU | $0.15 | $0.35 |
| DBU Cost | $239.25 | $558.25 |
| VM Cost | $171.60 | $0.00 |
| **Monthly Total** | **$410.85** | **$558.25** |
| **Annual Total** | **$4,930.20** | **$6,699.00** |

:::note
In this scenario, Classic is cheaper because the VM costs ($171.60) are less than the DBU price premium for Serverless ($0.35 vs $0.15 per DBU). Serverless becomes more cost-effective for workloads with low utilization, burst patterns, or where you value the operational simplicity of not managing cluster infrastructure.
:::

---

## Formula Reference by Workload Type

### Jobs & All-Purpose (Classic)

```
DBU/Hour = (Driver DBU + Worker DBU × Workers) × Photon Multiplier
```

| Parameter | Value |
|-----------|-------|
| Photon Multiplier | Varies by workload and cloud: Jobs/DLT on AWS = 2.9, Azure/GCP = 2.5; All-Purpose = 2.0 on all clouds. 1.0 when Photon is disabled. Fallback = 2.0 if lookup fails. |
| Driver/Worker DBU | From instance type lookup (e.g., `i3.xlarge` = 1.0) |
| Fallback DBU | 0.5 for unknown instance types |

**SKUs:** `JOBS_COMPUTE`, `JOBS_COMPUTE_(PHOTON)`, `ALL_PURPOSE_COMPUTE`, `ALL_PURPOSE_COMPUTE_(PHOTON)`

### Jobs & All-Purpose (Serverless)

```
DBU/Hour = (Driver DBU + Worker DBU × Workers) × Photon × Serverless Multiplier
```

| Parameter | Jobs | All-Purpose |
|-----------|------|-------------|
| Photon | Always on (AWS: 2.9x, Azure/GCP: 2.5x) | Always on (2.0x) |
| Serverless Standard | 1x | N/A |
| Serverless Performance | 2x | Always 2x |

**SKUs:** `JOBS_SERVERLESS_COMPUTE`, `ALL_PURPOSE_SERVERLESS_COMPUTE`

No VM costs for serverless workloads.

### Delta Live Tables (DLT)

DLT Classic uses the same formula as Jobs Classic. DLT Serverless uses Jobs Serverless pricing.

| Edition | Classic SKU | Photon SKU | Serverless SKU |
|---------|------------|------------|----------------|
| Core | `DLT_CORE_COMPUTE` | `DLT_CORE_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Pro | `DLT_PRO_COMPUTE` | `DLT_PRO_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Advanced | `DLT_ADVANCED_COMPUTE` | `DLT_ADVANCED_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |

All DLT Serverless editions use the same `JOBS_SERVERLESS_COMPUTE` SKU.

### Databricks SQL (DBSQL)

```
DBU/Hour = Size DBU Map[Warehouse Size] × Number of Clusters
```

| Type | SKU |
|------|-----|
| Classic | `SQL_COMPUTE` |
| Pro | `SQL_PRO_COMPUTE` |
| Serverless | `SERVERLESS_SQL_COMPUTE` |

Classic and Pro include VM costs. Serverless does not.

### Model Serving

```
DBU/Hour = GPU DBU Rate (from lookup by GPU type)
```

Each GPU type maps to a fixed DBU/hour rate. All Model Serving uses the `SERVERLESS_REAL_TIME_INFERENCE` SKU. No VM costs.

### Vector Search

```
Units = CEILING(Capacity in Millions ÷ Divisor)
DBU/Hour = Units × Mode DBU Rate
```

| Mode | Divisor | DBU Rate per Unit |
|------|---------|-------------------|
| Standard | 2,000,000 vectors | 4.0 DBU/hr |
| Storage Optimized | 64,000,000 vectors | 18.29 DBU/hr |

**SKU:** `SERVERLESS_REAL_TIME_INFERENCE`

May produce a second storage row in exports when storage GB > 0.

### FMAPI — Databricks Models

| Pricing Type | Formula |
|-------------|---------|
| Token-based (input/output) | Monthly DBUs = Quantity (Millions) × DBU per 1M Tokens |
| Provisioned (entry/scaling) | Monthly DBUs = Hours × DBU per Hour |

**SKU:** `SERVERLESS_REAL_TIME_INFERENCE`

### FMAPI — Proprietary Models

Same token-based formula as Databricks FMAPI. Rate types include `input`, `output`, `cache_read`, and `cache_write`.

| Provider | SKU |
|----------|-----|
| Anthropic | `ANTHROPIC_MODEL_SERVING` |
| OpenAI | `OPENAI_MODEL_SERVING` |
| Google | `GEMINI_MODEL_SERVING` |

### Lakebase

**Compute:**
```
DBU/Hour = CU Size × Number of Nodes
```
- CU Size: 1, 2, 4, or 8 compute units per node
- Nodes: 1 (primary only), 2 (primary + 1 read replica), or 3 (primary + 2 read replicas)
- **SKU:** `DATABASE_SERVERLESS_COMPUTE`

**Storage:**
```
Storage Cost/Month = Storage GB × 15 DSU × $0.023/DSU
```
- Maximum storage: 8,192 GB
- **SKU:** `DATABRICKS_STORAGE`

Lakebase storage is a direct dollar cost (not DBU-based) and appears on a separate row in Excel exports.

### Databricks Apps

```
DBU/Hour = App Size DBU Rate
```

| App Size | DBU/Hour |
|----------|----------|
| Medium | Uses `ALL_PURPOSE_SERVERLESS_COMPUTE` rate |
| Large | Uses `ALL_PURPOSE_SERVERLESS_COMPUTE` rate (higher DBU) |

**SKU:** `ALL_PURPOSE_SERVERLESS_COMPUTE`

No VM costs — Databricks Apps are always serverless.

### AI Parse (Document AI)

**Pages-based mode:**
```
Monthly DBUs = Pages (thousands) × DBU per 1000 Pages
```

The DBU rate per 1000 pages depends on the document complexity:

| Complexity | Description |
|------------|-------------|
| Low (Text) | Simple text documents |
| Low (Images) | Documents with images but simple layout |
| Medium | Mixed content documents |
| High | Complex documents with tables, forms, multi-column layouts |

**SKU:** `SERVERLESS_REAL_TIME_INFERENCE`

### Shutterstock ImageAI

```
Monthly Cost = Images Per Month × Cost Per Image
```

Shutterstock ImageAI uses a fixed per-image cost rather than DBU-based pricing. The cost per image is retrieved from the pricing bundle.

No DBU calculation — this is a direct dollar cost.

---

## Excel Export Column Layout

The Excel export uses a 30-column layout. See the [Exporting guide](./exporting) for full details on sections and formatting.
