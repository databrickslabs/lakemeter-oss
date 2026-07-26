---
sidebar_position: 7
---

# Lakeflow Jobs Sizing

> **Lakemeter UI name:** Lakeflow Jobs

Use this guide to model Lakeflow Jobs compute consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not general job architecture, performance tuning, or product limits.

For current Lakeflow Jobs guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

A Lakeflow Jobs workload includes:

- Databricks compute consumption for the selected driver, workers, compute mode, and monthly usage
- VM infrastructure cost when **Serverless** is off
- No separate VM infrastructure charge when **Serverless** is on

The estimate-level cloud, region, and Databricks tier determine which choices and rates Lakemeter loads.

## Choose a compute mode

### Serverless off

Use this mode to model a driver-and-worker configuration with separate Databricks and VM charges.

Enter:

- **Driver Node → Instance Type**
- **Worker Nodes → Instance Type**
- Worker **Count**
- **Photon**, if it is part of the scenario
- The driver and worker **Pricing Tier**
- A **Payment Option** when Lakemeter displays one

The driver count is one. The worker count multiplies both worker DBU consumption and worker VM cost.

Choose the instance types and purchasing assumptions that match the workload being estimated. Use observed configurations, benchmark results, or current Databricks guidance rather than copying a hardware recommendation from this guide.

### Serverless on

When **Serverless** is on:

- Choose the **Mode** offered by Lakemeter.
- Select driver and worker instance types and a worker count as sizing proxies for the DBU estimate.
- Lakemeter marks Photon as automatic.
- Driver and worker VM pricing fields are not used, and no separate VM cost is added.

The node selections in this form are estimator assumptions; they do not represent a separately billed serverless VM configuration.

## Enter monthly usage

Lakemeter offers two usage input methods.

### Run-Based

Enter:

- **Runs/Day**
- **Avg Runtime (min)**
- **Days/Month**

Lakemeter converts these assumptions to monthly compute hours:

```text
Hours per month
  = Runs per day
  × (Average runtime in minutes ÷ 60)
  × Days per month
```

Include the full billed runtime expected for each run. If startup, retries, or overlapping runs materially affect the scenario, incorporate them into the average or model them as separate workloads.

### Direct Hours

Enter **Hours/Month** when total monthly compute time is already known. This is useful when sizing from historical usage or when run frequency and duration are not the best representation of the workload.

## How the estimate is calculated

Lakemeter resolves the current DBU consumption values, multipliers, SKU rate, and VM rates from the selected estimate context.

### Base DBU consumption

```text
Base DBU per hour
  = Driver DBU per hour
  + (Worker DBU per hour × Number of workers)
```

Lakemeter then applies the current acceleration and mode adjustments associated with the configuration:

```text
Effective DBU per hour
  = Base DBU per hour
  × Applicable acceleration adjustment
  × Applicable serverless mode adjustment

Monthly DBUs
  = Effective DBU per hour × Hours per month

DBU cost
  = Monthly DBUs × Regional price per DBU
```

An adjustment equals one when it does not apply. This guide intentionally does not reproduce the current multiplier or rate values. Open **Show Cost Calculation** for the workload to review the values Lakemeter used.

### VM infrastructure cost

When Serverless is off:

```text
VM cost
  = (Driver VM price per hour
     + Worker VM price per hour × Number of workers)
  × Hours per month

Total workload cost
  = DBU cost + VM cost
```

When Serverless is on:

```text
Total workload cost = DBU cost
```

## Symbolic sizing example

For a scheduled workload with one driver, `W` workers, `R` runs per day, average runtime `M` minutes, and `D` active days:

```text
Hours per month = R × (M ÷ 60) × D

Monthly DBUs
  = (Driver DBU/hour + Worker DBU/hour × W)
  × Applicable adjustments
  × Hours per month
```

For a non-serverless configuration, Lakemeter also adds the driver and worker VM cost for those hours. The expanded calculation supplies the current DBU values, adjustments, and prices.

## What to review before saving

- Does Serverless match the scenario being estimated?
- Do the driver, worker, and worker-count assumptions describe the intended compute shape?
- If Serverless is off, do the VM purchasing assumptions match the scenario?
- If Serverless is on, is the selected mode intentional?
- Does Photon reflect the configuration, or show as automatic for Serverless?
- Does the usage method represent actual billed runtime?
- Are retries, overlapping runs, and seasonal schedules represented where material?
- Does **Show Cost Calculation** use the expected hours, DBU rate, VM treatment, and regional SKU price?

## Excel export

Each Lakeflow Jobs workload is exported as one row. The row includes the compute mode, configuration, selected SKU, monthly hours, DBU per hour, monthly DBUs, list and discounted DBU costs, VM cost when applicable, and total cost.

The workbook keeps calculation cells as formulas so assumptions can be reviewed and adjusted. Serverless rows show no separate VM configuration or VM charge.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
