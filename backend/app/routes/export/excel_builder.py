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
from .excel_item_helpers import calc_item_values, write_storage_subrow
from app.routes.vm_pricing import DEFAULT_VM_PRICING


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


# Reserved instance discount factors relative to on-demand
_RESERVED_DISCOUNTS = {
    '1yr_reserved': 0.72,   # ~28% discount
    '3yr_reserved': 0.50,   # ~50% discount
    'spot': 0.30,           # ~70% discount
}


def _get_vm_hourly_rate(instance_prices: dict, pricing_tier: str) -> float:
    """Get VM hourly rate for a pricing tier. Uses direct lookup, falls back to discount."""
    if pricing_tier in instance_prices:
        return instance_prices[pricing_tier]
    on_demand = instance_prices.get('on_demand', 0)
    discount = _RESERVED_DISCOUNTS.get(pricing_tier, 1.0)
    return round(on_demand * discount, 4)


def _lookup_dbsql_vm_costs(item, cloud, region, vm_prices, db, auto_notes):
    """Look up VM costs for DBSQL Classic/Pro warehouses.

    Uses static dbsql-warehouse-config.json to find driver/worker instance types,
    then looks up VM costs from DEFAULT_VM_PRICING. Falls back to DB if needed.
    Returns (driver_vm_hr, worker_vm_hr, worker_count).
    """
    from .pricing import DBSQL_WAREHOUSE_CONFIG

    wh_type = (item.dbsql_warehouse_type or 'CLASSIC').upper()
    wh_size = item.dbsql_warehouse_size or 'Small'
    driver_tier = _get_val(item, 'dbsql_vm_pricing_tier', 'on_demand') or 'on_demand'
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

    driver_vm_hr = 0
    worker_vm_hr = 0
    if driver_inst and driver_inst in vm_prices:
        driver_vm_hr = _get_vm_hourly_rate(vm_prices[driver_inst], driver_tier)
    if worker_inst and worker_inst in vm_prices:
        worker_vm_hr = _get_vm_hourly_rate(vm_prices[worker_inst], driver_tier)

    # If not in static VM pricing, try the database
    if (driver_vm_hr == 0 or worker_vm_hr == 0) and db:
        _lookup_vm_costs_from_db(
            cloud, region, driver_inst, worker_inst, driver_tier,
            driver_vm_hr, worker_vm_hr, db, auto_notes
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


def _lookup_vm_costs_from_db(cloud, region, driver_inst, worker_inst, tier,
                              driver_vm_hr, worker_vm_hr, db, auto_notes):
    """Fallback: query VM costs from DB when not in static pricing."""
    try:
        from sqlalchemy import text as sa_text
        if driver_vm_hr == 0 and driver_inst:
            row = db.execute(sa_text("""
                SELECT cost_per_hour FROM lakemeter.sync_pricing_vm_costs
                WHERE UPPER(cloud) = UPPER(:cloud) AND region = :region
                    AND instance_type = :inst AND pricing_tier = :tier
                LIMIT 1
            """), {"cloud": cloud, "region": region, "inst": driver_inst, "tier": tier}).fetchone()
            if row:
                driver_vm_hr = float(row.cost_per_hour or 0)
        if worker_vm_hr == 0 and worker_inst:
            row = db.execute(sa_text("""
                SELECT cost_per_hour FROM lakemeter.sync_pricing_vm_costs
                WHERE UPPER(cloud) = UPPER(:cloud) AND region = :region
                    AND instance_type = :inst AND pricing_tier = :tier
                LIMIT 1
            """), {"cloud": cloud, "region": region, "inst": worker_inst, "tier": tier}).fetchone()
            if row:
                worker_vm_hr = float(row.cost_per_hour or 0)
    except Exception as e:
        auto_notes.append(f"VM cost DB lookup: {e}")


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
    sku = _get_sku_type(item, cloud)
    dbu_rate, dbu_rate_found = _get_dbu_price(cloud, region, tier, sku)
    dbu_per_hour, dbu_warnings = _calculate_dbu_per_hour(item, cloud, tier)
    is_serverless = _is_serverless_workload(item)
    is_fmapi = wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY')
    is_fmapi_token = is_fmapi and item.fmapi_rate_type in (
        'input_token', 'output_token', 'input', 'output',
        'cache_read', 'cache_write', 'batch_inference')
    is_fmapi_provisioned = is_fmapi and item.fmapi_rate_type in (
        'provisioned_scaling', 'provisioned_entry')

    auto_notes = list(dbu_warnings)
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
            if driver_node and driver_node in vm_prices:
                driver_vm_hr = _get_vm_hourly_rate(vm_prices[driver_node], driver_tier)
            if worker_node and worker_node in vm_prices:
                worker_vm_hr = _get_vm_hourly_rate(vm_prices[worker_node], worker_tier)

    user_notes = _get_val(item, 'notes', '') or ''
    notes_parts = [user_notes] if user_notes else []
    if auto_notes:
        notes_parts.append(' | '.join(auto_notes))

    # For DBSQL Classic/Pro, show warehouse info instead of generic driver/worker
    if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() in ('CLASSIC', 'PRO'):
        display_driver_tier = _get_pricing_tier_display(
            item.dbsql_vm_pricing_tier) if item.dbsql_vm_pricing_tier else '-'
        display_worker_tier = display_driver_tier
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
    elif wt == 'VECTOR_SEARCH' and (getattr(item, 'vector_search_storage_gb', 0) or 0) > 0:
        row = write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                   'Vector Search (Storage)', 'vector_search_storage_gb')
    return row


