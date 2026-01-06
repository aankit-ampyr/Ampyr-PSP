"""
Step 3: Sizing Range

Define what configurations to simulate:
- BESS capacity range
- Duration classes
- DG capacity range (if enabled)
"""

import streamlit as st
import numpy as np
import pandas as pd

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    update_wizard_section, set_current_step, mark_step_completed,
    validate_step_3, get_step_status, can_navigate_to_step,
    count_configurations, estimate_simulation_time, build_simulation_params
)
from src.template_inference import get_template_info
from src.load_builder import build_load_profile
from src.dispatch_engine import SimulationParams, run_simulation, calculate_metrics


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Sizing Range",
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
        ("5", "Analysis", get_step_status(5)),
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


def run_batch_simulation(progress_bar, status_text):
    """Run batch simulation for all configurations."""
    state = get_wizard_state()
    setup = state['setup']
    rules = state['rules']
    sizing = state['sizing']

    # Build load profile
    load_params = {
        'mw': setup['load_mw'],
        'start': setup.get('load_day_start', 6),
        'end': setup.get('load_day_end', 18),
        'windows': setup.get('load_windows', []),
        'data': setup.get('load_csv_data'),
        # Seasonal parameters
        'start_month': setup.get('load_season_start', 4),
        'end_month': setup.get('load_season_end', 10),
        'day_start': setup.get('load_season_day_start', 8),
        'day_end': setup.get('load_season_day_end', 0),
    }
    load_profile = build_load_profile(setup['load_mode'], load_params)

    # Load solar profile from wizard state
    solar_source = setup.get('solar_source', 'default')
    solar_profile = None

    if solar_source == 'upload' and setup.get('solar_csv_data') is not None:
        # Use uploaded solar profile
        solar_profile = setup['solar_csv_data']
        if isinstance(solar_profile, list):
            solar_profile = solar_profile[:8760] if len(solar_profile) >= 8760 else solar_profile
    elif 'default_solar_profile' in st.session_state and st.session_state.default_solar_profile is not None:
        # Use default solar profile from session state
        solar_data = st.session_state.default_solar_profile
        solar_profile = solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
    else:
        # Fallback: try loading default solar profile
        try:
            from src.data_loader import load_solar_profile
            solar_data = load_solar_profile()
            if solar_data is not None and len(solar_data) > 0:
                solar_profile = solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
        except Exception:
            pass

    # If still no solar profile, use synthetic curve
    if solar_profile is None or len(solar_profile) == 0:
        solar_profile = [0] * 8760
        for h in range(8760):
            hour_of_day = h % 24
            if 6 <= hour_of_day <= 18:
                peak_hour = 12
                solar_profile[h] = setup['solar_capacity_mw'] * max(0, 1 - abs(hour_of_day - peak_hour) / 6) * 0.8

    # Get template
    template_id = rules['inferred_template']

    # Generate configurations
    configs = []
    cap_values = np.arange(
        sizing['capacity_min'],
        sizing['capacity_max'] + sizing['capacity_step'],
        sizing['capacity_step']
    )
    dur_values = sizing['durations']

    if setup['dg_enabled']:
        dg_values = np.arange(
            sizing['dg_min'],
            sizing['dg_max'] + sizing['dg_step'],
            sizing['dg_step']
        )
    else:
        dg_values = [0]

    for cap in cap_values:
        for dur in dur_values:
            for dg in dg_values:
                configs.append({
                    'capacity': cap,
                    'duration': dur,
                    'dg_capacity': dg,
                })

    # Run simulations
    results = []
    total = len(configs)

    for i, config in enumerate(configs):
        # Update progress
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Running {i + 1} of {total}...")

        # Build simulation params
        power = config['capacity'] / config['duration']

        params = SimulationParams(
            load_profile=load_profile.tolist(),
            solar_profile=solar_profile,
            bess_capacity=config['capacity'],
            bess_charge_power=power,
            bess_discharge_power=power,
            bess_efficiency=setup['bess_efficiency'],
            bess_min_soc=setup['bess_min_soc'],
            bess_max_soc=setup['bess_max_soc'],
            bess_initial_soc=setup['bess_initial_soc'],
            bess_daily_cycle_limit=setup['bess_daily_cycle_limit'],
            bess_enforce_cycle_limit=setup['bess_enforce_cycle_limit'],
            dg_enabled=setup['dg_enabled'],
            dg_capacity=config['dg_capacity'],
            dg_charges_bess=rules['dg_charges_bess'],
            dg_load_priority=rules.get('dg_load_priority', 'bess_first'),
            dg_takeover_mode=rules.get('dg_takeover_mode', False),
            night_start_hour=rules['night_start'],
            night_end_hour=rules['night_end'],
            day_start_hour=rules['day_start'],
            day_end_hour=rules['day_end'],
            blackout_start_hour=rules['blackout_start'],
            blackout_end_hour=rules['blackout_end'],
            dg_soc_on_threshold=rules['soc_on_threshold'],
            dg_soc_off_threshold=rules['soc_off_threshold'],
            # Fuel model parameters
            dg_fuel_curve_enabled=setup.get('dg_fuel_curve_enabled', False),
            dg_fuel_f0=setup.get('dg_fuel_f0', 0.03),
            dg_fuel_f1=setup.get('dg_fuel_f1', 0.22),
            dg_fuel_flat_rate=setup.get('dg_fuel_flat_rate', 0.25),
            # Cycle charging parameters
            cycle_charging_enabled=rules.get('cycle_charging_enabled', False),
            cycle_charging_min_load_pct=rules.get('cycle_charging_min_load_pct', 70.0),
            cycle_charging_off_soc=rules.get('cycle_charging_off_soc', 80.0),
        )

        # Run simulation
        hourly_results = run_simulation(params, template_id, num_hours=8760)
        metrics = calculate_metrics(hourly_results, params)

        # Store result
        results.append({
            'bess_mwh': config['capacity'],
            'duration_hrs': config['duration'],
            'power_mw': power,
            'dg_mw': config['dg_capacity'],
            'delivery_pct': metrics.pct_full_delivery,
            'wastage_pct': metrics.pct_solar_curtailed,
            'wastage_load_pct': metrics.pct_solar_curtailed_load_hours,  # Wastage during load hours only
            'delivery_hours': metrics.hours_full_delivery,
            'load_hours': metrics.hours_with_load,  # Total hours with load demand
            'green_hours': metrics.hours_green_delivery,
            'dg_hours': metrics.dg_runtime_hours,
            'dg_starts': metrics.dg_starts,
            'bess_cycles': metrics.bess_equivalent_cycles,
            'fuel_consumed': metrics.total_fuel_consumed,  # Liters
            'cycle_charging_hours': metrics.cycle_charging_hours,
            'unserved_mwh': metrics.total_unserved,
        })

    return pd.DataFrame(results)


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("📐 Sizing Range")
st.markdown("### Step 3 of 4: Define Configuration Range")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']
sizing = state['sizing']

dg_enabled = setup['dg_enabled']


# =============================================================================
# SIZING CONFIGURATION
# =============================================================================

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔋 Battery Capacity Range")

    cap_min = st.number_input(
        "Minimum (MWh)",
        min_value=10.0,
        max_value=1000.0,
        value=float(sizing['capacity_min']),
        step=10.0,
        key='cap_min_input'
    )
    update_wizard_state('sizing', 'capacity_min', cap_min)

    cap_max = st.number_input(
        "Maximum (MWh)",
        min_value=cap_min,
        max_value=2000.0,
        value=max(float(sizing['capacity_max']), cap_min),
        step=10.0,
        key='cap_max_input'
    )
    update_wizard_state('sizing', 'capacity_max', cap_max)

    step_options = [5.0, 10.0, 25.0, 50.0, 100.0]
    cap_step = st.selectbox(
        "Step Size (MWh)",
        options=step_options,
        index=step_options.index(sizing['capacity_step']) if sizing['capacity_step'] in step_options else 1,
        key='cap_step_select'
    )
    update_wizard_state('sizing', 'capacity_step', cap_step)

    # Duration classes
    st.markdown("### ⏱️ Duration Classes")
    st.caption("Power is auto-calculated: Power = Capacity / Duration")

    duration_options = sizing['duration_options']
    selected_durations = []

    dur_cols = st.columns(len(duration_options))
    for i, dur in enumerate(duration_options):
        with dur_cols[i]:
            checked = st.checkbox(
                f"{dur}-hr",
                value=dur in sizing['durations'],
                key=f'dur_{dur}_check'
            )
            if checked:
                selected_durations.append(dur)

    update_wizard_state('sizing', 'durations', selected_durations)

    if not selected_durations:
        st.error("Select at least one duration class")

with col2:
    if dg_enabled:
        st.markdown("### ⛽ Generator Capacity Range")

        dg_min = st.number_input(
            "Minimum (MW)",
            min_value=0.0,
            max_value=100.0,
            value=float(sizing['dg_min']),
            step=5.0,
            key='dg_min_input'
        )
        update_wizard_state('sizing', 'dg_min', dg_min)

        dg_max = st.number_input(
            "Maximum (MW)",
            min_value=dg_min,
            max_value=200.0,
            value=max(float(sizing['dg_max']), dg_min),
            step=5.0,
            key='dg_max_input'
        )
        update_wizard_state('sizing', 'dg_max', dg_max)

        dg_step = st.selectbox(
            "Step Size (MW)",
            options=[5.0, 10.0, 20.0],
            index=[5.0, 10.0, 20.0].index(sizing['dg_step']) if sizing['dg_step'] in [5.0, 10.0, 20.0] else 0,
            key='dg_step_select'
        )
        update_wizard_state('sizing', 'dg_step', dg_step)
    else:
        st.info("Generator is disabled. Only Solar + BESS configurations will be tested.")

    # Configuration summary
    st.markdown("### 📊 Simulation Summary")

    num_configs = count_configurations()
    est_time = estimate_simulation_time()

    st.metric("Total Configurations", f"{num_configs:,}")
    st.metric("Estimated Time", est_time)

    if num_configs > 10000:
        st.warning("⚠️ Large number of configurations. Consider reducing range or increasing step size.")
    elif num_configs > 50000:
        st.error("❌ Too many configurations. Please reduce the range.")


st.divider()


# =============================================================================
# VALIDATION & RUN
# =============================================================================

is_valid, errors = validate_step_3()

if errors:
    for error in errors:
        if error.startswith("Warning"):
            st.warning(error)
        else:
            st.error(error)


# Navigation
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back to Rules", width='stretch'):
        st.switch_page("pages/9_📋_Step2_Rules.py")

with col3:
    run_button = st.button(
        "🚀 Run Simulation",
        type="primary",
        disabled=not is_valid,
        width='stretch'
    )

if run_button:
    st.markdown("---")
    st.markdown("### Running Simulations...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        results_df = run_batch_simulation(progress_bar, status_text)

        # Store results
        update_wizard_state('results', 'simulation_results', results_df)

        # Calculate ranked recommendations
        from utils.metrics import calculate_ranked_recommendations
        ranked = calculate_ranked_recommendations(results_df)
        update_wizard_state('results', 'ranked_recommendations', ranked)

        status_text.text("✅ Simulation complete!")
        st.success(f"Completed {len(results_df)} configurations")

        # Mark step complete and navigate
        mark_step_completed(3)

        if st.button("View Results →", type="primary"):
            st.switch_page("pages/11_📊_Step4_Results.py")

    except Exception as e:
        st.error(f"Simulation error: {e}")
        import traceback
        st.code(traceback.format_exc())


# Sidebar summary
with st.sidebar:
    st.markdown("### 📋 Configuration Summary")

    # From previous steps
    st.markdown("**Step 1 - Setup:**")
    st.markdown(f"- Load: {setup['load_mw']} MW")
    st.markdown(f"- Solar: {setup['solar_capacity_mw']} MWp")

    st.markdown("**Step 2 - Rules:**")
    template_info = get_template_info(rules['inferred_template'])
    st.markdown(f"- Strategy: {template_info['name']}")

    st.markdown("---")

    st.markdown("**Step 3 - Sizing:**")
    st.markdown(f"- BESS: {sizing['capacity_min']}-{sizing['capacity_max']} MWh")
    st.markdown(f"- Durations: {sizing['durations']}")
    if dg_enabled:
        st.markdown(f"- DG: {sizing['dg_min']}-{sizing['dg_max']} MW")
