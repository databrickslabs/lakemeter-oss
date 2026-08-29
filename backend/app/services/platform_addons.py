"""Estimate-level Databricks Platform add-on pricing."""

from __future__ import annotations

import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "static"
    / "pricing"
    / "platform-addons.json"
)


@lru_cache(maxsize=1)
def load_platform_addon_catalog() -> dict[str, Any]:
    """Load the curated percentage-based Platform add-on catalog."""
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def _pricing_date(value: date | str | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def get_selected_platform_addon(
    discount_config: dict[str, Any] | None,
) -> str | None:
    """Read the estimate-level add-on selection from its JSON envelope."""
    if not discount_config or not isinstance(discount_config, dict):
        return None
    selections = discount_config.get("platform_addons", [])
    if selections in (None, []):
        return None
    if not isinstance(selections, list):
        raise ValueError("discount_config.platform_addons must be a list")
    if len(selections) > 1:
        raise ValueError(
            "Select only one Platform add-on; Mission Critical already includes "
            "Enhanced Security and Compliance"
        )
    selection = selections[0]
    if not isinstance(selection, str):
        raise ValueError("Platform add-on identifiers must be strings")
    return selection.upper()


def get_platform_addon_discount(
    discount_config: dict[str, Any] | None,
) -> float:
    """Read the negotiated discount applied after the add-on uplift."""
    if not discount_config or not isinstance(discount_config, dict):
        return 0.0
    global_discounts = discount_config.get("global", {})
    if not isinstance(global_discounts, dict):
        return 0.0
    value = float(global_discounts.get("platform_addon_discount", 0) or 0)
    if not math.isfinite(value) or value < 0 or value > 100:
        raise ValueError(
            "global.platform_addon_discount must be between 0 and 100"
        )
    return value


def get_platform_addon_rate(
    addon_type: str,
    cloud: str,
    tier: str,
    pricing_date: date | str | None = None,
) -> dict[str, Any]:
    """Resolve availability and the active published uplift."""
    catalog = load_platform_addon_catalog()
    addon_key = (addon_type or "").upper()
    cloud_key = (cloud or "").upper()
    tier_key = (tier or "").upper()
    addon = catalog["addons"].get(addon_key)
    if addon is None:
        raise ValueError(f"Unknown Platform add-on: {addon_type}")

    cloud_config = addon.get("clouds", {}).get(cloud_key)
    if cloud_config is None:
        raise ValueError(
            f"{addon['display_name']} is not available on {cloud_key or 'this cloud'}"
        )
    eligible_tiers = [value.upper() for value in cloud_config["eligible_tiers"]]
    if tier_key not in eligible_tiers:
        required = " or ".join(eligible_tiers)
        raise ValueError(
            f"{addon['display_name']} requires {required} tier on {cloud_key}"
        )

    as_of = _pricing_date(pricing_date)
    standard_rate = float(cloud_config["standard_rate_pct"])
    applied_rate = standard_rate
    promotion = cloud_config.get("promotion")
    active_promotion = None
    if promotion:
        promotion_end = date.fromisoformat(promotion["end_date"])
        if as_of <= promotion_end:
            applied_rate = float(promotion["rate_pct"])
            active_promotion = {
                **promotion,
                "rate_pct": applied_rate,
            }

    return {
        "addon_type": addon_key,
        "display_name": addon["display_name"],
        "sku": addon["sku"],
        "cloud": cloud_key,
        "tier": tier_key,
        "standard_rate_pct": standard_rate,
        "applied_rate_pct": applied_rate,
        "promotion": active_promotion,
        "basis": catalog["basis"],
        "as_of_date": as_of.isoformat(),
        "source_url": catalog["source_url"],
    }


def validate_platform_addon_selection(
    discount_config: dict[str, Any] | None,
    cloud: str,
    tier: str,
) -> str | None:
    """Validate a saved selection against its estimate cloud and tier."""
    selected = get_selected_platform_addon(discount_config)
    if selected:
        get_platform_addon_rate(selected, cloud, tier)
    return selected


def calculate_platform_addon_cost(
    product_spend_at_list: float,
    addon_type: str,
    cloud: str,
    tier: str,
    pricing_date: date | str | None = None,
    discount_pct: float = 0,
) -> dict[str, Any]:
    """Calculate an add-on from pre-discount Databricks product spend."""
    spend = float(product_spend_at_list)
    if not math.isfinite(spend) or spend < 0:
        raise ValueError("product_spend_at_list must be a non-negative finite number")
    discount = float(discount_pct)
    if not math.isfinite(discount) or discount < 0 or discount > 100:
        raise ValueError("discount_pct must be between 0 and 100")

    rate = get_platform_addon_rate(
        addon_type,
        cloud,
        tier,
        pricing_date=pricing_date,
    )
    standard_cost = spend * rate["standard_rate_pct"] / 100
    cost_before_discount = spend * rate["applied_rate_pct"] / 100
    discount_amount = cost_before_discount * discount / 100
    applied_cost = cost_before_discount - discount_amount
    return {
        **rate,
        "product_spend_at_list": spend,
        "standard_cost": standard_cost,
        "cost_before_discount": cost_before_discount,
        "discount_pct": discount,
        "discount_amount": discount_amount,
        "cost": applied_cost,
    }
