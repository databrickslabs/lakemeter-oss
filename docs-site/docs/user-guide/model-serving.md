---
sidebar_position: 12
---

# Model Serving

> **Lakemeter UI name:** Model Serving

Model Serving provides fully managed, real-time inference endpoints for deploying ML models at scale. You select a GPU type, and Databricks handles provisioning, scaling, and infrastructure. Costs are based on the GPU type's DBU rate and endpoint uptime.

![Model Serving documentation page](/img/guides/model-serving-guide.png)
*The Model Serving guide — GPU selection, DBU rates, and real-world cost example for inference endpoints.*

![Model Serving worked cost example](/img/guides/model-serving-worked-example.png)
*Worked example showing GPU type comparison and monthly cost calculation.*

## When to use Model Serving

Use Model Serving when you need to **deploy a custom ML model** (fine-tuned LLM, classification model, recommendation engine) as a REST API endpoint. If you want to call pre-built foundation models (Llama, Claude, GPT) without deploying your own endpoint, see [FMAPI — Databricks Models](/user-guide/fmapi-databricks) or [FMAPI — Proprietary Models](/user-guide/fmapi-proprietary) instead.

## Real-world example

> **Scenario:** You are deploying a fine-tuned text classification model on AWS us-east-1 (Premium tier). The model needs a single A10G GPU and serves requests during business hours -- about 8 hours a day, 22 days a month. You want to estimate the monthly cost.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Model Serving |
| GPU Type | Medium (A10G 1x) |
| Hours Per Month | 176 (= 8 hrs x 22 days) |

### Step-by-step calculation

**1. DBU rate per hour**

Each GPU type has a fixed DBU/hour rate that varies by cloud. For Medium (A10G 1x) on AWS:

```
DBU/Hour = 20.0 (from pricing bundle)
```

**2. Monthly DBUs and cost**

```
Monthly DBUs = DBU/Hour x Hours/Month = 20.0 x 176 = 3,520 DBUs
DBU Cost     = 3,520 x $0.07/DBU = $246.40
Total Cost   = $246.40 (no VM costs — always serverless)
```

:::note
These are example rates for illustration. Actual $/DBU depends on your cloud, region, and pricing tier. The $0.07 rate is the fallback for the `SERVERLESS_REAL_TIME_INFERENCE` SKU on AWS/us-east-1/Premium.
:::

### What about a smaller GPU?

If a CPU endpoint is sufficient (for lightweight models):

```
DBU/Hour     = 1.0 (CPU rate on AWS)
Monthly DBUs = 1.0 x 176 = 176 DBUs
Total Cost   = 176 x $0.07 = $12.32/month
```

Or a GPU Small (T4) for moderate inference:

```
DBU/Hour     = 10.48 (T4 rate on AWS)
Monthly DBUs = 10.48 x 176 = 1,844.48 DBUs
Total Cost   = 1,844.48 x $0.07 = $129.11/month
```

## GPU types

Model Serving supports 14 GPU configurations. Each has a cloud-specific DBU/hour rate:

| GPU Type | Display Name | Typical use case |
|----------|-------------|-----------------|
| `cpu` | CPU | Light inference, small models, testing |
| `gpu_small_t4` | Small (T4) | Cost-effective inference, small-medium models |
| `gpu_medium_a10g_1x` | Medium (A10G 1x) | General-purpose inference |
| `gpu_medium_a10g_4x` | Medium (A10G 4x) | Medium models, higher throughput |
| `gpu_medium_a10g_8x` | Medium (A10G 8x) | Large models on A10G |
| `gpu_large_a10g_4x` | Large (A10G 4x) | High-throughput inference |
| `gpu_medium_a100_1x` | Medium (A100 1x) | Large models, high performance |
| `gpu_large_a100_2x` | Large (A100 2x) | Very large models |
| `gpu_xlarge_a100_40gb_8x` | XLarge (A100 40GB 8x) | LLM inference, maximum A100 40GB |
| `gpu_xlarge_a100_80gb_1x` | XLarge (A100 80GB 1x) | Single high-memory GPU |
| `gpu_xlarge_a100_80gb_8x` | XLarge (A100 80GB 8x) | Maximum compute, largest models |
| `gpu_2xlarge_a100_80gb_2x` | 2XLarge (A100 80GB 2x) | Multi-GPU high-memory |
| `gpu_4xlarge_a100_80gb_4x` | 4XLarge (A100 80GB 4x) | Extreme compute requirements |
| `gpu_medium_g2_standard_8` | Medium (G2 Standard 8) | GCP-specific GPU option |

:::tip
DBU rates vary by cloud provider. The same GPU type may have a different DBU/hour on AWS vs Azure vs GCP. Lakemeter automatically loads the correct rates for your selected cloud.
:::

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **GPU Type** | The GPU configuration for the endpoint. Determines DBU/hour rate. | CPU |
| **Number of Endpoints** | Number of identical serving endpoints. This field is visible in the UI for planning purposes but does not multiply the cost calculation — each endpoint should be added as a separate workload entry if you need to estimate multiple endpoints. | 1 |
| **Hours Per Month** | Endpoint uptime. Use 730 for 24/7 endpoints. | 730 |

### Estimating hours for intermittent usage

Model Serving uses direct hours input only. If your endpoint serves intermittent batch requests rather than continuous traffic, calculate your hours manually:

```
Hours/Month = (Batches Per Day x Avg Duration Minutes / 60) x Days Per Month
```

**Example**: 100 inference batches/day x 2 min each x 22 days = 73.3 hours/month — enter **73** in the Hours/Month field.

## How costs are calculated

```
DBU/Hour     = GPU Rate Lookup[cloud:gpu_type]
Monthly DBUs = DBU/Hour x Hours/Month
DBU Cost     = Monthly DBUs x $/DBU
Total Cost   = DBU Cost (no VM costs — always serverless)
```

Model Serving is **always serverless**. There are no VM infrastructure costs to estimate.

### Fallback behavior

If a GPU type is not found in the pricing bundle for your selected cloud:
- **Frontend**: Uses 2 DBU/hour as a default so you still see a non-zero estimate
- **Backend**: Uses 0 DBU/hour, which produces $0 in the Excel export

This difference is by design -- the frontend provides a UX-friendly default, while the backend avoids generating incorrect export data for unknown GPU types.

### SKU mapping

| Workload | SKU | Fallback $/DBU |
|----------|-----|----------------|
| Model Serving (all GPU types) | `SERVERLESS_REAL_TIME_INFERENCE` | $0.07 |

## Tips

- **Start with CPU for testing**: CPU endpoints cost ~$0.07/hr in DBUs and are ideal for validating your model deployment before scaling to GPU.
- **Match GPU to model size**: Small models (< 1B parameters) run well on T4. Medium models (1-7B) need A10G. Large models (7B+) require A100. Over-provisioning wastes money.
- **24/7 vs on-demand**: If your endpoint serves real-time traffic, 730 hours is correct. If it only handles batch inference during business hours, enter 176 hours to avoid paying for idle time.
- **Cross-cloud comparison**: GPU rates differ by cloud. Create duplicate estimates for each cloud to compare -- a T4 on AWS may cost differently than on Azure.

## Common mistakes

- **Choosing the largest GPU "just in case"**: A100 80GB 8x costs hundreds of DBUs/hour. Start with the smallest GPU that meets your latency and throughput requirements, then scale up if needed.
- **Overestimating hours for intermittent usage**: If your model serves 100 requests/day taking 2 minutes each, that is only ~73 hours/month -- not 730. Calculate your actual usage hours and enter them directly. Using 730 hours for intermittent usage inflates cost by 10x.
- **Expecting VM costs**: Model Serving is always serverless. If you see $0 in the VM Cost column, that is correct.
- **Comparing $/DBU across workload types**: Model Serving uses `SERVERLESS_REAL_TIME_INFERENCE` at $0.07/DBU, which is much lower than DBSQL or Jobs. The total cost depends on DBU/hour x hours, not just the per-DBU rate.

## Excel export

Each Model Serving workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | GPU type display name |
| Mode | Serverless (always) |
| SKU | `SERVERLESS_REAL_TIME_INFERENCE` |
| DBU/Hour | GPU rate from pricing lookup |
| Hours/Month | Direct hours value |
| Monthly DBUs | DBU/Hour x Hours/Month |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost |
