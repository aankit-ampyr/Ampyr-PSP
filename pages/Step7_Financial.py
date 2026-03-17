"""
Step 7: Financial Analysis (Project IRR)

Calculates ungeared Project IRR using the FCFF chain from the Excel model.
UI-first approach: input forms for visual validation, engine wired up behind.

Currency: GBP (thousands unless noted)
Monthly periods: up to 420 months (35-year project life)
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime

from src.wizard_state import (
    init_wizard_state, get_wizard_state, get_step_status,
    update_wizard_section,
)
from src.financial_config import (
    INPUT_CELLS, REFERENCE_CASE, ITERATION_A1_PARAMS, ITERATION_A2_PARAMS,
)


# Page config
st.set_page_config(
    page_title="Financial Analysis",
    page_icon="£",
    layout="wide",
)

init_wizard_state()


# =============================================================================
# STEP INDICATOR
# =============================================================================

def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Multi-Year", get_step_status(5)),
        ("6", "Green Energy", get_step_status(6)),
        ("7", "Financial", 'current'),
    ]

    cols = st.columns(7)
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == 'completed':
                st.markdown(f"**Step {num}**: {label}")
            elif status == 'current':
                st.markdown(f"**Step {num}**: {label}")
            elif status == 'pending':
                st.markdown(f"Step {num}: {label}")
            else:
                st.markdown(f"Step {num}: {label}")


# =============================================================================
# HELPERS
# =============================================================================

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Reference case defaults for form fields
REF = REFERENCE_CASE.get("values", {})


def _pct_to_display(val):
    """Convert decimal fraction (0.003) to display % (0.3)."""
    if val is not None and val < 1:
        return val * 100
    return val


def _display_to_pct(val):
    """Convert display % (0.3) to decimal fraction (0.003)."""
    if val is not None:
        return val / 100
    return val


def get_financial_state():
    """Get the financial section of wizard state."""
    state = get_wizard_state()
    return state.get('financial', {})


def save_financial_inputs(updates: dict):
    """Save financial inputs to wizard state."""
    update_wizard_section('financial', updates)


# =============================================================================
# PREREQUISITE CHECK
# =============================================================================

def check_prerequisites():
    """Check that Step 5 multi-year projection data is available."""
    state = get_wizard_state()

    # Check for multi-year monthly data from Step 5
    has_multiyear = 'multiyear_monthly' in st.session_state
    has_sizing = state.get('results', {}).get('simulation_results') is not None

    return has_multiyear, has_sizing


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    render_step_indicator()
    st.divider()

    st.title("Financial Analysis — Ungeared Project IRR")
    st.markdown("""
    Calculate the **Ungeared Project IRR** (return on the project before debt/leverage effects)
    using the FCFF (Free Cash Flow to Firm) chain. Parameters mirror the Excel model
    (*Off-Grid Solution v8.xlsm*).
    """)

    has_multiyear, has_sizing = check_prerequisites()

    if not has_multiyear:
        st.warning(
            "**Step 5 (Multi-Year Projection) must be completed first.**  \n"
            "The financial model requires monthly operational data (delivery hours, "
            "DG hours, energy flows) from the multi-year projection."
        )
        st.info("You can still review and configure the financial inputs below.")

    # Get current financial state
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
                    fin.get('generation_selection', REF.get('generation_selection', 'P90'))
                ),
                help="Yield scenario selection",
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
                                    _pct_to_display(REF.get('degradation_pct', 0.003)))),
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

        # Default seasonality from reference case or equal distribution
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
                value=int(fin.get('bess_operating_life', 15)),
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
                                    _pct_to_display(REF.get('bess_merchant_discount', 0.05)))),
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
                value=float(fin.get('rego_price', 5.0)),
                step=0.5,
            )
        with rego_col2:
            rego_indexation = st.selectbox(
                "REGO Indexation",
                options=["CPI", "RPI", "Fixed"],
                index=0,
            )
            rego_tenor_years = st.number_input(
                "REGO Tenor (years)",
                min_value=0, max_value=35,
                value=int(fin.get('rego_tenor_years', 15)),
            )

    # --- Capacity Market ---
    with st.expander("Capacity Market"):
        cm_col1, cm_col2 = st.columns(2)
        with cm_col1:
            st.subheader("T-1 Contract")
            cm_t1_value = st.number_input(
                "T-1 Value (GBPk/MW/Yr)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t1_value', REF.get('cm_t1_value', 20))),
                step=1.0,
            )
            cm_t1_derating = st.number_input(
                "T-1 De-rating Factor (%)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t1_derating',
                                    _pct_to_display(REF.get('cm_t1_derating', 0.2715)))),
                step=0.1, format="%.2f",
            )
            cm_t1_tenor = st.number_input(
                "T-1 Tenor (years)",
                min_value=0, max_value=20,
                value=int(fin.get('cm_t1_tenor', 1)),
            )
        with cm_col2:
            st.subheader("T-4 Contract")
            cm_t4_value = st.number_input(
                "T-4 Value (GBPk/MW/Yr)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t4_value', 0.0)),
                step=1.0,
            )
            cm_t4_derating = st.number_input(
                "T-4 De-rating Factor (%)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('cm_t4_derating', 0.0)),
                step=0.1, format="%.2f",
            )
            cm_t4_tenor = st.number_input(
                "T-4 Tenor (years)",
                min_value=0, max_value=20,
                value=int(fin.get('cm_t4_tenor', 0)),
            )

    # --- Embedded Benefits ---
    with st.expander("Embedded Benefits (11kV)"):
        emb_col1, emb_col2 = st.columns(2)
        with emb_col1:
            emb_benefits_switch = st.selectbox(
                "Embedded Benefits Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('emb_benefits_switch', 0) else 1,
            )
            emb_benefits_tenor = st.number_input(
                "Embedded Benefits Tenor (years)",
                min_value=0, max_value=35,
                value=int(fin.get('emb_benefits_tenor', 15)),
            )
        with emb_col2:
            emb_benefits_index = st.selectbox(
                "Embedded Benefits Indexation",
                options=["CPI", "RPI", "Fixed"],
                index=0,
            )

    # --- BESS Floor ---
    with st.expander("BESS Floor Price"):
        bf_col1, bf_col2 = st.columns(2)
        with bf_col1:
            bess_floor_switch = st.selectbox(
                "BESS Floor Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('bess_floor_switch', 1) else 1,
            )
            bess_floor_price = st.number_input(
                "Floor Price (GBP/MW/yr)",
                min_value=0.0, max_value=200.0,
                value=float(fin.get('bess_floor_price',
                                    REF.get('bess_floor_price', 40))),
                step=1.0,
            )
        with bf_col2:
            bess_floor_rev_share = st.number_input(
                "Floor Underwriter Revenue Share (%)",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_floor_rev_share', 10.0)),
                step=0.5,
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
                help="Engineering, Procurement, Construction",
            )
            capex_grid = st.number_input(
                "Grid Costs",
                min_value=0.0, max_value=500.0,
                value=float(fin.get('capex_grid', 30.0)),
                step=1.0,
            )
            capex_development = st.number_input(
                "Development Costs",
                min_value=0.0, max_value=200.0,
                value=float(fin.get('capex_development', 15.0)),
                step=1.0,
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
                value=float(fin.get('capex_dd', 5.0)),
                step=1.0,
            )
            capex_discharge = st.number_input(
                "Discharge of Conditions",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_discharge', 0.0)),
                step=1.0,
            )
            capex_sdlt = st.number_input(
                "Stamp Duty Land Tax",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_sdlt', 0.0)),
                step=1.0,
            )

        with cx_col2:
            capex_land_legal = st.number_input(
                "Land-Related Legal",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_land_legal', 2.0)),
                step=1.0,
            )
            capex_other_finance = st.number_input(
                "Other (Financing etc.)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_other_finance', 0.0)),
                step=1.0,
            )
            capex_other_legal = st.number_input(
                "Other Legal (PPA, EPC etc.)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_other_legal', 2.0)),
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
                value=float(fin.get('capex_ampyr_tech', 0.0)),
                step=1.0,
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
                min_value=0.0, max_value=500.0,
                value=float(fin.get('capex_bess', 80.0)),
                step=5.0,
                help="BESS capital cost in GBP/kWp of solar capacity",
            )
            capex_landowner_fees = st.number_input(
                "Landowner Fees / Premiums",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_landowner_fees', 0.0)),
                step=1.0,
            )
            capex_insurance = st.number_input(
                "Insurance (CAPEX)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_insurance', 3.0)),
                step=1.0,
            )
            capex_land_lease_constr = st.number_input(
                "Land Lease (Construction)",
                min_value=0.0, max_value=100.0,
                value=float(fin.get('capex_land_lease_constr', 0.0)),
                step=1.0,
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
                value=float(fin.get('capex_misc', 0.0)),
                step=1.0,
            )

        # Contingency
        capex_contingency_pct = st.number_input(
            "Contingency (%)",
            min_value=0.0, max_value=20.0,
            value=float(fin.get('capex_contingency_pct',
                                _pct_to_display(REF.get('capex_contingency_pct', 0.01)))),
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
        total_capex_gbp_k = total_capex_per_kwp * solar_capacity_mwp * 1000 / 1000  # GBP/kWp * kWp -> GBP -> GBPk

        st.divider()
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Total CAPEX (GBP/kWp)", f"£{total_capex_per_kwp:,.1f}")
        mcol2.metric("Total CAPEX (GBP millions)", f"£{total_capex_gbp_k / 1000:,.2f}m")
        mcol3.metric("Contingency", f"{capex_contingency_pct:.1f}%")

    # =========================================================================
    # SECTION 6: OPEX
    # =========================================================================
    st.header("6. Operating Expenditure (OPEX)")

    # --- Solar OPEX ---
    with st.expander("Solar OPEX (GBP/kWp/Yr)", expanded=True):
        ox_col1, ox_col2 = st.columns(2)

        with ox_col1:
            opex_pv_om = st.number_input(
                "PV Plant O&M",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('opex_pv_om', REF.get('opex_pv_om', 5.48))),
                step=0.1, format="%.2f",
            )
            opex_grid_conn = st.number_input(
                "Grid Connection Expense",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('opex_grid_conn', 1.5)),
                step=0.1, format="%.2f",
            )
            opex_greenkeeping = st.number_input(
                "Greenkeeping, Metering etc.",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_greenkeeping', 0.5)),
                step=0.1, format="%.2f",
            )
            opex_community_opex = st.number_input(
                "Community Benefit (OPEX)",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_community', 0.0)),
                step=0.1, format="%.2f",
            )
            opex_real_estate_tax = st.number_input(
                "Real Estate Taxes",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_real_estate_tax', 1.0)),
                step=0.1, format="%.2f",
            )
            opex_non_tech_am = st.number_input(
                "Non-Technical Asset Management",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_non_tech_am', 1.0)),
                step=0.1, format="%.2f",
            )

        with ox_col2:
            opex_subsidy_loss = st.number_input(
                "Landowner Subsidy Loss",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_subsidy_loss', 0.0)),
                step=0.1, format="%.2f",
            )
            opex_insurance_opex = st.number_input(
                "Insurance on Plant & Machinery",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_insurance',
                                    REF.get('opex_insurance', 2.02))),
                step=0.1, format="%.2f",
            )
            opex_fixed_lease = st.number_input(
                "Fixed Lease OPEX",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_fixed_lease', 0.0)),
                step=0.1, format="%.2f",
            )
            opex_corrective_maint = st.number_input(
                "Corrective Maintenance",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_corrective_maint',
                                    REF.get('opex_corrective_maint', 3.2))),
                step=0.1, format="%.2f",
            )
            opex_tech_am = st.number_input(
                "Technical Asset Management",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_tech_am', 1.5)),
                step=0.1, format="%.2f",
            )

        # Variable OPEX
        st.subheader("Variable OPEX (GBP/MWh)")
        vox_col1, vox_col2 = st.columns(2)
        with vox_col1:
            opex_social_cost = st.number_input(
                "Social/Local Participation",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_social_cost', 0.0)),
                step=0.1, format="%.2f",
            )
        with vox_col2:
            opex_balancing_cfd = st.number_input(
                "Balancing Services for CfD",
                min_value=0.0, max_value=20.0,
                value=float(fin.get('opex_balancing_cfd', 0.0)),
                step=0.1, format="%.2f",
            )

        # Total solar OPEX
        total_solar_opex = (opex_pv_om + opex_grid_conn + opex_greenkeeping +
                            opex_community_opex + opex_real_estate_tax + opex_non_tech_am +
                            opex_subsidy_loss + opex_insurance_opex + opex_fixed_lease +
                            opex_corrective_maint + opex_tech_am)
        st.metric("Total Solar OPEX (GBP/kWp/Yr)", f"£{total_solar_opex:,.2f}")

    # --- BESS OPEX ---
    with st.expander("BESS OPEX (GBPk/MW/Yr)"):
        box_col1, box_col2 = st.columns(2)
        with box_col1:
            bess_opex_om = st.number_input(
                "BESS O&M Expense",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_om', REF.get('bess_opex_om', 7.06))),
                step=0.1, format="%.2f",
            )
            bess_opex_import = st.number_input(
                "BESS Import Charges",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_import', 0.0)),
                step=0.1, format="%.2f",
            )
        with box_col2:
            bess_opex_rates = st.number_input(
                "BESS Business Rates",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_rates', 0.0)),
                step=0.1, format="%.2f",
            )
            bess_opex_lease = st.number_input(
                "BESS Lease",
                min_value=0.0, max_value=50.0,
                value=float(fin.get('bess_opex_lease', 0.0)),
                step=0.1, format="%.2f",
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
                index=0 if fin.get('fixed_lease_switch', 0) else 1,
                key="fixed_lease_sw",
            )
            fixed_lease_acres = st.number_input(
                "Land Area (acres)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('fixed_lease_acres', 200.0)),
                step=10.0,
            )
            fixed_lease_price = st.number_input(
                "Lease Price (GBP/Acre/Yr)",
                min_value=0.0, max_value=5000.0,
                value=float(fin.get('fixed_lease_price', 800.0)),
                step=50.0,
            )

            st.subheader("Revenue-Dependent Lease")
            rev_dep_lease_switch = st.selectbox(
                "Revenue-Dependent Lease Enabled",
                options=["Yes", "No"],
                index=0 if fin.get('rev_dep_lease_switch', 0) else 1,
                key="rev_dep_lease_sw",
            )
            rev_share_yr1_10 = st.number_input(
                "Revenue Share Yrs 1-10 (%)",
                min_value=0.0, max_value=30.0,
                value=float(fin.get('rev_share_yr1_10', 5.0)),
                step=0.5,
            )
            rev_share_yr11_35 = st.number_input(
                "Revenue Share Yrs 11-35 (%)",
                min_value=0.0, max_value=30.0,
                value=float(fin.get('rev_share_yr11_35', 7.5)),
                step=0.5,
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
    # SECTION 9: WORKING CAPITAL & FINANCIAL
    # =========================================================================
    st.header("9. Working Capital & Discount Rate")

    with st.expander("Working Capital & Financial Parameters", expanded=True):
        wc_col1, wc_col2 = st.columns(2)

        with wc_col1:
            wc_debtors_days = st.number_input(
                "Debtors (days)",
                min_value=0, max_value=180,
                value=int(fin.get('wc_debtors_days', 45)),
                help="Average days to collect receivables",
            )
            wc_creditors_days = st.number_input(
                "Creditors (days)",
                min_value=0, max_value=180,
                value=int(fin.get('wc_creditors_days', 30)),
                help="Average days to pay suppliers",
            )

        with wc_col2:
            project_discount_rate = st.number_input(
                "Project Discount Rate / WACC (%)",
                min_value=0.0, max_value=25.0,
                value=float(fin.get('project_discount_rate', 8.0)),
                step=0.25, format="%.2f",
                help="Discount rate for XNPV calculation",
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

    if st.button("Save Financial Inputs", type="primary", use_container_width=True):
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
        }

        save_financial_inputs(financial_data)
        st.success("Financial inputs saved successfully.")

    # =========================================================================
    # SECTION 10: SCREENING RESULTS (Placeholder)
    # =========================================================================
    st.divider()
    st.header("10. Financial Screening Results")

    if not has_multiyear:
        st.info(
            "Financial screening will be available once Step 5 (Multi-Year Projection) "
            "is completed. The engine uses monthly delivery hours, DG hours, and energy "
            "flows from the multi-year simulation to calculate the FCFF and Project IRR."
        )
    else:
        st.markdown("""
        **Status**: Engine not yet wired up.
        Once the Python financial engine (Phase A) is complete, this section will:
        - Read sized configurations from Step 3/4
        - Apply financial inputs from above
        - Calculate monthly FCFF for each configuration
        - Compute XIRR (ungeared Project IRR)
        - Display results table with IRR, NPV, CAPEX, payback period
        """)

        if st.button("Run Financial Screening", disabled=True):
            pass

    # =========================================================================
    # SECTION 11: EXCEL EXPORT (Placeholder — Windows/COM only)
    # =========================================================================
    st.divider()
    st.header("11. Excel Workbook Export")

    # Check if xlwings/COM is available
    excel_available = False
    try:
        import xlwings  # noqa: F401
        excel_available = True
    except ImportError:
        pass

    if not excel_available:
        st.info(
            "Excel export requires **xlwings** and Microsoft Excel (Windows only). "
            "Install with `pip install xlwings` to enable this feature.  \n"
            "Financial screening (Section 10) works on all platforms."
        )
    else:
        st.markdown("""
        **Status**: Excel Copy Manager (Phase B) not yet implemented.
        Once complete, this section will:
        - Create a temporary copy of the master Excel workbook
        - Write financial inputs to the correct case column
        - Trigger Excel recalculation via COM
        - Read back the calculated IRR and other outputs
        - Provide download button for the populated workbook
        """)

        if st.button("Generate Excel Workbook", disabled=True):
            pass


# =============================================================================
# RUN
# =============================================================================

main()
