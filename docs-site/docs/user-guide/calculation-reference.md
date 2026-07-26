---
sidebar_position: 9
---

# Calculation Reference

Lakemeter calculations turn sizing assumptions into monthly planning costs. This page explains the shared calculation structure. Each [workload sizing guide](./workloads) owns its workload-specific fields and formulas.

Lakemeter does not replace current Databricks documentation, official pricing, or customer-specific commercial terms. Use the [official Databricks documentation](https://docs.databricks.com/) for product guidance and the [Databricks pricing page](https://www.databricks.com/product/pricing) to validate current public pricing.

## Calculation flow

Most estimates follow four steps:

1. Convert the workload inputs into a monthly billing quantity.
2. Resolve the applicable SKU and list rate for the estimate context.
3. Multiply the billing quantity by the rate.
4. Add any separately modeled VM, storage, or direct-cost components.

The expanded calculation in the Lakemeter UI shows the actual inputs, quantities, and rates used for a saved workload.

## DBU-based calculations

For workloads billed through DBUs, the common pattern is:

```text
Monthly DBUs = Estimated DBU consumption per hour × Billable hours
DBU cost     = Monthly DBUs × List price per DBU
```

The workload guide explains how Lakemeter derives DBU consumption. It may depend on a selected compute shape, worker or cluster count, endpoint capacity, database capacity, or another workload-specific input.

## Usage calculations

Lakemeter supports several ways to express monthly usage:

### Run-based usage

```text
Billable hours =
  Runs per day × Average runtime in hours × Active days per month
```

Use run-based inputs when the workload executes a predictable number of times.

### Direct active hours

Enter the expected billable hours for the month. Use representative operating time rather than the total hours in a month unless the workload is intentionally modeled as always on.

### Quantity-based usage

Some workloads are sized by tokens, pages, images, storage, vectors, or another billing quantity:

```text
Monthly cost = Monthly quantity × Rate per billing unit
```

Refer to the workload guide for the exact unit expected by each field.

## Classic infrastructure costs

When Lakemeter models cloud infrastructure separately, the estimate combines DBU cost and VM cost:

```text
VM cost =
  (Driver hourly cost + Worker hourly cost × Worker count)
  × Billable hours

Total cost = DBU cost + VM cost
```

The selected instance, purchasing option, worker count, and usage assumptions determine the modeled VM component.

## Serverless calculations

For serverless calculations, Lakemeter does not add a separate VM line:

```text
Total cost = Monthly DBUs × List price per DBU
```

Use the mode and rate shown in the app. For current platform behavior and availability, consult the official Databricks documentation.

## Storage and other subcomponents

A workload can contain more than one billable component. For example, compute, storage, backups, or snapshots may appear as separate lines in an expanded calculation or Excel export.

Review every subcomponent rather than treating the first row as the complete workload total.

## Discounts

Lakemeter starts with the list rate loaded for the selected estimate context. A standard percentage discount is modeled as:

```text
Discounted rate = List rate × (1 − Discount percentage)
Discounted cost = Billing quantity × Discounted rate
```

Some workload calculations can include a workload-specific pricing adjustment before the list rate is applied. The canonical workload guide explains those cases.

Discounts in Lakemeter are planning assumptions. Confirm eligibility and actual contract pricing separately.

## Rate lookup

The estimate context identifies the cloud, region, and pricing tier. Lakemeter then resolves the applicable rate for the selected SKU from its pricing data.

Use the [SKU Explorer](./pricing/sku-explorer) to inspect SKU list rates and the [FMAPI Tokens](./pricing/fmapi-tokens) view for proprietary model token-rate combinations. Because rates and availability change, this documentation intentionally does not reproduce the rate tables.

## Workload-specific calculations

Use the [Workload Sizing Guides](./workloads) for the canonical calculation behavior of a specific workload. In particular:

- [Jobs Compute](./jobs-compute) — run-based compute, workers, DBUs, and VM costs
- [Databricks SQL](./dbsql-warehouses) — warehouse size, clusters, hours, and mode
- [FMAPI — Databricks](./fmapi-databricks) — token or provisioned quantities
- [FMAPI — Proprietary](./fmapi-proprietary) — model, geography, context, and token quantities
- [Lakebase](./lakebase) — minimum and scale-up compute, nodes, storage, PITR, and snapshots

## Validate an estimate

Before sharing an estimate:

1. Expand every workload and verify its billing quantity.
2. Confirm the selected SKU and list rate.
3. Check whether VM or storage components are separate.
4. Confirm monthly usage and concurrency assumptions.
5. Validate important rates and commercial terms.
6. Export the estimate and review all workload sub-rows.
