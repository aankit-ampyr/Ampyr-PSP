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
from src.data_loader import load_solar_profile, list_solar_profiles, load_solar_profile_by_name


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
        ("1", "Setup", 'current'),
        ("2", "Rules", get_step_status(2)),
        ("2b", "Financial Setup", get_step_status(2)),
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


def create_monthly_generation_chart(solar: np.ndarray) -> go.Figure:
    """Create a monthly solar generation bar chart."""
    import pandas as pd

    # Create datetime index for a full year (non-leap)
    start_date = pd.Timestamp('2024-01-01')
    date_range = pd.date_range(start=start_date, periods=len(solar), freq='h')

    # Create DataFrame with solar data
    df = pd.DataFrame({'solar_mw': solar}, index=date_range)

    # Calculate monthly totals (MWh = MW * 1 hour)
    monthly_generation = df.groupby(df.index.month)['solar_mw'].sum()

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=month_names,
        y=monthly_generation.values,
        marker_color='#f4a460',  # Sandy brown for solar
        name='Generation',
        text=[f'{v:,.0f}' for v in monthly_generation.values],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis_title="Month",
        yaxis_title="MWh",
        showlegend=False,
        title=dict(text="Monthly Solar Generation", font=dict(size=14)),
    )

    return fig


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("🚀 BESS & DG Sizing Tool")
st.markdown("### Step 1 of 7: System Setup")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']


# =============================================================================
# OPERATIONAL SECTION (Load / Solar / Storable / Battery / DG)
# =============================================================================

st.markdown("## ⚙️ Operational")
st.caption("Physical system configuration — what's being built, how it dispatches.")


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

# Get available solar profiles from Inputs folder
available_profiles = list_solar_profiles()

# Determine source options based on available profiles
if len(available_profiles) > 0:
    source_options = ['inputs', 'upload']
    source_labels = {
        'inputs': f"Select from Inputs folder ({len(available_profiles)} file{'s' if len(available_profiles) > 1 else ''})",
        'upload': "Upload Custom CSV"
    }
else:
    source_options = ['upload']
    source_labels = {'upload': "Upload Custom CSV"}

# Get current source from state, default to 'inputs' if available
current_source = setup.get('solar_source', 'inputs' if len(available_profiles) > 0 else 'upload')
if current_source == 'default':
    current_source = 'inputs'  # Migrate old 'default' to 'inputs'
if current_source not in source_options:
    current_source = source_options[0]

solar_source = st.radio(
    "Solar generation profile source:",
    options=source_options,
    format_func=lambda x: source_labels[x],
    horizontal=True,
    index=source_options.index(current_source),
    key='solar_source_radio'
)
update_wizard_state('setup', 'solar_source', solar_source)

# Active solar profile variable
active_solar_profile = None

if solar_source == 'inputs':
    # Select from available profiles in Inputs folder
    if len(available_profiles) == 1:
        # Only one file - auto-select it
        selected_file = available_profiles[0][0]
        st.info(f"Using: **{available_profiles[0][1]}**")
    else:
        # Multiple files - show dropdown
        # Get previously selected file from state
        prev_selected = setup.get('solar_selected_file', available_profiles[0][0])
        # Validate it's still available
        available_filenames = [p[0] for p in available_profiles]
        if prev_selected not in available_filenames:
            prev_selected = available_profiles[0][0]

        selected_file = st.selectbox(
            "Select solar profile:",
            options=[p[0] for p in available_profiles],
            format_func=lambda x: next((p[1] for p in available_profiles if p[0] == x), x),
            index=available_filenames.index(prev_selected),
            key='solar_file_select'
        )

    # Store selected file
    update_wizard_state('setup', 'solar_selected_file', selected_file)

    # Load the selected profile
    solar_data = load_solar_profile_by_name(selected_file)
    if solar_data is not None and len(solar_data) > 0:
        active_solar_profile = solar_data
        st.success(f"✅ Loaded: {len(active_solar_profile)} hours")
    else:
        st.error(f"❌ Failed to load '{selected_file}'. Please check the file format.")

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

    # Monthly generation profile
    st.plotly_chart(create_monthly_generation_chart(active_solar_profile), width='stretch')

    # Store the active solar profile for use in simulation
    if solar_source == 'inputs':
        update_wizard_state('setup', 'solar_csv_data', None)  # Clear uploaded data when using Inputs folder

    # =========================================================================
    # CANONICAL PROFILE STORAGE — Step 1 is the single source of profile truth.
    # See decisions log A27. All downstream consumers (Step 3, Step 3a, Step 4,
    # Step 7) read `wizard['setup']['solar_profile_array']` directly rather
    # than re-loading from disk per-page. Eliminates loader/extension/length
    # drift surfaced repeatedly by the Step 3a smoke test loop.
    # =========================================================================
    active_array = np.asarray(active_solar_profile, dtype=float)

    # Pad to 8760 if needed (defensive — Option B fix makes data_loader return
    # 8760 already; this is a safety net for future uploads).
    if len(active_array) == 8759:
        active_array = np.concatenate([active_array, [active_array[-1]]])
    if len(active_array) >= 8760:
        active_array = active_array[:8760]

    # Profile-change signature → invalidates downstream caches on change.
    source_id = selected_file if solar_source == 'inputs' else 'upload'
    new_signature = (
        solar_source,
        source_id,
        round(float(active_array.max()), 4),
        round(float(active_array.sum()), 1),
    )
    old_signature = setup.get('solar_profile_signature')
    if old_signature != new_signature:
        # Clear all downstream caches that depend on the solar profile (spec §8
        # cache invalidation rules). Any cache derived from this profile is
        # now stale; force re-computation on next visit.
        for cache_key in (
            'sizing_results',
            'sizing_monthly_aggregates',
            'financial_results',
            'step7_pirr_result',
            'dispatch_monthly',
            'multiyear_monthly',
        ):
            st.session_state.pop(cache_key, None)
        update_wizard_state('setup', 'solar_profile_signature', new_signature)

    # Store the canonical 8760-element array for downstream consumers.
    update_wizard_state('setup', 'solar_profile_array', active_array.tolist())
else:
    st.warning("⚠️ No valid solar profile available. Simulation requires a solar profile.")


st.divider()


# =============================================================================
# STORABLE SOLAR CHART (Dynamic based on Load & Solar profiles)
# =============================================================================

# Determine if we have both profiles available
have_load_profile = False
have_solar_profile = active_solar_profile is not None and len(active_solar_profile) > 0

# Get load profile based on source
if load_source == 'builder':
    current_load_profile = load_profile
    have_load_profile = True
elif load_source == 'csv' and setup.get('load_csv_data') is not None:
    current_load_profile = build_load_profile('csv', {'data': setup['load_csv_data']})
    have_load_profile = True
else:
    current_load_profile = None

if have_load_profile and have_solar_profile:
    st.subheader("⚡ Storable Solar Analysis")
    st.caption("Excess solar available for battery storage after serving load")

    # Calculate storable solar
    solar_arr = np.array(active_solar_profile)
    load_arr = np.array(current_load_profile)

    # Ensure same length (use minimum)
    min_len = min(len(solar_arr), len(load_arr))
    solar_arr = solar_arr[:min_len]
    load_arr = load_arr[:min_len]

    storable_solar = np.maximum(solar_arr - load_arr, 0)

    # Summary metrics
    excess_hours = int(np.sum(storable_solar > 0))
    max_storable = float(storable_solar.max())
    total_storable = float(storable_solar.sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Storable", f"{max_storable:.2f} MW")
    col2.metric("Hours with Excess", f"{excess_hours:,}")
    col3.metric("Total Storable", f"{total_storable:,.0f} MWh")

    # Availability of max storable (as % of excess hours)
    if excess_hours > 0:
        hours_at_max = int(np.sum(storable_solar >= max_storable * 0.99))
        max_availability_pct = hours_at_max / excess_hours * 100
        col4.metric("Max Available", f"{max_availability_pct:.1f}%", f"{hours_at_max} hrs")
    else:
        col4.metric("Max Available", "N/A")

    # Create storable solar curve
    hours = np.arange(len(storable_solar))

    fig_storable = go.Figure()

    fig_storable.add_trace(go.Scatter(
        x=hours,
        y=storable_solar,
        mode='lines',
        name='Storable Solar',
        fill='tozeroy',
        fillcolor='rgba(255, 165, 0, 0.3)',
        line=dict(color='orange', width=1)
    ))

    fig_storable.add_hline(
        y=max_storable,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Max: {max_storable:.2f} MW"
    )

    fig_storable.update_layout(
        title="Storable Solar Throughout the Year (Solar - Load when positive)",
        xaxis_title="Hour of Year",
        yaxis_title="Storable Solar (MW)",
        height=350,
        margin=dict(l=40, r=20, t=40, b=40),
        hovermode='x unified'
    )

    st.plotly_chart(fig_storable, width='stretch')


st.divider()


# =============================================================================
# BESS PARAMETERS SECTION
# =============================================================================

st.subheader("🔋 Battery (BESS)")

# Container Type Selection
st.markdown("**Container Configuration**")
container_options = {
    '5mwh_2.5mw': '5 MWh / 2.5 MW (2-hour, 0.5C)',
    '5mwh_1.25mw': '5 MWh / 1.25 MW (4-hour, 0.25C)',
}
current_containers = setup.get('bess_container_types', ['5mwh_2.5mw', '5mwh_1.25mw'])

container_types = st.multiselect(
    "Standard container sizes to evaluate:",
    options=list(container_options.keys()),
    default=current_containers,
    format_func=lambda x: container_options[x],
    key='bess_container_types_multiselect'
)
update_wizard_state('setup', 'bess_container_types', container_types)

# Show specs for selected containers
if container_types:
    specs_text = []
    if '5mwh_2.5mw' in container_types:
        specs_text.append("2-hour: 5 MWh / 2.5 MW per container")
    if '5mwh_1.25mw' in container_types:
        specs_text.append("4-hour: 5 MWh / 1.25 MW per container")
    st.caption(" | ".join(specs_text))
else:
    st.warning("Please select at least one container type")

st.markdown("---")

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

    # Advanced DG Fuel Model
    with st.expander("⛽ Advanced DG Fuel Model"):
        fuel_curve_enabled = st.checkbox(
            "Use advanced fuel curve model",
            value=setup.get('dg_fuel_curve_enabled', False),
            help="Uses Willans line model: Fuel = F0 x P_rated + F1 x P_actual",
            key='fuel_curve_enabled_check'
        )
        update_wizard_state('setup', 'dg_fuel_curve_enabled', fuel_curve_enabled)

        if fuel_curve_enabled:
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                f0 = st.number_input(
                    "F0 (No-load coeff, L/hr/kW)",
                    min_value=0.01,
                    max_value=0.10,
                    value=float(setup.get('dg_fuel_f0', 0.03)),
                    step=0.005,
                    format="%.3f",
                    help="Fuel consumption per kW of rated capacity at zero load",
                    key='dg_f0_input'
                )
                update_wizard_state('setup', 'dg_fuel_f0', f0)

            with fcol2:
                f1 = st.number_input(
                    "F1 (Load coeff, L/kWh)",
                    min_value=0.15,
                    max_value=0.35,
                    value=float(setup.get('dg_fuel_f1', 0.22)),
                    step=0.01,
                    format="%.2f",
                    help="Fuel consumption per kWh of actual output",
                    key='dg_f1_input'
                )
                update_wizard_state('setup', 'dg_fuel_f1', f1)

            # Show efficiency table
            st.markdown("**Efficiency at Different Load Levels (25 MW DG):**")
            eff_data = []
            for load_pct in [25, 50, 75, 100]:
                p_actual_kw = 25000 * (load_pct / 100)
                fuel_rate = f0 * 25000 + f1 * p_actual_kw
                specific = fuel_rate / p_actual_kw if p_actual_kw > 0 else 0
                eff_data.append({
                    'Load': f"{load_pct}%",
                    'Output': f"{p_actual_kw/1000:.1f} MW",
                    'Fuel Rate': f"{fuel_rate:.0f} L/hr",
                    'Specific': f"{specific:.3f} L/kWh"
                })
            st.dataframe(pd.DataFrame(eff_data), hide_index=True, width='stretch')

            st.caption("Lower load = higher specific fuel consumption (less efficient)")
        else:
            flat_rate = st.number_input(
                "Flat fuel rate (L/kWh)",
                min_value=0.15,
                max_value=0.40,
                value=float(setup.get('dg_fuel_flat_rate', 0.25)),
                step=0.01,
                format="%.2f",
                key='dg_flat_rate_input'
            )
            update_wizard_state('setup', 'dg_fuel_flat_rate', flat_rate)

        fuel_price = st.number_input(
            "Fuel price ($/L)",
            min_value=0.50,
            max_value=5.00,
            value=float(setup.get('dg_fuel_price', 1.50)),
            step=0.10,
            format="%.2f",
            key='dg_fuel_price_input'
        )
        update_wizard_state('setup', 'dg_fuel_price', fuel_price)

else:
    st.info("No generator in this configuration. System will be Solar + BESS only.")


st.divider()


# =============================================================================
# COMMERCIAL SECTION (Price curves + inflation — feeds PIRR engine)
# =============================================================================

st.markdown("## 💼 Commercial")
st.caption(
    "Market price assumptions that drive financial outcomes. The PIRR engine "
    "consumes the **Nominal Merchant Curve**; vendor forecast curves "
    "(Baringa / Aurora) and the inflation curve compute into it. Real-terms "
    "uploads + variable CPI editing are planned for v2 — see "
    "[`docs/future_improvements/v2_price_and_inflation_curves.md`]"
    "(docs/future_improvements/v2_price_and_inflation_curves.md)."
)


# =============================================================================
# COMMERCIAL HELPERS + SHARED STATE (used by Raw, Inflation, Nominal panels)
# =============================================================================

financial = state.get('financial', {})

# Engine defaults — locked Burton-Leonard snapshots, used as the
# baseline display in each panel's 'default' mode.
try:
    from src.project_irr import (
        _DEFAULT_MERCHANT_PRICES_MONTHLY as _ENGINE_DEFAULT_CURVE,
        _DEFAULT_BARINGA_CURVE_REAL,
        _DEFAULT_AURORA_CURVE_REAL,
        _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR,
        _apply_inflation_to_real_curve,
        _select_raw_curve,
    )
except ImportError:
    _ENGINE_DEFAULT_CURVE = {}
    _DEFAULT_BARINGA_CURVE_REAL = {}
    _DEFAULT_AURORA_CURVE_REAL = {}
    _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR = {}
    _apply_inflation_to_real_curve = lambda r, c, s, b: r
    _select_raw_curve = lambda b, a, sel: b or a


def _curve_to_dataframe(curve_dict):
    """Convert {(year, month): price} to a DataFrame sorted by date."""
    if not curve_dict:
        return pd.DataFrame(columns=['date', 'year', 'month', 'price'])
    rows = []
    for (yr, mo), price in curve_dict.items():
        rows.append({
            'date': pd.Timestamp(year=int(yr), month=int(mo), day=1),
            'year': int(yr),
            'month': int(mo),
            'price': float(price),
        })
    df = pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    return df


def _render_price_curve_chart(curve_dict, title, y_label="£/MWh"):
    """Render a monthly + yearly-average price-curve chart."""
    df = _curve_to_dataframe(curve_dict)
    if df.empty:
        st.info("No price curve data to display.")
        return

    yearly_avg = df.groupby('year')['price'].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['price'],
        mode='lines', name='Monthly',
        line=dict(color='#3498db', width=1),
        opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(yearly_avg['year'].astype(str) + '-07-01'),
        y=yearly_avg['price'],
        mode='lines+markers', name='Yearly avg',
        line=dict(color='#e74c3c', width=2),
        marker=dict(size=5),
    ))
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Date",
        yaxis_title=y_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        hovermode='x unified',
    )
    st.plotly_chart(fig, width='stretch')

    # Summary stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Min", f"{df['price'].min():.1f}")
    c2.metric("Mean", f"{df['price'].mean():.1f}")
    c3.metric("Max", f"{df['price'].max():.1f}")
    c4.metric("Months", f"{len(df):,}")


def _compute_post_ppa_range(fin_dict):
    """Returns (first_key, last_key) for the post-PPA window as (year, month)
    tuples. Uses wizard financial state; falls back to engine D13 defaults
    when fields are missing (e.g. user hasn't visited Step 2b yet).
    """
    from datetime import date as _date

    cod = fin_dict.get('cod_date')
    if cod is None:
        cstart = fin_dict.get('construction_start')
        cmonths = int(fin_dict.get('construction_months') or 9)
        if cstart is not None:
            total = cstart.month - 1 + cmonths
            cod = _date(cstart.year + total // 12, total % 12 + 1, 1)
        else:
            cod = _date(2027, 7, 1)  # D13 engine default

    ppa_tenor = int(fin_dict.get('ppa_tenor_years') or 10)
    proj_life = int(fin_dict.get('project_life_years') or 35)
    first = (cod.year + ppa_tenor, cod.month)
    last = (cod.year + proj_life - 1, 12)
    return first, last


def _validate_curve_coverage(curve_dict, fin_dict):
    """Check curve_dict covers every (year, month) in the post-PPA window.

    Returns: (ok: bool, missing_count: int, first_missing_str: str | None,
              range_str: str)
    """
    first, last = _compute_post_ppa_range(fin_dict)
    first_y, first_m = first
    last_y, last_m = last

    missing = []
    y, m = first_y, first_m
    while (y, m) <= (last_y, last_m):
        if (y, m) not in curve_dict:
            missing.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    range_str = f"{first_y}-{first_m:02d} through {last_y}-{last_m:02d}"
    if not missing:
        return True, 0, None, range_str
    first_missing_str = f"{missing[0][0]}-{missing[0][1]:02d}"
    return False, len(missing), first_missing_str, range_str


# Compute the required coverage range upfront for the help text + validator.
_required_first, _required_last = _compute_post_ppa_range(financial)
_required_range_str = (
    f"{_required_first[0]}-{_required_first[1]:02d} through "
    f"{_required_last[0]}-{_required_last[1]:02d}"
)


def _parse_real_curve_csv(uploaded_file, vendor_label):
    """Parse a real-terms vendor CSV. Returns dict[(y,m), float] or None on
    error (with st.error rendered)."""
    try:
        df_u = pd.read_csv(uploaded_file)
        df_u.columns = [c.strip().lower() for c in df_u.columns]
        # Accept either price_gbp_mwh_real or price_gbp_mwh as the value column
        if 'price_gbp_mwh_real' in df_u.columns:
            value_col = 'price_gbp_mwh_real'
        elif 'price_gbp_mwh' in df_u.columns:
            value_col = 'price_gbp_mwh'
        else:
            st.error(
                f"{vendor_label} CSV must have a value column named "
                "`price_gbp_mwh_real` (preferred) or `price_gbp_mwh`. "
                f"Got: {', '.join(df_u.columns)}"
            )
            return None
        if 'year' not in df_u.columns or 'month' not in df_u.columns:
            st.error(f"{vendor_label} CSV must have `year` and `month` columns.")
            return None
        df_u = df_u.dropna(subset=['year', 'month', value_col])
        df_u['year'] = df_u['year'].astype(int)
        df_u['month'] = df_u['month'].astype(int)
        df_u[value_col] = df_u[value_col].astype(float)
        if ((df_u['month'] < 1) | (df_u['month'] > 12)).any():
            st.error(f"{vendor_label}: month values must be 1-12.")
            return None
        if (df_u[value_col] < 0).any():
            st.error(f"{vendor_label}: price values must be non-negative.")
            return None
        return {
            (int(r.year), int(r.month)): float(getattr(r, value_col))
            for r in df_u.itertuples()
        }
    except Exception as e:
        st.error(f"{vendor_label}: error reading CSV: {e}")
        return None


# =============================================================================
# RAW PRICE CURVE SUBSECTION (A50b — Baringa + Aurora real-terms)
# =============================================================================

st.subheader("📈 Raw Price Curve")
st.caption(
    "Vendor forecasts of wholesale merchant electricity prices in **real terms** "
    "(today's £). The PIRR engine applies the inflation curve below to convert "
    "real → nominal for the 'Computed' Nominal Merchant Curve mode. Defaults "
    "extracted from Excel `Baringa and Aurora` sheet (rows 114 + 194, "
    "Applied Fixed Tilt)."
)


def _render_vendor_panel(vendor: str, default_curve: dict,
                          state_key: str, base_year_key: str,
                          excel_ref: str):
    """Render a Baringa or Aurora panel inside an st.expander.

    Reads/writes wizard['setup'][state_key] + wizard['setup'][base_year_key].
    """
    stored = setup.get(state_key)
    with st.expander(f"▸ {vendor} Curve", expanded=False):
        st.caption(
            f"{excel_ref}. Real-terms £/MWh, monthly. Base year = year at "
            "which 1 real £ = 1 nominal £."
        )
        cols = st.columns([3, 1])
        with cols[0]:
            src_opts = ['default', 'upload']
            src_labels = {'default': "Use Excel default", 'upload': "Upload custom CSV"}
            current_src = 'upload' if stored else 'default'
            src = st.radio(
                "Source:",
                options=src_opts,
                format_func=lambda x: src_labels[x],
                horizontal=True,
                index=src_opts.index(current_src),
                key=f'{vendor.lower()}_src_radio',
            )
        with cols[1]:
            base_year = st.number_input(
                "Base year",
                min_value=2020, max_value=2030,
                value=int(setup.get(base_year_key, 2024)),
                step=1,
                key=f'{vendor.lower()}_base_year_input',
            )
            update_wizard_state('setup', base_year_key, int(base_year))

        if src == 'default':
            _render_price_curve_chart(
                default_curve,
                f"{vendor} default real curve (Excel, locked)",
                y_label="£/MWh (real)",
            )
            update_wizard_state('setup', state_key, None)
        else:
            uploaded = st.file_uploader(
                f"Upload {vendor} CSV (real-terms £/MWh)",
                type=['csv'],
                help=(
                    f"CSV with columns: `year`, `month` (1-12), `price_gbp_mwh_real`. "
                    f"Required coverage: **{_required_range_str}** (post-PPA window)."
                ),
                key=f'{vendor.lower()}_csv_uploader',
            )
            if uploaded is not None:
                curve = _parse_real_curve_csv(uploaded, vendor)
                if curve is not None:
                    ok, n_miss, first_miss, range_str = _validate_curve_coverage(
                        curve, financial
                    )
                    if not ok:
                        st.error(
                            f"{vendor}: curve must cover **{range_str}**. "
                            f"Missing {n_miss} months — first: {first_miss}. "
                            "Stored curve unchanged."
                        )
                    else:
                        update_wizard_state('setup', state_key, curve)
                        st.success(
                            f"{vendor}: loaded {len(curve)} months "
                            f"(covers {range_str} + extras)."
                        )
                        _render_price_curve_chart(
                            curve, f"{vendor} uploaded real curve",
                            y_label="£/MWh (real)",
                        )
            elif stored:
                st.info(f"Using previously uploaded {vendor} curve: {len(stored)} months.")
                _render_price_curve_chart(
                    stored, f"{vendor} uploaded real curve",
                    y_label="£/MWh (real)",
                )
            else:
                st.info(
                    f"Upload a CSV to override the default {vendor} curve. "
                    f"Required coverage: {_required_range_str}."
                )


_render_vendor_panel(
    "Baringa",
    _DEFAULT_BARINGA_CURVE_REAL,
    state_key='baringa_curve',
    base_year_key='baringa_curve_base_year',
    excel_ref="Source: Excel `Baringa and Aurora!row 114` (Applied FT)",
)
_render_vendor_panel(
    "Aurora",
    _DEFAULT_AURORA_CURVE_REAL,
    state_key='aurora_curve',
    base_year_key='aurora_curve_base_year',
    excel_ref="Source: Excel `Baringa and Aurora!row 194` (Applied FT)",
)


# Curve selector: which raw curve drives the Computed nominal mode.
selector_options = ['baringa', 'aurora', 'average']
selector_labels = {
    'baringa': "🔵 Baringa",
    'aurora':  "🟢 Aurora",
    'average': "🔵🟢 Average of two",
}
current_selector = setup.get('raw_curve_selector', 'baringa')
if current_selector not in selector_options:
    current_selector = 'baringa'

selected_curve = st.radio(
    "Which raw curve feeds the 'Computed' Nominal Merchant Curve mode?",
    options=selector_options,
    format_func=lambda x: selector_labels[x],
    horizontal=True,
    index=selector_options.index(current_selector),
    key='raw_curve_selector_radio',
)
update_wizard_state('setup', 'raw_curve_selector', selected_curve)


st.divider()


# =============================================================================
# INFLATION CURVE SUBSECTION (A50b — uploadable CPI curve)
# =============================================================================

st.subheader("💸 Inflation Curve")
st.caption(
    "Year-by-year CPI rates. Drives opex / tax escalation throughout the engine "
    "AND the real → nominal conversion when the Nominal Merchant Curve is in "
    "'Computed' mode. Default = Excel `Curves and D&T!row 10` (2024-2029 "
    "explicit + 2.0% steady-state from 2030)."
)

cpi_source_options = ['default', 'upload']
cpi_source_labels = {
    'default': "Use Excel default curve",
    'upload': "Upload custom curve",
}
current_cpi_source = financial.get('cpi_curve_source', 'default')
if current_cpi_source not in cpi_source_options:
    current_cpi_source = 'default'

cpi_source = st.radio(
    "Inflation source:",
    options=cpi_source_options,
    format_func=lambda x: cpi_source_labels[x],
    horizontal=True,
    index=cpi_source_options.index(current_cpi_source),
    key='cpi_source_radio',
)
update_wizard_section('financial', {'cpi_curve_source': cpi_source})


def _render_cpi_bar_chart(cpi_dict, steady, label_suffix=""):
    """Bar chart of annual CPI rates (display %)."""
    if not cpi_dict:
        st.info("No inflation curve data to display.")
        return
    years = sorted(cpi_dict.keys())
    rates_pct = [cpi_dict[y] * 100 for y in years]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=rates_pct, name='CPI %', marker_color='#9b59b6'))
    fig.add_hline(
        y=steady * 100, line_dash='dash', line_color='#e67e22',
        annotation_text=f"Steady-state {steady * 100:.1f}%",
        annotation_position="right",
    )
    fig.update_layout(
        height=260,
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text=f"Annual CPI rate{label_suffix}", font=dict(size=14)),
        xaxis_title="Calendar year",
        yaxis_title="CPI rate (%)",
        showlegend=False,
    )
    st.plotly_chart(fig, width='stretch')


# Steady-state input (display %, stored as decimal)
default_steady = financial.get('cpi_steady_state_rate')
default_steady_display = (default_steady * 100) if default_steady is not None else 2.0

steady_pct = st.number_input(
    "Steady-state CPI rate beyond curve (%)",
    min_value=0.0, max_value=20.0,
    value=float(default_steady_display),
    step=0.1,
    format="%.2f",
    help="Used for years not present in the curve. Excel default = 2.0%.",
    key='cpi_steady_state_input',
)
# Store as decimal; None when unchanged from 2.0 default to keep state clean
steady_decimal = round(steady_pct / 100.0, 6)
if cpi_source == 'default' and abs(steady_decimal - 0.020) < 1e-9:
    update_wizard_section('financial', {'cpi_steady_state_rate': None})
else:
    update_wizard_section('financial', {'cpi_steady_state_rate': steady_decimal})

if cpi_source == 'default':
    _render_cpi_bar_chart(
        _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR, steady_decimal,
        label_suffix=" (Excel locked default)",
    )
    update_wizard_section('financial', {'cpi_curve_by_calendar_year': None})

else:
    cpi_uploaded = st.file_uploader(
        "Upload CPI curve CSV",
        type=['csv'],
        help="CSV with columns: `year`, `rate_pct` (display percentage, e.g. `2.2` for 2.2%).",
        key='cpi_csv_uploader',
    )
    if cpi_uploaded is not None:
        try:
            df_c = pd.read_csv(cpi_uploaded)
            df_c.columns = [c.strip().lower() for c in df_c.columns]
            if not {'year', 'rate_pct'}.issubset(set(df_c.columns)):
                st.error(
                    "CPI CSV must have columns `year` and `rate_pct`. "
                    f"Got: {', '.join(df_c.columns)}"
                )
            else:
                df_c = df_c.dropna(subset=['year', 'rate_pct'])
                df_c['year'] = df_c['year'].astype(int)
                df_c['rate_pct'] = df_c['rate_pct'].astype(float)
                if (df_c['rate_pct'] < 0).any() or (df_c['rate_pct'] > 50).any():
                    st.error("CPI rates must be in [0, 50] %.")
                else:
                    cpi_dict = {
                        int(r.year): round(float(r.rate_pct) / 100.0, 6)
                        for r in df_c.itertuples()
                    }
                    update_wizard_section('financial', {'cpi_curve_by_calendar_year': cpi_dict})
                    st.success(f"Loaded {len(cpi_dict)} annual CPI rates.")
                    _render_cpi_bar_chart(cpi_dict, steady_decimal, label_suffix=" (uploaded)")
        except Exception as e:
            st.error(f"Error reading CPI CSV: {e}")
    else:
        stored_cpi = financial.get('cpi_curve_by_calendar_year')
        if stored_cpi:
            st.info(f"Using previously uploaded CPI curve: {len(stored_cpi)} years.")
            _render_cpi_bar_chart(stored_cpi, steady_decimal, label_suffix=" (uploaded)")
        else:
            st.info("Upload a CPI CSV to override the Excel default.")


st.divider()


# =============================================================================
# NOMINAL MERCHANT CURVE SECTION (A49 + A50b: now supports 'computed' mode)
# =============================================================================
# Post-PPA merchant electricity price curve. Feeds `PirrInputs.merchant_prices_monthly`
# via the engine adapter `pirr_inputs_from_wizard_state`. Treated as
# **nominal £/MWh** — engine consumes verbatim, no further escalation.
#
# Three modes (A50b):
#   - 'default'  : engine's locked Burton-Leonard curve from
#                  `Solar&BESS Operation!row 66`. D13 audit invariant.
#   - 'computed' : adapter computes nominal = selected raw curve × inflation
#                  factors at engine call time. Source curves above.
#   - 'upload'   : user provides a pre-computed nominal CSV directly (A49).
# =============================================================================

st.subheader("💰 Nominal Merchant Curve")
st.caption(
    "Final post-PPA merchant electricity price (£/MWh, monthly, **nominal "
    "terms**) consumed by the PIRR engine. Default = locked Excel snapshot. "
    "Computed = pipeline output of Raw Price Curve × Inflation Curve. "
    "Upload = drop in a pre-computed nominal CSV."
)

nm_source_options = ['default', 'computed', 'upload']
nm_source_labels = {
    'default':  "🔒 Default (Excel `Solar&BESS Operation!r66`)",
    'computed': "🧮 Computed (Raw × Inflation)",
    'upload':   "📤 Upload custom nominal CSV",
}
current_nm_source = setup.get('merchant_price_curve_source', 'default')
if current_nm_source not in nm_source_options:
    current_nm_source = 'default'

price_source = st.radio(
    "Curve source:",
    options=nm_source_options,
    format_func=lambda x: nm_source_labels[x],
    horizontal=False,
    index=nm_source_options.index(current_nm_source),
    key='merchant_price_source_radio',
)
update_wizard_state('setup', 'merchant_price_curve_source', price_source)


if price_source == 'default':
    _render_price_curve_chart(
        _ENGINE_DEFAULT_CURVE,
        "Engine default merchant curve (Burton-Leonard, locked)",
        y_label="£/MWh (nominal)",
    )
    # Clear any stored upload if user toggled back to default
    update_wizard_state('setup', 'merchant_price_curve', None)

elif price_source == 'computed':
    # Live preview: apply current inflation curve to the selected raw curve.
    # Engine adapter will perform the same computation at PIRR call time.
    stored_baringa = setup.get('baringa_curve')
    stored_aurora = setup.get('aurora_curve')
    effective_baringa = stored_baringa if stored_baringa else _DEFAULT_BARINGA_CURVE_REAL
    effective_aurora = stored_aurora if stored_aurora else _DEFAULT_AURORA_CURVE_REAL
    effective_selector = setup.get('raw_curve_selector', 'baringa')
    # Active CPI: uploaded curve overrides default; steady-state always read.
    effective_cpi_curve = (
        financial.get('cpi_curve_by_calendar_year')
        or _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR
    )
    effective_cpi_steady = financial.get('cpi_steady_state_rate') or 0.020
    # Pick base year per the selected vendor
    if effective_selector == 'baringa':
        effective_base = int(setup.get('baringa_curve_base_year', 2024))
    elif effective_selector == 'aurora':
        effective_base = int(setup.get('aurora_curve_base_year', 2024))
    else:
        # Average: use the earlier of the two for safety
        effective_base = min(
            int(setup.get('baringa_curve_base_year', 2024)),
            int(setup.get('aurora_curve_base_year', 2024)),
        )

    selected_real = _select_raw_curve(
        effective_baringa, effective_aurora, effective_selector,
    )
    if not selected_real:
        st.warning(
            "No raw curve available to compute from. Upload Baringa or "
            "Aurora above, or switch to Default."
        )
    else:
        computed_nominal = _apply_inflation_to_real_curve(
            selected_real, effective_cpi_curve, effective_cpi_steady,
            base_year=effective_base,
        )
        st.success(
            f"Computed from {effective_selector.title()} × inflation "
            f"(base year {effective_base}). {len(computed_nominal)} months."
        )
        _render_price_curve_chart(
            computed_nominal,
            f"Computed nominal (selected raw × inflation, base {effective_base})",
            y_label="£/MWh (nominal)",
        )
        st.caption(
            "ℹ️ Engine adapter recomputes this at PIRR call time using the same "
            "raw curves + inflation curve. No data is written to wizard state — "
            "the computation is live."
        )
    # Clear direct-upload to avoid stale state surprise on mode switch
    update_wizard_state('setup', 'merchant_price_curve', None)

else:  # 'upload'
    uploaded_price = st.file_uploader(
        "Upload Nominal Merchant Curve CSV",
        type=['csv'],
        help=(
            "CSV with columns: `year`, `month` (1-12), `price_gbp_mwh` "
            "(nominal £/MWh — must include inflation; engine does not "
            "escalate this curve). One row per month. Required coverage: "
            f"**{_required_range_str}** (post-PPA window for current "
            "project timeline)."
        ),
        key='merchant_price_csv_uploader',
    )

    if uploaded_price is not None:
        try:
            df_upload = pd.read_csv(uploaded_price)
            df_upload.columns = [c.strip().lower() for c in df_upload.columns]
            required = {'year', 'month', 'price_gbp_mwh'}
            if not required.issubset(set(df_upload.columns)):
                st.error(
                    f"CSV must have columns: {', '.join(sorted(required))}. "
                    f"Got: {', '.join(df_upload.columns)}"
                )
            else:
                df_upload = df_upload.dropna(subset=['year', 'month', 'price_gbp_mwh'])
                df_upload['year'] = df_upload['year'].astype(int)
                df_upload['month'] = df_upload['month'].astype(int)
                df_upload['price_gbp_mwh'] = df_upload['price_gbp_mwh'].astype(float)

                bad_months = df_upload[(df_upload['month'] < 1) | (df_upload['month'] > 12)]
                if not bad_months.empty:
                    st.error(f"Month values must be 1-12. Found: {bad_months['month'].tolist()[:5]}")
                elif (df_upload['price_gbp_mwh'] < 0).any():
                    st.error("Price values must be non-negative.")
                else:
                    curve_dict = {
                        (int(r.year), int(r.month)): float(r.price_gbp_mwh)
                        for r in df_upload.itertuples()
                    }
                    ok, n_missing, first_miss, range_str = _validate_curve_coverage(
                        curve_dict, financial
                    )
                    if not ok:
                        st.error(
                            f"Curve must cover **{range_str}** (post-PPA "
                            f"window for current project timeline). Missing "
                            f"{n_missing} months — first: {first_miss}. "
                            "Stored curve unchanged."
                        )
                    else:
                        update_wizard_state('setup', 'merchant_price_curve', curve_dict)
                        st.success(
                            f"Loaded {len(curve_dict)} monthly price points "
                            f"(covers {range_str} + extras)."
                        )
                        _render_price_curve_chart(
                            curve_dict, "Uploaded merchant curve",
                            y_label="£/MWh (nominal)",
                        )
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    else:
        stored = setup.get('merchant_price_curve')
        if stored:
            st.info(f"Using previously uploaded curve: {len(stored)} months.")
            _render_price_curve_chart(
                stored, "Uploaded merchant curve",
                y_label="£/MWh (nominal)",
            )
        else:
            st.info(
                f"Upload a CSV to set a custom merchant price curve. "
                f"Required coverage: {_required_range_str}. "
                "Engine uses the default curve until upload."
            )


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

with col3:
    if st.button("Next → Dispatch Rules", type="primary", disabled=not is_valid, width='stretch'):
        mark_step_completed(1)
        st.switch_page("pages/Step2_Rules.py")

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
