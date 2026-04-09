"""Excel format definitions for export workbook."""


def create_formats(workbook):
    """Create and return all xlsxwriter format objects as a dict."""
    f = {}

    f['title'] = workbook.add_format({
        'bold': True, 'font_size': 18, 'font_color': '#1e293b',
        'bottom': 2, 'bottom_color': '#f97316'
    })
    f['subtitle'] = workbook.add_format({
        'font_size': 11, 'font_color': '#64748b', 'italic': True
    })
    f['section_header'] = workbook.add_format({
        'bold': True, 'font_size': 12, 'font_color': 'white',
        'bg_color': '#1e293b', 'border': 1, 'align': 'left', 'valign': 'vcenter'
    })
    f['header_main'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#f97316', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    f['header_dbu'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#3b82f6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    f['header_token'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#06b6d4', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    f['header_discount'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#ec4899', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    f['header_vm'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#10b981', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })
    f['header_total'] = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': 'white',
        'bg_color': '#8b5cf6', 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True
    })

    f['cell'] = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
    f['cell_center'] = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})
    f['cell_mono'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'font_name': 'Consolas', 'font_size': 9
    })
    f['number'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0', 'align': 'right'
    })
    f['decimal'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.00', 'align': 'right'
    })
    f['decimal3'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.000', 'align': 'right'
    })
    f['currency'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right'
    })
    f['pct'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '0%', 'align': 'center'
    })

    f['dbu_currency'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00',
        'align': 'right', 'bg_color': '#eff6ff'
    })
    f['discount_currency'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00',
        'align': 'right', 'bg_color': '#fdf2f8'
    })
    f['vm_currency'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00',
        'align': 'right', 'bg_color': '#ecfdf5'
    })
    f['total_currency'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '$#,##0.00', 'align': 'right',
        'bg_color': '#f5f3ff', 'bold': True
    })
    f['token_cell'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'bg_color': '#ecfeff'
    })
    f['token_num'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.0',
        'align': 'right', 'bg_color': '#ecfeff'
    })
    f['token_dbu'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.000',
        'align': 'right', 'bg_color': '#ecfeff'
    })

    f['total_label'] = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#f1f5f9', 'align': 'right'
    })
    f['total_dbu_value'] = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#dbeafe',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    f['total_vm_value'] = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#d1fae5',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    f['total_grand_value'] = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#ede9fe',
        'num_format': '$#,##0.00', 'align': 'right'
    })
    f['total_dbu_num'] = workbook.add_format({
        'bold': True, 'border': 1, 'bg_color': '#f1f5f9',
        'num_format': '#,##0', 'align': 'right'
    })

    f['label'] = workbook.add_format({'bold': True, 'font_color': '#64748b', 'align': 'right'})
    f['value'] = workbook.add_format({'font_color': '#1e293b'})
    f['notes'] = workbook.add_format({
        'font_size': 9, 'font_color': '#64748b', 'italic': True, 'text_wrap': True
    })
    f['serverless'] = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center',
        'font_color': '#059669', 'italic': True
    })

    return f
