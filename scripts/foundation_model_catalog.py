#!/usr/bin/env python3
"""Generate and audit Foundation Model Serving pricing catalogs.

Official sources:
  https://www.databricks.com/product/pricing/foundation-model-serving
  https://www.databricks.com/product/pricing/proprietary-foundation-model-serving
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRICING_DIR = ROOT / "backend" / "static" / "pricing"
DB_JSON = PRICING_DIR / "fmapi-databricks-rates.json"
DB_CSV = PRICING_DIR / "fmapi-databricks-rates.csv"
PROP_JSON = PRICING_DIR / "fmapi-proprietary-rates.json"
PROP_CSV = PRICING_DIR / "fmapi-proprietary-rates.csv"

CLOUDS = ("aws", "azure", "gcp")
TOKEN_RATE_TYPES = {
    "input": "input_token",
    "output": "output_token",
    "cache_read": "cache_read",
    "cache_write": "cache_write",
}


def _rate(
    dbu_rate: float,
    *,
    hourly: bool,
    sku: str,
    display_name: str,
    status: str = "active",
    **metadata: Any,
) -> dict[str, Any]:
    result = {
        "dbu_rate": dbu_rate,
        "input_divisor": 1 if hourly else 1_000_000,
        "is_hourly": hourly,
        "sku_product_type": sku,
        "display_name": display_name,
        "status": status,
    }
    result.update({key: value for key, value in metadata.items() if value is not None})
    return result


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _retire_existing(
    catalog: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    retired: dict[str, dict[str, Any]] = {}
    for key, value in catalog.items():
        entry = dict(value)
        entry["status"] = "retired"
        parts = key.split(":")
        model = parts[1] if len(parts) == 3 else parts[2]
        entry.setdefault("display_name", model.replace("-", " ").title())
        retired[key] = entry
    return retired


def build_databricks_catalog(
    existing: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    catalog = _retire_existing(existing)
    sku = "SERVERLESS_REAL_TIME_INFERENCE"

    models: list[dict[str, Any]] = [
        {
            "id": "kimi-k3",
            "name": "Kimi K3",
            "rates": {"input": 42.857, "output": 214.286, "cache_read": 4.286},
            "regional_uplift_percent": 10,
        },
        {
            "id": "kimi-k2-7",
            "name": "Kimi K2.7",
            "rates": {"input": 13.571, "output": 57.143, "cache_read": 2.714},
        },
        {
            "id": "glm-5-2",
            "name": "GLM-5.2",
            "rates": {"input": 20.0, "output": 62.857, "cache_read": 3.714},
            "provisioned": {
                "entry_1_month": 142.857,
                "entry_3_month": 121.429,
                "scaling_1_month": 142.857,
                "scaling_3_month": 121.429,
            },
        },
        {
            "id": "glm-5-2-priority",
            "name": "GLM-5.2 (Priority)",
            "rates": {"input": 35.0, "output": 110.0, "cache_read": 6.5},
        },
        {
            "id": "inkling",
            "name": "Inkling",
            "rates": {"input": 14.286, "output": 57.857, "cache_read": 2.429},
        },
        {
            "id": "deepseek-v4-pro-0813",
            "name": "DeepSeek V4 Pro (0813)",
            "rates": {"input": 18.857, "output": 56.571, "cache_read": 1.886},
        },
        {
            "id": "deepseek-v4-flash-0731",
            "name": "DeepSeek V4 Flash (0731)",
            "rates": {"input": 2.0, "output": 4.0, "cache_read": 0.4},
        },
        {
            "id": "qwen35-122b-a10b",
            "name": "Qwen 3.5 122B",
            "rates": {"input": 3.143, "output": 31.429},
            "provisioned": {"entry": 85.714, "scaling": 85.714},
        },
        {
            "id": "qwen35-122b-a10b-priority",
            "name": "Qwen 3.5 122B (Priority)",
            "rates": {"input": 6.286, "output": 62.858},
        },
        {
            "id": "qwen3-next-80b-a3b-instruct",
            "name": "Qwen 3 Next 80B",
            "rates": {"input": 2.143, "output": 17.143},
            "provisioned": {"entry": 78.571, "scaling": 78.571},
        },
        {
            "id": "gpt-oss-120b",
            "name": "GPT OSS 120B",
            "rates": {"input": 2.143, "output": 8.571},
            "provisioned": {"entry": 71.429, "scaling": 71.429},
        },
        {
            "id": "gpt-oss-20b",
            "name": "GPT OSS 20B",
            "rates": {"input": 1.0, "output": 4.286},
            "provisioned": {"entry": 53.571, "scaling": 53.571},
        },
        {
            "id": "llama-4-maverick",
            "name": "Llama 4 Maverick",
            "rates": {"input": 7.143, "output": 21.429},
            "provisioned": {"entry": 85.714, "scaling": 85.714},
        },
        {
            "id": "llama-3-3-70b",
            "name": "Llama 3.3 70B",
            "rates": {"input": 7.143, "output": 21.429},
            "provisioned": {"entry": 85.714, "scaling": 342.857},
        },
        {
            "id": "gemma-3-12b",
            "name": "Gemma 3 12B",
            "rates": {"input": 2.143, "output": 7.143},
            "provisioned": {"entry": 71.429, "scaling": 71.429},
        },
        {
            "id": "llama-3-1-8b",
            "name": "Llama 3.1 8B",
            "rates": {"input": 2.143, "output": 6.429},
            "provisioned": {"entry": 53.571, "scaling": 106.0},
        },
        {
            "id": "llama-3-2-3b",
            "name": "Llama 3.2 3B",
            "rates": {},
            "provisioned": {"entry": 46.429, "scaling": 92.857},
        },
        {
            "id": "llama-3-2-1b",
            "name": "Llama 3.2 1B",
            "rates": {},
            "provisioned": {"entry": 42.857, "scaling": 85.714},
        },
        {
            "id": "qwen3-embedding-0-6b",
            "name": "Qwen 3 0.6B Embedding",
            "rates": {"input": 0.286},
            "provisioned": {"entry": 25.0, "scaling": 25.0},
        },
        {
            "id": "gte",
            "name": "GTE",
            "rates": {"input": 1.857},
            "provisioned": {"entry": 20.0, "scaling": 20.0},
        },
        {
            "id": "bge-large",
            "name": "BGE Large",
            "rates": {"input": 1.429},
            "provisioned": {"entry": 24.0, "scaling": 24.0},
        },
    ]

    for model in models:
        metadata = {
            "regional_uplift_percent": model.get("regional_uplift_percent"),
            "source": "databricks_foundation_model_serving",
        }
        for cloud in CLOUDS:
            for short_type, dbu_rate in model["rates"].items():
                rate_type = TOKEN_RATE_TYPES[short_type]
                catalog[f"{cloud}:{model['id']}:{rate_type}"] = _rate(
                    dbu_rate,
                    hourly=False,
                    sku=sku,
                    display_name=model["name"],
                    **metadata,
                )

            for provisioned_type, dbu_rate in model.get("provisioned", {}).items():
                is_entry = provisioned_type.startswith("entry")
                if is_entry and cloud == "gcp":
                    continue
                rate_type = f"provisioned_{provisioned_type}"
                reservation_months = None
                if provisioned_type.endswith("_1_month"):
                    reservation_months = 1
                elif provisioned_type.endswith("_3_month"):
                    reservation_months = 3
                catalog[f"{cloud}:{model['id']}:{rate_type}"] = _rate(
                    dbu_rate,
                    hourly=True,
                    sku=sku,
                    display_name=model["name"],
                    reservation_months=reservation_months,
                    supported_region_group="americas" if is_entry else None,
                    source="databricks_foundation_model_serving",
                )

    # Historical aliases remain priceable for existing saved estimates but are
    # excluded from active selectors by their retired status.
    for cloud in CLOUDS:
        for alias, canonical in (
            ("bge-large-en", "bge-large"),
            ("gte-large-en", "gte"),
        ):
            prefix = f"{cloud}:{canonical}:"
            for key, value in list(catalog.items()):
                if key.startswith(prefix) and value.get("status") == "active":
                    alias_key = key.replace(prefix, f"{cloud}:{alias}:", 1)
                    alias_value = dict(value)
                    alias_value["status"] = "retired"
                    alias_value["alias_for"] = canonical
                    catalog[alias_key] = alias_value

    return dict(sorted(catalog.items()))


def _proprietary_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(
        provider: str,
        model: str,
        name: str,
        endpoint: str,
        context: str,
        rates: tuple[float, float, float | None, float | None, float | None],
        *,
        promo_rates: tuple[float, float, float | None, float | None, float | None] | None = None,
        promo_end: str | None = None,
        promo_label: str | None = None,
        batch_status: str | None = None,
    ) -> None:
        rows.append(
            {
                "provider": provider,
                "model": model,
                "name": name,
                "endpoint": endpoint,
                "context": context,
                "rates": rates,
                "promo_rates": promo_rates,
                "promo_end": promo_end,
                "promo_label": promo_label,
                "batch_status": batch_status,
            }
        )

    def paired(
        provider: str,
        model: str,
        name: str,
        context: str,
        global_rates: tuple[float, float, float | None, float | None, float | None],
        in_geo_rates: tuple[float, float, float | None, float | None, float | None],
        **kwargs: Any,
    ) -> None:
        add(provider, model, name, "global", context, global_rates, **kwargs)
        add(provider, model, name, "in_geo", context, in_geo_rates, **kwargs)

    # OpenAI
    paired("openai", "gpt-5-6-sol", "GPT 5.6 Sol", "short",
           (71.429, 428.571, 89.286, 7.143, 214.286),
           (78.571, 471.429, 98.214, 7.857, 235.715))
    paired("openai", "gpt-5-6-sol", "GPT 5.6 Sol", "long",
           (142.857, 642.857, 178.571, 14.286, 214.286),
           (157.143, 707.143, 196.429, 15.714, 235.715))
    paired("openai", "gpt-5-6-terra", "GPT 5.6 Terra", "short",
           (28.571, 171.429, 35.714, 2.857, 154.286),
           (31.429, 188.571, 39.286, 3.143, 169.714))
    paired("openai", "gpt-5-6-terra", "GPT 5.6 Terra", "long",
           (57.143, 257.143, 71.429, 5.714, 154.286),
           (62.857, 282.857, 78.571, 6.286, 169.714))
    paired("openai", "gpt-5-6-luna", "GPT 5.6 Luna", "short",
           (2.857, 17.143, 3.571, 0.286, 22.857),
           (3.143, 18.857, 3.929, 0.314, 25.143))
    paired("openai", "gpt-5-6-luna", "GPT 5.6 Luna", "long",
           (5.714, 25.714, 7.143, 0.571, 22.857),
           (6.286, 28.286, 7.857, 0.629, 25.143))
    paired("openai", "gpt-5-5", "GPT 5.5", "short",
           (71.429, 428.571, 71.429, 7.143, 214.286),
           (78.572, 471.428, 78.572, 7.857, 235.715))
    paired("openai", "gpt-5-5", "GPT 5.5", "long",
           (142.857, 642.857, 142.857, 14.286, 214.286),
           (157.143, 707.143, 157.143, 15.714, 235.715))
    for model, name in (
        ("gpt-5-4-pro", "GPT 5.4 Pro"),
        ("gpt-5-5-pro", "GPT 5.5 Pro"),
    ):
        paired("openai", model, name, "short",
               (428.571, 2571.429, 428.571, None, 1142.857),
               (471.428, 2828.572, 471.428, None, 1257.143))
        paired("openai", model, name, "long",
               (857.142, 3857.144, 857.142, None, 1142.857),
               (942.856, 4242.858, 942.856, None, 1257.143))
    paired("openai", "gpt-5-4", "GPT 5.4", "short",
           (35.714, 214.286, 35.714, 3.571, 192.857),
           (39.285, 235.715, 39.285, 3.929, 212.143))
    paired("openai", "gpt-5-4", "GPT 5.4", "long",
           (71.428, 321.429, 71.428, 7.143, 192.857),
           (78.571, 353.572, 78.571, 7.857, 212.143))
    paired("openai", "gpt-5-4-mini", "GPT 5.4 Mini", "all",
           (10.714, 64.286, 10.714, 1.071, 107.143),
           (11.786, 70.714, 11.786, 1.179, 117.857))
    paired("openai", "gpt-5-4-nano", "GPT 5.4 Nano", "all",
           (2.857, 17.857, 2.857, 0.286, 71.429),
           (3.143, 19.643, 3.143, 0.314, 78.571))
    openai_all = [
        ("gpt-5-2-5-3-codex", "GPT 5.2/5.3 Codex",
         (25.0, 200.0, 25.0, 2.5, None), (27.5, 220.0, 27.5, 2.75, None)),
        ("gpt-5-2", "GPT 5.2",
         (25.0, 200.0, 25.0, 2.5, 184.286), (27.5, 220.0, 27.5, 2.75, 202.714)),
        ("gpt-5-1", "GPT 5.1",
         (17.857, 142.857, 17.857, 1.786, 131.429), (19.643, 157.143, 19.643, 1.965, 144.571)),
        ("gpt-5-1-codex-max", "GPT 5.1 Codex Max",
         (17.857, 142.857, 17.857, 1.786, None), (19.643, 157.143, 19.643, 1.965, None)),
        ("gpt-5", "GPT 5",
         (17.857, 142.857, 17.857, 1.786, 131.429), (19.643, 157.143, 19.643, 1.965, 144.571)),
        ("gpt-5-mini", "GPT 5 Mini",
         (3.571, 28.571, 3.571, 0.357, 71.429), (3.929, 31.429, 3.929, 0.393, 78.571)),
        ("gpt-5-1-codex-mini", "GPT 5.1 Codex Mini",
         (3.571, 28.571, 3.571, 0.357, None), (3.929, 31.429, 3.929, 0.393, None)),
        ("gpt-5-nano", "GPT 5 Nano",
         (0.714, 5.714, 0.714, 0.071, 53.571), (0.786, 6.286, 0.786, 0.078, 58.929)),
    ]
    for model, name, global_rates, in_geo_rates in openai_all:
        paired("openai", model, name, "all", global_rates, in_geo_rates)

    # Anthropic
    paired("anthropic", "claude-fable-5", "Claude Fable 5", "all",
           (142.858, 714.286, 178.572, 14.286, 357.142),
           (157.142, 785.714, 196.428, 15.714, 392.858))
    for model, name in (
        ("claude-opus-4-5", "Claude Opus 4.5"),
        ("claude-opus-4-6", "Claude Opus 4.6"),
        ("claude-opus-4-7", "Claude Opus 4.7"),
        ("claude-opus-4-8", "Claude Opus 4.8"),
        ("claude-opus-5", "Claude Opus 5"),
    ):
        paired("anthropic", model, name, "all",
               (71.429, 357.143, 89.286, 7.143, 178.571),
               (78.571, 392.857, 98.214, 7.857, 196.429))
    for model, name in (
        ("claude-opus-4", "Claude Opus 4"),
        ("claude-opus-4-1", "Claude Opus 4.1"),
    ):
        paired("anthropic", model, name, "all",
               (214.286, 1071.429, 267.857, 21.429, 514.286),
               (214.286, 1071.429, 267.857, 21.429, 514.286))
    paired(
        "anthropic", "claude-sonnet-5", "Claude Sonnet 5", "all",
        (42.857, 214.286, 53.571, 4.286, 214.286),
        (47.143, 235.715, 58.928, 4.715, 235.715),
        promo_rates=(28.571, 142.857, 35.714, 2.857, 142.857),
        promo_end="2026-08-31",
        promo_label="Anthropic introductory launch pricing",
    )
    # Override the in-geo promotional values from the official table.
    rows[-1]["promo_rates"] = (31.428, 157.143, 39.285, 3.143, 157.143)
    for model, name in (
        ("claude-sonnet-4-5", "Claude Sonnet 4.5"),
        ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ):
        paired("anthropic", model, name, "all",
               (42.857, 214.286, 53.571, 4.286, 214.286),
               (47.143, 235.715, 58.928, 4.715, 235.715))
    paired("anthropic", "claude-sonnet-4", "Claude Sonnet 4", "all",
           (42.857, 214.286, 53.571, 4.286, 214.286),
           (42.857, 214.286, 53.571, 4.286, 214.286))
    paired("anthropic", "claude-haiku-4-5", "Claude Haiku 4.5", "all",
           (14.286, 71.429, 17.857, 1.429, 114.286),
           (15.715, 78.572, 19.643, 1.572, 125.714))

    # Google. The official table shows list rates; current promotional rates are
    # 20% lower through January 31, 2027.
    gemini_promo = {
        "promo_end": "2027-01-31",
        "promo_label": "Google 20% promotional discount",
    }

    def google(
        model: str,
        name: str,
        context: str,
        global_rates: tuple[float, float, float | None, float | None, float | None],
        in_geo_rates: tuple[float, float, float | None, float | None, float | None] | None = None,
        *,
        batch_status: str | None = None,
    ) -> None:
        in_geo_rates = in_geo_rates or global_rates

        def discounted(rates: tuple[float, float, float | None, float | None, float | None]):
            return tuple(
                round(value * 0.8, 6) if value is not None else None
                for value in rates
            )

        paired(
            "google", model, name, context, global_rates, in_geo_rates,
            promo_rates=discounted(global_rates),
            batch_status=batch_status,
            **gemini_promo,
        )
        rows[-1]["promo_rates"] = discounted(in_geo_rates)

    google("gemini-3-6-flash", "Gemini 3.6 Flash", "all",
           (26.786, 133.929, 26.786, 2.679, None),
           batch_status="coming_soon")
    google("gemini-3-5-flash-lite", "Gemini 3.5 Flash Lite", "all",
           (5.357, 44.643, 5.357, 0.536, None),
           (5.893, 49.107, 5.893, 0.589, None),
           batch_status="coming_soon")
    google("gemini-3-5-flash", "Gemini 3.5 Flash", "all",
           (26.786, 160.714, 26.786, 2.679, 196.429),
           (29.464, 176.786, 29.464, 2.946, 216.071))
    google("gemini-3-1-flash-lite", "Gemini 3.1 Flash Lite", "all",
           (4.464, 26.786, 4.464, 0.446, 89.286),
           (4.911, 29.464, 4.911, 0.491, 98.214))
    for model, name in (
        ("gemini-3-0-pro", "Gemini 3.0 Pro"),
        ("gemini-3-1-pro", "Gemini 3.1 Pro"),
    ):
        google(model, name, "short", (35.714, 214.286, 35.714, 3.571, 230.429))
        google(model, name, "long", (71.429, 321.429, 71.429, 7.143, 230.429))
    google("gemini-3-0-flash", "Gemini 3.0 Flash", "all",
           (8.929, 53.571, 8.929, 0.893, 125.0))
    google("gemini-2-5-pro", "Gemini 2.5 Pro", "short",
           (22.321, 178.571, 22.321, 2.232, 164.286))
    google("gemini-2-5-pro", "Gemini 2.5 Pro", "long",
           (44.643, 267.857, 44.643, 4.464, 164.286))
    google("gemini-2-5-flash", "Gemini 2.5 Flash", "all",
           (5.357, 44.643, 5.357, 0.536, 107.143))
    google("gemini-2-5-flash-lite", "Gemini 2.5 Flash Lite", "all",
           (1.786, 7.143, 1.786, 0.179, None))

    return rows


def build_proprietary_catalog(
    existing: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    catalog = _retire_existing(existing)
    sku_by_provider = {
        "openai": "OPENAI_MODEL_SERVING",
        "anthropic": "ANTHROPIC_MODEL_SERVING",
        "google": "GEMINI_MODEL_SERVING",
    }
    rate_names = (
        "input_token",
        "output_token",
        "cache_write",
        "cache_read",
        "batch_inference",
    )

    for row in _proprietary_rows():
        for cloud in CLOUDS:
            for index, (rate_type, dbu_rate) in enumerate(zip(rate_names, row["rates"])):
                if dbu_rate is None:
                    continue
                promo_rate = (
                    row["promo_rates"][index]
                    if row.get("promo_rates") is not None
                    else None
                )
                hourly = rate_type == "batch_inference"
                key = (
                    f"{cloud}:{row['provider']}:{row['model']}:"
                    f"{row['endpoint']}:{row['context']}:{rate_type}"
                )
                catalog[key] = _rate(
                    dbu_rate,
                    hourly=hourly,
                    sku=sku_by_provider[row["provider"]],
                    display_name=row["name"],
                    promotional_dbu_rate=promo_rate,
                    promotion_end_date=row.get("promo_end"),
                    promotion_label=row.get("promo_label"),
                    batch_status=row.get("batch_status"),
                    source="databricks_proprietary_foundation_model_serving",
                )

    return dict(sorted(catalog.items()))


def effective_dbu_rate(entry: dict[str, Any], as_of: date) -> float:
    promotional_rate = entry.get("promotional_dbu_rate")
    promotion_end = entry.get("promotion_end_date")
    if promotional_rate is not None and promotion_end:
        if as_of <= date.fromisoformat(promotion_end):
            return float(promotional_rate)
    return float(entry["dbu_rate"])


def _json_text(catalog: dict[str, dict[str, Any]]) -> str:
    return json.dumps(catalog, indent=2, sort_keys=True) + "\n"


def _csv_text(
    catalog: dict[str, dict[str, Any]],
    *,
    proprietary: bool,
    as_of: date,
) -> str:
    buffer = io.StringIO()
    if proprietary:
        columns = [
            "provider", "model", "endpoint_type", "context_length", "rate_type",
            "dbu_rate", "input_divisor", "is_hourly", "sku_product_type", "cloud",
        ]
    else:
        columns = [
            "cloud", "model", "rate_type", "dbu_rate", "input_divisor",
            "is_hourly", "sku_product_type",
        ]
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for key, entry in catalog.items():
        if entry.get("status") == "retired":
            continue
        parts = key.split(":")
        if proprietary:
            cloud, provider, model, endpoint, context, rate_type = parts
            row = {
                "provider": provider,
                "model": model,
                "endpoint_type": endpoint,
                "context_length": context,
                "rate_type": rate_type,
                "cloud": cloud.upper(),
            }
        else:
            cloud, model, rate_type = parts
            row = {
                "cloud": cloud.upper(),
                "model": model,
                "rate_type": rate_type,
            }
        row.update(
            {
                # Sync tables retain stable list prices. Promotions are
                # resolved from dated JSON metadata at runtime.
                "dbu_rate": entry["dbu_rate"],
                "input_divisor": entry["input_divisor"],
                "is_hourly": entry["is_hourly"],
                "sku_product_type": entry["sku_product_type"],
            }
        )
        writer.writerow(row)
    return buffer.getvalue()


def generate(as_of: date) -> dict[Path, str]:
    databricks = build_databricks_catalog(_load_existing(DB_JSON))
    proprietary = build_proprietary_catalog(_load_existing(PROP_JSON))
    return {
        DB_JSON: _json_text(databricks),
        DB_CSV: _csv_text(databricks, proprietary=False, as_of=as_of),
        PROP_JSON: _json_text(proprietary),
        PROP_CSV: _csv_text(proprietary, proprietary=True, as_of=as_of),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Date used to resolve promotional rates in CSV output (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    outputs = generate(args.as_of)
    stale: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(content)
            print(f"Wrote {path.relative_to(ROOT)}")

    if stale:
        print("Foundation model catalogs are stale:")
        for path in stale:
            print(f"  - {path}")
        return 1
    if args.check:
        print("Foundation model catalogs match the canonical source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
