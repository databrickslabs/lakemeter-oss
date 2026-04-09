"""Item-level calculation and storage sub-row helpers for Excel export."""
from .pricing import _get_dbu_price, _get_fmapi_dbu_per_million, FMAPI_PROP_FALLBACK_RATES
from .calculations import _calculate_hours_per_month
from .excel_row_writer import write_data_row


# Token type display map for FMAPI token-based rate types
TOKEN_TYPE_DISPLAY = {
    'input_token': 'Input', 'input': 'Input',
    'output_token': 'Output', 'output': 'Output',
    'cache_read': 'Cache Read', 'cache_write': 'Cache Write',
    'batch_inference': 'Batch',
}

# Fallback DBU/1M token rates for FMAPI_DATABRICKS — matches frontend costCalculation.ts
# These are much lower than proprietary rates (Databricks OSS models are cheaper)
FMAPI_DB_FALLBACK_RATES = {
    'input_token': 1.0, 'input': 1.0,
    'output_token': 3.0, 'output': 3.0,
}

# Fallback DBU/hr rates for FMAPI_DATABRICKS provisioned — matches frontend costCalculation.ts
FMAPI_DB_PROVISIONED_FALLBACK = {
    'provisioned_scaling': 200,
    'provisioned_entry': 50,
}


def calc_item_values(item, is_fmapi_token, is_fmapi_provisioned,
                     dbu_per_hour, cloud, auto_notes):
    """Calculate hours, tokens, DBUs for a line item.

    Returns (hours, token_qty, dbu_per_m, total_dbus, token_type).
    """
    if is_fmapi_token:
        token_qty = float(item.fmapi_quantity or 0)
        dbu_per_m, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            # Use workload-appropriate fallback rates matching frontend
            rate_type = item.fmapi_rate_type or 'input_token'
            wt = item.workload_type or ''
            if wt == 'FMAPI_DATABRICKS':
                dbu_per_m = FMAPI_DB_FALLBACK_RATES.get(rate_type, 1.0)
            else:
                dbu_per_m = FMAPI_PROP_FALLBACK_RATES.get(rate_type, 21.43)
            auto_notes.append(
                f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}, using fallback {dbu_per_m}")
        token_type = TOKEN_TYPE_DISPLAY.get(item.fmapi_rate_type, 'Input')
        return 0, token_qty, dbu_per_m, token_qty * dbu_per_m, token_type
    elif is_fmapi_provisioned:
        hours = float(item.fmapi_quantity or 0)
        dbu_hr, found = _get_fmapi_dbu_per_million(item, cloud)
        if not found:
            # Use workload-appropriate provisioned fallback matching frontend
            rate_type = item.fmapi_rate_type or 'provisioned_scaling'
            wt = item.workload_type or ''
            if wt == 'FMAPI_DATABRICKS':
                dbu_hr = FMAPI_DB_PROVISIONED_FALLBACK.get(rate_type, 200)
            else:
                dbu_hr = 150  # Frontend proprietary provisioned fallback
            auto_notes.append(
                f"FMAPI rate not found for {item.fmapi_model or 'unknown model'}, using fallback {dbu_hr}")
        return hours, 0, 0, dbu_hr * hours, ''
    else:
        wt = (item.workload_type or '').upper()
        # AI Parse: quantity-based (pages × complexity rate)
        if wt == 'AI_PARSE':
            complexity_rates = {
                'low_text': 12.5, 'low_images': 22.5, 'medium': 62.5, 'high': 87.5
            }
            complexity = (getattr(item, 'ai_parse_complexity', None) or 'medium').lower()
            pages_k = float(getattr(item, 'ai_parse_pages_thousands', 0) or 0)
            total_dbus = pages_k * complexity_rates.get(complexity, 62.5)
            return 0, 0, 0, total_dbus, ''
        # Shutterstock ImageAI: quantity-based (images × 0.857 DBU)
        if wt == 'SHUTTERSTOCK_IMAGEAI':
            images = int(getattr(item, 'shutterstock_images', 0) or 0)
            total_dbus = images * 0.857
            return 0, 0, 0, total_dbus, ''
        hours = _calculate_hours_per_month(item)
        return hours, 0, 0, dbu_per_hour * hours, ''


def write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                         type_display, size_attr):
    """Write a storage sub-row for Lakebase (storage/PITR/snapshots) or Vector Search.

    Lakebase uses DSU pricing with different multipliers per feature:
      - Database Storage: 15x DSU/GB
      - PITR: 8.7x DSU/GB
      - Snapshots: 3.91x DSU/GB
    Vector Search uses standard storage pricing: cost = GB × $/GB/month.
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

    if size_attr in DSU_MULTIPLIERS:
        storage_gb = float(getattr(item, size_attr, 0) or 0)
        dsu_per_gb = DSU_MULTIPLIERS[size_attr]
        total_dsu = storage_gb * dsu_per_gb
        price_per_dsu = 0.023
        storage_cost = total_dsu * price_per_dsu
        storage_rate = price_per_dsu
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
        free_gb = units * 20
        billable_gb = max(0, storage_gb - free_gb)
        price_per_gb = 0.023
        storage_cost = billable_gb * price_per_gb
        storage_rate = price_per_gb
        config = f'Storage: {storage_gb:.0f} GB (free: {free_gb} GB)'
        notes = f'{storage_gb:.0f} GB total, {free_gb} GB free ({units} units × 20 GB), {billable_gb:.0f} GB billable × ${price_per_gb}/GB = ${storage_cost:.2f}/mo'
    else:
        storage_gb = 0
        storage_rate = 0.023
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
        'dbu_rate': storage_rate,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': 0, 'worker_vm_cost_per_hour': 0,
        'notes': notes,
        'storage_cost_monthly': storage_cost,
    }
    write_data_row(sheet, row, storage_row, False, True, fmt, is_storage_row=True)
    return row + 1
