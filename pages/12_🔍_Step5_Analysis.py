"""
Step 5: Detailed Analysis

Explore simulation results in detail for a selected configuration:
- Section 1: Configuration selection (BESS size, duration, DG, dates)
- Section 2: Dispatch visualization graph
- Section 3: Hourly data table with color-coded states
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    set_current_step, get_step_status, can_navigate_to_step
)
from src.template_inference import get_template_info


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Analysis",
    page_icon="🔍",
    layout="wide"
)

# Initialize wizard state
init_wizard_state()
set_current_step(5)

# Check if can access this step
if not can_navigate_to_step(4):  # Need Step 4 complete
    st.warning("Please complete Steps 1-4 first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/8_🚀_Step1_Setup.py")
    st.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Analysis", 'current'),
    ]

    cols = st.columns(5)
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


def date_to_hour_index(selected_date, base_year=2024):
    """Convert date to hour index in simulation."""
    base_date = date(base_year, 1, 1)
    days_since_start = (selected_date - base_date).days
    return days_since_start * 24


def create_dispatch_graph(hourly_df: pd.DataFrame, load_mw: float, bess_capacity: float = 100,
                          soc_on: float = 30, soc_off: float = 80) -> go.Figure:
    """Create dispatch visualization with dual y-axis (matching Calculation Logic style)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    hours = list(range(len(hourly_df)))

    # Solar (orange area fill)
    fig.add_trace(go.Scatter(
        x=hours, y=hourly_df['solar_mw'].values,
        name='Solar', fill='tozeroy',
        line=dict(color='#FFA500', width=2),
        fillcolor='rgba(255,165,0,0.3)',
        hovertemplate='Hour %{x}<br>Solar: %{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    # DG Output (red fill) - only if DG is used
    if 'dg_output_mw' in hourly_df.columns and hourly_df['dg_output_mw'].sum() > 0:
        fig.add_trace(go.Scatter(
            x=hours, y=hourly_df['dg_output_mw'].values,
            name='DG Output', fill='tozeroy',
            line=dict(color='#DC143C', width=2, shape='hv'),
            fillcolor='rgba(220,20,60,0.3)',
            hovertemplate='Hour %{x}<br>DG: %{y:.1f} MW<extra></extra>'
        ), secondary_y=False)

    # BESS Power (blue line, +ve=discharge, -ve=charge)
    if 'bess_mw' in hourly_df.columns:
        fig.add_trace(go.Scatter(
            x=hours, y=hourly_df['bess_mw'].values,
            name='BESS Power',
            line=dict(color='#1f77b4', width=2, shape='hv'),
            hovertemplate='Hour %{x}<br>BESS: %{y:.1f} MW<extra></extra>'
        ), secondary_y=False)

    # SOC % (green dotted on secondary axis)
    if 'soc_percent' in hourly_df.columns:
        fig.add_trace(go.Scatter(
            x=hours, y=hourly_df['soc_percent'].values,
            name='SOC %',
            line=dict(color='#2E8B57', width=2, dash='dot', shape='hv'),
            hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'
        ), secondary_y=True)

    # BESS Energy (MWh) - royal blue dashed
    if 'soc_percent' in hourly_df.columns:
        bess_energy = hourly_df['soc_percent'].values * bess_capacity / 100
        fig.add_trace(go.Scatter(
            x=hours, y=bess_energy,
            name='BESS Energy (MWh)',
            line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
            hovertemplate='Hour %{x}<br>Energy: %{y:.1f} MWh<extra></extra>'
        ), secondary_y=True)

    # Delivery (purple line - 25 MW or 0)
    delivery_values = [load_mw if d == 'Yes' else 0 for d in hourly_df['delivery'].values]
    fig.add_trace(go.Scatter(
        x=hours, y=delivery_values,
        name='Delivery',
        line=dict(color='purple', width=3, shape='hv'),
        hovertemplate='Hour %{x}<br>Delivery: %{y:.0f} MW<extra></extra>'
    ), secondary_y=False)

    # Reference lines
    fig.add_hline(y=load_mw, line_dash="dash", line_color="gray",
                  annotation_text=f"Load {load_mw:.0f} MW", secondary_y=False)
    fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)

    # SOC threshold lines (on secondary y-axis)
    fig.add_hline(y=soc_on, line_dash="dot", line_color="red",
                  annotation_text=f"DG ON ({soc_on:.0f}%)", secondary_y=True)
    fig.add_hline(y=soc_off, line_dash="dot", line_color="green",
                  annotation_text=f"DG OFF ({soc_off:.0f}%)", secondary_y=True)

    # Day boundary markers (every 24 hours)
    num_days = len(hours) // 24
    for day in range(1, num_days + 1):
        fig.add_vline(x=day * 24, line_dash="dash", line_color="black", line_width=1,
                      annotation_text=f"Day {day + 1}", annotation_position="top")

    fig.update_layout(
        height=450,
        title="Hourly Dispatch Visualization",
        xaxis_title="Hour",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis=dict(showgrid=True, dtick=6)
    )
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="SOC (%) / Energy (MWh)", secondary_y=True, range=[0, 100])

    return fig


def style_hourly_row(row):
    """Color-code rows based on state (matching Calculation Logic style)."""
    # Check for unmet load (deficit) - highest priority
    if 'Unmet (MW)' in row.index and row['Unmet (MW)'] > 0:
        return ['background-color: #FFB6C1'] * len(row)  # Pink - deficit

    # Check DG output (not just state)
    if 'DG (MW)' in row.index and row['DG (MW)'] > 0:
        return ['background-color: #FFFACD'] * len(row)  # Yellow - DG running

    # Check BESS state
    if 'BESS State' in row.index:
        if row['BESS State'] == 'Discharging':
            return ['background-color: #E6E6FA'] * len(row)  # Lavender - discharging
        if row['BESS State'] == 'Charging':
            return ['background-color: #90EE90'] * len(row)  # Green - charging

    return [''] * len(row)


def run_single_simulation(bess_mwh, duration, dg_mw, template_id, setup, rules, solar_profile, load_profile):
    """Run simulation for a single configuration and return hourly data."""
    from src.dispatch_engine import SimulationParams, run_simulation

    power_mw = bess_mwh / duration

    # Build SimulationParams object (same as Step 3)
    params = SimulationParams(
        load_profile=load_profile if isinstance(load_profile, list) else load_profile.tolist(),
        solar_profile=solar_profile if isinstance(solar_profile, list) else solar_profile.tolist(),
        bess_capacity=bess_mwh,
        bess_charge_power=power_mw,
        bess_discharge_power=power_mw,
        bess_efficiency=setup['bess_efficiency'],
        bess_min_soc=setup['bess_min_soc'],
        bess_max_soc=setup['bess_max_soc'],
        bess_initial_soc=setup['bess_initial_soc'],
        bess_daily_cycle_limit=setup['bess_daily_cycle_limit'],
        bess_enforce_cycle_limit=setup['bess_enforce_cycle_limit'],
        dg_enabled=setup['dg_enabled'],
        dg_capacity=dg_mw,
        dg_charges_bess=rules.get('dg_charges_bess', False),
        dg_load_priority=rules.get('dg_load_priority', 'bess_first'),
        dg_takeover_mode=rules.get('dg_takeover_mode', False),
        night_start_hour=rules.get('night_start', 18),
        night_end_hour=rules.get('night_end', 6),
        day_start_hour=rules.get('day_start', 6),
        day_end_hour=rules.get('day_end', 18),
        blackout_start_hour=rules.get('blackout_start', 22),
        blackout_end_hour=rules.get('blackout_end', 6),
        dg_soc_on_threshold=rules.get('soc_on_threshold', 30),
        dg_soc_off_threshold=rules.get('soc_off_threshold', 80),
    )

    try:
        hourly_results = run_simulation(params, template_id, num_hours=8760)
        return hourly_results
    except Exception as e:
        st.error(f"Simulation error: {e}")
        return None


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("🔍 Detailed Analysis")
st.markdown("### Step 5 of 5: Explore Configuration Details")

render_step_indicator()

st.divider()

# Get wizard state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']
sizing = state['sizing']
results_state = state['results']

# Check for results
results_df = results_state.get('simulation_results') if results_state else None

if results_df is None or len(results_df) == 0:
    st.warning("No simulation results found. Please run simulations in Step 3 first.")
    if st.button("Go to Step 3"):
        st.switch_page("pages/10_📐_Step3_Sizing.py")
    st.stop()


# =============================================================================
# SECTION 1: CONFIGURATION SELECTION
# =============================================================================

st.subheader("📋 Section 1: Configuration Selection")

col1, col2, col3 = st.columns(3)

with col1:
    bess_options = sorted(results_df['bess_mwh'].unique())
    # Default to first option or pre-selected from Step 4
    default_bess_idx = 0
    if 'analysis_config_idx' in (results_state or {}):
        selected_idx = results_state.get('analysis_config_idx')
        if selected_idx in results_df.index:
            default_bess = results_df.loc[selected_idx, 'bess_mwh']
            if default_bess in bess_options:
                default_bess_idx = bess_options.index(default_bess)

    selected_bess = st.selectbox(
        "BESS Capacity (MWh)",
        options=bess_options,
        index=default_bess_idx,
        key='analysis_bess'
    )

with col2:
    # Filter durations available for selected BESS size
    available_durations = sorted(results_df[results_df['bess_mwh'] == selected_bess]['duration_hrs'].unique())
    selected_duration = st.selectbox(
        "Duration (hrs)",
        options=available_durations,
        key='analysis_duration'
    )

with col3:
    # Filter DG sizes available for selected BESS/duration combo
    filtered = results_df[(results_df['bess_mwh'] == selected_bess) &
                          (results_df['duration_hrs'] == selected_duration)]
    dg_options = sorted(filtered['dg_mw'].unique())
    selected_dg = st.selectbox(
        "DG Capacity (MW)",
        options=dg_options,
        key='analysis_dg'
    )

# Date range selection
st.markdown("**Date Range for Analysis:**")
date_col1, date_col2, date_col3 = st.columns([1, 1, 2])

with date_col1:
    start_date = st.date_input(
        "Start Date",
        value=date(2024, 1, 1),
        min_value=date(2024, 1, 1),
        max_value=date(2024, 12, 31),
        key='analysis_start_date'
    )

with date_col2:
    # End date max 7 days from start for performance
    max_end = min(start_date + timedelta(days=6), date(2024, 12, 31))
    default_end = min(start_date + timedelta(days=2), max_end)

    end_date = st.date_input(
        "End Date",
        value=default_end,
        min_value=start_date,
        max_value=max_end,
        key='analysis_end_date'
    )

with date_col3:
    days_selected = (end_date - start_date).days + 1
    st.info(f"📅 Analyzing **{days_selected} days** ({days_selected * 24} hours)")

# Configuration summary
power_mw = selected_bess / selected_duration
st.markdown(f"""
**Selected Configuration:** `{power_mw:.0f} MW × {selected_duration}-hr = {selected_bess:.0f} MWh` |
DG: `{selected_dg:.0f} MW`
""")

# Template info
template_id = rules.get('inferred_template', 0)
template_info = get_template_info(template_id)
st.markdown(f"**Dispatch Strategy:** {template_info['name']}")

# Run Analysis button
run_analysis = st.button("🚀 Load Analysis", type="primary", width='stretch')

st.divider()


# =============================================================================
# SECTION 2 & 3: DISPATCH GRAPH AND HOURLY TABLE
# =============================================================================

if run_analysis or 'analysis_hourly_data' in st.session_state:

    # Check if we need to re-run simulation
    needs_rerun = True
    if 'analysis_hourly_data' in st.session_state:
        cached = st.session_state.get('analysis_cache_key')
        current_key = f"{selected_bess}_{selected_duration}_{selected_dg}_{start_date}_{end_date}"
        if cached == current_key:
            needs_rerun = False

    if needs_rerun or run_analysis:
        with st.spinner("Running simulation for selected configuration..."):
            # Load solar profile
            solar_source = setup.get('solar_source', 'default')
            if solar_source == 'upload' and setup.get('solar_csv_data') is not None:
                solar_profile = setup['solar_csv_data']
            elif 'default_solar_profile' in st.session_state:
                solar_profile = st.session_state.default_solar_profile.tolist()
            else:
                try:
                    from src.data_loader import load_solar_profile
                    solar_data = load_solar_profile()
                    solar_profile = solar_data.tolist() if solar_data is not None else [0] * 8760
                except:
                    solar_profile = [0] * 8760

            # Build load profile
            from src.load_builder import build_load_profile
            load_params = {
                'mw': setup['load_mw'],
                'start': setup.get('load_day_start', 6),
                'end': setup.get('load_day_end', 18),
                'windows': setup.get('load_windows', []),
                'data': setup.get('load_csv_data'),
            }
            load_profile = build_load_profile(setup['load_mode'], load_params)

            # Run simulation
            hourly_results = run_single_simulation(
                selected_bess, selected_duration, selected_dg,
                template_id, setup, rules,
                solar_profile, load_profile.tolist()
            )

            if hourly_results is not None and len(hourly_results) > 0:
                # Convert hourly results list to DataFrame
                hourly_df = pd.DataFrame([{
                    'hour': h.t,
                    'day': h.day,
                    'hour_of_day': h.hour_of_day,
                    'solar_mw': h.solar,
                    'load_mw': h.load,
                    'bess_mw': h.bess_power,
                    'soc_percent': h.soc_pct,
                    'bess_state': h.bess_state,
                    'dg_output_mw': h.dg_to_load + h.dg_to_bess + h.dg_curtailed,  # Total DG output
                    'dg_state': 'ON' if h.dg_running else 'OFF',
                    'solar_to_load': h.solar_to_load,
                    'dg_to_load': h.dg_to_load,
                    'dg_to_bess': h.dg_to_bess,
                    'dg_curtailed': h.dg_curtailed,
                    'bess_to_load': h.bess_to_load,
                    'unmet_mw': h.unserved,
                    'delivery': 'Yes' if h.unserved == 0 else 'No',
                    'solar_curtailed': h.solar_curtailed,
                } for h in hourly_results])

                # Filter to selected date range
                start_hour = date_to_hour_index(start_date)
                end_hour = date_to_hour_index(end_date) + 24
                hourly_df = hourly_df.iloc[start_hour:end_hour].reset_index(drop=True)

                # Cache the results
                st.session_state.analysis_hourly_data = hourly_df
                st.session_state.analysis_cache_key = f"{selected_bess}_{selected_duration}_{selected_dg}_{start_date}_{end_date}"
            else:
                st.error("Failed to get hourly data from simulation")
                st.stop()

    # Get cached hourly data
    hourly_df = st.session_state.get('analysis_hourly_data')

    if hourly_df is not None and len(hourly_df) > 0:

        # =============================================================================
        # SECTION 2: DISPATCH GRAPH
        # =============================================================================

        st.subheader("📈 Section 2: Dispatch Visualization")

        # Summary metrics for selected period
        total_hours = len(hourly_df)
        delivery_hours = (hourly_df['delivery'] == 'Yes').sum()
        dg_hours = (hourly_df['dg_state'] == 'ON').sum()
        avg_soc = hourly_df['soc_percent'].mean()
        solar_curtailed = hourly_df['solar_curtailed'].sum()
        total_solar = hourly_df['solar_mw'].sum()
        wastage_pct = (solar_curtailed / total_solar * 100) if total_solar > 0 else 0

        metric_cols = st.columns(5)
        metric_cols[0].metric("Delivery Hours", f"{delivery_hours}/{total_hours}", f"{delivery_hours/total_hours*100:.1f}%")
        metric_cols[1].metric("DG Runtime", f"{dg_hours} hrs", f"{dg_hours/total_hours*100:.1f}% of period")
        metric_cols[2].metric("Avg SOC", f"{avg_soc:.0f}%")
        metric_cols[3].metric("Solar Curtailed", f"{solar_curtailed:.1f} MWh")
        metric_cols[4].metric("Wastage %", f"{wastage_pct:.1f}%")

        # Create and display dispatch graph
        soc_on = rules.get('soc_on_threshold', 30)
        soc_off = rules.get('soc_off_threshold', 80)
        fig = create_dispatch_graph(hourly_df, setup['load_mw'], selected_bess, soc_on, soc_off)
        st.plotly_chart(fig, width='stretch')

        # Graph legend
        st.caption("""
        **Orange**: Solar | **Red**: DG Output | **Blue**: BESS Power (negative=charging) | **Purple**: Delivery

        **Green dotted**: SOC % | **Royal Blue dashed**: BESS Energy (MWh)
        """)

        st.divider()

        # =============================================================================
        # SECTION 3: HOURLY DATA TABLE
        # =============================================================================

        st.subheader("📊 Section 3: Hourly Data Table")

        # Prepare display DataFrame
        display_df = hourly_df.copy()
        display_df['Hour'] = display_df['hour']
        display_df['Day'] = display_df['day']
        display_df['HoD'] = display_df['hour_of_day']
        display_df['Solar (MW)'] = display_df['solar_mw'].round(1)
        display_df['DG (MW)'] = display_df['dg_output_mw'].round(1)
        display_df['DG→Load'] = display_df['dg_to_load'].round(1)
        display_df['DG→BESS'] = display_df['dg_to_bess'].round(1)
        display_df['DG Curt'] = display_df['dg_curtailed'].round(1)
        display_df['BESS (MW)'] = display_df['bess_mw'].round(1)
        display_df['SOC (%)'] = display_df['soc_percent'].round(1)
        display_df['BESS State'] = display_df['bess_state']
        display_df['DG State'] = display_df['dg_state']
        display_df['To Load (MW)'] = (display_df['solar_to_load'] + display_df['dg_to_load'] + display_df['bess_to_load']).round(1)
        display_df['Unmet (MW)'] = display_df['unmet_mw'].round(1)
        display_df['Delivery'] = display_df['delivery']

        display_cols = [
            'Hour', 'Day', 'HoD',
            'Solar (MW)', 'DG (MW)', 'DG→Load', 'DG→BESS', 'DG Curt',
            'BESS (MW)', 'SOC (%)',
            'BESS State', 'DG State',
            'To Load (MW)', 'Unmet (MW)', 'Delivery'
        ]

        # Apply styling
        styled_df = display_df[display_cols].style.apply(style_hourly_row, axis=1)

        st.dataframe(
            styled_df,
            width='stretch',
            height=500
        )

        # Legend for colors
        st.markdown("""
        **Row Colors:**
        🟢 Green = BESS Charging |
        🟣 Lavender = BESS Discharging |
        🟡 Yellow = DG Running |
        🔴 Pink = Unmet Load (Deficit)
        """)

        # Export button
        st.markdown("---")
        csv_data = display_df[display_cols].to_csv(index=False)
        st.download_button(
            "📥 Download Hourly CSV",
            data=csv_data,
            file_name=f"analysis_{selected_bess}mwh_{selected_duration}hr_{selected_dg}mw_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            width='stretch'
        )

else:
    st.info("👆 Select a configuration and click **Load Analysis** to view detailed dispatch data.")


# =============================================================================
# NAVIGATION
# =============================================================================

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("← Back to Results", width='stretch'):
        st.switch_page("pages/11_📊_Step4_Results.py")

# Sidebar summary
with st.sidebar:
    st.markdown("### 📋 Analysis Summary")

    st.markdown("**Configuration:**")
    st.markdown(f"- BESS: {selected_bess:.0f} MWh")
    st.markdown(f"- Duration: {selected_duration} hrs")
    st.markdown(f"- Power: {selected_bess/selected_duration:.0f} MW")
    st.markdown(f"- DG: {selected_dg:.0f} MW")

    st.markdown("---")

    st.markdown("**Date Range:**")
    st.markdown(f"- Start: {start_date}")
    st.markdown(f"- End: {end_date}")

    st.markdown("---")

    template_info = get_template_info(template_id)
    st.markdown(f"**Strategy:** {template_info['name']}")
    st.markdown(f"**Load:** {setup['load_mw']} MW")
