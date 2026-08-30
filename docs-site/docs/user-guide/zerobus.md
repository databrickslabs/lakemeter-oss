---
sidebar_position: 21
---

# Zerobus Ingest Sizing

> **Lakemeter UI name:** Zerobus Ingest

Use this guide to estimate the Databricks DBU charge for data ingested through Zerobus. Lakemeter supports standard Zerobus ingestion and OpenTelemetry (OTel) ingestion.

Zerobus is volume-based in Lakemeter. It is not sized from cluster hours.

## Form inputs

### Ingestion mode

- **Standard** — direct Zerobus ingestion at 0.143 DBU per GB
- **OTel** — OpenTelemetry ingestion at 0.222 DBU per GB

### Monthly ingested data

Enter the total data volume sent through Zerobus during the month in GB.

## Availability

Lakemeter exposes Zerobus pricing for:

- AWS: Premium and Enterprise
- Azure: Premium
- GCP: Premium and Enterprise

The form rejects unsupported cloud and tier combinations.

## How Lakemeter calculates cost

Both modes use the regional `JOBS_SERVERLESS_COMPUTE` SKU price.

```text
Monthly DBUs = Monthly ingested GB × DBU per GB for the selected mode

Monthly cost = Monthly DBUs × Regional Jobs Serverless price per DBU
```

Example for 1,000 GB:

```text
Standard: 1,000 × 0.143 = 143 DBUs
OTel:     1,000 × 0.222 = 222 DBUs
```

## Costs not included

The Zerobus workload excludes:

- Producer or collector compute
- Target Delta table storage
- Downstream processing
- Data transfer or network egress

Add separate Lakemeter workloads for supported components and model external costs outside Lakemeter where necessary.

## What to review before saving

- Is the mode Standard or OTel?
- Is the quantity the complete monthly ingested volume in GB?
- Is the selected cloud and tier supported?
- Does the expanded calculation show 0.143 or 0.222 DBU per GB?
- Have storage, producer compute, downstream processing, and transfer costs been considered separately?

## Excel export

Zerobus emits one DBU row. The configuration shows the selected mode, monthly ingested GB, and DBU-per-GB conversion. VM and DSU columns remain zero.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [Jobs Compute](./jobs-compute)
- [Databricks pricing](https://www.databricks.com/product/pricing)
