"""Quick script to read Excel revenue detail rows from FS sheet."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pathlib import Path
import xlwings as xw

WORKBOOK_PATH = Path(__file__).parent.parent / "Financial Model" / "Off-Grid Solution v8.xlsm"

app = xw.App(visible=False)
try:
    wb = app.books.open(str(WORKBOOK_PATH.resolve()), read_only=True)
    fs = wb.sheets["FS"]
    eq = wb.sheets["Equity"]
    inp = wb.sheets["Solar&BESS Inputs"]
    dt = wb.sheets["D&T"]

    # Check model start from Timing sheet or Equity row 5
    print("=== TIMING ===")
    try:
        timing = wb.sheets["Timing"]
        for r in range(5, 30):
            label = timing.range(f"C{r}").value
            val = timing.range(f"J{r}").value
            if label or val:
                print(f"  Timing row {r}: {label} = {val}")
    except Exception as e:
        print(f"  (Timing sheet error: {e})")

    # Read first few dates from Equity row 5
    dates_sample = eq.range("J5:S5").value
    print(f"\n=== DATES (first 10) ===")
    for i, d in enumerate(dates_sample):
        print(f"  Period {i+1}: {d}")

    # Model start from Equity I5 or H5
    for col in ["G", "H", "I"]:
        val = eq.range(f"{col}5").value
        print(f"  Equity {col}5 = {val}")

    # FS Revenue breakdown - first ops month values
    print("\n=== FS REVENUE DETAIL (rows 13-27) ===")
    # Find first non-zero revenue column
    rev_row = fs.range("J27").expand('right').value
    if isinstance(rev_row, list):
        first_nz = next((i for i, v in enumerate(rev_row) if v and v != 0), 0)
        col_offset = first_nz + 10  # Column J = 10
        col_letter = chr(65 + col_offset) if col_offset < 26 else \
            chr(64 + col_offset // 26) + chr(65 + col_offset % 26)
        print(f"  First non-zero revenue at column index {first_nz} (col ~{col_offset})")
    else:
        col_offset = 10

    # Read labels from column G/H and values from first ops column
    for row in range(13, 28):
        label_g = fs.range(f"G{row}").value
        label_h = fs.range(f"H{row}").value
        label = label_g or label_h or ""
        # Read first 3 ops month values
        vals = []
        for offset in [first_nz, first_nz+1, first_nz+2]:
            cell = fs.cells(row, 10 + offset)  # 10 = col J (1-based)
            vals.append(cell.value)
        total_col = fs.range(f"I{row}").value
        print(f"  Row {row}: {label:<40} First3: {vals}  Total: {total_col}")

    # BESS revenue detail
    print("\n=== FS BESS REVENUE (rows 20-27) ===")
    for row in range(20, 28):
        label = fs.range(f"G{row}").value or fs.range(f"H{row}").value or ""
        total = fs.range(f"I{row}").value
        print(f"  Row {row}: {label:<40} Total: {total}")

    # OPEX detail
    print("\n=== FS EXPENSES (rows 30-59) ===")
    for row in range(30, 60):
        label = fs.range(f"G{row}").value or fs.range(f"H{row}").value or ""
        total = fs.range(f"I{row}").value
        if total and total != 0:
            print(f"  Row {row}: {label:<40} Total: {total}")

    # PPA price - check what the effective price is
    print("\n=== PPA / MERCHANT PRICE ===")
    # Check Solar&BESS Operation sheet for revenue formula
    try:
        op = wb.sheets["Solar&BESS Operation"]
        for row in [13, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25]:
            label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
            total = op.range(f"I{row}").value
            print(f"  Operation row {row}: {label:<40} Total: {total}")
    except Exception as e:
        print(f"  (Operation sheet error: {e})")

    # Check for PPA price row in inputs
    print("\n=== PPA PRICE FROM INPUTS ===")
    for row in [73, 74, 75, 76, 77, 78]:
        label = inp.range(f"H{row}").value or inp.range(f"G{row}").value or ""
        val_j = inp.range(f"J{row}").value
        val_h = inp.range(f"H{row}").value
        print(f"  Input row {row}: {label:<40} H={val_h}  J={val_j}")

    # Look for the actual PPA price somewhere
    print("\n=== OVERALL INPUTS SHEET ===")
    try:
        oi = wb.sheets["Overall Inputs"]
        for row in range(5, 50):
            label = oi.range(f"C{row}").value or oi.range(f"D{row}").value or ""
            val = oi.range(f"E{row}").value
            if label and "price" in str(label).lower():
                print(f"  Overall row {row}: {label} = {val}")
    except Exception as e:
        print(f"  (Overall Inputs error: {e})")

    # Check merchant curves
    print("\n=== MERCHANT / PRICE CURVES ===")
    try:
        curves = wb.sheets["Curves and D&T"]
        # Look for merchant price rows
        for row in range(5, 50):
            label = curves.range(f"C{row}").value or curves.range(f"D{row}").value or ""
            if label:
                val = curves.range(f"E{row}").value
                print(f"  Curves row {row}: {label:<50} = {val}")
    except Exception as e:
        print(f"  (Curves sheet error: {e})")

    # Check Solar&BESS Operation for revenue calculation
    print("\n=== SOLAR&BESS OPERATION - REVENUE ROWS ===")
    try:
        op = wb.sheets["Solar&BESS Operation"]
        # Revenue rows typically around 130-180
        for row in range(130, 180):
            label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
            total = op.range(f"I{row}").value
            if (label and total) or (total and total != 0):
                print(f"  Op row {row}: {label:<50} Total: {total}")
    except Exception as e:
        print(f"  (error: {e})")

    # Check what the Equity row 5 actually contains (period dates vs labels)
    print("\n=== EQUITY SHEET STRUCTURE ===")
    for row in [3, 4, 5, 6, 7]:
        labels = []
        for col in ["G", "H", "I", "J", "K"]:
            val = eq.range(f"{col}{row}").value
            labels.append(f"{col}={val}")
        print(f"  Row {row}: {', '.join(labels)}")

    wb.close()
finally:
    app.quit()
