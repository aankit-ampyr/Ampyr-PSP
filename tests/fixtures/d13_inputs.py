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
LARGE_SOLAR_PROFILE = Path("Inputs/Burton_Leonard_115MWp_DC_82MW_AC.csv")


# Excel merchant curve — ACTUAL evaluated monthly prices from `Solar&BESS
# Operation` r66, averaged per year.
#
# Background: Op r66 uses `LOOKUP(date, 'Curves and D&T'!J29:TZ29,
# 'Curves and D&T'!J30:TZ30)`. Curves r29-30 has 6 columns per year (multiple
# scenarios). A naive "first price per year" extract from r30 cherry-picks
# high-scenario values and over-states by 30-60%. The correct values come
# from extracting the LOOKUP results directly per month, then averaging.
# Curve runs £62 (2027) → £118 (2066), nominal with ~2% CAGR. CPI-like.
D13_MERCHANT_PRICES = {
    2027: 62.18, 2028: 65.53, 2029: 69.39, 2030: 74.19, 2031: 72.71,
    2032: 69.56, 2033: 69.26, 2034: 70.22, 2035: 73.83, 2036: 77.23,
    2037: 79.91, 2038: 80.91, 2039: 82.58, 2040: 79.10, 2041: 80.43,
    2042: 80.31, 2043: 83.28, 2044: 85.92, 2045: 87.42, 2046: 87.26,
    2047: 89.21, 2048: 89.19, 2049: 92.76, 2050: 92.95, 2051: 96.73,
    2052: 97.27, 2053: 99.56, 2054: 101.15, 2055: 103.96, 2056: 106.05,
    2057: 107.49, 2058: 108.14, 2059: 107.48, 2060: 106.45, 2061: 107.59,
    2062: 109.74, 2063: 111.94, 2064: 114.17, 2065: 116.46, 2066: 118.79,
}


def d13_inputs(
    solar_dc_mwp: float = 82.0,
    grid_limit_mw: float = 58.4,
    ppa_tariff: float = 170.0,
    solar_profile: Path | None = None,
) -> PirrInputs:
    """Build PirrInputs for the SME reference matrix.

    Defaults to D13 (82 MWp / £170 / 58 MW grid profile). Override
    `solar_dc_mwp` / `ppa_tariff` / `solar_profile` to switch to one of the
    other 3 SME matrix rows.

    Year-1 monthly aggregates come from running the existing dispatch helper
    on the canonical Burton Leonard profile selected for the case.
    """
    if solar_profile is None:
        solar_profile = D13_SOLAR_PROFILE if solar_dc_mwp <= 100 else LARGE_SOLAR_PROFILE

    energy = compute_monthly_energy(
        solar_profile_path=solar_profile,
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
        solar_dc_mwp=solar_dc_mwp,   # F31 (case-parameterised)
        grid_limit_mw=grid_limit_mw, # case-parameterised
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
        ppa_tariff_gbp_mwh=ppa_tariff,  # case-parameterised
        ppa_tenor_years=10,
        ppa_indexation="NIL",
        ppa_escalation_rate=0.0,

        # --- Solar merchant ---
        merchant_prices=D13_MERCHANT_PRICES,
        merchant_price_default=0.0,    # Excel uses 0 for pre-curve years; no fallback

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
