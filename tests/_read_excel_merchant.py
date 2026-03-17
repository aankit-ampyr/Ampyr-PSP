"""Read merchant price curve and revenue structure."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pathlib import Path
import xlwings as xw

WORKBOOK_PATH = Path(__file__).parent.parent / "Financial Model" / "Off-Grid Solution v8.xlsm"

app = xw.App(visible=False)
try:
    wb = app.books.open(str(WORKBOOK_PATH.resolve()), read_only=True)

    # The PPA is 170 GBP/MWh for 10 years with NIL indexation.
    # Row 14 (merchant) has 155k total - this is the post-PPA merchant revenue.
    # Need to understand: PPA covers X years, then merchant kicks in?

    curves = wb.sheets["Curves and D&T"]
    fs = wb.sheets["FS"]
    inp = wb.sheets["Solar&BESS Inputs"]

    # PPA tenor from row 37 col E = 10 years
    print("=== PPA DETAILS ===")
    ppa_selection = inp.range("J73").value
    print(f"  PPA Selection: {ppa_selection}")
    ppa_price = curves.range(f"E37").value  # col E for "PPA with Data Centre"
    print(f"  PPA tenor (E37): {ppa_price} years")

    # Applied PPA price (row 48)
    applied_price = curves.cells(48, 63).value  # First ops month
    print(f"  Applied PPA price (first ops): {applied_price} GBP/MWh")

    # Read PPA revenue (row 13) for a range of ops months to see PPA tenor effect
    print("\n=== PPA REVENUE (FS row 13) by year ===")
    for yr in range(15):
        start_col = 63 + yr * 12
        vals = []
        for c in range(start_col, min(start_col + 12, 600)):
            vals.append(fs.cells(13, c).value or 0)
        annual = sum(vals)
        if annual == 0 and yr > 0:
            print(f"  Year {yr+1}: {annual:.1f} GBPk (PPA ended)")
            break
        print(f"  Year {yr+1}: {annual:.1f} GBPk")

    # Merchant revenue (row 14) by year
    print("\n=== MERCHANT REVENUE (FS row 14) by year ===")
    for yr in range(15):
        start_col = 63 + yr * 12
        vals = []
        for c in range(start_col, min(start_col + 12, 600)):
            vals.append(fs.cells(14, c).value or 0)
        annual = sum(vals)
        print(f"  Year {yr+1}: {annual:.1f} GBPk")

    # Read merchant price curve (what prices are used for merchant period?)
    # Check Curves and D&T for the Baringa/Aurora merchant curves
    print("\n=== MERCHANT PRICE DATA ===")
    # The "Applied" row for merchant prices
    # Check rows around 29-30
    merchant_indexation = curves.range("E29").value
    print(f"  Merchant price indexation: {merchant_indexation}")

    # Look at Curves rows further down for actual merchant price data
    for row in range(25, 35):
        label = curves.range(f"C{row}").value or curves.range(f"D{row}").value or ""
        if label:
            val_e = curves.range(f"E{row}").value
            # Get first few ops month values
            vals = [curves.cells(row, c).value for c in range(63, 68)]
            print(f"  Curves row {row}: {str(label):<40} E={val_e}  Ops: {vals}")

    # Check SETUP sheet for merchant curves
    try:
        setup = wb.sheets["SETUP"]
        print("\n=== SETUP SHEET - Merchant curve selection ===")
        for row in range(5, 80):
            label = setup.range(f"C{row}").value or setup.range(f"D{row}").value or ""
            if label and any(kw in str(label).lower() for kw in ['merchant', 'price', 'baringa', 'aurora', 'blend', 'curve']):
                val = setup.range(f"E{row}").value
                print(f"  Setup row {row}: {str(label):<50} = {val}")
    except:
        pass

    # Look at the Merchant sheet if it exists
    print("\n=== AVAILABLE SHEETS ===")
    for s in wb.sheets:
        print(f"  {s.name}")

    # Try to find merchant price monthly curve
    # Often in a dedicated "Merchant" or "Power Price" sheet
    for sheet_name in ["Merchant", "Power Price", "Merchant Curves", "Price Curve"]:
        try:
            s = wb.sheets[sheet_name]
            print(f"\n=== {sheet_name} sheet found ===")
            for row in range(5, 30):
                label = s.range(f"C{row}").value or s.range(f"D{row}").value or ""
                if label:
                    val = s.range(f"E{row}").value
                    print(f"  Row {row}: {str(label):<40} = {val}")
        except:
            pass

    # Check Solar&BESS Operation for the generation and revenue formula chain
    op = wb.sheets["Solar&BESS Operation"]
    print("\n=== SOLAR&BESS OPERATION - Revenue formula rows (100-175) ===")
    for row in range(100, 175):
        label_f = op.range(f"F{row}").value or ""
        label_g = op.range(f"G{row}").value or ""
        label_h = op.range(f"H{row}").value or ""
        label = label_f or label_g or label_h
        total = op.range(f"I{row}").value
        if label and str(label).strip():
            first_ops = op.cells(row, 63).value
            print(f"  Row {row}: {str(label):<50} Total={total}  FirstOps={first_ops}")

    # Check what generation numbers are
    print("\n=== SOLAR&BESS OPERATION - Generation rows (30-50) ===")
    for row in range(30, 55):
        label = op.range(f"G{row}").value or op.range(f"H{row}").value or ""
        total = op.range(f"I{row}").value
        if (label and str(label).strip()) or (total and total != 0):
            first_ops = op.cells(row, 63).value
            print(f"  Row {row}: {str(label):<50} Total={total}  FirstOps={first_ops}")

    # Read embedded benefits monthly prices from inputs
    print("\n=== EMBEDDED BENEFITS (Input rows 87-105) ===")
    for row in range(87, 106):
        label = inp.range(f"H{row}").value or inp.range(f"G{row}").value or ""
        val_j = inp.range(f"J{row}").value
        if label or val_j:
            print(f"  Row {row}: {str(label):<40} J={val_j}")

    # REGO details
    print("\n=== REGO (Input rows 79-82) ===")
    for row in range(79, 83):
        label = inp.range(f"H{row}").value or inp.range(f"G{row}").value or ""
        val_j = inp.range(f"J{row}").value
        print(f"  Row {row}: {str(label):<40} J={val_j}")

    wb.close()
finally:
    app.quit()
