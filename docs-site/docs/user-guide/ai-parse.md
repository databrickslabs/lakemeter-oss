---
sidebar_position: 17
---

# AI Parse Sizing

> **Lakemeter UI name:** AI Parse

Use this guide to model monthly AI Parse page-processing consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not document-processing capabilities, supported formats, or product limits.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### Complexity

Select the complexity option that represents the pages in this workload entry. The selection determines the DBU conversion applied per thousand pages.

Use the options and descriptions shown in Lakemeter. If the monthly volume spans materially different complexity levels, create separate workload entries so each quantity uses the appropriate conversion.

### Pages/Month (thousands)

Enter the expected monthly page-processing quantity in thousands of pages, not the raw page count.

```text
Pages/Month (thousands)
  = Expected pages processed per month
  ÷ 1,000
```

For example, a forecast of 50,000 pages is entered as `50`.

## Expected monthly quantity

The monthly quantity is the total number of pages expected to be processed, expressed in thousands. Estimate it from observed page volume or from forecast document volume:

```text
Expected pages per month
  = Documents processed per month
  × Average pages per document
```

Include all page-processing volume that the estimate is intended to cover. Keep separate entries for groups that use different complexity selections.

## How Lakemeter calculates cost

Lakemeter resolves the DBU-per-thousand-pages conversion for the selected complexity and the regional DBU price for the estimate context.

```text
Monthly DBUs
  = Pages/Month (thousands)
  × DBU per thousand pages for the selected complexity

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

The conversion and price values are intentionally not reproduced here because they can change. Review the values shown in Lakemeter and verify important estimates against current Databricks pricing.

This Lakemeter workload model does not add a separate VM infrastructure charge.

## What to review before saving

- Is the quantity entered in thousands of pages rather than individual pages?
- Is the page forecast based on total pages, not only document count?
- Does the selected complexity match the option intended for this page group?
- Are page groups with different complexity assumptions modeled separately?
- Does the estimate use the intended cloud, region, and pricing tier?
- Do the conversion and DBU price shown in Lakemeter match the current pricing source?

## Excel export

Each AI Parse workload is exported as one row. The configuration records the selected complexity and page quantity, while the cost fields include monthly DBUs, applicable DBU rates, and calculated list and discounted costs.

Use separate exported rows to review page groups with different complexity assumptions. The VM cost fields remain zero because this Lakemeter workload model calculates the entry from DBU consumption only.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
