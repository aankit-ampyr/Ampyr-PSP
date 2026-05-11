"""
Validate Python financial engine against Excel model (Off-Grid Solution v8.xlsm).

Reads the Burton Top-3.8h case (Case 1, Column J) from Excel via xlwings/COM,
runs the Python engine with matching inputs, and compares key outputs.

Requirements:
  - Windows with Excel installed
  - xlwings >= 0.30
  - The workbook must NOT be open in Excel already

Run:  python tests/validate_vs_excel.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from datetime import date
import numpy as np

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

WORKBOOK_PATH = Path(__file__).parent.parent / "Financial Model" / "Off-Grid Solution v8.xlsm"

# Excel sheet & row references (from financial_config.py)
SHEET_EQUITY = "Equity"
SHEET_FS = "FS"
SHEET_DT = "D&T"
SHEET_INPUTS = "Solar&BESS Inputs"
SHEET_CURVES_DT = "Curves and D&T"

# Monthly data columns: J = col 10 through TS = col 539 (up to 456 periods)
MONTHLY_COL_START = 10   # Column J
CASE_COL = 10            # Column J = Case 1 (Burton Top-3.8h Debt)


# ---------------------------------------------------------------------------
# STEP 1: Read Excel
# ---------------------------------------------------------------------------

def read_excel_outputs():
    """Open workbook, read key monthly arrays and summary outputs."""
    import xlwings as xw

    if not WORKBOOK_PATH.exists():
        print(f"ERROR: Workbook not found at {WORKBOOK_PATH}")
        sys.exit(1)

    print(f"Opening workbook: {WORKBOOK_PATH}")
    app = xw.App(visible=False)
    try:
        wb = app.books.open(str(WORKBOOK_PATH.resolve()), read_only=True)

        # --- Read timeline length from Equity sheet row 5 (dates row) ---
        eq = wb.sheets[SHEET_EQUITY]
        fs = wb.sheets[SHEET_FS]
        dt = wb.sheets[SHEET_DT]
        inp = wb.sheets[SHEET_INPUTS]

        # Find last non-empty column in Equity row 5 (dates)
        # Read a reasonable range and find the extent
        date_row = eq.range("J5").expand('right').value
        if isinstance(date_row, list):
            n_periods = len([d for d in date_row if d is not None])
        else:
            n_periods = 1
        print(f"Timeline periods found: {n_periods}")

        # Read monthly date row (row 5 in Equity)
        dates_raw = eq.range(f"J5").resize(1, n_periods).value
        if not isinstance(dates_raw, list):
            dates_raw = [dates_raw]

        # --- Read key input parameters from Solar&BESS Inputs (Column J) ---
        inputs_data = {}

        def read_input(row, name):
            val = inp.range(f"J{row}").value
            inputs_data[name] = val
            return val

        # Timing
        read_input(16, "model_start")
        read_input(19, "construction_start")
        read_input(20, "construction_months")
        read_input(23, "cod_date")
        read_input(24, "project_life_years")

        # Solar
        read_input(31, "solar_capacity_mwp")
        read_input(34, "yield_p50")
        read_input(35, "yield_p75")
        read_input(36, "yield_p90")
        read_input(40, "degradation_pct")

        # Seasonality (rows 51-62)
        seasonality = []
        for r in range(51, 63):
            val = inp.range(f"J{r}").value
            seasonality.append(val if val else 1/12)
        inputs_data["seasonality"] = seasonality

        # BESS
        read_input(109, "bess_switch")
        read_input(116, "bess_capacity_mw")
        read_input(117, "bess_duration_hrs")
        read_input(112, "bess_operating_life")
        read_input(120, "bess_degradation_pct")

        # BESS revenue
        read_input(131, "bess_floor_switch")
        read_input(132, "bess_floor_price")
        read_input(133, "bess_floor_rev_share")
        read_input(134, "bess_floor_tenor")

        # CM
        read_input(140, "cm_t1_value")
        read_input(141, "cm_t1_derating")
        read_input(142, "cm_t1_tenor")

        # PPA price - read from FS or wherever the effective PPA price is
        # For now use the PPA selection row
        read_input(73, "ppa_selection")

        # CAPEX items
        for row, name in [(335, "capex_acquisition"), (336, "capex_development"),
                          (337, "capex_discharge"), (338, "capex_dd"),
                          (339, "capex_epc"), (340, "capex_grid"),
                          (341, "capex_sdlt"), (342, "capex_land_legal"),
                          (343, "capex_other_finance"), (344, "capex_other_legal"),
                          (345, "capex_land_purchase"), (346, "capex_ampyr_tech"),
                          (347, "capex_success_fee"), (348, "capex_community"),
                          (349, "capex_bess"), (350, "capex_landowner_fees"),
                          (351, "capex_insurance"), (352, "capex_land_lease_constr"),
                          (353, "capex_asset_adoption"), (354, "capex_others"),
                          (355, "capex_misc")]:
            read_input(row, name)
        read_input(363, "capex_contingency_pct")

        # OPEX
        for row, name in [(215, "opex_pv_om"), (216, "opex_grid_conn"),
                          (217, "opex_greenkeeping"), (218, "opex_community"),
                          (219, "opex_real_estate_tax"), (220, "opex_non_tech_am"),
                          (221, "opex_subsidy_loss"), (222, "opex_insurance"),
                          (223, "opex_fixed_lease"), (224, "opex_corrective_maint"),
                          (225, "opex_tech_am")]:
            read_input(row, name)

        # BESS OPEX
        for row, name in [(308, "bess_opex_om"), (309, "bess_opex_import"),
                          (310, "bess_opex_rates"), (311, "bess_opex_lease")]:
            read_input(row, name)

        # Tax config from Curves and D&T
        curves = wb.sheets[SHEET_CURVES_DT]
        inputs_data["corp_tax_rate_low"] = curves.range("E105").value
        inputs_data["corp_tax_rate_high"] = curves.range("E106").value
        inputs_data["corp_tax_threshold"] = curves.range("E107").value
        inputs_data["taxation_month"] = curves.range("E108").value

        # Working capital
        read_input(327, "wc_debtors_days")
        read_input(328, "wc_creditors_days")

        # Discount rate
        read_input(590, "project_discount_rate")

        # --- Read FCFF chain outputs (Equity rows 150-162) ---
        def read_monthly_row(sheet, row):
            """Read a full monthly row from a sheet."""
            vals = sheet.range(f"J{row}").resize(1, n_periods).value
            if not isinstance(vals, list):
                vals = [vals]
            return np.array([v if v is not None else 0.0 for v in vals])

        excel_outputs = {}

        # Equity sheet FCFF chain
        excel_outputs["revenue"] = read_monthly_row(eq, 150)
        excel_outputs["opex"] = read_monthly_row(eq, 151)
        excel_outputs["nwc"] = read_monthly_row(eq, 152)
        excel_outputs["capex"] = read_monthly_row(eq, 153)
        excel_outputs["mra"] = read_monthly_row(eq, 154)
        excel_outputs["tax"] = read_monthly_row(eq, 155)
        excel_outputs["fcff"] = read_monthly_row(eq, 156)

        # XIRR result
        xirr_val = eq.range("G162").value
        excel_outputs["project_irr"] = xirr_val

        # FS sheet details
        excel_outputs["solar_rev_total"] = read_monthly_row(fs, 17)
        excel_outputs["bess_rev_total"] = read_monthly_row(fs, 24)
        excel_outputs["total_revenue"] = read_monthly_row(fs, 27)
        excel_outputs["solar_expenses"] = read_monthly_row(fs, 44)
        excel_outputs["bess_expenses"] = read_monthly_row(fs, 56)
        excel_outputs["total_expenses"] = read_monthly_row(fs, 59)
        excel_outputs["nwc_fs"] = read_monthly_row(fs, 61)
        excel_outputs["capex_total_fs"] = read_monthly_row(fs, 93)

        # D&T tax
        excel_outputs["ungeared_ebitda"] = read_monthly_row(dt, 244)
        excel_outputs["tax_depreciation"] = read_monthly_row(dt, 245)
        excel_outputs["tax_paid"] = read_monthly_row(dt, 265)

        # Totals (Column I = col 9)
        excel_outputs["total_capex_sum"] = eq.range("I153").value
        excel_outputs["total_revenue_sum"] = eq.range("I150").value
        excel_outputs["total_opex_sum"] = eq.range("I151").value

        wb.close()
        return inputs_data, excel_outputs, dates_raw, n_periods

    finally:
        app.quit()


# ---------------------------------------------------------------------------
# STEP 2: Run Python engine with matched inputs
# ---------------------------------------------------------------------------

def run_python_engine(inputs_data):
    """Run the Python financial model with inputs read from Excel."""
    from src.financial_model_v0 import FinancialInputs, run_financial_model

    def to_date(val):
        """Convert Excel datetime to Python date."""
        if val is None:
            return None
        import datetime
        if isinstance(val, datetime.datetime):
            return val.date()
        if isinstance(val, date):
            return val
        return val

    def safe_float(val, default=0.0):
        if val is None:
            return default
        return float(val)

    def safe_int(val, default=0):
        if val is None:
            return default
        return int(val)

    inputs = FinancialInputs(
        model_start=to_date(inputs_data.get("model_start")) or date(2024, 7, 1),
        construction_start=to_date(inputs_data.get("construction_start")) or date(2026, 1, 1),
        construction_months=safe_int(inputs_data.get("construction_months"), 18),
        cod_date=to_date(inputs_data.get("cod_date")) or date(2027, 7, 1),
        project_life_years=safe_int(inputs_data.get("project_life_years"), 35),

        solar_capacity_mwp=safe_float(inputs_data.get("solar_capacity_mwp"), 82.0),
        yield_p50=safe_float(inputs_data.get("yield_p50"), 967.0),
        yield_p75=safe_float(inputs_data.get("yield_p75"), 936.0),
        yield_p90=safe_float(inputs_data.get("yield_p90"), 895.0),
        generation_selection="P90",
        degradation_pct=safe_float(inputs_data.get("degradation_pct"), 0.3) * 100
            if safe_float(inputs_data.get("degradation_pct"), 0.3) < 1
            else safe_float(inputs_data.get("degradation_pct"), 0.3),
        seasonality=inputs_data.get("seasonality", [1/12]*12),

        bess_switch=safe_int(inputs_data.get("bess_switch"), 1),
        bess_capacity_mw=safe_float(inputs_data.get("bess_capacity_mw"), 62.5),
        bess_duration_hrs=safe_float(inputs_data.get("bess_duration_hrs"), 4.0),
        bess_operating_life=safe_int(inputs_data.get("bess_operating_life"), 15),
        bess_degradation_pct=safe_float(inputs_data.get("bess_degradation_pct"), 2.5) * 100
            if safe_float(inputs_data.get("bess_degradation_pct"), 2.5) < 1
            else safe_float(inputs_data.get("bess_degradation_pct"), 2.5),

        bess_floor_switch=safe_int(inputs_data.get("bess_floor_switch"), 1),
        bess_floor_price=safe_float(inputs_data.get("bess_floor_price"), 40.0),
        bess_floor_rev_share=safe_float(inputs_data.get("bess_floor_rev_share"), 10.0),
        bess_floor_tenor=safe_int(inputs_data.get("bess_floor_tenor"), 10),

        cm_t1_value=safe_float(inputs_data.get("cm_t1_value"), 20.0),
        cm_t1_derating=safe_float(inputs_data.get("cm_t1_derating"), 27.15) * 100
            if safe_float(inputs_data.get("cm_t1_derating"), 27.15) < 1
            else safe_float(inputs_data.get("cm_t1_derating"), 27.15),
        cm_t1_tenor=safe_int(inputs_data.get("cm_t1_tenor"), 1),

        capex_epc=safe_float(inputs_data.get("capex_epc"), 400.0),
        capex_grid=safe_float(inputs_data.get("capex_grid"), 30.0),
        capex_development=safe_float(inputs_data.get("capex_development"), 15.0),
        capex_acquisition=safe_float(inputs_data.get("capex_acquisition"), 0.0),
        capex_dd=safe_float(inputs_data.get("capex_dd"), 5.0),
        capex_discharge=safe_float(inputs_data.get("capex_discharge"), 0.0),
        capex_sdlt=safe_float(inputs_data.get("capex_sdlt"), 0.0),
        capex_land_legal=safe_float(inputs_data.get("capex_land_legal"), 2.0),
        capex_other_finance=safe_float(inputs_data.get("capex_other_finance"), 0.0),
        capex_other_legal=safe_float(inputs_data.get("capex_other_legal"), 2.0),
        capex_land_purchase=safe_float(inputs_data.get("capex_land_purchase"), 0.0),
        capex_ampyr_tech=safe_float(inputs_data.get("capex_ampyr_tech"), 0.0),
        capex_success_fee=safe_float(inputs_data.get("capex_success_fee"), 0.0),
        capex_community=safe_float(inputs_data.get("capex_community"), 0.0),
        capex_bess=safe_float(inputs_data.get("capex_bess"), 80.0),
        capex_landowner_fees=safe_float(inputs_data.get("capex_landowner_fees"), 0.0),
        capex_insurance=safe_float(inputs_data.get("capex_insurance"), 3.0),
        capex_land_lease_constr=safe_float(inputs_data.get("capex_land_lease_constr"), 0.0),
        capex_asset_adoption=safe_float(inputs_data.get("capex_asset_adoption"), 0.0),
        capex_others=safe_float(inputs_data.get("capex_others"), 0.0),
        capex_misc=safe_float(inputs_data.get("capex_misc"), 0.0),
        capex_contingency_pct=safe_float(inputs_data.get("capex_contingency_pct"), 1.0) * 100
            if safe_float(inputs_data.get("capex_contingency_pct"), 1.0) < 1
            else safe_float(inputs_data.get("capex_contingency_pct"), 1.0),

        opex_pv_om=safe_float(inputs_data.get("opex_pv_om"), 5.48),
        opex_grid_conn=safe_float(inputs_data.get("opex_grid_conn"), 1.5),
        opex_greenkeeping=safe_float(inputs_data.get("opex_greenkeeping"), 0.5),
        opex_community=safe_float(inputs_data.get("opex_community"), 0.0),
        opex_real_estate_tax=safe_float(inputs_data.get("opex_real_estate_tax"), 1.0),
        opex_non_tech_am=safe_float(inputs_data.get("opex_non_tech_am"), 1.0),
        opex_subsidy_loss=safe_float(inputs_data.get("opex_subsidy_loss"), 0.0),
        opex_insurance=safe_float(inputs_data.get("opex_insurance"), 2.02),
        opex_fixed_lease=safe_float(inputs_data.get("opex_fixed_lease"), 0.0),
        opex_corrective_maint=safe_float(inputs_data.get("opex_corrective_maint"), 3.2),
        opex_tech_am=safe_float(inputs_data.get("opex_tech_am"), 1.5),

        bess_opex_om=safe_float(inputs_data.get("bess_opex_om"), 7.06),
        bess_opex_import=safe_float(inputs_data.get("bess_opex_import"), 0.0),
        bess_opex_rates=safe_float(inputs_data.get("bess_opex_rates"), 0.0),
        bess_opex_lease=safe_float(inputs_data.get("bess_opex_lease"), 0.0),

        corp_tax_rate_low=safe_float(inputs_data.get("corp_tax_rate_low"), 19.0) * 100
            if safe_float(inputs_data.get("corp_tax_rate_low"), 0.19) < 1
            else safe_float(inputs_data.get("corp_tax_rate_low"), 19.0),
        corp_tax_rate_high=safe_float(inputs_data.get("corp_tax_rate_high"), 25.0) * 100
            if safe_float(inputs_data.get("corp_tax_rate_high"), 0.25) < 1
            else safe_float(inputs_data.get("corp_tax_rate_high"), 25.0),
        corp_tax_threshold=safe_float(inputs_data.get("corp_tax_threshold"), 250.0),
        taxation_month=safe_int(inputs_data.get("taxation_month"), 12),

        wc_debtors_days=safe_int(inputs_data.get("wc_debtors_days"), 45),
        wc_creditors_days=safe_int(inputs_data.get("wc_creditors_days"), 30),

        project_discount_rate=safe_float(inputs_data.get("project_discount_rate"), 8.0) * 100
            if safe_float(inputs_data.get("project_discount_rate"), 0.08) < 1
            else safe_float(inputs_data.get("project_discount_rate"), 8.0),
    )

    results = run_financial_model(inputs)
    return inputs, results


# ---------------------------------------------------------------------------
# STEP 3: Compare
# ---------------------------------------------------------------------------

def compare_results(py_results, excel_outputs, py_inputs):
    """Compare Python vs Excel results and print detailed report."""
    print("\n" + "=" * 80)
    print("PYTHON vs EXCEL VALIDATION REPORT")
    print(f"Reference case: Burton Top-3.8h (Column J)")
    print("=" * 80)

    all_pass = True
    comparisons = []

    def compare_scalar(name, py_val, xl_val, tol_pct=1.0, tol_abs=None):
        nonlocal all_pass
        if xl_val is None or (isinstance(xl_val, float) and np.isnan(xl_val)):
            status = "SKIP"
            diff = "-"
            pct = "-"
        elif tol_abs is not None:
            diff = abs(py_val - xl_val)
            pct = f"{diff/max(abs(xl_val),1e-10)*100:.4f}%"
            if diff <= tol_abs:
                status = "PASS"
            else:
                status = "FAIL"
                all_pass = False
        else:
            diff = abs(py_val - xl_val)
            pct_val = diff / max(abs(xl_val), 1e-10) * 100
            pct = f"{pct_val:.4f}%"
            if pct_val <= tol_pct:
                status = "PASS"
            else:
                status = "FAIL"
                all_pass = False

        comparisons.append((name, py_val, xl_val, diff, pct, status))
        return status

    def compare_array_total(name, py_arr, xl_arr, tol_pct=1.0):
        """Compare the sum of monthly arrays."""
        py_total = py_arr.sum()
        xl_total = xl_arr.sum() if len(xl_arr) > 0 else 0.0
        return compare_scalar(f"{name} (total)", py_total, xl_total, tol_pct)

    def compare_array_first_ops(name, py_arr, xl_arr, tol_pct=5.0):
        """Compare first operations month value."""
        # Find first non-zero in Excel array
        xl_nz = np.where(xl_arr != 0)[0]
        py_nz = np.where(py_arr != 0)[0]
        if len(xl_nz) > 0 and len(py_nz) > 0:
            xl_val = xl_arr[xl_nz[0]]
            py_val = py_arr[py_nz[0]]
            return compare_scalar(f"{name} (1st ops month)", py_val, xl_val, tol_pct)
        return "SKIP"

    # ---- SUMMARY METRICS ----
    print("\n--- SUMMARY METRICS ---")

    compare_scalar("Project IRR",
                   py_results.project_irr,
                   excel_outputs.get("project_irr"),
                   tol_abs=0.01)  # Within 1 percentage point

    compare_scalar("Total CAPEX (GBPk)",
                   -py_results.total_capex,  # Python stores positive, Excel may store negative
                   excel_outputs.get("total_capex_sum"),
                   tol_pct=1.0)

    compare_scalar("Total Revenue (GBPk)",
                   py_results.total_revenue_lifetime,
                   excel_outputs.get("total_revenue_sum"),
                   tol_pct=5.0)

    compare_scalar("Total OPEX (GBPk)",
                   -py_results.total_opex_lifetime,
                   excel_outputs.get("total_opex_sum"),
                   tol_pct=5.0)

    # ---- MONTHLY ARRAY COMPARISONS ----
    print("\n--- MONTHLY ARRAY TOTALS ---")

    n_py = len(py_results.revenue)
    n_xl_rev = len(excel_outputs.get("revenue", []))
    print(f"  Timeline: Python={n_py} months, Excel={n_xl_rev} months")

    # Match array lengths for comparison
    n = min(n_py, n_xl_rev)

    compare_array_total("Revenue", py_results.revenue[:n], excel_outputs["revenue"][:n], tol_pct=5.0)
    compare_array_total("OPEX", py_results.opex[:n], excel_outputs["opex"][:n], tol_pct=5.0)
    compare_array_total("CAPEX", py_results.capex[:n], excel_outputs["capex"][:n], tol_pct=2.0)
    compare_array_total("Tax", py_results.tax[:n], excel_outputs["tax"][:n], tol_pct=10.0)
    compare_array_total("NWC", py_results.nwc[:n], excel_outputs["nwc"][:n], tol_pct=10.0)
    compare_array_total("FCFF", py_results.fcff[:n], excel_outputs["fcff"][:n], tol_pct=5.0)

    # ---- FIRST OPS MONTH SPOT CHECKS ----
    print("\n--- FIRST OPS MONTH SPOT CHECK ---")
    compare_array_first_ops("Revenue", py_results.revenue[:n], excel_outputs["revenue"][:n], tol_pct=10.0)
    compare_array_first_ops("OPEX", py_results.opex[:n], excel_outputs["opex"][:n], tol_pct=10.0)

    # ---- PRINT REPORT TABLE ----
    print("\n" + "-" * 95)
    print(f"{'Metric':<35} {'Python':>14} {'Excel':>14} {'Diff':>12} {'%Diff':>10} {'Status':>6}")
    print("-" * 95)
    for name, py_val, xl_val, diff, pct, status in comparisons:
        py_str = f"{py_val:>14.2f}" if isinstance(py_val, (int, float)) and not isinstance(py_val, bool) else f"{py_val!s:>14}"
        xl_str = f"{xl_val:>14.2f}" if isinstance(xl_val, (int, float)) and not isinstance(xl_val, bool) and xl_val is not None else f"{xl_val!s:>14}"
        diff_str = f"{diff:>12.2f}" if isinstance(diff, (int, float)) else f"{diff:>12}"
        status_mark = "OK" if status == "PASS" else ("--" if status == "SKIP" else "XX")
        print(f"{name:<35} {py_str} {xl_str} {diff_str} {pct:>10} {status_mark:>6}")
    print("-" * 95)

    # ---- YEARLY REVENUE BREAKDOWN (first 5 ops years) ----
    print("\n--- YEARLY REVENUE COMPARISON (first 5 ops years) ---")
    xl_rev = excel_outputs["revenue"]
    py_rev = py_results.revenue

    # Find first ops month in Excel (first non-zero revenue)
    xl_ops_start = 0
    for idx in range(len(xl_rev)):
        if xl_rev[idx] != 0:
            xl_ops_start = idx
            break

    # Find first ops month in Python
    py_ops_start = 0
    for idx in range(len(py_rev)):
        if py_rev[idx] != 0:
            py_ops_start = idx
            break

    print(f"  Ops starts: Python=month {py_ops_start}, Excel=month {xl_ops_start}")

    for yr in range(5):
        xl_start = xl_ops_start + yr * 12
        xl_end = min(xl_start + 12, len(xl_rev))
        py_start = py_ops_start + yr * 12
        py_end = min(py_start + 12, len(py_rev))

        if xl_end <= xl_start or py_end <= py_start:
            break

        xl_yr_rev = xl_rev[xl_start:xl_end].sum()
        py_yr_rev = py_rev[py_start:py_end].sum()
        diff_pct = abs(py_yr_rev - xl_yr_rev) / max(abs(xl_yr_rev), 1e-10) * 100

        print(f"  Year {yr+1}: Python={py_yr_rev:>10.1f}  Excel={xl_yr_rev:>10.1f}  "
              f"Diff={py_yr_rev-xl_yr_rev:>+8.1f} ({diff_pct:.2f}%)")

    # ---- OVERALL VERDICT ----
    print("\n" + "=" * 80)
    if all_pass:
        print("VERDICT: ALL CHECKS PASSED")
    else:
        failed = [c for c in comparisons if c[5] == "FAIL"]
        print(f"VERDICT: {len(failed)} CHECK(S) FAILED")
        for name, py_val, xl_val, diff, pct, status in failed:
            print(f"  - {name}: Python={py_val:.4f}, Excel={xl_val:.4f}, Diff={pct}")
    print("=" * 80)

    # ---- DUMP RAW INPUTS READ FROM EXCEL ----
    print("\n--- RAW INPUTS READ FROM EXCEL (Column J) ---")
    for k, v in sorted(inputs_data.items()):
        if k != "seasonality":
            print(f"  {k}: {v}")
    print(f"  seasonality: {[f'{s:.4f}' if isinstance(s, float) else s for s in inputs_data.get('seasonality', [])]}")

    return all_pass


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("FINANCIAL MODEL VALIDATION: Python Engine vs Excel (Off-Grid Solution v8)")
    print("=" * 80)

    # Step 1: Read Excel
    print("\nStep 1: Reading Excel workbook...")
    inputs_data, excel_outputs, dates_raw, n_periods = read_excel_outputs()
    print(f"  Read {n_periods} periods, {len(inputs_data)} input params")

    # Step 2: Run Python
    print("\nStep 2: Running Python financial engine...")
    py_inputs, py_results = run_python_engine(inputs_data)
    print(f"  Python IRR: {py_results.project_irr*100:.4f}%")
    print(f"  Python CAPEX: {py_results.total_capex:.0f} GBPk")

    # Step 3: Compare
    print("\nStep 3: Comparing results...")
    all_pass = compare_results(py_results, excel_outputs, inputs_data)

    sys.exit(0 if all_pass else 1)
