---
sidebar_position: 21
---

# Unity AI Gateway Sizing

> **Lakemeter UI name:** Unity AI Gateway

Use this guide to model monthly Unity AI Gateway consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not gateway capabilities, policy configuration, or product limits.

AI Gateway charges are additive. They are billed on top of the inference the gateway observes, so this workload prices the gateway features only. Add a [Model Serving](./model-serving) or foundation model workload for the underlying inference, and note that guardrail evaluator costs are also excluded.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

Inference Tables and Usage Tracking are billed independently. Each is enabled separately and carries its own inputs, so one workload entry can model either feature or both. At least one must be enabled.

### Inference Tables and Usage Tracking

Both features are enabled by default and both convert payload at 1.429 DBUs per GB.

- **Inference Tables**: logs request and response payloads to a Delta table.
- **Usage Tracking**: records usage metadata for the traffic passing through the gateway.

Enable only the features the workload actually uses. A feature that is turned off contributes nothing to the estimate.

### Input method

Each enabled feature takes its monthly volume one of two ways:

- **Requests**: derives billable payload from request volume and average payload sizes. Use this when you know traffic shape but not metered payload.
- **Direct payload GB**: takes the monthly billable payload as given. Prefer this when the metered payload is already known, because it removes the payload-size assumption from the estimate.

### Requests/Month (millions)

Monthly request volume in millions, for the requests input method. Defaults to `1`.

### Avg Request Payload (KB) and Avg Response Payload (KB)

Average request and response payload sizes in kilobytes. Both default to `1`. Request and response payloads are both billable, so both values are required for the requests input method.

### Monthly Payload (GB)

Total monthly billable payload in gigabytes, for the direct payload GB input method. Defaults to `2`.

## Expected monthly quantity

For the requests input method, payload is derived from request volume:

```text
Monthly payload (GB)
  = Requests/Month (millions)
  × (Avg Request Payload KB + Avg Response Payload KB)
```

Requests in millions multiplied by kilobytes per request gives gigabytes directly, so no further conversion is applied. For example, 2 million requests at 1 KB request and 3 KB response is 8 GB per month.

If traffic splits into groups with materially different payload sizes, create separate workload entries so each group carries its own assumption.

## How Lakemeter calculates cost

Each enabled feature is converted independently and the workload total is the sum of the enabled features.

```text
Feature monthly DBUs
  = Monthly payload (GB)
  × 1.429 DBUs per GB

Workload monthly DBUs
  = Sum of enabled feature DBUs

Monthly cost
  = Workload monthly DBUs
  × Regional price per DBU
```

Both features bill against the serverless real-time inference SKU. Lakemeter requires an exact rate for the estimate's cloud, region, and tier: if no rate exists for that combination the calculation is rejected rather than falling back to another region's rate.

The regional DBU price can change. Review the value shown in Lakemeter and verify important estimates against current Databricks pricing.

## Excel export

Each enabled feature is exported as its own row, so Inference Tables and Usage Tracking can be reviewed and adjusted independently. The configuration column records each feature's payload and DBU values, and the exclusion note travels with the export so a reviewer sees that the underlying inference is not included.

## Related workloads

- **Model Serving** and the foundation model guides price the inference the gateway observes, which this estimate excludes.
- **Agent Evaluation** is the other additive AI service workload, billed separately from the application it measures.
