"""Parse exported Excel workbooks and extract values for verification.

The Lakemeter Excel export has a 30-column layout (see excel_columns.py).
Key columns for verification:
  Col 0: #           Col 11: Hours/Mo       Col 16: DBUs/Mo
  Col 1: Name        Col 12: Token Type     Col 17: DBU Rate (List)
  Col 2: Type        Col 13: Tokens/Mo (M)  Col 18: Discount %
  Col 3: Mode        Col 14: DBU/1M Tokens  Col 19: DBU Rate (Disc.)
  Col 4: Config      Col 15: DBU/Hr         Col 20: DBU Cost (List)
  Col 5: SKU         Col 21: DBU Cost (Disc.)
  Col 6: Driver Node Col 22: Driver VM $/Hr Col 27: Total Cost (List)
  Col 7: Worker Node Col 23: Worker VM $/Hr Col 28: Total Cost (Disc.)
  Col 8: Workers     Col 24: Driver VM Cost Col 29: Notes
  Col 9: Driver Tier Col 25: Worker VM Cost
  Col 10: Worker Tier Col 26: Total VM Cost
"""
import openpyxl
from io import BytesIO
from typing import Optional


class ExcelRow:
    """Parsed row from the Excel export."""

    def __init__(self, row_data: list):
        self.raw = row_data
        self.idx = row_data[0]
        self.name = row_data[1]
        self.type_display = row_data[2]
        self.mode = row_data[3]
        self.config = row_data[4]
        self.sku = row_data[5]
        self.driver_node = row_data[6]
        self.worker_node = row_data[7]
        self.num_workers = _to_num(row_data[8])
        self.driver_tier = row_data[9]
        self.worker_tier = row_data[10]
        self.hours_per_month = _to_num(row_data[11])
        self.token_type = row_data[12]
        self.tokens_per_month_m = _to_num(row_data[13])
        self.dbu_per_million = _to_num(row_data[14])
        self.dbu_per_hour = _to_num(row_data[15])
        self.dbus_per_month = _to_num(row_data[16])
        self.dbu_rate_list = _to_num(row_data[17])
        self.discount_pct = _to_num(row_data[18])
        self.dbu_rate_disc = _to_num(row_data[19])
        self.dbu_cost_list = _to_num(row_data[20])
        self.dbu_cost_disc = _to_num(row_data[21])
        self.driver_vm_per_hr = _to_num(row_data[22])
        self.worker_vm_per_hr = _to_num(row_data[23])
        self.driver_vm_cost = _to_num(row_data[24])
        self.worker_vm_cost = _to_num(row_data[25])
        self.total_vm_cost = _to_num(row_data[26])
        self.total_cost_list = _to_num(row_data[27])
        self.total_cost_disc = _to_num(row_data[28])
        self.notes = row_data[29] if len(row_data) > 29 else ""

    @property
    def is_serverless(self) -> bool:
        return str(self.mode).strip().lower() == "serverless"

    @property
    def is_fmapi_token(self) -> bool:
        return self.token_type not in (None, "", "-", "N/A")


def _to_num(val) -> Optional[float]:
    """Convert cell value to float, handling N/A, '-', None, formulas."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s in ("-", "N/A", "", "Serverless"):
        return None
    try:
        return float(s.replace(",", "").replace("$", "").replace("%", ""))
    except (ValueError, TypeError):
        return None


def parse_estimate_excel(excel_bytes: BytesIO) -> dict:
    """Parse an exported estimate Excel file.

    Returns dict with:
      - 'rows': list of ExcelRow (data rows only, excludes headers/totals)
      - 'totals': dict of total values from the TOTALS row
      - 'raw_sheet': the openpyxl worksheet for custom queries
    """
    wb = openpyxl.load_workbook(excel_bytes, data_only=True)
    sheet = wb.active

    rows = []
    totals = {}
    header_row_idx = None
    data_start = None

    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        # Find the header row by looking for '#' and 'Workload Name'
        if row[0] == '#' and row[1] == 'Workload Name':
            header_row_idx = row_idx
            data_start = row_idx + 1
            continue

        # Once we've found headers, collect data rows
        if data_start and row_idx >= data_start:
            # Check if this is a data row (starts with a number)
            if isinstance(row[0], (int, float)) and row[0] > 0:
                rows.append(ExcelRow(list(row)))
            # Check for TOTALS row
            elif row[1] and 'TOTAL' in str(row[1]).upper():
                totals = {
                    "dbus_per_month": _to_num(row[16]),
                    "dbu_cost_list": _to_num(row[20]),
                    "dbu_cost_disc": _to_num(row[21]),
                    "driver_vm_cost": _to_num(row[24]),
                    "worker_vm_cost": _to_num(row[25]),
                    "total_vm_cost": _to_num(row[26]),
                    "total_cost_list": _to_num(row[27]),
                    "total_cost_disc": _to_num(row[28]),
                }
                break  # Stop after totals

    wb.close()
    return {"rows": rows, "totals": totals, "row_count": len(rows)}
