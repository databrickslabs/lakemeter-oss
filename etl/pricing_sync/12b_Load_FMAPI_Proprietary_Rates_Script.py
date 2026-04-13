# Databricks notebook source
# MAGIC %md
# MAGIC # Load FMAPI Proprietary Rates
# MAGIC
# MAGIC This notebook creates the `fmapi_proprietary_rates` table for proprietary foundation models:
# MAGIC - **OpenAI**: GPT 5.4 Pro, GPT 5.4, GPT 5.2/5.3 Codex, GPT 5.2, GPT 5.1, GPT 5.1 Codex Max, GPT 5.1 Codex Mini, GPT 5, GPT 5 mini, GPT 5 nano
# MAGIC - **Anthropic**: Claude Opus 4.6, Claude Opus 4.5, Claude Opus 4/4.1, Claude Sonnet 4.5/4.6, Claude Sonnet 3.7/4/4.1, Claude Haiku 4.5
# MAGIC - **Google**: Gemini 3.1 Pro, Gemini 3.0 Flash, Gemini 2.5 Pro, Gemini 2.5 Flash
# MAGIC
# MAGIC **Additional dimensions:**
# MAGIC - Endpoint type: Global vs In-geo
# MAGIC - Context length: Short vs Long (>200k tokens)
# MAGIC - Rate types: input_token, output_token, cache_write, cache_read, batch_inference
# MAGIC
# MAGIC **Source:** https://www.databricks.com/product/pricing/proprietary-foundation-model-serving
# MAGIC

# COMMAND ----------

# Configuration
CATALOG = "lakemeter_catalog"
SCHEMA = "lakemeter"
TABLE_FMAPI_PROPRIETARY = f"{CATALOG}.{SCHEMA}.fmapi_proprietary_rates"

print(f"✅ Target table: {TABLE_FMAPI_PROPRIETARY}")


# COMMAND ----------

import pandas as pd
from datetime import datetime

# =============================================================================
# FMAPI PROPRIETARY RATES
# Additional columns: cloud, provider, endpoint_type, context_length
#
# NOTE: Creating one row per cloud (AWS, AZURE, GCP) for future flexibility
# =============================================================================

CLOUDS = ["AWS", "AZURE", "GCP"]
BASE_FMAPI_PROP_RATES = []

def add_prop_rate(provider, model, endpoint_type, context_length, 
                  input_rate, output_rate, cache_write=None, cache_read=None, batch_rate=None,
                  sku_product_type=None):
    """Add proprietary model rates (to base list, will expand to clouds later)."""
    
    # Determine SKU based on provider
    if sku_product_type is None:
        sku_map = {
            "openai": "OPENAI_MODEL_SERVING",
            "anthropic": "ANTHROPIC_MODEL_SERVING", 
            "google": "GEMINI_MODEL_SERVING",
        }
        sku_product_type = sku_map.get(provider, "SERVERLESS_REAL_TIME_INFERENCE")
    
    base = {
        "provider": provider,
        "model": model,
        "endpoint_type": endpoint_type,
        "context_length": context_length,
        "input_divisor": 1000000,
        "is_hourly": False,
        "sku_product_type": sku_product_type,
    }
    
    if input_rate:
        BASE_FMAPI_PROP_RATES.append({**base, "rate_type": "input_token", "dbu_rate": input_rate})
    if output_rate:
        BASE_FMAPI_PROP_RATES.append({**base, "rate_type": "output_token", "dbu_rate": output_rate})
    if cache_write:
        BASE_FMAPI_PROP_RATES.append({**base, "rate_type": "cache_write", "dbu_rate": cache_write})
    if cache_read:
        BASE_FMAPI_PROP_RATES.append({**base, "rate_type": "cache_read", "dbu_rate": cache_read})
    if batch_rate:
        BASE_FMAPI_PROP_RATES.append({**base, "rate_type": "batch_inference", "dbu_rate": batch_rate, 
                                  "input_divisor": 1, "is_hourly": True})

print("✅ Helper function defined")


# COMMAND ----------

# =============================================================================
# OPENAI MODELS (from pricing screenshot)
# =============================================================================

# GPT 5.4 Pro - Short Context
add_prop_rate("openai", "gpt-5-4-pro", "global", "short",
              input_rate=428.571, output_rate=2571.429,
              cache_write=428.571, cache_read=42.857, batch_rate=1142.857)
add_prop_rate("openai", "gpt-5-4-pro", "in_geo", "short",
              input_rate=471.428, output_rate=2828.572,
              cache_write=471.428, cache_read=47.143, batch_rate=1257.143)

# GPT 5.4 Pro - Long Context
add_prop_rate("openai", "gpt-5-4-pro", "global", "long",
              input_rate=857.142, output_rate=3857.144,
              cache_write=857.142, cache_read=85.714, batch_rate=192.857)
add_prop_rate("openai", "gpt-5-4-pro", "in_geo", "long",
              input_rate=942.856, output_rate=4242.858,
              cache_write=942.856, cache_read=94.286, batch_rate=1142.857)

# GPT 5.4 - Short Context
add_prop_rate("openai", "gpt-5-4", "global", "short",
              input_rate=35.714, output_rate=214.286,
              cache_write=35.714, cache_read=3.571, batch_rate=192.857)
add_prop_rate("openai", "gpt-5-4", "in_geo", "short",
              input_rate=39.285, output_rate=235.715,
              cache_write=39.285, cache_read=3.929, batch_rate=212.143)

# GPT 5.4 - Long Context
add_prop_rate("openai", "gpt-5-4", "global", "long",
              input_rate=71.428, output_rate=321.429,
              cache_write=71.428, cache_read=7.143, batch_rate=192.857)
add_prop_rate("openai", "gpt-5-4", "in_geo", "long",
              input_rate=78.571, output_rate=353.572,
              cache_write=78.571, cache_read=7.857, batch_rate=212.143)

# GPT 5.1
add_prop_rate("openai", "gpt-5-1", "global", "all",
              input_rate=17.857, output_rate=142.857, 
              cache_write=17.857, cache_read=1.786, batch_rate=131.429)
add_prop_rate("openai", "gpt-5-1", "in_geo", "all",
              input_rate=19.643, output_rate=157.143,
              cache_write=19.643, cache_read=1.965, batch_rate=144.571)

# GPT 5
add_prop_rate("openai", "gpt-5", "global", "all",
              input_rate=17.857, output_rate=142.857,
              cache_write=17.857, cache_read=1.786, batch_rate=131.429)
add_prop_rate("openai", "gpt-5", "in_geo", "all",
              input_rate=19.643, output_rate=157.143,
              cache_write=19.643, cache_read=1.965, batch_rate=144.571)

# GPT 5 mini
add_prop_rate("openai", "gpt-5-mini", "global", "all",
              input_rate=3.571, output_rate=28.571,
              cache_write=3.571, cache_read=0.357, batch_rate=71.429)
add_prop_rate("openai", "gpt-5-mini", "in_geo", "all",
              input_rate=3.929, output_rate=31.429,
              cache_write=3.929, cache_read=0.393, batch_rate=78.571)

# GPT 5 nano
add_prop_rate("openai", "gpt-5-nano", "global", "all",
              input_rate=0.714, output_rate=5.714,
              cache_write=0.714, cache_read=0.071, batch_rate=53.571)
add_prop_rate("openai", "gpt-5-nano", "in_geo", "all",
              input_rate=0.786, output_rate=6.286,
              cache_write=0.786, cache_read=0.078, batch_rate=58.929)

# GPT 5.2
add_prop_rate("openai", "gpt-5-2", "global", "all",
              input_rate=25.000, output_rate=200.000,
              cache_write=25.000, cache_read=2.500, batch_rate=184.286)
add_prop_rate("openai", "gpt-5-2", "in_geo", "all",
              input_rate=27.500, output_rate=220.000,
              cache_write=27.500, cache_read=2.750, batch_rate=202.714)

# GPT 5.2/5.3 Codex (no batch inference)
add_prop_rate("openai", "gpt-5-2-5-3-codex", "global", "all",
              input_rate=25.000, output_rate=200.000,
              cache_write=25.000, cache_read=2.500)
add_prop_rate("openai", "gpt-5-2-5-3-codex", "in_geo", "all",
              input_rate=27.500, output_rate=220.000,
              cache_write=27.500, cache_read=2.750)

# GPT 5.1 Codex Max (no batch inference)
add_prop_rate("openai", "gpt-5-1-codex-max", "global", "all",
              input_rate=17.857, output_rate=142.857,
              cache_write=17.857, cache_read=1.786)
add_prop_rate("openai", "gpt-5-1-codex-max", "in_geo", "all",
              input_rate=19.643, output_rate=157.143,
              cache_write=19.643, cache_read=1.965)

# GPT 5.1 Codex Mini (no batch inference)
add_prop_rate("openai", "gpt-5-1-codex-mini", "global", "all",
              input_rate=3.571, output_rate=28.571,
              cache_write=3.571, cache_read=0.357)
add_prop_rate("openai", "gpt-5-1-codex-mini", "in_geo", "all",
              input_rate=3.929, output_rate=31.429,
              cache_write=3.929, cache_read=0.393)

print(f"✅ OpenAI models added: {len([r for r in BASE_FMAPI_PROP_RATES if r['provider'] == 'openai'])} rates")


# COMMAND ----------

# =============================================================================
# ANTHROPIC MODELS (from pricing screenshot)
# =============================================================================

# Claude Opus 4.6 - Short Context (different pricing for global vs in-geo)
add_prop_rate("anthropic", "claude-opus-4-6", "global", "short",
              input_rate=71.429, output_rate=357.143,
              cache_write=89.286, cache_read=7.143, batch_rate=178.571)
add_prop_rate("anthropic", "claude-opus-4-6", "in_geo", "short",
              input_rate=78.571, output_rate=392.857,
              cache_write=98.214, cache_read=7.857, batch_rate=196.429)

# Claude Opus 4.6 - Long Context (>200k tokens)
add_prop_rate("anthropic", "claude-opus-4-6", "global", "long",
              input_rate=142.858, output_rate=535.715,
              cache_write=178.572, cache_read=14.286, batch_rate=178.571)
add_prop_rate("anthropic", "claude-opus-4-6", "in_geo", "long",
              input_rate=157.142, output_rate=589.286,
              cache_write=196.428, cache_read=15.714, batch_rate=196.429)

# Claude Opus 4.5 - Short Context (different pricing for global vs in-geo)
add_prop_rate("anthropic", "claude-opus-4-5", "global", "short",
              input_rate=71.429, output_rate=357.143,
              cache_write=89.286, cache_read=7.143, batch_rate=178.571)
add_prop_rate("anthropic", "claude-opus-4-5", "in_geo", "short",
              input_rate=78.571, output_rate=392.857,
              cache_write=98.214, cache_read=7.857, batch_rate=196.429)

# Claude Opus 4 / 4.1 - All Lengths (Global/In-geo = same price, split into rows)
add_prop_rate("anthropic", "claude-opus-4", "global", "all",
              input_rate=214.286, output_rate=1071.429,
              cache_write=267.857, cache_read=21.429, batch_rate=514.286)
add_prop_rate("anthropic", "claude-opus-4", "in_geo", "all",
              input_rate=214.286, output_rate=1071.429,
              cache_write=267.857, cache_read=21.429, batch_rate=514.286)
add_prop_rate("anthropic", "claude-opus-4-1", "global", "all",
              input_rate=214.286, output_rate=1071.429,
              cache_write=267.857, cache_read=21.429, batch_rate=514.286)
add_prop_rate("anthropic", "claude-opus-4-1", "in_geo", "all",
              input_rate=214.286, output_rate=1071.429,
              cache_write=267.857, cache_read=21.429, batch_rate=514.286)

# Claude Sonnet 4.5 / 4.6 - Short Context (different pricing for global vs in-geo)
add_prop_rate("anthropic", "claude-sonnet-4-5", "global", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-5", "in_geo", "short",
              input_rate=47.143, output_rate=235.715,
              cache_write=58.928, cache_read=4.715, batch_rate=235.715)

# Claude Sonnet 4.5 / 4.6 - Long Context (different pricing for global vs in-geo)
add_prop_rate("anthropic", "claude-sonnet-4-5", "global", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-5", "in_geo", "long",
              input_rate=94.285, output_rate=353.572,
              cache_write=117.857, cache_read=9.428, batch_rate=235.715)

# Claude Sonnet 4.6 - Short Context (same pricing as Sonnet 4.5)
add_prop_rate("anthropic", "claude-sonnet-4-6", "global", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-6", "in_geo", "short",
              input_rate=47.143, output_rate=235.715,
              cache_write=58.928, cache_read=4.715, batch_rate=235.715)

# Claude Sonnet 4.6 - Long Context (same pricing as Sonnet 4.5)
add_prop_rate("anthropic", "claude-sonnet-4-6", "global", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-6", "in_geo", "long",
              input_rate=94.285, output_rate=353.572,
              cache_write=117.857, cache_read=9.428, batch_rate=235.715)

# Claude Sonnet 3.7 / 4 / 4.1 - Short Context (Global/In-geo = same price, split into rows)
add_prop_rate("anthropic", "claude-sonnet-3-7", "global", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-3-7", "in_geo", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4", "global", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4", "in_geo", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-1", "global", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-1", "in_geo", "short",
              input_rate=42.857, output_rate=214.286,
              cache_write=53.571, cache_read=4.286, batch_rate=214.286)

# Claude Sonnet 3.7 / 4 / 4.1 - Long Context (Global/In-geo = same price, split into rows)
add_prop_rate("anthropic", "claude-sonnet-3-7", "global", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-3-7", "in_geo", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4", "global", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4", "in_geo", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-1", "global", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)
add_prop_rate("anthropic", "claude-sonnet-4-1", "in_geo", "long",
              input_rate=85.714, output_rate=321.429,
              cache_write=107.143, cache_read=8.571, batch_rate=214.286)

# Claude Haiku 4.5 (different pricing for global vs in-geo)
add_prop_rate("anthropic", "claude-haiku-4-5", "global", "all",
              input_rate=14.286, output_rate=71.429,
              cache_write=17.857, cache_read=1.429, batch_rate=114.286)
add_prop_rate("anthropic", "claude-haiku-4-5", "in_geo", "all",
              input_rate=15.715, output_rate=78.572,
              cache_write=19.643, cache_read=1.572, batch_rate=125.714)

print(f"✅ Anthropic models added: {len([r for r in BASE_FMAPI_PROP_RATES if r['provider'] == 'anthropic'])} rates")


# COMMAND ----------

# =============================================================================
# GOOGLE MODELS (from pricing screenshot)
# Global/In-geo = same price, split into separate rows
# =============================================================================

# Gemini 3.1 Pro - Short Context (Global/In-geo same price, replaces Gemini 3.0 Pro)
add_prop_rate("google", "gemini-3-1-pro", "global", "short",
              input_rate=35.714, output_rate=214.286,
              cache_write=35.714, cache_read=3.571, batch_rate=230.357)
add_prop_rate("google", "gemini-3-1-pro", "in_geo", "short",
              input_rate=35.714, output_rate=214.286,
              cache_write=35.714, cache_read=3.571, batch_rate=230.357)

# Gemini 3.1 Pro - Long Context (Global/In-geo same price)
add_prop_rate("google", "gemini-3-1-pro", "global", "long",
              input_rate=71.429, output_rate=321.429,
              cache_write=71.429, cache_read=7.143, batch_rate=230.357)
add_prop_rate("google", "gemini-3-1-pro", "in_geo", "long",
              input_rate=71.429, output_rate=321.429,
              cache_write=71.429, cache_read=7.143, batch_rate=230.357)

# Gemini 3.0 Pro - kept for backwards compatibility (redirects to 3.1 Pro)
add_prop_rate("google", "gemini-3-0-pro", "global", "short",
              input_rate=35.714, output_rate=214.286,
              cache_write=35.714, cache_read=3.571, batch_rate=230.357)
add_prop_rate("google", "gemini-3-0-pro", "in_geo", "short",
              input_rate=35.714, output_rate=214.286,
              cache_write=35.714, cache_read=3.571, batch_rate=230.357)
add_prop_rate("google", "gemini-3-0-pro", "global", "long",
              input_rate=71.429, output_rate=321.429,
              cache_write=71.429, cache_read=7.143, batch_rate=230.357)
add_prop_rate("google", "gemini-3-0-pro", "in_geo", "long",
              input_rate=71.429, output_rate=321.429,
              cache_write=71.429, cache_read=7.143, batch_rate=230.357)

# Gemini 3.0 Flash - Short Context (Global/In-geo same price)
add_prop_rate("google", "gemini-3-0-flash", "global", "short",
              input_rate=8.929, output_rate=53.571,
              cache_write=8.929, cache_read=0.893, batch_rate=125.000)
add_prop_rate("google", "gemini-3-0-flash", "in_geo", "short",
              input_rate=8.929, output_rate=53.571,
              cache_write=8.929, cache_read=0.893, batch_rate=125.000)

# Gemini 3.0 Flash - Long Context (Global/In-geo same price)
add_prop_rate("google", "gemini-3-0-flash", "global", "long",
              input_rate=8.929, output_rate=53.571,
              cache_write=8.929, cache_read=0.893, batch_rate=125.000)
add_prop_rate("google", "gemini-3-0-flash", "in_geo", "long",
              input_rate=8.929, output_rate=53.571,
              cache_write=8.929, cache_read=0.893, batch_rate=125.000)

# Gemini 2.5 Pro - Short Context (Global/In-geo same price)
add_prop_rate("google", "gemini-2-5-pro", "global", "short",
              input_rate=17.857, output_rate=142.857, batch_rate=164.286)
add_prop_rate("google", "gemini-2-5-pro", "in_geo", "short",
              input_rate=17.857, output_rate=142.857, batch_rate=164.286)

# Gemini 2.5 Pro - Long Context (Global/In-geo same price)
add_prop_rate("google", "gemini-2-5-pro", "global", "long",
              input_rate=35.714, output_rate=214.286, batch_rate=164.286)
add_prop_rate("google", "gemini-2-5-pro", "in_geo", "long",
              input_rate=35.714, output_rate=214.286, batch_rate=164.286)

# Gemini 2.5 Flash - Short Context (Global/In-geo same price)
add_prop_rate("google", "gemini-2-5-flash", "global", "short",
              input_rate=4.286, output_rate=35.714, batch_rate=107.143)
add_prop_rate("google", "gemini-2-5-flash", "in_geo", "short",
              input_rate=4.286, output_rate=35.714, batch_rate=107.143)

# Gemini 2.5 Flash - Long Context (Global/In-geo same price)
add_prop_rate("google", "gemini-2-5-flash", "global", "long",
              input_rate=4.286, output_rate=35.714, batch_rate=107.143)
add_prop_rate("google", "gemini-2-5-flash", "in_geo", "long",
              input_rate=4.286, output_rate=35.714, batch_rate=107.143)

print(f"✅ Google models added: {len([r for r in BASE_FMAPI_PROP_RATES if r['provider'] == 'google'])} rates")

# =============================================================================
# EXPAND TO ALL CLOUDS
# =============================================================================
FMAPI_PROP_RATES = []
for cloud in CLOUDS:
    for rate in BASE_FMAPI_PROP_RATES:
        row = rate.copy()
        row["cloud"] = cloud
        FMAPI_PROP_RATES.append(row)

print(f"\n✅ Total: {len(FMAPI_PROP_RATES)} proprietary rates ({len(BASE_FMAPI_PROP_RATES)} base × {len(CLOUDS)} clouds)")


# COMMAND ----------

# =============================================================================
# CREATE DATAFRAME AND SAVE
# =============================================================================

# Add timestamp
for row in FMAPI_PROP_RATES:
    row["updated_at"] = datetime.utcnow().isoformat()

df = pd.DataFrame(FMAPI_PROP_RATES)

print(f"📊 Clouds: {df['cloud'].unique().tolist()}")
print(f"📊 Providers: {df['provider'].unique().tolist()}")
print(f"📊 Models: {df['model'].unique().tolist()}")
print(f"📊 Endpoint types: {df['endpoint_type'].unique().tolist()}")
print(f"📊 Context lengths: {df['context_length'].unique().tolist()}")
print(f"📊 Rate types: {df['rate_type'].unique().tolist()}")
print(f"📊 Total rates: {len(df)}")

display(df)

# Save to table
spark_df = spark.createDataFrame(df)
spark_df.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(TABLE_FMAPI_PROPRIETARY)

print(f"\n✅ Saved to {TABLE_FMAPI_PROPRIETARY}")
