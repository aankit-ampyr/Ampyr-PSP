"""Read PPA and merchant price details from Excel."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pathlib import Path
import xlwings as xw

WORKBOOK_PATH = Path(__file__).parent.parent / "Financial Model" / "Off-Grid Solution v8.xlsm"

app = xw.App(visible=False)
try:
    wb = app.books.open(str(WORKBOOK_PATH.resolve()), read_only=True)

    # Solar&BESS Operation sheet - find revenue calculation rows
    op = wb.sheets["Solar&BESS Operation"]

    print("=== SOLAR&BESS OPERATION - Full scan of key rows ===")
    for row in range(5, 200):
        label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
        total = op.range(f"I{row}").value
        if label and str(label).strip():
            # Read first few data columns
            first_val = op.range(f"J{row}").value
            print(f"  Row {row}: {str(label):<50} I={total}  J={first_val}")

    # Check for merchant price rows in FS
    fs = wb.sheets["FS"]
    print("\n=== FS ROWS 10-27 with labels ===")
    for row in range(10, 28):
        label_f = fs.range(f"F{row}").value or ""
        label_g = fs.range(f"G{row}").value or ""
        label_h = fs.range(f"H{row}").value or ""
        total = fs.range(f"I{row}").value
        # Get first ops month value (column index 53+10=63)
        first_ops = fs.cells(row, 63).value
        print(f"  Row {row}: F={str(label_f):<20} G={str(label_g):<20} "
              f"H={str(label_h):<20} Total={total}  FirstOps={first_ops}")

    # Read actual price per MWh from first ops months
    # Row 13 revenue / generation = price
    print("\n=== EFFECTIVE PRICE CHECK ===")
    # Check Solar&BESS Operation for generation and price rows
    for row in range(50, 130):
        label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
        if label and any(kw in str(label).lower() for kw in ['generation', 'yield', 'price', 'revenue',
                                                              'ppa', 'merchant', 'mwh', 'total']):
            total = op.range(f"I{row}").value
            first_val = op.cells(row, 63).value  # First ops month
            print(f"  Op row {row}: {str(label):<50} Total={total}  FirstOps={first_val}")

    # Check Curves sheet for merchant price curves (the actual monthly prices)
    curves = wb.sheets["Curves and D&T"]
    print("\n=== CURVES SHEET - Merchant prices (rows 50-100) ===")
    for row in range(50, 110):
        label = curves.range(f"C{row}").value or curves.range(f"D{row}").value or ""
        if label and str(label).strip():
            val_e = curves.range(f"E{row}").value
            print(f"  Curves row {row}: {str(label):<50} E={val_e}")

    # Read a few merchant price monthly values to understand the curve
    print("\n=== MERCHANT PRICE CURVE (first 10 ops months) ===")
    # These are typically in Curves and D&T or a dedicated sheet
    for row in range(50, 100):
        label = curves.range(f"C{row}").value or curves.range(f"D{row}").value or ""
        if label and 'merchant' in str(label).lower():
            vals = []
            for c in range(63, 73):  # ~first 10 ops months
                vals.append(curves.cells(row, c).value)
            print(f"  Row {row}: {str(label):<40} Values: {vals}")

    # Also check what the Solar&BESS Operation generation rows look like
    print("\n=== GENERATION DATA (first few ops months) ===")
    for row in [55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 70, 75, 80, 85, 90, 95, 100]:
        label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
        if label:
            first_ops = op.cells(row, 63).value
            total = op.range(f"I{row}").value
            print(f"  Op row {row}: {str(label):<50} FirstOps={first_ops}  Total={total}")

    # Look at the PPA price per MWh
    print("\n=== PPA PRICE CURVE (Curves sheet, rows 35-48) ===")
    for row in range(35, 50):
        label = curves.range(f"C{row}").value or curves.range(f"D{row}").value or ""
        if label:
            # Read first 5 ops months prices
            vals = []
            for c in range(63, 68):
                vals.append(curves.cells(row, c).value)
            val_e = curves.range(f"E{row}").value
            print(f"  Row {row}: {str(label):<40} E={val_e}  OpsVals: {vals}")

    wb.close()
finally:
    app.quit()
