---
sidebar_position: 10
---

# Lakeflow Spark Declarative Pipelines (SDP) Sizing

> **Lakemeter UI name:** Lakeflow Spark Declarative Pipelines (SDP)

Use this guide to model Lakeflow Spark Declarative Pipelines (SDP) compute consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not pipeline design, edition features, performance tuning, or product limits.

For current Lakeflow Spark Declarative Pipelines guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

An SDP workload includes:

- Databricks compute consumption for the selected pipeline configuration and monthly usage
- VM infrastructure cost when **Serverless** is off
- No separate VM infrastructure charge when **Serverless** is on

The estimate-level cloud, region, and Databricks tier determine which choices and rates Lakemeter loads.

## Choose a compute mode

### Serverless off

Use this mode to model an SDP edition and a driver-and-worker configuration with separate Databricks and VM charges.

Enter:

- **SDP Edition**
- **Driver Node → Instance Type**
- **Worker Nodes → Instance Type**
- Worker **Count**
- **Photon**, if it is part of the scenario
- The driver and worker **Pricing Tier**
- A **Payment Option** when Lakemeter displays one

The selected SDP edition determines the pricing context used by Lakemeter. Choose the edition that matches the planned pipeline; use the official Databricks documentation for current edition capabilities rather than using this guide as a feature matrix.

The driver count is one. The worker count multiplies both worker DBU consumption and worker VM cost.

### Serverless on

When **Serverless** is on:

- Choose the **Mode** offered by Lakemeter.
- Select driver and worker instance types and a worker count as sizing proxies for the DBU estimate.
- Lakemeter marks Photon as automatic.
- The **SDP Edition** field is not used for the serverless estimate.
- Driver and worker VM pricing fields are not used, and no separate VM cost is added.

The node selections in this form are estimator assumptions; they do not represent a separately billed serverless VM configuration.

## Enter monthly usage

Lakemeter offers two usage input methods.

### Run-Based

Use this method for a pipeline modeled as repeated updates. Enter:

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

Use the expected billed duration of each update. Include retries or overlapping pipeline activity when they materially change compute time.

### Direct Hours

Enter **Hours/Month** when total active pipeline time is known directly. This can represent a continuously active scenario or a monthly total derived from observed usage.

Enter the hours represented by the scenario rather than relying on a fixed example from this guide.

## How the estimate is calculated

Lakemeter resolves the current DBU consumption values, multipliers, SKU rate, and VM rates from the selected estimate context.

### Base DBU consumption

```text
Base DBU per hour
  = Driver DBU per hour
  + (Worker DBU per hour × Number of workers)
```

Lakemeter then applies the current adjustments associated with the selected configuration:

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

An adjustment equals one when it does not apply. For non-serverless workloads, the SDP edition and Photon setting determine the pricing context resolved by Lakemeter. For serverless workloads, Lakemeter uses the serverless pricing context shown in the expanded calculation.

This guide intentionally does not reproduce current edition rates, multiplier values, or SKU inventories. Open **Show Cost Calculation** for the workload to review the values Lakemeter used.

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

For a pipeline with one driver, `W` workers, `R` updates per day, average runtime `M` minutes, and `D` active days:

```text
Hours per month = R × (M ÷ 60) × D

Monthly DBUs
  = (Driver DBU/hour + Worker DBU/hour × W)
  × Applicable adjustments
  × Hours per month
```

For a non-serverless configuration, Lakemeter also adds the driver and worker VM cost for those hours. The expanded calculation supplies the current DBU values, adjustments, and prices.

## What to review before saving

- Does Serverless match the pipeline scenario?
- If Serverless is off, does **SDP Edition** match the planned pipeline?
- Do the driver, worker, and worker-count assumptions describe the intended compute shape?
- If Serverless is off, do the VM purchasing assumptions match the scenario?
- If Serverless is on, is the selected mode intentional?
- Does Photon reflect the configuration, or show as automatic for Serverless?
- Does the usage method represent actual active pipeline time?
- Are continuous operation, retries, and overlapping updates represented where material?
- Does **Show Cost Calculation** use the expected hours, DBU rate, VM treatment, and regional SKU price?

## Excel export

Each Lakeflow Spark Declarative Pipelines workload is exported as one row. The row includes the compute mode, configuration, selected SKU, monthly hours, DBU per hour, monthly DBUs, list and discounted DBU costs, VM cost when applicable, and total cost.

For non-serverless estimates, the configuration identifies the selected edition and Photon setting. For serverless estimates, it identifies the selected mode. The workbook keeps calculation cells as formulas so assumptions can be reviewed and adjusted.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
