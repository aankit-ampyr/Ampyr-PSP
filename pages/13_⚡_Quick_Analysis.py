"""
Quick Analysis: Combined Rules + Configuration + Analysis

Alternative to the 5-step wizard flow. Allows users to:
1. Configure dispatch rules
2. Select a single BESS/Duration/DG configuration
3. Run full year simulation
4. Explore results by date range
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
    can_navigate_to_step, get_step_status
)
from src.template_inference import (
    infer_template, get_template_info, get_valid_triggers_for_timing
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Quick Analysis",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS to reduce metric font sizes to prevent overlapping
st.markdown("""
<style>
    /* Reduce metric value font size */
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    /* Reduce metric label font size */
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    /* Reduce metric delta font size */
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize wizard state
init_wizard_state()

# Check if Step 1 completed
if not can_navigate_to_step(2):
    st.warning("Please complete Step 1 (Setup) first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/8_🚀_Step1_Setup.py")
    st.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_template_card(template_id: int, dg_charges_bess: bool = False, dg_load_priority: str = 'bess_first'):
    """Render an informational card showing the inferred template."""
    info = get_template_info(template_id)

    if not info['dg_enabled']:
        border_color = "#2ecc71"
        icon = "☀️"
    else:
        border_color = "#3498db"
        icon = "⚡"

    if not info['dg_enabled']:
        merit_order = info['merit_order']
    elif dg_load_priority == 'dg_first':
        merit_order = "Solar → DG → BESS → Unserved"
        if dg_charges_bess:
            merit_order += " + DG→Battery"
    else:
        merit_order = "Solar → BESS → DG → Unserved"
        if dg_charges_bess:
            merit_order += " + DG→Battery"

    description = info['description']
    if info['dg_enabled']:
        if dg_charges_bess:
            description += " (Excess DG charges battery)"
        else:
            description += " (Battery charges from solar only)"

    st.markdown(f"""
    <div style="
        border: 2px solid {border_color};
        border-radius: 10px;
        padding: 15px;
        background-color: rgba(255,255,255,0.05);
    ">
        <h4 style="margin: 0;">{icon} {info['name']}</h4>
        <p style="color: #888; margin: 5px 0;">{merit_order}</p>
        <p style="margin: 5px 0;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def date_to_hour_index(selected_date, base_year=2024):
    """Convert date to hour index in simulation."""
    base_date = date(base_year, 1, 1)
    days_since_start = (selected_date - base_date).days
    return days_since_start * 24


def create_dispatch_graph(hourly_df: pd.DataFrame, load_mw: float, bess_capacity: float = 100,
                          soc_on: float = 30, soc_off: float = 80) -> go.Figure:
    """Create dispatch visualization with dual y-axis."""
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


def run_simulation(bess_mwh, duration, dg_mw, template_id, setup, rules, solar_profile, load_profile):
    """Run simulation for full year and return hourly data."""
    from src.dispatch_engine import SimulationParams, run_simulation as dispatch_run

    power_mw = bess_mwh / duration

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

    hourly_results = dispatch_run(params, template_id, num_hours=8760)
    return hourly_results


def convert_results_to_dataframe(hourly_results):
    """Convert hourly results to DataFrame."""
    return pd.DataFrame([{
        'hour': h.t,
        'day': h.day,
        'hour_of_day': h.hour_of_day,
        'solar_mw': h.solar,
        'load_mw': h.load,
        'bess_mw': h.bess_power,
        'soc_percent': h.soc_pct,
        'bess_state': h.bess_state,
        'dg_output_mw': h.dg_to_load + h.dg_to_bess + h.dg_curtailed,
        'dg_state': 'ON' if h.dg_running else 'OFF',
        'solar_to_load': h.solar_to_load,
        'dg_to_load': h.dg_to_load,
        'dg_to_bess': h.dg_to_bess,
        'dg_curtailed': h.dg_curtailed,
        'bess_to_load': h.bess_to_load,
        'unmet_mw': h.unserved,
        'delivery': 'Yes' if (h.load > 0 and h.unserved < 0.001) else 'No',
        'solar_curtailed': h.solar_curtailed,
    } for h in hourly_results])


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("⚡ Quick Analysis")
st.markdown("Configure dispatch rules, select a configuration, and analyze results - all in one page.")

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']

dg_enabled = setup['dg_enabled']


# =============================================================================
# SECTION 1: DISPATCH RULES
# =============================================================================

st.header("1️⃣ Dispatch Rules")

if not dg_enabled:
    st.info("Your system has no generator. The dispatch strategy is **Solar + BESS Only**.")
    render_template_card(0)
    template_id = 0
    dg_charges_bess = False
    dg_load_priority = 'bess_first'
else:
    col_rules1, col_rules2 = st.columns(2)

    with col_rules1:
        # Question 1: DG Timing
        st.markdown("**When can the generator run?**")
        dg_timing_options = {
            'anytime': "Anytime (no restrictions)",
            'day_only': "Day only (nights must be silent)",
            'night_only': "Night only (days must be green)",
            'custom_blackout': "Custom blackout window",
        }
        dg_timing = st.radio(
            "DG timing:",
            options=list(dg_timing_options.keys()),
            format_func=lambda x: dg_timing_options[x],
            index=list(dg_timing_options.keys()).index(rules.get('dg_timing', 'anytime')),
            key='qa_dg_timing',
            label_visibility="collapsed"
        )
        update_wizard_state('rules', 'dg_timing', dg_timing)

        # Time window settings
        if dg_timing == 'day_only':
            tc1, tc2 = st.columns(2)
            with tc1:
                day_start = st.slider("Day starts", 0, 23, rules.get('day_start', 6), key='qa_day_start')
                update_wizard_state('rules', 'day_start', day_start)
            with tc2:
                day_end = st.slider("Day ends", 0, 23, rules.get('day_end', 18), key='qa_day_end')
                update_wizard_state('rules', 'day_end', day_end)
        elif dg_timing == 'night_only':
            tc1, tc2 = st.columns(2)
            with tc1:
                night_start = st.slider("Night starts", 0, 23, rules.get('night_start', 18), key='qa_night_start')
                update_wizard_state('rules', 'night_start', night_start)
            with tc2:
                night_end = st.slider("Night ends", 0, 23, rules.get('night_end', 6), key='qa_night_end')
                update_wizard_state('rules', 'night_end', night_end)
        elif dg_timing == 'custom_blackout':
            tc1, tc2 = st.columns(2)
            with tc1:
                blackout_start = st.slider("Blackout starts", 0, 23, rules.get('blackout_start', 22), key='qa_blackout_start')
                update_wizard_state('rules', 'blackout_start', blackout_start)
            with tc2:
                blackout_end = st.slider("Blackout ends", 0, 23, rules.get('blackout_end', 6), key='qa_blackout_end')
                update_wizard_state('rules', 'blackout_end', blackout_end)

        # Question 2: DG Trigger
        st.markdown("**What triggers the generator?**")
        valid_triggers = get_valid_triggers_for_timing(dg_timing)
        trigger_options = {t[0]: t[1] for t in valid_triggers}

        current_trigger = rules.get('dg_trigger', 'reactive')
        if current_trigger not in trigger_options:
            current_trigger = list(trigger_options.keys())[0]
            update_wizard_state('rules', 'dg_trigger', current_trigger)

        dg_trigger = st.radio(
            "DG trigger:",
            options=list(trigger_options.keys()),
            format_func=lambda x: trigger_options[x],
            index=list(trigger_options.keys()).index(current_trigger),
            key='qa_dg_trigger',
            label_visibility="collapsed"
        )
        update_wizard_state('rules', 'dg_trigger', dg_trigger)

        # SOC thresholds
        if dg_trigger == 'soc_based':
            st.markdown("**SOC Thresholds:**")
            soc_col1, soc_col2 = st.columns(2)
            with soc_col1:
                soc_on = st.slider(
                    "DG ON below (%)",
                    int(setup['bess_min_soc']), int(setup['bess_max_soc']) - 10,
                    int(rules.get('soc_on_threshold', 30)), step=5, key='qa_soc_on'
                )
                update_wizard_state('rules', 'soc_on_threshold', float(soc_on))
            with soc_col2:
                soc_off = st.slider(
                    "DG OFF above (%)",
                    soc_on + 10, int(setup['bess_max_soc']),
                    max(int(rules.get('soc_off_threshold', 80)), soc_on + 10), step=5, key='qa_soc_off'
                )
                update_wizard_state('rules', 'soc_off_threshold', float(soc_off))

    with col_rules2:
        # Question 3: DG charges BESS
        st.markdown("**Can DG charge the battery?**")
        dg_charges_bess = st.radio(
            "DG charging:",
            options=[False, True],
            format_func=lambda x: "Yes — excess DG charges battery" if x else "No — solar only charges battery",
            index=1 if rules.get('dg_charges_bess', False) else 0,
            key='qa_dg_charges',
            label_visibility="collapsed"
        )
        update_wizard_state('rules', 'dg_charges_bess', dg_charges_bess)

        # Question 4: Load priority
        st.markdown("**Load serving priority:**")
        dg_load_priority = st.radio(
            "Priority:",
            options=['bess_first', 'dg_first'],
            format_func=lambda x: {
                'bess_first': "BESS First — Battery serves load, DG fills gap",
                'dg_first': "DG First — Generator serves load directly"
            }[x],
            index=0 if rules.get('dg_load_priority', 'bess_first') == 'bess_first' else 1,
            key='qa_load_priority',
            label_visibility="collapsed"
        )
        update_wizard_state('rules', 'dg_load_priority', dg_load_priority)

        # Question 5: DG Takeover Mode
        st.markdown("**DG Takeover Mode:**")
        dg_takeover_mode = st.radio(
            "Takeover:",
            options=[False, True],
            format_func=lambda x: "Yes — DG serves full load, solar goes to BESS" if x else "No — DG fills gap only (standard)",
            index=1 if rules.get('dg_takeover_mode', False) else 0,
            key='qa_dg_takeover',
            label_visibility="collapsed"
        )
        update_wizard_state('rules', 'dg_takeover_mode', dg_takeover_mode)

        if dg_takeover_mode:
            st.caption("When DG runs: DG → Load (full), Solar → BESS. Zero DG curtailment.")

        # Template card
        st.markdown("**Dispatch Strategy:**")
        template_id = infer_template(dg_enabled=True, dg_timing=dg_timing, dg_trigger=dg_trigger)
        update_wizard_state('rules', 'inferred_template', template_id)
        render_template_card(template_id, dg_charges_bess, dg_load_priority)

st.divider()


# =============================================================================
# SECTION 2: CONFIGURATION SELECTION
# =============================================================================

st.header("2️⃣ Configuration")

# Initialize quick analysis state if needed
if 'quick_analysis' not in st.session_state:
    st.session_state.quick_analysis = {
        'bess_capacity': 100.0,
        'duration': 4,
        'dg_capacity': 10.0,
        'simulation_results': None,
        'cache_key': None,
    }

qa_state = st.session_state.quick_analysis

# Initialize widget keys if they don't exist (first run)
if 'qa_bess_slider' not in st.session_state:
    st.session_state.qa_bess_slider = qa_state['bess_capacity']
if 'qa_bess_input' not in st.session_state:
    st.session_state.qa_bess_input = qa_state['bess_capacity']
if 'qa_dg_slider' not in st.session_state:
    st.session_state.qa_dg_slider = qa_state['dg_capacity']
if 'qa_dg_input' not in st.session_state:
    st.session_state.qa_dg_input = qa_state['dg_capacity']

# Callbacks to sync slider and number input values
def on_bess_slider_change():
    val = st.session_state.qa_bess_slider
    st.session_state.qa_bess_input = val
    st.session_state.quick_analysis['bess_capacity'] = val

def on_bess_input_change():
    val = st.session_state.qa_bess_input
    st.session_state.qa_bess_slider = val
    st.session_state.quick_analysis['bess_capacity'] = val

def on_dg_slider_change():
    val = st.session_state.qa_dg_slider
    st.session_state.qa_dg_input = val
    st.session_state.quick_analysis['dg_capacity'] = val

def on_dg_input_change():
    val = st.session_state.qa_dg_input
    st.session_state.qa_dg_slider = val
    st.session_state.quick_analysis['dg_capacity'] = val

col_config1, col_config2, col_config3 = st.columns(3)

with col_config1:
    st.markdown("**BESS Capacity (MWh)**")
    st.slider(
        "BESS MWh",
        min_value=10.0, max_value=800.0,
        step=10.0,
        key='qa_bess_slider',
        on_change=on_bess_slider_change,
        label_visibility="collapsed"
    )
    st.number_input(
        "Fine-tune",
        min_value=10.0, max_value=800.0,
        step=5.0,
        key='qa_bess_input',
        on_change=on_bess_input_change
    )
    bess_capacity = qa_state['bess_capacity']

with col_config2:
    st.markdown("**Duration (hours)**")
    duration = st.selectbox(
        "Duration",
        options=[1, 2, 4, 6, 8],
        index=[1, 2, 4, 6, 8].index(qa_state['duration']) if qa_state['duration'] in [1, 2, 4, 6, 8] else 2,
        key='qa_duration',
        label_visibility="collapsed"
    )
    qa_state['duration'] = duration

    power_mw = bess_capacity / duration
    st.info(f"**Power:** {power_mw:.1f} MW")

with col_config3:
    if dg_enabled:
        st.markdown("**DG Capacity (MW)**")
        st.slider(
            "DG MW",
            min_value=0.0, max_value=50.0,
            step=5.0,
            key='qa_dg_slider',
            on_change=on_dg_slider_change,
            label_visibility="collapsed"
        )
        st.number_input(
            "Fine-tune",
            min_value=0.0, max_value=50.0,
            step=1.0,
            key='qa_dg_input',
            on_change=on_dg_input_change
        )
        dg_capacity = qa_state['dg_capacity']
    else:
        dg_capacity = 0.0
        st.markdown("**DG Capacity**")
        st.info("DG disabled in Setup")

# Configuration summary
st.markdown(f"""
**Selected Configuration:** `{power_mw:.0f} MW × {duration}-hr = {bess_capacity:.0f} MWh` | DG: `{dg_capacity:.0f} MW`
""")

# Run simulation button
run_btn = st.button("🚀 Run Full Year Simulation", type="primary", width='stretch')

st.divider()


# =============================================================================
# SECTION 3: RESULTS ANALYSIS
# =============================================================================

# Build cache key
cache_key = f"{bess_capacity}_{duration}_{dg_capacity}_{template_id}_{dg_charges_bess}_{dg_load_priority}"
cache_key += f"_{rules.get('soc_on_threshold', 30)}_{rules.get('soc_off_threshold', 80)}"

# Check if simulation needs to run
if run_btn or (qa_state['simulation_results'] is not None and qa_state['cache_key'] == cache_key):

    if run_btn or qa_state['cache_key'] != cache_key:
        with st.spinner("Running 8760-hour simulation..."):
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
                # Seasonal parameters
                'start_month': setup.get('load_season_start', 4),
                'end_month': setup.get('load_season_end', 10),
                'day_start': setup.get('load_season_day_start', 8),
                'day_end': setup.get('load_season_day_end', 0),
            }
            load_profile = build_load_profile(setup['load_mode'], load_params)

            # Run simulation
            hourly_results = run_simulation(
                bess_capacity, duration, dg_capacity,
                template_id, setup, rules,
                solar_profile, load_profile.tolist()
            )

            if hourly_results is not None and len(hourly_results) > 0:
                qa_state['simulation_results'] = hourly_results
                qa_state['cache_key'] = cache_key
                # Store profiles for 20-year projection
                qa_state['solar_profile'] = solar_profile
                qa_state['load_profile'] = load_profile.tolist()
                st.success("Simulation complete! Full year (8760 hours) simulated.")
            else:
                st.error("Simulation failed.")
                st.stop()

    # Get results and profiles from state
    hourly_results = qa_state['simulation_results']
    solar_profile = qa_state.get('solar_profile', [0] * 8760)
    load_profile = qa_state.get('load_profile', [setup['load_mw']] * 8760)

    if hourly_results is not None:
        # Convert to DataFrame
        full_year_df = convert_results_to_dataframe(hourly_results)

        st.header("3️⃣ Results")

        # ===========================================
        # PART A: FULL YEAR SUMMARY
        # ===========================================

        # Count hours with actual load (for seasonal patterns)
        load_hours = (full_year_df['load_mw'] > 0).sum()
        total_hours = load_hours if load_hours > 0 else 8760

        if load_hours < 8760:
            st.subheader(f"📊 Full Year Summary ({load_hours:,} load hours)")
        else:
            st.subheader("📊 Full Year Summary (8760 hours)")

        delivery_hours = (full_year_df['delivery'] == 'Yes').sum()
        dg_hours = (full_year_df['dg_state'] == 'ON').sum()
        total_solar = full_year_df['solar_mw'].sum()
        solar_curtailed = full_year_df['solar_curtailed'].sum()
        wastage_pct = (solar_curtailed / total_solar * 100) if total_solar > 0 else 0
        avg_soc = full_year_df['soc_percent'].mean()

        # Calculate load period wastage (only during hours with load)
        load_hours_df = full_year_df[full_year_df['load_mw'] > 0]
        load_solar = load_hours_df['solar_mw'].sum()
        load_curtailed = load_hours_df['solar_curtailed'].sum()
        load_wastage_pct = (load_curtailed / load_solar * 100) if load_solar > 0 else 0

        metric_cols = st.columns(6)
        metric_cols[0].metric("Delivery Hours", f"{delivery_hours:,} / {total_hours:,}", f"{delivery_hours/total_hours*100:.1f}%")
        metric_cols[1].metric("DG Runtime", f"{dg_hours:,} hrs", f"{dg_hours/8760*100:.1f}%")
        metric_cols[2].metric("Avg SOC", f"{avg_soc:.0f}%")
        metric_cols[3].metric("Solar Curtailed", f"{solar_curtailed:,.0f} MWh")
        metric_cols[4].metric("Total Wastage", f"{wastage_pct:.1f}%")
        metric_cols[5].metric("Load Period Wastage", f"{load_wastage_pct:.1f}%", help="Wastage during load hours only")

        # Monthly delivery chart
        st.markdown("#### Monthly Delivery Performance")

        # Calculate monthly stats
        # Calculate month from hour index using non-leap year (2023) to match 8760 hours / 365 days
        full_year_df['month'] = full_year_df['hour'].apply(
            lambda h: min(11, (date(2023, 1, 1) + timedelta(hours=h)).month - 1)
        )

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        monthly_stats = full_year_df.groupby('month').agg({
            'delivery': lambda x: (x == 'Yes').sum(),
            'dg_state': lambda x: (x == 'ON').sum(),
            'solar_to_load': lambda x: (x > 0).sum(),
            'bess_to_load': lambda x: (x > 0).sum(),
            'dg_to_load': lambda x: (x > 0).sum(),
            'load_mw': lambda x: (x > 0).sum(),  # Count hours with actual load
            'hour': 'count'
        }).reset_index()
        monthly_stats.columns = ['month', 'delivery_hours', 'dg_runtime_hours', 'solar_hrs', 'bess_hrs', 'dg_hrs', 'load_hours', 'total_hours']
        # Calculate delivery % based on load hours (not total hours) for seasonal patterns
        monthly_stats['effective_hours'] = monthly_stats['load_hours'].apply(lambda x: x if x > 0 else 1)
        monthly_stats['delivery_pct'] = (monthly_stats['delivery_hours'] / monthly_stats['effective_hours'] * 100).clip(0, 100)
        monthly_stats['month_name'] = monthly_stats['month'].apply(lambda x: month_names[x])

        # Create stacked bar chart for energy sources
        fig_monthly = go.Figure()

        # Solar hours (bottom of stack - orange)
        fig_monthly.add_trace(go.Bar(
            x=monthly_stats['month_name'],
            y=monthly_stats['solar_hrs'],
            name='Solar Hours',
            marker_color='#FFA500',
            hovertemplate='%{x}<br>Solar: %{y} hrs<extra></extra>'
        ))

        # BESS hours (middle of stack - blue)
        fig_monthly.add_trace(go.Bar(
            x=monthly_stats['month_name'],
            y=monthly_stats['bess_hrs'],
            name='BESS Hours',
            marker_color='#1f77b4',
            hovertemplate='%{x}<br>BESS: %{y} hrs<extra></extra>'
        ))

        # DG hours (top of stack - red)
        fig_monthly.add_trace(go.Bar(
            x=monthly_stats['month_name'],
            y=monthly_stats['dg_hrs'],
            name='DG Hours',
            marker_color='#e74c3c',
            hovertemplate='%{x}<br>DG: %{y} hrs<extra></extra>'
        ))

        # Delivery % line overlay with load hours context
        # Build custom hover text showing delivery/load hours
        monthly_stats['hover_text'] = monthly_stats.apply(
            lambda r: f"{r['month_name']}<br>Delivery: {r['delivery_hours']}/{r['load_hours']} hrs ({r['delivery_pct']:.0f}%)",
            axis=1
        )
        fig_monthly.add_trace(go.Scatter(
            x=monthly_stats['month_name'],
            y=monthly_stats['delivery_pct'],
            name='Delivery %',
            mode='lines+markers+text',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=8),
            text=monthly_stats['delivery_pct'].apply(lambda x: f'{x:.0f}%'),
            textposition='top center',
            yaxis='y2',
            hovertemplate='%{customdata}<extra></extra>',
            customdata=monthly_stats['hover_text']
        ))

        # Hours per month for non-leap year (matches 8760 hours / 365 days)
        hours_per_month = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]

        fig_monthly.update_layout(
            height=400,
            xaxis_title="Month",
            yaxis_title="Hours Contributing to Load",
            yaxis2=dict(
                title='Delivery %',
                overlaying='y',
                side='right',
                range=[0, 110]
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(l=50, r=50, t=50, b=50),
            barmode='stack',
            bargap=0.2
        )

        st.plotly_chart(fig_monthly, width='stretch')

        # Monthly breakdown table
        st.markdown("#### Monthly Breakdown")

        # Calculate detailed monthly stats
        monthly_detail = full_year_df.groupby('month').agg({
            'solar_to_load': lambda x: (x > 0).sum(),  # Hours with solar contribution
            'bess_to_load': lambda x: (x > 0).sum(),   # Hours with BESS contribution
            'dg_to_load': lambda x: (x > 0).sum(),     # Hours with DG contribution
            'solar_curtailed': 'sum',                   # Total solar curtailed MWh
            'solar_mw': 'sum',                          # Total solar generated MWh
        }).reset_index()
        monthly_detail.columns = ['month', 'solar_hrs', 'bess_hrs', 'dg_hrs', 'curtailed_mwh', 'total_solar_mwh']
        monthly_detail['wastage_pct'] = (monthly_detail['curtailed_mwh'] / monthly_detail['total_solar_mwh'] * 100).fillna(0)
        monthly_detail['month_name'] = monthly_detail['month'].apply(lambda x: month_names[x])

        # Create display DataFrame
        monthly_table = pd.DataFrame({
            'Month': monthly_detail['month_name'],
            'Solar Hrs': monthly_detail['solar_hrs'].astype(int),
            'BESS Hrs': monthly_detail['bess_hrs'].astype(int),
            'DG Hrs': monthly_detail['dg_hrs'].astype(int),
            'Curtailed (MWh)': monthly_detail['curtailed_mwh'].round(1),
            'Wastage %': monthly_detail['wastage_pct'].round(1),
        })

        st.dataframe(
            monthly_table,
            width='stretch',
            hide_index=True,
            column_config={
                'Month': st.column_config.TextColumn('Month'),
                'Solar Hrs': st.column_config.NumberColumn('Solar Hrs', help='Hours with solar contributing to load'),
                'BESS Hrs': st.column_config.NumberColumn('BESS Hrs', help='Hours with BESS contributing to load'),
                'DG Hrs': st.column_config.NumberColumn('DG Hrs', help='Hours with DG contributing to load'),
                'Curtailed (MWh)': st.column_config.NumberColumn('Curtailed (MWh)', format='%.1f', help='Solar energy curtailed'),
                'Wastage %': st.column_config.NumberColumn('Wastage %', format='%.1f%%', help='% of solar energy wasted'),
            }
        )

        # Download button for monthly breakdown
        monthly_csv = monthly_table.to_csv(index=False)
        st.download_button(
            "📥 Download Monthly Breakdown CSV",
            data=monthly_csv,
            file_name=f"monthly_breakdown_{bess_capacity}mwh_{duration}hr.csv",
            mime="text/csv",
        )

        st.divider()

        # ===========================================
        # PART B: DATE RANGE ANALYSIS
        # ===========================================

        st.subheader("📈 Date Range Analysis")

        # Date selection
        date_col1, date_col2, date_col3 = st.columns([1, 1, 2])

        with date_col1:
            start_date = st.date_input(
                "Start Date",
                value=date(2024, 1, 1),
                min_value=date(2024, 1, 1),
                max_value=date(2024, 12, 31),
                key='qa_start_date'
            )

        with date_col2:
            max_end = min(start_date + timedelta(days=6), date(2024, 12, 31))
            default_end = min(start_date + timedelta(days=2), max_end)
            end_date = st.date_input(
                "End Date",
                value=default_end,
                min_value=start_date,
                max_value=max_end,
                key='qa_end_date'
            )

        with date_col3:
            days_selected = (end_date - start_date).days + 1
            st.info(f"📅 Viewing **{days_selected} days** ({days_selected * 24} hours)")

        # Filter to date range
        start_hour = date_to_hour_index(start_date)
        end_hour = date_to_hour_index(end_date) + 24
        hourly_df = full_year_df.iloc[start_hour:end_hour].reset_index(drop=True)

        # Period metrics
        period_hours = len(hourly_df)
        period_load_hours = (hourly_df['load_mw'] > 0).sum()
        period_delivery = (hourly_df['delivery'] == 'Yes').sum()
        period_dg = (hourly_df['dg_state'] == 'ON').sum()
        period_soc = hourly_df['soc_percent'].mean()
        period_curtailed = hourly_df['solar_curtailed'].sum()
        period_solar = hourly_df['solar_mw'].sum()
        period_wastage = (period_curtailed / period_solar * 100) if period_solar > 0 else 0

        # Calculate load period wastage (only during hours with load)
        period_load_df = hourly_df[hourly_df['load_mw'] > 0]
        period_load_solar = period_load_df['solar_mw'].sum()
        period_load_curtailed = period_load_df['solar_curtailed'].sum()
        period_load_wastage = (period_load_curtailed / period_load_solar * 100) if period_load_solar > 0 else 0

        # Use load hours for delivery % if there are load hours
        effective_period_hours = period_load_hours if period_load_hours > 0 else period_hours
        delivery_pct = (period_delivery / effective_period_hours * 100) if effective_period_hours > 0 else 0

        pm_cols = st.columns(6)
        pm_cols[0].metric("Delivery", f"{period_delivery}/{effective_period_hours}", f"{delivery_pct:.1f}%")
        pm_cols[1].metric("DG Hours", f"{period_dg}", f"{period_dg/period_hours*100:.1f}%")
        pm_cols[2].metric("Avg SOC", f"{period_soc:.0f}%")
        pm_cols[3].metric("Curtailed", f"{period_curtailed:.1f} MWh")
        pm_cols[4].metric("Total Wastage", f"{period_wastage:.1f}%")
        pm_cols[5].metric("Load Wastage", f"{period_load_wastage:.1f}%", help="Wastage during load hours only")

        # Dispatch graph
        soc_on = rules.get('soc_on_threshold', 30)
        soc_off = rules.get('soc_off_threshold', 80)
        fig = create_dispatch_graph(hourly_df, setup['load_mw'], bess_capacity, soc_on, soc_off)
        st.plotly_chart(fig, width='stretch')

        st.caption("""
        **Orange**: Solar | **Red**: DG Output | **Blue**: BESS Power (negative=charging) | **Purple**: Delivery
        **Green dotted**: SOC % | **Royal Blue dashed**: BESS Energy (MWh)
        """)

        # Hourly table
        with st.expander("📊 Hourly Data Table", expanded=False):
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

            styled_df = display_df[display_cols].style.apply(style_hourly_row, axis=1)
            st.dataframe(styled_df, width='stretch', height=400)

            st.markdown("""
            **Row Colors:** 🟢 Green = Charging | 🟣 Lavender = Discharging | 🟡 Yellow = DG Running | 🔴 Pink = Unmet Load
            """)

        # Export
        csv_data = hourly_df.to_csv(index=False)
        st.download_button(
            "📥 Download Selected Range CSV",
            data=csv_data,
            file_name=f"quick_analysis_{bess_capacity}mwh_{duration}hr_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            width='stretch'
        )

        st.divider()

        # ===========================================
        # SECTION 4: MULTI-YEAR PROJECTION (ACTUAL SIMULATIONS)
        # ===========================================

        st.header("4️⃣ Multi-Year Projection")
        st.markdown("Battery degradation impact on system performance (2% compound degradation per year).")
        st.caption("**Note:** Running actual simulations for each year with degraded BESS capacity...")

        # Build 20-year monthly projection data using ACTUAL SIMULATIONS
        monthly_20yr_data = []
        yearly_projection_data = []  # For 10-year annual table

        # Degradation rate and efficiency
        degradation_rate = 0.02  # 2% per year
        one_way_eff = (setup['bess_efficiency'] / 100) ** 0.5
        loss_factor = 1 - one_way_eff

        # Progress bar for 20-year simulation
        progress_bar = st.progress(0, text="Simulating Year 1...")

        # Store yearly totals for summary
        yearly_totals = []

        for year in range(1, 21):
            progress_bar.progress(year / 20, text=f"Simulating Year {year}...")

            # Compound degradation
            capacity_factor = (1 - degradation_rate) ** (year - 1)
            effective_capacity = bess_capacity * capacity_factor
            effective_power = power_mw * capacity_factor

            # Run actual simulation for this year
            year_results = run_simulation(
                effective_capacity, duration, dg_capacity,
                template_id, setup, rules,
                solar_profile, load_profile
            )

            # Convert to DataFrame for analysis
            year_df = convert_results_to_dataframe(year_results)

            # Add month column (use non-leap year to match 8760 hours / 365 days)
            year_df['month'] = year_df['hour'].apply(
                lambda h: min(11, (date(2023, 1, 1) + timedelta(hours=h)).month - 1)
            )

            # Calculate year totals for summary
            year_solar_gen = year_df['solar_mw'].sum()
            year_dg_gen = year_df['dg_to_load'].sum()
            year_curtailed = year_df['solar_curtailed'].sum()
            year_load_met = (year_df['delivery'] == 'Yes').sum() * setup['load_mw']

            # BESS losses
            charging_energy = year_df[year_df['bess_mw'] < 0]['bess_mw'].abs().sum()
            discharging_energy = year_df[year_df['bess_mw'] > 0]['bess_mw'].sum()
            year_charging_loss = charging_energy * loss_factor
            year_discharging_loss = discharging_energy * loss_factor

            # Calculate year-level metrics
            year_delivery_hrs = (year_df['delivery'] == 'Yes').sum()
            year_load_hrs = (year_df['load_mw'] > 0).sum()  # Hours with actual load demand
            year_dg_hrs = (year_df['dg_state'] == 'ON').sum()
            year_solar_hrs = (year_df['solar_to_load'] > 0).sum()
            year_bess_hrs = (year_df['bess_to_load'] > 0).sum()
            year_wastage_pct = (year_curtailed / year_solar_gen * 100) if year_solar_gen > 0 else 0

            # Calculate load period wastage (only during hours with load)
            year_load_df = year_df[year_df['load_mw'] > 0]
            year_load_solar = year_load_df['solar_mw'].sum()
            year_load_curtailed = year_load_df['solar_curtailed'].sum()
            year_load_wastage_pct = (year_load_curtailed / year_load_solar * 100) if year_load_solar > 0 else 0

            yearly_totals.append({
                'year': year,
                'capacity': effective_capacity,
                'solar_gen': year_solar_gen,
                'dg_gen': year_dg_gen,
                'curtailed': year_curtailed,
                'load_met': year_load_met,
                'load_hrs': year_load_hrs,  # Track actual load hours per year
                'load_solar': year_load_solar,  # Solar during load hours
                'load_curtailed': year_load_curtailed,  # Curtailment during load hours
                'charging_loss': year_charging_loss,
                'discharging_loss': year_discharging_loss,
            })

            # Build 10-year/20-year annual projection table data
            # Use actual load hours for delivery % (important for seasonal loads)
            effective_load_hrs = year_load_hrs if year_load_hrs > 0 else 8760
            # Cap delivery % at 100% (delivery hours cannot exceed load hours)
            delivery_pct = min(100.0, round(year_delivery_hrs / effective_load_hrs * 100, 1))
            yearly_projection_data.append({
                'Year': year,
                'Capacity (MWh)': round(effective_capacity, 1),
                'Capacity %': round(capacity_factor * 100, 1),
                'Delivery Hrs': year_delivery_hrs,
                'Load Hrs': year_load_hrs,
                'Delivery %': delivery_pct,
                'DG Hrs': year_dg_hrs,
                'Solar Hrs': year_solar_hrs,
                'BESS Hrs': year_bess_hrs,
                'Curtailed (MWh)': round(year_curtailed, 0),
                'Total Wastage %': round(year_wastage_pct, 1),
                'Load Wastage %': round(year_load_wastage_pct, 1),
                'BESS Loss (MWh)': round(year_charging_loss + year_discharging_loss, 0),
            })

            # Process each month
            for month_idx in range(12):
                month_data = year_df[year_df['month'] == month_idx]
                month_name = month_names[month_idx]

                # Calculate month metrics from actual simulation
                month_delivery_hrs = (month_data['delivery'] == 'Yes').sum()
                month_solar_hrs = (month_data['solar_to_load'] > 0).sum()
                month_bess_hrs = (month_data['bess_to_load'] > 0).sum()
                month_dg_hrs = (month_data['dg_state'] == 'ON').sum()
                month_curtailed = month_data['solar_curtailed'].sum()
                month_solar_gen = month_data['solar_mw'].sum()
                month_wastage_pct = (month_curtailed / month_solar_gen * 100) if month_solar_gen > 0 else 0

                # BESS losses for month
                month_charging = month_data[month_data['bess_mw'] < 0]['bess_mw'].abs().sum()
                month_discharging = month_data[month_data['bess_mw'] > 0]['bess_mw'].sum()
                month_charging_loss = month_charging * loss_factor
                month_discharging_loss = month_discharging * loss_factor

                monthly_20yr_data.append({
                    'Year': year,
                    'Month': month_name,
                    'Month_Num': month_idx + 1,
                    'Capacity_MWh': round(effective_capacity, 1),
                    'Capacity_%': round(capacity_factor * 100, 1),
                    'Delivery_Hrs': month_delivery_hrs,
                    'Delivery_%': round(month_delivery_hrs / hours_per_month[month_idx] * 100, 1),
                    'Solar_Hrs': month_solar_hrs,
                    'BESS_Hrs': month_bess_hrs,
                    'DG_Hrs': month_dg_hrs,
                    'Curtailed_MWh': round(month_curtailed, 1),
                    'Wastage_%': round(month_wastage_pct, 1),
                    'Charging_Loss_MWh': round(month_charging_loss, 2),
                    'Discharging_Loss_MWh': round(month_discharging_loss, 2),
                })

        progress_bar.progress(1.0, text="Complete!")

        # Create DataFrames
        yearly_projection_df = pd.DataFrame(yearly_projection_data)
        monthly_20yr_df = pd.DataFrame(monthly_20yr_data)

        # ===========================================
        # 10-YEAR ANNUAL PROJECTION TABLE
        # ===========================================

        st.markdown("### 📅 10-Year Annual Projection")

        # Display first 10 years
        ten_year_df = yearly_projection_df[yearly_projection_df['Year'] <= 10].copy()

        st.dataframe(
            ten_year_df,
            width='stretch',
            hide_index=True,
            column_config={
                'Year': st.column_config.NumberColumn('Year', format='%d'),
                'Capacity (MWh)': st.column_config.NumberColumn('Capacity', format='%.1f'),
                'Capacity %': st.column_config.NumberColumn('Cap %', format='%.1f%%'),
                'Delivery Hrs': st.column_config.NumberColumn('Delivery Hrs', format='%d'),
                'Load Hrs': st.column_config.NumberColumn('Load Hrs', format='%d'),
                'Delivery %': st.column_config.NumberColumn('Delivery %', format='%.1f%%'),
                'DG Hrs': st.column_config.NumberColumn('DG Hrs', format='%d'),
                'Solar Hrs': st.column_config.NumberColumn('Solar Hrs', format='%d'),
                'BESS Hrs': st.column_config.NumberColumn('BESS Hrs', format='%d'),
                'Curtailed (MWh)': st.column_config.NumberColumn('Curtailed', format='%d'),
                'Total Wastage %': st.column_config.NumberColumn('Total Wastage %', format='%.1f%%'),
                'Load Wastage %': st.column_config.NumberColumn('Load Wastage %', format='%.1f%%', help='Wastage during load hours only'),
                'BESS Loss (MWh)': st.column_config.NumberColumn('BESS Loss', format='%d'),
            }
        )

        # Year 10 insight
        year1_data = yearly_projection_df[yearly_projection_df['Year'] == 1].iloc[0]
        year10_data = yearly_projection_df[yearly_projection_df['Year'] == 10].iloc[0]

        if dg_enabled:
            dg_increase = year10_data['DG Hrs'] - year1_data['DG Hrs']
            st.info(f"📉 **Year 10 Impact:** Battery at {year10_data['Capacity (MWh)']:.0f} MWh ({year10_data['Capacity %']:.1f}% of original). "
                    f"DG runtime increases by {dg_increase:,.0f} hrs/year.")
        else:
            delivery_drop = year1_data['Delivery Hrs'] - year10_data['Delivery Hrs']
            st.info(f"📉 **Year 10 Impact:** Battery at {year10_data['Capacity (MWh)']:.0f} MWh ({year10_data['Capacity %']:.1f}% of original). "
                    f"Delivery drops by {delivery_drop:,.0f} hrs/year.")

        # Download buttons in columns
        col_10yr, col_20yr = st.columns(2)

        with col_10yr:
            ten_year_csv = ten_year_df.to_csv(index=False)
            st.download_button(
                "📥 Download 10-Year Projection",
                data=ten_year_csv,
                file_name=f"10year_projection_{bess_capacity}mwh_{duration}hr.csv",
                mime="text/csv",
                width='stretch'
            )

        with col_20yr:
            twenty_year_csv = yearly_projection_df.to_csv(index=False)
            st.download_button(
                "📥 Download 20-Year Projection",
                data=twenty_year_csv,
                file_name=f"20year_projection_{bess_capacity}mwh_{duration}hr.csv",
                mime="text/csv",
                width='stretch'
            )

        # ===========================================
        # 20-YEAR MONTHLY BREAKDOWN
        # ===========================================

        st.divider()
        st.markdown("### 📊 20-Year Monthly Breakdown")
        st.caption("Detailed monthly data for all 20 years with degradation effects.")

        # Download button for monthly data
        monthly_20yr_csv = monthly_20yr_df.to_csv(index=False)
        st.download_button(
            "📥 Download 20-Year Monthly CSV",
            data=monthly_20yr_csv,
            file_name=f"20year_monthly_{bess_capacity}mwh_{duration}hr.csv",
            mime="text/csv",
            width='stretch'
        )

        st.caption(f"Contains {len(monthly_20yr_df)} rows (12 months × 20 years) with actual simulation results.")

        # ===========================================
        # 20-YEAR SUMMARY METRICS TABLE
        # ===========================================

        st.divider()
        st.markdown("### 📈 20-Year Energy Summary")

        # Calculate totals from yearly data
        total_solar_gen = sum(y['solar_gen'] for y in yearly_totals)
        total_dg_gen = sum(y['dg_gen'] for y in yearly_totals)
        total_curtailed = sum(y['curtailed'] for y in yearly_totals)
        total_load_met = sum(y['load_met'] for y in yearly_totals)
        total_load_hrs = sum(y['load_hrs'] for y in yearly_totals)  # Total load hours across 20 years
        total_load_solar = sum(y['load_solar'] for y in yearly_totals)  # Solar during load hours
        total_load_curtailed = sum(y['load_curtailed'] for y in yearly_totals)  # Curtailment during load hours
        total_charging_loss = sum(y['charging_loss'] for y in yearly_totals)
        total_discharging_loss = sum(y['discharging_loss'] for y in yearly_totals)
        total_bess_losses = total_charging_loss + total_discharging_loss

        # Calculate average load hours per year for display
        avg_load_hrs_per_year = total_load_hrs / 20

        # Load period wastage percentage (curtailment during load hours only)
        load_wastage_pct = (total_load_curtailed / total_load_solar * 100) if total_load_solar > 0 else 0

        # Calculate "Missing" per user formula
        net_supply = total_solar_gen + total_dg_gen - total_curtailed
        missing = total_load_met - net_supply

        # Display summary metrics
        summary_cols = st.columns(6)
        summary_cols[0].metric("Total Solar", f"{total_solar_gen:,.0f} MWh")
        summary_cols[1].metric("Total DG", f"{total_dg_gen:,.0f} MWh")
        summary_cols[2].metric("Total Curtailed", f"{total_curtailed:,.0f} MWh", f"{total_curtailed/total_solar_gen*100:.1f}%")
        summary_cols[3].metric("Load Period Wastage", f"{total_load_curtailed:,.0f} MWh", f"{load_wastage_pct:.1f}%")
        summary_cols[4].metric("Total Load Met", f"{total_load_met:,.0f} MWh")
        summary_cols[5].metric("BESS Losses", f"{total_bess_losses:,.0f} MWh")

        # Create detailed summary table
        summary_data = {
            'Metric': [
                '1. Total Solar Generated',
                '2. Total DG Generated',
                '3. Total Curtailed (Solar Wastage)',
                '3a. Load Period Wastage',
                '4. Total Load Met',
                '5. Total BESS Losses',
                '',
                'Net Supply (Solar + DG - Curtailed)',
                'Missing (Load - Net Supply)',
            ],
            'Value (MWh)': [
                f"{total_solar_gen:,.1f}",
                f"{total_dg_gen:,.1f}",
                f"{total_curtailed:,.1f}",
                f"{total_load_curtailed:,.1f}",
                f"{total_load_met:,.1f}",
                f"{total_bess_losses:,.1f}",
                '',
                f"{net_supply:,.1f}",
                f"{missing:,.1f}",
            ],
            'Notes': [
                f"{total_solar_gen/20:,.0f} MWh/year avg",
                f"{total_dg_gen/20:,.0f} MWh/year avg",
                f"{total_curtailed/total_solar_gen*100:.1f}% total wastage rate",
                f"{load_wastage_pct:.1f}% wastage during load hours",
                f"{avg_load_hrs_per_year:,.0f} hrs × {setup['load_mw']} MW × 20 years",
                f"Charging: {total_charging_loss:,.0f} + Discharging: {total_discharging_loss:,.0f}",
                '',
                'Energy available for consumption',
                'Should ≈ -BESS Losses (energy balance)',
            ]
        }

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, width='stretch', hide_index=True)

        # Energy balance verification
        balance_check = abs(missing + total_bess_losses)
        if balance_check < 1000:
            st.success(f"✓ Energy balance verified: Missing ({missing:,.0f}) + BESS Losses ({total_bess_losses:,.0f}) = {missing + total_bess_losses:,.0f} MWh (< 1,000 MWh tolerance)")
        else:
            st.warning(f"⚠ Energy imbalance detected: {balance_check:,.0f} MWh gap")

else:
    st.info("👆 Configure your settings above and click **Run Full Year Simulation** to see results.")


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("### ⚡ Quick Analysis")

    st.markdown("**Setup (from Step 1):**")
    st.markdown(f"- Load: {setup['load_mw']} MW")
    st.markdown(f"- Solar: {setup['solar_capacity_mw']} MWp")
    st.markdown(f"- DG: {'Enabled' if dg_enabled else 'Disabled'}")

    st.markdown("---")

    st.markdown("**Configuration:**")
    st.markdown(f"- BESS: {bess_capacity:.0f} MWh")
    st.markdown(f"- Duration: {duration} hrs")
    st.markdown(f"- Power: {bess_capacity/duration:.0f} MW")
    if dg_enabled:
        st.markdown(f"- DG: {dg_capacity:.0f} MW")

    st.markdown("---")

    if st.button("← Back to Step 1", width='stretch'):
        st.switch_page("pages/8_🚀_Step1_Setup.py")

    st.markdown("---")

    st.caption("Alternative to the 5-step wizard. Use this for quick single-configuration analysis.")
