"""Excel sections: totals, cost summary, legend, assumptions, footer."""
from datetime import datetime
from xlsxwriter.utility import xl_col_to_name as _col


def write_totals(sheet, fmt, row, data_start_row, data_end_row):
    """Write the totals row with SUM formulas."""
    row += 1
    sheet.merge_range(row, 0, row, 15, 'TOTALS:', fmt['total_label'])

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
    """Write the cost summary section (monthly + annual)."""
    sheet.merge_range(row, 0, row, 9, 'COST SUMMARY', fmt['section_header'])
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


def write_dbu_summary(sheet, fmt, row, data_start_row, data_end_row):
    """Write total DBUs/month and DSUs/month summary lines."""
    sheet.merge_range(row, 0, row, 1, 'Total DBUs/Month:', fmt['label'])
    if data_end_row >= data_start_row:
        sheet.write_formula(row, 2,
                            f'=SUM({_col(16)}{data_start_row + 1}:{_col(16)}{data_end_row + 1})',
                            fmt['total_dbu_num'])
    else:
        sheet.write(row, 2, 0, fmt['total_dbu_num'])
    row += 1
    sheet.merge_range(row, 0, row, 1, 'Total DSUs/Month:', fmt['label'])
    if data_end_row >= data_start_row:
        sheet.write_formula(row, 2,
                            f'=SUM({_col(22)}{data_start_row + 1}:{_col(22)}{data_end_row + 1})',
                            fmt['total_dsu_num'])
    else:
        sheet.write(row, 2, 0, fmt['total_dsu_num'])
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
        ('Purple columns', 'Total cost (DBU + DSU + VM)'),
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
