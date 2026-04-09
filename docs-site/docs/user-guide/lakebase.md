---
sidebar_position: 16
---

# Lakebase

> **Lakemeter UI name:** Lakebase

Lakebase is Databricks' managed PostgreSQL-compatible transactional database. Unlike compute workloads, Lakebase has two independent cost components: **compute** (CU-based) and **storage** (DSU-based), which appear as separate rows in the Excel export.

![Lakebase documentation page](/img/guides/lakebase-guide.png)
*The Lakebase guide — compute units, storage pricing, and dual-row Excel export explained.*

![Lakebase worked cost example](/img/guides/lakebase-worked-example.png)
*Worked example showing separate compute and storage cost calculations.*

## When to use Lakebase

Use Lakebase when you need a **managed transactional database** for your Databricks application -- CRUD operations, user data, application state, or any workload that needs PostgreSQL compatibility. If you need analytics/BI queries over large datasets, see [DBSQL](/user-guide/dbsql-warehouses) instead.

## Real-world example

> **Scenario:** You are deploying a web application backend on AWS us-east-1 (Premium tier). The database needs 4 Compute Units with a read replica for high availability (2 nodes total), 500 GB of storage, and runs 24/7.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Lakebase |
| CU Size | 4 |
| Number of Nodes | 2 (primary + 1 read replica) |
| Storage (GB) | 500 |
| Hours Per Month | 730 (24/7) |

### Step-by-step calculation

**1. Compute cost**

```
DBU/Hour     = CU Size x Number of Nodes = 4 x 2 = 8 DBU/hour
Monthly DBUs = DBU/Hour x Hours/Month = 8 x 730 = 5,840 DBUs
Compute Cost = 5,840 x $0.40/DBU = $2,336.00
```

**2. Storage cost**

Lakebase storage is measured in Databricks Storage Units (DSU). Each GB equals 15 DSU:

```
Total DSU    = Storage GB x 15 = 500 x 15 = 7,500 DSU
Storage Cost = 7,500 x $0.023/DSU = $172.50/month
```

**3. Total monthly cost**

```
Total = Compute Cost + Storage Cost = $2,336.00 + $172.50 = $2,508.50/month
```

:::note
These are example rates for illustration. The $0.40/DBU rate is the fallback for `DATABASE_SERVERLESS_COMPUTE` on AWS/us-east-1/Premium. Actual rates depend on your cloud, region, and pricing tier. Storage at $0.023/DSU is a fixed rate.
:::

### What about a smaller deployment?

For a development database with 1 CU, 1 node, 100 GB, business hours only:

```
Compute: 1 x 1 x 176 hrs = 176 DBUs x $0.40 = $70.40
Storage: 100 x 15 x $0.023 = $34.50
Total:   $104.90/month
```

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **CU Size** | Compute Units per node: 1, 2, 4, or 8. Determines the DBU/hour rate per node. | 1 |
| **Number of Nodes** | 1 = primary only. 2 = primary + 1 read replica (HA). 3 = primary + 2 read replicas (max HA). | 1 |
| **Storage (GB)** | Provisioned storage in gigabytes, 0 to 8,192. | 0 |
| **Hours Per Month** | Compute uptime. Use 730 for always-on databases. | 730 |

### Nodes and high availability

| Nodes | Description | Use case |
|-------|-------------|----------|
| 1 | Primary node only | Development, non-critical workloads |
| 2 | Primary + 1 read replica | Production with read scaling and failover |
| 3 | Primary + 2 read replicas | Maximum HA, heavy read workloads |

Each additional node multiplies the compute cost linearly.

### Estimating hours for part-time usage

Lakebase uses direct hours input only. If your database is not always-on (e.g., a development database used during work hours), calculate your hours manually:

```
Hours/Month = Sessions Per Day x Avg Duration Hours x Days Per Month
```

**Example**: 8 hours/day x 22 business days = 176 hours/month — enter **176** in the Hours/Month field.

## How costs are calculated

### Compute

```
DBU/Hour     = CU Size x Number of Nodes
Monthly DBUs = DBU/Hour x Hours/Month
Compute Cost = Monthly DBUs x $/DBU
```

**SKU**: `DATABASE_SERVERLESS_COMPUTE` (fallback: $0.40/DBU)

### Storage

```
Total DSU     = Storage GB x 15
Storage Cost  = Total DSU x $0.023/DSU
```

**SKU**: `DATABRICKS_STORAGE`

Storage cost is a **fixed monthly amount** independent of compute hours. You pay for provisioned storage capacity regardless of how many hours the compute runs.

### Total

```
Total = Compute Cost + Storage Cost
```

### Edge cases

| Scenario | Behavior |
|----------|----------|
| Storage = 0 or not set | No storage sub-row emitted in Excel |
| Maximum storage (8,192 GB) | Storage cost = 8,192 x 15 x $0.023 = $2,826.24/month |

## Tips

- **Start with 1 CU for development**: A single CU with 1 node is sufficient for development and testing. Scale to 2, 4, or 8 CU based on query load and concurrency.
- **Use 2 nodes for production**: A read replica provides both read scaling and automatic failover. The 2x compute cost is worth it for production reliability.
- **Storage is cheap relative to compute**: 500 GB costs ~$172/month, while even 1 CU at 730 hours costs ~$292. Optimize CU size first.

## Common mistakes

- **Expecting a single cost number**: Lakebase produces **two rows** in the Excel export -- one for compute, one for storage. The total is the sum of both.
- **Setting storage to 0 for testing**: If storage is 0 or not set, no storage row appears. Remember to include realistic storage estimates for production sizing.
- **Forgetting nodes multiply compute**: 2 nodes doubles the DBU/hour, 3 nodes triples it. A 4 CU database with 3 nodes uses 12 DBU/hour, not 4.
- **Confusing CU with vCPU**: Compute Units (CU) are a Databricks-specific unit, not CPU cores. The available CU sizes (1, 2, 4, 8) map to DBU rates, not to hardware specifications.

## Excel export

Lakebase workloads export as **two rows** per line item:

| Row | Contents | SKU |
|-----|----------|-----|
| **Compute row** | CU-based DBU costs (CU x nodes x hours x $/DBU) | `DATABASE_SERVERLESS_COMPUTE` |
| **Storage row** | GB-based storage costs (GB x 15 DSU x $0.023/DSU) | `DATABRICKS_STORAGE` |

| Column (compute row) | What it shows |
|--------|--------------|
| Configuration | CU size and node count |
| Mode | Serverless (always) |
| SKU | `DATABASE_SERVERLESS_COMPUTE` |
| DBU/Hour | CU x nodes |
| Hours/Month | Direct hours value |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost | Monthly DBUs x $/DBU |
| VM Cost | $0 (always serverless) |
| Total Cost | Compute cost only (storage is in the second row) |

The bottom-line total in the spreadsheet sums across both compute and storage rows for the final Lakebase cost.
