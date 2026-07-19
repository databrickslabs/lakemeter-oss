from app.services.lakebase_pricing import (
    ALWAYS_ON_HOURS_PER_MONTH,
    calculate_lakebase_compute_usage,
    resolve_lakebase_autoscale_config,
)


def test_always_on_floor_gets_discount_but_scale_up_does_not():
    config = resolve_lakebase_autoscale_config(
        {
            "lakebase_min_cu": 4,
            "lakebase_max_cu": 8,
            "lakebase_scale_to_zero_enabled": False,
            "lakebase_scale_up_hours_per_month": 100,
            "lakebase_always_on_discount_pct": 25,
        },
        legacy_cu=4,
    )

    usage = calculate_lakebase_compute_usage(config, dbu_per_cu_hour=0.213, nodes=1)

    assert config.max_cu == 8
    assert usage.baseline_hours == ALWAYS_ON_HOURS_PER_MONTH - 100
    assert usage.baseline_dbu == 4 * 0.213 * (ALWAYS_ON_HOURS_PER_MONTH - 100)
    assert usage.billable_baseline_dbu == usage.baseline_dbu * 0.75
    assert usage.scale_up_dbu == 8 * 0.213 * 100
    assert usage.total_raw_dbu == usage.baseline_dbu + usage.scale_up_dbu
    assert usage.total_billable_dbu == usage.billable_baseline_dbu + usage.scale_up_dbu


def test_scale_to_zero_active_hours_do_not_get_always_on_discount():
    config = resolve_lakebase_autoscale_config(
        {
            "lakebase_min_cu": 4,
            "lakebase_max_cu": 8,
            "lakebase_scale_to_zero_enabled": True,
            "lakebase_active_hours_per_month": 200,
            "lakebase_scale_up_hours_per_month": 50,
            "lakebase_always_on_discount_pct": 25,
        },
        legacy_cu=4,
    )

    usage = calculate_lakebase_compute_usage(config, dbu_per_cu_hour=0.213, nodes=1)

    assert config.max_cu == 8
    assert usage.baseline_hours == 150
    assert usage.baseline_discount_pct == 0
    assert usage.billable_baseline_dbu == 4 * 0.213 * 150
    assert usage.scale_up_dbu == 8 * 0.213 * 50
    assert usage.total_raw_dbu == usage.total_billable_dbu


def test_explicit_range_over_16_cu_is_capped():
    from app.services.lakebase_pricing import cap_max_cu

    config = resolve_lakebase_autoscale_config(
        {
            "lakebase_min_cu": 40,
            "lakebase_max_cu": 64,
            "lakebase_scale_to_zero_enabled": False,
        },
        legacy_cu=40,
    )

    assert config.max_cu == cap_max_cu(40)
    assert config.max_cu == 56


def test_legacy_single_cu_defaults_to_discounted_always_on_floor():
    config = resolve_lakebase_autoscale_config(None, legacy_cu=2)
    usage = calculate_lakebase_compute_usage(config, dbu_per_cu_hour=0.213, nodes=1)

    assert config.min_cu == 2
    assert config.max_cu == 2
    assert config.scale_to_zero_enabled is False
    assert usage.scale_up_dbu == 0
    assert usage.total_raw_dbu == 2 * 0.213 * ALWAYS_ON_HOURS_PER_MONTH
    assert usage.billable_baseline_dbu == 2 * 0.213 * ALWAYS_ON_HOURS_PER_MONTH * 0.75
