---
sidebar_position: 1
---

# SKU Explorer

Use **Pricing > SKU Explorer** to inspect the SKU list rates loaded in Lakemeter and model simple daily, monthly, and annual cost scenarios.

This page is a pricing aid, not a replacement for a workload estimate. Use the [Workload Sizing Guides](../workloads) when you need workload-specific assumptions and an exportable estimate.

For current public pricing and commercial guidance, refer to the [Databricks pricing page](https://www.databricks.com/product/pricing).

## Select the pricing context

Choose the context you want to inspect:

- **Cloud**
- **Region**
- **Tier**
- **Discount %**
- **USD to local FX**

Lakemeter displays only the combinations available in its loaded pricing data. Changing the cloud can also change the region and tier options.

## Understand the rate columns

| Column | Meaning |
|---|---|
| **List rate** | Loaded rate after applying the optional FX multiplier |
| **Discount** | Planning discount entered for that row |
| **Net rate** | List rate after the planning discount |
| **Volume** | Daily billing quantity entered for the scenario |
| **Daily cost** | Net rate multiplied by the daily quantity |
| **Monthly cost** | Daily modeled cost extended to a 30-day month |

Some storage and networking rows do not accept the standard discount input. Lakemeter marks these rows as not applicable rather than applying the default discount.

## Enter volume assumptions

Most SKU rows accept a daily DBU quantity. Enter the expected DBUs per day to see the resulting daily, monthly, and annual planning cost.

Lakebase compute is entered as CU in this view. Lakemeter converts the entered capacity to a daily DBU quantity before applying the selected list rate. For a full minimum-versus-scale-up estimate, use the [Lakebase Sizing](../lakebase) workload instead.

The sticky summary appears after a non-zero volume is entered and aggregates the modeled daily, monthly, and annual values.

## Simple and Advanced views

### Simple

Use **Simple** to compare the base SKU rows grouped by:

- Compute
- SQL
- Data Engineering
- AI/ML
- Database
- Storage & Networking

### Advanced

Use **Advanced** to expand SKUs that have feature multipliers in the Lakemeter pricing data. Enter quantities on the relevant expanded rows when the estimate depends on a feature-specific rate.

The expanded rows are driven by the loaded data. This documentation intentionally does not reproduce their names or multipliers.

## Use discounts and FX

The default discount is applied to eligible rows. You can override it for an individual SKU.

The **USD to local FX** value multiplies displayed rates and costs:

```text
Displayed list rate = USD list rate × FX
Net rate = Displayed list rate × (1 − Discount percentage)
```

An FX value of `1` displays USD list pricing. The FX input is a modeling convenience; Lakemeter does not retrieve live foreign-exchange rates.

## Copy prices

Select **Copy Prices** to copy the current SKU table as tab-separated text. The copied data includes:

- Pricing context
- Product group and name
- Variant
- List rate
- Discount
- Net rate
- Billing unit

Paste the result into a spreadsheet or planning document. Volume and cost totals are not included in the copied rate table.

## Review checklist

- Is the cloud, region, and tier correct?
- Is the FX value intentional?
- Does the discount reflect a planning assumption rather than an unverified contract term?
- Is volume entered in the unit shown beside the field?
- Is a full workload estimate needed instead of a simple rate comparison?

## Related

- [FMAPI Tokens](./fmapi-tokens)
- [Workload Sizing Guides](../workloads)
- [Calculation Reference](../calculation-reference)
- [Lakebase Sizing](../lakebase)
- [Databricks pricing](https://www.databricks.com/product/pricing)
