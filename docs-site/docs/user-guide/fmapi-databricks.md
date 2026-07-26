---
sidebar_position: 13
---

# FMAPI — Databricks Models Sizing

> **Lakemeter UI name:** FMAPI - Databricks

Use this guide to model Databricks-hosted FMAPI consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not model capabilities, model selection, or serving architecture.

For current FMAPI capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rates shown in Lakemeter.

## What Lakemeter estimates

Each FMAPI - Databricks workload represents one model and one rate type. Lakemeter supports two calculation units:

- Millions of tokens per month for token-based rate types
- Hours per month for provisioned rate types

Add separate workload entries for separate usage quantities. For example, input and output tokens are separate line items.

## Configure the workload

### Model

Select the model used by the workload. The selected model, cloud, and rate type determine the usage conversion loaded by Lakemeter.

Use the model list shown in the app rather than relying on a static list in this guide.

### Rate Type

Select the rate type that matches the quantity being entered:

- **Input Token** or **Output Token** uses millions of tokens per month
- A **Provisioned** rate type uses hours per month

Only add rate types that apply to the workload. If multiple rate types apply, create one Lakemeter workload for each.

### Quantity

For a token-based rate type, enter monthly token volume in millions:

```text
Quantity = 1 means 1 million tokens per month
```

For a provisioned rate type, enter the number of provisioned hours in the month. The field label changes to **Hours/Month** when a provisioned rate type is selected.

## How token-based cost is calculated

```text
Monthly DBUs
  = Quantity in millions
  × DBU per 1 million tokens

Monthly cost
  = Monthly DBUs × Regional price per DBU
```

## How provisioned cost is calculated

```text
Monthly DBUs
  = Provisioned hours × DBU per hour

Monthly cost
  = Monthly DBUs × Regional price per DBU
```

Lakemeter resolves the usage conversion and DBU price for the selected model, rate type, cloud, region, and pricing tier. The expanded calculation shows whether the quantity is being interpreted as tokens or hours. No separate VM infrastructure cost is added.

## What to review before saving

- Is the selected model the one used by the workload?
- Is the rate type valid for that model?
- For token-based usage, is quantity entered in millions rather than raw tokens?
- For provisioned usage, is quantity entered as hours rather than tokens?
- Are all applicable token directions represented as separate workload entries?
- Does the expanded calculation show the expected DBU-per-token or DBU-per-hour conversion?
- Is the cloud, region, and pricing tier correct for the estimate?

## Common sizing errors

- Combining input and output token volumes into one line item
- Entering raw token count in a field measured in millions
- Entering token volume for a provisioned rate type
- Entering provisioned hours for a token-based rate type
- Assuming every model supports every rate type shown elsewhere
- Reusing a conversion from another model or an older pricing reference
- Expecting one line item to include all FMAPI usage automatically

## Excel export

Each FMAPI - Databricks workload emits one row.

For token-based rows, the export records the model, rate type, token quantity in millions, DBU per million tokens, monthly DBUs, and DBU cost. For provisioned rows, it records hours, DBU per hour, monthly DBUs, and DBU cost instead.

When reviewing the workbook, verify the row uses the formula for its selected rate type:

```text
Token-based row: Quantity in millions × DBU per million
Provisioned row: Hours × DBU per hour
```

The VM cost remains zero. Add the rows for all applicable rate types to obtain the complete FMAPI estimate.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
