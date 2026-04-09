"""Discount helper functions — ported from old API (async→sync)."""
import logging
from typing import Union

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def infer_discount_category(sku: str) -> str:
    sku_upper = sku.upper()
    if sku_upper.startswith("VM_"):
        return "vm"
    if sku_upper.startswith("STORAGE_"):
        return "storage"
    if "SUPPORT" in sku_upper:
        return "support"
    if "ENHANCED_SECURITY" in sku_upper:
        return "platform_addon"
    return "dbu"


def get_discount_category_from_db(sku: str, db: Session) -> tuple:
    """Returns (discount_category, cross_service_eligible)."""
    try:
        query = text("""
            SELECT discount_category, COALESCE(cross_service_eligible, TRUE)
            FROM lakemeter.sku_discount_mapping
            WHERE sku = :sku
        """)
        row = db.execute(query, {"sku": sku}).fetchone()
        if row:
            return (row[0], bool(row[1]))
        logger.warning(f"SKU '{sku}' not found in sku_discount_mapping, inferring category")
        return (infer_discount_category(sku), True)
    except Exception as e:
        logger.error(f"Error querying discount category for SKU '{sku}': {e}")
        return (infer_discount_category(sku), True)


def get_discount_for_sku(
    sku: str,
    discount_config,
    db: Session,
) -> tuple:
    """Returns (discount_percentage, source_label)."""
    if not discount_config:
        return (0.0, "none")

    if hasattr(discount_config, "sku_specific"):
        sku_specific = discount_config.sku_specific
        global_discounts = discount_config.global_discounts
    else:
        sku_specific = discount_config.get("sku_specific", {})
        global_discounts = discount_config.get("global", {})

    # 1. Exact SKU match always wins
    if sku in sku_specific:
        return (float(sku_specific[sku]), f"sku_specific:{sku}")

    # 2. Look up category + cross-service eligibility
    category, cross_service_eligible = get_discount_category_from_db(sku, db)

    def _get_global(field: str) -> float:
        if hasattr(global_discounts, field):
            return float(getattr(global_discounts, field))
        return float(global_discounts.get(field, 0))

    if category == "dbu":
        if not cross_service_eligible:
            return (0.0, "global:dbu:excluded_from_cross_service")
        return (_get_global("dbu_discount"), "global:dbu")
    elif category == "vm":
        return (_get_global("vm_discount"), "global:vm")
    elif category == "storage":
        return (_get_global("storage_discount"), "global:storage")
    elif category == "platform_addon":
        return (_get_global("platform_addon_discount"), "global:platform_addon")
    elif category == "support":
        return (_get_global("support_discount"), "global:support")

    return (0.0, "none")


def apply_discount_to_sku_breakdown(
    sku_breakdown: list,
    discount_config,
    db: Session,
) -> list:
    if not discount_config or not sku_breakdown:
        return sku_breakdown

    enhanced_breakdown = []
    for item in sku_breakdown:
        sku = item["sku"]
        original_cost = item["cost"]
        unit_price = item["unit_price_before_discount"]

        discount_pct, discount_source = get_discount_for_sku(sku, discount_config, db)

        discount_amount = original_cost * (discount_pct / 100)
        discounted_cost = original_cost - discount_amount
        discounted_unit_price = unit_price * (1 - discount_pct / 100)

        enhanced_item = {
            **item,
            "cost_after_discount": round(discounted_cost, 2),
            "unit_price_after_discount": round(discounted_unit_price, 6),
            "discount": {
                "percentage": discount_pct,
                "amount": round(discount_amount, 2),
                "source": discount_source,
            },
        }
        enhanced_breakdown.append(enhanced_item)

    return enhanced_breakdown


def calculate_total_discount_summary(sku_breakdown: list) -> dict:
    total_before = 0.0
    total_after = 0.0
    for item in sku_breakdown:
        total_before += item["cost"]
        total_after += item.get("cost_after_discount", item["cost"])

    total_discount = total_before - total_after
    total_discount_pct = (total_discount / total_before * 100) if total_before > 0 else 0

    return {
        "total_cost_before_discount": round(total_before, 2),
        "total_cost_after_discount": round(total_after, 2),
        "total_discount_amount": round(total_discount, 2),
        "total_discount_percentage": round(total_discount_pct, 2),
        "discount_applied": total_discount > 0,
    }


def enhance_total_cost_with_discount(total_cost: dict, sku_breakdown: list) -> dict:
    by_type = {}
    for item in sku_breakdown:
        item_type = item["type"]
        if item_type not in by_type:
            by_type[item_type] = {"cost_before": 0, "cost_after": 0, "discount_amount": 0}
        by_type[item_type]["cost_before"] += item["cost"]
        by_type[item_type]["cost_after"] += item.get("cost_after_discount", item["cost"])
        by_type[item_type]["discount_amount"] += item.get("discount", {}).get("amount", 0)

    enhanced = total_cost.copy()

    if "breakdown" in total_cost:
        breakdown_after_discount = {}
        for key in total_cost["breakdown"]:
            type_key = key.replace("_cost", "")
            if type_key in by_type:
                breakdown_after_discount[key] = round(by_type[type_key]["cost_after"], 2)
            else:
                breakdown_after_discount[key] = total_cost["breakdown"][key]
        enhanced["breakdown_after_discount"] = breakdown_after_discount

        discount_by_category = {}
        for key in total_cost["breakdown"]:
            type_key = key.replace("_cost", "")
            if type_key in by_type and by_type[type_key]["discount_amount"] > 0:
                cost_before = by_type[type_key]["cost_before"]
                discount_amt = by_type[type_key]["discount_amount"]
                discount_pct = (discount_amt / cost_before * 100) if cost_before > 0 else 0
                discount_by_category[type_key] = {"amount": round(discount_amt, 2), "percentage": round(discount_pct, 2)}
            else:
                discount_by_category[type_key] = {"amount": 0, "percentage": 0}
        enhanced["discount_by_category"] = discount_by_category
    else:
        breakdown_after_discount = {}
        discount_by_category = {}
        for type_key, data in by_type.items():
            cost_key = f"{type_key}_cost"
            breakdown_after_discount[cost_key] = round(data["cost_after"], 2)
            if data["discount_amount"] > 0:
                discount_pct = (data["discount_amount"] / data["cost_before"] * 100) if data["cost_before"] > 0 else 0
                discount_by_category[type_key] = {"amount": round(data["discount_amount"], 2), "percentage": round(discount_pct, 2)}
        enhanced["breakdown_after_discount"] = breakdown_after_discount
        enhanced["discount_by_category"] = discount_by_category

    total_cost_before = sum(item["cost"] for item in sku_breakdown)
    total_cost_after = sum(item.get("cost_after_discount", item["cost"]) for item in sku_breakdown)
    total_discount = total_cost_before - total_cost_after
    effective_discount_pct = (total_discount / total_cost_before * 100) if total_cost_before > 0 else 0

    enhanced["total_after_discount"] = round(total_cost_after, 2)
    enhanced["total_discount"] = round(total_discount, 2)
    enhanced["effective_discount_percentage"] = round(effective_discount_pct, 2)

    excluded_skus = [
        item["sku"]
        for item in sku_breakdown
        if item.get("discount", {}).get("source", "").endswith("excluded_from_cross_service")
    ]
    if excluded_skus:
        enhanced["cross_service_exclusions"] = {
            "excluded_skus": excluded_skus,
            "reason": (
                "These SKUs are excluded from the cross-service (dbu_discount) per "
                "https://www.databricks.com/product/sku-groups#exclusions. "
                "To discount them, add each SKU to sku_specific."
            ),
        }

    return enhanced
