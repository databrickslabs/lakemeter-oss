---
sidebar_position: 3
---

# End-to-End Workflow

This guide covers the complete Lakemeter workflow from creating an estimate to interpreting the exported Excel report. Follow this when you need to produce a cost estimate for a customer proposal, internal planning exercise, or vendor comparison.

## Video walkthrough

<video controls width="100%" preload="metadata" aria-label="End-to-end workflow tutorial showing the complete Lakemeter process from estimate creation through export">
  <source src="/lakemeter-opensource/video/getting-started-tutorial.mp4" type="video/mp4" />
  Your browser does not support the video tag. <a href="/lakemeter-opensource/video/getting-started-tutorial.mp4">Download the tutorial video</a>.
</video>

*Full walkthrough: create an estimate, add workloads, configure compute and usage, review costs, and export the report.*

## Overview

```
Create Estimate → Add Workloads → Configure Each Workload → Review Costs → Export Excel → Interpret Report
```

![Lakemeter home page with estimates list](/img/home-page.png)
*Start from the Lakemeter home page — click **New Estimate** to begin building a cost estimate.*

## 1. Plan your estimate

Before opening Lakemeter, decide:

- **Cloud provider** -- AWS, Azure, or GCP. This determines available regions, instance types, and pricing.
- **Region** -- Where the Databricks workspace will run. Pricing varies by region.
- **Pricing tier** -- Standard, Premium, or Enterprise. This affects DBU rates and which workload types are available.

| Tier | Available Workloads | Typical Use |
|------|-------------------|-------------|
| **Standard** | Jobs, All-Purpose, DLT, DBSQL (Classic, Pro) | Basic data engineering |
| **Premium** | All Standard + DBSQL Serverless, Model Serving, Vector Search, FMAPI, Lakebase | Most production deployments |
| **Enterprise** | Same as Premium with enhanced SLAs | Large-scale, regulated workloads |

:::caution
Once you add workloads to an estimate, you cannot change its cloud provider. Choose carefully, or create separate estimates for multi-cloud comparisons.
:::

## 2. Create the estimate

1. Click **New Estimate** from the home page.
2. Enter a descriptive name (e.g., "Acme Corp - AWS us-east-1 Premium").
3. Select your cloud, region, and tier.
4. Click **Create**.

You are taken to the Calculator page.

## 3. Add and configure workloads

Click **Add Workload** for each Databricks service in your architecture. For each workload:

1. **Choose the workload type.** See the [Quick Reference](/user-guide/quick-reference) if you are unsure which type to use.
2. **Name it descriptively.** Use names like "Nightly ETL Pipeline" or "Analyst SQL Warehouse" -- not "Workload 1".
3. **Configure compute.** For classic workloads (Jobs, All-Purpose, DLT), select instance types and worker count. For serverless or managed services (DBSQL Serverless, Model Serving, Vector Search), choose the size or capacity tier.
4. **Set usage patterns.** Enter how much the workload runs:
   - Jobs: runs per day, average runtime in minutes, days per month
   - All-Purpose: hours per month
   - DBSQL: hours per month
   - Always-on services (Model Serving, Vector Search): default is 730 hrs/month (24/7)
   - FMAPI: token quantity in millions
5. **Choose pricing options.** For classic compute, pick between on-demand, spot, or reserved (1-year/3-year) pricing for driver and worker nodes.
6. **Add notes** (optional). Use the notes field to document why you chose a particular configuration -- useful when reviewing the estimate later or sharing with others.

Costs update in real-time as you adjust parameters.

:::tip
**Use the AI Assistant** to speed up configuration. Open the chat panel and describe your workload: "I need a DLT pipeline processing 500GB daily with Pro edition." The assistant proposes a workload configuration you can accept, modify, or reject.
:::

## 4. Review the cost breakdown

The Calculator page displays:

- **Per-workload costs** -- Monthly cost for each workload, broken down into DBU costs and VM infrastructure costs (where applicable).
- **Total estimate** -- Sum of all workloads displayed at the top.
- **DBU consumption** -- Total Databricks Units consumed per month by each workload.

**Understanding the cost components:**

| Component | Applies to | What it is |
|-----------|-----------|------------|
| **DBU cost** | All workloads | Databricks Units consumed x $/DBU rate. The rate depends on your cloud, region, tier, and workload type. |
| **VM cost** | Classic compute only (Jobs, All-Purpose, DLT, DBSQL Classic/Pro) | Cloud infrastructure cost for driver and worker VMs. Not applicable to serverless workloads. |
| **Token cost** | FMAPI workloads | Cost per million input/output tokens for foundation model API calls. |
| **Storage cost** | Lakebase, Vector Search | Storage capacity costs beyond the compute/DBU component. |

### Quick cost optimization checks

- **Spot pricing** on workers can reduce VM costs by 60-90% for fault-tolerant Jobs workloads.
- **Reserved instances** (1yr or 3yr) lower VM costs for always-on workloads like DBSQL warehouses.
- **Serverless** eliminates VM costs entirely -- the infrastructure cost is bundled into a higher DBU rate. Compare total cost, not just DBU rate.
- **Photon** doubles the DBU rate but often halves the runtime for compatible workloads. Check whether the faster execution offsets the higher per-hour cost.

## 5. Export to Excel

1. Click the **Export** button (download icon) at the top of the Calculator page.
2. The file downloads as `Databricks_Estimate_{name}_{date}.xlsx`.

You can also export all your estimates at once from the home page using the bulk export option.

## 6. Interpret the Excel report

The exported spreadsheet contains several sections:

### Header

The estimate name, cloud provider, region, pricing tier, status, version, and timestamps.

### Workload table

One row per workload with columns for:

| Column | Description |
|--------|-------------|
| Workload Name | The name you assigned |
| Type | Workload type (Jobs, DBSQL, etc.) |
| Config | Key configuration summary (instance types, warehouse size, etc.) |
| SKU | The specific Databricks SKU used for pricing |
| Driver / Workers | Instance types and worker count |
| Hours/Month | Total compute hours |
| Token Type / Qty | For FMAPI: input/output tokens in millions |
| DBU/hr | Databricks Units consumed per hour |
| Total DBUs/Month | DBU/hr x hours/month |
| $/DBU | Price per Databricks Unit |
| VM $/hr | Combined VM cost per hour (driver + workers) |
| Total Cost | Monthly cost for this workload |
| Notes | Configuration notes and any pricing warnings |

### Summary section

- **Total monthly cost** across all workloads
- **DBU breakdown** by SKU type (e.g., JOBS_COMPUTE, SERVERLESS_SQL_COMPUTE)
- **Assumptions** explaining the pricing basis and disclaimers

### How to use the report

| Use case | What to focus on |
|----------|-----------------|
| **Customer proposal / RFP** | Total cost, workload table, assumptions section |
| **Internal budget planning** | Total cost, DBU breakdown for chargeback allocation |
| **Vendor comparison** | Duplicate the estimate for each cloud/region, export both, compare total costs |
| **Architecture review** | Workload table configuration details, notes column |

## 7. Iterate and refine

Estimates are living documents. Common iteration patterns:

- **Duplicate** the estimate to create a "what-if" scenario (e.g., "What if we use serverless instead of classic?")
- **Adjust usage patterns** as you learn more about actual workload behavior
- **Add workloads** as the project scope grows
- **Change pricing options** to model the impact of reserved capacity commitments
- **Re-export** after changes to get an updated report

Each save increments the estimate's version number, so you can track how the estimate evolved over time.
