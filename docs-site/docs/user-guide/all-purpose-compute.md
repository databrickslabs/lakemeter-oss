---
sidebar_position: 8
---

# All-Purpose Compute

> **Lakemeter UI name:** All Purpose Compute

All-Purpose Compute is for interactive notebooks, development clusters, and ad-hoc analysis. Like Jobs, it supports **Classic** and **Serverless** modes -- but with key differences in pricing and how usage is measured.

![Estimate with configured workloads and cost summary](/img/estimate-with-workloads.png)
*Lakemeter showing workloads with live cost calculation — All-Purpose Compute appears alongside other workload types.*

## When to use All-Purpose

Use All-Purpose when you need an **always-on or frequently-used** interactive environment -- data scientists exploring data in notebooks, developers testing code, or analysts running ad-hoc queries. If your workload runs on a schedule and then stops, [Jobs](/user-guide/jobs-compute) is a better fit.

## Real-world example

> **Scenario:** Your data science team of 5 people shares a development cluster on AWS us-east-1 (Premium tier). The cluster runs during business hours -- about 8 hours a day, 22 business days a month. You want Photon enabled for faster DataFrame operations.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | All-Purpose |
| Serverless | Off |
| Driver Instance Type | m5d.xlarge |
| Worker Instance Type | m5d.xlarge |
| Number of Workers | 4 |
| Photon | On |
| Driver Pricing Tier | On-Demand |
| Worker Pricing Tier | On-Demand |
| Hours Per Month | 176 (= 8 hrs x 22 days) |

### Step-by-step calculation

**1. DBU rate per hour**

```
DBU/Hour = (Driver DBU + Worker DBU x Workers) x Photon Multiplier
         = (1.0 + 1.0 x 4) x 2.0
         = 10.0 DBU/hour
```

:::info Photon multiplier for All-Purpose
The Photon multiplier for All-Purpose Compute is **2.0x on all clouds** (AWS, Azure, and GCP). This is lower than the Jobs and DLT multiplier (2.9x AWS / 2.5x Azure, GCP). Lakemeter loads the correct multiplier automatically from the pricing bundle.
:::

**2. Monthly DBUs and cost**

```
Monthly DBUs = 10.0 x 176 = 1,760 DBUs
DBU Cost     = 1,760 x $0.55/DBU (example All-Purpose Photon rate) = $968.00
```

**3. VM cost**

```
VM Cost = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
        = ($0.192 + $0.192 x 4) x 176
        = $0.960/hr x 176
        = $168.96
```

**4. Total**

```
Total = $968.00 + $168.96 = $1,136.96/month
```

### What if you used Serverless instead?

All-Purpose Serverless always runs in **Performance mode** with a 4x total multiplier (2x Photon x 2x Performance):

```
DBU/Hour     = (1.0 + 1.0 x 4) x 2 x 2 = 20.0 DBU/hour
Monthly DBUs = 20.0 x 176 = 3,520 DBUs
DBU Cost     = 3,520 x $0.75/DBU (example Serverless rate) = $2,640.00
VM Cost      = $0 (no infrastructure costs)
Total        = $2,640.00/month
```

In this case, Classic is significantly cheaper for a cluster running 176 hours/month. Serverless shines for shorter, less predictable usage.

:::note
These are example rates for illustration. Actual prices depend on your cloud, region, and tier.
:::

## Configuration reference

### Compute mode

| Field | Description | Default |
|-------|-------------|---------|
| **Serverless** | Toggle between Classic and Serverless. Requires **Premium** tier or above. | Off |

:::caution
All-Purpose Serverless **always runs in Performance mode** -- there is no Standard option. This is a Databricks platform constraint, not a Lakemeter setting. The UI shows a fixed "Performance Mode" badge instead of a dropdown.
:::

### Classic mode fields

| Field | Description | Default |
|-------|-------------|---------|
| **Driver Instance Type** | VM size for the Spark driver | -- (select from list) |
| **Worker Instance Type** | VM size for the Spark executors | -- (select from list) |
| **Number of Workers** | Cluster size | 2 |
| **Photon** | Hardware-accelerated engine (2x DBU multiplier) | Off |
| **Driver Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | On-Demand |
| **Worker Pricing Tier** | Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved | Spot |

:::tip AWS Reserved Payment Options
When you select a Reserved tier on AWS, an additional **Payment Option** field appears with choices: No Upfront, Partial Upfront, or All Upfront. This field is not shown for Azure or GCP.
:::

### Usage fields

All-Purpose supports two input methods (toggle between them in the UI):

**Direct Hours (default for All-Purpose):**

| Field | Description | Default |
|-------|-------------|---------|
| **Hours Per Month** | Total cluster uptime hours | 0 |

Common values: 730 (24/7), 176 (8 hrs x 22 days), 44 (2 hrs x 22 days).

**Run-Based:**

| Field | Description | Default |
|-------|-------------|---------|
| **Runs Per Day** | Number of sessions per day | 1 |
| **Avg Runtime (minutes)** | Duration per session | 30 |
| **Days Per Month** | Active days | 22 |

## How costs are calculated

### Classic

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x Photon Multiplier
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
VM Cost     = (Driver $/hr + Worker $/hr x Workers) x Hours/Month
Total       = DBU Cost + VM Cost
```

### Serverless

```
DBU/Hour    = (Driver DBU Rate + Worker DBU Rate x Workers) x 2 x 2
DBU Cost    = DBU/Hour x Hours/Month x $/DBU
Total       = DBU Cost  (no VM costs)
```

The two `x 2` factors are:
- **Photon** (always on for Serverless) = 2x
- **Performance mode** (always on for All-Purpose Serverless) = 2x

Combined: **4x multiplier** on the base DBU rate.

### SKU mapping

| Configuration | SKU |
|--------------|-----|
| Classic, Photon off | `ALL_PURPOSE_COMPUTE` |
| Classic, Photon on | `ALL_PURPOSE_COMPUTE_(PHOTON)` |
| Serverless | `ALL_PURPOSE_SERVERLESS_COMPUTE` |

## Classic vs Serverless comparison

| Factor | Classic | Serverless |
|--------|---------|------------|
| DBU multiplier | 1x (or 2x with Photon) | 4x always |
| VM costs | Yes | No |
| $/DBU SKU | `ALL_PURPOSE_COMPUTE` | `ALL_PURPOSE_SERVERLESS_COMPUTE` |
| Cluster startup | Minutes | Seconds |
| Instance selection | You choose | Managed |
| Best for | Long-running, predictable usage | Short bursts, fast startup needed |

## Tips

- **Serverless is not always more expensive**: For short, infrequent sessions (e.g., 30 minutes a few times a week), Serverless often costs less because there are no VM costs and no time wasted on cluster startup.
- **For 24/7 clusters, Classic wins**: The 4x DBU multiplier on Serverless makes it expensive for always-on workloads. Use Classic with Reserved pricing for the best rate on long-running clusters.
- **Worker pricing tier**: Unlike Jobs, many teams use On-Demand for All-Purpose workers because interactive work is more sensitive to Spot interruptions. If your team can tolerate occasional restarts, Spot saves 60-70%.
- **Right-size the cluster**: Start with 2-4 workers and scale up if needed. Each additional worker adds to both DBU and VM costs linearly.

## Common mistakes

- **Leaving Hours Per Month at 0**: If you do not enter hours (or switch to run-based input and fill in those fields), the calculated cost will be $0. Make sure to set your expected usage.
- **Expecting a Standard mode option for Serverless**: All-Purpose Serverless only supports Performance mode. If you need lower Serverless costs for batch work, use [Jobs](/user-guide/jobs-compute) with Standard mode instead.
- **Comparing only DBU rates**: Serverless has a higher DBU rate but no VM costs. Always compare the **total monthly cost** between Classic and Serverless, not just the per-DBU price.

## Excel export

Each All-Purpose workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Hours/Month | Direct value or calculated from runs/runtime/days |
| DBU/Hour | Based on instance types, workers, and multipliers |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | Classic: driver + workers infrastructure; Serverless: $0 |
| Total Cost | DBU Cost + VM Cost |
