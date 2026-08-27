---
sidebar_position: 23
---

# AI Runtime Sizing

> **Lakemeter UI name:** AI Runtime

Use this guide to model monthly AI Runtime serverless GPU model-training consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not training capabilities, framework support, or product limits.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Cloud availability

Lakemeter offers AI Runtime on AWS and Azure. The form does not offer GCP: Lakemeter prices this workload from per-cloud accelerator rates and does not substitute another cloud's rate when one is unavailable.

Accelerator rates also differ between AWS and Azure, so changing the estimate's cloud can change the cost of an otherwise unchanged workload.

## Form inputs

### Accelerator

Select the GPU configuration for the training workload. Defaults to `1x A10 (24 GB)`. Rates are DBUs per GPU-hour and differ by cloud:

- **1x A10 (24 GB)**: 1 GPU. About 3.85 DBUs per GPU-hour on AWS, about 7.54 on Azure.
- **1x H100 (80 GB)**: 1 GPU. About 10.77 DBUs per GPU-hour on both clouds.
- **8x H100 (640 GB total)**: 8 GPUs. Same per-GPU rate as the single H100.

These conversions are the values Lakemeter applies. They are anchored to the published AI Runtime GPU-hour prices at the `MODEL_TRAINING` SKU rate in the reference US regions, so confirm them against current Databricks pricing before relying on an estimate.

The multi-GPU option bills per GPU, so an 8x H100 node consumes eight times the GPU-hours of a single H100 for the same runtime, and costs roughly eight times as much.

### Monthly runtime

Runtime is entered one of two ways, matching the other compute workloads:

- **Direct active hours**: enter Hours/Month and Lakemeter uses it as given.
- **Run-based**: enter Runs/Day, Avg Runtime (minutes), and Days/Month.

When Hours/Month is supplied it takes precedence. Otherwise runtime is derived from the run-based inputs, with Days/Month defaulting to 22.

## Expected monthly quantity

```text
Monthly runtime hours
  = Runs/Day
  × (Avg Runtime minutes ÷ 60)
  × Days/Month
```

Enter node runtime, not GPU-hours. Lakemeter derives GPU-hours from the accelerator's GPU count, so this figure should be the wall-clock time the training node is active. For example, a nightly two-hour fine-tune on 22 working days is 44 hours per month, which on an 8x H100 node is 352 GPU-hours.

## How Lakemeter calculates cost

```text
Monthly GPU-hours
  = Monthly runtime hours
  × GPUs per node

DBUs per node-hour
  = GPUs per node
  × DBUs per GPU-hour for the accelerator and cloud

Monthly DBUs
  = Monthly runtime hours
  × DBUs per node-hour

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

AI Runtime bills against the `MODEL_TRAINING` SKU, which is separate from the serverless real-time inference SKU used by the inference and AI service workloads. Lakemeter requires an exact rate for the estimate's cloud, region, and tier: if no rate exists for that combination the calculation is rejected rather than falling back to another region's rate.

AI Runtime requires the Premium or Enterprise tier. An estimate on the Standard tier is rejected.

The regional DBU price can change. Review the value shown in Lakemeter and verify important estimates against current Databricks pricing.

## Related workloads

- **Model Serving** prices serving a trained model, which is billed separately from training it.
- **Jobs Compute** prices training that runs on classic or serverless job compute rather than the AI Runtime serverless GPU service.
