---
sidebar_position: 19
---

# AI Extract Sizing

> **Lakemeter UI name:** AI Extract

Use this guide to model monthly AI Extract consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not extraction capabilities, supported schemas, or product limits.

AI Extract accepts raw `STRING` inputs directly. It does not accept document files directly: pass files through `ai_parse_document` first, then use the parsed output. Add an AI Parse workload for file-based volume so the estimate covers the full pipeline.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### Document Type

Select the option that best represents the inputs in this workload entry. Lakemeter uses the midpoint of the published planning range:

- **Short text** — receipt with a few fields; 30–60 DBUs per 1,000 inputs (45 midpoint).
- **Invoices** — typical invoice or purchase order, about one page; 30–60 DBUs per 1,000 inputs (45 midpoint).
- **Complex reasoning (Precision Mode)** — reasoning-heavy fields from dense text; 400–725 DBUs per 1,000 inputs (562.5 midpoint).
- **Deep nesting (Precision Mode)** — deeply nested schemas from long, complex documents; 375–700 DBUs per 1,000 inputs (537.5 midpoint).
- **Custom rate** — a positive DBU-per-thousand-inputs value from a measured pilot.

If the monthly volume spans materially different input shapes, create separate workload entries so each quantity uses the appropriate conversion.

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

The regional DBU price can change. Review the value shown in Lakemeter and verify important estimates against current Databricks pricing.

## Related workloads

- **AI Parse** parses source files before extraction; raw `STRING` inputs do not need it.
- **AI Classify** prices classification over the same parsed documents.
