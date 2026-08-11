---
sidebar_position: 19
---

# AI Extract Sizing

> **Lakemeter UI name:** AI Extract

Use this guide to model monthly AI Extract consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not extraction capabilities, supported schemas, or product limits.

AI Extract consumes documents produced by `ai_parse_document`; it does not accept files directly. If the documents in this workload are not already parsed elsewhere in your estimate, add an AI Parse workload for the same volume so the estimate covers the full pipeline.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### Document Type

Select the option that best represents the documents in this workload entry. The selection determines the DBU conversion applied per thousand inputs; longer documents consume more DBUs per input.

Use the options and descriptions shown in Lakemeter. If the monthly volume spans materially different document lengths, create separate workload entries so each quantity uses the appropriate conversion. Select **Custom rate** to supply your own DBU-per-thousand-inputs conversion, for example from a measured pilot.

### Document Inputs/Month

Enter the expected number of documents processed per month as a raw count:

```text
Document Inputs/Month
  = Documents extracted per month
```

## How Lakemeter calculates cost

Lakemeter resolves the DBU-per-thousand-inputs conversion for the selected document type and the regional DBU price for the estimate context.

```text
Monthly DBUs
  = Document Inputs/Month ÷ 1,000
  × DBU per thousand inputs for the selected document type

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

The conversion and price values are intentionally not reproduced here because they can change. Review the values shown in Lakemeter and verify important estimates against current Databricks pricing.

## Related workloads

- **AI Parse** parses the source files into documents; extraction volume usually mirrors parse volume.
- **AI Classify** prices classification over the same parsed documents.
