---
sidebar_position: 12
---

# Model Serving Sizing

> **Lakemeter UI name:** Model Serving

Use this guide to model Model Serving consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not model deployment, endpoint capabilities, or hardware selection.

For current Model Serving capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

A Model Serving workload combines:

- The DBU-per-hour rate for the selected endpoint type
- A scale-out concurrency multiplier
- Active hours per month

Lakemeter models this as serverless DBU consumption. It does not add separate VM infrastructure cost.

## Configure the endpoint

### Endpoint Type

Select the endpoint type planned for the workload. Lakemeter loads the corresponding base DBU-per-hour rate for the estimate's cloud.

Use the options and rates shown in Lakemeter rather than copying an endpoint inventory from this guide. Use the official Databricks documentation to validate that the selected endpoint type fits the deployment.

### Compute Scale-Out

Select a scale-out preset or choose **Custom**. Each preset resolves to the concurrency displayed by Lakemeter. With **Custom**, enter the concurrency directly using the increments accepted by the form.

Concurrency is a cost multiplier in the estimate; it is not informational metadata.

### Hours/Month

Enter the number of hours the endpoint is expected to be active during the month. This is a direct monthly input, so derive it from the planned endpoint schedule rather than request count alone.

## How cost is calculated

Lakemeter resolves the endpoint's base DBU-per-hour rate, the selected concurrency, and the regional DBU price:

```text
Effective DBU per hour
  = Endpoint DBU per hour × Concurrency

Monthly DBUs
  = Effective DBU per hour × Hours per month

Monthly DBU cost
  = Monthly DBUs × Regional price per DBU
```

The expanded calculation shows this chain so the endpoint rate, concurrency multiplier, hours, DBUs, and price can be checked independently. If a discount is configured, Lakemeter also applies it to the relevant DBU cost.

## What to review before saving

- Does the endpoint type match the deployment being sized?
- Does the selected scale-out resolve to the intended concurrency?
- If using **Custom**, is the concurrency within the form's accepted range and increment?
- Do hours represent endpoint-active time for the month?
- Does the expanded calculation show the expected base rate and concurrency multiplier?
- Is the cloud, region, and pricing tier correct for the estimate?

## Common sizing errors

- Treating scale-out as a label instead of a multiplier
- Entering request count or inference duration in the hours field without converting it to endpoint-active hours
- Using an always-on monthly schedule for an endpoint that is only active during a limited window
- Multiplying the estimate again outside Lakemeter for concurrency that is already included
- Assuming a rate from another cloud or an older endpoint inventory
- Expecting a separate VM charge in addition to the serverless DBU cost

## Excel export

Each Model Serving workload emits one compute row. The row includes the selected endpoint type, scale-out and concurrency, hours per month, effective DBU per hour, monthly DBUs, selected SKU rate, and list and discounted DBU costs.

The VM cost remains zero because the workload is modeled as serverless. The total for the row is the DBU cost after any configured discount.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
