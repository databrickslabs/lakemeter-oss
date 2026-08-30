---
sidebar_position: 20
---

# Databricks Default Storage Sizing

> **Lakemeter UI name:** Databricks Default Storage

Use this guide to estimate Databricks-managed storage and storage API operations. Lakemeter converts the entered quantities into Databricks Storage Units (DSUs) and prices them with the regional `DATABRICKS_STORAGE` SKU.

This workload does not estimate customer-managed object storage, backups, data transfer, or compute that reads and writes the stored data.

## Form inputs

### Stored data

Enter the average monthly quantity in GB or TB. Lakemeter converts 1 TB to 1,024 GB.

```text
Stored-data DSUs = Stored GB-months × 1 DSU/GB-month
```

### Tier 1 operations

Enter the monthly number of Tier 1 operations in thousands. Lakemeter uses this field for PUT, COPY, POST, and LIST operations.

### Tier 2 operations

Enter the monthly number of other storage API operations in thousands.

Use the operation tier shown by the current Databricks pricing source. Cloud providers can classify operations differently.

## How Lakemeter calculates cost

The operation multipliers in the current pricing bundle are:

- AWS and GCP: 0.2174 DSU per 1,000 Tier 1 operations and 0.0174 DSU per 1,000 Tier 2 operations
- Azure: 0.3535 DSU per 1,000 Tier 1 operations and 0.0226 DSU per 1,000 Tier 2 operations

```text
Tier 1 DSUs = Tier 1 operations in thousands × Cloud Tier 1 multiplier
Tier 2 DSUs = Tier 2 operations in thousands × Cloud Tier 2 multiplier

Total DSUs
  = Stored-data DSUs
  + Tier 1 DSUs
  + Tier 2 DSUs

Monthly cost = Total DSUs × Regional price per DSU
```

The regional price is resolved from the `DATABRICKS_STORAGE` SKU for the estimate cloud, region, and tier.

## What to review before saving

- Is stored data an average GB-month quantity rather than a one-time upload?
- Is the GB or TB unit correct?
- Are operation counts entered in thousands?
- Are operations assigned to the correct cloud-specific tier?
- Does the expanded calculation show the expected DSU quantity and regional DSU price?
- Have customer-managed storage and data transfer been modeled separately where required?

## Excel export

Each workload emits three component rows:

1. Stored Data
2. Tier 1 Operations
3. Tier 2 Operations

Each row shows its input quantity, DSU multiplier, monthly DSUs, list DSU rate, and monthly cost. Components remain visible when their quantity is zero so the calculation is auditable.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Databricks pricing](https://www.databricks.com/product/pricing/storage)
