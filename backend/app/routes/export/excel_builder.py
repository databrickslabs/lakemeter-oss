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


def build_estimate_excel(estimate, line_items, cloud, region, tier):
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
    row = _write_line_items(sheet, fmt, row, line_items, cloud, region, tier)
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


def _write_line_items(sheet, fmt, row, line_items, cloud, region, tier):
    """Write all line item data rows including storage sub-rows."""
    for idx, item in enumerate(line_items):
        row = _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier)
    return row


def _write_single_item(sheet, fmt, row, idx, item, cloud, region, tier):
    """Write one line item (and its storage sub-row if applicable)."""
    wt = item.workload_type or 'JOBS'
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
    # Look up VM costs from DEFAULT_VM_PRICING; serverless workloads have no VM costs
    driver_vm_hr = 0
    worker_vm_hr = 0
    if not is_serverless:
        cloud_lc = (cloud or 'aws').lower()
        vm_prices = DEFAULT_VM_PRICING.get(cloud_lc, {})
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

    base_row = {
        'idx': idx + 1,
        'name': _get_val(item, 'workload_name', f'Workload {idx + 1}'),
        'type_display': _get_workload_display_name(wt),
        'config': _get_workload_config_details(item),
        'sku': sku,
        'driver_node': _get_val(item, 'driver_node_type', '-') or '-',
        'worker_node': _get_val(item, 'worker_node_type', '-') or '-',
        'num_workers': num_workers,
        'driver_tier': _get_pricing_tier_display(item.driver_pricing_tier)
        if hasattr(item, 'driver_pricing_tier') else '-',
        'worker_tier': _get_pricing_tier_display(item.worker_pricing_tier)
        if hasattr(item, 'worker_pricing_tier') else '-',
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
    elif wt == 'VECTOR_SEARCH' and (getattr(item, 'vector_search_storage_gb', 0) or 0) > 0:
        row = write_storage_subrow(sheet, fmt, row, item, idx, cloud, region, tier,
                                   'Vector Search (Storage)', 'vector_search_storage_gb')
    return row


