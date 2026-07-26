---
sidebar_position: 14
---

# Vector Search Sizing

> **Lakemeter UI name:** Vector Search

Use this guide to model Vector Search compute and storage consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not Vector Search architecture, endpoint limits, or workload design.

For current Vector Search capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

A Vector Search workload can include:

- Endpoint compute based on vector capacity units
- Storage above the included allowance

Compute is modeled through a Databricks serverless compute SKU. Storage is calculated separately from DBU consumption.

## Configure the workload

### Vector Search Type

Select the type that matches the endpoint being sized. The selection determines both the number of vectors represented by one capacity unit and the DBU-per-hour rate for each unit.

Use the values shown in Lakemeter rather than copying unit sizes or rates from this guide.

### Capacity (M vectors)

Enter the expected vector capacity in millions:

```text
Entered capacity = 1 means 1 million vectors
```

Lakemeter converts the value to vectors, divides by the loaded vectors-per-unit value, and rounds up to a whole capacity unit. Partial units are not used in the estimate.

### Storage (GB)

Enter the total storage quantity to include in the scenario. Lakemeter calculates the included storage allowance from the number of capacity units, then charges only for storage above that allowance.

Leave this field at zero when storage should not be included in the estimate.

### Hours/Month

Enter the number of hours the endpoint is expected to be active during the month.

## How compute cost is calculated

```text
Capacity units
  = CEILING(
      Capacity in millions × 1,000,000
      ÷ Vectors per unit
    )

DBU per hour
  = Capacity units × DBU per unit-hour

Monthly DBUs
  = DBU per hour × Hours per month

Compute cost
  = Monthly DBUs × Regional price per DBU
```

Lakemeter loads the vectors-per-unit value, DBU-per-unit-hour rate, and regional DBU price for the selected estimate context. Review these values in the expanded calculation because they are not duplicated here.

## How storage cost is calculated

```text
Included storage
  = Capacity units × Included storage per unit

Billable storage
  = MAX(0, Configured storage − Included storage)

Storage cost
  = Billable storage × Loaded storage rate

Total Vector Search cost
  = Compute cost + Storage cost
```

Configured storage can therefore produce a zero storage charge when it is within the included allowance.

## What to review before saving

- Is the selected Vector Search type the one being deployed?
- Is capacity entered in millions rather than as a raw vector count?
- Does capacity include expected growth and duplicated or retained vectors?
- Does the rounded capacity-unit count match the expanded calculation?
- Is the storage value the total configured quantity, not only the expected billable excess?
- Do hours represent the endpoint-active schedule?
- Is the cloud, region, and pricing tier correct for the estimate?

## Common sizing errors

- Entering a raw vector count in a field measured in millions
- Ignoring whole-unit rounding near a capacity boundary
- Estimating document count without converting documents and chunks to vectors
- Entering only storage above the included allowance instead of total storage
- Assuming configured storage always produces a non-zero storage charge
- Comparing endpoint types using a copied capacity table or old rate instead of the values loaded by Lakemeter
- Expecting a separate VM charge for the serverless compute row

## Excel export

Vector Search emits:

1. A compute row for endpoint DBU consumption
2. A storage sub-row when **Storage (GB) is configured with a value greater than zero**

The storage sub-row is emitted whenever configured storage is greater than zero, even when the included allowance reduces billable storage and storage cost to zero. This matches the current export behavior.

The compute row includes the selected type, capacity, hours, effective DBU per hour, monthly DBUs, and selected SKU rate. The storage row keeps configured, included, and billable storage separate from compute. The total Vector Search estimate is the sum of both emitted rows.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
