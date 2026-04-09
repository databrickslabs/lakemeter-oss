---
sidebar_position: 15
---

# FMAPI — Proprietary Models

> **Lakemeter UI name:** FMAPI - Proprietary

FMAPI for proprietary models lets you access commercial LLMs -- Claude (Anthropic), GPT (OpenAI), and Gemini (Google) -- through Databricks with pay-per-token pricing. Unlike Databricks-hosted open-source models, proprietary model pricing varies significantly by **provider**, **model**, **endpoint type**, and **context length**.

![FMAPI Proprietary documentation page](/img/guides/fmapi-proprietary-guide.png)
*The FMAPI Proprietary guide — provider/model selection, endpoint types, context lengths, and cache read/write rates.*

![FMAPI Proprietary worked cost example](/img/guides/fmapi-proprietary-worked-example.png)
*Worked example showing Claude Sonnet 4.5 token costs with global vs in-geo endpoint comparison.*

## When to use FMAPI Proprietary

Use FMAPI Proprietary when you want to call **commercial LLMs through Databricks** rather than directly through the provider's API. Databricks routes the requests and bills through your Databricks account using DBUs. If you need open-source models (Llama, DBRX, BGE), see [FMAPI — Databricks Models](/user-guide/fmapi-databricks) instead.

## Real-world example

> **Scenario:** You are building an AI-powered document analysis feature on AWS us-east-1 (Premium tier) using Claude Sonnet 4.5. Your users submit documents averaging 5,000 tokens each, and the model generates 1,000-token summaries. You estimate 5 million input tokens and 1 million output tokens per month. You will use the global endpoint with long context.

### Configuration (input tokens)

| Field | Value |
|-------|-------|
| Workload Type | FMAPI Proprietary |
| Provider | Anthropic |
| Model | Claude Sonnet 4.5 |
| Endpoint Type | Global |
| Context Length | Long |
| Rate Type | Input Token |
| Quantity (Millions) | 5 |

### Configuration (output tokens)

| Field | Value |
|-------|-------|
| Workload Type | FMAPI Proprietary |
| Provider | Anthropic |
| Model | Claude Sonnet 4.5 |
| Endpoint Type | Global |
| Context Length | Long |
| Rate Type | Output Token |
| Quantity (Millions) | 1 |

:::info
Each rate type is a **separate line item**. Add one for input tokens and another for output tokens. If using prompt caching, add additional line items for Cache Read and Cache Write.
:::

### Step-by-step calculation

**1. Input token cost**

```
Monthly DBUs = Quantity (millions) x DBU per 1M Tokens
             = 5 x 85.714
             = 428.57 DBUs
DBU Cost     = 428.57 x $0.07/DBU = $30.00
```

**2. Output token cost**

```
Monthly DBUs = 1 x 321.429 = 321.429 DBUs
DBU Cost     = 321.429 x $0.07/DBU = $22.50
```

**3. Total monthly cost**

```
Total = Input Cost + Output Cost = $30.00 + $22.50 = $52.50/month
```

:::note
These are example rates for Claude Sonnet 4.5 on AWS with global endpoint and long context. Actual rates depend on the model, provider, endpoint type, and context length. Lakemeter loads real rates from the pricing bundle.
:::

### How does endpoint type affect cost?

The same model with in-geo (regional) endpoint costs more:

```
Input:  5 x 94.285 x $0.07 = $33.00 (vs $30.00 for global)
Output: 1 x 353.572 x $0.07 = $24.75 (vs $22.50 for global)
Total:  $57.75/month (vs $52.50 for global)
```

In-geo routes requests to a specific geographic region for data residency compliance. It costs ~10% more than global.

### How does context length affect cost?

Short context is cheaper than long context for the same model:

```
Input (short):  5 x 42.857 x $0.07 = $15.00 (vs $30.00 for long)
Output (short): 1 x 214.286 x $0.07 = $15.00 (vs $22.50 for long)
Total (short):  $30.00/month (vs $52.50 for long)
```

Short context uses a smaller context window. If your prompts are under the short context limit, this is a significant cost saving.

## Supported providers and models

| Provider | Models |
|----------|--------|
| **Anthropic** | Claude Sonnet 3.7, Claude Sonnet 4, Claude Sonnet 4.1, Claude Sonnet 4.5, Claude Opus 4, Claude Opus 4.1, Claude Opus 4.5, Claude Haiku 4.5 |
| **OpenAI** | GPT-5, GPT-5.1, GPT-5 Mini, GPT-5 Nano |
| **Google** | Gemini 2.5 Flash, Gemini 2.5 Pro |

## Configuration reference

| Field | Description | Options | Default |
|-------|-------------|---------|---------|
| **Provider** | The commercial LLM provider | Anthropic, OpenAI, Google | Anthropic |
| **Model** | Specific model variant (filtered by provider) | See table above | First model in list |
| **Endpoint Type** | How requests are routed | Global, In-Geo (Regional) | Global |
| **Context Length** | Context window size tier | All, Short, Long | Long |
| **Rate Type** | Token direction | Input Token, Output Token | Input Token |
| **Quantity (Millions)** | Monthly token volume in millions | Any positive number | — |

### Endpoint types

| Type | Description | Cost |
|------|-------------|------|
| **Global** | Requests routed to nearest available region | Lower |
| **In-Geo (Regional)** | Requests stay within a specific geographic region | ~10% higher |

Use In-Geo when you have data residency requirements (e.g., data must stay in EU). Use Global for the lowest cost.

### Context lengths

| Length | Description | Cost |
|--------|-------------|------|
| **Long** | Extended context window (default) | Higher |
| **Short** | Reduced context window | Lower (~50% less) |
| **All** | Standard context window — rate varies by model | Varies |

Short context is significantly cheaper (often 50% less) than long context. Use short when your prompts fit within the shorter window. Not all models support all context lengths — Lakemeter automatically filters available options based on the selected model.

## Rate types

| Rate Type | Unit | Description |
|-----------|------|-------------|
| `input_token` | DBU per 1M tokens | Tokens sent to the model (prompts, documents, context) |
| `output_token` | DBU per 1M tokens | Tokens generated by the model (completions, summaries) |
| `cache_read` | DBU per 1M tokens | Reading from prompt cache (cheaper than input tokens for repeated context) |
| `cache_write` | DBU per 1M tokens | Writing to prompt cache (initial cost to cache context for reuse) |

:::tip Prompt caching
Cache Read and Cache Write rate types are available for models that support prompt caching. If you repeatedly send the same system prompt or context, caching can significantly reduce costs -- Cache Read rates are typically much lower than Input Token rates. Add separate line items for each rate type you plan to use.
:::

:::info No provisioned pricing
Unlike FMAPI Databricks, proprietary models **do not offer provisioned throughput**. All pricing is pay-per-token.
:::

## How costs are calculated

```
Monthly DBUs = Quantity (millions) x DBU per 1M Tokens
DBU Cost     = Monthly DBUs x $/DBU
Total Cost   = DBU Cost (no VM costs — always serverless)
```

The DBU per 1M tokens rate depends on the combination of: cloud + provider + model + endpoint type + context length + rate type. Lakemeter looks up the exact rate from the pricing bundle.

### Fallback behavior

When a specific combination is not found in the pricing bundle:

| Component | Input fallback | Output fallback |
|-----------|---------------|-----------------|
| **Frontend** | 21.43 DBU/1M | 321.43 DBU/1M |
| **Backend** | 0 DBU | 0 DBU |

### SKU mapping

Proprietary models use provider-specific SKUs:

| Provider | SKU |
|----------|-----|
| Anthropic | `ANTHROPIC_MODEL_SERVING` |
| OpenAI | `OPENAI_MODEL_SERVING` |
| Google | `GOOGLE_MODEL_SERVING` |

## Tips

- **Compare providers for your use case**: Claude excels at long-context analysis, GPT at general-purpose tasks, and Gemini at multimodal workloads. Choose based on capability, then estimate cost.
- **Use short context when possible**: Short context rates are often 50% cheaper. If your prompts are consistently under the short context limit, this is the biggest cost lever.
- **Global endpoint is cheaper**: Unless you have regulatory data residency requirements, use Global to avoid the ~10% In-Geo premium.
- **Consider open-source alternatives**: FMAPI Databricks models (Llama 3.3 70B at ~7 DBU/1M input tokens) are dramatically cheaper than proprietary models (Claude Sonnet 4.5 at ~86 DBU/1M). Evaluate whether an open-source model meets your quality requirements.

## Common mistakes

- **Forgetting to add both input and output line items**: Each rate type is a separate workload entry. If you only add input tokens, you are underestimating by the output cost.
- **Ignoring context length**: Leaving context length at "Long" when your prompts would fit in "Short" doubles the cost.
- **Comparing raw DBU rates across providers**: Different providers have different DBU/1M rates. Compare the **total monthly cost** for your expected token volume, not just the per-million rate.
- **Expecting the same rate across all configurations**: The rate changes with endpoint type (global vs in-geo) and context length (short vs long). Always check that you have selected the correct options.

## Excel export

Each FMAPI Proprietary workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | Provider, model, endpoint type, context length, rate type |
| Mode | Serverless (always) |
| SKU | Provider-specific (`ANTHROPIC_MODEL_SERVING`, etc.) |
| Token Type | Rate type label |
| Tokens/Mo in Millions | Quantity |
| DBU per 1M Tokens | DBU rate for the specific configuration |
| Monthly DBUs | Quantity x DBU/1M |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost |
