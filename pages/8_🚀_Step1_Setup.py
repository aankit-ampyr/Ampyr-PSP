"""
Step 1: System Setup

Define the energy system being evaluated:
- Load profile (CSV or Load Builder)
- Solar profile
- BESS parameters
- DG enabled/disabled
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    update_wizard_section, set_current_step, mark_step_completed,
    validate_step_1, get_step_status
)
from src.load_builder import (
    build_load_profile, analyze_load_profile, validate_load_csv,
    validate_solar_csv, analyze_solar_profile,
    get_load_sparkline_data, LOAD_PRESETS,
    calculate_seasonal_stats, MONTH_NAMES_FULL
)
from src.data_loader import load_solar_profile


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Setup",
    page_icon="🚀",
    layout="wide"
)

# Initialize wizard state
init_wizard_state()
set_current_step(1)


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


def create_load_preview_chart(load: np.ndarray) -> go.Figure:
    """Create a daily load pattern preview chart."""
    # Calculate hourly averages for typical day
    hours = np.arange(len(load)) % 24
    hourly_avg = [np.mean(load[hours == h]) for h in range(24)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(24)),
        y=hourly_avg,
        marker_color='#1f77b4',
        name='Load'
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Hour of Day",
        yaxis_title="MW",
        showlegend=False,
        xaxis=dict(tickmode='array', tickvals=list(range(0, 24, 3))),
    )

    return fig


def create_solar_preview_chart(solar: np.ndarray) -> go.Figure:
    """Create a daily solar generation pattern preview chart."""
    # Calculate hourly averages for typical day
    hours = np.arange(len(solar)) % 24
    hourly_avg = [np.mean(solar[hours == h]) for h in range(24)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(24)),
        y=hourly_avg,
        marker_color='#f4a460',  # Sandy brown for solar
        name='Solar'
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Hour of Day",
        yaxis_title="MW",
        showlegend=False,
        xaxis=dict(tickmode='array', tickvals=list(range(0, 24, 3))),
    )

    return fig


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("🚀 BESS & DG Sizing Tool")
st.markdown("### Step 1 of 4: System Setup")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']


# =============================================================================
# LOAD PROFILE SECTION
# =============================================================================

st.subheader("📊 Load Profile")

load_source = st.radio(
    "How do you want to define the load?",
    options=['builder', 'csv'],
    format_func=lambda x: "Use Load Builder" if x == 'builder' else "Upload CSV",
    horizontal=True,
    key='load_source_radio'
)

if load_source == 'builder':
    # Load Builder Mode
    col1, col2 = st.columns([1, 1])

    with col1:
        load_options = ['constant', 'day_only', 'night_only', 'seasonal', 'custom']
        current_mode = setup.get('load_mode', 'constant')
        current_index = load_options.index(current_mode) if current_mode in load_options else 0

        load_mode = st.selectbox(
            "Load Pattern",
            options=load_options,
            index=current_index,
            format_func=lambda x: {
                'constant': 'Constant (24/7)',
                'day_only': 'Day Only',
                'night_only': 'Night Only',
                'seasonal': 'Seasonal Pattern',
                'custom': 'Custom Windows'
            }.get(x, x),
            key='load_mode_select'
        )
        update_wizard_state('setup', 'load_mode', load_mode)

        load_mw = st.number_input(
            "Load (MW)",
            min_value=1.0,
            max_value=500.0,
            value=float(setup['load_mw']),
            step=5.0,
            key='load_mw_input'
        )
        update_wizard_state('setup', 'load_mw', load_mw)

    with col2:
        if load_mode == 'day_only':
            day_start = st.slider(
                "Day Start Hour",
                min_value=0, max_value=23,
                value=setup['load_day_start'],
                key='day_start_slider'
            )
            day_end = st.slider(
                "Day End Hour",
                min_value=0, max_value=23,
                value=setup['load_day_end'],
                key='day_end_slider'
            )
            update_wizard_state('setup', 'load_day_start', day_start)
            update_wizard_state('setup', 'load_day_end', day_end)

        elif load_mode == 'night_only':
            night_start = st.slider(
                "Night Start Hour",
                min_value=0, max_value=23,
                value=setup['load_night_start'],
                key='night_start_slider'
            )
            night_end = st.slider(
                "Night End Hour",
                min_value=0, max_value=23,
                value=setup['load_night_end'],
                key='night_end_slider'
            )
            update_wizard_state('setup', 'load_night_start', night_start)
            update_wizard_state('setup', 'load_night_end', night_end)

        elif load_mode == 'seasonal':
            st.markdown("**Active Months:**")
            season_start = st.selectbox(
                "From",
                options=list(range(1, 13)),
                format_func=lambda x: MONTH_NAMES_FULL[x-1],
                index=setup.get('load_season_start', 4) - 1,
                key='season_start_select'
            )
            season_end = st.selectbox(
                "To",
                options=list(range(1, 13)),
                format_func=lambda x: MONTH_NAMES_FULL[x-1],
                index=setup.get('load_season_end', 10) - 1,
                key='season_end_select'
            )
            update_wizard_state('setup', 'load_season_start', season_start)
            update_wizard_state('setup', 'load_season_end', season_end)

            st.markdown("**Daily Window:**")
            # Time options with readable labels
            hour_options = list(range(24))
            day_start_hour = st.selectbox(
                "Start Time",
                options=hour_options,
                format_func=lambda x: f"{x:02d}:00",
                index=setup.get('load_season_day_start', 8),
                key='season_day_start_select'
            )
            # End time: 1-23 plus 0 (midnight) at the end
            end_options = list(range(1, 24)) + [0]
            current_end = setup.get('load_season_day_end', 0)
            end_index = end_options.index(current_end) if current_end in end_options else len(end_options) - 1
            day_end_hour = st.selectbox(
                "End Time",
                options=end_options,
                format_func=lambda x: "Midnight (00:00)" if x == 0 else f"{x:02d}:00",
                index=end_index,
                key='season_day_end_select'
            )
            update_wizard_state('setup', 'load_season_day_start', day_start_hour)
            update_wizard_state('setup', 'load_season_day_end', day_end_hour)

            # Preview stats
            stats = calculate_seasonal_stats(season_start, season_end, day_start_hour, day_end_hour)
            st.info(f"**{stats['description']}**")

        elif load_mode == 'custom':
            st.info("Define custom time windows below")
            # Simplified: use two windows
            w1_start = st.number_input("Window 1 Start", 0, 23, 6, key='w1_start')
            w1_end = st.number_input("Window 1 End", 0, 23, 12, key='w1_end')
            w1_mw = st.number_input("Window 1 MW", 1.0, 500.0, 25.0, key='w1_mw')

            w2_start = st.number_input("Window 2 Start", 0, 23, 14, key='w2_start')
            w2_end = st.number_input("Window 2 End", 0, 23, 20, key='w2_end')
            w2_mw = st.number_input("Window 2 MW", 1.0, 500.0, 25.0, key='w2_mw')

            windows = [
                {'start': w1_start, 'end': w1_end, 'mw': w1_mw},
                {'start': w2_start, 'end': w2_end, 'mw': w2_mw},
            ]
            update_wizard_state('setup', 'load_windows', windows)

    # Build and preview load profile
    if load_mode == 'constant':
        params = {'mw': load_mw}
    elif load_mode == 'day_only':
        params = {'mw': load_mw, 'start': setup['load_day_start'], 'end': setup['load_day_end']}
    elif load_mode == 'night_only':
        params = {'mw': load_mw, 'start': setup['load_night_start'], 'end': setup['load_night_end']}
    elif load_mode == 'seasonal':
        params = {
            'mw': load_mw,
            'start_month': setup.get('load_season_start', 4),
            'end_month': setup.get('load_season_end', 10),
            'day_start': setup.get('load_season_day_start', 8),
            'day_end': setup.get('load_season_day_end', 0)
        }
    elif load_mode == 'custom':
        params = {'windows': setup['load_windows']}
    else:
        params = {'mw': load_mw}

    load_profile = build_load_profile(load_mode, params)
    stats = analyze_load_profile(load_profile)

    # Preview
    st.markdown("**Preview:**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Energy", f"{stats['total_energy_mwh']:,.0f} MWh/yr")
    col2.metric("Peak Load", f"{stats['peak_mw']:.1f} MW")
    # Show load hours with context (for seasonal loads, show vs 8760)
    if stats['load_hours'] < 8760:
        load_pct = stats['load_hours'] / 87.6
        col3.metric("Load Hours", f"{stats['load_hours']:,}", f"{load_pct:.1f}% of year")
    else:
        col3.metric("Load Hours", f"{stats['load_hours']:,}", "24/7")

    st.plotly_chart(create_load_preview_chart(load_profile), width='stretch')

else:
    # CSV Upload Mode
    update_wizard_state('setup', 'load_mode', 'csv')

    uploaded_file = st.file_uploader(
        "Upload Load Profile CSV",
        type=['csv'],
        help="CSV with hourly load values (MW). Should have 8760 rows for full year.",
        key='load_csv_uploader'
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            is_valid, message, data = validate_load_csv(df)

            if is_valid:
                st.success(message)
                update_wizard_state('setup', 'load_csv_data', data)

                load_profile = build_load_profile('csv', {'data': data})
                stats = analyze_load_profile(load_profile)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Energy", f"{stats['total_energy_mwh']:,.0f} MWh/yr")
                col2.metric("Peak Load", f"{stats['peak_mw']:.1f} MW")
                col3.metric("Load Hours", f"{stats['load_hours']:,}")

                st.plotly_chart(create_load_preview_chart(load_profile), width='stretch')
            else:
                st.error(message)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    else:
        st.info("Please upload a CSV file with hourly load data")


st.divider()


# =============================================================================
# SOLAR PROFILE SECTION
# =============================================================================

st.subheader("☀️ Solar Profile")

# Load default solar profile once
if 'default_solar_profile' not in st.session_state:
    try:
        default_solar = load_solar_profile()
        if default_solar is not None and len(default_solar) > 0:
            st.session_state.default_solar_profile = default_solar
            st.session_state.default_solar_available = True
        else:
            st.session_state.default_solar_profile = None
            st.session_state.default_solar_available = False
    except Exception:
        st.session_state.default_solar_profile = None
        st.session_state.default_solar_available = False

solar_source = st.radio(
    "Solar generation profile source:",
    options=['default', 'upload'],
    format_func=lambda x: "Use Default Profile (Inputs/Solar Profile.csv)" if x == 'default' else "Upload Custom CSV",
    horizontal=True,
    key='solar_source_radio'
)
update_wizard_state('setup', 'solar_source', solar_source)

# Active solar profile variable
active_solar_profile = None

if solar_source == 'default':
    # Use default solar profile
    if st.session_state.default_solar_available:
        active_solar_profile = st.session_state.default_solar_profile
        st.success(f"✅ Default solar profile loaded: {len(active_solar_profile)} hours")
    else:
        st.error("❌ Default solar profile not found. Please upload a custom profile or check that 'Inputs/Solar Profile.csv' exists.")

else:
    # Upload custom solar profile
    uploaded_solar = st.file_uploader(
        "Upload Solar Profile CSV",
        type=['csv'],
        help="CSV with hourly solar generation values (MW). Should have 8760 rows for full year.",
        key='solar_csv_uploader'
    )

    if uploaded_solar is not None:
        try:
            df = pd.read_csv(uploaded_solar)
            is_valid, message, data = validate_solar_csv(df)

            if is_valid:
                st.success(message)
                update_wizard_state('setup', 'solar_csv_data', data.tolist())  # Store as list for JSON serialization
                active_solar_profile = data
            else:
                st.error(message)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    else:
        # Check if we have previously uploaded data
        stored_solar = setup.get('solar_csv_data')
        if stored_solar is not None:
            active_solar_profile = np.array(stored_solar)
            st.info(f"Using previously uploaded solar profile: {len(active_solar_profile)} hours")
        else:
            st.info("Please upload a CSV file with hourly solar generation data")

# Display solar profile metrics and preview
if active_solar_profile is not None and len(active_solar_profile) > 0:
    stats = analyze_solar_profile(active_solar_profile)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Generation", f"{stats['total_generation_mwh']:,.0f} MWh/yr")
    col2.metric("Peak Generation", f"{stats['peak_mw']:.1f} MW")
    col3.metric("Avg Generation", f"{stats['mean_mw']:.1f} MW")
    col4.metric("Generation Hours", f"{stats['generation_hours']:,}/8760")

    st.plotly_chart(create_solar_preview_chart(active_solar_profile), width='stretch')

    # Store the active solar profile for use in simulation
    if solar_source == 'default':
        update_wizard_state('setup', 'solar_csv_data', None)  # Clear uploaded data when using default
else:
    st.warning("⚠️ No valid solar profile available. Simulation requires a solar profile.")


st.divider()


# =============================================================================
# BESS PARAMETERS SECTION
# =============================================================================

st.subheader("🔋 Battery (BESS)")

col1, col2, col3 = st.columns(3)

with col1:
    bess_efficiency = st.slider(
        "Round-trip Efficiency (%)",
        min_value=70,
        max_value=95,
        value=int(setup['bess_efficiency']),
        step=1,
        key='bess_efficiency_slider'
    )
    update_wizard_state('setup', 'bess_efficiency', float(bess_efficiency))

with col2:
    bess_min_soc = st.slider(
        "Min State of Charge (%)",
        min_value=0,
        max_value=50,
        value=int(setup['bess_min_soc']),
        step=5,
        key='bess_min_soc_slider'
    )
    update_wizard_state('setup', 'bess_min_soc', float(bess_min_soc))

    bess_max_soc = st.slider(
        "Max State of Charge (%)",
        min_value=50,
        max_value=100,
        value=int(setup['bess_max_soc']),
        step=5,
        key='bess_max_soc_slider'
    )
    update_wizard_state('setup', 'bess_max_soc', float(bess_max_soc))

with col3:
    bess_initial_soc = st.slider(
        "Initial State of Charge (%)",
        min_value=int(bess_min_soc),
        max_value=int(bess_max_soc),
        value=min(max(int(setup['bess_initial_soc']), int(bess_min_soc)), int(bess_max_soc)),
        step=5,
        key='bess_initial_soc_slider'
    )
    update_wizard_state('setup', 'bess_initial_soc', float(bess_initial_soc))

# Advanced BESS settings
with st.expander("⚙️ Advanced BESS Settings"):
    col1, col2 = st.columns(2)

    with col1:
        bess_cycle_limit = st.number_input(
            "Daily Cycle Limit",
            min_value=0.5,
            max_value=3.0,
            value=float(setup['bess_daily_cycle_limit']),
            step=0.1,
            key='bess_cycle_limit_input'
        )
        update_wizard_state('setup', 'bess_daily_cycle_limit', bess_cycle_limit)

    with col2:
        bess_enforce_limit = st.checkbox(
            "Enforce Cycle Limit",
            value=setup['bess_enforce_cycle_limit'],
            help="If enabled, BESS will stop discharging when daily cycle limit is reached",
            key='bess_enforce_limit_check'
        )
        update_wizard_state('setup', 'bess_enforce_cycle_limit', bess_enforce_limit)


st.divider()


# =============================================================================
# GENERATOR (DG) SECTION
# =============================================================================

st.subheader("⛽ Generator (DG)")

dg_enabled = st.checkbox(
    "Include diesel/gas generator in system",
    value=setup['dg_enabled'],
    key='dg_enabled_check'
)
update_wizard_state('setup', 'dg_enabled', dg_enabled)

if dg_enabled:
    col1, col2 = st.columns(2)

    with col1:
        dg_operating_mode = st.radio(
            "DG Operating Mode",
            options=['binary', 'variable'],
            format_func=lambda x: "Binary (100% capacity or OFF)" if x == 'binary' else "Variable (above minimum load)",
            index=0 if setup.get('dg_operating_mode', 'binary') == 'binary' else 1,
            help="Binary: DG runs at full capacity only. Variable: DG can run at any load above minimum.",
            key='dg_operating_mode_radio'
        )
        update_wizard_state('setup', 'dg_operating_mode', dg_operating_mode)

        # Show minimum load slider only for variable mode
        if dg_operating_mode == 'variable':
            dg_min_load = st.slider(
                "Minimum Stable Load (%)",
                min_value=10,
                max_value=50,
                value=int(setup['dg_min_load_pct']),
                step=5,
                help="DG cannot run below this percentage of capacity",
                key='dg_min_load_slider'
            )
            update_wizard_state('setup', 'dg_min_load_pct', float(dg_min_load))
        else:
            # Binary mode: internally set to 100%
            update_wizard_state('setup', 'dg_min_load_pct', 100.0)
            st.caption("ℹ️ In binary mode, DG will only run at 100% capacity when needed")

    with col2:
        st.info("DG capacity will be configured in Step 3 (Sizing)")
else:
    st.info("No generator in this configuration. System will be Solar + BESS only.")


st.divider()


# =============================================================================
# VALIDATION & NAVIGATION
# =============================================================================

is_valid, errors = validate_step_1()

if errors:
    for error in errors:
        if error.startswith("Warning"):
            st.warning(error)
        else:
            st.error(error)

col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    if st.button("⚡ Quick Analysis", disabled=not is_valid, width='stretch',
                 help="Skip the wizard - configure and analyze in one page"):
        mark_step_completed(1)
        st.switch_page("pages/13_⚡_Quick_Analysis.py")

with col3:
    if st.button("Next → Dispatch Rules", type="primary", disabled=not is_valid, width='stretch'):
        mark_step_completed(1)
        st.switch_page("pages/9_📋_Step2_Rules.py")

# Summary box
with st.sidebar:
    st.markdown("### 📋 Configuration Summary")
    st.markdown(f"**Load:** {setup['load_mw']} MW ({setup['load_mode']})")
    solar_src = setup.get('solar_source', 'default')
    st.markdown(f"**Solar:** {'Default' if solar_src == 'default' else 'Uploaded'} profile")
    st.markdown(f"**BESS Efficiency:** {setup['bess_efficiency']}%")
    st.markdown(f"**SOC Range:** {setup['bess_min_soc']}-{setup['bess_max_soc']}%")
    if setup['dg_enabled']:
        dg_mode = setup.get('dg_operating_mode', 'binary')
        if dg_mode == 'binary':
            st.markdown("**DG:** Binary (100% or OFF)")
        else:
            st.markdown(f"**DG:** Variable (≥{setup['dg_min_load_pct']:.0f}%)")
    else:
        st.markdown("**DG:** Disabled")
