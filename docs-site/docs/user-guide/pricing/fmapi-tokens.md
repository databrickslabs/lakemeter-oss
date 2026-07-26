---
sidebar_position: 2
---

# FMAPI Tokens

Use **Pricing > FMAPI Tokens** to compare proprietary Foundation Model API rate combinations loaded in Lakemeter.

The view helps identify the correct model, geography, context-length, and token-rate assumptions before creating FMAPI workload lines. It does not determine how many tokens an application will use.

Model availability and rates change. Use the values shown in Lakemeter for planning and validate current product guidance in the [official Databricks documentation](https://docs.databricks.com/) and current public pricing on the [Databricks pricing page](https://www.databricks.com/product/pricing).

![FMAPI Tokens pricing view](/img/guides/fmapi-token-pricing.png)
*Filter proprietary model rates and display them as DBUs or estimated currency values.*

## Choose a display mode

### DBU

The **DBU** view shows the source billing rates without applying a regional price per DBU:

- Token rates are displayed in DBUs per one million tokens.
- Batch inference rates are displayed in DBUs per hour.

Use this mode to compare relative consumption across model and rate combinations.

### Currency

The **$** view converts DBU rates to estimated currency values using the selected cloud, region, tier, discount, and FX assumptions:

```text
Displayed token rate
  = DBUs per billing unit
  × Regional price per DBU
  × (1 − Discount percentage)
  × FX
```

The dollar view shows Global and In-geo values side by side when both are available.

## Filter the rate matrix

Use the filters to narrow the table:

| Filter | Sizing use |
|---|---|
| **Cloud** | Select the cloud context for the rate |
| **Region** | Select the regional price per DBU used in currency mode |
| **Tier** | Select the pricing tier used in currency mode |
| **Family** | Limit the table to a model provider or family |
| **Model contains** | Search within available model identifiers |
| **Geo** | Filter the geography in DBU mode |
| **Context length** | Select the context-rate category |
| **Discount %** | Apply a planning discount in currency mode |
| **USD to local FX** | Shared Pricing-page control that converts displayed dollar values with a manually supplied multiplier |

The controls change with the selected display mode because the DBU view compares source token rates, while currency mode also needs a regional DBU price. The FX input remains in the Pricing page header and applies across both Pricing tabs.

## Read the table

The table separates model context from billable rate types.

### Model context

- Cloud
- Family
- Model
- Geography, where shown
- Context-length category

### Token and batch rates

- Input tokens
- Output tokens
- Cache writes
- Cache reads
- Batch inference

A dash means Lakemeter does not have a published rate for that combination. Do not treat a dash as a zero-cost rate.

## Turn a rate into a sizing assumption

For token-based usage:

```text
Monthly DBUs
  = Monthly tokens in millions
  × DBUs per one million tokens
```

For batch inference:

```text
Monthly DBUs
  = Batch hours
  × DBUs per hour
```

Create separate FMAPI workload lines for separately billed rate types such as input tokens, output tokens, cache reads, or cache writes. The [FMAPI — Proprietary sizing guide](../fmapi-proprietary) explains how those quantities are entered in an estimate.

## Review checklist

- Is the model identifier correct?
- Does the geography match the planned serving option?
- Is the context-length category appropriate?
- Are input, output, cache, and batch quantities modeled separately?
- In currency mode, are region, tier, discount, and FX correct?
- Have missing rates been treated as unavailable rather than free?

## Related

- [FMAPI — Proprietary sizing](../fmapi-proprietary)
- [SKU Explorer](./sku-explorer)
- [Calculation Reference](../calculation-reference)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
