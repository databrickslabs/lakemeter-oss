"""Item-level calculation and storage sub-row helpers for Excel export."""
from .pricing import _get_dbu_price, _get_fmapi_dbu_per_million
from .calculations import _calculate_hours_per_month
from .excel_row_writer import write_data_row


# Token type display map for FMAPI token-based rate types
TOKEN_TYPE_DISPLAY = {
    'input_token': 'Input', 'input': 'Input',
    'output_token': 'Output', 'output': 'Output',
    'cache_read': 'Cache Read', 'cache_write': 'Cache Write',
    'batch_inference': 'Batch',
}

def _get_json_backed_value(item, field, default=None):
    """Read a public field from an attribute or workload_config."""
    value = getattr(item, field, None)
    if value is not None:
        return value
    workload_config = getattr(item, 'workload_config', None) or {}
    return workload_config.get(field, default)


def get_ai_gateway_usage(item):
    """Calculate independent AI Gateway component usage from one line item."""
    from app.routes.calculate.ai_gateway_calc import (
        calculate_ai_gateway_usage,
    )

    values = {}
    for component in ("inference_tables", "usage_tracking"):
        values[f"{component}_enabled"] = bool(_get_json_backed_value(
            item,
            f"ai_gateway_{component}_enabled",
            False,
        ))
        for suffix in (
            "input_method",
            "requests_millions",
            "avg_request_payload_kb",
            "avg_response_payload_kb",
            "monthly_payload_gb",
        ):
            values[f"{component}_{suffix}"] = _get_json_backed_value(
                item,
                f"ai_gateway_{component}_{suffix}",
            )
    return calculate_ai_gateway_usage(**values)


def get_agent_evaluation_usage(item):
    """Calculate Agent Evaluation dimensions from one line item."""
    from app.routes.calculate.agent_evaluation_calc import (
        calculate_agent_evaluation_usage,
    )

    return calculate_agent_evaluation_usage(
        labels_enabled=bool(_get_json_backed_value(
            item,
            "agent_evaluation_labels_enabled",
            False,
        )),
        input_tokens_millions=float(_get_json_backed_value(
            item,
            "agent_evaluation_input_tokens_millions",
            0,
        ) or 0),
        output_tokens_millions=float(_get_json_backed_value(
            item,
            "agent_evaluation_output_tokens_millions",
            0,
        ) or 0),
        synthetic_data_enabled=bool(_get_json_backed_value(
            item,
            "agent_evaluation_synthetic_data_enabled",
            False,
        )),
        synthetic_questions=_get_json_backed_value(
            item,
            "agent_evaluation_synthetic_questions",
            0,
        ) or 0,
    )


def get_zerobus_usage(item):
    """Calculate Zerobus DBUs from JSON-backed monthly ingestion fields."""
    from app.services.zerobus_pricing import calculate_zerobus_usage

    return calculate_zerobus_usage(
        _get_json_backed_value(
            item,
            "zerobus_monthly_ingested_gb",
            0,
        ),
        _get_json_backed_value(item, "zerobus_mode", "standard"),
    )


def get_ai_search_reranker_usage(item):
    """Calculate optional AI Search Reranker usage from one line item."""
    from app.routes.calculate.vector_search_calc import (
        AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS,
    )

    enabled = bool(_get_json_backed_value(
        item,
        "ai_search_reranker_enabled",
        False,
    ))
    requests_thousands = float(_get_json_backed_value(
        item,
        "ai_search_reranker_requests_thousands",
        0,
    ) or 0)
    return {
        "enabled": enabled,
        "requests_thousands": requests_thousands,
        "dbu_per_thousand_requests": (
            AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
        ),
        "monthly_dbus": (
            requests_thousands
            * AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
            if enabled
            else 0
        ),
    }


def write_general_storage_row(
    sheet,
    fmt,
    row,
    item,
    idx,
    cloud,
    dsu_price,
    cost_accumulator=None,
):
    """Write stored-data and operation components as separate DSU rows."""
    from app.services.general_storage_pricing import (
        calculate_general_storage_usage,
    )

    usage = calculate_general_storage_usage(
        _get_json_backed_value(item, 'general_storage_quantity', 0),
        _get_json_backed_value(item, 'general_storage_unit', 'gb'),
        cloud,
        _get_json_backed_value(
            item,
            'general_storage_tier1_operations_thousands',
            0,
        ),
        _get_json_backed_value(
            item,
            'general_storage_tier2_operations_thousands',
            0,
        ),
    )
    quantity = usage['quantity']
    unit = usage['unit'].upper()
    billable_gb = usage['billable_gb_months']
    workload_name = getattr(
        item,
        'workload_name',
        f'Workload {idx + 1}',
    ) or f'Workload {idx + 1}'
    components = [
        {
            'label': 'Stored Data',
            'input': (
                f'{quantity:g} {unit}/mo = {billable_gb:g} GB-month'
            ),
            'multiplier': usage['dsu_rates']['stored_data_per_gb_month'],
            'multiplier_unit': 'DSU/GB-month',
            'dsus': usage['stored_data_dsu'],
        },
        {
            'label': 'Tier 1 Operations',
            'input': (
                f"{usage['tier_1_operations_thousands']:g}K operations"
            ),
            'multiplier': usage['dsu_rates']['tier_1_per_thousand'],
            'multiplier_unit': 'DSU/1K',
            'dsus': usage['tier_1_operations_dsu'],
        },
        {
            'label': 'Tier 2 Operations',
            'input': (
                f"{usage['tier_2_operations_thousands']:g}K operations"
            ),
            'multiplier': usage['dsu_rates']['tier_2_per_thousand'],
            'multiplier_unit': 'DSU/1K',
            'dsus': usage['tier_2_operations_dsu'],
        },
    ]
    for component_index, component in enumerate(components, start=1):
        cost = component['dsus'] * dsu_price
        config = (
            f"{component['input']} × {component['multiplier']:g} "
            f"{component['multiplier_unit']}"
        )
        notes = (
            f"{component['dsus']:.4f} DSU × ${dsu_price:.3f}/DSU "
            f"= ${cost:.2f}/mo"
        )
        if component_index == 3:
            notes += (
                '. Excludes customer-managed object storage, backups, '
                'and data transfer. '
                'https://www.databricks.com/product/pricing/storage'
            )
        dsu_row = {
            'idx': f'{idx + 1}.{component_index}',
            'name': f"{workload_name} – {component['label']}",
            'type_display': 'Databricks Default Storage',
            'config': config,
            'sku': 'DATABRICKS_STORAGE',
            'driver_node': '-',
            'worker_node': '-',
            'num_workers': 0,
            'driver_tier': '-',
            'worker_tier': '-',
            'hours_per_month': 0,
            'token_type': '',
            'token_quantity_millions': 0,
            'dbu_per_million': 0,
            'dbu_per_hour': 0,
            'total_dbus_month': 0,
            'dbu_rate': 0,
            'monthly_dsus': component['dsus'],
            'dsu_rate': dsu_price,
            'discount_pct': 0.0,
            'driver_vm_cost_per_hour': 0,
            'worker_vm_cost_per_hour': 0,
            'notes': notes,
        }
        write_data_row(
            sheet,
            row,
            dsu_row,
            False,
            True,
            fmt,
            is_storage_row=True,
            cost_accumulator=cost_accumulator,
        )
        row += 1
    return row


def calc_item_values(item, is_fmapi_token, is_fmapi_provisioned,
                     dbu_per_hour, cloud, auto_notes, region=None):
    """Calculate hours, tokens, DBUs for a line item.

    Returns (hours, token_qty, dbu_per_m, total_dbus, token_type).
    """
    if is_fmapi_token:
        token_qty = float(item.fmapi_quantity or 0)
        dbu_per_m, found = _get_fmapi_dbu_per_million(item, cloud, region)
        if not found:
            dbu_per_m = 0
            auto_notes.append(
                f"Unsupported FMAPI pricing combination for "
                f"{item.fmapi_model or 'unknown model'}; no fallback rate applied"
            )
        token_type = TOKEN_TYPE_DISPLAY.get(item.fmapi_rate_type, 'Input')
        return 0, token_qty, dbu_per_m, token_qty * dbu_per_m, token_type
    elif is_fmapi_provisioned:
        hours = float(item.fmapi_quantity or 0)
        dbu_hr, found = _get_fmapi_dbu_per_million(item, cloud, region)
        if not found:
            dbu_hr = 0
            auto_notes.append(
                f"Unsupported FMAPI pricing combination for "
                f"{item.fmapi_model or 'unknown model'}; no fallback rate applied"
            )
        return hours, 0, 0, dbu_hr * hours, ''
    else:
        wt = (item.workload_type or '').upper()
        # AI Parse: quantity-based (pages × complexity rate)
        if wt == 'AI_PARSE':
            complexity_rates = {
                'low_text': 12.5, 'low_images': 22.5, 'medium': 62.5, 'high': 87.5
            }
            complexity = (getattr(item, 'ai_parse_complexity', None) or 'medium').lower()
            pages_k = getattr(item, 'ai_parse_pages_thousands', None)
            if pages_k is None:
                pages_k = float(getattr(item, 'ai_parse_num_pages', 0) or 0) / 1000
            pages_k = float(pages_k or 0)
            total_dbus = pages_k * complexity_rates.get(complexity, 62.5)
            return 0, 0, 0, total_dbus, ''
        # AI Extract / AI Classify: quantity-based (documents per 1,000 × preset rate)
        if wt in ('AI_EXTRACT', 'AI_CLASSIFY'):
            from app.routes.calculate.ai_extract_calc import EXTRACT_DOCUMENT_RATES
            from app.routes.calculate.ai_classify_calc import CLASSIFY_DOCUMENT_RATES
            if wt == 'AI_EXTRACT':
                rates = EXTRACT_DOCUMENT_RATES
                doc_type = (_get_json_backed_value(
                    item, 'ai_extract_document_type', 'invoice'
                ) or 'invoice').lower()
                quantity = float(_get_json_backed_value(
                    item, 'ai_extract_num_inputs', 0
                ) or 0)
                custom_rate = _get_json_backed_value(
                    item, 'ai_extract_dbus_per_thousand'
                )
            else:
                rates = CLASSIFY_DOCUMENT_RATES
                doc_type = (_get_json_backed_value(
                    item, 'ai_classify_document_type', 'short_text'
                ) or 'short_text').lower()
                quantity = float(_get_json_backed_value(
                    item, 'ai_classify_num_docs', 0
                ) or 0)
                custom_rate = _get_json_backed_value(
                    item, 'ai_classify_dbus_per_thousand'
                )
            if doc_type == 'custom':
                if custom_rate is None or float(custom_rate) <= 0:
                    raise ValueError(
                        f"{wt} custom rate must be greater than 0"
                    )
                rate = float(custom_rate)
            else:
                if doc_type not in rates:
                    raise ValueError(
                        f"Unsupported {wt} document type: {doc_type}"
                    )
                rate = rates[doc_type]
            total_dbus = (quantity / 1000.0) * rate
            return 0, 0, 0, total_dbus, ''
        # AI Gateway: quantity-based (request-derived or direct payload GB)
        if wt == 'AI_GATEWAY':
            usage = get_ai_gateway_usage(item)
            return 0, 0, 0, usage['monthly_dbus'], ''
        # Agent Evaluation: quantity-based token/question dimensions
        if wt == 'AGENT_EVALUATION':
            usage = get_agent_evaluation_usage(item)
            return 0, 0, 0, usage['monthly_dbus'], ''
        # Zerobus: quantity-based monthly ingested GB
        if wt == 'ZEROBUS':
            usage = get_zerobus_usage(item)
            return 0, 0, 0, usage['monthly_dbus'], ''
        # Shutterstock ImageAI: quantity-based (images × 0.857 DBU)
        if wt == 'SHUTTERSTOCK_IMAGEAI':
            images = getattr(item, 'shutterstock_images', None)
            if images is None:
                images = getattr(item, 'shutterstock_imageai_num_images', 0)
            images = int(images or 0)
            total_dbus = images * 0.857
            return 0, 0, 0, total_dbus, ''
        hours = _calculate_hours_per_month(item)
        return hours, 0, 0, dbu_per_hour * hours, ''


def write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                         type_display, size_attr, cost_accumulator=None):
    """Write a storage sub-row for Lakebase or AI Search.

    Lakebase uses DSU pricing with different multipliers per feature:
      - Database Storage: 15x DSU/GB
      - PITR: 8.7x DSU/GB
      - Snapshots: 3.91x DSU/GB
    AI Search uses mode-specific DSUs above its included allowance.
    """
    # DSU multipliers per Databricks SKU page
    DSU_MULTIPLIERS = {
        'lakebase_storage_gb': 15.0,
        'lakebase_pitr_gb': 8.7,
        'lakebase_snapshot_gb': 3.91,
    }
    DSU_LABELS = {
        'lakebase_storage_gb': 'Storage',
        'lakebase_pitr_gb': 'PITR',
        'lakebase_snapshot_gb': 'Snapshots',
    }

    price_per_dsu, found = _get_dbu_price(
        cloud,
        region,
        tier,
        'DATABRICKS_STORAGE',
        allow_cross_region=False,
    )
    if not found:
        raise ValueError(
            "DATABRICKS_STORAGE pricing is not available for "
            f"{cloud.upper()} {region} {tier.upper()}"
        )

    if size_attr in DSU_MULTIPLIERS:
        storage_gb = float(getattr(item, size_attr, 0) or 0)
        dsu_per_gb = DSU_MULTIPLIERS[size_attr]
        total_dsu = storage_gb * dsu_per_gb
        storage_cost = total_dsu * price_per_dsu
        label = DSU_LABELS[size_attr]
        config = f'{label}: {storage_gb:.0f} GB'
        notes = f'{storage_gb:.0f} GB × {dsu_per_gb} DSU/GB × ${price_per_dsu}/DSU = ${storage_cost:.2f}/mo'
    elif size_attr == 'vector_search_storage_gb':
        import math
        storage_gb = float(item.vector_search_storage_gb or 0)
        capacity_m = float(item.vector_capacity_millions or 1)
        mode = (item.vector_search_mode or 'standard').lower()
        divisor = 64_000_000 if mode == 'storage_optimized' else 2_000_000
        units = math.ceil(capacity_m * 1_000_000 / divisor) if divisor else 0
        free_gb = 30 if units > 0 else 0
        billable_gb = max(0, storage_gb - free_gb)
        dsu_per_gb = 2 if mode == 'storage_optimized' else 10
        total_dsu = billable_gb * dsu_per_gb
        storage_cost = total_dsu * price_per_dsu
        config = f'Storage: {storage_gb:.0f} GB (free: {free_gb} GB)'
        notes = (
            f'{storage_gb:.0f} GB total, first {free_gb} GB free, '
            f'{billable_gb:.0f} GB billable × {dsu_per_gb} DSU/GB '
            f'× ${price_per_dsu}/DSU = ${storage_cost:.2f}/mo'
        )
    else:
        storage_gb = 0
        total_dsu = 0
        storage_cost = 0
        config = 'Storage: 0 GB'
        notes = ''

    name = getattr(item, 'workload_name', f'Workload {idx + 1}') or f'Workload {idx + 1}'
    storage_row = {
        'idx': '',
        'name': name,
        'type_display': type_display,
        'config': config,
        'sku': 'DATABRICKS_STORAGE',
        'driver_node': '-', 'worker_node': '-',
        'num_workers': 0,
        'driver_tier': '-', 'worker_tier': '-',
        'hours_per_month': 0,
        'token_type': '', 'token_quantity_millions': 0,
        'dbu_per_million': 0, 'dbu_per_hour': 0,
        'total_dbus_month': 0,
        'dbu_rate': 0,
        'monthly_dsus': total_dsu,
        'dsu_rate': price_per_dsu,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': 0, 'worker_vm_cost_per_hour': 0,
        'notes': notes,
    }
    write_data_row(
        sheet,
        row,
        storage_row,
        False,
        True,
        fmt,
        is_storage_row=True,
        cost_accumulator=cost_accumulator,
    )
    return row + 1
