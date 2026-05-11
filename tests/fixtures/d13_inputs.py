"""
D13 audit fixture — frozen inputs from `Off-Grid Solution v8.xlsm`.

Decoupled from the workbook so the audit target is reproducible without
loading Excel. Values dumped via `src/excel_reader.py` on 2026-05-09.

Configuration (per spec D13):
  82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS /
  25 MW gas / 25 MW load / Burton Leonard 58 MW AC profile.

Excel cell sources annotated next to each value. When a hardcoded value
needs revisiting, regenerate by running:
    python -m src.excel_reader   (or use read_model_params() directly)
"""

from datetime import date
from pathlib import Path

import numpy as np

from src.dispatch_energy import compute_monthly_energy
from src.project_irr import PirrInputs


# Solar profile path (D20: canonical Burton Leonard files)
D13_SOLAR_PROFILE = Path("Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv")


# Baringa blend nominal merchant prices (Baringa and Aurora!row131).
# Years before 2034 carry zero in the Excel (no curve published) — engine
# falls back to merchant_price_default for those.
D13_MERCHANT_PRICES = {
    2034: 67.85, 2035: 67.85, 2036: 67.85, 2037: 67.85, 2038: 70.41,
    2039: 71.32, 2040: 72.16, 2041: 72.94, 2042: 74.30, 2043: 75.31,
    2044: 75.97, 2045: 76.69, 2046: 77.05, 2047: 77.05, 2048: 77.05,
    2049: 77.05, 2050: 77.05, 2051: 77.24, 2052: 77.24, 2053: 77.24,
    2054: 77.24, 2055: 77.24, 2056: 77.24, 2057: 77.24, 2058: 77.24,
    2059: 77.24, 2060: 77.24, 2061: 77.24, 2062: 77.24,
}


def d13_inputs() -> PirrInputs:
    """Build PirrInputs for the D13 audit case.

    Year-1 monthly aggregates come from running the existing dispatch
    helper on the canonical 58 MW AC profile (D20).
    """
    energy = compute_monthly_energy(
        solar_profile_path=D13_SOLAR_PROFILE,
        load_mw=25.0,
        bess_mwh=250.0,
        bess_mw=62.5,
    )
    monthly = energy["monthly"]

    return PirrInputs(
        # --- Timeline (Solar&BESS Inputs F19/F20/F23/F24) ---
        construction_start=date(2026, 10, 1),
        construction_months=9,
        cod_date=date(2027, 7, 1),
        project_life_years=35,

        # --- Capacity ---
        solar_dc_mwp=82.0,           # F31
        grid_limit_mw=58.4,
        bess_mwh=250.0,              # F116 × F117
        bess_mw=62.5,                # F116
        bess_operating_life_years=10,  # F112
        gas_mw=25.0,                 # Inputs-Gas I14 (effective)
        gas_capacity_mw_gross=28.32, # Inputs-Gas I11 (gross installed, for fixed opex)
        load_mw=25.0,                # Overall Inputs E7

        # --- Solar yield ---
        yield_p50=967.0,             # F34
        yield_p75=936.0,
        yield_p90=895.0,
        generation_selection="P50",  # F66
        seasonality=[
            0.024625, 0.048049, 0.090481, 0.119068, 0.135136, 0.135006,
            0.130144, 0.119599, 0.090190, 0.059662, 0.029606, 0.018434,
        ],
        solar_degradation_pct=0.003,  # F40

        # --- Year-1 monthly aggregates from dispatch ---
        monthly_solar_bess_to_dc=monthly["solar_bess_to_dc"],
        monthly_solar_surplus=monthly["solar_surplus"],
        monthly_gas_mwh=monthly["gas_energy"],

        # --- PPA (Overall Inputs E13/E14) ---
        ppa_tariff_gbp_mwh=170.0,
        ppa_tenor_years=10,
        ppa_indexation="NIL",
        ppa_escalation_rate=0.0,

        # --- Solar merchant ---
        merchant_prices=D13_MERCHANT_PRICES,
        merchant_price_default=67.85,   # Baringa value at curve start

        # --- REGOs (F79-82) ---
        rego_switch=1,
        rego_price=2.5,
        rego_indexation="NIL",
        rego_tenor_years=35,

        # --- 11kV embedded benefits (F94-105, F87-89) ---
        emb_switch=1,
        emb_benefits_monthly=[
            5.376, 6.271, 8.308, 8.191, 9.399, 10.384,
            10.782, 10.045, 7.541, 5.951, 5.370, 5.370,
        ],
        emb_indexation="CPI",
        emb_tenor_years=15,

        # --- CM T-1 / CM T-4 / BESS floor: per Excel current snapshot, all
        # BESS revenue evaluates to zero (BESS sheet rows 93-96 → FS r20-23
        # all zero). Likely conditional on a switch the spec hasn't captured;
        # for D13 audit parity we mirror Excel's zero revenue. ---
        cm_t1_value=0.0,
        cm_t1_derating=0.2715,
        cm_t1_tenor_years=3,
        cm_t1_start=date(2026, 10, 1),
        cm_t1_indexation="CPI",
        cm_t4_value=0.0,
        cm_t4_derating=0.2094,
        cm_t4_tenor_years=15,
        cm_t4_start=date(2029, 10, 1),
        cm_t4_indexation="CPI",
        bess_floor_switch=0,
        bess_floor_price=40.0,
        bess_floor_rev_share=0.09,
        bess_floor_tenor_years=10,
        bess_floor_indexation="NIL",

        # --- BESS merchant (F124) — OFF in PPA mode for D13 ---
        bess_merchant_switch=0,

        # --- Gas PPA (Inputs-Gas I19/I20/I16) ---
        gas_ppa_tariff=170.0,
        gas_ppa_tenor_years=10,
        gas_ppa_escalation=0.0,

        # --- Gas merchant (Overall Inputs E17/E18; gas plant life I7) ---
        gas_merchant_tariff=200.0,
        gas_merchant_hours_per_day=9.0,
        gas_merchant_escalation=0.0,        # Excel: gas merchant flat £200
        gas_operations_years=20,            # Inputs-Gas I7

        # --- Solar OPEX (F215-225, F282) ---
        opex_pv_om=5.48,
        opex_grid_conn=0.003,
        opex_greenkeeping=1.5,
        opex_community=0.5,
        opex_real_estate_tax=1.222,
        opex_non_tech_am=1.3,
        opex_subsidy_loss=0.0,
        opex_insurance=2.021,
        opex_corrective_maint=3.2,    # retained for back-compat; engine no longer uses
        opex_tech_am=0.3,
        opex_solar_fixed_indexation="CPI",
        opex_balancing_cfd=2.75,
        opex_solar_var_indexation="CPI",
        # FS r39 lifetime £525k → level base ≈ £9.83k/yr (CPI Σ=53.4 over 35yr)
        opex_corrective_maint_annual_gbpk=9.83,

        # --- BESS OPEX (F308-311) + step costs from BESS sheet ---
        bess_opex_om=7.063,
        bess_opex_import=0.0,
        bess_opex_rates=3.276,
        bess_opex_lease=1.489,
        bess_opex_indexation="BESS Indexation",
        # FS r51 £3,569k, r52 £395k, r53 £3,125k. BESS Indexation Σ ≈ 10.95 over 10 yr.
        bess_opex_ltsa_annual_gbpk=326.0,
        bess_opex_pcs_warranty_annual_gbpk=36.1,
        bess_opex_augmentation_annual_gbpk=285.5,

        # --- Gas OPEX (Inputs-Gas I32-49, I54) ---
        gas_opex_environmental=10.166,
        gas_opex_om_contract=9.378,
        gas_opex_site_maintenance=1.801,
        gas_opex_other_variable=2.022,
        gas_opex_site_lease=3.900,
        gas_opex_fixed_operating=14.232,
        gas_opex_professional_fees=4.584,
        gas_opex_property_tax=4.0,
        gas_opex_telecom=0.3,
        gas_opex_audit_fees=0.837,
        gas_opex_insurance=3.54,
        gas_opex_legal=0.872,
        gas_opex_inflation=0.020,
        gas_opex_reactive_per_mwh=0.0015,    # Cash Flows-Gas r48 / Inputs-Gas I38
        gas_opex_major_maint_annual=685.0,   # Cash Flows-Gas r44 (£16,650k / Σ inflation factors)
        gas_fuel_price_gbp_mwh=32.51,
        gas_net_efficiency=0.385,
        gas_co2_kg_per_mwh=185.0,
        gas_ukets_cost_gbp_per_kg=0.07,
        gas_fixed_cost_gbp_day=1087.54,
        gas_starts_per_day=4.0,
        gas_start_fuel=0.1,
        gas_fuel_escalation_from_yr4=0.01,

        # --- Land (F172-181) ---
        fixed_lease_switch=1,
        fixed_lease_acres=205.0,
        fixed_lease_price=700.0,
        fixed_lease_indexation="Land Lease RPI",
        rev_dep_lease_switch=1,
        rev_share_yr1_10=0.05,
        rev_share_yr11_35=0.05,

        # --- CAPEX (F335-355, F363) ---
        capex_acquisition=0.0,
        capex_development=2.949,
        capex_discharge=0.983,
        capex_dd=3.775,
        capex_epc=400.0,
        capex_grid=57.858,
        capex_sdlt=0.753,
        capex_land_legal=3.686,
        capex_other_finance=5.0,
        capex_other_legal=0.0,
        capex_land_purchase=0.0,
        capex_ampyr_tech=3.236,
        capex_success_fee=0.0,
        capex_community=0.0,
        capex_landowner_fees=11.597,
        capex_insurance=6.329,
        capex_land_lease_constr=2.457,
        capex_asset_adoption=0.0,
        capex_others=0.0,
        capex_misc=4.916,
        # D5: BESS scales with BESS MW. F349 = 600 GBP/kW_BESS.
        capex_bess_gbp_per_kw_bess=600.0,
        # Inputs-Gas I58
        gas_capex_total_gbpk=21839.4,
        capex_contingency_pct=0.01,
        # IDC / Financing / DSRA — D3 says include. Excel populates these from
        # the debt convergence macro; for the v1 audit they remain 0 here and
        # the engine will under-shoot capex by their amount. To be filled in
        # once the SME-confirmed values are extracted from `Construction!`
        # rows 110-112. See decisions log A16 follow-up.
        capex_idc_gbpk=0.0,
        capex_financing_fees_gbpk=0.0,
        capex_dsra_gbpk=0.0,

        # --- Tax (Curves and D&T E105/E108) ---
        corp_tax_rate=0.25,
        taxation_month=12,

        # --- Working capital (F327/F328) ---
        debtor_days=30,
        creditor_days=30,

        # --- Debt for tax shield (D2 / A15) ---
        gearing=0.80,
        interest_rate=0.04,
        debt_tenor_years=19,
        grace_period_months=36,

        # --- Discount (F590) ---
        discount_rate=0.065,
    )
