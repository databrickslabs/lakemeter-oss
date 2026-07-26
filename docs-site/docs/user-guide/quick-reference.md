---
sidebar_position: 4
---

# Sizing Quick Reference

Use this page when reviewing an estimate. Workload-specific fields and formulas live in the [Workload Sizing Guides](./workloads), so they can change independently without making this reference stale.

## Build an estimate

1. **Set the deployment context.** Select the cloud, region, and pricing tier available for the scenario.
2. **Choose a workload.** Use the [workload catalog](./workloads) to match the billing pattern you need to size.
3. **Enter representative usage.** Model expected runs, runtime, active hours, capacity, tokens, pages, images, or storage.
4. **Inspect the breakdown.** Confirm the SKU, billing quantity, list rate, and separate infrastructure or storage components.
5. **Export and review.** Treat the result as a planning estimate and validate important assumptions with the current Databricks pricing information and your commercial terms.

## Common sizing quantities

| Quantity | How to use it |
|---|---|
| **Runs and runtime** | Estimate how often a workload executes and how long each execution consumes compute. |
| **Active hours** | Use the expected billable operating time, not the total hours in a month unless the workload is modeled as always on. |
| **Capacity** | Select the compute, endpoint, warehouse, or database capacity appropriate for the expected load. |
| **Scale-out count** | Include workers, clusters, endpoints, nodes, or apps that can consume capacity concurrently. |
| **Tokens or items** | Enter monthly input/output tokens, pages, images, or another workload-specific billing quantity. |
| **Storage** | Include persistent data and any separately modeled protection or overflow storage. |

## Key cost terms

| Term | Meaning in Lakemeter |
|---|---|
| **DBU** | A Databricks billing unit. Lakemeter multiplies estimated DBU consumption by the selected SKU's list rate. |
| **SKU** | The priced Databricks product entry used for a calculation. |
| **List rate** | The rate loaded for the selected SKU, cloud, region, and tier. |
| **Discount** | A planning adjustment applied to eligible list-rate costs. Confirm actual commercial terms separately. |
| **VM cost** | Cloud infrastructure cost shown separately for calculations where Lakemeter models it independently. |
| **Direct cost** | A cost calculated from a non-DBU billing quantity, such as an item quantity or a storage charge. |

## Review checklist

- Does the selected workload match the billing pattern being estimated?
- Are usage values monthly and in the units shown by the form?
- Does the scale-out count represent peak concurrency or average concurrency?
- Are always-on and scale-to-zero assumptions intentional?
- Are storage and data-protection quantities included where relevant?
- Does the expanded calculation show the expected SKU and billing unit?
- Have list rates and negotiated terms been checked before external use?

## Go deeper

- [Workload Sizing Guides](./workloads)
- [Calculation Reference](./calculation-reference)
- [SKU Explorer](./pricing/sku-explorer)
- [FMAPI Tokens](./pricing/fmapi-tokens)
- [Exporting to Excel](./exporting)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
