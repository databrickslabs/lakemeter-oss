"""Lakebase autoscaling pricing helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALWAYS_ON_HOURS_PER_MONTH = 730.0
LAKEBASE_ALWAYS_ON_DISCOUNT_PCT = 25.0
LAKEBASE_AUTOSCALE_CU_VALUES = [
    0.5, 1, 2, 4, 8, 12, 16, 24, 28, 32, 40, 48, 56, 64,
]
LAKEBASE_MAX_AUTOSCALE_SPREAD_CU = 16.0


def cap_max_cu(min_cu: float, max_cu: float | None = None) -> float:
    """Largest documented autoscale CU where max - min <= 16."""
    capped = min_cu
    for cu in LAKEBASE_AUTOSCALE_CU_VALUES:
        if cu >= min_cu and cu - min_cu <= LAKEBASE_MAX_AUTOSCALE_SPREAD_CU:
            capped = cu
    if max_cu is not None and max_cu >= min_cu:
        return min(max_cu, capped)
    return capped


@dataclass(frozen=True)
class LakebaseAutoscaleConfig:
    compute_mode: str
    min_cu: float
    max_cu: float
    scale_to_zero_enabled: bool
    active_hours_per_month: float
    scale_up_hours_per_month: float
    always_on_discount_pct: float


@dataclass(frozen=True)
class LakebaseComputeUsage:
    config: LakebaseAutoscaleConfig
    nodes: float
    dbu_per_cu_hour: float
    baseline_cu: float
    baseline_hours: float
    baseline_discount_pct: float
    baseline_effective_dbu_per_cu_hour: float
    scale_up_effective_dbu_per_cu_hour: float
    baseline_dbu: float
    billable_baseline_dbu: float
    scale_up_cu: float
    scale_up_hours: float
    scale_up_dbu: float
    total_raw_dbu: float
    total_billable_dbu: float
    raw_equivalent_dbu_per_hour: float
    equivalent_dbu_per_hour: float


def _as_float(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _get_config_value(config: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in config:
            return config[key]
    return None


def resolve_lakebase_autoscale_config(
    workload_config: Mapping[str, Any] | None,
    legacy_cu: Any,
    hours_per_month: Any = None,
) -> LakebaseAutoscaleConfig:
    """Resolve new autoscaling fields with fallback to the legacy single-CU field."""
    config = workload_config or {}
    legacy_cu_value = _as_float(legacy_cu, 1.0)
    compute_mode = _get_config_value(config, "lakebase_compute_mode", "compute_mode")
    compute_mode = "fixed" if compute_mode == "fixed" or legacy_cu_value > 64 else "autoscale"
    min_cu = _as_float(_get_config_value(config, "lakebase_min_cu", "min_cu"), legacy_cu_value)
    max_cu = _as_float(_get_config_value(config, "lakebase_max_cu", "max_cu"), min_cu)
    if max_cu < min_cu:
        max_cu = min_cu
    if compute_mode == "fixed" or min_cu > 64 or max_cu > 64:
        fixed_cu = max_cu if max_cu > 64 else min_cu
        min_cu = fixed_cu
        max_cu = fixed_cu
    elif max_cu - min_cu > LAKEBASE_MAX_AUTOSCALE_SPREAD_CU:
        max_cu = cap_max_cu(min_cu)

    scale_to_zero_enabled = _as_bool(
        _get_config_value(config, "lakebase_scale_to_zero_enabled", "scale_to_zero_enabled"),
        False,
    )
    active_hours = _as_float(
        _get_config_value(config, "lakebase_active_hours_per_month", "active_hours_per_month"),
        _as_float(hours_per_month, ALWAYS_ON_HOURS_PER_MONTH),
    )
    scale_up_hours = _as_float(
        _get_config_value(config, "lakebase_scale_up_hours_per_month", "scale_up_hours_per_month"),
        0.0,
    )
    scale_up_hours = max(0.0, min(scale_up_hours, active_hours))
    discount_pct = _as_float(
        _get_config_value(config, "lakebase_always_on_discount_pct", "always_on_discount_pct"),
        LAKEBASE_ALWAYS_ON_DISCOUNT_PCT,
    )

    return LakebaseAutoscaleConfig(
        compute_mode=compute_mode,
        min_cu=max(0.0, min_cu),
        max_cu=max(0.0, max_cu),
        scale_to_zero_enabled=scale_to_zero_enabled,
        active_hours_per_month=max(0.0, active_hours),
        scale_up_hours_per_month=scale_up_hours,
        always_on_discount_pct=max(0.0, min(discount_pct, 100.0)),
    )


def calculate_lakebase_compute_usage(
    config: LakebaseAutoscaleConfig,
    dbu_per_cu_hour: float,
    nodes: Any,
) -> LakebaseComputeUsage:
    node_count = max(1.0, _as_float(nodes, 1.0))
    scale_up_cu = config.max_cu

    if config.scale_to_zero_enabled:
        baseline_cu = config.min_cu
        baseline_hours = max(0.0, config.active_hours_per_month - config.scale_up_hours_per_month)
        baseline_discount_pct = 0.0
    else:
        baseline_cu = config.min_cu
        baseline_hours = max(0.0, ALWAYS_ON_HOURS_PER_MONTH - config.scale_up_hours_per_month)
        baseline_discount_pct = config.always_on_discount_pct

    baseline_effective_dbu_per_cu_hour = dbu_per_cu_hour * (1 - baseline_discount_pct / 100)
    scale_up_effective_dbu_per_cu_hour = dbu_per_cu_hour
    baseline_dbu = baseline_cu * dbu_per_cu_hour * node_count * baseline_hours
    billable_baseline_dbu = baseline_cu * baseline_effective_dbu_per_cu_hour * node_count * baseline_hours
    scale_up_dbu = scale_up_cu * dbu_per_cu_hour * node_count * config.scale_up_hours_per_month
    total_raw_dbu = baseline_dbu + scale_up_dbu
    total_billable_dbu = billable_baseline_dbu + scale_up_dbu

    denominator_hours = (
        config.active_hours_per_month
        if config.scale_to_zero_enabled
        else ALWAYS_ON_HOURS_PER_MONTH
    )
    raw_equivalent_dbu_per_hour = total_raw_dbu / denominator_hours if denominator_hours > 0 else 0.0
    equivalent_dbu_per_hour = total_billable_dbu / denominator_hours if denominator_hours > 0 else 0.0

    return LakebaseComputeUsage(
        config=config,
        nodes=node_count,
        dbu_per_cu_hour=dbu_per_cu_hour,
        baseline_cu=baseline_cu,
        baseline_hours=baseline_hours,
        baseline_discount_pct=baseline_discount_pct,
        baseline_effective_dbu_per_cu_hour=baseline_effective_dbu_per_cu_hour,
        scale_up_effective_dbu_per_cu_hour=scale_up_effective_dbu_per_cu_hour,
        baseline_dbu=baseline_dbu,
        billable_baseline_dbu=billable_baseline_dbu,
        scale_up_cu=scale_up_cu,
        scale_up_hours=config.scale_up_hours_per_month,
        scale_up_dbu=scale_up_dbu,
        total_raw_dbu=total_raw_dbu,
        total_billable_dbu=total_billable_dbu,
        raw_equivalent_dbu_per_hour=raw_equivalent_dbu_per_hour,
        equivalent_dbu_per_hour=equivalent_dbu_per_hour,
    )
