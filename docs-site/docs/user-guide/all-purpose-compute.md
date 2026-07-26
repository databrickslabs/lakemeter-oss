---
sidebar_position: 8
---

# All-Purpose Compute Sizing

> **Lakemeter UI name:** All-Purpose Compute

Use this guide to model All-Purpose Compute consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not general compute architecture, performance tuning, or product limits.

For current All-Purpose Compute guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

An All-Purpose Compute workload includes:

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

Choose the instance types and purchasing assumptions from the environment being modeled. Use observed utilization, benchmarks, or current Databricks guidance rather than fixed hardware advice from this guide.

### Serverless on

When **Serverless** is on:

- Lakemeter displays **Performance Mode** for the estimate.
- Select driver and worker instance types and a worker count as sizing proxies for the DBU calculation.
- Lakemeter marks Photon as automatic.
- Driver and worker VM pricing fields are not used, and no separate VM cost is added.

The node selections in this form are estimator assumptions; they do not represent a separately billed serverless VM configuration.

## Enter monthly usage

Lakemeter offers two usage input methods.

### Direct Hours

Enter **Hours/Month** when total monthly compute uptime is known. Derive this assumption from observed active hours, schedules, or another documented capacity plan.

Do not automatically treat a full calendar month as active time. Enter only the hours represented by the scenario.

### Run-Based

Enter:

- **Runs/Day**
- **Avg Runtime (min)**
- **Days/Month**

Lakemeter converts the entries to monthly compute hours:

```text
Hours per month
  = Runs per day
  × (Average runtime in minutes ÷ 60)
  × Days per month
```

For interactive usage, a “run” can represent a modeled session or active window. If several users share the same compute concurrently, do not multiply the hours unless that activity creates separately billed compute time.

## How the estimate is calculated

Lakemeter resolves the current DBU consumption values, multipliers, SKU rate, and VM rates from the selected estimate context.

### Base DBU consumption

```text
Base DBU per hour
  = Driver DBU per hour
  + (Worker DBU per hour × Number of workers)
```

Lakemeter then applies the current adjustments associated with the configuration:

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

An adjustment equals one when it does not apply. This guide intentionally does not reproduce current multipliers or prices. Open **Show Cost Calculation** for the workload to review the values Lakemeter used.

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

For one driver, `W` workers, and `H` active hours per month:

```text
Monthly DBUs
  = (Driver DBU/hour + Worker DBU/hour × W)
  × Applicable adjustments
  × H
```

For a non-serverless configuration, Lakemeter also applies the selected driver and worker VM prices for `H` hours. The expanded calculation supplies the current DBU values, adjustments, and prices.

## What to review before saving

- Does Serverless match the scenario being estimated?
- Do the driver, worker, and worker-count assumptions describe the intended compute shape?
- If Serverless is off, do the VM purchasing assumptions match the scenario?
- Does Photon reflect the configuration, or show as automatic for Serverless?
- Are monthly hours based on expected active compute time rather than user headcount alone?
- If using Run-Based input, does each modeled session represent separately billed compute time?
- Does **Show Cost Calculation** use the expected hours, DBU rate, VM treatment, and regional SKU price?

## Excel export

Each All-Purpose Compute workload is exported as one row. The row includes the compute mode, configuration, selected SKU, monthly hours, DBU per hour, monthly DBUs, list and discounted DBU costs, VM cost when applicable, and total cost.

The workbook keeps calculation cells as formulas so assumptions can be reviewed and adjusted. Serverless rows show no separate VM configuration or VM charge.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
