---
sidebar_position: 11
---

# Databricks SQL (DBSQL)

> **Lakemeter UI name:** Databricks SQL

DBSQL provides SQL analytics warehouses for business intelligence, reporting, and ad-hoc queries. It supports **Classic**, **Pro**, and **Serverless** warehouse types across 9 sizes, from 2X-Small to 4X-Large.

![DBSQL Warehouses documentation page](/img/guides/dbsql-warehouses-guide.png)
*The DBSQL guide — real-world scenario, worked cost example, and configuration reference for Classic, Pro, and Serverless warehouses.*

![DBSQL worked cost example](/img/guides/dbsql-worked-example.png)
*Step-by-step cost calculation showing DBU rates, warehouse sizing, and monthly totals.*

## When to use DBSQL

Use DBSQL when you need a **SQL-first analytics environment** -- dashboards, scheduled reports, BI tool connections (Tableau, Power BI, dbt), or ad-hoc SQL queries. Unlike Jobs or All-Purpose Compute, DBSQL pricing is based on fixed **warehouse sizes** rather than individual instance types. If you need a general-purpose Spark cluster for notebooks or Python/Scala workloads, see [All-Purpose Compute](/user-guide/all-purpose-compute).

## Real-world example

> **Scenario:** Your analytics team runs a BI dashboard platform on AWS us-east-1 (Premium tier). You need a Pro warehouse sized Medium for ~50 concurrent users, running 8 hours a day on business days. You also want a second cluster for peak-hour scaling.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | DBSQL |
| Warehouse Type | Pro |
| Warehouse Size | Medium |
| Number of Clusters | 2 |
| Hours Per Month | 176 (= 8 hrs x 22 days) |

### Step-by-step calculation

**1. DBU rate per hour**

Each warehouse size has a fixed DBU/hour rate. Medium = 24 DBU/hr. With 2 clusters:

```
DBU/Hour = Warehouse Size DBU x Number of Clusters
         = 24 x 2
         = 48 DBU/hour
```

**2. Monthly DBUs and cost**

```
Monthly DBUs = DBU/Hour x Hours/Month = 48 x 176 = 8,448 DBUs
DBU Cost     = 8,448 x $0.55/DBU (Pro rate) = $4,646.40
```

**3. VM infrastructure cost**

Classic and Pro warehouses also have VM costs based on the warehouse size's underlying instances. Lakemeter uses default estimates:

```
VM Cost = (Driver VMs x Driver $/hr + Worker VMs x Worker $/hr) x Clusters x Hours/Month
```

The exact VM cost depends on the warehouse size. For illustration, a Medium warehouse might produce ~$200-400 in VM costs at 176 hours.

**4. Total monthly cost**

```
Total = DBU Cost + VM Cost ≈ $4,646.40 + VM estimate
```

:::note
These are example rates for illustration. Actual $/DBU and VM prices depend on your cloud, region, and pricing tier. Lakemeter loads real rates from the Databricks pricing bundle.
:::

### What if you used Serverless instead?

Serverless eliminates VM costs entirely but has a higher $/DBU rate:

```
Monthly DBUs = 48 x 176 = 8,448 DBUs (same)
DBU Cost     = 8,448 x $0.70/DBU (Serverless rate) = $5,913.60
VM Cost      = $0
Total        = $5,913.60
```

Serverless costs more per DBU but eliminates VM overhead and provides instant startup. For intermittent or bursty BI workloads, the total cost may be lower because you only pay for active query time.

## Warehouse sizes

DBSQL uses a fixed mapping from warehouse size to DBU/hour. The DBU/hour is the same regardless of warehouse type (Classic, Pro, or Serverless) -- what changes is the $/DBU rate.

| Size | DBU/Hour | Typical use case |
|------|----------|-----------------|
| **2X-Small** | 4 | Light dashboards, single-user queries |
| **X-Small** | 6 | Small team dashboards |
| **Small** | 12 | Team analytics, moderate concurrency |
| **Medium** | 24 | Department-level BI |
| **Large** | 40 | Heavy analytics, high concurrency |
| **X-Large** | 80 | Enterprise BI platforms |
| **2X-Large** | 144 | Large-scale data warehousing |
| **3X-Large** | 272 | Very large queries, complex joins |
| **4X-Large** | 528 | Maximum compute, extreme workloads |

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **Warehouse Type** | Classic, Pro, or Serverless. Serverless requires **Premium** tier or above. | Serverless |
| **Warehouse Size** | 2X-Small through 4X-Large. Determines the DBU/hour rate. | Small |
| **Number of Clusters** | Concurrent cluster count for horizontal scaling. Multiplies DBU/hour linearly. | 1 |
| **Hours Per Month** | Warehouse uptime hours. Use 730 for 24/7, 176 for business hours (8 x 22 days). | 730 |

### Classic and Pro VM costs

Classic and Pro warehouses have underlying VM infrastructure. Lakemeter estimates VM costs using default rates ($0.20/hr driver, $0.10/hr worker) scaled by the warehouse size's instance counts. These are approximations -- actual VM costs depend on your cloud provider's instance pricing.

Serverless warehouses have **no VM costs**.

### Run-based usage

DBSQL also supports run-based usage if your warehouse has intermittent query patterns:

```
Hours/Month = (Runs Per Day x Avg Runtime Minutes / 60) x Days Per Month
```

## How costs are calculated

### DBU cost

```
DBU/Hour     = Warehouse Size DBU Map[size] x Number of Clusters
Monthly DBUs = DBU/Hour x Hours/Month
DBU Cost     = Monthly DBUs x $/DBU (from pricing tier)
```

### VM cost (Classic and Pro only)

```
VM Cost = (Driver Instance Count x Driver $/hr + Worker Instance Count x Worker $/hr) x Clusters x Hours/Month
```

VM instance counts are determined by the warehouse size configuration. Serverless has no VM costs.

### Total

```
Total = DBU Cost + VM Cost
```

### SKU mapping

| Warehouse Type | SKU | Fallback $/DBU |
|---------------|-----|----------------|
| Classic | `SQL_COMPUTE` | $0.22 |
| Pro | `SQL_PRO_COMPUTE` | $0.55 |
| Serverless | `SERVERLESS_SQL_COMPUTE` | $0.70 |

## Choosing a warehouse type

| Factor | Classic | Pro | Serverless |
|--------|---------|-----|------------|
| **Startup time** | Minutes | Minutes | Seconds |
| **Auto-scaling** | Manual config | Manual config | Automatic |
| **VM costs** | Yes | Yes | No |
| **$/DBU** | Lowest ($0.22) | Medium ($0.55) | Highest ($0.70) |
| **Management** | User-managed | User-managed | Fully managed |
| **Best for** | Cost-sensitive, predictable workloads | Advanced SQL features, materialized views | On-demand BI, variable or bursty workloads |

## Tips

- **Start small, scale up**: Begin with a Small warehouse (12 DBU/hr) and increase the size based on query performance and concurrency needs. Over-provisioning wastes DBUs.
- **Multi-cluster for concurrency, not speed**: Adding clusters helps when many users run queries simultaneously. It does not make individual queries faster -- increase warehouse size for that.
- **Serverless for intermittent use**: If your BI tool only runs queries during business hours with idle periods between, Serverless auto-scaling means you only pay during active queries. Classic/Pro charge for the full uptime window.
- **Pro vs Classic**: Pro adds features like materialized views and enhanced security. If you only need basic SQL analytics, Classic is significantly cheaper per DBU ($0.22 vs $0.55).

## Common mistakes

- **Comparing warehouse types by $/DBU alone**: Serverless has the highest $/DBU but zero VM costs and zero startup time. Compare total monthly cost, including VM estimates for Classic/Pro.
- **Setting too many clusters for low concurrency**: Each cluster multiplies the DBU rate. If you have fewer than 10 concurrent users, 1 cluster is usually sufficient.
- **Using 730 hours for a weekday-only dashboard**: If your team only uses dashboards during business hours (8 hrs x 22 days = 176 hrs), don't set 730 hours. The cost difference is 4x.
- **Ignoring VM costs on Classic/Pro**: The $/DBU rate is lower, but VM infrastructure adds significant cost. Always check the total, not just DBU cost.

## Excel export

Each DBSQL workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | Warehouse size and cluster count |
| Mode | Classic, Pro, or Serverless |
| SKU | `SQL_COMPUTE`, `SQL_PRO_COMPUTE`, or `SERVERLESS_SQL_COMPUTE` |
| DBU/Hour | Size DBU x clusters |
| Hours/Month | Direct value or run-based calculation |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | Classic/Pro: estimated infrastructure; Serverless: $0 |
| Total Cost | DBU Cost + VM Cost |
