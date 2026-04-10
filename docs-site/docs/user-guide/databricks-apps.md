---
sidebar_position: 16
---

# Databricks Apps

> **Lakemeter UI name:** Databricks Apps

Databricks Apps lets you deploy and run custom web applications (dashboards, data apps, internal tools) directly on Databricks infrastructure. Apps are fully serverless — you choose a size (Medium or Large) and Databricks handles provisioning. Costs are based on a fixed DBU/hour rate and app uptime.

## When to use Databricks Apps

Use Databricks Apps when you need to **host a custom web application** on Databricks — things like Streamlit dashboards, Gradio ML demos, FastAPI backends, or React frontends. If you need to run batch data processing, see [Jobs Compute](/user-guide/jobs-compute). If you need interactive notebook exploration, see [All-Purpose Compute](/user-guide/all-purpose-compute).

## Real-world example

> **Scenario:** You are deploying an internal cost estimation dashboard on AWS us-east-1 (Premium tier). The app runs during business hours — about 10 hours a day, 22 days a month. You need a Large app size to handle concurrent users.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Databricks Apps |
| App Size | Large |
| Hours Per Month | 220 (= 10 hrs × 22 days) |

### Step-by-step calculation

**1. DBU rate per hour**

Each app size has a fixed DBU/hour rate:

```
DBU/Hour = 1.0 (Large size)
```

**2. Monthly DBUs and cost**

```
Monthly DBUs = DBU/Hour × Hours/Month = 1.0 × 220 = 220 DBUs
DBU Cost     = 220 × $0.07/DBU = $15.40
Total Cost   = $15.40 (no VM costs — always serverless)
```

:::note
These are example rates for illustration. Actual $/DBU depends on your cloud, region, and pricing tier. The $0.07 rate is the fallback for the `ALL_PURPOSE_SERVERLESS_COMPUTE` SKU on AWS/us-east-1/Premium.
:::

### What about a Medium app?

For lighter workloads with fewer concurrent users:

```
DBU/Hour     = 0.5 (Medium size)
Monthly DBUs = 0.5 × 220 = 110 DBUs
Total Cost   = 110 × $0.07 = $7.70/month
```

### Always-on app (24/7)

If your app needs to be available around the clock:

```
DBU/Hour     = 1.0 (Large)
Monthly DBUs = 1.0 × 730 = 730 DBUs
Total Cost   = 730 × $0.07 = $51.10/month
```

## App sizes

| Size | DBU/Hour | Best for |
|------|----------|----------|
| **Medium** | 0.5 | Low-traffic dashboards, internal tools, dev/test apps |
| **Large** | 1.0 | Production apps, concurrent users, ML demos, heavier workloads |

Both sizes use the `ALL_PURPOSE_SERVERLESS_COMPUTE` SKU.

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **App Size** | Medium (0.5 DBU/hr) or Large (1.0 DBU/hr). Determines DBU consumption rate. | Medium |
| **Hours Per Month** | App uptime. Use 730 for 24/7 apps. | 730 |

### Estimating hours for intermittent usage

If your app only serves traffic during specific hours:

```
Hours/Month = Hours Per Day × Days Per Month
```

**Example**: Dashboard used 8 hours/day, 22 weekdays = 176 hours/month.

## How costs are calculated

```
DBU/Hour     = App Size Rate (0.5 for Medium, 1.0 for Large)
Monthly DBUs = DBU/Hour × Hours/Month
DBU Cost     = Monthly DBUs × $/DBU
Total Cost   = DBU Cost (no VM costs — always serverless)
```

Databricks Apps are **always serverless**. There are no VM infrastructure costs to estimate.

### SKU mapping

| Workload | SKU | Fallback $/DBU |
|----------|-----|----------------|
| Databricks Apps (all sizes) | `ALL_PURPOSE_SERVERLESS_COMPUTE` | $0.07 |

## Tips

- **Start with Medium**: Most internal dashboards and tools run fine on Medium. Only upgrade to Large if you see performance issues with concurrent users.
- **Right-size your hours**: If the app is only used during business hours, enter 176 (8 × 22) instead of 730. This cuts costs by ~76%.
- **Cross-cloud comparison**: Like all serverless workloads, the $/DBU rate varies by cloud and region. Create estimates for each cloud to compare.

## Common mistakes

- **Using 730 hours for business-only apps**: An internal dashboard used 9-to-5 doesn't need 24/7 uptime. Calculate your actual usage hours.
- **Choosing Large "just in case"**: Large costs exactly 2× Medium. Start with Medium and upgrade if needed.
- **Expecting VM costs**: Databricks Apps are always serverless. $0 in the VM Cost column is correct.

## Excel export

Each Databricks Apps workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | App size (Medium or Large) |
| Mode | Serverless (always) |
| SKU | `ALL_PURPOSE_SERVERLESS_COMPUTE` |
| DBU/Hour | 0.5 (Medium) or 1.0 (Large) |
| Hours/Month | Direct hours value |
| Monthly DBUs | DBU/Hour × Hours/Month |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost |
