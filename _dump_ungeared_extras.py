"""Dump the missing pieces needed for pure ungeared Project IRR trace."""

import openpyxl
from openpyxl.utils import get_column_letter

WB = "Financial Model/Off-Grid Solution v8.xlsm"

EXTRAS = [
    # D&T rows 100-180: tax depreciation accounts (rows 175-176 used for ungeared)
    ("D&T", (100, 180), (1, 12)),
    # FS rows 140-150: MRA (row 144)
    ("FS", (140, 175), (1, 12)),
    # Solar&BESS Operation: revenue rows 90-100, opex rows 160-180, NWC row 222
    ("Solar&BESS Operation", (90, 110), (1, 18)),
    ("Solar&BESS Operation", (155, 230), (1, 18)),
    # BESS sheet: revenue rows 90-100, opex rows 120-160
    ("BESS", (85, 165), (1, 18)),
    # Solar&BESS Inputs rows for CAPEX phasing — rows 50-75 column J for phasing percentages
    ("Construction", (40, 75), (1, 12)),
    # Curves and D&T tax rates rows 60-100 for tax depreciation method
    ("Curves and D&T", (60, 100), (1, 10)),
]


def dump(ws, name, row_range, col_range):
    print(f"\n{'='*100}\nSHEET: {name}  rows {row_range[0]}-{row_range[1]}, cols {get_column_letter(col_range[0])}-{get_column_letter(col_range[1])}\n{'='*100}")
    last_row = None
    for row in range(row_range[0], min(row_range[1] + 1, ws.max_row + 1)):
        for col in range(col_range[0], min(col_range[1] + 1, ws.max_column + 1)):
            v = ws.cell(row=row, column=col).value
            if v is None:
                continue
            s = str(v)
            if len(s) > 110:
                s = s[:107] + "..."
            if last_row is not None and row > last_row + 1:
                print()
            print(f"  {get_column_letter(col)}{row}: {s}")
            last_row = row


def main():
    wb = openpyxl.load_workbook(WB, data_only=False, keep_vba=True)
    for name, rr, cr in EXTRAS:
        if name not in wb.sheetnames:
            print(f"\n*** Sheet '{name}' missing")
            continue
        dump(wb[name], name, rr, cr)
    wb.close()


if __name__ == "__main__":
    main()
