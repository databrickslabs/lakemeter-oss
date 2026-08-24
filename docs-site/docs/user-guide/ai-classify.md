---
sidebar_position: 20
---

# AI Classify Sizing

> **Lakemeter UI name:** AI Classify

Use this guide to model monthly AI Classify consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not classification capabilities, label design, or product limits.

AI Classify accepts raw `STRING` inputs directly. It does not accept document files directly: pass files through `ai_parse_document` first, then use the parsed output. Add an AI Parse workload for file-based volume so the estimate covers the full pipeline.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### Document Type

Select the option that best represents the inputs in this workload entry. Lakemeter uses the midpoint of the published planning range:

- **Short text** — news brief; 3–6 DBUs per 1,000 inputs (4.5 midpoint).
- **Rental contracts** — contracts of about 7–10 pages; 40–60 DBUs per 1,000 inputs (50 midpoint).
- **Custom rate** — a positive DBU-per-thousand-inputs value from a measured pilot.

If the monthly volume spans materially different input shapes, create separate workload entries so each quantity uses the appropriate conversion.

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

The regional DBU price can change. Review the value shown in Lakemeter and verify important estimates against current Databricks pricing.

## Related workloads

- **AI Parse** parses source files before classification; raw `STRING` inputs do not need it.
- **AI Extract** prices structured field extraction over the same parsed documents.
