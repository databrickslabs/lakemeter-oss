---
sidebar_position: 18
---

# Shutterstock ImageAI

> **Lakemeter UI name:** Shutterstock ImageAI

Shutterstock ImageAI provides AI-powered image generation on Databricks. You specify the number of images to generate per month, and costs are calculated based on a fixed DBU rate per image. This is one of the simplest workload types to estimate.

## When to use Shutterstock ImageAI

Use Shutterstock ImageAI when you need to **generate images using AI** — things like marketing content, product mockups, creative assets, or data augmentation for ML training. If you need text generation or chat capabilities, see [FMAPI — Databricks Models](/user-guide/fmapi-databricks) instead.

## Real-world example

> **Scenario:** Your marketing team generates 2,000 AI images per month for social media and ad campaigns on AWS us-east-1 (Premium tier).

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | Shutterstock ImageAI |
| Images Per Month | 2,000 |

### Step-by-step calculation

**1. DBU rate per image**

Each image costs a fixed 0.857 DBU:

```
DBU per Image = 0.857
```

**2. Monthly DBUs and cost**

```
Monthly DBUs = Images × DBU per Image = 2,000 × 0.857 = 1,714 DBUs
DBU Cost     = 1,714 × $0.07/DBU = $119.98
Total Cost   = $119.98 (no VM costs — always serverless)
```

:::note
These are example rates for illustration. Actual $/DBU depends on your cloud, region, and pricing tier. The $0.07 rate is the fallback for the `SERVERLESS_REAL_TIME_INFERENCE` SKU on AWS/us-east-1/Premium.
:::

### Scaling examples

| Images/Month | Monthly DBUs | Estimated Cost |
|-------------|-------------|----------------|
| 500 | 428.5 | ~$30 |
| 1,000 | 857.0 | ~$60 |
| 5,000 | 4,285.0 | ~$300 |
| 10,000 | 8,570.0 | ~$600 |

Costs scale linearly with image count.

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **Images Per Month** | Number of images to generate per month. | 1,000 |

That's it — Shutterstock ImageAI has the simplest configuration of any workload type.

## How costs are calculated

```
DBU per Image  = 0.857 (fixed)
Monthly DBUs   = Images Per Month × DBU per Image
DBU Cost       = Monthly DBUs × $/DBU
Total Cost     = DBU Cost (no VM costs — always serverless)
```

Shutterstock ImageAI is **always serverless**. There are no VM infrastructure costs.

### SKU mapping

| Workload | SKU | Fallback $/DBU |
|----------|-----|----------------|
| Shutterstock ImageAI | `SERVERLESS_REAL_TIME_INFERENCE` | $0.07 |

## Tips

- **Start with actual usage**: Track how many images your team generates in a typical month before estimating. Marketing teams often overestimate their needs.
- **Costs are linear**: Double the images = double the cost. No volume discounts or tier thresholds to worry about.
- **Compare with external services**: At ~$0.06 per image (at $0.07/DBU), Shutterstock ImageAI is competitive with other AI image generation APIs.

## Common mistakes

- **Overestimating image volume**: A marketing team generating 50 social media posts per week needs ~200 images/month, not 5,000. Estimate based on actual creative workflows.
- **Expecting VM costs**: Shutterstock ImageAI is always serverless. $0 VM cost is correct.

## Excel export

Each Shutterstock ImageAI workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | Image count |
| Mode | Serverless (always) |
| SKU | `SERVERLESS_REAL_TIME_INFERENCE` |
| Images/Month | Direct value |
| Monthly DBUs | Images × 0.857 |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost |
