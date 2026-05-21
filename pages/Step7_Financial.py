"""
Step 7: Financial Analysis (Project IRR) — Output Page

Single-config deep-dive of the Project IRR for the active sizing config.
Reads `wizard['financial']` (written by Step 2b) and runs the PIRR engine
on the dispatch produced from Step 1's load + solar profile.

Architecture (A48, 2026-05-21):
- Step 7 is a READER of `wizard['financial']`. The writer is Step 2b
  (Financial Setup). Step 3a (Financial Sweep) is the other reader.
- Sections 1-9 of the pre-A48 Step 7 (~1100 lines of input UI) live in
  pages/Step2b_FinancialSetup.py now. Step 7 keeps sections 10 (Results)
  and 11 (Excel Export).

Currency: GBP (thousands unless noted)
Monthly periods: up to 420 months (35-year project life)

Decisions log: docs/Project_IRR_Integration_Decisions.md A48.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.wizard_state import (
    init_wizard_state, get_wizard_state, get_step_status,
)
from src.project_irr import (
    PirrResults,
    run_pirr, pirr_inputs_from_wizard_state,
)
from utils.financial_inputs import get_financial_state


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
    """9-cell indicator including 2b + 3a sub-steps. Step 7 is current."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("2b", "Financial Setup", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("3a", "Financial Sweep", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Multi-Year", get_step_status(5)),
        ("6", "Green Energy", get_step_status(6)),
        ("7", "Financial", "current"),
    ]
    cols = st.columns(len(steps))
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == 'completed':
                st.markdown(f"✅ **Step {num}**: {label}")
            elif status == 'current':
                st.markdown(f"🔵 **Step {num}**: {label}")
            elif status == 'pending':
                st.markdown(f"⚪ Step {num}: {label}")
            else:
                st.markdown(f"🔒 Step {num}: {label}")


# =============================================================================
# PREREQUISITE CHECK
# =============================================================================

def check_prerequisites():
    """Check that Step 5 multi-year projection data is available."""
    has_multiyear = 'multiyear_monthly' in st.session_state
    # Top-level `st.session_state.sizing_results` is the canonical storage per
    # Spec §8 (Step 3 writes; Step 3a/Step 4/Step 7 read).
    has_sizing = (
        'sizing_results' in st.session_state
        and st.session_state.sizing_results is not None
    )
    return has_multiyear, has_sizing


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    render_step_indicator()
    st.divider()

    st.title("Financial Analysis — Ungeared Project IRR")
    st.markdown("""
    Calculate the **Ungeared Project IRR** (return on the project before
    debt/leverage effects) using the FCFF (Free Cash Flow to Firm) chain.
    Parameters mirror the Excel model (*Off-Grid Solution v8.xlsm*).
    """)

    # Step 2b pointer banner — financial inputs now live there.
    fin = get_financial_state()
    if not fin.get('enabled'):
        st.warning(
            "**Financial inputs not yet saved.** Visit **Step 2b (Financial "
            "Setup)** to configure CAPEX / OPEX / Revenue / Tax / etc., "
            "click *Save Financial Inputs*, then come back here."
        )
        if st.button("Go to Step 2b"):
            st.switch_page("pages/Step2b_FinancialSetup.py")
    else:
        st.info(
            "Financial assumptions are configured in **Step 2b (Financial "
            "Setup)** — edit there. This page reads those inputs and "
            "computes PIRR + cash-flow charts for the active sizing config."
        )

    has_multiyear, has_sizing = check_prerequisites()

    if not has_multiyear:
        st.warning(
            "**Step 5 (Multi-Year Projection) must be completed first.**  \n"
            "The financial model requires monthly operational data (delivery "
            "hours, DG hours, energy flows) from the multi-year projection."
        )

    # =========================================================================
    # SECTION 10: FINANCIAL ANALYSIS RESULTS
    # =========================================================================
    st.divider()
    st.header("10. Financial Analysis Results")

    st.markdown("""
    Run the ungeared FCFF model using the inputs configured in Step 2b.
    The engine calculates monthly Revenue, OPEX, CAPEX, Depreciation,
    Tax (two-tier UK with loss carry-forward), and NWC over the project
    life, then computes **XIRR** (Project IRR) and **XNPV**.
    """)

    run_dispatch = st.button(
        "Run Financial Analysis",
        type="primary",
        width='stretch',
    )

    if run_dispatch:
        fin_state = get_financial_state()
        if not fin_state.get('enabled'):
            st.warning("Please save financial inputs in Step 2b first.")
        else:
            with st.spinner("Running dispatch + financial model..."):
                try:
                    from src.data_loader import get_active_solar_profile
                    from src.dispatch_energy import (
                        run_hourly_dispatch,
                        aggregate_to_monthly,
                    )

                    # 1. Load solar profile from Step 1's canonical wizard
                    # state (per decisions log A27 — Step 1 is single source
                    # of profile truth).
                    setup_state = get_wizard_state().get('setup', {})
                    raw_profile = get_active_solar_profile(setup_state)
                    if raw_profile is None:
                        st.error(
                            "No solar profile loaded. Complete Step 1 "
                            "(select a solar profile) before running the "
                            "financial analysis."
                        )
                        st.stop()

                    # Per spec D8: profile is AC + grid-capped, used as-is.
                    # Default `ref_mwp` to declared DC MWp → scaling = 1.0.
                    # See decisions log A25.
                    target_mwp = float(fin_state.get('solar_capacity_mwp', 82.0))
                    ref_mwp = float(
                        fin_state.get('profile_reference_mwp')
                        or target_mwp
                        or raw_profile.max()
                    )
                    if ref_mwp <= 0:
                        ref_mwp = float(raw_profile.max())
                    solar_mw = raw_profile * (target_mwp / ref_mwp)

                    profile_peak = float(raw_profile.max())
                    if target_mwp > 0:
                        ratio = profile_peak / target_mwp
                        if ratio < 0.5 or ratio > 1.1:
                            st.warning(
                                f"Solar profile peak ({profile_peak:.1f} MW) "
                                f"is {ratio*100:.0f}% of declared DC "
                                f"({target_mwp:.0f} MWp). Expected 50–110 %. "
                                "If the profile is per-unit, set "
                                "`profile_reference_mwp` in financial inputs."
                            )

                    # 2. Hourly dispatch — load from Step 1 setup, not hardcoded
                    target_load_mw = float(setup_state.get('load_mw', 25.0))
                    bess_mw = float(fin_state.get('bess_capacity_mw', 62.5))
                    bess_mwh = bess_mw * float(
                        fin_state.get('bess_duration_hrs', 4.0))
                    hourly = run_hourly_dispatch(
                        solar_mw,
                        load_mw=target_load_mw,
                        bess_mwh=bess_mwh,
                        bess_mw=bess_mw,
                        rte=0.87,
                        min_soc=0.05,
                        max_soc=0.95,
                    )
                    monthly = aggregate_to_monthly(hourly, solar_mw)

                    # 3. Financial model — new project_irr engine
                    pi = pirr_inputs_from_wizard_state(
                        fin_state, setup_state, monthly)
                    results = run_pirr(pi)

                    # Per Spec §8: `financial_results` is the Step 3a sweep DataFrame.
                    # Step 7's single-config PirrResults lives at a distinct key
                    # to avoid AttributeError when both pages populate state.
                    st.session_state['step7_pirr_result'] = results
                    st.session_state['dispatch_monthly'] = monthly

                    total_demand = target_load_mw * 8760
                    green_pct = (monthly['solar_bess_to_dc'].sum()
                                 / total_demand * 100)
                    gas_pct = (monthly['gas_energy'].sum()
                               / total_demand * 100)
                    irr_str = (f"{results.project_irr * 100:.2f}%"
                               if not np.isnan(results.project_irr) else "n/a")
                    st.success(
                        f"Dispatch: {green_pct:.1f}% green / {gas_pct:.1f}% "
                        f"gas (load = {target_load_mw:.0f} MW from Step 1). "
                        f"Project IRR: {irr_str}"
                    )
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    # Display results if available
    if 'step7_pirr_result' in st.session_state:
        results: PirrResults = st.session_state['step7_pirr_result']

        # v1 SME-facing disclosure (A45): the engine reports IRR ~0.3-0.5 pp
        # lower than Excel for the audit matrix. Gap is the structural v1
        # carve-out (DSCR sculpting + cash sweep + Equity IRR deferred to v2).
        st.info(
            "ℹ️ **v1 reports Project IRR ~0.3-0.5 pp lower than Excel.** Gap is "
            "the structural v1 carve-out (DSCR sculpting + cash sweep + Equity "
            "IRR deferred to v2). Config ranking + sensitivity preserved; use "
            "Excel for the IC-pack headline IRR."
        )

        # --- Primary metric: Combined Project IRR ---
        st.subheader("Summary")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1:
            irr_pct = results.project_irr * 100 if not np.isnan(results.project_irr) else 0
            st.metric("Project IRR (Combined)", f"{irr_pct:.2f}%",
                      help="Solar+BESS+Gas Combined PIRR — matches Excel "
                      "`Consol Cash Flows!B9`.")
        with m_col2:
            st.metric("Project NPV (GBPm)", f"{results.project_npv / 1000:,.2f}")
        with m_col3:
            st.metric("Total CAPEX (GBPm)", f"{results.total_capex / 1000:,.2f}")
        with m_col4:
            moic_val = results.moic if not np.isnan(results.moic) else 0
            st.metric(
                "MOIC", f"{moic_val:.2f}x" if moic_val > 0 else "N/A",
                help="Multiple on Invested Capital, ungeared FCFF basis: "
                     "sum(positive FCFF) / |sum(negative FCFF)|."
            )
        with m_col5:
            if len(results.fcff) > 0:
                cum = np.cumsum(results.fcff)
                pos_idx = np.where(cum > 0)[0]
                payback_yrs = pos_idx[0] / 12 if len(pos_idx) > 0 else 0
            else:
                payback_yrs = 0
            st.metric("Payback", f"{payback_yrs:.1f} yrs" if payback_yrs > 0 else "N/A")

        # --- Component PIRRs (per Anchal Q1 — Excel reports all 3) ---
        m2_col1, m2_col2, m2_col3 = st.columns(3)
        with m2_col1:
            sb_pct = results.project_irr_solar_bess * 100 \
                if not np.isnan(results.project_irr_solar_bess) else 0
            st.metric("Solar+BESS PIRR", f"{sb_pct:.2f}%",
                      help="S+B standalone — matches Excel `Equity!D175`.")
        with m2_col2:
            gas_pct = results.project_irr_gas * 100 \
                if not np.isnan(results.project_irr_gas) else 0
            st.metric("Gas PIRR", f"{gas_pct:.2f}%",
                      help="Gas standalone — matches Excel `Cash Flows-Gas!D84`.")
        with m2_col3:
            net = results.total_revenue_lifetime - results.total_opex_lifetime
            st.metric("Lifetime EBITDA (GBPm)", f"{net / 1000:,.1f}")

        m3_col1, m3_col2 = st.columns(2)
        with m3_col1:
            st.metric("Lifetime Revenue (GBPm)", f"{results.total_revenue_lifetime / 1000:,.1f}")
        with m3_col2:
            st.metric("Lifetime OPEX (GBPm)", f"{results.total_opex_lifetime / 1000:,.1f}")

        # --- Charts ---
        st.subheader("Monthly Cash Flows")

        if len(results.dates) > 0:
            annual_data = {}
            for i, d in enumerate(results.dates):
                yr = d.year
                if yr not in annual_data:
                    annual_data[yr] = {'revenue': 0, 'opex': 0, 'capex': 0,
                                       'tax': 0, 'fcff': 0}
                annual_data[yr]['revenue'] += results.revenue[i]
                annual_data[yr]['opex'] += results.opex[i]
                annual_data[yr]['capex'] += results.capex[i]
                annual_data[yr]['tax'] += results.tax[i]
                annual_data[yr]['fcff'] += results.fcff[i]

            years = sorted(annual_data.keys())
            rev_annual = [annual_data[y]['revenue'] / 1000 for y in years]
            opex_annual = [annual_data[y]['opex'] / 1000 for y in years]
            capex_annual = [annual_data[y]['capex'] / 1000 for y in years]
            tax_annual = [annual_data[y]['tax'] / 1000 for y in years]
            fcff_annual = [annual_data[y]['fcff'] / 1000 for y in years]

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=("Annual Cash Flow Components (GBPm)",
                                                "Annual FCFF (GBPm)"),
                                vertical_spacing=0.12)

            fig.add_trace(go.Bar(x=years, y=rev_annual, name="Revenue",
                                 marker_color="#2ecc71"), row=1, col=1)
            fig.add_trace(go.Bar(x=years, y=opex_annual, name="OPEX",
                                 marker_color="#e74c3c"), row=1, col=1)
            fig.add_trace(go.Bar(x=years, y=capex_annual, name="CAPEX",
                                 marker_color="#3498db"), row=1, col=1)
            fig.add_trace(go.Bar(x=years, y=tax_annual, name="Tax",
                                 marker_color="#f39c12"), row=1, col=1)

            fcff_colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in fcff_annual]
            fig.add_trace(go.Bar(x=years, y=fcff_annual, name="FCFF",
                                 marker_color=fcff_colors,
                                 showlegend=False), row=2, col=1)

            fig.update_layout(
                height=700,
                barmode='relative',
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1),
            )
            fig.update_yaxes(title_text="GBPm", row=1, col=1)
            fig.update_yaxes(title_text="GBPm", row=2, col=1)

            st.plotly_chart(fig, width='stretch')

        # --- Cumulative FCFF ---
        st.subheader("Cumulative FCFF")

        if len(results.dates) > 0:
            cum_annual = np.cumsum(fcff_annual)

            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=years, y=cum_annual.tolist(),
                mode='lines+markers',
                name='Cumulative FCFF',
                line=dict(color='#2c3e50', width=2),
                fill='tozeroy',
                fillcolor='rgba(46,204,113,0.1)',
            ))
            fig_cum.add_hline(y=0, line_dash="dash", line_color="grey")
            fig_cum.update_layout(
                height=350,
                yaxis_title="Cumulative FCFF (GBPm)",
                xaxis_title="Year",
            )
            st.plotly_chart(fig_cum, width='stretch')

        # --- Data table ---
        with st.expander("Detailed Annual Data"):
            if len(results.dates) > 0:
                annual_df = pd.DataFrame({
                    'Year': years,
                    'Revenue (GBPk)': [annual_data[y]['revenue'] for y in years],
                    'OPEX (GBPk)': [annual_data[y]['opex'] for y in years],
                    'CAPEX (GBPk)': [annual_data[y]['capex'] for y in years],
                    'Tax (GBPk)': [annual_data[y]['tax'] for y in years],
                    'FCFF (GBPk)': [annual_data[y]['fcff'] for y in years],
                })
                annual_df = annual_df.round(1)
                st.dataframe(annual_df, width='stretch', hide_index=True)

                csv = annual_df.to_csv(index=False)
                st.download_button(
                    "Download Annual Data (CSV)",
                    data=csv,
                    file_name="financial_analysis_annual.csv",
                    mime="text/csv",
                )

    # =========================================================================
    # SECTION 11: EXCEL EXPORT (Placeholder — Windows/COM only)
    # =========================================================================
    st.divider()
    st.header("11. Excel Workbook Export")

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
