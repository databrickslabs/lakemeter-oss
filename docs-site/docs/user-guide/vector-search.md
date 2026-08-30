---
sidebar_position: 14
---

# AI Search Sizing

> **Lakemeter UI name:** AI Search

Use this guide to model AI Search compute, storage, and optional reranker consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not AI Search architecture, endpoint limits, or workload design.

For current AI Search capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

An AI Search workload can include:

- Endpoint compute based on vector capacity units
- Storage above the first 30 GB included allowance
- Optional AI Search Reranker requests

Compute and reranker requests are modeled through Databricks DBU SKUs. Storage is calculated separately in DSUs using the regional `DATABRICKS_STORAGE` rate.

## Configure the workload

### AI Search Type

Select the type that matches the endpoint being sized. The selection determines both the number of vectors represented by one capacity unit and the DBU-per-hour rate for each unit.

Use the values shown in Lakemeter rather than copying unit sizes or rates from this guide.

### Capacity (M vectors)

Enter the expected vector capacity in millions:

```text
Entered capacity = 1 means 1 million vectors
```

Lakemeter converts the value to vectors, divides by the loaded vectors-per-unit value, and rounds up to a whole capacity unit. Partial units are not used in the estimate.

### Storage (GB)

Enter the total storage quantity to include in the scenario. The first 30 GB is included, and Lakemeter charges only for storage above that allowance.

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
  = 30 GB when an endpoint is provisioned

Billable storage
  = MAX(0, Configured storage − Included storage)

Storage DSUs
  = Billable storage × DSU per GB for the selected type

Storage cost
  = Storage DSUs × Regional price per DSU

Reranker DBUs
  = Reranker requests in thousands × 28.571 DBU

Reranker cost
  = Reranker DBUs × Regional price per DBU

Total AI Search cost
  = Compute cost + Reranker cost + Storage cost
```

Configured storage can therefore produce a zero storage charge when it is within the included allowance.

Standard AI Search uses 10 DSU per billable GB-month. Storage Optimized AI Search uses 2 DSU per billable GB-month.

## What to review before saving

- Is the selected AI Search type the one being deployed?
- Is capacity entered in millions rather than as a raw vector count?
- Does capacity include expected growth and duplicated or retained vectors?
- Does the rounded capacity-unit count match the expanded calculation?
- Is the storage value the total configured quantity, not only the expected billable excess?
- Does the expanded calculation show the expected 10 or 2 DSU per billable GB and the regional DSU price?
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

AI Search emits:

1. A compute row for endpoint DBU consumption
2. A reranker row when **AI Search Reranker is enabled**
3. A storage sub-row when **Storage (GB) is configured with a value greater than zero**

The storage sub-row is emitted whenever configured storage is greater than zero, even when the included allowance reduces billable storage and storage cost to zero. This matches the current export behavior.

The compute row includes the selected type, capacity, hours, effective DBU per hour, monthly DBUs, and selected SKU rate. The reranker row shows requests, DBU per 1,000 requests, and regional SKU rate. The storage row keeps configured, included, and billable storage separate from compute and reports its DSU quantity and rate. The total AI Search estimate is the sum of all emitted rows.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
