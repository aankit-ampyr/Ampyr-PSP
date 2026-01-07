"""
Step 3: BESS & DG Sizing

Run 8760-hour simulations across BESS configurations to find optimal sizing.
Configurations use discrete 5 MWh container increments.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    set_current_step, mark_step_completed, get_step_status, can_navigate_to_step
)
from src.load_builder import build_load_profile
from src.data_loader import load_solar_profile, load_solar_profile_by_name
from src.dispatch_engine import SimulationParams, run_simulation, calculate_metrics


# =============================================================================
# CONSTANTS
# =============================================================================

# Container specifications
CONTAINER_SPECS = {
    '5mwh_2.5mw': {'energy_mwh': 5, 'power_mw': 2.5, 'duration_hr': 2, 'label': '2-hour (0.5C)'},
    '5mwh_1.25mw': {'energy_mwh': 5, 'power_mw': 1.25, 'duration_hr': 4, 'label': '4-hour (0.25C)'},
}

CAPACITY_STEP_MWH = 5  # Discrete container increment


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Step 3",
    page_icon="📐",
    layout="wide"
)

# Initialize wizard state
init_wizard_state()
set_current_step(3)

# Check if can access this step
if not can_navigate_to_step(3):
    st.warning("Please complete Steps 1 and 2 first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/Step1_Setup.py")
    st.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", 'current'),
        ("4", "Results", get_step_status(4)),
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


def get_load_profile(setup):
    """Build load profile from setup configuration."""
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


def get_solar_profile(setup):
    """Get solar profile from setup configuration."""
    solar_source = setup.get('solar_source', 'inputs')

    # Handle uploaded CSV data
    if solar_source == 'upload' and setup.get('solar_csv_data') is not None:
        solar_data = setup['solar_csv_data']
        if isinstance(solar_data, list):
            return solar_data[:8760] if len(solar_data) >= 8760 else solar_data
        return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()

    # Handle selection from Inputs folder
    if solar_source in ('inputs', 'default'):
        selected_file = setup.get('solar_selected_file')
        if selected_file:
            try:
                solar_data = load_solar_profile_by_name(selected_file)
                if solar_data is not None and len(solar_data) > 0:
                    return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
            except Exception:
                pass

    # Fallback: load default profile
    try:
        solar_data = load_solar_profile()
        if solar_data is not None and len(solar_data) > 0:
            return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
    except Exception:
        pass

    return None


def run_sizing_simulation(capacity_range, container_types, dg_range, setup, rules, progress_callback=None):
    """
    Run batch simulation for all BESS/DG configurations.

    Args:
        capacity_range: tuple (min_mwh, max_mwh, step_mwh)
        container_types: list of container type keys
        dg_range: tuple (min_mw, max_mw, step_mw) or None if DG disabled
        setup: wizard setup state
        rules: wizard rules state
        progress_callback: function(current, total, message) for progress updates

    Returns:
        DataFrame with simulation results
    """
    # Get profiles
    load_profile = get_load_profile(setup)
    solar_profile = get_solar_profile(setup)

    if solar_profile is None:
        raise ValueError("No solar profile available")

    # Get template
    template_id = rules.get('inferred_template', 0)

    # Generate configurations
    configs = []
    cap_min, cap_max, cap_step = capacity_range
    cap_values = np.arange(cap_min, cap_max + cap_step, cap_step)

    # DG values
    if dg_range and setup['dg_enabled']:
        dg_min, dg_max, dg_step = dg_range
        dg_values = np.arange(dg_min, dg_max + dg_step, dg_step)
    else:
        dg_values = [0]

    # Build all configs
    for cap in cap_values:
        for container_type in container_types:
            spec = CONTAINER_SPECS[container_type]
            power = cap / spec['duration_hr']  # MW = MWh / hours

            for dg in dg_values:
                configs.append({
                    'capacity_mwh': float(cap),
                    'container_type': container_type,
                    'duration_hr': spec['duration_hr'],
                    'power_mw': float(power),
                    'dg_capacity_mw': float(dg),
                    'containers': int(cap / spec['energy_mwh']),
                })

    # Run simulations
    results = []
    total = len(configs)

    for i, config in enumerate(configs):
        if progress_callback:
            progress_callback(i + 1, total, f"Config {i+1}/{total}: {config['capacity_mwh']:.0f} MWh, {config['duration_hr']}hr")

        # Build simulation params
        params = SimulationParams(
            load_profile=load_profile.tolist(),
            solar_profile=solar_profile,
            bess_capacity=config['capacity_mwh'],
            bess_charge_power=config['power_mw'],
            bess_discharge_power=config['power_mw'],
            bess_efficiency=setup['bess_efficiency'],
            bess_min_soc=setup['bess_min_soc'],
            bess_max_soc=setup['bess_max_soc'],
            bess_initial_soc=setup['bess_initial_soc'],
            bess_daily_cycle_limit=setup['bess_daily_cycle_limit'],
            bess_enforce_cycle_limit=setup['bess_enforce_cycle_limit'],
            dg_enabled=setup['dg_enabled'] and config['dg_capacity_mw'] > 0,
            dg_capacity=config['dg_capacity_mw'],
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

        # Run simulation
        hourly_results = run_simulation(params, template_id, num_hours=8760)
        metrics = calculate_metrics(hourly_results, params)

        # Store result
        results.append({
            'BESS (MWh)': config['capacity_mwh'],
            'Duration (hr)': config['duration_hr'],
            'Power (MW)': config['power_mw'],
            'Containers': config['containers'],
            'DG (MW)': config['dg_capacity_mw'],
            'Delivery %': round(metrics.pct_full_delivery, 1),
            'Green %': round(metrics.pct_green_delivery, 1) if metrics.hours_full_delivery > 0 else 0,
            'Wastage %': round(metrics.pct_solar_curtailed, 1),
            'Delivery Hrs': metrics.hours_full_delivery,
            'Load Hrs': metrics.hours_with_load,
            'Green Hrs': metrics.hours_green_delivery,
            'DG Hrs': metrics.dg_runtime_hours,
            'DG Starts': metrics.dg_starts,
            'BESS Cycles': round(metrics.bess_equivalent_cycles, 0),
            'Unserved (MWh)': round(metrics.total_unserved, 1),
            'Fuel (L)': round(metrics.total_fuel_consumed, 0),
        })

    return pd.DataFrame(results)


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("📐 BESS & DG Sizing")
st.markdown("### Step 3: Configure and Run Sizing Simulation")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']
sizing = state['sizing']

dg_enabled = setup['dg_enabled']
container_types = setup.get('bess_container_types', ['5mwh_2.5mw', '5mwh_1.25mw'])

# Validate container types
if not container_types:
    st.error("No container types selected. Please go back to Step 1 and select at least one container type.")
    st.stop()


# =============================================================================
# SIZING CONFIGURATION
# =============================================================================

st.subheader("Configuration Range")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**BESS Capacity Range**")

    # Capacity inputs (5 MWh steps)
    cap_col1, cap_col2 = st.columns(2)
    with cap_col1:
        cap_min = st.number_input(
            "Minimum (MWh)",
            min_value=5,
            max_value=500,
            value=int(sizing.get('capacity_min', 25)),
            step=5,
            key='cap_min_input'
        )
    with cap_col2:
        cap_max = st.number_input(
            "Maximum (MWh)",
            min_value=cap_min,
            max_value=1000,
            value=max(int(sizing.get('capacity_max', 150)), cap_min),
            step=5,
            key='cap_max_input'
        )

    update_wizard_state('sizing', 'capacity_min', float(cap_min))
    update_wizard_state('sizing', 'capacity_max', float(cap_max))

    # Show container count preview
    for ct in container_types:
        spec = CONTAINER_SPECS[ct]
        min_containers = cap_min // spec['energy_mwh']
        max_containers = cap_max // spec['energy_mwh']
        st.caption(f"{spec['label']}: {min_containers}-{max_containers} containers")

    # Duration classes from selected containers
    st.markdown("**Duration Classes**")
    duration_labels = [f"{CONTAINER_SPECS[ct]['duration_hr']}-hour ({CONTAINER_SPECS[ct]['label']})" for ct in container_types]
    st.info(f"Evaluating: {', '.join(duration_labels)}")

with col2:
    if dg_enabled:
        st.markdown("**DG Capacity Range**")

        # Default DG capacity to load value
        load_mw = int(setup.get('load_mw', 25))

        dg_col1, dg_col2 = st.columns(2)
        with dg_col1:
            dg_min = st.number_input(
                "Minimum (MW)",
                min_value=0,
                max_value=200,
                value=int(sizing.get('dg_min', load_mw)),
                step=5,
                key='dg_min_input'
            )
        with dg_col2:
            dg_max = st.number_input(
                "Maximum (MW)",
                min_value=dg_min,
                max_value=200,
                value=max(int(sizing.get('dg_max', load_mw)), dg_min),
                step=5,
                key='dg_max_input'
            )

        dg_step = st.selectbox(
            "DG Step Size (MW)",
            options=[5, 10, 25],
            index=0,
            key='dg_step_select'
        )

        update_wizard_state('sizing', 'dg_min', float(dg_min))
        update_wizard_state('sizing', 'dg_max', float(dg_max))
        update_wizard_state('sizing', 'dg_step', float(dg_step))
    else:
        st.info("DG is disabled. Running Solar + BESS only configurations.")
        dg_min, dg_max, dg_step = 0, 0, 5


# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================

st.divider()

# Calculate number of configurations
num_cap_values = ((cap_max - cap_min) // CAPACITY_STEP_MWH) + 1
num_duration_values = len(container_types)
num_dg_values = ((dg_max - dg_min) // dg_step) + 1 if dg_enabled else 1
total_configs = int(num_cap_values * num_duration_values * num_dg_values)

col1, col2, col3, col4 = st.columns(4)
col1.metric("BESS Sizes", f"{int(num_cap_values)}")
col2.metric("Durations", f"{num_duration_values}")
col3.metric("DG Sizes", f"{int(num_dg_values)}")
col4.metric("Total Configs", f"{total_configs}")

# Estimate time
est_seconds = total_configs * 0.05  # ~50ms per config
if est_seconds < 60:
    est_time = f"~{int(est_seconds)} seconds"
else:
    est_time = f"~{int(est_seconds / 60)} minutes"
st.caption(f"Estimated runtime: {est_time}")


# =============================================================================
# RUN SIMULATION
# =============================================================================

st.divider()

if st.button("🚀 Run Sizing Simulation", type="primary", use_container_width=True):

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, message):
        progress_bar.progress(current / total)
        status_text.text(message)

    try:
        # Run simulation
        capacity_range = (cap_min, cap_max, CAPACITY_STEP_MWH)
        dg_range = (dg_min, dg_max, dg_step) if dg_enabled else None

        results_df = run_sizing_simulation(
            capacity_range=capacity_range,
            container_types=container_types,
            dg_range=dg_range,
            setup=setup,
            rules=rules,
            progress_callback=update_progress
        )

        # Store results in session state
        st.session_state.sizing_results = results_df

        progress_bar.progress(1.0)
        status_text.text("Simulation complete!")

        st.success(f"Completed {len(results_df)} configurations!")

    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


# =============================================================================
# RESULTS TABLE
# =============================================================================

if 'sizing_results' in st.session_state and st.session_state.sizing_results is not None:
    results_df = st.session_state.sizing_results

    st.divider()
    st.subheader("Simulation Results")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_100_delivery = st.checkbox("Show only 100% delivery", value=False, key='filter_100')
    with col2:
        filter_zero_dg = st.checkbox("Show only zero DG hours", value=False, key='filter_zero_dg')
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=['Delivery %', 'BESS (MWh)', 'Wastage %', 'Green %', 'DG Hrs'],
            index=0,
            key='sort_by_select'
        )

    # Apply filters
    filtered_df = results_df.copy()
    if filter_100_delivery:
        filtered_df = filtered_df[filtered_df['Delivery %'] >= 99.9]
    if filter_zero_dg:
        filtered_df = filtered_df[filtered_df['DG Hrs'] == 0]

    # Sort
    ascending = sort_by in ['BESS (MWh)', 'Wastage %', 'DG Hrs']
    filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)

    # Display
    st.dataframe(
        filtered_df,
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

    st.caption(f"Showing {len(filtered_df)} of {len(results_df)} configurations")

    # Quick insights
    if len(filtered_df) > 0:
        st.markdown("---")
        st.markdown("**Quick Insights:**")

        # Find optimal configs
        full_delivery = filtered_df[filtered_df['Delivery %'] >= 99.9]

        if len(full_delivery) > 0:
            # Smallest BESS with 100% delivery
            min_bess = full_delivery.loc[full_delivery['BESS (MWh)'].idxmin()]
            st.success(f"Smallest BESS for 100% delivery: **{min_bess['BESS (MWh)']:.0f} MWh** ({min_bess['Duration (hr)']}-hr) with {min_bess['Wastage %']:.1f}% wastage")

            # Lowest wastage with 100% delivery
            min_waste = full_delivery.loc[full_delivery['Wastage %'].idxmin()]
            if min_waste['BESS (MWh)'] != min_bess['BESS (MWh)']:
                st.info(f"Lowest wastage with 100% delivery: **{min_waste['BESS (MWh)']:.0f} MWh** ({min_waste['Duration (hr)']}-hr) with {min_waste['Wastage %']:.1f}% wastage")
        else:
            max_delivery = filtered_df.loc[filtered_df['Delivery %'].idxmax()]
            st.warning(f"No configuration achieves 100% delivery. Best: **{max_delivery['Delivery %']:.1f}%** with {max_delivery['BESS (MWh)']:.0f} MWh")


# =============================================================================
# NAVIGATION
# =============================================================================

st.divider()

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back to Rules", use_container_width=True):
        st.switch_page("pages/Step2_Rules.py")

with col3:
    has_results = 'sizing_results' in st.session_state and st.session_state.sizing_results is not None
    if st.button("Next → Results", type="primary" if has_results else "secondary",
                 disabled=not has_results, use_container_width=True):
        mark_step_completed(3)
        st.switch_page("pages/Step4_Results.py")


# =============================================================================
# SIDEBAR SUMMARY
# =============================================================================

with st.sidebar:
    st.markdown("### 📋 Configuration Summary")

    st.markdown("**From Step 1:**")
    st.markdown(f"- Load: {setup['load_mw']} MW ({setup['load_mode']})")
    st.markdown(f"- Containers: {', '.join([CONTAINER_SPECS[ct]['label'] for ct in container_types])}")
    st.markdown(f"- Efficiency: {setup['bess_efficiency']}%")
    st.markdown(f"- SOC: {setup['bess_min_soc']}-{setup['bess_max_soc']}%")

    st.markdown("---")
    st.markdown("**From Step 2:**")
    if dg_enabled:
        st.markdown(f"- DG: Enabled")
        st.markdown(f"- DG Timing: {rules.get('dg_timing', 'anytime')}")
        st.markdown(f"- DG Trigger: {rules.get('dg_trigger', 'reactive')}")
    else:
        st.markdown("- DG: Disabled")

    st.markdown("---")
    st.markdown("**Step 3 Range:**")
    st.markdown(f"- BESS: {cap_min}-{cap_max} MWh")
    if dg_enabled:
        st.markdown(f"- DG: {dg_min}-{dg_max} MW")
    st.markdown(f"- Configs: {total_configs}")
