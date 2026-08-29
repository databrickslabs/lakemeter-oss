"""Canonical Zerobus Ingest usage and availability rules."""
import math


ZEROBUS_SKU = "JOBS_SERVERLESS_COMPUTE"
ZEROBUS_DBU_PER_GB = {
    "standard": 0.143,
    "otel": 0.222,
}
ZEROBUS_MODE_NAMES = {
    "standard": "Zerobus Ingest",
    "otel": "Zerobus OTel Ingest",
}
ZEROBUS_SUPPORTED_TIERS = {
    "AWS": {"PREMIUM", "ENTERPRISE"},
    "AZURE": {"PREMIUM"},
    "GCP": {"PREMIUM", "ENTERPRISE"},
}


def normalize_zerobus_mode(mode: str) -> str:
    """Normalize the public Zerobus mode aliases."""
    normalized = (mode or "").strip().lower()
    aliases = {
        "normal": "standard",
        "grpc": "standard",
        "http": "standard",
        "opentelemetry": "otel",
        "otlp": "otel",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in ZEROBUS_DBU_PER_GB:
        raise ValueError("zerobus_mode must be standard or otel")
    return normalized


def validate_zerobus_availability(cloud: str, tier: str) -> None:
    """Require a cloud/tier combination published for Zerobus pricing."""
    normalized_cloud = (cloud or "").strip().upper()
    normalized_tier = (tier or "").strip().upper()
    supported_tiers = ZEROBUS_SUPPORTED_TIERS.get(normalized_cloud)
    if not supported_tiers or normalized_tier not in supported_tiers:
        supported = ", ".join(sorted(supported_tiers or ()))
        detail = (
            f" Supported tiers for {normalized_cloud}: {supported}."
            if supported
            else ""
        )
        raise ValueError(
            "Zerobus pricing is not available for "
            f"{normalized_cloud} {normalized_tier}.{detail}"
        )


def calculate_zerobus_usage(
    monthly_ingested_gb: float,
    mode: str,
) -> dict:
    """Convert monthly Zerobus ingress volume into Jobs Serverless DBUs."""
    numeric_gb = float(monthly_ingested_gb)
    if not math.isfinite(numeric_gb):
        raise ValueError("zerobus_monthly_ingested_gb must be finite")
    if numeric_gb < 0:
        raise ValueError(
            "zerobus_monthly_ingested_gb must be greater than or equal to 0"
        )

    normalized_mode = normalize_zerobus_mode(mode)
    dbu_per_gb = ZEROBUS_DBU_PER_GB[normalized_mode]
    return {
        "mode": normalized_mode,
        "mode_display_name": ZEROBUS_MODE_NAMES[normalized_mode],
        "monthly_ingested_gb": numeric_gb,
        "dbu_per_gb": dbu_per_gb,
        "monthly_dbus": numeric_gb * dbu_per_gb,
    }
