---
sidebar_position: 18
---

# Shutterstock ImageAI Sizing

> **Lakemeter UI name:** Shutterstock ImageAI

Use this guide to model monthly Shutterstock ImageAI consumption in Lakemeter. It explains the estimator input and calculation behavior, not image-generation capabilities, usage guidance, or product limits.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form input

### Images/Month

Enter the expected number of image generations for one month. Use a whole-image count.

If different teams, environments, or scenarios need separate assumptions, create separate workload entries so their quantities remain visible in the estimate.

## Expected monthly quantity

The monthly quantity is the total expected image-generation count represented by the workload entry.

Estimate it from observed usage or a forecast:

```text
Images per month
  = Expected image generations per activity
  × Expected activities per month
```

Include every image generation that the estimate is intended to cover. Do not substitute the number of requests, users, or final retained assets unless it equals the expected billed image quantity.

## How Lakemeter calculates cost

Lakemeter applies its current DBU-per-image conversion and the regional DBU price for the estimate context.

```text
Monthly DBUs
  = Images per month
  × DBU per image

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

The conversion and price values are intentionally not reproduced here because they can change. Review the values shown in Lakemeter and verify important estimates against current Databricks pricing.

This Lakemeter workload model does not add a separate VM infrastructure charge.

## What to review before saving

- Does the image count represent expected monthly generations rather than only retained outputs?
- Is the quantity a whole-image count for the complete workload scope?
- Are materially different teams, environments, or scenarios modeled separately when useful?
- Does the estimate use the intended cloud, region, and pricing tier?
- Do the conversion and DBU price shown in Lakemeter match the current pricing source?

## Excel export

Each Shutterstock ImageAI workload is exported as one row. The configuration records the image count, while the cost fields include monthly DBUs, applicable DBU rates, and calculated list and discounted costs.

Use the exported configuration to trace the result back to the monthly image forecast. The VM cost fields remain zero because this Lakemeter workload model calculates the entry from DBU consumption only.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
