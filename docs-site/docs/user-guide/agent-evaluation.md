---
sidebar_position: 22
---

# Agent Evaluation Sizing

> **Lakemeter UI name:** Agent Evaluation

Use this guide to model monthly Agent Evaluation consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not evaluation capabilities, judge configuration, or product limits.

Agent Evaluation service charges are additive. They cover the evaluation service itself and exclude the cost of running the application being evaluated. An evaluation run bills for the evaluation service and for every inference call the evaluated application makes, and only the first of those appears in this workload. Add a [Model Serving](./model-serving) or foundation model workload for the application under evaluation.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

Agent Evaluation bills two features independently. Each is enabled separately, and at least one must be enabled.

### Evaluation labels

Enabled by default. Bills the tokens the evaluation service consumes when producing labels. Input and output tokens convert at different rates, so enter them separately rather than as one combined figure:

- **Input Tokens/Month (millions)**: 2.143 DBUs per million tokens. Defaults to `1`.
- **Output Tokens/Month (millions)**: 8.571 DBUs per million tokens. Defaults to `1`.

Output tokens convert at about four times the rate of input tokens, so the output figure usually dominates the cost of this component.

### Synthetic data generation

Disabled by default. Bills per generated question:

- **Synthetic Questions/Month**: 5 DBUs per question. Defaults to `0`, and must be a whole number.

These DBU conversions are the values Lakemeter applies. They are anchored to the published Agent Evaluation per-unit prices at the US serverless real-time inference rate, so confirm them against current Databricks pricing before relying on an estimate.

## Expected monthly quantity

Estimate token volume from the evaluation runs you expect to perform:

```text
Input Tokens/Month (millions)
  = Evaluation runs per month
  × Questions per run
  × Average input tokens per evaluated question
  ÷ 1,000,000
```

For example, 20 evaluation runs of 500 questions each, at 2,000 input tokens per question, is 20 million input tokens per month, entered as `20`.

Keep separate workload entries for evaluation programs with materially different question sets or cadences, so each carries its own assumption.

## How Lakemeter calculates cost

Each enabled component is converted at its own rate and the workload total is the sum of the enabled components.

```text
Component monthly DBUs
  = Component quantity
  × DBUs per unit for that component

Workload monthly DBUs
  = Sum of enabled component DBUs

Monthly cost
  = Workload monthly DBUs
  × Regional price per DBU
```

All three components bill against the serverless real-time inference SKU. Lakemeter requires an exact rate for the estimate's cloud, region, and tier: if no rate exists for that combination the calculation is rejected rather than falling back to another region's rate.

Agent Evaluation requires the Premium or Enterprise tier. An estimate on the Standard tier is rejected.

The regional DBU price can change. Review the value shown in Lakemeter and verify important estimates against current Databricks pricing.

## Excel export

Each enabled component is exported as its own row, so evaluation-label tokens and synthetic questions can be reviewed independently. The exclusion note travels with the export, so a reviewer sees that the evaluated application's inference is not included.

## Related workloads

- **Model Serving**, **FMAPI Databricks**, and **FMAPI Proprietary** price the inference performed by the application under evaluation, which this estimate excludes.
- **Unity AI Gateway** is the other additive AI service workload, billed separately from the traffic it observes.
