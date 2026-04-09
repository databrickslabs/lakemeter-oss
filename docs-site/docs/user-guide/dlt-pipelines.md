---
sidebar_position: 10
---

# Delta Live Tables (DLT)

> **Lakemeter UI name:** Lakeflow Spark Declarative Pipelines (SDP)

Delta Live Tables is Databricks' declarative ETL framework for building reliable, automated data pipelines. Lakemeter supports cost estimation for all three editions -- **Core**, **Pro**, and **Advanced** -- in both **Classic** and **Serverless** modes.

![Workload configuration in Lakemeter calculator](/img/workload-expanded-config.png)
*Expanding a workload reveals its full configuration — DLT pipelines show edition, cluster size, and Photon settings.*

## When to use DLT

Use DLT when you need **managed, declarative data pipelines** with built-in data quality checks, automatic dependency management, and pipeline monitoring. If you just need simple batch jobs without the DLT framework, [Jobs](/user-guide/jobs-compute) is simpler and often cheaper.

## Real-world example

> **Scenario:** You are building a real-time streaming pipeline on AWS us-east-1 (Premium tier) that ingests change data from a source database using CDC. The pipeline runs continuously, 24/7. You need the **Pro** edition for CDC support and want a 3-worker cluster with Photon.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | DLT |
| Serverless | Off |
| SDP Edition | Pro |
| Driver Instance Type | m5d.xlarge |
| Worker Instance Type | m5d.xlarge |
| Number of Workers | 3 |
| Photon | On |
| Driver Pricing Tier | On-Demand |
| Worker Pricing Tier | On-Demand |
| Hours Per Month | 730 (24/7) |

### Step-by-step calculation

**1. DBU rate per hour**

```
DBU/Hour = (Driver DBU + Worker DBU x Workers) x Photon Multiplier
         = (1.0 + 1.0 x 3) x 2.9
         = 4.0 x 2.9
         = 11.6 DBU/hour
```

:::info Photon multiplier varies by cloud
The Photon multiplier for DLT is **2.9x on AWS** and **2.5x on Azure/GCP**. This example uses the AWS rate. Lakemeter loads the correct multiplier automatically from the pricing bundle.
:::

**2. Monthly DBUs and cost**

```
Monthly DBUs = 11.6 x 730 = 8,468 DBUs
DBU Cost     = 8,468 x $0.25/DBU (example DLT Pro Photon rate) = $2,117.00
```

**3. VM cost**

```
VM Cost = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
        = ($0.192 + $0.192 x 3) x 730
        = $0.768/hr x 730
        = $560.64
```

**4. Total**

```
Total = $2,117.00 + $560.64 = $2,677.64/month
```

:::note
These are example rates for illustration. Actual $/DBU and VM prices depend on your cloud, region, and pricing tier. Lakemeter loads real rates from the Databricks pricing bundle.
:::

## Choosing an edition

| Feature | Core | Pro | Advanced |
|---------|:----:|:---:|:--------:|
| Change Data Capture (CDC) | No | Yes | Yes |
| Advanced monitoring | Basic | Enhanced | Full |
| Data quality expectations | No | No | Yes |

All editions support pipeline orchestration, auto-scaling, Photon, and Serverless.

- **Core** -- Simple ETL without CDC. Lowest cost.
- **Pro** -- CDC and enhanced monitoring. Most common choice.
- **Advanced** -- Data quality expectations (assertions). Highest cost.

:::tip
The edition selector in the UI is labeled **"SDP Edition"** (Spark Declarative Pipelines). Core, Pro, and Advanced correspond to increasing levels of DLT features and pricing.
:::

## Configuration reference

### Compute mode

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle between Classic and Serverless. Requires **Premium** tier or above. | Off |
| **Serverless Mode** | Standard (1x) or Performance (2x). Only shown when Serverless is on. | Standard |

### Classic mode fields

| Field | Description | Default |
|-------|-------------|---------|
| **SDP Edition** | Core, Pro, or Advanced. Determines the DLT pricing tier. Hidden when Serverless is on. | Pro |
| **Driver Instance Type** | VM size for the driver | -- (select from list) |
| **Worker Instance Type** | VM size for the workers | -- (select from list) |
| **Number of Workers** | Cluster size | 2 |
| **Photon** | Hardware-accelerated engine (2.9x DBU multiplier on AWS, 2.5x on Azure/GCP) | Off |
| **Driver Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | On-Demand |
| **Worker Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | Spot |

:::tip AWS Reserved Payment Options
When you select a Reserved tier on AWS, an additional **Payment Option** field appears with choices: No Upfront, Partial Upfront, or All Upfront. This field is not shown for Azure or GCP.
:::

### Usage fields

DLT supports two input methods:

**Direct Hours (for continuous pipelines):**

| Field | Description | Default |
|-------|-------------|---------|
| **Hours Per Month** | Total pipeline uptime | 0 |

Common values: 730 (24/7 streaming), 176 (business hours), 44 (light usage).

**Run-Based (for scheduled pipelines):**

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Pipeline executions per day | 1 |
| **Avg Runtime (minutes)** | Duration per run | 30 |
| **Days Per Month** | Active days | 22 |

## How costs are calculated

### Classic

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
VM Cost     = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
Total       = DBU Cost + VM Cost
```

The $/DBU rate depends on edition and Photon. The Photon multiplier is cloud-specific: **2.9x** on AWS, **2.5x** on Azure/GCP.

### Serverless

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier x Serverless Multiplier
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
Total       = DBU Cost  (no VM costs)
```

- Photon is always applied for Serverless. The multiplier is cloud-specific: **2.9x** on AWS, **2.5x** on Azure/GCP.
- **Serverless Multiplier**: 1.0 for Standard, 2.0 for Performance

:::caution Important
DLT Serverless uses the **`JOBS_SERVERLESS_COMPUTE`** SKU regardless of which edition you selected in Classic mode. This means all DLT Serverless workloads are billed at the same $/DBU rate -- the edition distinction only affects Classic pricing.

When Serverless is enabled, the edition selector is hidden in the UI because the edition does not affect the Serverless price.
:::

### SKU mapping

| Edition | Classic SKU | Classic + Photon SKU | Serverless SKU |
|---------|------------|---------------------|----------------|
| Core | `DLT_CORE_COMPUTE` | `DLT_CORE_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Pro | `DLT_PRO_COMPUTE` | `DLT_PRO_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |
| Advanced | `DLT_ADVANCED_COMPUTE` | `DLT_ADVANCED_COMPUTE_(PHOTON)` | `JOBS_SERVERLESS_COMPUTE` |

## Tips

- **DLT Serverless pricing is edition-independent**: All editions use the same Serverless rate. Pick edition based on features, not cost, when using Serverless.
- **Classic edition pricing varies significantly**: Core is cheapest, Advanced most expensive. Stick with Core Classic if you don't need CDC or data quality expectations.
- **Photon for DLT is almost always worth it**: Photon's higher DBU rate (2.9x AWS, 2.5x Azure/GCP) is usually offset by faster execution and fewer total hours billed.
- **Continuous vs scheduled**: Use run-based scheduling for batch pipelines (e.g., 4 runs/day x 15 min). Reserve 730 hours for true streaming.

## Common mistakes

- **Choosing Advanced "just in case"**: Advanced costs significantly more in Classic mode. Only choose it if you need data quality expectations.
- **Assuming edition affects Serverless cost**: All DLT Serverless uses `JOBS_SERVERLESS_COMPUTE` pricing. Edition has no effect on Serverless cost.
- **Setting 730 hours for a batch pipeline**: If your pipeline runs 4x/day for 15 min each, that is 22 hrs/month, not 730. Use run-based input.
- **Forgetting the Photon multiplier**: Photon increases DBUs by 2.9x (AWS) or 2.5x (Azure/GCP). Compare total cost, not just DBU rate.

## Excel export

Each DLT workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Hours/Month | Direct value or calculated from runs/runtime/days |
| DBU/Hour | Based on instance types, workers, and multipliers |
| Monthly DBUs | DBU/Hour x Hours/Month |
| SKU | Edition-specific Classic SKU or `JOBS_SERVERLESS_COMPUTE` |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | Classic: driver + workers; Serverless: $0 |
| Total Cost | DBU Cost + VM Cost |
