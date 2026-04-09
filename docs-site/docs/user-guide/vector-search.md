---
sidebar_position: 14
---

# Vector Search

> **Lakemeter UI name:** Vector Search

Vector Search provides managed vector database endpoints for similarity search, powering RAG (Retrieval Augmented Generation) applications, recommendation systems, and semantic search. Lakemeter supports cost estimation for **Standard** and **Storage-Optimized** endpoint types.

![Vector Search documentation page](/img/guides/vector-search-guide.png)
*The Vector Search guide — endpoint types, vector capacity calculation, and free storage tier explained.*

![Vector Search worked cost example](/img/guides/vector-search-worked-example.png)
*Worked example showing CEILING-based unit calculation, DBU costs, and storage tier breakdown.*

## When to use Vector Search

Use Vector Search when you need a **managed vector database** for storing and querying embeddings -- things like RAG chatbots, document retrieval, product recommendations, or image similarity search. If you need to call a language model directly (not store embeddings), see [FMAPI — Databricks Models](/user-guide/fmapi-databricks) instead.

## Real-world example

> **Scenario:** You are building a RAG-powered knowledge base on AWS us-east-1 (Premium tier). Your document corpus produces 10 million embeddings and you estimate 50 GB of associated metadata storage. You want a Standard endpoint running 24/7.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Vector Search |
| Endpoint Type | Standard |
| Capacity (Millions) | 10 |
| Storage (GB) | 50 |
| Hours Per Month | 730 (24/7) |

### Step-by-step calculation

**1. Compute units**

Vector Search divides your vector capacity into fixed-size units. For Standard mode, each unit holds 2 million vectors:

```
Units = CEILING(Capacity in Vectors / Divisor)
      = CEILING(10,000,000 / 2,000,000)
      = CEILING(5)
      = 5 units
```

**2. DBU rate per hour**

Each unit consumes 4.0 DBU/hour in Standard mode:

```
DBU/Hour = Units x DBU per Unit = 5 x 4.0 = 20.0 DBU/hour
```

**3. Monthly compute cost**

```
Monthly DBUs = DBU/Hour x Hours/Month = 20.0 x 730 = 14,600 DBUs
DBU Cost     = 14,600 x $0.07/DBU = $1,022.00
```

**4. Storage cost**

Each unit includes 20 GB of free storage. Billing only applies to storage beyond this free tier:

```
Free Storage  = Units x 20 GB = 5 x 20 = 100 GB
Billable      = MAX(0, 50 - 100) = 0 GB (within free tier)
Storage Cost  = $0.00
```

In this case, 50 GB is fully covered by the 100 GB free tier.

**5. Total monthly cost**

```
Total = DBU Cost + Storage Cost = $1,022.00 + $0.00 = $1,022.00/month
```

:::note
These are example rates for illustration. Actual $/DBU depends on your cloud, region, and pricing tier. Lakemeter loads real rates from the Databricks pricing bundle.
:::

### What about Storage-Optimized?

For the same 10 million vectors with Storage-Optimized:

```
Units    = CEILING(10,000,000 / 64,000,000) = CEILING(0.15625) = 1 unit
DBU/Hour = 1 x 18.29 = 18.29 DBU/hour
Monthly  = 18.29 x 730 = 13,351.7 DBUs
DBU Cost = 13,351.7 x $0.07 = $934.62
```

Storage-Optimized uses a much larger unit size (64M vectors vs 2M), so small deployments may actually cost more per unit but fewer units are needed. At 10M vectors, Standard and Storage-Optimized end up being close in cost.

:::tip When to choose Storage-Optimized
Storage-Optimized becomes significantly cheaper at **100M+ vectors** where the 64M divisor means far fewer units. For smaller deployments under 50M vectors, Standard is usually the better choice.
:::

## Endpoint types

| Type | Unit size | DBU/hr per unit | Best for |
|------|-----------|----------------|----------|
| **Standard** | 2 million vectors | 4.0 | General RAG, moderate vector counts (< 100M) |
| **Storage-Optimized** | 64 million vectors | 18.29 | Large-scale search, 100M+ vectors, cost-sensitive storage |

### How the CEILING function works

The number of compute units is always **rounded up** to the nearest whole number. This means:
- 1 vector → 1 unit (minimum)
- 2,000,001 vectors (Standard) → 2 units (crossed the 2M boundary)
- 63,999,999 vectors (Storage-Optimized) → 1 unit (still within 64M)

This is important for cost planning -- there is no "partial unit" pricing.

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **Endpoint Type** | Standard or Storage-Optimized. Determines unit size and DBU rate. | Standard |
| **Capacity (Millions)** | Number of vectors to store, in millions. | 1 |
| **Storage (GB)** | Metadata/additional storage in GB. Triggers a storage sub-row when it exceeds the free tier. | 0 |
| **Hours Per Month** | Service uptime. Use 730 for always-on endpoints. | 730 |

### Free storage tier

Each compute unit includes free storage:

| Endpoint Type | Free storage per unit |
|--------------|----------------------|
| Standard | 20 GB |
| Storage-Optimized | 20 GB |

Storage beyond the free tier is billed at **$0.023/GB/month** and appears as a separate sub-row in the Excel export.

## How costs are calculated

### Compute

```
Units        = CEILING(Capacity Millions x 1,000,000 / Divisor)
DBU/Hour     = Units x Mode DBU Rate
Monthly DBUs = DBU/Hour x Hours/Month
Compute Cost = Monthly DBUs x $/DBU
```

Where:
- Standard: Divisor = 2,000,000, DBU Rate = 4.0/hr per unit
- Storage-Optimized: Divisor = 64,000,000, DBU Rate = 18.29/hr per unit

### Storage

```
Free Storage GB = Units x 20
Billable GB     = MAX(0, Storage GB - Free Storage GB)
Storage Cost    = Billable GB x $0.023/month
```

### Total

```
Total = Compute Cost + Storage Cost
```

### SKU mapping

| Component | SKU | Rate |
|-----------|-----|------|
| Compute (all modes) | `SERVERLESS_REAL_TIME_INFERENCE` | $0.07/DBU (fallback) |
| Storage (over free tier) | Direct dollar amount | $0.023/GB/month |

## Tips

- **Right-size your capacity**: Estimate the actual number of embeddings you will store. A typical RAG application with 10,000 documents (chunked into ~10 chunks each) needs ~100K vectors, not 100M. Enter capacity in millions.
- **Account for the CEILING function**: 2.1 million vectors costs the same as 4 million vectors in Standard mode (both need 2 units). Plan around unit boundaries to avoid paying for unused capacity.
- **Storage-Optimized for large catalogs**: If you have 100M+ product embeddings for e-commerce search, Storage-Optimized is significantly cheaper because each unit holds 64M vectors instead of 2M.
- **Free storage covers many use cases**: With 5 Standard units (10M vectors), you get 100 GB free storage. Most RAG metadata fits within the free tier.

## Common mistakes

- **Confusing millions with actual vector count**: The Capacity field is in **millions**. If you have 5 million vectors, enter 5, not 5,000,000.
- **Ignoring the unit rounding**: Going from 2M to 2.1M vectors in Standard mode doubles your cost (1 unit → 2 units). Be aware of the unit boundaries.
- **Choosing Storage-Optimized for small deployments**: At less than 10M vectors, Standard is almost always cheaper because the minimum is 1 unit either way, and Standard's per-unit DBU rate is lower.
- **Expecting VM costs**: Vector Search is always serverless. $0 VM cost is correct.

## Excel export

Vector Search workloads may export as **one or two rows**:

| Row | When | Contents |
|-----|------|----------|
| **Compute row** | Always | DBU-based cost for the endpoint units |
| **Storage sub-row** | When storage exceeds free tier | Dollar-based storage cost ($0.023/GB/month for billable GB) |

| Column (compute row) | What it shows |
|--------|--------------|
| Configuration | Endpoint type and capacity |
| Mode | Serverless (always) |
| SKU | `SERVERLESS_REAL_TIME_INFERENCE` |
| DBU/Hour | Units x mode DBU rate |
| Hours/Month | Direct value |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost | Monthly DBUs x $/DBU |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost + Storage Cost |
