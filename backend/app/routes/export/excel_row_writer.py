"""Excel row writing logic with formula generation."""
from xlsxwriter.utility import xl_col_to_name as _col

from .excel_columns import NUM_COLS, COLUMN_WIDTHS, get_headers  # noqa: F401


def write_data_row(sheet, row, row_data, is_fmapi_token, is_serverless, fmt,
                   is_storage_row=False):
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
    if is_fmapi_token:
        sheet.write(row, 15, 'N/A', fmt['token_cell'])
    elif is_storage_row:
        sheet.write(row, 15, 'N/A', fmt['cell_center'])
    else:
        sheet.write(row, 15, row_data['dbu_per_hour'], fmt['decimal'])

    # Col 16-21: DBU calculations with formulas
    _write_dbu_costs(sheet, row, r, row_data, is_fmapi_token, is_storage_row, fmt)

    # Col 22-26: VM costs
    _write_vm_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt)

    # Col 27-28: Total costs
    _write_total_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt)

    # Col 29: Notes
    sheet.write(row, 29, row_data.get('notes', ''), fmt['cell'])


def _write_hours(sheet, row, row_data, is_fmapi_token, is_storage_row, fmt):
    if is_fmapi_token:
        sheet.write(row, 11, 'N/A', fmt['token_cell'])
    elif is_storage_row:
        sheet.write(row, 11, 'N/A', fmt['cell_center'])
    else:
        sheet.write(row, 11, row_data['hours_per_month'], fmt['decimal'])


def _write_token_cols(sheet, row, row_data, is_fmapi_token, fmt):
    if is_fmapi_token:
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

    # Col 16: DBUs/Mo — FORMULA
    if is_storage_row:
        sheet.write(row, 16, 0, fmt['number'])
    elif is_fmapi_token:
        formula = f'={_col(13)}{r}*{_col(14)}{r}'
        sheet.write_formula(row, 16, formula, fmt['number'], total_dbus_month)
    else:
        formula = f'={_col(15)}{r}*{_col(11)}{r}'
        sheet.write_formula(row, 16, formula, fmt['number'], total_dbus_month)

    # Col 17: DBU Rate (List)
    sheet.write(row, 17, dbu_rate, fmt['currency'])
    # Col 18: Discount %
    sheet.write(row, 18, discount_pct, fmt['pct'])

    # Col 19: DBU Rate (Disc.) — FORMULA: =R*(1-S)
    discounted_rate = dbu_rate * (1 - discount_pct)
    formula = f'={_col(17)}{r}*(1-{_col(18)}{r})'
    sheet.write_formula(row, 19, formula, fmt['currency'], discounted_rate)

    # Col 20: DBU Cost (List)
    dbu_cost_list = total_dbus_month * dbu_rate
    if is_storage_row:
        storage_cost = row_data.get('storage_cost_monthly', 0)
        sheet.write(row, 20, storage_cost, fmt['dbu_currency'])
    else:
        formula = f'={_col(16)}{r}*{_col(17)}{r}'
        sheet.write_formula(row, 20, formula, fmt['dbu_currency'], dbu_cost_list)

    # Col 21: DBU Cost (Disc.)
    dbu_cost_disc = total_dbus_month * discounted_rate
    if is_storage_row:
        storage_cost = row_data.get('storage_cost_monthly', 0)
        formula = f'={_col(20)}{r}*(1-{_col(18)}{r})'
        sheet.write_formula(row, 21, formula, fmt['discount_currency'],
                            storage_cost * (1 - discount_pct))
    else:
        formula = f'={_col(16)}{r}*{_col(19)}{r}'
        sheet.write_formula(row, 21, formula, fmt['discount_currency'], dbu_cost_disc)


def _write_vm_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt):
    driver_vm_hr = row_data.get('driver_vm_cost_per_hour', 0)
    worker_vm_hr = row_data.get('worker_vm_cost_per_hour', 0)
    hours = row_data.get('hours_per_month', 0)
    nw = row_data.get('num_workers', 0)

    if is_serverless or is_storage_row:
        for c in range(22, 27):
            sheet.write(row, c, 0, fmt['vm_currency'])
    else:
        sheet.write(row, 22, driver_vm_hr, fmt['currency'])
        sheet.write(row, 23, worker_vm_hr, fmt['currency'])
        driver_vm_total = driver_vm_hr * hours
        formula = f'={_col(22)}{r}*{_col(11)}{r}'
        sheet.write_formula(row, 24, formula, fmt['vm_currency'], driver_vm_total)
        worker_vm_total = worker_vm_hr * hours * nw
        formula = f'={_col(23)}{r}*{_col(11)}{r}*{_col(8)}{r}'
        sheet.write_formula(row, 25, formula, fmt['vm_currency'], worker_vm_total)
        formula = f'={_col(24)}{r}+{_col(25)}{r}'
        sheet.write_formula(row, 26, formula, fmt['vm_currency'],
                            driver_vm_total + worker_vm_total)


def _write_total_costs(sheet, row, r, row_data, is_serverless, is_storage_row, fmt):
    driver_vm_hr = row_data.get('driver_vm_cost_per_hour', 0)
    worker_vm_hr = row_data.get('worker_vm_cost_per_hour', 0)
    hours = row_data.get('hours_per_month', 0)
    nw = row_data.get('num_workers', 0)
    dbu_rate = row_data['dbu_rate']
    discount_pct = row_data['discount_pct']
    total_dbus_month = row_data.get('total_dbus_month', 0)
    discounted_rate = dbu_rate * (1 - discount_pct)
    dbu_cost_list = total_dbus_month * dbu_rate
    dbu_cost_disc = total_dbus_month * discounted_rate
    vm_total = 0
    if not is_serverless and not is_storage_row:
        vm_total = driver_vm_hr * hours + worker_vm_hr * hours * nw

    # Col 27: Total Cost (List)
    if is_storage_row:
        storage_cost = row_data.get('storage_cost_monthly', 0)
        formula = f'={_col(20)}{r}+{_col(26)}{r}'
        sheet.write_formula(row, 27, formula, fmt['total_currency'], storage_cost)
    else:
        formula = f'={_col(20)}{r}+{_col(26)}{r}'
        sheet.write_formula(row, 27, formula, fmt['total_currency'],
                            dbu_cost_list + vm_total)

    # Col 28: Total Cost (Disc.)
    if is_storage_row:
        storage_cost = row_data.get('storage_cost_monthly', 0)
        formula = f'={_col(21)}{r}+{_col(26)}{r}'
        sheet.write_formula(row, 28, formula, fmt['total_currency'],
                            storage_cost * (1 - discount_pct))
    else:
        formula = f'={_col(21)}{r}+{_col(26)}{r}'
        sheet.write_formula(row, 28, formula, fmt['total_currency'],
                            dbu_cost_disc + vm_total)
