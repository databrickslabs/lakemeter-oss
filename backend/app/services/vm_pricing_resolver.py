"""Canonical VM price resolution for calculators and exports."""
from dataclasses import dataclass
from typing import Mapping

from sqlalchemy import text


@dataclass(frozen=True)
class VMPriceResolution:
    rate: float
    source: str
    warning: str | None = None


def resolve_vm_hourly_rate(
    db,
    *,
    cloud: str,
    region: str,
    instance_type: str,
    pricing_tier: str,
    payment_option: str | None = None,
    fallback_prices: Mapping[str, float] | None = None,
) -> VMPriceResolution:
    """Resolve an exact regional VM rate, with an explicit conservative fallback."""
    cloud_upper = (cloud or "").strip().upper()
    region_value = (region or "").strip()
    instance_value = (instance_type or "").strip()
    tier_value = (pricing_tier or "on_demand").strip().lower()
    payment_value = _normalize_payment_option(
        cloud_upper,
        tier_value,
        payment_option,
    )
    fallback_prices = fallback_prices or {}

    lookup_failed = False
    if db is not None and instance_value:
        try:
            row = db.execute(
                text(
                    """
                    SELECT cost_per_hour, source
                    FROM lakemeter.sync_pricing_vm_costs
                    WHERE UPPER(cloud) = :cloud
                      AND LOWER(region) = LOWER(:region)
                      AND LOWER(instance_type) = LOWER(:instance_type)
                      AND LOWER(pricing_tier) = :pricing_tier
                      AND UPPER(payment_option) = UPPER(:payment_option)
                    LIMIT 1
                    """
                ),
                {
                    "cloud": cloud_upper,
                    "region": region_value,
                    "instance_type": instance_value,
                    "pricing_tier": tier_value,
                    "payment_option": payment_value,
                },
            ).fetchone()
            if row and row.cost_per_hour is not None:
                source = getattr(row, "source", None) or "database"
                return VMPriceResolution(
                    rate=float(row.cost_per_hour),
                    source=source,
                    warning=_source_warning(source),
                )
        except Exception:
            lookup_failed = True

    if tier_value in fallback_prices:
        warning = _fallback_warning(
            cloud_upper,
            region_value,
            instance_value,
            tier_value,
            payment_value,
            lookup_failed,
            "using a non-regional fallback rate",
        )
        return VMPriceResolution(
            rate=float(fallback_prices[tier_value]),
            source="static_exact_tier",
            warning=warning,
        )

    on_demand = float(fallback_prices.get("on_demand", 0))
    warning = _fallback_warning(
        cloud_upper,
        region_value,
        instance_value,
        tier_value,
        payment_value,
        lookup_failed,
        "using on-demand as a conservative fallback",
    )
    return VMPriceResolution(
        rate=on_demand,
        source="static_on_demand_fallback",
        warning=warning,
    )


def _normalize_payment_option(
    cloud: str,
    pricing_tier: str,
    payment_option: str | None,
) -> str:
    if pricing_tier not in {"reserved_1y", "reserved_3y"}:
        return "NA"
    value = (payment_option or "NA").strip()
    if cloud != "AWS":
        return "NA"
    # The AWS UI defaults reserved pricing to No Upfront. Older DBSQL records
    # may still contain NA because the select displayed its first option
    # without updating the stored value.
    if not value or value.upper() == "NA":
        return "no_upfront"
    return value


def _fallback_warning(
    cloud: str,
    region: str,
    instance_type: str,
    pricing_tier: str,
    payment_option: str,
    lookup_failed: bool,
    fallback_message: str,
) -> str:
    reason = "VM pricing lookup failed" if lookup_failed else "Exact VM rate not found"
    return (
        f"{reason} for {cloud}/{region}/{instance_type} "
        f"{pricing_tier}/{payment_option}; {fallback_message}"
    )


def _source_warning(source: str) -> str | None:
    source_lower = source.lower()
    if "estimated" in source_lower or "deprecated" in source_lower:
        return f"VM rate uses estimated pricing source: {source}"
    return None
