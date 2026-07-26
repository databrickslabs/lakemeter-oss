---
sidebar_position: 15
---

# FMAPI — Proprietary Models Sizing

> **Lakemeter UI name:** FMAPI - Proprietary

Use this guide to model proprietary FMAPI token consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not provider capabilities, model selection, endpoint routing, or context-window limits.

For current FMAPI capabilities and availability, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing). To inspect the proprietary FMAPI rates loaded by Lakemeter, use [FMAPI Token Pricing](./pricing/fmapi-tokens).

## What Lakemeter estimates

Each FMAPI - Proprietary workload represents one selected provider, model, endpoint type, context length, rate type, and monthly token quantity.

Each rate type is a separate line item. Add one workload entry for every usage category that applies, such as input, output, cache read, or cache write when those choices are available for the selected configuration.

## Configure the rate combination

### Provider and Model

Select the provider first, then select the model. Lakemeter uses both values when resolving the rate.

Use the provider and model options shown in Lakemeter rather than a static inventory in this guide.

### Endpoint Type

Select the endpoint type used by the workload. This is part of the pricing key, so changing it can select a different DBU-per-token conversion.

Use the official Databricks documentation to validate routing and residency requirements. This guide does not recommend one endpoint type over another.

### Context Length

Select the context-length category that matches the requests being sized. Lakemeter filters the available values from its loaded pricing data and includes the selection in the rate lookup.

### Rate Type

Select the usage category represented by this line item. The available choices depend on the selected provider, model, endpoint type, and context length.

Create separate entries for each applicable rate type. Do not combine multiple token categories into one quantity.

### Quantity (M tokens/month)

Enter the monthly quantity in millions of tokens:

```text
Quantity = 1 means 1 million tokens per month
```

Derive each quantity from the usage data for its matching rate type.

## How cost is calculated

Lakemeter resolves a DBU-per-million-token conversion from the full selected combination:

```text
Rate lookup key
  = Cloud
  + Provider
  + Model
  + Endpoint type
  + Context length
  + Rate type

Monthly DBUs
  = Quantity in millions
  × DBU per 1 million tokens

Monthly cost
  = Monthly DBUs × Selected SKU price per DBU
```

No separate VM infrastructure cost is added. If a discount is configured for the applicable SKU, Lakemeter also shows the discounted DBU cost.

Use [FMAPI Token Pricing](./pricing/fmapi-tokens) to inspect the loaded rate combinations rather than copying rates into an estimate from this guide.

## What to review before saving

- Is the provider and model combination correct?
- Does the endpoint type match the requests being sized?
- Does the context-length category match the selected model and traffic?
- Is the rate type the usage category represented by this quantity?
- Is quantity entered in millions rather than raw tokens?
- Are all applicable token categories represented as separate workload entries?
- Does the expanded calculation resolve the expected SKU and DBU-per-million conversion?
- Is the cloud, region, and pricing tier correct for the estimate?

## Common sizing errors

- Combining input, output, and cache quantities into one line item
- Entering raw token count in a field measured in millions
- Reusing the same quantity for every rate type without measuring each category
- Changing the model without rechecking endpoint type and context length
- Assuming a rate type is available because another model exposes it
- Copying an exact rate from an older document instead of inspecting Lakemeter's loaded pricing
- Comparing providers or models without holding the expected usage quantities and configuration constant

## Excel export

Each FMAPI - Proprietary workload emits one row. The row includes the model, rate type, token quantity in millions, DBU per million tokens, monthly DBUs, provider-specific SKU rate, and list and discounted DBU costs. The selected endpoint type and context length participate in the rate lookup but are not repeated as dedicated export columns.

The export formula is:

```text
Monthly DBUs
  = Tokens per month in millions × DBU per million tokens

DBU cost
  = Monthly DBUs × Selected SKU price per DBU
```

The VM cost remains zero. Add the exported rows for all applicable rate types to obtain the complete proprietary FMAPI estimate.

## Related

- [FMAPI Token Pricing](./pricing/fmapi-tokens)
- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
