"""Excel row writing logic with formula generation."""
from xlsxwriter.utility import xl_col_to_name as _col

from .excel_columns import NUM_COLS, COLUMN_WIDTHS, get_headers  # noqa: F401


def write_data_row(sheet, row, row_data, is_fmapi_token, is_serverless, fmt,
                   is_storage_row=False, cost_accumulator=None):
    """Write a single export row with formulas for all computed cells."""
    r = row + 1  # 1-indexed for Excel formulas

    # Col 0-5: static fields
    sheet.write(row, 0, row_data['idx'], fmt['cell_center'])
    sheet.write(row, 1, row_data['name'], fmt['cell'])
    sheet.write(row, 2, row_data['type_display'], fmt['cell'])
    if is_serverless:
        sheet.write(row, 3, "Serverless", fmt['serverless'])
    else:
        sheet.write(row, 3, "Classic", fmt['cell_center'])
    sheet.write(row, 4, row_data['config'], fmt['cell'])
    sheet.write(row, 5, row_data['sku'], fmt['cell_mono'])

    # Col 6-10: VM config
    if is_serverless:
        for c in range(6, 11):
            sheet.write(row, c, '-', fmt['serverless'])
    else:
        sheet.write(row, 6, row_data.get('driver_node', '-'), fmt['cell_mono'])
        sheet.write(row, 7, row_data.get('worker_node', '-'), fmt['cell_mono'])
        sheet.write(row, 8, row_data['num_workers'], fmt['number'])
        sheet.write(row, 9, row_data.get('driver_tier', '-'), fmt['cell_center'])
        sheet.write(row, 10, row_data.get('worker_tier', '-'), fmt['cell_center'])

    # Col 11: Hours/Mo
    _write_hours(sheet, row, row_data, is_fmapi_token, is_storage_row, fmt)

    # Col 12-14: Token columns
    _write_token_cols(sheet, row, row_data, is_fmapi_token, fmt)

    # Col 15: DBU/Hr
    if is_fmapi_token or row_data.get('is_quantity_based', False):
        sheet.write(row, 15, 'N/A', fmt['token_cell'])
    elif is_storage_row:
        sheet.write(row, 15, 'N/A', fmt['cell_center'])
    else:
        sheet.write(row, 15, row_data['dbu_per_hour'], fmt['decimal'])

    # Col 16-21: DBU calculations with formulas
    _write_dbu_costs(sheet, row, r, row_data, is_fmapi_token, is_storage_row, fmt)

    # Col 22-25: DSU calculations
    _write_dsu_costs(sheet, row, r, row_data, fmt)

    # Col 26-30: VM costs
    _write_vm_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt)

    # Col 31-32: Total costs
    _write_total_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt)

    # Col 33: Notes
    sheet.write(row, 33, row_data.get('notes', ''), fmt['cell'])

    if cost_accumulator is not None:
        dbu_list = (
            row_data.get('total_dbus_month', 0)
            * row_data.get('dbu_rate', 0)
        )
        dsu_list = (
            row_data.get('monthly_dsus', 0)
            * row_data.get('dsu_rate', 0)
        )
        cost_accumulator['product_spend_at_list'] += dbu_list + dsu_list


def _write_hours(sheet, row, row_data, is_fmapi_token, is_storage_row, fmt):
    if is_fmapi_token or row_data.get('is_quantity_based', False):
        sheet.write(row, 11, 'N/A', fmt['token_cell'])
    elif is_storage_row:
        sheet.write(row, 11, 'N/A', fmt['cell_center'])
    else:
        sheet.write(row, 11, row_data['hours_per_month'], fmt['decimal'])


def _write_token_cols(sheet, row, row_data, is_fmapi_token, fmt):
    if row_data.get('token_columns_na', False):
        for column in range(12, 15):
            sheet.write(row, column, 'N/A', fmt['cell_center'])
    elif is_fmapi_token:
        sheet.write(row, 12, row_data.get('token_type', ''), fmt['token_cell'])
        sheet.write(row, 13, row_data['token_quantity_millions'], fmt['token_num'])
        sheet.write(row, 14, row_data['dbu_per_million'], fmt['token_dbu'])
    else:
        sheet.write(row, 12, '-', fmt['cell_center'])
        sheet.write(row, 13, '-', fmt['cell_center'])
        sheet.write(row, 14, '-', fmt['cell_center'])


def _write_dbu_costs(sheet, row, r, row_data, is_fmapi_token, is_storage_row, fmt):
    total_dbus_month = row_data.get('total_dbus_month', 0)
    dbu_rate = row_data['dbu_rate']
    discount_pct = row_data['discount_pct']

    # Col 16: DBUs/Mo
    if is_storage_row:
        sheet.write(row, 16, 0, fmt['number'])
    elif row_data.get('is_quantity_based', False):
        # Quantity workloads have no Hours/Mo × DBU/Hr basis. Writing their
        # computed DBUs as a value keeps downstream formulas recalculation-safe.
        dbu_format = (
            fmt['decimal']
            if row_data.get('show_dbu_month_decimals', False)
            else fmt['number']
        )
        sheet.write(row, 16, total_dbus_month, dbu_format)
    elif is_fmapi_token:
        formula = f'={_col(13)}{r}*{_col(14)}{r}'
        sheet.write_formula(row, 16, formula, fmt['number'], total_dbus_month)
    else:
        formula = f'={_col(15)}{r}*{_col(11)}{r}'
        sheet.write_formula(row, 16, formula, fmt['number'], total_dbus_month)

    # Col 17: DBU Rate (List)
    sheet.write(row, 17, 0 if is_storage_row else dbu_rate, fmt['currency'])
    # Col 18: Discount %
    sheet.write(row, 18, discount_pct, fmt['pct'])

    # Col 19: DBU Rate (Disc.) — FORMULA: =R*(1-S)
    discounted_rate = (
        0 if is_storage_row else dbu_rate * (1 - discount_pct)
    )
    formula = f'={_col(17)}{r}*(1-{_col(18)}{r})'
    sheet.write_formula(row, 19, formula, fmt['currency'], discounted_rate)

    # Col 20: DBU Cost (List)
    dbu_cost_list = total_dbus_month * dbu_rate
    if is_storage_row:
        sheet.write(row, 20, 0, fmt['dbu_currency'])
    else:
        formula = f'={_col(16)}{r}*{_col(17)}{r}'
        sheet.write_formula(row, 20, formula, fmt['dbu_currency'], dbu_cost_list)

    # Col 21: DBU Cost (Disc.)
    dbu_cost_disc = total_dbus_month * discounted_rate
    if is_storage_row:
        sheet.write(row, 21, 0, fmt['discount_currency'])
    else:
        formula = f'={_col(16)}{r}*{_col(19)}{r}'
        sheet.write_formula(row, 21, formula, fmt['discount_currency'], dbu_cost_disc)


def _write_dsu_costs(sheet, row, r, row_data, fmt):
    """Write monthly DSUs and their list/discounted cost formulas."""
    monthly_dsus = row_data.get('monthly_dsus', 0)
    dsu_rate = row_data.get('dsu_rate', 0)
    discount_pct = row_data.get('discount_pct', 0)
    dsu_cost_list = monthly_dsus * dsu_rate
    dsu_cost_disc = dsu_cost_list * (1 - discount_pct)

    sheet.write(row, 22, monthly_dsus, fmt['decimal3'])
    sheet.write(row, 23, dsu_rate, fmt['currency'])
    sheet.write_formula(
        row,
        24,
        f'={_col(22)}{r}*{_col(23)}{r}',
        fmt['dsu_currency'],
        dsu_cost_list,
    )
    sheet.write_formula(
        row,
        25,
        f'={_col(24)}{r}*(1-{_col(18)}{r})',
        fmt['discount_currency'],
        dsu_cost_disc,
    )


def _write_vm_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt):
    driver_vm_hr = row_data.get('driver_vm_cost_per_hour', 0)
    worker_vm_hr = row_data.get('worker_vm_cost_per_hour', 0)
    hours = row_data.get('hours_per_month', 0)
    nw = row_data.get('num_workers', 0)

    if is_serverless or is_storage_row:
        for c in range(26, 31):
            sheet.write(row, c, 0, fmt['vm_currency'])
    else:
        sheet.write(row, 26, driver_vm_hr, fmt['currency'])
        sheet.write(row, 27, worker_vm_hr, fmt['currency'])
        driver_vm_total = driver_vm_hr * hours
        formula = f'={_col(26)}{r}*{_col(11)}{r}'
        sheet.write_formula(row, 28, formula, fmt['vm_currency'], driver_vm_total)
        worker_vm_total = worker_vm_hr * hours * nw
        formula = f'={_col(27)}{r}*{_col(11)}{r}*{_col(8)}{r}'
        sheet.write_formula(row, 29, formula, fmt['vm_currency'], worker_vm_total)
        formula = f'={_col(28)}{r}+{_col(29)}{r}'
        sheet.write_formula(row, 30, formula, fmt['vm_currency'],
                            driver_vm_total + worker_vm_total)


def _write_total_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt):
    driver_vm_hr = row_data.get('driver_vm_cost_per_hour', 0)
    worker_vm_hr = row_data.get('worker_vm_cost_per_hour', 0)
    hours = row_data.get('hours_per_month', 0)
    nw = row_data.get('num_workers', 0)
    dbu_rate = row_data['dbu_rate']
    discount_pct = row_data['discount_pct']
    total_dbus_month = row_data.get('total_dbus_month', 0)
    monthly_dsus = row_data.get('monthly_dsus', 0)
    dsu_rate = row_data.get('dsu_rate', 0)
    discounted_rate = dbu_rate * (1 - discount_pct)
    dbu_cost_list = total_dbus_month * dbu_rate
    dbu_cost_disc = total_dbus_month * discounted_rate
    dsu_cost_list = monthly_dsus * dsu_rate
    dsu_cost_disc = dsu_cost_list * (1 - discount_pct)
    vm_total = 0
    if not is_serverless and not is_storage_row:
        vm_total = driver_vm_hr * hours + worker_vm_hr * hours * nw

    # Col 31: Total Cost (List)
    formula = f'={_col(20)}{r}+{_col(24)}{r}+{_col(30)}{r}'
    sheet.write_formula(
        row,
        31,
        formula,
        fmt['total_currency'],
        dbu_cost_list + dsu_cost_list + vm_total,
    )

    # Col 32: Total Cost (Disc.)
    formula = f'={_col(21)}{r}+{_col(25)}{r}+{_col(30)}{r}'
    sheet.write_formula(
        row,
        32,
        formula,
        fmt['total_currency'],
        dbu_cost_disc + dsu_cost_disc + vm_total,
    )
