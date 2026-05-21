"""
Financial Model Cell Mapping Configuration

Maps Python parameter names to Excel cell addresses in 'Off-Grid Solution v8.xlsm'.
The workbook uses a multi-case layout:
  - Column H: IC assumptions / defaults
  - Columns J-Q: 8 project cases (Burton Top variants, Northwold, etc.)
  - Column F: selected case (ArrayFormula referencing case # in F7)

For COM/xlwings integration, we write to case columns (J+) and read outputs.
For pure Python screening, we use the parameter semantics documented here.

Currency: GBP (thousands unless noted)
Monthly periods: columns J through TS (up to 420 months for 35-year life)
"""

from pathlib import Path

# =============================================================================
# FILE PATHS
# =============================================================================

MASTER_EXCEL_PATH = Path("Financial Model/Off-Grid Solution v8.xlsm")

# =============================================================================
# SHEET NAMES
# =============================================================================

SHEET_INPUTS = "Solar&BESS Inputs"
SHEET_EQUITY = "Equity"
SHEET_FS = "FS"
SHEET_DT = "D&T"
SHEET_CONSTRUCTION = "Construction"
SHEET_OPERATION = "Solar&BESS Operation"
SHEET_BESS = "BESS"
SHEET_BESS_OPEX = "BESS OPEX"
SHEET_INSURANCE = "Insurance"
SHEET_CURVES_DT = "Curves and D&T"
SHEET_TIMING = "Timing"
SHEET_OVERALL = "Overall Inputs"
SHEET_SETUP = "SETUP"

# =============================================================================
# CASE COLUMN MAPPING
# =============================================================================
# Column index for each case (1-based, for openpyxl/xlwings)

CASE_COLUMNS = {
    1: "J",   # e.g. Burton Top-3.8h (Debt)
    2: "K",   # e.g. Burton Top-3.8h (Equity)
    3: "L",   # e.g. Burton Top-2.3h (Debt)
    4: "M",   # e.g. Burton Top-2.3h (Equity)
    5: "N",   # e.g. Burton Top-6h (Debt)
    6: "O",   # e.g. Burton Top-6h (Equity)
    7: "P",   # e.g. Northwold (Debt)
    8: "Q",   # e.g. Northwold (Equity)
}

DEFAULT_CASE_COLUMN = "J"  # Case 1

# First monthly data column and last (for XIRR range)
MONTHLY_COL_START = "J"   # Period 1 (construction or first month)
MONTHLY_COL_END = "TS"    # Up to 420 months (35yr * 12)

# =============================================================================
# INPUT CELL MAP — Solar&BESS Inputs sheet
# =============================================================================
# Format: 'param_name': (sheet, row, description, unit)
# The column depends on which case is being written (J-Q).
# Column H contains IC defaults.

INPUT_CELLS = {
    # --- GENERAL / TIMING ---
    "project_name":         (SHEET_INPUTS, 12, "Project name", "Name"),
    "model_start":          (SHEET_INPUTS, 16, "Model start date", "Date"),
    "dev_start":            (SHEET_INPUTS, 17, "Development start date", "Date"),
    "dev_time_months":      (SHEET_INPUTS, 18, "Development time", "Months"),
    "construction_start":   (SHEET_INPUTS, 19, "Construction start date", "Date"),
    "construction_months":  (SHEET_INPUTS, 20, "Construction time", "Months"),
    "cod_date":             (SHEET_INPUTS, 23, "Operations start (COD)", "Date"),
    "project_life_years":   (SHEET_INPUTS, 24, "Project life", "Years"),
    "operations_end":       (SHEET_INPUTS, 25, "Operations end date", "Date"),

    # --- SOLAR GENERATION ---
    "solar_capacity_mwp":   (SHEET_INPUTS, 31, "Solar capacity", "MWp"),
    "yield_p50":            (SHEET_INPUTS, 34, "P50 gross yield", "MWh/MWp/Yr"),
    "yield_p75":            (SHEET_INPUTS, 35, "P75 gross yield", "MWh/MWp/Yr"),
    "yield_p90":            (SHEET_INPUTS, 36, "P90 gross yield", "MWh/MWp/Yr"),
    "degradation_pct":      (SHEET_INPUTS, 40, "Linear degradation from 2nd year", "%"),
    "outage_selection":     (SHEET_INPUTS, 43, "Annual outage switch", "0/1"),
    "outage_month":         (SHEET_INPUTS, 44, "Outage month", "Month name"),
    "outage_length_days":   (SHEET_INPUTS, 45, "Outage length", "Days"),
    "neg_price_curtailment":(SHEET_INPUTS, 48, "Negative price curtailment switch", "0/1"),

    # --- SEASONALITY (12 monthly values, rows 51-62) ---
    # These are fractional shares of annual generation per month
    "seasonality_jan":      (SHEET_INPUTS, 51, "Seasonality - January", "fraction"),
    "seasonality_feb":      (SHEET_INPUTS, 52, "Seasonality - February", "fraction"),
    "seasonality_mar":      (SHEET_INPUTS, 53, "Seasonality - March", "fraction"),
    "seasonality_apr":      (SHEET_INPUTS, 54, "Seasonality - April", "fraction"),
    "seasonality_may":      (SHEET_INPUTS, 55, "Seasonality - May", "fraction"),
    "seasonality_jun":      (SHEET_INPUTS, 56, "Seasonality - June", "fraction"),
    "seasonality_jul":      (SHEET_INPUTS, 57, "Seasonality - July", "fraction"),
    "seasonality_aug":      (SHEET_INPUTS, 58, "Seasonality - August", "fraction"),
    "seasonality_sep":      (SHEET_INPUTS, 59, "Seasonality - September", "fraction"),
    "seasonality_oct":      (SHEET_INPUTS, 60, "Seasonality - October", "fraction"),
    "seasonality_nov":      (SHEET_INPUTS, 61, "Seasonality - November", "fraction"),
    "seasonality_dec":      (SHEET_INPUTS, 62, "Seasonality - December", "fraction"),

    # --- MERCHANT / GENERATION SELECTION ---
    "generation_selection": (SHEET_INPUTS, 66, "Generation case (P50/P75/P90)", "Case"),
    "merchant_price_sel":   (SHEET_INPUTS, 67, "Merchant price selection", "Case"),
    "merchant_curve":       (SHEET_INPUTS, 68, "Price curve (Baringa/Aurora/Blend)", "Case"),
    "technology":           (SHEET_INPUTS, 69, "Technology type (FT)", "Case"),
    "price_flex_pct":       (SHEET_INPUTS, 70, "Price flex", "%"),

    # --- PPA ---
    "ppa_selection":        (SHEET_INPUTS, 73, "PPA selection", "Case"),
    "ppa_flex_pct":         (SHEET_INPUTS, 74, "PPA flex", "%"),
    "ppa_indexation":       (SHEET_INPUTS, 75, "PPA price indexation", "Index name"),

    # --- REGOs ---
    "rego_switch":          (SHEET_INPUTS, 79, "REGO switch", "0/1"),
    "rego_price":           (SHEET_INPUTS, 80, "REGO price", "GBP/MWh"),
    "rego_indexation":      (SHEET_INPUTS, 81, "REGO price indexation", "Index name"),
    "rego_tenor_years":     (SHEET_INPUTS, 82, "REGO tenor", "Years"),

    # --- EMBEDDED BENEFITS 11kV ---
    "emb_benefits_switch":  (SHEET_INPUTS, 87, "Embedded benefits switch", "0/1"),
    "emb_benefits_index":   (SHEET_INPUTS, 88, "Embedded benefits indexation", "Index name"),
    "emb_benefits_tenor":   (SHEET_INPUTS, 89, "Embedded benefits tenor", "Years"),

    # --- EMBEDDED BENEFITS 11kV MONTHLY (rows 94-105) ---
    # 12 monthly GBP/MWh values for embedded benefits
    "emb_benefit_jan":      (SHEET_INPUTS, 94, "Embedded benefit - January", "GBP/MWh"),
    "emb_benefit_feb":      (SHEET_INPUTS, 95, "Embedded benefit - February", "GBP/MWh"),
    "emb_benefit_mar":      (SHEET_INPUTS, 96, "Embedded benefit - March", "GBP/MWh"),
    "emb_benefit_apr":      (SHEET_INPUTS, 97, "Embedded benefit - April", "GBP/MWh"),
    "emb_benefit_may":      (SHEET_INPUTS, 98, "Embedded benefit - May", "GBP/MWh"),
    "emb_benefit_jun":      (SHEET_INPUTS, 99, "Embedded benefit - June", "GBP/MWh"),
    "emb_benefit_jul":      (SHEET_INPUTS, 100, "Embedded benefit - July", "GBP/MWh"),
    "emb_benefit_aug":      (SHEET_INPUTS, 101, "Embedded benefit - August", "GBP/MWh"),
    "emb_benefit_sep":      (SHEET_INPUTS, 102, "Embedded benefit - September", "GBP/MWh"),
    "emb_benefit_oct":      (SHEET_INPUTS, 103, "Embedded benefit - October", "GBP/MWh"),
    "emb_benefit_nov":      (SHEET_INPUTS, 104, "Embedded benefit - November", "GBP/MWh"),
    "emb_benefit_dec":      (SHEET_INPUTS, 105, "Embedded benefit - December", "GBP/MWh"),

    # --- BESS REVENUE ---
    "bess_switch":          (SHEET_INPUTS, 109, "BESS switch", "0/1"),
    "bess_operating_life":  (SHEET_INPUTS, 112, "BESS operating life", "Years"),
    "bess_capacity_mw":     (SHEET_INPUTS, 116, "BESS capacity", "MW"),
    "bess_duration_hrs":    (SHEET_INPUTS, 117, "BESS duration", "Hours"),
    # Row 118 = MW * hrs = MWh (formula)
    "bess_degradation_pct": (SHEET_INPUTS, 120, "BESS degradation", "%"),
    "bess_initial_state":   (SHEET_INPUTS, 121, "BESS initial state", "%"),
    "bess_merchant_switch": (SHEET_INPUTS, 124, "BESS merchant switch", "0/1"),
    "bess_scenario":        (SHEET_INPUTS, 125, "BESS battery scenario", "Case"),
    "bess_merchant_discount":(SHEET_INPUTS, 126, "Merchant curve discount / share", "%"),
    "bess_offtake_pct":     (SHEET_INPUTS, 127, "BESS offtake %", "%"),
    "bess_indexation":      (SHEET_INPUTS, 128, "BESS merchant indexation", "Index name"),

    # --- BESS FLOOR ---
    "bess_floor_switch":    (SHEET_INPUTS, 131, "BESS floor switch", "0/1"),
    "bess_floor_price":     (SHEET_INPUTS, 132, "BESS floor price", "GBP/MW/yr"),
    "bess_floor_rev_share": (SHEET_INPUTS, 133, "Floor underwriter revenue share", "%"),
    "bess_floor_tenor":     (SHEET_INPUTS, 134, "BESS floor tenor", "Years"),

    # --- CAPACITY MARKET ---
    "cm_t1_value":          (SHEET_INPUTS, 140, "CM T-1 contract value", "GBPk/MW/Yr"),
    "cm_t1_derating":       (SHEET_INPUTS, 141, "CM T-1 de-rating factor", "%"),
    "cm_t1_tenor":          (SHEET_INPUTS, 142, "CM T-1 tenor", "Years"),
    # T-4 (rows 147-153) follows similar pattern
    "cm_t4_value":          (SHEET_INPUTS, 147, "CM T-4 contract value", "GBPk/MW/Yr"),
    "cm_t4_derating":       (SHEET_INPUTS, 148, "CM T-4 de-rating factor", "%"),
    "cm_t4_tenor":          (SHEET_INPUTS, 149, "CM T-4 tenor", "Years"),

    # --- LAND ---
    "land_lease_indexation": (SHEET_INPUTS, 168, "Land lease indexation", "Selection"),
    "fixed_lease_switch":    (SHEET_INPUTS, 172, "Fixed lease switch", "0/1"),
    "fixed_lease_acres":     (SHEET_INPUTS, 173, "Land area for fixed lease", "Acres"),
    "fixed_lease_price":     (SHEET_INPUTS, 174, "Land lease price", "GBP/Acre/Yr"),
    "rev_dep_lease_switch":  (SHEET_INPUTS, 178, "Revenue dependent lease switch", "0/1"),
    "rev_dep_lease_acres":   (SHEET_INPUTS, 179, "Land area for rev dep lease", "Acres"),
    "rev_share_yr1_10":      (SHEET_INPUTS, 180, "Revenue share years 1-10", "%"),
    "rev_share_yr11_35":     (SHEET_INPUTS, 181, "Revenue share years 11-35", "%"),
    "construction_rent_sw":  (SHEET_INPUTS, 184, "Construction rent switch", "0/1"),
    "construction_rent":     (SHEET_INPUTS, 185, "Construction rent", "GBP/Acre/Yr"),
    "land_purchase_switch":  (SHEET_INPUTS, 188, "Land purchase switch", "0/1"),
    "land_purchase_acres":   (SHEET_INPUTS, 189, "Land purchase area", "Acres"),
    "land_purchase_price":   (SHEET_INPUTS, 190, "Land purchase price", "GBP/Acre"),
    "land_sale_switch":      (SHEET_INPUTS, 191, "Sell land after project life", "0/1"),
    "land_sale_price":       (SHEET_INPUTS, 192, "Land sale price", "GBP/Acre"),

    # --- SOLAR OPEX (fixed costs, GBP/kWp/Yr) ---
    "opex_pv_om":           (SHEET_INPUTS, 215, "PV Plant O&M Expense", "GBP/kWp/Yr"),
    "opex_grid_conn":       (SHEET_INPUTS, 216, "Grid Connection Expense", "GBP/kWp/Yr"),
    "opex_greenkeeping":    (SHEET_INPUTS, 217, "Greenkeeping, Metering etc.", "GBP/kWp/Yr"),
    "opex_community":       (SHEET_INPUTS, 218, "Community Benefit", "GBP/kWp/Yr"),
    "opex_real_estate_tax": (SHEET_INPUTS, 219, "Real Estate Taxes", "GBP/kWp/Yr"),
    "opex_non_tech_am":     (SHEET_INPUTS, 220, "Non-Technical Asset Management", "GBP/kWp/Yr"),
    "opex_subsidy_loss":    (SHEET_INPUTS, 221, "Landowner Subsidy Loss", "GBP/kWp/Yr"),
    "opex_insurance":       (SHEET_INPUTS, 222, "Insurance on Plant & Machinery", "GBP/kWp/Yr"),
    "opex_fixed_lease":     (SHEET_INPUTS, 223, "Fixed lease OPEX", "GBP/kWp/Yr"),
    "opex_corrective_maint":(SHEET_INPUTS, 224, "Corrective Maintenance", "GBP/kWp/Yr"),
    "opex_tech_am":         (SHEET_INPUTS, 225, "Technical Asset Management", "GBP/kWp/Yr"),

    # --- SOLAR OPEX variable costs ---
    "opex_social_cost":     (SHEET_INPUTS, 281, "Social/Local Participation Cost", "GBP/MWh"),
    "opex_balancing_cfd":   (SHEET_INPUTS, 282, "Balancing Services for CfD", "GBP/MWh"),

    # --- BESS OPEX (fixed costs, GBPk/MW/Yr) ---
    "bess_opex_om":         (SHEET_INPUTS, 308, "BESS O&M Expense", "GBPk/MW/Yr"),
    "bess_opex_import":     (SHEET_INPUTS, 309, "BESS Import Charges", "GBPk/MW/Yr"),
    "bess_opex_rates":      (SHEET_INPUTS, 310, "BESS Business Rates", "GBPk/MW/Yr"),
    "bess_opex_lease":      (SHEET_INPUTS, 311, "BESS Lease", "GBPk/MW/Yr"),
    # Rows 312-314: LTSA, PCS Warranty, Augmentation — calculated in BESS OPEX sheet

    # --- WORKING CAPITAL ---
    "wc_debtors_days":      (SHEET_INPUTS, 327, "Debtors", "Days"),
    "wc_creditors_days":    (SHEET_INPUTS, 328, "Creditors", "Days"),

    # --- CAPEX (GBP/kWp unless noted) ---
    "capex_acquisition":    (SHEET_INPUTS, 335, "Acquisition Fee", "GBP/kWp"),
    "capex_development":    (SHEET_INPUTS, 336, "Development Costs", "GBP/kWp"),
    "capex_discharge":      (SHEET_INPUTS, 337, "Discharge of Conditions", "GBP/kWp"),
    "capex_dd":             (SHEET_INPUTS, 338, "DD Costs", "GBP/kWp"),
    "capex_epc":            (SHEET_INPUTS, 339, "EPC Cost", "GBP/kWp"),
    "capex_grid":           (SHEET_INPUTS, 340, "Grid Costs", "GBP/kWp"),
    "capex_sdlt":           (SHEET_INPUTS, 341, "Stamp Duty Land Tax", "GBP/kWp"),
    "capex_land_legal":     (SHEET_INPUTS, 342, "Land-Related Legal Costs", "GBP/kWp"),
    "capex_other_finance":  (SHEET_INPUTS, 343, "Other Cost (Financing etc.)", "GBP/kWp"),
    "capex_other_legal":    (SHEET_INPUTS, 344, "Other Legal (PPA, EPC etc.)", "GBP/kWp"),
    "capex_land_purchase":  (SHEET_INPUTS, 345, "Land purchase", "GBP/kWp"),
    "capex_ampyr_tech":     (SHEET_INPUTS, 346, "Ampyr Tech", "GBP/kWp"),
    "capex_success_fee":    (SHEET_INPUTS, 347, "Success Fee", "GBP/kWp"),
    "capex_community":      (SHEET_INPUTS, 348, "Community Benefit", "GBP/kWp"),
    "capex_bess":           (SHEET_INPUTS, 349, "BESS CAPEX", "GBP/kWp"),
    "capex_landowner_fees": (SHEET_INPUTS, 350, "Landowner Fees / Premiums", "GBP/kWp"),
    "capex_insurance":      (SHEET_INPUTS, 351, "Insurance", "GBP/kWp"),
    "capex_land_lease_constr":(SHEET_INPUTS, 352, "Land Lease during Construction", "GBP/kWp"),
    "capex_asset_adoption": (SHEET_INPUTS, 353, "Asset Adoption Value", "GBP/kWp"),
    "capex_others":         (SHEET_INPUTS, 354, "Others", "GBP/kWp"),
    "capex_misc":           (SHEET_INPUTS, 355, "Miscellaneous", "GBP/kWp"),
    "capex_contingency_pct":(SHEET_INPUTS, 363, "Contingency", "%"),
    "capex_phasing_profile":(SHEET_INPUTS, 332, "Phasing profile number", "#"),

    # --- FINANCING (subset needed for ungeared IRR) ---
    "project_discount_rate":(SHEET_INPUTS, 590, "Project discount rate", "%"),
    "cost_of_capital":      (SHEET_INPUTS, 589, "Cost of capital", "%"),
}

# =============================================================================
# OUTPUT CELL MAP — Key results to read from Excel
# =============================================================================
# Format: 'output_name': (sheet, cell_ref, description)
# These are single-cell outputs (not case-dependent monthly arrays)

OUTPUT_CELLS = {
    # Equity sheet — summary outputs
    "project_irr":      (SHEET_EQUITY, "G162", "XIRR of ungeared FCFF (PIRR)"),
    "fcff_irr":         (SHEET_EQUITY, "D175", "XIRR of FCFF with geared tax"),
    "equity_irr":       (SHEET_INPUTS, "E4", "EIRR = Equity!F118"),
    "npm":              (SHEET_INPUTS, "G4", "NPM = Equity!E146"),
    "moic":             (SHEET_INPUTS, "F6", "MOIC = Equity!H138"),

    # Equity sheet — per-case outputs (use with case column)
    "pirr_display":     (SHEET_INPUTS, "E4", "PIRR display = Equity!G162"),
    "fcff_irr_display": (SHEET_INPUTS, "E6", "FCFF IRR display = Equity!D175"),
}

# =============================================================================
# FCFF CHAIN — Row references in Equity sheet
# =============================================================================
# These are the rows that assemble the ungeared FCFF
# Monthly values span columns J:TS, totals in column I

FCFF_ROWS = {
    "revenues":         (SHEET_EQUITY, 150, "= FS!row27 (Total Solar + BESS revenue)"),
    "opex":             (SHEET_EQUITY, 151, "= FS!row59 (Total expenses)"),
    "nwc_adjustment":   (SHEET_EQUITY, 152, "= FS!row61 (Net working capital)"),
    "construction":     (SHEET_EQUITY, 153, "= SUM(FS!rows69:89) (CAPEX)"),
    "mra":              (SHEET_EQUITY, 154, "= FS!row144 (Maintenance reserve)"),
    "tax_ungeared":     (SHEET_EQUITY, 155, "= D&T!row265 (Ungeared tax paid)"),
    "fcff_total":       (SHEET_EQUITY, 156, "= SUM(rows 150:155)"),
    "fcff_for_xirr":    (SHEET_EQUITY, 160, "= row156 (used in XIRR formula)"),
    "xirr_result":      (SHEET_EQUITY, 162, "XIRR(I160:TS160, I5:TS5)"),
}

# =============================================================================
# FS (FINANCIAL STATEMENTS) — Row references
# =============================================================================

FS_ROWS = {
    # Revenue
    "solar_rev_ppa":        (SHEET_FS, 13, "Solar PPA revenue line 1"),
    "solar_rev_merchant":   (SHEET_FS, 14, "Solar merchant revenue line 2"),
    "solar_rev_rego":       (SHEET_FS, 15, "Solar REGO revenue"),
    "solar_rev_emb":        (SHEET_FS, 16, "Solar embedded benefits revenue"),
    "solar_rev_total":      (SHEET_FS, 17, "Total solar revenue"),
    "bess_merchant_1":      (SHEET_FS, 20, "BESS merchant revenue line 1"),
    "bess_merchant_2":      (SHEET_FS, 21, "BESS merchant revenue line 2"),
    "bess_merchant_3":      (SHEET_FS, 22, "BESS merchant revenue line 3"),
    "bess_cm":              (SHEET_FS, 23, "BESS capacity market revenue"),
    "bess_rev_total":       (SHEET_FS, 24, "Total BESS revenue"),
    "total_revenue":        (SHEET_FS, 27, "Total Revenue (Solar + BESS)"),

    # Solar Expenses (rows 30-44, labels from Solar&BESS Operation rows 161-174)
    "solar_expenses_total": (SHEET_FS, 44, "Total Solar Expenses"),

    # BESS Expenses (rows 47-56, labels from BESS rows 125-133)
    "bess_expenses_total":  (SHEET_FS, 56, "Total BESS Expenses"),

    # Totals
    "total_expenses":       (SHEET_FS, 59, "Total Expenses (Solar + BESS)"),
    "nwc_adjustments":      (SHEET_FS, 61, "Net working capital adjustments"),
    "operating_cashflow":   (SHEET_FS, 63, "Operating cashflow"),
    "loc_interest":         (SHEET_FS, 66, "Letter of credit interest"),

    # Construction CAPEX (rows 69-89, from Construction sheet rows 76-96)
    "capex_line_start":     (SHEET_FS, 69, "First CAPEX line item"),
    "capex_line_end":       (SHEET_FS, 89, "Last CAPEX line item"),
    "capex_dsra":           (SHEET_FS, 90, "DSRA"),
    "capex_idc":            (SHEET_FS, 91, "Interest during construction"),
    "capex_financing_fees": (SHEET_FS, 92, "Financing fees"),
    "capex_total":          (SHEET_FS, 93, "Total construction costs"),
}

# =============================================================================
# D&T (DEPRECIATION & TAX) — Key row references
# =============================================================================

DT_ROWS = {
    # Tax depreciation (3 accounts, each with BOP/additions/depreciation/EOP)
    "tax_depr_account1":    (SHEET_DT, 111, "Tax depreciation account 1"),
    "tax_depr_account2":    (SHEET_DT, 130, "Tax depreciation account 2"),
    "tax_depr_account3":    (SHEET_DT, 149, "Tax depreciation account 3"),

    # Ungeared corporate tax (rows 242-265)
    "ungeared_ebitda":      (SHEET_DT, 244, "EBITDA for ungeared tax"),
    "ungeared_tax_depr":    (SHEET_DT, 245, "Less: tax depreciation"),
    "ungeared_taxable":     (SHEET_DT, 246, "Taxable income"),
    "ungeared_taxable_ann": (SHEET_DT, 247, "Taxable income (annual)"),
    "ungeared_loss_bop":    (SHEET_DT, 250, "Tax loss account BOP"),
    "ungeared_loss_gen":    (SHEET_DT, 251, "Tax loss generated"),
    "ungeared_loss_used":   (SHEET_DT, 252, "Tax loss utilised"),
    "ungeared_loss_eop":    (SHEET_DT, 253, "Tax loss account EOP"),
    "ungeared_net_taxable": (SHEET_DT, 256, "Net taxable income (+ve only)"),
    "ungeared_tax_payable": (SHEET_DT, 260, "Tax payable"),
    "ungeared_tax_paid":    (SHEET_DT, 265, "Tax paid (CFW) — feeds Equity row 155"),
}

# =============================================================================
# TAX CONFIGURATION — Curves and D&T sheet
# =============================================================================

TAX_CONFIG = {
    "corp_tax_rate_low":    (SHEET_CURVES_DT, "E105", "Corporate tax rate up to threshold"),
    "corp_tax_rate_high":   (SHEET_CURVES_DT, "E106", "Corporate rate exceeding threshold"),
    "corp_tax_threshold":   (SHEET_CURVES_DT, "E107", "Corporate rate threshold (GBPk)"),
    "taxation_month":       (SHEET_CURVES_DT, "E108", "Taxation month (1-12)"),
}

# =============================================================================
# CONSTRUCTION SHEET — Key rows
# =============================================================================

CONSTRUCTION_ROWS = {
    "capex_with_contingency_start": (SHEET_CONSTRUCTION, 76, "First CAPEX line (incl contingency)"),
    "capex_with_contingency_end":   (SHEET_CONSTRUCTION, 96, "Last CAPEX line"),
    "capex_total":                  (SHEET_CONSTRUCTION, 97, "Total CAPEX"),
    "land_sale":                    (SHEET_CONSTRUCTION, 104, "Sale of land at end"),
    "uses_capex":                   (SHEET_CONSTRUCTION, 108, "Uses: CAPEX incl contingency"),
    "uses_min_cash":                (SHEET_CONSTRUCTION, 109, "Uses: Min cash balance funding"),
    "uses_dsra":                    (SHEET_CONSTRUCTION, 110, "Uses: DSRA funding"),
    "uses_idc":                     (SHEET_CONSTRUCTION, 111, "Uses: Interest during construction"),
    "uses_financing_fees":          (SHEET_CONSTRUCTION, 112, "Uses: Financing fees"),
    "sources_equity":               (SHEET_CONSTRUCTION, 117, "Sources: Equity"),
    "sources_fixed_debt":           (SHEET_CONSTRUCTION, 118, "Sources: Fixed debt"),
    "sources_sculpted_debt":        (SHEET_CONSTRUCTION, 119, "Sources: Sculpted debt"),
}

# =============================================================================
# REFERENCE CASE VALUES — Burton Top-3.8h (Case 1, Column J)
# =============================================================================
# Known values for validation testing

REFERENCE_CASE = {
    "name": "Burton Top-3.8h",
    "column": "J",
    "values": {
        "solar_capacity_mwp": 82,
        "yield_p50": 967,
        "yield_p75": 936,
        "yield_p90": 895,
        "degradation_pct": 0.003,
        "generation_selection": "P90",
        "cod_date": "2027-07-01",
        "project_life_years": 35,
        "bess_capacity_mw": 62.5,
        "bess_duration_hrs": 4,
        # bess_mwh = 62.5 * 4 = 250
        "bess_merchant_discount": 0.05,
        "bess_floor_price": 40,
        "cm_t1_value": 20,
        "cm_t1_derating": 0.2715,
        "capex_epc": 400,  # GBP/kWp
        "capex_contingency_pct": 0.01,
        "opex_pv_om": 5.48,  # GBP/kWp/Yr
        "opex_corrective_maint": 3.2,
        "opex_insurance": 2.02,
        "bess_opex_om": 7.06,  # GBPk/MW/Yr
    },
}

# =============================================================================
# ITERATION SCOPE TRACKING
# =============================================================================
# Which parameters are needed for each iteration of the Python engine

ITERATION_A1_PARAMS = [
    # Timing
    "model_start", "dev_start", "construction_start", "construction_months",
    "cod_date", "project_life_years",
    # Solar
    "solar_capacity_mwp", "yield_p50", "yield_p75", "yield_p90",
    "generation_selection", "degradation_pct",
    # Seasonality
    "seasonality_jan", "seasonality_feb", "seasonality_mar", "seasonality_apr",
    "seasonality_may", "seasonality_jun", "seasonality_jul", "seasonality_aug",
    "seasonality_sep", "seasonality_oct", "seasonality_nov", "seasonality_dec",
    # BESS
    "bess_switch", "bess_capacity_mw", "bess_duration_hrs",
    # PPA
    "ppa_selection", "ppa_indexation",
    # CAPEX (core items)
    "capex_epc", "capex_grid", "capex_development", "capex_bess",
    "capex_contingency_pct",
    # OPEX (core items)
    "opex_pv_om", "opex_insurance", "opex_corrective_maint",
    "bess_opex_om",
    # Financial
    "project_discount_rate",
]

ITERATION_A2_PARAMS = [
    # REGOs
    "rego_switch", "rego_price", "rego_indexation", "rego_tenor_years",
    # Capacity Market
    "cm_t1_value", "cm_t1_derating", "cm_t1_tenor",
    "cm_t4_value", "cm_t4_derating", "cm_t4_tenor",
    # Embedded benefits
    "emb_benefits_switch", "emb_benefits_index", "emb_benefits_tenor",
    # BESS floor
    "bess_floor_switch", "bess_floor_price", "bess_floor_rev_share",
    "bess_floor_tenor",
    # Merchant
    "merchant_price_sel", "merchant_curve", "bess_merchant_discount",
    "bess_indexation",
]
