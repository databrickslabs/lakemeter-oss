"""Shared Foundation Model API catalog lookup and effective-rate logic."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


_PRICING_DIR = Path(__file__).resolve().parents[2] / "static" / "pricing"


def _load_catalog(filename: str) -> dict[str, dict[str, Any]]:
    path = _PRICING_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text())


FMAPI_DATABRICKS_RATES = _load_catalog("fmapi-databricks-rates.json")
FMAPI_PROPRIETARY_RATES = _load_catalog("fmapi-proprietary-rates.json")

_PROVISIONED_ENTRY_REGIONS = {
    "aws": {
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "ca-central-1",
        "ca-west-1",
        "sa-east-1",
    },
    "azure": {
        "brazilsouth",
        "brazilsoutheast",
        "canadacentral",
        "canadaeast",
        "centralus",
        "eastus",
        "eastus2",
        "northcentralus",
        "southcentralus",
        "westcentralus",
        "westus",
        "westus2",
        "westus3",
    },
}


class FMAPIRateNotFound(ValueError):
    """Raised when a model pricing combination is unsupported."""


def get_effective_dbu_rate(
    rate: dict[str, Any],
    *,
    as_of: date | None = None,
) -> float:
    """Return the rate effective on a date, including time-limited promotions."""
    as_of = as_of or date.today()
    promotional_rate = rate.get("promotional_dbu_rate")
    promotion_end = rate.get("promotion_end_date")
    if promotional_rate is not None and promotion_end:
        if as_of <= date.fromisoformat(promotion_end):
            return float(promotional_rate)
    return float(rate["dbu_rate"])


def _get_rate(
    catalog: dict[str, dict[str, Any]],
    key: str,
    *,
    allow_retired: bool,
) -> dict[str, Any]:
    rate = catalog.get(key.lower())
    if not rate:
        raise FMAPIRateNotFound(f"Unsupported Foundation Model pricing combination: {key}")
    if rate.get("status", "active") == "retired" and not allow_retired:
        raise FMAPIRateNotFound(
            f"Retired Foundation Model pricing combination cannot be used for new estimates: {key}"
        )
    result = dict(rate)
    result["list_dbu_rate"] = float(rate["dbu_rate"])
    effective_rate = get_effective_dbu_rate(rate)
    result["dbu_rate"] = effective_rate
    result["effective_dbu_rate"] = effective_rate
    result["promotion_applied"] = effective_rate != result["list_dbu_rate"]
    return result


def get_databricks_rate(
    cloud: str,
    model: str,
    rate_type: str,
    *,
    region: str | None = None,
    processing_type: str = "global",
    allow_retired: bool = False,
) -> dict[str, Any]:
    key = f"{cloud}:{model}:{rate_type}"
    rate = _get_rate(
        FMAPI_DATABRICKS_RATES,
        key,
        allow_retired=allow_retired,
    )
    if (
        region
        and rate_type.startswith("provisioned_entry")
        and region.lower() not in _PROVISIONED_ENTRY_REGIONS.get(cloud.lower(), set())
    ):
        raise FMAPIRateNotFound(
            "Provisioned Entry is available only in supported AWS and Azure "
            f"regions in the Americas, not {cloud}:{region}"
        )

    processing_type = processing_type.lower()
    if processing_type not in {"global", "regional"}:
        raise FMAPIRateNotFound(
            f"Unsupported Databricks-hosted processing type: {processing_type}"
        )
    if processing_type == "regional":
        uplift = rate.get("regional_uplift_percent")
        if not uplift:
            raise FMAPIRateNotFound(
                f"Regional processing is not published for {cloud}:{model}:{rate_type}"
            )
        rate["dbu_rate"] = round(rate["dbu_rate"] * (1 + float(uplift) / 100), 6)
        rate["regional_uplift_applied"] = True
    else:
        rate["regional_uplift_applied"] = False
    return rate


def get_proprietary_rate(
    cloud: str,
    provider: str,
    model: str,
    endpoint_type: str,
    context_length: str,
    rate_type: str,
    *,
    allow_retired: bool = False,
) -> dict[str, Any]:
    key = (
        f"{cloud}:{provider}:{model}:{endpoint_type}:"
        f"{context_length}:{rate_type}"
    )
    return _get_rate(
        FMAPI_PROPRIETARY_RATES,
        key,
        allow_retired=allow_retired,
    )


def active_databricks_models() -> list[dict[str, str]]:
    """Return active Databricks-hosted models with display metadata."""
    models: dict[str, str] = {}
    for key, rate in FMAPI_DATABRICKS_RATES.items():
        cloud, model, _rate_type = key.split(":")
        if cloud == "aws" and rate.get("status", "active") == "active":
            models[model] = rate.get("display_name", model)
    return [
        {"id": model, "name": display_name}
        for model, display_name in sorted(models.items(), key=lambda pair: pair[1])
    ]


def active_proprietary_models() -> dict[str, list[dict[str, str]]]:
    """Return active proprietary models grouped by provider."""
    models: dict[str, dict[str, str]] = {}
    for key, rate in FMAPI_PROPRIETARY_RATES.items():
        cloud, provider, model, _endpoint, _context, _rate_type = key.split(":")
        if cloud != "aws" or rate.get("status", "active") != "active":
            continue
        models.setdefault(provider, {})[model] = rate.get("display_name", model)
    return {
        provider: [
            {"id": model, "name": display_name}
            for model, display_name in sorted(
                provider_models.items(),
                key=lambda pair: pair[1],
            )
        ]
        for provider, provider_models in sorted(models.items())
    }
