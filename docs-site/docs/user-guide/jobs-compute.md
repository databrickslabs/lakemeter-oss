---
sidebar_position: 7
---

# Jobs Compute

> **Lakemeter UI name:** Lakeflow Jobs

Jobs is the workload type for batch processing, ETL workflows, and scheduled data pipelines. It supports both **Classic** (you manage the cluster) and **Serverless** (Databricks manages everything) modes.

![Calculator page showing workloads with cost breakdown](/img/calculator-overview.png)
*The Calculator page with configured workloads — Jobs workloads appear in the list with their individual cost displayed.*

## When to use Jobs

Use Jobs when you have workloads that **start, run, and stop** on a schedule or trigger -- things like nightly data ingestion, hourly aggregation pipelines, or ML training runs. If you need an always-on interactive environment instead, see [All-Purpose Compute](/user-guide/all-purpose-compute).

## Real-world example

> **Scenario:** You are estimating cost for a nightly ETL pipeline on AWS us-east-1 (Premium tier). The pipeline runs twice a day, takes about 45 minutes per run, and uses a 4-worker cluster with Photon enabled for faster Spark processing. It runs every day of the month including weekends.

Here is how to configure this in Lakemeter and what the numbers mean.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Jobs |
| Serverless | Off |
| Driver Instance Type | m5d.xlarge |
| Worker Instance Type | m5d.xlarge |
| Number of Workers | 4 |
| Photon | On |
| Driver Pricing Tier | On-Demand |
| Worker Pricing Tier | Spot |
| Runs Per Day | 2 |
| Avg Runtime (minutes) | 45 |
| Days Per Month | 30 |

### Step-by-step calculation

**1. Compute hours per month**

```
Hours/Month = (Runs Per Day x Avg Runtime / 60) x Days Per Month
            = (2 x 45 / 60) x 30
            = 1.5 x 30
            = 45 hours/month
```

**2. DBU rate per hour**

Each m5d.xlarge has a DBU rate of approximately 1.0 DBU/hr. With 1 driver + 4 workers and Photon enabled:

```
DBU/Hour = (Driver DBU + Worker DBU x Workers) x Photon Multiplier
         = (1.0 + 1.0 x 4) x 2.9
         = 5.0 x 2.9
         = 14.5 DBU/hour
```

:::info Photon multiplier varies by cloud
The Photon multiplier for Jobs is **2.9x on AWS** and **2.5x on Azure/GCP**. This example uses the AWS rate. Lakemeter loads the correct multiplier automatically from the pricing bundle based on your cloud selection.
:::

**3. Monthly DBUs and cost**

```
Monthly DBUs = DBU/Hour x Hours/Month = 14.5 x 45 = 652.5 DBUs
DBU Cost     = 652.5 x $0.15/DBU (example Jobs Photon rate) = $97.88
```

**4. VM infrastructure cost**

Classic workloads also have VM costs for the driver and worker instances:

```
VM Cost = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
        = ($0.192 on-demand + $0.069 spot x 4) x 45
        = $0.468/hr x 45
        = $21.06
```

**5. Total monthly cost**

```
Total = DBU Cost + VM Cost = $97.88 + $21.06 = $118.94/month
```

:::note
These are example rates for illustration. Actual $/DBU and VM prices depend on your cloud, region, and pricing tier. Lakemeter loads real rates from the Databricks pricing bundle.
:::

## Configuration reference

### Compute mode

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle between Classic (off) and Serverless (on). Serverless requires **Premium** tier or above. | Off |
| **Serverless Mode** | Standard (1x) or Performance (2x multiplier). Only shown for Jobs and DLT when Serverless is on. | Standard |

### Classic mode fields

These fields appear when Serverless is **off**:

| Field | Description | Default |
|-------|-------------|---------|
| **Driver Instance Type** | VM size for the Spark driver node | -- (select from list) |
| **Worker Instance Type** | VM size for the Spark executor nodes | -- (select from list) |
| **Number of Workers** | How many worker nodes in the cluster | 2 |
| **Photon** | Enables the hardware-accelerated Spark engine. Increases the DBU rate (2.9x on AWS, 2.5x on Azure/GCP) but often halves runtime for compatible workloads. | Off |
| **Driver Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | On-Demand |
| **Worker Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | Spot |

:::tip AWS Reserved Payment Options
When you select a **1-Year Reserved** or **3-Year Reserved** tier on AWS, an additional **Payment Option** field appears with choices: No Upfront, Partial Upfront, or All Upfront. This field is not shown for Azure or GCP.
:::

### Serverless mode fields

When Serverless is **on**, you still select driver and worker instance types -- these are used to **estimate DBU consumption** only. You do not pay VM costs for serverless workloads.

Photon is always enabled automatically when Serverless is on (shown with an "Auto" badge in the UI).

### Usage fields

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Number of job executions per day | 1 |
| **Avg Runtime (minutes)** | Average duration of each run | 30 |
| **Days Per Month** | How many days per month the job runs | 22 |
| **Hours Per Month** | Alternative: set total hours directly (use the toggle to switch between Run-Based and Direct Hours input) | 0 |

## How costs are calculated

### Classic

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier
Hours/Month = (Runs Per Day x Runtime / 60) x Days Per Month
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
VM Cost     = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
Total       = DBU Cost + VM Cost
```

- **Photon Multiplier** depends on your cloud: **2.9x** on AWS, **2.5x** on Azure/GCP. When Photon is off, the multiplier is 1.0.
- DBU rates come from the instance type (e.g., m5d.xlarge = ~1.0 DBU/hr)
- If an instance type is not found in the pricing data, Lakemeter uses a fallback of 0.5 DBU/hr

### Serverless

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier x Serverless Multiplier
Hours/Month = (Runs Per Day x Runtime / 60) x Days Per Month
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
Total       = DBU Cost  (no VM costs)
```

- Photon is always applied for Serverless. The multiplier is cloud-specific: **2.9x** on AWS, **2.5x** on Azure/GCP.
- **Serverless Multiplier**: 1.0 for Standard mode, 2.0 for Performance mode
- The $/DBU rate comes from the `JOBS_SERVERLESS_COMPUTE` SKU

### SKU mapping

| Configuration | SKU |
|--------------|-----|
| Classic, Photon off | `JOBS_COMPUTE` |
| Classic, Photon on | `JOBS_COMPUTE_(PHOTON)` |
| Serverless (any mode) | `JOBS_SERVERLESS_COMPUTE` |

## Tips

- **Classic vs Serverless**: Classic gives you control over instance types and is usually cheaper for long-running, predictable workloads. Serverless eliminates startup time and management overhead -- good for short, frequent jobs or when you want zero infrastructure management.
- **Photon**: Enable Photon for data-heavy Spark workloads (aggregations, joins, ETL). It increases the DBU rate by 2.9x (AWS) or 2.5x (Azure/GCP), but often cuts runtime by 50% or more, resulting in similar or lower total cost. It has less impact on simple Python/ML workloads.
- **Spot pricing for workers**: The default worker tier is Spot, which is significantly cheaper than On-Demand. Spot is a good choice for batch jobs that can tolerate occasional interruptions. Use On-Demand for the driver to keep the job coordinator stable.
- **Days Per Month**: The default is 22 (business days). Change this to 30 or 31 for jobs that run on weekends too.

## Common mistakes

- **Using only 1 worker**: With 1 worker, parallelism is limited. Most production workloads benefit from at least 2-4 workers. The minimum in Lakemeter is 1.
- **Forgetting Photon increases DBUs**: If your cost estimate is nearly 3x what you expected (on AWS), check whether Photon is enabled. The higher DBU rate (2.9x on AWS) is intentional -- compare total cost (including shorter runtime) rather than just the DBU rate.
- **Serverless with Performance mode for simple ETL**: Performance mode (2x multiplier) is for latency-sensitive workloads. Standard mode is usually sufficient and cheaper for batch ETL.
- **Comparing Classic and Serverless by DBU rate alone**: Serverless has higher $/DBU but zero VM costs and zero startup time. Compare total monthly cost, not just the DBU price.

## Excel export

Each Jobs workload appears as one row in the exported spreadsheet with these key columns:

| Column | What it shows |
|--------|--------------|
| Hours/Month | Calculated from runs, runtime, and days |
| DBU/Hour | Based on instance types, workers, and multipliers |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost (List) | At list price before any discounts |
| DBU Cost (Discounted) | At your negotiated rate (if applicable) |
| VM Cost | Driver + worker infrastructure (Classic only; $0 for Serverless) |
| Total Cost | DBU Cost + VM Cost |
