---
sidebar_position: 11
---

# Databricks SQL Sizing

> **Lakemeter UI name:** Databricks SQL

Use this guide to model Databricks SQL warehouse consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not warehouse architecture, feature differences, performance tuning, or product limits.

For current Databricks SQL guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

A Databricks SQL workload includes:

- Databricks compute consumption for the selected warehouse type, size, cluster count, and monthly usage
- VM infrastructure cost for non-serverless warehouse types
- No separate VM infrastructure charge when **Serverless** is on

The estimate-level cloud, region, and Databricks tier determine which choices, mappings, and rates Lakemeter loads.

## Choose a warehouse configuration

### Serverless

Turn **Serverless** on when the estimate should use the serverless warehouse pricing context. Select:

- **Size**
- **Number of Clusters**
- Monthly usage

Lakemeter does not add a separate VM charge for this configuration.

### Non-serverless

Turn **Serverless** off, then select the **Type** offered by Lakemeter. Also select:

- **Size**
- **Number of Clusters**
- The driver and worker VM pricing assumptions shown by the form
- A payment option when Lakemeter displays one
- Monthly usage

For these configurations, Lakemeter displays the underlying driver and worker mapping loaded for the selected warehouse type and size. The user selects the VM purchasing assumptions; the form does not require manually choosing the mapped instance types or node counts.

Choose the warehouse type and size that match the scenario being estimated. Use observed warehouse settings, benchmark results, or current Databricks guidance rather than fixed sizing or concurrency advice from this guide.

## Size and cluster count

**Size** selects a warehouse capacity and its current DBU-per-hour value. Use the choices and values displayed by Lakemeter rather than copying a size-to-rate table from this guide.

**Number of Clusters** multiplies the selected size's DBU consumption:

```text
DBU per hour
  = Selected size DBU per hour × Number of clusters
```

Model the number of clusters expected to be billed during the entered usage window. If cluster count varies materially over time, use separate workload rows for the distinct usage periods or enter a documented representative assumption.

## Enter monthly usage

Lakemeter offers two usage input methods.

### Direct Hours

Enter **Hours/Month** when total monthly warehouse usage is known. Base this on observed active time, schedules, or another documented capacity plan.

### Run-Based

Enter:

- **Runs/Day**
- **Avg Runtime (min)**
- **Days/Month**

Lakemeter converts the entries to monthly usage hours:

```text
Hours per month
  = Runs per day
  × (Average runtime in minutes ÷ 60)
  × Days per month
```

Use run-based input only when a run and its average duration reasonably represent the warehouse's billed activity. Otherwise use Direct Hours.

## How the estimate is calculated

Lakemeter resolves the current size consumption value, selected SKU rate, warehouse VM mapping, and regional VM rates from the estimate context.

### DBU cost

```text
DBU per hour
  = Selected size DBU per hour × Number of clusters

Monthly DBUs
  = DBU per hour × Hours per month

DBU cost
  = Monthly DBUs × Regional price per DBU
```

The warehouse type determines the pricing context applied to the monthly DBUs. This guide intentionally does not reproduce current size mappings, SKU names, or rates. Open **Show Cost Calculation** for the workload to review the current values Lakemeter used.

### VM infrastructure cost

For a non-serverless warehouse:

```text
VM cost per cluster-hour
  = (Mapped driver count × Driver VM price per hour)
  + (Mapped worker count × Worker VM price per hour)

Monthly VM cost
  = VM cost per cluster-hour
  × Number of clusters
  × Hours per month

Total workload cost
  = DBU cost + Monthly VM cost
```

For a serverless warehouse:

```text
Total workload cost = DBU cost
```

## Symbolic sizing example

For warehouse size `S`, `C` clusters, and `H` monthly hours:

```text
Monthly DBUs = DBU per hour for S × C × H

DBU cost
  = Monthly DBUs × Regional price per DBU
```

For a non-serverless configuration, Lakemeter also multiplies the mapped per-cluster VM cost by `C × H`. The expanded calculation supplies the current size consumption, rate, and resulting totals.

## What to review before saving

- Does Serverless match the warehouse scenario?
- If Serverless is off, is the selected warehouse type intentional?
- Does **Size** match the warehouse being modeled?
- Does **Number of Clusters** represent the expected billed cluster count during the usage window?
- For a non-serverless configuration, do the displayed node mapping and VM purchasing assumptions look correct?
- Does the usage method represent actual warehouse activity?
- If capacity or cluster count changes over the month, should the periods be modeled separately?
- Does **Show Cost Calculation** use the expected hours, DBU per hour, VM treatment, and regional SKU price?

## Excel export

Each Databricks SQL workload is exported as one row. The row includes warehouse type, size, cluster count, selected SKU, monthly hours, DBU per hour, monthly DBUs, list and discounted DBU costs, VM cost when applicable, and total cost.

For non-serverless rows, the export also shows the mapped driver and worker configuration used for VM cost. The workbook keeps calculation cells as formulas so assumptions can be reviewed and adjusted. Serverless rows show no separate VM configuration or VM charge.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
