"""Excel sections: totals, cost summary, legend, assumptions, footer."""
from datetime import datetime
from xlsxwriter.utility import xl_col_to_name as _col


def write_totals(sheet, fmt, row, data_start_row, data_end_row):
    """Write the totals row with SUM formulas."""
    row += 1
    sheet.merge_range(
        row,
        0,
        row,
        15,
        'WORKLOAD TOTALS:',
        fmt['total_label'],
    )

    if data_end_row >= data_start_row:
        ds = data_start_row + 1
        de = data_end_row + 1
        sheet.write_formula(row, 16, f'=SUM({_col(16)}{ds}:{_col(16)}{de})', fmt['total_dbu_num'])
        for c in [17, 18, 19]:
            sheet.write(row, c, '', fmt['total_label'])
        sheet.write_formula(row, 20, f'=SUM({_col(20)}{ds}:{_col(20)}{de})', fmt['total_dbu_value'])
        sheet.write_formula(row, 21, f'=SUM({_col(21)}{ds}:{_col(21)}{de})', fmt['total_dbu_value'])
        sheet.write_formula(row, 22, f'=SUM({_col(22)}{ds}:{_col(22)}{de})', fmt['total_dsu_num'])
        sheet.write(row, 23, '', fmt['total_label'])
        sheet.write_formula(row, 24, f'=SUM({_col(24)}{ds}:{_col(24)}{de})', fmt['total_dsu_value'])
        sheet.write_formula(row, 25, f'=SUM({_col(25)}{ds}:{_col(25)}{de})', fmt['total_dsu_value'])
        sheet.write(row, 26, '', fmt['total_label'])
        sheet.write(row, 27, '', fmt['total_label'])
        sheet.write_formula(row, 28, f'=SUM({_col(28)}{ds}:{_col(28)}{de})', fmt['total_vm_value'])
        sheet.write_formula(row, 29, f'=SUM({_col(29)}{ds}:{_col(29)}{de})', fmt['total_vm_value'])
        sheet.write_formula(row, 30, f'=SUM({_col(30)}{ds}:{_col(30)}{de})', fmt['total_vm_value'])
        sheet.write_formula(row, 31, f'=SUM({_col(31)}{ds}:{_col(31)}{de})', fmt['total_grand_value'])
        sheet.write_formula(row, 32, f'=SUM({_col(32)}{ds}:{_col(32)}{de})', fmt['total_grand_value'])
        sheet.write(row, 33, '', fmt['total_label'])
    else:
        for c in [16, 17, 18, 19, 22, 23, 26, 27]:
            sheet.write(row, c, '', fmt['total_label'])
        for c in [20, 21, 24, 25, 28, 29, 30, 31, 32]:
            if c <= 21:
                f_key = 'total_dbu_value'
            elif c <= 25:
                f_key = 'total_dsu_value'
            elif c <= 30:
                f_key = 'total_vm_value'
            else:
                f_key = 'total_grand_value'
            sheet.write(row, c, 0, fmt[f_key])
        for c in [33]:
            sheet.write(row, c, '', fmt['total_label'])

    row += 2
    return row


def write_cost_summary(sheet, fmt, row, totals_row):
    """Write the workload-only cost summary before estimate add-ons."""
    sheet.merge_range(
        row,
        0,
        row,
        9,
        'WORKLOAD COST SUMMARY (BEFORE PLATFORM ADD-ONS)',
        fmt['section_header'],
    )
    row += 1

    summary_headers = [
        '',
        'DBU Cost\n(List)',
        'DBU Cost\n(Disc.)',
        'DSU Cost\n(List)',
        'DSU Cost\n(Disc.)',
        'Driver VM',
        'Worker VM',
        'Total VM',
        'Total (List)',
        'Total (Disc.)',
    ]
    summary_fmts = [fmt['header_main'], fmt['header_dbu'], fmt['header_discount'],
                    fmt['header_dsu'], fmt['header_discount'],
                    fmt['header_vm'], fmt['header_vm'], fmt['header_vm'],
                    fmt['header_total'], fmt['header_total']]
    for col, (h, f) in enumerate(zip(summary_headers, summary_fmts)):
        sheet.write(row, col, h, f)
    row += 1

    tr = totals_row + 1
    sheet.write(row, 0, 'Monthly', fmt['cell'])
    col_map = [20, 21, 24, 25, 28, 29, 30, 31, 32]
    fmt_map = [fmt['dbu_currency'], fmt['discount_currency'],
               fmt['dsu_currency'], fmt['discount_currency'], fmt['vm_currency'],
               fmt['vm_currency'], fmt['vm_currency'], fmt['total_currency'],
               fmt['total_currency']]
    for i, (src_col, cell_fmt) in enumerate(zip(col_map, fmt_map)):
        sheet.write_formula(row, i + 1, f'={_col(src_col)}{tr}', cell_fmt)
    monthly_row = row
    row += 1

    sheet.write(row, 0, 'Annual', fmt['cell'])
    for c in range(1, 10):
        col_letter = chr(ord('B') + c - 1)
        sheet.write_formula(row, c, f'={col_letter}{monthly_row + 1}*12', fmt_map[c - 1])
    row += 2
    return row


def write_platform_addon_summary(
    sheet,
    fmt,
    row,
    totals_row,
    addon,
    product_spend_at_list=0,
):
    """Write a dedicated estimate-level add-on section after workloads."""
    sheet.merge_range(
        row,
        0,
        row,
        9,
        'PLATFORM ADD-ON',
        fmt['section_header'],
    )
    row += 1
    sheet.write(row, 0, 'Metric', fmt['header_main'])
    sheet.write(row, 1, 'Monthly Value', fmt['header_total'])
    sheet.merge_range(row, 2, row, 9, 'Details', fmt['header_main'])
    row += 1

    totals_excel_row = totals_row + 1
    selected_name = addon['display_name'] if addon else 'None selected'
    selected_detail = (
        f"{addon['cloud']} / {addon['tier']}"
        if addon
        else 'No Platform add-on charge is included'
    )
    sheet.write(row, 0, 'Selected Add-on', fmt['label'])
    sheet.write(row, 1, selected_name, fmt['value'])
    sheet.merge_range(row, 2, row, 9, selected_detail, fmt['value'])
    row += 1

    product_spend_row = row
    product_spend = (
        addon['product_spend_at_list']
        if addon
        else product_spend_at_list
    )
    sheet.write(row, 0, 'Product Spend at List', fmt['label'])
    sheet.write_formula(
        row,
        1,
        f'=U{totals_excel_row}+Y{totals_excel_row}',
        fmt['total_currency'],
        product_spend,
    )
    sheet.merge_range(
        row,
        2,
        row,
        9,
        'DBU Cost (List) + DSU Cost (List); cloud VM costs excluded',
        fmt['value'],
    )
    row += 1

    uplift_row = row
    applied_rate = addon['applied_rate_pct'] / 100 if addon else 0
    sheet.write(row, 0, 'Applied Uplift', fmt['label'])
    sheet.write(row, 1, applied_rate, fmt['pct'])
    if addon and addon['promotion']:
        uplift_detail = (
            f"Regular {addon['standard_rate_pct']:g}%; "
            f"{addon['promotion']['label']} "
            f"(ends {addon['promotion']['end_date']})"
        )
    elif addon:
        uplift_detail = f"Published uplift: {addon['standard_rate_pct']:g}%"
    else:
        uplift_detail = 'No uplift'
    sheet.merge_range(row, 2, row, 9, uplift_detail, fmt['value'])
    row += 1

    list_cost_row = row
    sheet.write(row, 0, 'Add-on Cost (List)', fmt['label'])
    sheet.write_formula(
        row,
        1,
        f'=B{product_spend_row + 1}*B{uplift_row + 1}',
        fmt['total_currency'],
        addon['cost_before_discount'] if addon else 0,
    )
    sheet.merge_range(
        row,
        2,
        row,
        9,
        'Calculated from Product Spend at List',
        fmt['value'],
    )
    row += 1

    discount_row = row
    discount = addon['discount_pct'] / 100 if addon else 0
    sheet.write(row, 0, 'Negotiated Add-on Discount', fmt['label'])
    sheet.write(row, 1, discount, fmt['pct'])
    sheet.merge_range(
        row,
        2,
        row,
        9,
        'Applied only after the published add-on uplift',
        fmt['value'],
    )
    row += 1

    discounted_cost_row = row
    sheet.write(row, 0, 'Platform Add-on Cost', fmt['label'])
    sheet.write_formula(
        row,
        1,
        f'=B{list_cost_row + 1}*(1-B{discount_row + 1})',
        fmt['total_currency'],
        addon['cost'] if addon else 0,
    )
    source = addon['source_url'] if addon else 'Not applicable'
    sheet.merge_range(row, 2, row, 9, source, fmt['value'])
    row += 2

    return row, {
        'list_cell': f'B{list_cost_row + 1}',
        'discounted_cell': f'B{discounted_cost_row + 1}',
    }


def write_final_estimate_summary(
    sheet,
    fmt,
    row,
    totals_row,
    addon_cells,
):
    """Write final monthly and annual totals after Platform add-ons."""
    sheet.merge_range(
        row,
        0,
        row,
        4,
        'FINAL ESTIMATE SUMMARY',
        fmt['section_header'],
    )
    row += 1
    sheet.write(row, 0, 'Cost Component', fmt['header_main'])
    sheet.write(row, 1, 'Monthly', fmt['header_total'])
    sheet.write(row, 2, 'Annual', fmt['header_total'])
    sheet.merge_range(row, 3, row, 4, 'Basis', fmt['header_main'])
    row += 1

    totals_excel_row = totals_row + 1
    components = [
        (
            'Workloads (List)',
            f'AF{totals_excel_row}',
            'DBU + DSU + VM before discounts',
        ),
        (
            'Workloads (After Discounts)',
            f'AG{totals_excel_row}',
            'DBU + DSU after discounts, plus VM',
        ),
        (
            'Platform Add-on (List)',
            addon_cells['list_cell'],
            'Published uplift before negotiated add-on discount',
        ),
        (
            'Platform Add-on (After Discount)',
            addon_cells['discounted_cell'],
            'Final add-on charge',
        ),
    ]
    component_rows = {}
    for label, source_cell, basis in components:
        component_rows[label] = row
        sheet.write(row, 0, label, fmt['label'])
        sheet.write_formula(row, 1, f'={source_cell}', fmt['total_currency'])
        sheet.write_formula(row, 2, f'=B{row + 1}*12', fmt['total_currency'])
        sheet.merge_range(row, 3, row, 4, basis, fmt['value'])
        row += 1

    final_row = row
    workload_row = component_rows['Workloads (After Discounts)'] + 1
    addon_row = component_rows['Platform Add-on (After Discount)'] + 1
    sheet.write(row, 0, 'FINAL ESTIMATE', fmt['total_label'])
    sheet.write_formula(
        row,
        1,
        f'=B{workload_row}+B{addon_row}',
        fmt['total_grand_value'],
    )
    sheet.write_formula(
        row,
        2,
        f'=B{final_row + 1}*12',
        fmt['total_grand_value'],
    )
    sheet.merge_range(
        row,
        3,
        row,
        4,
        'Workloads after discounts + Platform add-on after discount',
        fmt['total_label'],
    )
    row += 2
    return row


def write_legend(sheet, fmt, row):
    """Write the legend section."""
    sheet.merge_range(row, 0, row, 7, 'LEGEND', fmt['section_header'])
    row += 1
    legend_items = [
        ('Blue columns', 'DBU-related costs (Databricks compute units)'),
        ('Violet columns', 'DSU-related costs (Databricks storage units)'),
        ('Cyan columns', 'Token-based pricing (FMAPI workloads)'),
        ('Pink columns', 'Discount pricing (Discounted DBU Rate & Cost)'),
        ('Green columns', 'VM infrastructure costs (cloud provider)'),
        ('Purple columns', 'Workload total cost (DBU + DSU + VM)'),
        ('Platform Add-on', 'Separate estimate-level uplift on DBU + DSU Product Spend at List; VM costs excluded'),
        ('Serverless', 'No VM costs - compute is fully managed by Databricks'),
    ]
    for label_text, desc in legend_items:
        sheet.write(row, 0, f'• {label_text}:', fmt['label'])
        sheet.merge_range(row, 1, row, 7, desc, fmt['value'])
        row += 1
    row += 1
    return row


def write_assumptions(sheet, fmt, row, max_col):
    """Write the assumptions & notes section."""
    sheet.merge_range(row, 0, row, max_col, 'ASSUMPTIONS & NOTES', fmt['section_header'])
    row += 1
    assumptions = [
        "• This estimate is based on list pricing. Actual costs may vary based on negotiated discounts.",
        "• DBU rates are based on the selected cloud provider, region, and tier.",
        "• DSU rates use exact regional DATABRICKS_STORAGE pricing.",
        "• VM costs use default estimates. For exact VM pricing, consult your cloud provider.",
        "• FMAPI token workloads: cost = Tokens/Mo(M) × DBU/1M Tokens × $/DBU. No hourly usage.",
        "• Provisioned FMAPI workloads use Hours/Mo × DBU/Hr × $/DBU.",
        "• Discount % column is reserved for negotiated discounts (default 0% = list price).",
        "• Serverless workloads have no VM costs - compute is included in the DBU rate.",
        f"• Estimate exported: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    for assumption in assumptions:
        sheet.merge_range(row, 0, row, max_col, assumption, fmt['notes'])
        row += 1
    row += 1
    return row


def write_footer(sheet, workbook, row, max_col):
    """Write the footer line."""
    footer_format = workbook.add_format({
        'font_size': 9, 'font_color': '#94a3b8', 'align': 'center'
    })
    sheet.merge_range(row, 0, row, max_col,
                      f'Generated by Lakemeter • Databricks Pricing Calculator • {datetime.now().year}',
                      footer_format)
