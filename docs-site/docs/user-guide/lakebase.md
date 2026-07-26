---
sidebar_position: 16
---

# Lakebase Sizing

> **Lakemeter UI name:** Lakebase

Use this guide to model Lakebase compute and storage-related consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not general Lakebase architecture or product limits.

For current Lakebase capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## What Lakemeter estimates

A Lakebase workload can include:

- Compute at the configured capacity and node count
- Database storage
- Point-in-time restore storage
- Snapshot storage

Compute is modeled through a Databricks compute SKU. Storage-related quantities are modeled separately and only appear when their input is greater than zero.

## Choose a compute type

Lakemeter presents two compute types.

### Auto-scaling

Use **Auto-scaling** when the estimate should include a minimum capacity and time spent at a higher capacity.

Enter:

- **Minimum CU** — the baseline capacity
- **Maximum CU** — the capacity modeled during scale-up hours
- **Scale to Zero** — whether compute is billed only during active hours
- **Active Hours / Month** — shown when scale-to-zero is enabled
- **Scale-up Hours / Month** — the time modeled at maximum CU

Lakemeter restricts the maximum choices based on the selected minimum so the configured range is 16 CU or less. Use the values offered by the form rather than copying a capacity list from this guide.

### Fixed size

Use **Fixed size** when the estimate should use one larger capacity without a separate autoscaling range.

Select one of the fixed sizes offered by Lakemeter. Fixed-size mode disables scale-to-zero and scale-up hours, so the selected capacity is treated as one always-on compute level.

## Size the compute range

For an auto-scaling estimate:

1. Choose the minimum CU expected during baseline operation.
2. Choose the maximum CU expected during periods of higher demand.
3. Estimate how many hours per month the workload spends at maximum CU.
4. Decide whether the compute can scale to zero.

The **Scale-up Hours / Month** value represents hours at maximum CU, not hours for only the difference between minimum and maximum. Lakemeter therefore separates the month into two buckets:

```text
Baseline bucket = Minimum CU × Baseline hours
Scale-up bucket = Maximum CU × Scale-up hours
```

This avoids billing the same scale-up hours once at minimum CU and again as incremental capacity.

## Scale-to-zero behavior

### Scale to zero off

When scale-to-zero is off, Lakemeter treats the minimum capacity as always on:

```text
Baseline hours = 730 − Scale-up hours
Scale-up hours = Entered scale-up hours
```

The always-on minimum bucket receives the Lakebase always-on adjustment used by Lakemeter, currently 25%. The scale-up bucket uses the normal DBU-per-CU-hour conversion.

### Scale to zero on

When scale-to-zero is on, enter the total active hours for the month:

```text
Baseline hours = Active hours − Scale-up hours
Scale-up hours = Entered scale-up hours
```

The always-on adjustment does not apply. Both active buckets use the normal DBU-per-CU-hour conversion.

Make sure scale-up hours do not exceed active hours.

## Number of nodes

**Number of Nodes** is the total number of nodes included in the estimate. Every selected node multiplies both baseline and scale-up compute consumption:

```text
Compute DBUs = CU × DBU per CU-hour × Nodes × Hours
```

Choose the total node count required by the scenario from the options shown in Lakemeter. Use the official Databricks documentation to determine the appropriate production topology.

## How compute cost is calculated

Lakemeter resolves the DBU-per-CU-hour conversion and regional list price for the selected estimate context.

### Always-on baseline

When scale-to-zero is off, Lakemeter applies the always-on adjustment to the DBU-per-CU-hour conversion for the minimum bucket:

```text
Effective baseline DBU per CU-hour
  = Standard DBU per CU-hour × (1 − Always-on adjustment)

Baseline DBUs
  = Minimum CU
  × Effective baseline DBU per CU-hour
  × Nodes
  × Baseline hours
```

The regional **price per DBU does not change** between the baseline and scale-up buckets. The adjustment is represented by lower DBU consumption per CU-hour.

### Scale-up bucket

```text
Scale-up DBUs
  = Maximum CU
  × Standard DBU per CU-hour
  × Nodes
  × Scale-up hours
```

### Convert DBUs to cost

```text
Baseline $ per CU-hour
  = Effective baseline DBU per CU-hour × Regional $ per DBU

Scale-up $ per CU-hour
  = Standard DBU per CU-hour × Regional $ per DBU

Compute cost
  = (Baseline DBUs + Scale-up DBUs) × Regional $ per DBU
```

Lakemeter displays the DBU-per-CU-hour and dollar-per-CU-hour chain in the expanded calculation so the values can be cross-checked against the pricing source.

## Worked sizing example

Assume an auto-scaling workload with:

- Minimum capacity of 4 CU
- Maximum capacity of 8 CU
- One node
- 50 scale-up hours per month
- Scale-to-zero off

Lakemeter models:

```text
Baseline:
  4 CU × adjusted DBU/CU-hour × 1 node × (730 − 50) hours

Scale-up:
  8 CU × standard DBU/CU-hour × 1 node × 50 hours

Compute total:
  (Baseline DBUs + Scale-up DBUs) × regional $/DBU
```

If scale-to-zero is enabled with 200 active hours, the baseline changes to `200 − 50` hours and does not receive the always-on adjustment.

The current conversion and price values are intentionally not reproduced here. Review them in the expanded Lakemeter calculation and verify important estimates against current Databricks pricing.

## Storage-related inputs

Enter monthly quantities for the components included in the scenario:

| Field | Sizing guidance |
|---|---|
| **Storage (GB)** | Expected database storage billed for the month |
| **Point-in-Time Restore (GB)** | Expected PITR storage quantity |
| **Snapshot Storage (GB)** | Expected snapshot storage quantity |

Lakemeter converts each configured quantity to its corresponding storage billing units and applies the loaded storage rate. The expanded calculation shows the multiplier and rate used. This guide does not duplicate those values because they can change.

## What to review before saving

- Is auto-scaling or fixed size the intended billing pattern?
- Does minimum CU represent normal baseline demand?
- Does maximum CU represent the capacity reached during the entered scale-up hours?
- If scale-to-zero is enabled, are active hours realistic?
- Is scale-up time a subset of active time?
- Does the node count represent all billed nodes?
- Are database, PITR, and snapshot storage entered separately?

## Excel export

Lakebase can emit these rows:

1. Compute
2. Database storage, when configured
3. Point-in-time restore, when configured
4. Snapshot storage, when configured

The compute row includes the configured CU range, scale-to-zero setting, scale-up hours, node count, DBU quantity, and selected SKU rate. Storage-related rows remain separate so each quantity and charge can be reviewed independently.

The total Lakebase estimate is the sum of every emitted row.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
