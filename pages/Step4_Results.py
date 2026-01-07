"""
Step 4: Results & Quick Analysis
View detailed simulation results with hourly dispatch visualization.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from src.wizard_state import (
    init_wizard_state, get_wizard_state, get_step_status
)
from src.dispatch_engine import (
    SimulationParams, run_simulation, HourlyResult, calculate_metrics
)
from src.data_loader import load_solar_profile
from src.load_builder import build_load_profile


def get_wizard_section(section: str) -> dict:
    """Get a section from wizard state."""
    state = get_wizard_state()
    return state.get(section, {})

# Page config
st.set_page_config(
    page_title="Results & Analysis",
    page_icon="📊",
    layout="wide"
)

init_wizard_state()


def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", 'current'),
        ("5", "Multi-Year", get_step_status(5)),
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

# =============================================================================
# CONSTANTS
# =============================================================================

CONTAINER_SPECS = {
    '5mwh_2.5mw': {'energy_mwh': 5, 'power_mw': 2.5, 'duration_hr': 2, 'label': '2-hour (0.5C)'},
    '5mwh_1.25mw': {'energy_mwh': 5, 'power_mw': 1.25, 'duration_hr': 4, 'label': '4-hour (0.25C)'},
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_solar_profile(setup):
    """Get solar profile from setup configuration - matches Step 3 exactly."""
    solar_source = setup.get('solar_source', 'default')

    if solar_source == 'upload' and setup.get('solar_csv_data') is not None:
        solar_data = setup['solar_csv_data']
        if isinstance(solar_data, list):
            return solar_data[:8760] if len(solar_data) >= 8760 else solar_data
        return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()

    # Try default profile
    if 'default_solar_profile' in st.session_state and st.session_state.default_solar_profile is not None:
        solar_data = st.session_state.default_solar_profile
        return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()

    # Fallback: load from file
    try:
        solar_data = load_solar_profile()
        if solar_data is not None and len(solar_data) > 0:
            return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
    except Exception:
        pass

    return None


def get_solar_peak(setup):
    """Get actual peak MW from solar profile."""
    solar_profile = get_solar_profile(setup)
    if solar_profile is not None and len(solar_profile) > 0:
        return max(solar_profile)
    return setup.get('solar_capacity_mw', 100)  # Fallback to configured value


def get_load_profile(setup):
    """Build load profile from setup configuration - matches Step 3 exactly."""
    load_params = {
        'mw': setup['load_mw'],
        'start': setup.get('load_day_start', 6),
        'end': setup.get('load_day_end', 18),
        'windows': setup.get('load_windows', []),
        'data': setup.get('load_csv_data'),
        'start_month': setup.get('load_season_start', 4),
        'end_month': setup.get('load_season_end', 10),
        'day_start': setup.get('load_season_day_start', 8),
        'day_end': setup.get('load_season_day_end', 0),
    }
    return build_load_profile(setup['load_mode'], load_params)


def build_simulation_params(bess_mwh: float, bess_power_mw: float, dg_mw: float) -> SimulationParams:
    """Build simulation parameters from wizard state - matches Step 3 exactly."""
    setup = get_wizard_section('setup')
    rules = get_wizard_section('rules')

    # Get profiles - matches Step 3
    load_profile = get_load_profile(setup)
    solar_profile = get_solar_profile(setup)

    if solar_profile is None:
        raise ValueError("No solar profile available")

    # Build params - matches Step 3 exactly
    params = SimulationParams(
        load_profile=load_profile.tolist(),
        solar_profile=solar_profile,
        bess_capacity=bess_mwh,
        bess_charge_power=bess_power_mw,
        bess_discharge_power=bess_power_mw,
        bess_efficiency=setup['bess_efficiency'],
        bess_min_soc=setup['bess_min_soc'],
        bess_max_soc=setup['bess_max_soc'],
        bess_initial_soc=setup['bess_initial_soc'],
        bess_daily_cycle_limit=setup['bess_daily_cycle_limit'],
        bess_enforce_cycle_limit=setup['bess_enforce_cycle_limit'],
        dg_enabled=setup['dg_enabled'] and dg_mw > 0,
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
        dg_fuel_curve_enabled=setup.get('dg_fuel_curve_enabled', False),
        dg_fuel_f0=setup.get('dg_fuel_f0', 0.03),
        dg_fuel_f1=setup.get('dg_fuel_f1', 0.22),
        dg_fuel_flat_rate=setup.get('dg_fuel_flat_rate', 0.25),
        cycle_charging_enabled=rules.get('cycle_charging_enabled', False),
        cycle_charging_min_load_pct=rules.get('cycle_charging_min_load_pct', 70.0),
        cycle_charging_off_soc=rules.get('cycle_charging_off_soc', 80.0),
    )

    return params


def get_template_id() -> int:
    """Get template ID from rules - uses inferred_template from Step 2."""
    rules = get_wizard_section('rules')
    return rules.get('inferred_template', 0)


def find_cached_result(bess_mwh: float, dg_mw: float, container_type: str):
    """Check if this configuration was already simulated in Step 3."""
    if 'sizing_results' not in st.session_state:
        return None

    results_df = st.session_state.sizing_results
    if results_df is None or len(results_df) == 0:
        return None

    # Results are stored as a DataFrame - filter for matching configuration
    spec = CONTAINER_SPECS.get(container_type, {})
    duration_hr = spec.get('duration_hr', 2)

    # Filter DataFrame for matching config
    mask = (
        (results_df['BESS (MWh)'] == bess_mwh) &
        (results_df['DG (MW)'] == dg_mw) &
        (results_df['Duration (hr)'] == duration_hr)
    )

    matching = results_df[mask]
    if len(matching) > 0:
        return matching.iloc[0].to_dict()

    return None


def run_single_simulation(bess_mwh: float, container_type: str, dg_mw: float):
    """Run a single simulation and return hourly results."""
    spec = CONTAINER_SPECS.get(container_type, CONTAINER_SPECS['5mwh_2.5mw'])

    # Calculate power from energy and duration
    bess_power_mw = bess_mwh / spec['duration_hr']

    params = build_simulation_params(bess_mwh, bess_power_mw, dg_mw)
    template_id = get_template_id()

    hourly_results = run_simulation(params, template_id, num_hours=8760)
    metrics = calculate_metrics(hourly_results, params)

    return hourly_results, metrics


def hourly_results_to_dataframe(hourly_results: list) -> pd.DataFrame:
    """Convert hourly results to DataFrame - matches Quick Analysis format."""
    data = []
    start_date = datetime(2024, 1, 1)

    for hr in hourly_results:
        timestamp = start_date + timedelta(hours=hr.t - 1)
        data.append({
            'timestamp': timestamp,
            'hour': hr.t,
            'day': hr.day,
            'hour_of_day': hr.hour_of_day,
            'load_mw': hr.load,
            'solar_mw': hr.solar,
            'solar_to_load': hr.solar_to_load,
            'solar_to_bess': hr.solar_to_bess,
            'bess_to_load': hr.bess_to_load,
            'bess_mw': hr.bess_power,
            'bess_state': hr.bess_state,
            'dg_output_mw': hr.dg_to_load + hr.dg_to_bess + hr.dg_curtailed,
            'dg_state': 'ON' if hr.dg_running else 'OFF',
            'dg_to_load': hr.dg_to_load,
            'dg_to_bess': hr.dg_to_bess,
            'dg_curtailed': hr.dg_curtailed,
            'soc_mwh': hr.soc,
            'soc_percent': hr.soc_pct,
            'unmet_mw': hr.unserved,
            'delivery': 'Yes' if (hr.load > 0 and hr.unserved < 0.001) else 'No',
            'solar_curtailed': hr.solar_curtailed,
            'daily_cycles': hr.daily_cycles,
        })

    return pd.DataFrame(data)


def style_hourly_row(row):
    """Color-code rows based on state."""
    if 'Unmet (MW)' in row.index and row['Unmet (MW)'] > 0:
        return ['background-color: #FFB6C1'] * len(row)
    if 'DG (MW)' in row.index and row['DG (MW)'] > 0:
        return ['background-color: #FFFACD'] * len(row)
    if 'BESS State' in row.index:
        if row['BESS State'] == 'Discharging':
            return ['background-color: #E6E6FA'] * len(row)
        if row['BESS State'] == 'Charging':
            return ['background-color: #90EE90'] * len(row)
    return [''] * len(row)


def create_dispatch_graph(hourly_df: pd.DataFrame, load_mw: float, bess_capacity: float = 100,
                          soc_on: float = 30, soc_off: float = 80) -> go.Figure:
    """Create dispatch visualization with dual y-axis - matches Quick Analysis."""
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

    # DG Output (red fill)
    if 'dg_output_mw' in hourly_df.columns and hourly_df['dg_output_mw'].sum() > 0:
        fig.add_trace(go.Scatter(
            x=hours, y=hourly_df['dg_output_mw'].values,
            name='DG Output', fill='tozeroy',
            line=dict(color='#DC143C', width=2, shape='hv'),
            fillcolor='rgba(220,20,60,0.3)',
            hovertemplate='Hour %{x}<br>DG: %{y:.1f} MW<extra></extra>'
        ), secondary_y=False)

    # BESS Power (blue line)
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

    # BESS Energy (MWh)
    if 'soc_percent' in hourly_df.columns:
        bess_energy = hourly_df['soc_percent'].values * bess_capacity / 100
        fig.add_trace(go.Scatter(
            x=hours, y=bess_energy,
            name='BESS Energy (MWh)',
            line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
            hovertemplate='Hour %{x}<br>Energy: %{y:.1f} MWh<extra></extra>'
        ), secondary_y=True)

    # Delivery (purple line)
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
    fig.add_hline(y=soc_on, line_dash="dot", line_color="red",
                  annotation_text=f"DG ON ({soc_on:.0f}%)", secondary_y=True)
    fig.add_hline(y=soc_off, line_dash="dot", line_color="green",
                  annotation_text=f"DG OFF ({soc_off:.0f}%)", secondary_y=True)

    # Day boundary markers
    num_days = len(hours) // 24
    for day in range(1, min(num_days + 1, 15)):  # Limit markers for readability
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


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("📊 Results & Quick Analysis")
st.markdown("### Step 4: View Simulation Results")

render_step_indicator()

# Get configuration
setup = get_wizard_section('setup')
rules = get_wizard_section('rules')
dg_enabled = setup.get('dg_enabled', False)
container_types = setup.get('bess_container_types', ['5mwh_2.5mw'])

if not container_types:
    container_types = ['5mwh_2.5mw']

st.divider()

# =============================================================================
# CONFIGURATION SELECTION
# =============================================================================

st.subheader("Configuration Selection")

# Get previous values from analysis_results if available
prev_results = st.session_state.get('analysis_results')
default_bess = prev_results['bess_mwh'] if prev_results else 50
default_dg = prev_results['dg_mw'] if prev_results else int(setup.get('load_mw', 25))
default_container = prev_results['container_type'] if prev_results else container_types[0]

# Ensure default_container is valid for current container_types
if default_container not in container_types:
    default_container = container_types[0]

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**BESS Size**")

    # Container type selection
    container_options = {ct: CONTAINER_SPECS[ct]['label'] for ct in container_types}

    if len(container_types) > 1:
        default_index = container_types.index(default_container) if default_container in container_types else 0
        selected_container = st.radio(
            "Duration Class:",
            options=container_types,
            format_func=lambda x: container_options[x],
            horizontal=True,
            index=default_index,
            key='result_container_type'
        )
    else:
        selected_container = container_types[0]
        st.info(f"Duration: {container_options[selected_container]}")

    # BESS capacity (in 5 MWh increments)
    bess_mwh = st.number_input(
        "BESS Capacity (MWh)",
        min_value=5,
        max_value=500,
        value=default_bess,
        step=5,
        help="Select in 5 MWh increments (container units)",
        key='result_bess_mwh'
    )

    # Show derived power
    spec = CONTAINER_SPECS[selected_container]
    bess_power = bess_mwh / spec['duration_hr']
    num_containers = bess_mwh / spec['energy_mwh']
    st.caption(f"Power: {bess_power:.1f} MW | Containers: {num_containers:.0f}")

with col2:
    st.markdown("**DG Size**")

    if dg_enabled:
        dg_mw = st.number_input(
            "DG Capacity (MW)",
            min_value=0,
            max_value=200,
            value=default_dg,
            step=5,
            key='result_dg_mw'
        )
    else:
        dg_mw = 0
        st.info("DG not enabled in setup")
        st.caption("Enable DG in Step 1 to include generator")

with col3:
    st.markdown("**Configuration Summary**")
    st.markdown(f"- **Load:** {setup.get('load_mw', 25)} MW")
    solar_peak = get_solar_peak(setup)
    st.markdown(f"- **Solar Peak:** {solar_peak:.1f} MW")
    st.markdown(f"- **BESS:** {bess_mwh} MWh / {bess_power:.1f} MW")
    if dg_enabled and dg_mw > 0:
        st.markdown(f"- **DG:** {dg_mw} MW")
    else:
        st.markdown("- **DG:** None")

st.divider()

# =============================================================================
# RUN SIMULATION / FETCH RESULTS
# =============================================================================

# Check for cached results
cached = find_cached_result(bess_mwh, dg_mw, selected_container)

if cached:
    st.success(f"Found cached results from Step 3 sizing run")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button(
        "See Results" if cached else "Run Simulation",
        type="primary",
        use_container_width=True,
        key='run_analysis_btn'
    )

# Store results in session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_hourly_df' not in st.session_state:
    st.session_state.analysis_hourly_df = None

if run_button:
    with st.spinner("Running 8760-hour simulation..." if not cached else "Loading results..."):
        try:
            hourly_results, metrics = run_single_simulation(bess_mwh, selected_container, dg_mw)

            # Convert to DataFrame
            hourly_df = hourly_results_to_dataframe(hourly_results)

            # Store in session state
            st.session_state.analysis_results = {
                'metrics': metrics,
                'bess_mwh': bess_mwh,
                'dg_mw': dg_mw,
                'container_type': selected_container,
            }
            st.session_state.analysis_hourly_df = hourly_df

            st.success("Simulation complete!")
            st.rerun()

        except Exception as e:
            st.error(f"Simulation failed: {str(e)}")

# =============================================================================
# RESULTS DISPLAY
# =============================================================================

if st.session_state.analysis_results is not None:
    results = st.session_state.analysis_results
    metrics = results['metrics']
    hourly_df = st.session_state.analysis_hourly_df

    st.divider()
    st.subheader("Simulation Results")

    # Key metrics - metrics is a SummaryMetrics dataclass
    col1, col2, col3, col4, col5 = st.columns(5)

    delivery_pct = metrics.pct_full_delivery
    green_pct = metrics.pct_green_delivery
    dg_hours = metrics.dg_runtime_hours
    wastage_pct = metrics.pct_solar_curtailed
    total_cycles = metrics.bess_equivalent_cycles

    col1.metric("Delivery %", f"{delivery_pct:.1f}%")
    col2.metric("Green %", f"{green_pct:.1f}%")
    col3.metric("DG Hours", f"{dg_hours:,.0f}")
    col4.metric("Wastage %", f"{wastage_pct:.1f}%")
    col5.metric("Total Cycles", f"{total_cycles:.0f}")

    # Additional metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    # Calculate additional metrics from summary
    unserved_mwh = metrics.total_unserved
    hours_with_load = metrics.hours_with_load
    total_solar = metrics.total_solar_generation
    solar_used = total_solar - metrics.total_solar_curtailed
    solar_utilization = (solar_used / total_solar * 100) if total_solar > 0 else 0

    col1.metric("Unserved (MWh)", f"{unserved_mwh:,.1f}")
    col2.metric("DG Starts", f"{metrics.dg_starts:,}")
    col3.metric("Delivery Hours", f"{metrics.hours_full_delivery:,}")
    col4.metric("Solar Utilization", f"{solar_utilization:.1f}%")

    # =============================================================================
    # MONTHLY SUMMARY TABLE
    # =============================================================================

    st.divider()
    st.subheader("Monthly Performance Summary")

    # Calculate monthly metrics
    monthly_data = []
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for month_num in range(1, 13):
        # Filter data for this month
        month_mask = hourly_df['timestamp'].dt.month == month_num
        month_df = hourly_df[month_mask]

        if len(month_df) == 0:
            continue

        # Calculate metrics for this month
        month_hours = len(month_df)
        month_load_hours = (month_df['load_mw'] > 0).sum()
        month_delivery = (month_df['delivery'] == 'Yes').sum()
        month_dg_hours = (month_df['dg_state'] == 'ON').sum()
        month_solar = month_df['solar_mw'].sum()
        month_curtailed = month_df['solar_curtailed'].sum()

        effective_hours = month_load_hours if month_load_hours > 0 else month_hours
        delivery_pct = (month_delivery / effective_hours * 100) if effective_hours > 0 else 0
        green_delivery = month_delivery - month_dg_hours  # Approximate green hours
        green_pct = (green_delivery / month_delivery * 100) if month_delivery > 0 else 0
        wastage_pct = (month_curtailed / month_solar * 100) if month_solar > 0 else 0

        monthly_data.append({
            'Month': month_names[month_num - 1],
            'Delivery %': round(delivery_pct, 1),
            'Green %': round(max(0, green_pct), 1),
            'Wastage %': round(wastage_pct, 1),
            'Delivery Hrs': int(month_delivery),
            'Load Hrs': int(month_load_hours),
            'DG Hrs': int(month_dg_hours),
            'Curtailed (MWh)': round(month_curtailed, 1),
        })

    monthly_df = pd.DataFrame(monthly_data)

    st.dataframe(
        monthly_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Delivery %': st.column_config.ProgressColumn(
                'Delivery %',
                min_value=0,
                max_value=100,
                format="%.1f%%"
            ),
            'Green %': st.column_config.ProgressColumn(
                'Green %',
                min_value=0,
                max_value=100,
                format="%.1f%%"
            ),
            'Wastage %': st.column_config.NumberColumn(
                'Wastage %',
                format="%.1f%%"
            ),
        }
    )

    st.divider()

    # =============================================================================
    # HOURLY DISPATCH CHART WITH DATE RANGE
    # =============================================================================

    st.subheader("Hourly Dispatch Chart")

    # Date range selection
    col1, col2, col3 = st.columns([1, 1, 2])

    min_date = datetime(2024, 1, 1)
    max_date = datetime(2024, 12, 31, 23, 59)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime(2024, 1, 1),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key='chart_start_date'
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime(2024, 1, 7),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key='chart_end_date'
        )

    with col3:
        # Quick range buttons
        st.markdown("**Quick Ranges:**")
        qcol1, qcol2, qcol3, qcol4 = st.columns(4)

        with qcol1:
            if st.button("Week", key='range_week'):
                st.session_state.chart_start_date = datetime(2024, 1, 1).date()
                st.session_state.chart_end_date = datetime(2024, 1, 7).date()
                st.rerun()
        with qcol2:
            if st.button("Month", key='range_month'):
                st.session_state.chart_start_date = datetime(2024, 1, 1).date()
                st.session_state.chart_end_date = datetime(2024, 1, 31).date()
                st.rerun()
        with qcol3:
            if st.button("Summer", key='range_summer'):
                st.session_state.chart_start_date = datetime(2024, 6, 1).date()
                st.session_state.chart_end_date = datetime(2024, 6, 30).date()
                st.rerun()
        with qcol4:
            if st.button("Winter", key='range_winter'):
                st.session_state.chart_start_date = datetime(2024, 12, 1).date()
                st.session_state.chart_end_date = datetime(2024, 12, 31).date()
                st.rerun()

    # Convert dates to datetime
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Validate range
    if start_dt > end_dt:
        st.error("Start date must be before end date")
    else:
        # Filter data by date range
        mask = (hourly_df['timestamp'] >= start_dt) & (hourly_df['timestamp'] <= end_dt)
        filtered_df = hourly_df[mask].copy()

        # Calculate days in range
        days_in_range = (end_dt - start_dt).days + 1
        period_hours = len(filtered_df)

        # Period metrics
        period_delivery = (filtered_df['delivery'] == 'Yes').sum()
        period_load_hours = (filtered_df['load_mw'] > 0).sum()
        period_dg = (filtered_df['dg_state'] == 'ON').sum()
        period_soc = filtered_df['soc_percent'].mean()
        period_curtailed = filtered_df['solar_curtailed'].sum()
        period_solar = filtered_df['solar_mw'].sum()
        period_wastage = (period_curtailed / period_solar * 100) if period_solar > 0 else 0

        effective_period_hours = period_load_hours if period_load_hours > 0 else period_hours
        delivery_pct = (period_delivery / effective_period_hours * 100) if effective_period_hours > 0 else 0

        st.caption(f"Showing {days_in_range} days ({period_hours:,} hours)")

        pm_cols = st.columns(6)
        pm_cols[0].metric("Delivery", f"{period_delivery}/{effective_period_hours}", f"{delivery_pct:.1f}%")
        pm_cols[1].metric("DG Hours", f"{period_dg}", f"{period_dg/period_hours*100:.1f}%" if period_hours > 0 else "0%")
        pm_cols[2].metric("Avg SOC", f"{period_soc:.0f}%")
        pm_cols[3].metric("Curtailed", f"{period_curtailed:.1f} MWh")
        pm_cols[4].metric("Wastage", f"{period_wastage:.1f}%")

        # Get parameters for chart
        load_mw = setup.get('load_mw', 25)
        bess_capacity = results['bess_mwh']
        soc_on = rules.get('soc_on_threshold', 30)
        soc_off = rules.get('soc_off_threshold', 80)

        # Dispatch graph
        fig = create_dispatch_graph(filtered_df, load_mw, bess_capacity, soc_on, soc_off)
        st.plotly_chart(fig, use_container_width=True)

        st.caption("""
        **Orange**: Solar | **Red**: DG Output | **Blue**: BESS Power (negative=charging) | **Purple**: Delivery
        **Green dotted**: SOC % | **Royal Blue dashed**: BESS Energy (MWh)
        """)

        # Styled Hourly Data Table (always visible)
        st.subheader("📊 Hourly Data Table")

        display_df = filtered_df.copy()
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

        styled_df = display_df[display_cols].style.apply(style_hourly_row, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)

        st.markdown("""
        **Row Colors:** 🟢 Green = Charging | 🟣 Lavender = Discharging | 🟡 Yellow = DG Running | 🔴 Pink = Unmet Load
        """)

        # Export buttons
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            csv_data = filtered_df.to_csv(index=False)
            st.download_button(
                "📥 Download Selected Range CSV",
                data=csv_data,
                file_name=f"results_{bess_capacity}mwh_{start_date}_to_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            full_year_csv = hourly_df.to_csv(index=False)
            st.download_button(
                "📥 Download Full Year CSV (8760 hours)",
                data=full_year_csv,
                file_name=f"results_{bess_capacity}mwh_full_year.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    st.info("Select a configuration and click 'Run Simulation' to see results")

st.divider()

# Navigation
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back to Sizing", use_container_width=True):
        st.switch_page("pages/Step3_Sizing.py")

with col3:
    has_results = st.session_state.analysis_results is not None
    if st.button("Next → Multi-Year", type="primary" if has_results else "secondary",
                 disabled=not has_results, use_container_width=True):
        st.switch_page("pages/Step5_MultiYear.py")

# Sidebar summary
with st.sidebar:
    st.markdown("### Configuration")
    st.markdown(f"**Load:** {setup.get('load_mw', 25):.1f} MW")
    st.markdown(f"**Solar Peak:** {get_solar_peak(setup):.1f} MW")

    if st.session_state.analysis_results:
        r = st.session_state.analysis_results
        container_spec = CONTAINER_SPECS[r['container_type']]
        bess_power = r['bess_mwh'] / container_spec['energy_mwh'] * container_spec['power_mw']
        st.markdown(f"**BESS:** {r['bess_mwh']} MWh / {bess_power:.1f} MW")
        if r['dg_mw'] > 0:
            st.markdown(f"**DG:** {r['dg_mw']} MW")
        else:
            st.markdown("**DG:** Disabled")
