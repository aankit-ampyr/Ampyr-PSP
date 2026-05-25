"""
Step 2b: Financial Setup (PIRR Inputs)

Configures all ~80 financial inputs used by the Project IRR engine. Sits
between Step 2 (Dispatch Rules) and Step 3 (Sizing) so users prepare
financial assumptions before running the operational + financial sweeps.

Architecture (A48, 2026-05-21):
- Step 2b is the WRITER of `wizard['financial']` (this page only).
- Step 3a (Financial Sweep) and Step 7 (Financial Deep-Dive) are READERS.
- DEFAULT_WIZARD_STATE['financial'] (src/wizard_state.py) is A43-aligned —
  fresh sessions that skip Step 2b still get audit-correct D13 defaults.
  Step 2b is the editable layer on top.

Replaces sections 1-9 of the pre-A48 Step 7 page (which has been slimmed
to outputs only). The "Save Financial Inputs" button lives here now.

Decisions log: docs/Project_IRR_Integration_Decisions.md A48.
"""

import streamlit as st
from datetime import date

from src.wizard_state import (
    init_wizard_state, get_wizard_state, get_step_status,
    set_current_step, mark_step_completed, can_navigate_to_step,
)
from src.financial_config import REFERENCE_CASE
from utils.financial_inputs import (
    MONTH_NAMES, pct_to_display, get_financial_state, save_financial_inputs,
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Financial Setup — Step 2b",
    page_icon="£",
    layout="wide",
)

init_wizard_state()

# Prerequisite: Step 1 must be completed
if not can_navigate_to_step(2):
    st.warning("Please complete Step 1 (Setup) first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/Step1_Setup.py")
    st.stop()


# =============================================================================
# STEP INDICATOR
# =============================================================================

def render_step_indicator():
    """9-cell indicator including 2b (current) and 3a sub-steps."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("2b", "Financial Setup", "current"),
        ("3", "Sizing", get_step_status(3)),
        ("3a", "Financial Sweep", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Multi-Year", get_step_status(5)),
        ("6", "Green Energy", get_step_status(6)),
        ("7", "Financial", get_step_status(7)),
    ]
    cols = st.columns(len(steps))
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == "completed":
                st.markdown(f"✅ **Step {num}**: {label}")
            elif status == "current":
                st.markdown(f"🔵 **Step {num}**: {label}")
            elif status == "pending":
                st.markdown(f"⚪ Step {num}: {label}")
            else:
                st.markdown(f"🔒 Step {num}: {label}")


# Reference case defaults for form fields
REF = REFERENCE_CASE.get("values", {})


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    render_step_indicator()
    st.divider()

    st.title("£ Financial Setup — PIRR Inputs")
    st.markdown("""
    Configure all financial assumptions used by the **Project IRR** engine
    (revenue streams, CAPEX, OPEX, land, tax, working capital). Save once
    here, then Step 3a and Step 7 read these inputs for their PIRR runs.

    Defaults are anchored to the D13 audit case (Burton Leonard 82 MWp DC /
    £170 PPA / 250 MWh BESS). Edit per project, click **Save Financial
    Inputs** at the bottom, then proceed to **Step 3 (Sizing)**.
    """)

    fin = get_financial_state()

    # =========================================================================
    # SECTION 1: TIMING & PROJECT STRUCTURE
    # =========================================================================
    st.header("1. Timing & Project Structure")

    with st.expander("Project Timeline", expanded=True):
        t_col1, t_col2, t_col3 = st.columns(3)

        with t_col1:
            model_start = st.date_input(
                "Model Start Date",
                value=fin.get('model_start', date(2024, 7, 1)),
                help="Start date of the financial model period",
            )
            dev_start = st.date_input(
                "Development Start Date",
                value=fin.get('dev_start', date(2024, 7, 1)),
                help="Date development activities begin",
            )
            dev_time_months = st.number_input(
                "Development Time (months)",
                min_value=0, max_value=60,
                value=int(fin.get('dev_time_months', 12)),
                help="Duration of development phase",
            )

        with t_col2:
            construction_start = st.date_input(
                "Construction Start Date",
                value=fin.get('construction_start', date(2026, 1, 1)),
                help="Date construction begins",
            )
            construction_months = st.number_input(
                "Construction Time (months)",
                min_value=1, max_value=48,
                value=int(fin.get('construction_months', 18)),
                help="Duration of construction phase",
            )
            cod_date = st.date_input(
                "COD (Commercial Operation Date)",
                value=fin.get('cod_date', date(2027, 7, 1)),
                help="Date the project starts generating revenue",
            )

        with t_col3:
            project_life_years = st.number_input(
                "Project Life (years)",
                min_value=10, max_value=50,
                value=int(fin.get('project_life_years', 35)),
                help="Total operational life of the project",
            )
            st.metric(
                "Total Monthly Periods",
                f"{project_life_years * 12:,}",
                help="Number of monthly periods in the financial model",
            )

    # =========================================================================
    # SECTION 2: SOLAR GENERATION
    # =========================================================================
    st.header("2. Solar Generation")

    with st.expander("Solar Parameters", expanded=True):
        s_col1, s_col2 = st.columns(2)

        with s_col1:
            solar_capacity_mwp = st.number_input(
                "Solar Capacity (MWp)",
                min_value=1.0, max_value=500.0,
                value=float(fin.get('solar_capacity_mwp', REF.get('solar_capacity_mwp', 82))),
                step=1.0,
                help="Installed solar capacity in MWp",
            )
            generation_selection = st.selectbox(
                "Generation Case",
                options=["P50", "P75", "P90"],
                index=["P50", "P75", "P90"].index(
                    fin.get('generation_selection', 'P50')
                ),
                help="Yield scenario selection. D13 audit / Excel "
                "`Solar&BESS Inputs!F66` = P50.",
            )
            yield_p50 = st.number_input(
                "P50 Gross Yield (MWh/MWp/Yr)",
                min_value=500.0, max_value=2000.0,
                value=float(fin.get('yield_p50', REF.get('yield_p50', 967))),
                step=1.0,
            )
            yield_p75 = st.number_input(
                "P75 Gross Yield (MWh/MWp/Yr)",
                min_value=500.0, max_value=2000.0,
                value=float(fin.get('yield_p75', REF.get('yield_p75', 936))),
                step=1.0,
            )
            yield_p90 = st.number_input(
                "P90 Gross Yield (MWh/MWp/Yr)",
                min_value=500.0, max_value=2000.0,
                value=float(fin.get('yield_p90', REF.get('yield_p90', 895))),
                step=1.0,
            )

        with s_col2:
            degradation_pct = st.number_input(
                "Annual Degradation (%)",
                min_value=0.0, max_value=5.0,
                value=float(fin.get('degradation_pct',
                                    pct_to_display(REF.get('degradation_pct', 0.003)))),
                step=0.1, format="%.2f",
                help="Linear degradation from 2nd year onwards",
            )
            outage_selection = st.selectbox(
                "Annual Outage",
                options=["No", "Yes"],
                index=int(fin.get('outage_selection', 0)),
                help="Whether to model annual outage period",
            )
            if outage_selection == "Yes":
                outage_month = st.selectbox(
                    "Outage Month",
                    options=MONTH_NAMES,
                    index=fin.get('outage_month_idx', 0),
                )
                outage_length_days = st.number_input(
                    "Outage Length (days)",
                    min_value=1, max_value=60,
                    value=int(fin.get('outage_length_days', 14)),
                )

    # --- Seasonality profile ---
    with st.expander("Monthly Seasonality Profile"):
        st.markdown("Fractional share of annual generation per month (should sum to 1.0).")

        default_seasonality = [
            fin.get(f'seasonality_{m.lower()}', round(1/12, 4))
            for m in MONTH_NAMES
        ]

        season_cols = st.columns(6)
        seasonality_values = []
        for i, month in enumerate(MONTH_NAMES):
            with season_cols[i % 6]:
                val = st.number_input(
                    month,
                    min_value=0.0, max_value=0.5,
                    value=float(default_seasonality[i]),
                    step=0.001, format="%.4f",
                    key=f"season_{month}",
                )
                seasonality_values.append(val)

        season_sum = sum(seasonality_values)
        if abs(season_sum - 1.0) > 0.01:
            st.warning(f"Seasonality sum = {season_sum:.4f} (should be 1.0)")
        else:
            st.success(f"Seasonality sum = {season_sum:.4f}")

    # =========================================================================
    # SECTION 3: BESS PARAMETERS
    # =========================================================================
    st.header("3. BESS Configuration")

    with st.expander("BESS Parameters", expanded=True):
        b_col1, b_col2, b_col3 = st.columns(3)

        with b_col1:
            bess_switch = st.selectbox(
                "BESS Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('bess_switch', 1) else 1,
            )
            bess_capacity_mw = st.number_input(
                "BESS Capacity (MW)",
                min_value=0.0, max_value=500.0,
                value=float(fin.get('bess_capacity_mw', REF.get('bess_capacity_mw', 62.5))),
                step=0.5,
            )
            bess_duration_hrs = st.number_input(
                "BESS Duration (hours)",
                min_value=0.5, max_value=12.0,
                value=float(fin.get('bess_duration_hrs', REF.get('bess_duration_hrs', 4))),
                step=0.5,
            )

        with b_col2:
            bess_mwh = bess_capacity_mw * bess_duration_hrs
            st.metric("BESS Energy (MWh)", f"{bess_mwh:,.0f}")

            bess_operating_life = st.number_input(
                "BESS Operating Life (years)",
                min_value=5, max_value=30,
                value=int(fin.get('bess_operating_life', 10)),
                help="D13 / Excel `Solar&BESS Inputs!F112` = 10 years",
            )
            bess_degradation_pct = st.number_input(
                "BESS Degradation (%/yr)",
                min_value=0.0, max_value=10.0,
                value=float(fin.get('bess_degradation_pct', 2.5)),
                step=0.1, format="%.1f",
            )

        with b_col3:
            bess_merchant_switch = st.selectbox(
                "BESS Merchant Revenue",
                options=["Yes", "No"],
                index=0 if fin.get('bess_merchant_switch', 1) else 1,
            )
            bess_scenario = st.number_input(
                "Battery Scenario",
                min_value=1, max_value=5,
                value=int(fin.get('bess_scenario', 1)),
                help="BESS battery revenue scenario case",
            )
            bess_merchant_discount = st.number_input(
                "Merchant Curve Discount (%)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_merchant_discount',
                                    pct_to_display(REF.get('bess_merchant_discount', 0.05)))),
                step=0.5, format="%.1f",
                help="Discount/share applied to merchant curve",
            )

    # =========================================================================
    # SECTION 4: REVENUE STREAMS
    # =========================================================================
    st.header("4. Revenue Streams")

    # --- PPA ---
    with st.expander("PPA (Power Purchase Agreement)", expanded=True):
        ppa_col1, ppa_col2 = st.columns(2)
        with ppa_col1:
            ppa_selection = st.number_input(
                "PPA Selection (case #)",
                min_value=0, max_value=5,
                value=int(fin.get('ppa_selection', 1)),
                help="PPA scenario selection (0 = merchant only)",
            )
            ppa_flex_pct = st.number_input(
                "PPA Flex (%)",
                min_value=-50.0, max_value=50.0,
                value=float(fin.get('ppa_flex_pct', 0.0)),
                step=0.5,
            )
        with ppa_col2:
            ppa_indexation = st.selectbox(
                "PPA Indexation",
                options=["CPI", "RPI", "Fixed", "Blend"],
                index=0,
                help="Price indexation method for PPA",
            )

    # --- REGOs ---
    with st.expander("REGOs (Renewable Energy Guarantees of Origin)"):
        rego_col1, rego_col2 = st.columns(2)
        with rego_col1:
            rego_switch = st.selectbox(
                "REGO Revenue Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('rego_switch', 1) else 1,
            )
            rego_price = st.number_input(
                "REGO Price (GBP/MWh)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('rego_price', 2.5)),
                step=0.5,
                help="Excel `Solar&BESS Inputs!F80` = 2.5",
            )
        with rego_col2:
            rego_indexation = st.selectbox(
                "REGO Indexation",
                options=["NIL", "CPI", "RPI", "Fixed"],
                index=0,
                help="Excel `Solar&BESS Inputs!F81` = NIL INDEXATION",
            )
            rego_tenor_years = st.number_input(
                "REGO Tenor (years)",
                min_value=0, max_value=35,
                value=int(fin.get('rego_tenor_years', 35)),
                help="Excel `Solar&BESS Inputs!F82` = 35",
            )

    # --- Capacity Market ---
    with st.expander("Capacity Market"):
        cm_col1, cm_col2 = st.columns(2)
        with cm_col1:
            st.subheader("T-1 Contract")
            cm_t1_value = st.number_input(
                "T-1 Value (GBPk/MW/Yr)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t1_value', 0.0)),
                step=1.0,
                help="D13 / Burton Leonard: 0 (off). Non-Burton typical: 20.",
            )
            cm_t1_derating = st.number_input(
                "T-1 De-rating Factor (%)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t1_derating', 27.15)),
                step=0.1, format="%.2f",
                help="Excel default 0.2715 (27.15%)",
            )
            cm_t1_tenor = st.number_input(
                "T-1 Tenor (years)",
                min_value=0, max_value=20,
                value=int(fin.get('cm_t1_tenor', 3)),
                help="Excel default = 3 years",
            )
        with cm_col2:
            st.subheader("T-4 Contract")
            cm_t4_value = st.number_input(
                "T-4 Value (GBPk/MW/Yr)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t4_value', 0.0)),
                step=1.0,
                help="D13 / Burton Leonard: 0 (off). Non-Burton typical: 60.",
            )
            cm_t4_derating = st.number_input(
                "T-4 De-rating Factor (%)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t4_derating', 20.94)),
                step=0.1, format="%.2f",
                help="Excel default 0.2094 (20.94%)",
            )
            cm_t4_tenor = st.number_input(
                "T-4 Tenor (years)",
                min_value=0, max_value=20,
                value=int(fin.get('cm_t4_tenor', 15)),
                help="Excel default = 15 years",
            )

    # --- Embedded Benefits ---
    with st.expander("Embedded Benefits (11kV)"):
        emb_col1, emb_col2 = st.columns(2)
        with emb_col1:
            emb_benefits_switch = st.selectbox(
                "Embedded Benefits Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('emb_benefits_switch', 1) else 1,
                help="Excel `Solar&BESS Inputs!F87` = 1 (on)",
            )
            emb_benefits_tenor = st.number_input(
                "Embedded Benefits Tenor (years)",
                min_value=0, max_value=35,
                value=int(fin.get('emb_benefits_tenor', 15)),
                help="Excel `Solar&BESS Inputs!F89` = 15",
            )
        with emb_col2:
            emb_benefits_index = st.selectbox(
                "Embedded Benefits Indexation",
                options=["CPI", "RPI", "Fixed"],
                index=0,
                help="Excel `Solar&BESS Inputs!F88` = CPI",
            )

    # --- BESS Floor ---
    with st.expander("BESS Floor Price"):
        bf_col1, bf_col2 = st.columns(2)
        with bf_col1:
            bess_floor_switch = st.selectbox(
                "BESS Floor Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('bess_floor_switch', 0) else 1,
                help="D13 / Burton Leonard: OFF (BESS earns return through "
                "PPA contribution, not separate floor). Non-Burton: ON.",
            )
            bess_floor_price = st.number_input(
                "Floor Price (GBPk/MW/yr)",
                min_value=0.0, max_value=200.0,
                value=float(fin.get('bess_floor_price',
                                    REF.get('bess_floor_price', 40))),
                step=1.0,
            )
        with bf_col2:
            bess_floor_rev_share = st.number_input(
                "Floor Underwriter Revenue Share (%)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_floor_rev_share', 9.0)),
                step=0.5,
                help="Excel default 0.09 (9%)",
            )
            bess_floor_tenor = st.number_input(
                "Floor Tenor (years)",
                min_value=0, max_value=20,
                value=int(fin.get('bess_floor_tenor', 10)),
            )

    # =========================================================================
    # SECTION 5: CAPEX
    # =========================================================================
    st.header("5. Capital Expenditure (CAPEX)")

    with st.expander("CAPEX Line Items (GBP/kWp)", expanded=True):
        st.markdown("All values in **GBP per kWp** of solar capacity unless otherwise noted.")

        cx_col1, cx_col2, cx_col3 = st.columns(3)

        with cx_col1:
            capex_epc = st.number_input(
                "EPC Cost",
                min_value=0.0, max_value=1000.0,
                value=float(fin.get('capex_epc', REF.get('capex_epc', 400))),
                step=10.0,
                help="Engineering, Procurement, Construction. Excel "
                "`Solar&BESS Inputs!F340` = 400 GBP/kWp",
            )
            capex_grid = st.number_input(
                "Grid Costs",
                min_value=0.0, max_value=500.0,
                value=float(fin.get('capex_grid', 57.858)),
                step=1.0,
                help="Excel `Solar&BESS Inputs!F341` = 57.858 GBP/kWp DC",
            )
            capex_development = st.number_input(
                "Development Costs",
                min_value=0.0, max_value=200.0,
                value=float(fin.get('capex_development', 2.949)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F336` = 2.949 GBP/kWp",
            )
            capex_acquisition = st.number_input(
                "Acquisition Fee",
                min_value=0.0, max_value=200.0,
                value=float(fin.get('capex_acquisition', 0.0)),
                step=1.0,
            )
            capex_dd = st.number_input(
                "DD Costs",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_dd', 3.775)),
                step=0.1, format="%.3f",
                help="Due Diligence. Excel `Solar&BESS Inputs!F339` = 3.775",
            )
            capex_discharge = st.number_input(
                "Discharge of Conditions",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_discharge', 0.983)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F338` = 0.983",
            )
            capex_sdlt = st.number_input(
                "Stamp Duty Land Tax",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_sdlt', 0.753)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F343` = 0.753",
            )

        with cx_col2:
            capex_land_legal = st.number_input(
                "Land-Related Legal",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_land_legal', 3.686)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F344` = 3.686",
            )
            capex_other_finance = st.number_input(
                "Other (Financing etc.)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_other_finance', 5.0)),
                step=1.0,
                help="Excel `Solar&BESS Inputs!F345` = 5.0",
            )
            capex_other_legal = st.number_input(
                "Other Legal (PPA, EPC etc.)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_other_legal', 0.0)),
                step=1.0,
            )
            capex_land_purchase = st.number_input(
                "Land Purchase",
                min_value=0.0, max_value=500.0,
                value=float(fin.get('capex_land_purchase', 0.0)),
                step=1.0,
            )
            capex_ampyr_tech = st.number_input(
                "Ampyr Tech",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_ampyr_tech', 3.236)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F347` = 3.236",
            )
            capex_success_fee = st.number_input(
                "Success Fee",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_success_fee', 0.0)),
                step=1.0,
            )
            capex_community = st.number_input(
                "Community Benefit (CAPEX)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_community', 0.0)),
                step=1.0,
            )

        with cx_col3:
            capex_bess = st.number_input(
                "BESS CAPEX",
                min_value=0.0, max_value=2000.0,
                value=float(fin.get('capex_bess', 600.0)),
                step=10.0,
                help="BESS capital cost in GBP per kW of BESS power. "
                "Excel `Solar&BESS Inputs!F349` = 600 GBP/kW BESS. "
                "Multiplied by `bess_capacity_mw` to get total BESS capex.",
            )
            capex_landowner_fees = st.number_input(
                "Landowner Fees / Premiums",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_landowner_fees', 11.597)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F350` = 11.597",
            )
            capex_insurance = st.number_input(
                "Insurance (CAPEX)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_insurance', 6.329)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F351` = 6.329",
            )
            capex_land_lease_constr = st.number_input(
                "Land Lease (Construction)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_land_lease_constr', 2.457)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F352` = 2.457",
            )
            capex_asset_adoption = st.number_input(
                "Asset Adoption Value",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_asset_adoption', 0.0)),
                step=1.0,
            )
            capex_others = st.number_input(
                "Others",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_others', 0.0)),
                step=1.0,
            )
            capex_misc = st.number_input(
                "Miscellaneous",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_misc', 4.916)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F355` = 4.916",
            )

        capex_contingency_pct = st.number_input(
            "Contingency (%)",
            min_value=0.0, max_value=20.0,
            value=float(fin.get('capex_contingency_pct',
                                pct_to_display(REF.get('capex_contingency_pct', 0.01)))),
            step=0.5, format="%.1f",
        )

        # Total CAPEX summary
        capex_items = [
            capex_epc, capex_grid, capex_development, capex_acquisition,
            capex_dd, capex_discharge, capex_sdlt, capex_land_legal,
            capex_other_finance, capex_other_legal, capex_land_purchase,
            capex_ampyr_tech, capex_success_fee, capex_community,
            capex_bess, capex_landowner_fees, capex_insurance,
            capex_land_lease_constr, capex_asset_adoption, capex_others, capex_misc,
        ]
        total_capex_per_kwp = sum(capex_items)
        total_capex_gbp_k = total_capex_per_kwp * solar_capacity_mwp * 1000 / 1000

        st.divider()
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Total CAPEX (GBP/kWp)", f"£{total_capex_per_kwp:,.1f}")
        mcol2.metric("Total CAPEX (GBP millions)", f"£{total_capex_gbp_k / 1000:,.2f}m")
        mcol3.metric("Contingency", f"{capex_contingency_pct:.1f}%")

    # =========================================================================
    # SECTION 6: OPEX
    # =========================================================================
    st.header("6. Operating Expenditure (OPEX)")

    # A50b: surface the active CPI configuration since opex/tax escalation
    # uses it. Editing happens in Step 1 → Commercial → Inflation Curve.
    _cpi_src = fin.get('cpi_curve_source', 'default')
    _cpi_curve_user = fin.get('cpi_curve_by_calendar_year')
    _cpi_steady = fin.get('cpi_steady_state_rate')
    _cpi_steady_display = (
        f"{_cpi_steady * 100:.2f}%" if _cpi_steady is not None else "2.00% (Excel default)"
    )
    if _cpi_src == 'upload' and _cpi_curve_user:
        _cpi_msg = (
            f"📈 **Active inflation**: custom curve ({len(_cpi_curve_user)} years) "
            f"+ {_cpi_steady_display} steady-state. "
            "Edit in **Step 1 → Commercial → Inflation Curve**."
        )
    else:
        _cpi_msg = (
            f"📈 **Active inflation**: Excel locked default + {_cpi_steady_display} "
            "steady-state. CPI-indexed opex lines below escalate at these rates. "
            "Customise in **Step 1 → Commercial → Inflation Curve**."
        )
    st.info(_cpi_msg)

    with st.expander("Solar OPEX (GBP/kWp/Yr)", expanded=True):
        ox_col1, ox_col2 = st.columns(2)

        with ox_col1:
            opex_pv_om = st.number_input(
                "PV Plant O&M",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('opex_pv_om', REF.get('opex_pv_om', 5.48))),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F215` = 5.48",
            )
            opex_grid_conn = st.number_input(
                "Grid Connection Expense",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('opex_grid_conn', 0.003)),
                step=0.001, format="%.3f",
                help="Excel `Solar&BESS Inputs!F216` = 0.003 GBP/kWp/yr "
                "(near-zero — gas-fired baseload doesn't use grid connection)",
            )
            opex_greenkeeping = st.number_input(
                "Greenkeeping, Metering etc.",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_greenkeeping', 1.5)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F217` = 1.5",
            )
            opex_community_opex = st.number_input(
                "Community Benefit (OPEX)",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_community', 0.5)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F218` = 0.5",
            )
            opex_real_estate_tax = st.number_input(
                "Real Estate Taxes",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_real_estate_tax', 1.222)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F219` = 1.222",
            )
            opex_non_tech_am = st.number_input(
                "Non-Technical Asset Management",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_non_tech_am', 1.3)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F220` = 1.3",
            )

        with ox_col2:
            opex_subsidy_loss = st.number_input(
                "Landowner Subsidy Loss",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_subsidy_loss', 0.0)),
                step=0.1, format="%.3f",
            )
            opex_insurance_opex = st.number_input(
                "Insurance on Plant & Machinery",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_insurance',
                                    REF.get('opex_insurance', 2.021))),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F222` = 2.021",
            )
            opex_fixed_lease = st.number_input(
                "Fixed Lease OPEX",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_fixed_lease', 0.0)),
                step=0.1, format="%.3f",
                help="Engine reads Fixed Lease from §7 Land section "
                "(£/acre/yr × acres), not from this field.",
            )
            opex_corrective_maint = st.number_input(
                "Corrective Maintenance",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_corrective_maint',
                                    REF.get('opex_corrective_maint', 3.2))),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F224` = 3.2",
            )
            opex_tech_am = st.number_input(
                "Technical Asset Management",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_tech_am', 0.3)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F225` = 0.3",
            )

        st.subheader("Variable OPEX (GBP/MWh)")
        vox_col1, vox_col2 = st.columns(2)
        with vox_col1:
            opex_social_cost = st.number_input(
                "Social/Local Participation",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_social_cost', 0.0)),
                step=0.1, format="%.3f",
            )
        with vox_col2:
            opex_balancing_cfd = st.number_input(
                "Balancing Services for CfD",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_balancing_cfd', 2.75)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F282` = 2.75 GBP/MWh "
                "(applied to solar generation)",
            )

        total_solar_opex = (opex_pv_om + opex_grid_conn + opex_greenkeeping +
                            opex_community_opex + opex_real_estate_tax + opex_non_tech_am +
                            opex_subsidy_loss + opex_insurance_opex + opex_fixed_lease +
                            opex_corrective_maint + opex_tech_am)
        st.metric("Total Solar OPEX (GBP/kWp/Yr)", f"£{total_solar_opex:,.2f}")

    with st.expander("BESS OPEX (GBPk/MW/Yr)"):
        box_col1, box_col2 = st.columns(2)
        with box_col1:
            bess_opex_om = st.number_input(
                "BESS O&M Expense",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_om',
                                    REF.get('bess_opex_om', 7.063))),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F308` = 7.063",
            )
            bess_opex_import = st.number_input(
                "BESS Import Charges",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_import', 0.0)),
                step=0.1, format="%.3f",
            )
        with box_col2:
            bess_opex_rates = st.number_input(
                "BESS Business Rates",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_rates', 3.276)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F310` = 3.276",
            )
            bess_opex_lease = st.number_input(
                "BESS Lease",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_lease', 1.489)),
                step=0.1, format="%.3f",
                help="Excel `Solar&BESS Inputs!F311` = 1.489",
            )

    # =========================================================================
    # SECTION 7: LAND
    # =========================================================================
    st.header("7. Land")

    with st.expander("Land Lease & Purchase"):
        land_col1, land_col2 = st.columns(2)

        with land_col1:
            st.subheader("Fixed Lease")
            fixed_lease_switch = st.selectbox(
                "Fixed Lease Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('fixed_lease_switch', 1) else 1,
                key="fixed_lease_sw",
                help="D13: ON (Excel `Solar&BESS Inputs!F172` = 1)",
            )
            fixed_lease_acres = st.number_input(
                "Land Area (acres)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('fixed_lease_acres', 205.0)),
                step=5.0,
                help="D13 = 205 acres (Burton Leonard)",
            )
            fixed_lease_price = st.number_input(
                "Lease Price (GBP/Acre/Yr)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('fixed_lease_price', 700.0)),
                step=50.0,
                help="Excel default 700 GBP/acre/yr",
            )

            st.subheader("Revenue-Dependent Lease")
            rev_dep_lease_switch = st.selectbox(
                "Revenue-Dependent Lease Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('rev_dep_lease_switch', 1) else 1,
                key="rev_dep_lease_sw",
                help="D13: ON (Excel `Solar&BESS Inputs!F177` = 1)",
            )
            rev_share_yr1_10 = st.number_input(
                "Revenue Share Yrs 1-10 (%)",
                min_value=0.0, max_value=30.0,
                value=float(fin.get('rev_share_yr1_10', 5.0)),
                step=0.5,
                help="D13: 5% (Excel `Solar&BESS Inputs!F178`)",
            )
            rev_share_yr11_35 = st.number_input(
                "Revenue Share Yrs 11-35 (%)",
                min_value=0.0, max_value=30.0,
                value=float(fin.get('rev_share_yr11_35', 5.0)),
                step=0.5,
                help="D13: 5% (Excel `Solar&BESS Inputs!F179`)",
            )

        with land_col2:
            st.subheader("Land Purchase")
            land_purchase_switch = st.selectbox(
                "Land Purchase Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('land_purchase_switch', 0) else 1,
                key="land_purchase_sw",
            )
            land_purchase_acres = st.number_input(
                "Purchase Area (acres)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('land_purchase_acres', 0.0)),
                step=10.0,
            )
            land_purchase_price = st.number_input(
                "Purchase Price (GBP/Acre)",
                min_value=0.0, max_value=50000.0,
                value=float(fin.get('land_purchase_price', 10000.0)),
                step=500.0,
            )

            st.subheader("Construction Rent")
            construction_rent_sw = st.selectbox(
                "Construction Rent Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('construction_rent_sw', 0) else 1,
                key="construction_rent_sw",
            )
            construction_rent = st.number_input(
                "Construction Rent (GBP/Acre/Yr)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('construction_rent', 500.0)),
                step=50.0,
            )

    # =========================================================================
    # SECTION 8: TAX & DEPRECIATION
    # =========================================================================
    st.header("8. Tax & Depreciation")

    with st.expander("Corporate Tax & Depreciation", expanded=True):
        tax_col1, tax_col2 = st.columns(2)

        with tax_col1:
            st.subheader("Corporate Tax (Two-Tier UK)")
            corp_tax_rate_low = st.number_input(
                "Tax Rate - Up to Threshold (%)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('corp_tax_rate_low', 19.0)),
                step=0.5,
                help="UK small profits rate",
            )
            corp_tax_rate_high = st.number_input(
                "Tax Rate - Exceeding Threshold (%)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('corp_tax_rate_high', 25.0)),
                step=0.5,
                help="UK main rate of corporation tax",
            )
            corp_tax_threshold = st.number_input(
                "Tax Threshold (GBPk)",
                min_value=0.0, max_value=1000.0,
                value=float(fin.get('corp_tax_threshold', 250.0)),
                step=10.0,
                help="Profit threshold for higher tax rate",
            )
            taxation_month = st.number_input(
                "Taxation Month",
                min_value=1, max_value=12,
                value=int(fin.get('taxation_month', 12)),
                help="Month in which tax is paid (1-12)",
            )

        with tax_col2:
            st.subheader("Depreciation")
            st.markdown("""
            Three depreciation accounts in the Excel model:
            - **Account 1**: Main asset pool (straight-line or reducing balance)
            - **Account 2**: Secondary pool
            - **Account 3**: Additional items

            Depreciation method and rates are configured in the Excel model's
            D&T sheet. The Python engine will replicate this logic.
            """)

    # =========================================================================
    # SECTION 8b: ADVANCED — SHL + Depreciation method (Excel methodology)
    # =========================================================================
    st.header("8b. Advanced — Tax Shield Methodology")

    with st.expander(
        "Shareholder Loan + Depreciation Method (Excel defaults)",
        expanded=False,
    ):
        st.markdown(
            "These inputs mirror Excel's tax-shield mechanics "
            "(`Solar&BESS Inputs!F553/F556`, `D&T!r163-r165/r197/r210-r212`). "
            "Defaults are locked to the values used in the master workbook — "
            "change only if you know what you're doing."
        )

        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            st.subheader("Shareholder Loan (SHL)")
            shl_switch_yn = st.selectbox(
                "SHL Enabled",
                options=["Yes", "No"],
                index=0 if fin.get("shl_switch", 1) else 1,
                help="Excel models a Shareholder Loan covering the unfunded "
                "(non-senior-debt) portion of capex. SHL interest is "
                "tax-deductible up to the UK CIR cap.",
            )
            shl_pct_of_unfunded = st.number_input(
                "SHL % of Unfunded Amount",
                min_value=0.0, max_value=100.0,
                value=float(fin.get("shl_pct_of_unfunded", 99.0)),
                step=1.0, format="%.1f",
                help="Excel `Solar&BESS Inputs!F556` (default 99%).",
            )
            shl_rate = st.number_input(
                "SHL Interest Rate (% p.a.)",
                min_value=0.0, max_value=30.0,
                value=float(fin.get("shl_rate", 15.0)),
                step=0.5, format="%.2f",
                help="Excel `Solar&BESS Inputs!F553` (default 15% p.a.).",
            )

        with adv_col2:
            st.subheader("Tax Depreciation")
            depreciation_method = st.selectbox(
                "Method",
                options=["RB", "SLM"],
                index=["RB", "SLM"].index(fin.get("depreciation_method", "RB")),
                help="Excel `D&T!E165` Applied method. Default RB (Reducing "
                "Balance with SLM crossover).",
            )
            depreciation_rate = st.number_input(
                "Annual Depreciation Rate (%)",
                min_value=0.0, max_value=20.0,
                value=float(fin.get("depreciation_rate", 100.0 * 2.0 / 36.0)),
                step=0.5, format="%.3f",
                help="Excel `D&T!E164` RB rate (default 5.556%/yr = 2/36, "
                "double-declining over a 36-year nominal life).",
            )
            st.caption(
                "UK CIR cap (30% × EBITDA, £2m de minimis) is applied "
                "automatically. Senior debt interest is deducted first; "
                "SHL interest fills any remaining headroom."
            )

    # =========================================================================
    # SECTION 9: WORKING CAPITAL & FINANCIAL
    # =========================================================================
    st.header("9. Working Capital & Discount Rate")

    with st.expander("Working Capital & Financial Parameters", expanded=True):
        wc_col1, wc_col2 = st.columns(2)

        with wc_col1:
            wc_debtors_days = st.number_input(
                "Debtors (days)",
                min_value=0, max_value=180,
                value=int(fin.get('wc_debtors_days', 30)),
                help="Excel `Solar&BESS Inputs!F327` = 30 days",
            )
            wc_creditors_days = st.number_input(
                "Creditors (days)",
                min_value=0, max_value=180,
                value=int(fin.get('wc_creditors_days', 30)),
                help="Excel `Solar&BESS Inputs!F328` = 30 days",
            )

        with wc_col2:
            project_discount_rate = st.number_input(
                "Project Discount Rate / WACC (%)",
                min_value=0.0, max_value=25.0,
                value=float(fin.get('project_discount_rate', 6.5)),
                step=0.25, format="%.2f",
                help="Excel `Solar&BESS Inputs!F590` = 6.5%. "
                "Used for XNPV reporting only; does NOT affect IRR.",
            )
            cost_of_capital = st.number_input(
                "Cost of Capital (%)",
                min_value=0.0, max_value=25.0,
                value=float(fin.get('cost_of_capital', 6.0)),
                step=0.25, format="%.2f",
            )

    # =========================================================================
    # SAVE INPUTS
    # =========================================================================
    st.divider()

    if st.button("Save Financial Inputs", type="primary", width='stretch'):
        financial_data = {
            'enabled': True,
            # Timing
            'model_start': model_start,
            'dev_start': dev_start,
            'dev_time_months': dev_time_months,
            'construction_start': construction_start,
            'construction_months': construction_months,
            'cod_date': cod_date,
            'project_life_years': project_life_years,
            # Solar
            'solar_capacity_mwp': solar_capacity_mwp,
            'generation_selection': generation_selection,
            'yield_p50': yield_p50,
            'yield_p75': yield_p75,
            'yield_p90': yield_p90,
            'degradation_pct': degradation_pct,
            'outage_selection': 1 if outage_selection == "Yes" else 0,
            # Seasonality
            **{f'seasonality_{m.lower()}': v for m, v in zip(MONTH_NAMES, seasonality_values)},
            # BESS
            'bess_switch': 1 if bess_switch == "Yes" else 0,
            'bess_capacity_mw': bess_capacity_mw,
            'bess_duration_hrs': bess_duration_hrs,
            'bess_operating_life': bess_operating_life,
            'bess_degradation_pct': bess_degradation_pct,
            'bess_merchant_switch': 1 if bess_merchant_switch == "Yes" else 0,
            'bess_scenario': bess_scenario,
            'bess_merchant_discount': bess_merchant_discount,
            # PPA
            'ppa_selection': ppa_selection,
            'ppa_flex_pct': ppa_flex_pct,
            'ppa_indexation': ppa_indexation,
            # REGOs
            'rego_switch': 1 if rego_switch == "Yes" else 0,
            'rego_price': rego_price,
            'rego_indexation': rego_indexation,
            'rego_tenor_years': rego_tenor_years,
            # Capacity Market
            'cm_t1_value': cm_t1_value,
            'cm_t1_derating': cm_t1_derating,
            'cm_t1_tenor': cm_t1_tenor,
            'cm_t4_value': cm_t4_value,
            'cm_t4_derating': cm_t4_derating,
            'cm_t4_tenor': cm_t4_tenor,
            # Embedded Benefits
            'emb_benefits_switch': 1 if emb_benefits_switch == "Yes" else 0,
            'emb_benefits_tenor': emb_benefits_tenor,
            'emb_benefits_index': emb_benefits_index,
            # BESS Floor
            'bess_floor_switch': 1 if bess_floor_switch == "Yes" else 0,
            'bess_floor_price': bess_floor_price,
            'bess_floor_rev_share': bess_floor_rev_share,
            'bess_floor_tenor': bess_floor_tenor,
            # CAPEX
            'capex_epc': capex_epc,
            'capex_grid': capex_grid,
            'capex_development': capex_development,
            'capex_acquisition': capex_acquisition,
            'capex_dd': capex_dd,
            'capex_discharge': capex_discharge,
            'capex_sdlt': capex_sdlt,
            'capex_land_legal': capex_land_legal,
            'capex_other_finance': capex_other_finance,
            'capex_other_legal': capex_other_legal,
            'capex_land_purchase': capex_land_purchase,
            'capex_ampyr_tech': capex_ampyr_tech,
            'capex_success_fee': capex_success_fee,
            'capex_community': capex_community,
            'capex_bess': capex_bess,
            'capex_landowner_fees': capex_landowner_fees,
            'capex_insurance': capex_insurance,
            'capex_land_lease_constr': capex_land_lease_constr,
            'capex_asset_adoption': capex_asset_adoption,
            'capex_others': capex_others,
            'capex_misc': capex_misc,
            'capex_contingency_pct': capex_contingency_pct,
            # Solar OPEX
            'opex_pv_om': opex_pv_om,
            'opex_grid_conn': opex_grid_conn,
            'opex_greenkeeping': opex_greenkeeping,
            'opex_community': opex_community_opex,
            'opex_real_estate_tax': opex_real_estate_tax,
            'opex_non_tech_am': opex_non_tech_am,
            'opex_subsidy_loss': opex_subsidy_loss,
            'opex_insurance': opex_insurance_opex,
            'opex_fixed_lease': opex_fixed_lease,
            'opex_corrective_maint': opex_corrective_maint,
            'opex_tech_am': opex_tech_am,
            'opex_social_cost': opex_social_cost,
            'opex_balancing_cfd': opex_balancing_cfd,
            # BESS OPEX
            'bess_opex_om': bess_opex_om,
            'bess_opex_import': bess_opex_import,
            'bess_opex_rates': bess_opex_rates,
            'bess_opex_lease': bess_opex_lease,
            # Land
            'fixed_lease_switch': 1 if fixed_lease_switch == "Yes" else 0,
            'fixed_lease_acres': fixed_lease_acres,
            'fixed_lease_price': fixed_lease_price,
            'rev_dep_lease_switch': 1 if rev_dep_lease_switch == "Yes" else 0,
            'rev_share_yr1_10': rev_share_yr1_10,
            'rev_share_yr11_35': rev_share_yr11_35,
            'land_purchase_switch': 1 if land_purchase_switch == "Yes" else 0,
            'land_purchase_acres': land_purchase_acres,
            'land_purchase_price': land_purchase_price,
            'construction_rent_sw': 1 if construction_rent_sw == "Yes" else 0,
            'construction_rent': construction_rent,
            # Tax
            'corp_tax_rate_low': corp_tax_rate_low,
            'corp_tax_rate_high': corp_tax_rate_high,
            'corp_tax_threshold': corp_tax_threshold,
            'taxation_month': taxation_month,
            # Working Capital & Financial
            'wc_debtors_days': wc_debtors_days,
            'wc_creditors_days': wc_creditors_days,
            'project_discount_rate': project_discount_rate,
            'cost_of_capital': cost_of_capital,
            # Advanced — SHL + depreciation method (Excel methodology)
            'shl_switch': 1 if shl_switch_yn == "Yes" else 0,
            'shl_pct_of_unfunded': shl_pct_of_unfunded,
            'shl_rate': shl_rate,
            'depreciation_method': depreciation_method,
            'depreciation_rate': depreciation_rate,
        }

        save_financial_inputs(financial_data)
        mark_step_completed(2)  # Step 2b completes the Step 2 phase
        st.success(
            "Financial inputs saved. Proceed to **Step 3 (Sizing)** to run "
            "the operational sweep, then **Step 3a (Financial Sweep)** for "
            "PIRR ranking across configs."
        )

    st.divider()
    st.caption(
        "Step 7 (Financial) reads these inputs and computes single-config "
        "PIRR + cash flow charts after Step 3 has produced a sizing config. "
        "Step 3a (Financial Sweep) ranks all configs by PIRR using the same "
        "saved inputs."
    )


main()
