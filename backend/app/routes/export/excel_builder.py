"""Main Excel builder: assembles the estimate workbook."""
from io import BytesIO
from datetime import datetime, timezone
import xlsxwriter

from .excel_formats import create_formats
from .excel_row_writer import (
    NUM_COLS, COLUMN_WIDTHS, get_headers, write_data_row,
)
from .excel_sections import (
    write_totals, write_cost_summary, write_dbu_summary,
    write_legend, write_assumptions, write_footer,
)
from .pricing import _get_dbu_price, _get_sku_type
from .helpers import (
    _get_workload_display_name, _get_workload_config_details,
    _get_pricing_tier_display,
)
from .calculations import _calculate_dbu_per_hour, _is_serverless_workload
from .excel_item_helpers import (
    _get_json_backed_value,
    calc_item_values,
    get_ai_search_reranker_usage,
    get_agent_evaluation_usage,
    get_ai_gateway_usage,
    write_storage_subrow,
)
from app.routes.vm_pricing import DEFAULT_VM_PRICING
from app.routes.calculate.ai_gateway_calc import (
    AI_GATEWAY_DIRECT_GB_NOTE,
    AI_GATEWAY_EXCLUSION_NOTE,
)
from app.routes.calculate.agent_evaluation_calc import (
    AGENT_EVALUATION_EXCLUSION_NOTE,
)
from app.services.vm_pricing_resolver import resolve_vm_hourly_rate


def build_estimate_excel(estimate, line_items, cloud, region, tier, db=None):
    """Build an Excel workbook for an estimate. Returns BytesIO output."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    fmt = create_formats(workbook)
    max_col = NUM_COLS - 1

    sheet = workbook.add_worksheet('Databricks Estimate')
    for i, w in enumerate(COLUMN_WIDTHS):
        sheet.set_column(i, i, w)

    row = _write_header_section(sheet, fmt, estimate, cloud, region, tier, max_col)
    row, header_row, data_start_row = _write_table_headers(sheet, fmt, row, max_col)
    row = _write_line_items(sheet, fmt, row, line_items, cloud, region, tier, db=db)
    data_end_row = row - 1
    row = write_totals(sheet, fmt, row, data_start_row, data_end_row)
    totals_row = row - 2
    row = write_cost_summary(sheet, fmt, row, totals_row)
    row = write_dbu_summary(sheet, fmt, row, data_start_row, data_end_row)
    row = write_legend(sheet, fmt, row)
    row = write_assumptions(sheet, fmt, row, max_col)
    write_footer(sheet, workbook, row, max_col)

    sheet.freeze_panes(header_row + 1, 2)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)

    workbook.close()
    output.seek(0)
    return output


def _get_val(obj, key, default=''):
    val = getattr(obj, key, default)
    return val if val is not None else default


def _first_nonempty(item, *keys, default):
    """Return the first populated pricing field from newest to legacy."""
    for key in keys:
        value = _get_val(item, key, None)
        if value not in (None, ''):
            return value
    return default


def _get_dbsql_vm_pricing(item):
    """Resolve the driver/worker selections used by the DBSQL UI.

    Separate DBSQL fields are preferred when present, followed by the generic
    driver/worker fields persisted by the current UI. The legacy single-tier
    fields remain as a compatibility fallback for older estimates.
    """
    driver_tier = _first_nonempty(
        item,
        'dbsql_driver_pricing_tier',
        'driver_pricing_tier',
        'dbsql_vm_pricing_tier',
        default='on_demand',
    )
    worker_tier = _first_nonempty(
        item,
        'dbsql_worker_pricing_tier',
        'worker_pricing_tier',
        'dbsql_vm_pricing_tier',
        default='spot',
    )
    driver_payment = _first_nonempty(
        item,
        'dbsql_driver_payment_option',
        'driver_payment_option',
        'dbsql_vm_payment_option',
        default='NA',
    )
    worker_payment = _first_nonempty(
        item,
        'dbsql_worker_payment_option',
        'worker_payment_option',
        'dbsql_vm_payment_option',
        default='NA',
    )

    if driver_tier in ('on_demand', 'spot'):
        driver_payment = 'NA'
    if worker_tier in ('on_demand', 'spot'):
        worker_payment = 'NA'

    return driver_tier, driver_payment, worker_tier, worker_payment


def _resolve_vm_rate(
    db,
    *,
    cloud,
    region,
    instance_type,
    pricing_tier,
    payment_option,
    vm_prices,
    component,
    auto_notes,
):
    """Resolve one VM rate and attach any fallback warning to the export."""
    resolution = resolve_vm_hourly_rate(
        db,
        cloud=cloud,
        region=region,
        instance_type=instance_type,
        pricing_tier=pricing_tier,
        payment_option=payment_option,
        fallback_prices=vm_prices.get(instance_type, {}),
    )
    if resolution.warning:
        auto_notes.append(f"{component}: {resolution.warning}")
    return resolution.rate


def _lookup_dbsql_vm_costs(item, cloud, region, vm_prices, db, auto_notes):
    """Look up VM costs for DBSQL Classic/Pro warehouses.

    Uses static dbsql-warehouse-config.json to find driver/worker instance types,
    then resolves exact regional rates from sync_pricing_vm_costs.
    Returns (driver_vm_hr, worker_vm_hr, worker_count).
    """
    from .pricing import DBSQL_WAREHOUSE_CONFIG

    wh_type = (item.dbsql_warehouse_type or 'CLASSIC').upper()
    wh_size = item.dbsql_warehouse_size or 'Small'
    driver_tier, driver_payment, worker_tier, worker_payment = (
        _get_dbsql_vm_pricing(item)
    )
    cloud_lc = (cloud or 'aws').lower()

    # Look up warehouse config from static JSON (key format: "aws:classic:Small")
    config_key = f"{cloud_lc}:{wh_type.lower()}:{wh_size}"
    config = DBSQL_WAREHOUSE_CONFIG.get(config_key)

    if not config:
        # Try DB fallback
        config = _lookup_dbsql_config_from_db(cloud, wh_type, wh_size, db, auto_notes)
        if not config:
            auto_notes.append(f"DBSQL warehouse config not found for {config_key}")
            return 0, 0, 0

    driver_inst = config.get('driver_instance_type', '') if isinstance(config, dict) else getattr(config, 'driver_instance_type', '')
    worker_inst = config.get('worker_instance_type', '') if isinstance(config, dict) else getattr(config, 'worker_instance_type', '')
    worker_count = (config.get('worker_count', 0) if isinstance(config, dict) else getattr(config, 'worker_count', 0)) or 0

    driver_vm_hr = (
        _resolve_vm_rate(
            db,
            cloud=cloud,
            region=region,
            instance_type=driver_inst,
            pricing_tier=driver_tier,
            payment_option=driver_payment,
            vm_prices=vm_prices,
            component="DBSQL driver",
            auto_notes=auto_notes,
        )
        if driver_inst
        else 0
    )
    worker_vm_hr = (
        _resolve_vm_rate(
            db,
            cloud=cloud,
            region=region,
            instance_type=worker_inst,
            pricing_tier=worker_tier,
            payment_option=worker_payment,
            vm_prices=vm_prices,
            component="DBSQL worker",
            auto_notes=auto_notes,
        )
        if worker_inst
        else 0
    )

    return driver_vm_hr, worker_vm_hr, worker_count


def _lookup_dbsql_config_from_db(cloud, wh_type, wh_size, db, auto_notes):
    """Fallback: query warehouse config from DB table."""
    if not db:
        return None
    try:
        from sqlalchemy import text as sa_text
        row = db.execute(sa_text("""
            SELECT driver_instance_type, worker_instance_type, worker_count
            FROM lakemeter.sync_ref_dbsql_warehouse_config
            WHERE UPPER(cloud) = UPPER(:cloud)
                AND UPPER(warehouse_type) = UPPER(:wh_type)
                AND UPPER(warehouse_size) = UPPER(:wh_size)
        """), {"cloud": cloud, "wh_type": wh_type, "wh_size": wh_size}).fetchone()
        if row:
            return {'driver_instance_type': row.driver_instance_type,
                    'worker_instance_type': row.worker_instance_type,
                    'worker_count': row.worker_count}
    except Exception as e:
        auto_notes.append(f"DBSQL config DB fallback: {e}")
    return None


def _write_header_section(sheet, fmt, estimate, cloud, region, tier, max_col):
    """Write title, subtitle, and estimate details."""
    row = 0
    estimate_name = _get_val(estimate, 'estimate_name', 'Untitled Estimate')
    sheet.merge_range(row, 0, row, max_col, 'Databricks Pricing Estimate', fmt['title'])
    row += 1
    sheet.merge_range(row, 0, row, max_col, estimate_name, fmt['subtitle'])
    row += 2

    sheet.merge_range(row, 0, row, max_col, 'ESTIMATE DETAILS', fmt['section_header'])
    row += 1

    status = _get_val(estimate, 'status', 'draft').capitalize()
    version = _get_val(estimate, 'version', 1)
    created_at = _get_val(estimate, 'created_at', datetime.now(timezone.utc))
    updated_at = _get_val(estimate, 'updated_at', datetime.now(timezone.utc))
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d')
    if isinstance(updated_at, datetime):
        updated_at = updated_at.strftime('%Y-%m-%d')

    info_data = [
        [('Cloud:', cloud.upper()), ('Region:', region), ('Tier:', tier.upper()),
         ('Status:', status)],
        [('Version:', str(version)), ('Created:', created_at), ('Updated:', updated_at)],
    ]
    for info_row in info_data:
        col = 0
        for label_text, value_text in info_row:
            sheet.write(row, col, label_text, fmt['label'])
            sheet.write(row, col + 1, value_text, fmt['value'])
            col += 4
        row += 1
    row += 1
    return row


def _write_table_headers(sheet, fmt, row, max_col):
    """Write the workloads table header row."""
    sheet.merge_range(row, 0, row, max_col, 'WORKLOADS & COST BREAKDOWN',
                      fmt['section_header'])
    row += 1
    headers = get_headers(fmt)
    for col, (header, header_fmt) in enumerate(headers):
        sheet.write(row, col, header, header_fmt)
    header_row = row
    row += 1
    data_start_row = row
    return row, header_row, data_start_row


def _write_line_items(sheet, fmt, row, line_items, cloud, region, tier, db=None):
    """Write all line item data rows including storage sub-rows."""
    for idx, item in enumerate(line_items):
        row = _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier, db=db)
    return row


def _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier, db=None):
    """Write one line item (and its storage sub-row if applicable)."""
    wt = (item.workload_type or 'JOBS').upper()
    if wt == 'AGENT_EVALUATION' and (tier or '').upper() == 'STANDARD':
        raise ValueError(
            "Agent Evaluation requires Premium or Enterprise tier"
        )
    if wt == 'AI_RUNTIME':
        if (tier or '').upper() == 'STANDARD':
            raise ValueError(
                "AI Runtime requires Premium or Enterprise tier"
            )
    sku = _get_sku_type(item, cloud)
    requires_exact_regional_price = wt in (
        'AI_EXTRACT',
        'AI_CLASSIFY',
        'AI_GATEWAY',
        'AGENT_EVALUATION',
        'AI_RUNTIME',
    )
    dbu_rate, dbu_rate_found = _get_dbu_price(
        cloud,
        region,
        tier,
        sku,
        allow_cross_region=not requires_exact_regional_price,
    )
    if requires_exact_regional_price and not dbu_rate_found:
        raise ValueError(
            f"{sku} pricing is not available for "
            f"{cloud.upper()} {region} {tier.upper()}"
        )
    dbu_per_hour, dbu_warnings = _calculate_dbu_per_hour(item, cloud, tier)
    is_serverless = _is_serverless_workload(item)
    is_fmapi = wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY')
    is_fmapi_token = is_fmapi and item.fmapi_rate_type in (
        'input_token', 'output_token', 'input', 'output',
        'cache_read', 'cache_write', 'batch_inference')
    is_fmapi_provisioned = is_fmapi and item.fmapi_rate_type in (
        'provisioned_scaling', 'provisioned_entry')
    is_quantity_based = wt in (
        'AI_PARSE',
        'AI_EXTRACT',
        'AI_CLASSIFY',
        'AI_GATEWAY',
        'AGENT_EVALUATION',
        'SHUTTERSTOCK_IMAGEAI',
    )

    auto_notes = list(dbu_warnings)
    if wt == 'AI_GATEWAY':
        return _write_ai_gateway_component_rows(
            sheet,
            fmt,
            row,
            idx,
            item,
            dbu_rate,
            auto_notes,
        )
    if wt == 'AGENT_EVALUATION':
        return _write_agent_evaluation_component_rows(
            sheet,
            fmt,
            row,
            idx,
            item,
            dbu_rate,
            auto_notes,
        )
    if not dbu_rate_found:
        auto_notes.append(f"DBU rate not found for {sku}, using fallback ${dbu_rate:.2f}")

    hours, token_qty, dbu_per_m, total_dbus, token_type = calc_item_values(
        item, is_fmapi_token, is_fmapi_provisioned, dbu_per_hour, cloud, auto_notes)

    num_workers = int(item.num_workers or 0)
    dbsql_driver_inst = ''
    dbsql_worker_inst = ''
    # Look up VM costs from DEFAULT_VM_PRICING; serverless workloads have no VM costs
    driver_vm_hr = 0
    worker_vm_hr = 0
    if not is_serverless:
        cloud_lc = (cloud or 'aws').lower()
        vm_prices = DEFAULT_VM_PRICING.get(cloud_lc, {})

        # DBSQL Classic/Pro: look up VM costs via warehouse config → instance types
        if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() in ('CLASSIC', 'PRO'):
            driver_vm_hr, worker_vm_hr, num_workers = _lookup_dbsql_vm_costs(
                item, cloud, region, vm_prices, db, auto_notes)
            # Also capture instance types for display in the export
            from .pricing import DBSQL_WAREHOUSE_CONFIG
            wh_type = (item.dbsql_warehouse_type or 'CLASSIC').upper()
            wh_size = item.dbsql_warehouse_size or 'Small'
            cfg_key = f"{cloud_lc}:{wh_type.lower()}:{wh_size}"
            cfg = DBSQL_WAREHOUSE_CONFIG.get(cfg_key, {})
            dbsql_driver_inst = cfg.get('driver_instance_type', '')
            dbsql_worker_inst = cfg.get('worker_instance_type', '')
        else:
            driver_node = _get_val(item, 'driver_node_type', '')
            worker_node = _get_val(item, 'worker_node_type', '')
            driver_tier = _get_val(item, 'driver_pricing_tier', 'on_demand') or 'on_demand'
            worker_tier = _get_val(item, 'worker_pricing_tier', 'on_demand') or 'on_demand'
            if driver_node:
                driver_vm_hr = _resolve_vm_rate(
                    db,
                    cloud=cloud,
                    region=region,
                    instance_type=driver_node,
                    pricing_tier=driver_tier,
                    payment_option=_get_val(item, 'driver_payment_option', 'NA'),
                    vm_prices=vm_prices,
                    component="Driver",
                    auto_notes=auto_notes,
                )
            if worker_node:
                worker_vm_hr = _resolve_vm_rate(
                    db,
                    cloud=cloud,
                    region=region,
                    instance_type=worker_node,
                    pricing_tier=worker_tier,
                    payment_option=_get_val(item, 'worker_payment_option', 'NA'),
                    vm_prices=vm_prices,
                    component="Worker",
                    auto_notes=auto_notes,
                )

    user_notes = _get_val(item, 'notes', '') or ''
    notes_parts = [user_notes] if user_notes else []
    if auto_notes:
        notes_parts.append(' | '.join(auto_notes))

    # For DBSQL Classic/Pro, show warehouse info instead of generic driver/worker
    if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() in ('CLASSIC', 'PRO'):
        driver_tier, _, worker_tier, _ = _get_dbsql_vm_pricing(item)
        display_driver_tier = _get_pricing_tier_display(driver_tier)
        display_worker_tier = _get_pricing_tier_display(worker_tier)
    else:
        display_driver_tier = _get_pricing_tier_display(
            item.driver_pricing_tier) if hasattr(item, 'driver_pricing_tier') and item.driver_pricing_tier else '-'
        display_worker_tier = _get_pricing_tier_display(
            item.worker_pricing_tier) if hasattr(item, 'worker_pricing_tier') and item.worker_pricing_tier else '-'

    base_row = {
        'idx': idx + 1,
        'name': _get_val(item, 'workload_name', f'Workload {idx + 1}'),
        'type_display': _get_workload_display_name(wt),
        'config': _get_workload_config_details(item),
        'sku': sku,
        'driver_node': dbsql_driver_inst or _get_val(item, 'driver_node_type', '-') or '-',
        'worker_node': dbsql_worker_inst or _get_val(item, 'worker_node_type', '-') or '-',
        'num_workers': num_workers,
        'driver_tier': display_driver_tier,
        'worker_tier': display_worker_tier,
        'hours_per_month': hours,
        'token_type': token_type if is_fmapi_token else '',
        'token_quantity_millions': token_qty,
        'dbu_per_million': dbu_per_m,
        'dbu_per_hour': dbu_per_hour,
        'total_dbus_month': total_dbus,
        'is_quantity_based': is_quantity_based,
        'dbu_rate': dbu_rate,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': driver_vm_hr,
        'worker_vm_cost_per_hour': worker_vm_hr,
        'notes': ' — '.join(notes_parts) if notes_parts else '',
    }

    write_data_row(sheet, row, base_row, is_fmapi_token, is_serverless, fmt)
    row += 1

    if wt == 'LAKEBASE':
        row = write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                   'Lakebase (Storage)', 'lakebase_storage_gb')
        if getattr(item, 'lakebase_pitr_gb', 0) and item.lakebase_pitr_gb > 0:
            row = write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                       'Lakebase (PITR)', 'lakebase_pitr_gb')
        if getattr(item, 'lakebase_snapshot_gb', 0) and item.lakebase_snapshot_gb > 0:
            row = write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                       'Lakebase (Snapshots)', 'lakebase_snapshot_gb')
    elif wt == 'VECTOR_SEARCH':
        row = _write_ai_search_reranker_row(
            sheet,
            fmt,
            row,
            idx,
            item,
            dbu_rate,
        )
        if (getattr(item, 'vector_search_storage_gb', 0) or 0) > 0:
            row = write_storage_subrow(
                sheet,
                fmt,
                row,
                item,
                idx,
                cloud,
                region,
                tier,
                'AI Search (Storage)',
                'vector_search_storage_gb',
            )
    return row


def _write_ai_search_reranker_row(sheet, fmt, row, idx, item, dbu_rate):
    """Write a DBU/month row for optional AI Search Reranker usage."""
    usage = get_ai_search_reranker_usage(item)
    if not usage['enabled']:
        return row

    workload_name = _get_val(
        item,
        'workload_name',
        f'Workload {idx + 1}',
    )
    requests = usage['requests_thousands']
    component_rate = usage['dbu_per_thousand_requests']
    monthly_dbus = usage['monthly_dbus']
    config = (
        f"{requests:g}K requests × {component_rate:.3f} DBU/1K "
        f"= {monthly_dbus:.3f} DBU/mo"
    )
    row_data = {
        'idx': f'{idx + 1}.1',
        'name': f'{workload_name} – AI Search Reranker',
        'type_display': 'AI Search (Reranker)',
        'config': config,
        'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
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
        'total_dbus_month': monthly_dbus,
        'is_quantity_based': True,
        'token_columns_na': True,
        'show_dbu_month_decimals': True,
        'dbu_rate': dbu_rate,
        'discount_pct': 0.0,
        'driver_vm_cost_per_hour': 0,
        'worker_vm_cost_per_hour': 0,
        'notes': _get_val(item, 'notes', '') or '',
    }
    write_data_row(sheet, row, row_data, False, True, fmt)
    return row + 1


def _write_ai_gateway_component_rows(
    sheet,
    fmt,
    row,
    idx,
    item,
    dbu_rate,
    auto_notes,
):
    """Write one recalculation-safe row for each enabled gateway component."""
    usage = get_ai_gateway_usage(item)
    workload_name = _get_val(
        item,
        'workload_name',
        f'Workload {idx + 1}',
    )
    user_notes = _get_val(item, 'notes', '') or ''
    notes_parts = [user_notes] if user_notes else []
    notes_parts.extend(auto_notes)
    notes_parts.extend([
        AI_GATEWAY_DIRECT_GB_NOTE,
        AI_GATEWAY_EXCLUSION_NOTE,
    ])
    for component_index, component in enumerate(usage['components'], start=1):
        component_config = _get_ai_gateway_component_config(
            item,
            component,
        )
        config = (
            f"{component_config} | Component: {component['display_name']} | "
            f"Component rate: {component['dbu_per_gb']:.3f} DBU/GB"
        )
        row_data = {
            'idx': f'{idx + 1}.{component_index}',
            'name': f"{workload_name} – {component['display_name']}",
            'type_display': 'Unity AI Gateway',
            'config': config,
            'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
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
            'total_dbus_month': component['monthly_dbus'],
            'is_quantity_based': True,
            'dbu_rate': dbu_rate,
            'discount_pct': 0.0,
            'driver_vm_cost_per_hour': 0,
            'worker_vm_cost_per_hour': 0,
            'notes': ' — '.join(notes_parts),
        }
        write_data_row(sheet, row, row_data, False, True, fmt)
        row += 1
    return row


def _get_ai_gateway_component_config(item, component):
    """Return export configuration for one independent gateway component."""
    prefix = f"ai_gateway_{component['component']}"
    input_method = _get_json_backed_value(
        item,
        f"{prefix}_input_method",
    )
    details = []
    if input_method == "payload_gb":
        details.append("Input: Direct metered payload")
    else:
        requests_millions = float(_get_json_backed_value(
            item,
            f"{prefix}_requests_millions",
            0,
        ) or 0)
        request_kb = float(_get_json_backed_value(
            item,
            f"{prefix}_avg_request_payload_kb",
            0,
        ) or 0)
        response_kb = float(_get_json_backed_value(
            item,
            f"{prefix}_avg_response_payload_kb",
            0,
        ) or 0)
        details.append(f"Input: {requests_millions:g}M requests/mo")
        details.append(
            f"Payload/request: {request_kb:g} KB request + "
            f"{response_kb:g} KB response"
        )
    details.append(
        f"Monthly payload: {component['monthly_payload_gb']:g} GB"
    )
    return " | ".join(details)


def _write_agent_evaluation_component_rows(
    sheet,
    fmt,
    row,
    idx,
    item,
    dbu_rate,
    auto_notes,
):
    """Write one formula-backed row per enabled evaluation dimension."""
    usage = get_agent_evaluation_usage(item)
    workload_name = _get_val(
        item,
        'workload_name',
        f'Workload {idx + 1}',
    )
    user_notes = _get_val(item, 'notes', '') or ''
    notes_parts = [user_notes] if user_notes else []
    notes_parts.extend(auto_notes)
    notes_parts.append(AGENT_EVALUATION_EXCLUSION_NOTE)

    token_type_names = {
        'input_tokens': 'Input Tokens',
        'output_tokens': 'Output Tokens',
        'synthetic_questions': 'Synthetic Questions',
    }
    for component_index, component in enumerate(
        usage['components'],
        start=1,
    ):
        quantity_unit = (
            'million tokens'
            if component['quantity_unit'] == 'million_tokens'
            else 'questions'
        )
        config = (
            f"Quantity: {component['quantity']:g} {quantity_unit}/mo | "
            f"Canonical rate: {component['dbu_per_unit']:.3f} "
            f"DBU/{quantity_unit}"
        )
        row_data = {
            'idx': f'{idx + 1}.{component_index}',
            'name': f"{workload_name} – {component['display_name']}",
            'type_display': 'Agent Evaluation',
            'config': config,
            'sku': 'SERVERLESS_REAL_TIME_INFERENCE',
            'driver_node': '-',
            'worker_node': '-',
            'num_workers': 0,
            'driver_tier': '-',
            'worker_tier': '-',
            'hours_per_month': 0,
            'token_type': token_type_names[component['component']],
            'token_quantity_millions': component['quantity'],
            'dbu_per_million': component['dbu_per_unit'],
            'dbu_per_hour': 0,
            'total_dbus_month': component['monthly_dbus'],
            'is_quantity_based': False,
            'dbu_rate': dbu_rate,
            'discount_pct': 0.0,
            'driver_vm_cost_per_hour': 0,
            'worker_vm_cost_per_hour': 0,
            'notes': ' — '.join(notes_parts),
        }
        write_data_row(sheet, row, row_data, True, True, fmt)
        row += 1
    return row


