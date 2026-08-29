"""Excel column layout constants and header definitions."""

# 34-column layout constants
NUM_COLS = 34
COLUMN_WIDTHS = [
    34,  # 0: # / summary labels
    22,  # 1: Name
    18,  # 2: Type
    12,  # 3: Mode
    30,  # 4: Config
    22,  # 5: SKU
    18,  # 6: Driver Node
    18,  # 7: Worker Node
    8,   # 8: Workers
    12,  # 9: Driver Tier
    12,  # 10: Worker Tier
    10,  # 11: Hours/Mo
    12,  # 12: Token Type
    12,  # 13: Tokens/Mo (M)
    12,  # 14: DBU/1M Tokens
    10,  # 15: DBU/Hr
    12,  # 16: DBUs/Mo
    10,  # 17: DBU Rate (List)
    9,   # 18: Discount %
    10,  # 19: DBU Rate (Disc.)
    14,  # 20: DBU Cost (List)
    14,  # 21: DBU Cost (Disc.)
    12,  # 22: DSUs/Mo
    10,  # 23: DSU Rate (List)
    14,  # 24: DSU Cost (List)
    14,  # 25: DSU Cost (Disc.)
    12,  # 26: Driver VM $/Hr
    12,  # 27: Worker VM $/Hr
    12,  # 28: Driver VM Cost
    12,  # 29: Worker VM Cost
    12,  # 30: Total VM Cost
    14,  # 31: Total Cost (List)
    14,  # 32: Total Cost (Disc.)
    25,  # 33: Notes
]


def get_headers(fmt):
    """Return the header row spec as list of (label, format) tuples."""
    return [
        ('#', fmt['header_main']),
        ('Workload Name', fmt['header_main']),
        ('Type', fmt['header_main']),
        ('Mode', fmt['header_main']),
        ('Configuration', fmt['header_main']),
        ('SKU', fmt['header_main']),
        ('Driver Node', fmt['header_vm']),
        ('Worker Node', fmt['header_vm']),
        ('Workers', fmt['header_vm']),
        ('Driver Tier', fmt['header_vm']),
        ('Worker Tier', fmt['header_vm']),
        ('Hours/Mo', fmt['header_dbu']),
        ('Token Type', fmt['header_token']),
        ('Tokens/Mo (M)', fmt['header_token']),
        ('DBU/1M Tokens', fmt['header_token']),
        ('DBU/Hr', fmt['header_dbu']),
        ('DBUs/Mo', fmt['header_dbu']),
        ('DBU Rate\n(List)', fmt['header_dbu']),
        ('Discount %', fmt['header_discount']),
        ('DBU Rate\n(Disc.)', fmt['header_discount']),
        ('DBU Cost\n(List)', fmt['header_dbu']),
        ('DBU Cost\n(Disc.)', fmt['header_discount']),
        ('DSUs/Mo', fmt['header_dsu']),
        ('DSU Rate\n(List)', fmt['header_dsu']),
        ('DSU Cost\n(List)', fmt['header_dsu']),
        ('DSU Cost\n(Disc.)', fmt['header_discount']),
        ('Driver\nVM $/Hr', fmt['header_vm']),
        ('Worker\nVM $/Hr', fmt['header_vm']),
        ('Driver\nVM Cost', fmt['header_vm']),
        ('Worker\nVM Cost', fmt['header_vm']),
        ('Total\nVM Cost', fmt['header_vm']),
        ('Total Cost\n(List)', fmt['header_total']),
        ('Total Cost\n(Disc.)', fmt['header_total']),
        ('Notes', fmt['header_main']),
    ]
