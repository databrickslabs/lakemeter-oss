---
sidebar_position: 20
---

# AI Classify Sizing

> **Lakemeter UI name:** AI Classify

Use this guide to model monthly AI Classify consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not classification capabilities, label design, or product limits.

AI Classify consumes documents produced by `ai_parse_document`; it does not accept files directly. If the documents in this workload are not already parsed elsewhere in your estimate, add an AI Parse workload for the same volume so the estimate covers the full pipeline.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### Document Type

Select the option that best represents the documents in this workload entry. The selection determines the DBU conversion applied per thousand documents; longer documents consume more DBUs per classification.

Use the options and descriptions shown in Lakemeter. If the monthly volume spans materially different document lengths, create separate workload entries so each quantity uses the appropriate conversion. Select **Custom rate** to supply your own DBU-per-thousand-documents conversion, for example from a measured pilot.

### Documents/Month

Enter the expected number of documents classified per month as a raw count:

```text
Documents/Month
  = Documents classified per month
```

## How Lakemeter calculates cost

Lakemeter resolves the DBU-per-thousand-documents conversion for the selected document type and the regional DBU price for the estimate context.

```text
Monthly DBUs
  = Documents/Month ÷ 1,000
  × DBU per thousand documents for the selected document type

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

The conversion and price values are intentionally not reproduced here because they can change. Review the values shown in Lakemeter and verify important estimates against current Databricks pricing.

## Related workloads

- **AI Parse** parses the source files into documents; classification volume usually mirrors parse volume.
- **AI Extract** prices structured field extraction over the same parsed documents.
