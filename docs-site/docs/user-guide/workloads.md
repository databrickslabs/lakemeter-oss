---
sidebar_position: 4
---

# Workload Sizing Guides

Use this catalog to choose the Lakemeter form that matches the consumption you need to estimate. Each linked guide is the canonical source for that workload's sizing inputs, calculation behavior, and Excel export.

For current Databricks product capabilities and availability, refer to the [official Databricks documentation](https://docs.databricks.com/). These guides intentionally focus on how Lakemeter models cost.

![Adding a workload — select type, configure parameters, and save](/img/gifs/adding-workload.gif)
*Choose a workload type, enter its sizing assumptions, and save it to the estimate.*

## Compute and SQL

| What you need to size | Lakemeter guide | Main sizing inputs |
|---|---|---|
| Scheduled or triggered processing | [Lakeflow Jobs](./jobs-compute) | Compute shape, workers, runs, runtime |
| Interactive notebook compute | [All-Purpose Compute](./all-purpose-compute) | Compute shape, workers, active hours |
| Declarative data pipelines | [Lakeflow Spark Declarative Pipelines](./dlt-pipelines) | Compute mode, edition, workers, usage |
| SQL warehouses | [Databricks SQL](./dbsql-warehouses) | Warehouse type, size, clusters, hours |

## AI, ML, and data services

| What you need to size | Lakemeter guide | Main sizing inputs |
|---|---|---|
| Model inference endpoints | [Model Serving](./model-serving) | Endpoint type, endpoint count, hours |
| Vector indexing and search | [Vector Search](./vector-search) | Endpoint mode, vector capacity, storage, hours |
| Databricks-hosted foundation models | [FMAPI — Databricks](./fmapi-databricks) | Model, rate type, token volume or hours |
| Proprietary foundation models | [FMAPI — Proprietary](./fmapi-proprietary) | Provider, model, geography, context, token volume |
| Transactional database capacity | [Lakebase](./lakebase) | Compute range, usage, nodes, storage protection |
| Databricks-hosted applications | [Databricks Apps](./databricks-apps) | App size, app count, active hours |
| Document parsing | [AI Parse](./ai-parse) | Estimation mode, document complexity, page volume |
| Image generation | [Shutterstock ImageAI](./shutterstock-imageai) | Monthly image volume |

## Shared sizing principles

### Name the assumption

Use a workload name that identifies the scenario being modeled, not only the product. For example, `Nightly customer ingestion` is easier to review than `Jobs workload`.

### Model expected usage

Lakemeter may ask for run frequency and duration, active hours, capacity, storage, tokens, pages, or images. Use representative usage rather than maximum technical limits unless the estimate is intentionally modeling a peak case.

### Use the options shown in the app

Available clouds, regions, tiers, sizes, SKUs, and models can change. The current Lakemeter controls and pricing data determine what can be estimated. Check the [Databricks pricing page](https://www.databricks.com/product/pricing) and your commercial terms before using an estimate for a final purchasing decision.

### Review the breakdown

Expand each workload after saving it. Confirm the usage quantity, billing unit, selected SKU, rate, and any separate VM or storage components before exporting.

## Related tools

- [SKU Explorer](./pricing/sku-explorer) — inspect SKU list rates and model simple volume-based costs
- [FMAPI Tokens](./pricing/fmapi-tokens) — compare proprietary model token-rate combinations
- [Calculation Reference](./calculation-reference) — understand the calculation structure shared across workloads
- [Exporting to Excel](./exporting) — understand how sizing assumptions appear in the exported workbook
