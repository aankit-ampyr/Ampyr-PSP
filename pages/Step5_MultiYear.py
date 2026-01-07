"""
Step 5: Multi-Year Projection (10/20 Year Analysis)
Run actual simulations for each year with battery degradation to project long-term performance.
"""

import streamlit as st
import numpy as np
import pandas as pd
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date

from src.wizard_state import (
    init_wizard_state, get_wizard_state, get_step_status
)
from src.dispatch_engine import (
    SimulationParams, run_simulation, calculate_metrics
)
from src.data_loader import load_solar_profile
from src.load_builder import build_load_profile


def get_wizard_section(section: str) -> dict:
    """Get a section from wizard state."""
    state = get_wizard_state()
    return state.get(section, {})


# Page config
st.set_page_config(
    page_title="Multi-Year Projection",
    page_icon="📈",
    layout="wide"
)

init_wizard_state()


def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Multi-Year", 'current'),
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

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
HOURS_PER_MONTH = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_solar_profile(setup):
    """Get solar profile from setup configuration."""
    solar_source = setup.get('solar_source', 'default')

    if solar_source == 'upload' and setup.get('solar_csv_data') is not None:
        solar_data = setup['solar_csv_data']
        if isinstance(solar_data, list):
            return solar_data[:8760] if len(solar_data) >= 8760 else solar_data
        return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()

    if 'default_solar_profile' in st.session_state and st.session_state.default_solar_profile is not None:
        solar_data = st.session_state.default_solar_profile
        return solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()

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
    return setup.get('solar_capacity_mw', 100)


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


def run_year_simulation(bess_mwh, bess_power_mw, dg_mw, template_id, setup, rules,
                        solar_profile, load_profile, initial_soc_override=None):
    """Run simulation for a single year with optional SOC override."""
    initial_soc = initial_soc_override if initial_soc_override is not None else setup['bess_initial_soc']

    params = SimulationParams(
        load_profile=load_profile if isinstance(load_profile, list) else load_profile.tolist(),
        solar_profile=solar_profile if isinstance(solar_profile, list) else solar_profile,
        bess_capacity=bess_mwh,
        bess_charge_power=bess_power_mw,
        bess_discharge_power=bess_power_mw,
        bess_efficiency=setup['bess_efficiency'],
        bess_min_soc=setup['bess_min_soc'],
        bess_max_soc=setup['bess_max_soc'],
        bess_initial_soc=initial_soc,
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

    hourly_results = run_simulation(params, template_id, num_hours=8760)
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

st.title("📈 Multi-Year Projection")
st.markdown("### Step 5: 10/20 Year Performance Analysis")

render_step_indicator()

# Get configuration
setup = get_wizard_section('setup')
rules = get_wizard_section('rules')
dg_enabled = setup.get('dg_enabled', False)

# Check if Step 4 results exist
if 'analysis_results' not in st.session_state or st.session_state.analysis_results is None:
    st.warning("Please run a simulation in Step 4 first to configure BESS and DG sizes.")
    if st.button("Go to Step 4"):
        st.switch_page("pages/Step4_Results.py")
    st.stop()

# Get configuration from Step 4
step4_results = st.session_state.analysis_results
bess_capacity = step4_results['bess_mwh']
dg_capacity = step4_results['dg_mw']
container_type = step4_results['container_type']
spec = CONTAINER_SPECS.get(container_type, CONTAINER_SPECS['5mwh_2.5mw'])
duration = spec['duration_hr']

st.divider()

# =============================================================================
# CONFIGURATION FROM STEP 4
# =============================================================================

st.subheader("Configuration from Step 4")

bess_power = bess_capacity / duration
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**Load**")
    st.markdown(f"<span style='font-size:1.5em'>{setup.get('load_mw', 25):.1f} MW</span>", unsafe_allow_html=True)

with col2:
    st.markdown("**Solar Peak**")
    st.markdown(f"<span style='font-size:1.5em'>{get_solar_peak(setup):.1f} MW</span>", unsafe_allow_html=True)

with col3:
    st.markdown("**BESS**")
    st.markdown(f"<span style='font-size:1.5em'>{bess_capacity:.0f} MWh / {bess_power:.1f} MW</span>", unsafe_allow_html=True)

with col4:
    st.markdown("**DG**")
    dg_text = f"{dg_capacity:.0f} MW" if dg_enabled else "Disabled"
    st.markdown(f"<span style='font-size:1.5em'>{dg_text}</span>", unsafe_allow_html=True)

st.divider()

# =============================================================================
# DEGRADATION CONFIGURATION
# =============================================================================

st.subheader("Degradation & Sizing Strategy")

deg_col1, deg_col2, deg_col3, deg_col4 = st.columns(4)

with deg_col1:
    with st.container(border=True):
        st.markdown("##### Factory Degradation")
        st.caption("Initial capacity loss from nameplate")
        factory_degradation_pct = st.select_slider(
            "Factory Degradation %",
            options=[0.0, 4.0, 6.0, 8.0, 10.0],
            value=8.0,
            format_func=lambda x: f"{x}%" if x > 0 else "None",
            key='my_factory_degradation',
            label_visibility="collapsed",
            help="Industry standard: batteries ship at ~92% of nameplate capacity"
        )
        factory_degradation = factory_degradation_pct / 100

with deg_col2:
    with st.container(border=True):
        st.markdown("##### Annual Degradation")
        st.caption("Yearly capacity loss (compound)")
        degradation_pct = st.select_slider(
            "Degradation %/year",
            options=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            value=2.0,
            format_func=lambda x: f"{x}%/year",
            key='my_degradation_rate',
            label_visibility="collapsed"
        )
        degradation_rate = degradation_pct / 100

with deg_col3:
    with st.container(border=True):
        st.markdown("##### Sizing Strategy")
        st.caption("When should BESS meet target?")
        sizing_strategy = st.radio(
            "Strategy",
            options=['year1', 'year10', 'year20'],
            format_func=lambda x: {
                'year1': 'Year 1 BOL',
                'year10': 'Year 10 EOL',
                'year20': 'Year 20 EOL'
            }[x],
            index=0,
            key='my_sizing_strategy',
            label_visibility="collapsed"
        )

with deg_col4:
    with st.container(border=True):
        st.markdown("##### Order Size")
        # Calculate nameplate based on strategy
        # Container block size is 5 MWh
        container_energy = spec['energy_mwh']  # 5 MWh per container
        container_power = spec['power_mw']  # 2.5 or 1.25 MW per container

        if sizing_strategy == 'year1':
            raw_nameplate = bess_capacity / (1 - factory_degradation) if factory_degradation < 1 else bess_capacity
            year1_bol_capacity = bess_capacity
            target_year = 1
        elif sizing_strategy == 'year10':
            year1_bol_capacity = bess_capacity / ((1 - degradation_rate) ** 9)
            raw_nameplate = year1_bol_capacity / (1 - factory_degradation) if factory_degradation < 1 else year1_bol_capacity
            target_year = 10
        else:  # year20
            year1_bol_capacity = bess_capacity / ((1 - degradation_rate) ** 19)
            raw_nameplate = year1_bol_capacity / (1 - factory_degradation) if factory_degradation < 1 else year1_bol_capacity
            target_year = 20

        # Round UP to nearest container block (5 MWh)
        num_containers = math.ceil(raw_nameplate / container_energy)
        nameplate_capacity = num_containers * container_energy
        nameplate_power = num_containers * container_power

        oversize_factor = nameplate_capacity / bess_capacity if bess_capacity > 0 else 1.0

        st.markdown("**Nameplate to Order**")
        st.markdown(f"<span style='font-size:1.5em'>{nameplate_capacity:.0f} MWh / {nameplate_power:.1f} MW</span>", unsafe_allow_html=True)
        st.caption(f"{num_containers} containers")
        if oversize_factor > 1.01:
            st.caption(f"+{(oversize_factor - 1) * 100:.0f}%")
        if sizing_strategy != 'year1':
            st.caption(f"To have **{bess_capacity:.0f} MWh** at Year {target_year}")

# Capacity breakdown
st.markdown("---")
st.markdown("##### Capacity Degradation Breakdown")

breakdown_cols = st.columns(5)

after_factory = nameplate_capacity * (1 - factory_degradation)
year5_cap = after_factory * ((1 - degradation_rate) ** 4)
year10_cap = after_factory * ((1 - degradation_rate) ** 9)
year20_cap = after_factory * ((1 - degradation_rate) ** 19)

# Calculate power values based on container ratio (power degrades proportionally with energy)
power_ratio = container_power / container_energy  # MW per MWh for this container type
after_factory_pwr = after_factory * power_ratio
year5_pwr = year5_cap * power_ratio
year10_pwr = year10_cap * power_ratio
year20_pwr = year20_cap * power_ratio

with breakdown_cols[0]:
    st.markdown(f"**Nameplate**")
    st.markdown(f"<span style='font-size:1.5em'>{nameplate_capacity:.0f} MWh / {nameplate_power:.1f} MW</span>", unsafe_allow_html=True)
    st.caption(f"{num_containers} containers")

with breakdown_cols[1]:
    st.markdown(f"**Year 1 BOL**")
    st.markdown(f"<span style='font-size:1.5em'>{after_factory:.0f} MWh / {after_factory_pwr:.1f} MW</span>", unsafe_allow_html=True)
    st.caption(f"-{factory_degradation_pct:.0f}% factory" if factory_degradation > 0 else "No factory loss")

with breakdown_cols[2]:
    st.markdown(f"**Year 5**")
    st.markdown(f"<span style='font-size:1.5em'>{year5_cap:.0f} MWh / {year5_pwr:.1f} MW</span>", unsafe_allow_html=True)
    st.caption(f"{year5_cap/after_factory*100:.0f}% of BOL")

with breakdown_cols[3]:
    st.markdown(f"**Year 10**")
    st.markdown(f"<span style='font-size:1.5em'>{year10_cap:.0f} MWh / {year10_pwr:.1f} MW</span>", unsafe_allow_html=True)
    st.caption(f"{year10_cap/after_factory*100:.0f}% of BOL")

with breakdown_cols[4]:
    st.markdown(f"**Year 20**")
    st.markdown(f"<span style='font-size:1.5em'>{year20_cap:.0f} MWh / {year20_pwr:.1f} MW</span>", unsafe_allow_html=True)
    st.caption(f"{year20_cap/after_factory*100:.0f}% of BOL")

st.divider()

# =============================================================================
# RUN MULTI-YEAR SIMULATION
# =============================================================================

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_projection = st.button("🚀 Run 20-Year Projection", type="primary", use_container_width=True)

if run_projection:
    # Get profiles
    solar_profile = get_solar_profile(setup)
    load_profile = get_load_profile(setup)

    if solar_profile is None:
        st.error("No solar profile available")
        st.stop()

    template_id = rules.get('inferred_template', 0)

    # Use Year 1 BOL capacity for simulations
    initial_capacity = after_factory
    initial_power = initial_capacity / duration

    # Efficiency calculations
    one_way_eff = (setup['bess_efficiency'] / 100) ** 0.5
    loss_factor = 1 - one_way_eff

    # Progress bar
    progress_bar = st.progress(0, text="Simulating Year 1...")

    yearly_projection_data = []
    monthly_20yr_data = []
    carryover_energy_mwh = None

    for year in range(1, 21):
        progress_bar.progress(year / 20, text=f"Simulating Year {year}...")

        # Compound degradation
        capacity_factor = (1 - degradation_rate) ** (year - 1)
        effective_capacity = initial_capacity * capacity_factor
        effective_power = initial_power * capacity_factor

        # Calculate initial SOC for this year
        if year == 1:
            year_initial_soc = None
        else:
            carryover_soc_pct = (carryover_energy_mwh / effective_capacity) * 100
            year_initial_soc = max(setup['bess_min_soc'], min(setup['bess_max_soc'], carryover_soc_pct))

        # Run simulation
        year_results = run_year_simulation(
            effective_capacity, effective_power, dg_capacity,
            template_id, setup, rules,
            solar_profile, load_profile.tolist() if hasattr(load_profile, 'tolist') else load_profile,
            initial_soc_override=year_initial_soc
        )

        year_df = convert_results_to_dataframe(year_results)

        # Add month column
        year_df['month'] = year_df['hour'].apply(
            lambda h: min(11, (date(2023, 1, 1) + timedelta(hours=h)).month - 1)
        )

        # Calculate year metrics
        year_solar_gen = year_df['solar_mw'].sum()
        year_solar_curtailed = year_df['solar_curtailed'].sum()
        year_delivery_hrs = (year_df['delivery'] == 'Yes').sum()
        year_load_hrs = (year_df['load_mw'] > 0).sum()
        year_dg_hrs = (year_df['dg_state'] == 'ON').sum()
        year_solar_hrs = (year_df['solar_to_load'] > 0).sum()
        year_bess_hrs = (year_df['bess_to_load'] > 0).sum()
        year_wastage_pct = (year_solar_curtailed / year_solar_gen * 100) if year_solar_gen > 0 else 0

        # Energy flows for summary
        year_solar_to_load = year_df['solar_to_load'].sum()
        year_bess_to_load = year_df['bess_to_load'].sum()
        year_dg_to_load = year_df['dg_to_load'].sum()
        year_dg_gen = year_df['dg_output_mw'].sum()
        year_dg_curtailed = year_df['dg_curtailed'].sum()
        year_energy_to_load = year_solar_to_load + year_bess_to_load + year_dg_to_load
        year_delivery_met_mwh = year_delivery_hrs * setup.get('load_mw', 25)

        # Load period wastage
        year_load_df = year_df[year_df['load_mw'] > 0]
        year_load_solar = year_load_df['solar_mw'].sum()
        year_load_curtailed = year_load_df['solar_curtailed'].sum()
        year_load_wastage_pct = (year_load_curtailed / year_load_solar * 100) if year_load_solar > 0 else 0

        # BESS losses
        charging_energy = year_df[year_df['bess_mw'] < 0]['bess_mw'].abs().sum()
        discharging_energy = year_df[year_df['bess_mw'] > 0]['bess_mw'].sum()
        year_charging_loss = charging_energy * loss_factor
        year_discharging_loss = discharging_energy * loss_factor / one_way_eff

        # Get final SOC
        year_final_soc_pct = year_df.iloc[-1]['soc_percent'] / 100

        effective_load_hrs = year_load_hrs if year_load_hrs > 0 else 8760
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
            'Curtailed (MWh)': round(year_solar_curtailed, 0),
            'Total Wastage %': round(year_wastage_pct, 1),
            'Load Wastage %': round(year_load_wastage_pct, 1),
            'BESS Loss (MWh)': round(year_charging_loss + year_discharging_loss, 0),
            # Energy summary fields
            '_solar_gen': year_solar_gen,
            '_dg_gen': year_dg_gen,
            '_solar_to_load': year_solar_to_load,
            '_bess_to_load': year_bess_to_load,
            '_dg_to_load': year_dg_to_load,
            '_dg_curtailed': year_dg_curtailed,
            '_energy_to_load': year_energy_to_load,
            '_delivery_met_mwh': year_delivery_met_mwh,
            '_charging_loss': year_charging_loss,
            '_discharging_loss': year_discharging_loss,
            '_final_soc_pct': year_final_soc_pct,
            '_capacity': effective_capacity,
            '_load_solar': year_load_solar,
            '_load_curtailed': year_load_curtailed,
            '_solar_curtailed': year_solar_curtailed,
        })

        # Save carryover for next year
        carryover_energy_mwh = effective_capacity * year_final_soc_pct

        # Monthly data
        for month_idx in range(12):
            month_data = year_df[year_df['month'] == month_idx]
            month_delivery_hrs = (month_data['delivery'] == 'Yes').sum()
            month_dg_hrs = (month_data['dg_state'] == 'ON').sum()
            month_curtailed = month_data['solar_curtailed'].sum()
            month_solar_gen = month_data['solar_mw'].sum()
            month_wastage_pct = (month_curtailed / month_solar_gen * 100) if month_solar_gen > 0 else 0

            monthly_20yr_data.append({
                'Year': year,
                'Month': MONTH_NAMES[month_idx],
                'Month_Num': month_idx + 1,
                'Capacity_MWh': round(effective_capacity, 1),
                'Delivery_Hrs': month_delivery_hrs,
                'Delivery_%': round(month_delivery_hrs / HOURS_PER_MONTH[month_idx] * 100, 1),
                'DG_Hrs': month_dg_hrs,
                'Curtailed_MWh': round(month_curtailed, 1),
                'Wastage_%': round(month_wastage_pct, 1),
            })

    progress_bar.progress(1.0, text="Complete!")

    # Store results
    st.session_state.multiyear_yearly = pd.DataFrame(yearly_projection_data)
    st.session_state.multiyear_monthly = pd.DataFrame(monthly_20yr_data)

    st.success("20-year projection complete!")
    st.rerun()

# =============================================================================
# DISPLAY RESULTS
# =============================================================================

if 'multiyear_yearly' in st.session_state:
    yearly_df = st.session_state.multiyear_yearly
    monthly_df = st.session_state.multiyear_monthly

    st.divider()

    # 10-Year Table
    st.subheader("📅 10-Year Annual Projection")

    ten_year_df = yearly_df[yearly_df['Year'] <= 10].copy()

    st.dataframe(
        ten_year_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Year': st.column_config.NumberColumn('Year', format='%d'),
            'Capacity (MWh)': st.column_config.NumberColumn('Capacity', format='%.1f'),
            'Capacity %': st.column_config.NumberColumn('Cap %', format='%.1f%%'),
            'Delivery Hrs': st.column_config.NumberColumn('Delivery Hrs', format='%d'),
            'Load Hrs': st.column_config.NumberColumn('Load Hrs', format='%d'),
            'Delivery %': st.column_config.ProgressColumn('Delivery %', min_value=0, max_value=100, format='%.1f%%'),
            'DG Hrs': st.column_config.NumberColumn('DG Hrs', format='%d'),
            'Solar Hrs': st.column_config.NumberColumn('Solar Hrs', format='%d'),
            'BESS Hrs': st.column_config.NumberColumn('BESS Hrs', format='%d'),
            'Curtailed (MWh)': st.column_config.NumberColumn('Curtailed', format='%d'),
            'Total Wastage %': st.column_config.NumberColumn('Total Wastage %', format='%.1f%%'),
            'Load Wastage %': st.column_config.NumberColumn('Load Wastage %', format='%.1f%%'),
            'BESS Loss (MWh)': st.column_config.NumberColumn('BESS Loss', format='%d'),
        }
    )

    # Year 1 vs 10 insight
    year1_data = yearly_df[yearly_df['Year'] == 1].iloc[0]
    year10_data = yearly_df[yearly_df['Year'] == 10].iloc[0]

    if dg_enabled:
        dg_increase = year10_data['DG Hrs'] - year1_data['DG Hrs']
        st.info(f"📉 **Year 10 Impact:** Battery at {year10_data['Capacity (MWh)']:.0f} MWh ({year10_data['Capacity %']:.1f}% of original). "
                f"DG runtime increases by {dg_increase:,.0f} hrs/year.")
    else:
        delivery_drop = year1_data['Delivery %'] - year10_data['Delivery %']
        st.info(f"📉 **Year 10 Impact:** Battery at {year10_data['Capacity (MWh)']:.0f} MWh ({year10_data['Capacity %']:.1f}% of original). "
                f"Delivery drops from {year1_data['Delivery %']:.1f}% to {year10_data['Delivery %']:.1f}%.")

    # 10-Year Download
    export_columns = [c for c in yearly_df.columns if not c.startswith('_')]
    ten_year_export_df = yearly_df[yearly_df['Year'] <= 10][export_columns]
    ten_year_csv = ten_year_export_df.to_csv(index=False)
    st.download_button(
        "📥 Download 10-Year Projection",
        data=ten_year_csv,
        file_name=f"10year_projection_{bess_capacity:.0f}mwh_{duration}hr.csv",
        mime="text/csv",
        key="download_10yr"
    )

    st.divider()

    # 20-Year Table
    st.subheader("📅 20-Year Annual Projection")

    st.dataframe(
        yearly_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Year': st.column_config.NumberColumn('Year', format='%d'),
            'Capacity (MWh)': st.column_config.NumberColumn('Capacity', format='%.1f'),
            'Capacity %': st.column_config.NumberColumn('Cap %', format='%.1f%%'),
            'Delivery Hrs': st.column_config.NumberColumn('Delivery Hrs', format='%d'),
            'Load Hrs': st.column_config.NumberColumn('Load Hrs', format='%d'),
            'Delivery %': st.column_config.ProgressColumn('Delivery %', min_value=0, max_value=100, format='%.1f%%'),
            'DG Hrs': st.column_config.NumberColumn('DG Hrs', format='%d'),
            'Solar Hrs': st.column_config.NumberColumn('Solar Hrs', format='%d'),
            'BESS Hrs': st.column_config.NumberColumn('BESS Hrs', format='%d'),
            'Curtailed (MWh)': st.column_config.NumberColumn('Curtailed', format='%d'),
            'Total Wastage %': st.column_config.NumberColumn('Total Wastage %', format='%.1f%%'),
            'Load Wastage %': st.column_config.NumberColumn('Load Wastage %', format='%.1f%%'),
            'BESS Loss (MWh)': st.column_config.NumberColumn('BESS Loss', format='%d'),
        }
    )

    # Year 20 insight
    year20_data = yearly_df[yearly_df['Year'] == 20].iloc[0]
    st.warning(f"📉 **Year 20:** Battery at {year20_data['Capacity (MWh)']:.0f} MWh ({year20_data['Capacity %']:.1f}% of original). "
               f"Delivery at {year20_data['Delivery %']:.1f}%.")

    # 20-Year Download
    twenty_year_export_df = yearly_df[export_columns]
    twenty_year_csv = twenty_year_export_df.to_csv(index=False)
    st.download_button(
        "📥 Download 20-Year Projection",
        data=twenty_year_csv,
        file_name=f"20year_projection_{bess_capacity:.0f}mwh_{duration}hr.csv",
        mime="text/csv",
        key="download_20yr"
    )

    # =============================================================================
    # 20-YEAR ENERGY SUMMARY
    # =============================================================================
    st.divider()
    st.subheader("📊 20-Year Energy Summary")

    # Get yearly data for energy calculations
    yearly_data = yearly_df.to_dict('records')

    # Calculate totals from yearly data (use raw _ values for accuracy)
    total_solar_gen = sum(y.get('_solar_gen', 0) for y in yearly_data)
    total_dg_gen = sum(y.get('_dg_gen', 0) for y in yearly_data)
    total_dg_curtailed = sum(y.get('_dg_curtailed', 0) for y in yearly_data)
    total_solar_curtailed = sum(y.get('_solar_curtailed', 0) for y in yearly_data)
    total_curtailed = total_solar_curtailed + total_dg_curtailed
    total_delivery_met = sum(y.get('_delivery_met_mwh', 0) for y in yearly_data)
    total_energy_to_load = sum(y.get('_energy_to_load', 0) for y in yearly_data)
    total_solar_to_load = sum(y.get('_solar_to_load', 0) for y in yearly_data)
    total_bess_to_load = sum(y.get('_bess_to_load', 0) for y in yearly_data)
    total_dg_to_load = sum(y.get('_dg_to_load', 0) for y in yearly_data)
    total_load_hrs = sum(y.get('Load Hrs', 0) for y in yearly_data)
    total_load_solar = sum(y.get('_load_solar', 0) for y in yearly_data)
    total_load_curtailed = sum(y.get('_load_curtailed', 0) for y in yearly_data)
    total_charging_loss = sum(y.get('_charging_loss', 0) for y in yearly_data)
    total_discharging_loss = sum(y.get('_discharging_loss', 0) for y in yearly_data)
    total_bess_losses = total_charging_loss + total_discharging_loss

    # Initial and final BESS energy
    initial_soc_pct = setup['bess_initial_soc'] / 100
    initial_bess_energy = bess_capacity * initial_soc_pct

    year_20_capacity = yearly_data[-1].get('_capacity', bess_capacity) if yearly_data else bess_capacity
    year_20_final_soc = yearly_data[-1].get('_final_soc_pct', initial_soc_pct) if yearly_data else initial_soc_pct
    final_bess_energy = year_20_capacity * year_20_final_soc

    load_wastage_pct = (total_load_curtailed / total_load_solar * 100) if total_load_solar > 0 else 0

    # Energy balance
    total_energy_in = total_solar_gen + total_dg_gen + initial_bess_energy
    total_energy_out = total_energy_to_load + total_solar_curtailed + total_dg_curtailed + total_bess_losses + final_bess_energy
    balance_difference = total_energy_in - total_energy_out

    # Display summary metrics
    summary_cols = st.columns(6)
    summary_cols[0].metric("Total Solar", f"{total_solar_gen:,.0f} MWh")
    summary_cols[1].metric("Total DG", f"{total_dg_gen:,.0f} MWh")
    summary_cols[2].metric("Total Curtailed", f"{total_curtailed:,.0f} MWh",
                           f"{total_curtailed/total_solar_gen*100:.1f}%" if total_solar_gen > 0 else "N/A")
    summary_cols[3].metric("Load Wastage", f"{total_load_curtailed:,.0f} MWh", f"{load_wastage_pct:.1f}%")
    summary_cols[4].metric("Delivery Met", f"{total_delivery_met:,.0f} MWh")
    summary_cols[5].metric("BESS Losses", f"{total_bess_losses:,.0f} MWh")

    # Create detailed summary table
    summary_table_data = {
        'Category': [
            'ENERGY IN', '', '', '', '',
            'ENERGY OUT', '', '', '', '', '',
            'BALANCE',
        ],
        'Item': [
            'Solar Generated',
            'DG Generated',
            'Initial BESS Energy',
            'Total Energy In',
            '',
            'Energy to Load',
            'Solar Curtailed',
            'DG Curtailed',
            'BESS Losses',
            'Final BESS Energy',
            'Total Energy Out',
            'Difference (In - Out)',
        ],
        'Value (MWh)': [
            f"{total_solar_gen:,.0f}",
            f"{total_dg_gen:,.0f}",
            f"{initial_bess_energy:,.0f}",
            f"{total_energy_in:,.0f}",
            '',
            f"{total_energy_to_load:,.0f}",
            f"{total_solar_curtailed:,.0f}",
            f"{total_dg_curtailed:,.0f}",
            f"{total_bess_losses:,.0f}",
            f"{final_bess_energy:,.0f}",
            f"{total_energy_out:,.0f}",
            f"{balance_difference:,.0f}",
        ],
        'Details': [
            f"{total_solar_gen/20:,.0f} MWh/year avg",
            f"{total_dg_gen/20:,.0f} MWh/year avg" if total_dg_gen > 0 else "DG disabled",
            f"{bess_capacity:.0f} MWh × {setup['bess_initial_soc']:.0f}% SOC",
            '',
            '',
            f"Solar: {total_solar_to_load:,.0f} + BESS: {total_bess_to_load:,.0f} + DG: {total_dg_to_load:,.0f}",
            f"{total_solar_curtailed/total_solar_gen*100:.1f}% of solar" if total_solar_gen > 0 else "N/A",
            f"{total_dg_curtailed/total_dg_gen*100:.1f}% of DG" if total_dg_gen > 0 else "N/A",
            f"Charge: {total_charging_loss:,.0f} + Discharge: {total_discharging_loss:,.0f}",
            f"{year_20_capacity:.0f} MWh × {year_20_final_soc*100:.0f}% SOC (Year 20 end)",
            '',
            'Should be ~0 if balanced',
        ]
    }

    summary_table_df = pd.DataFrame(summary_table_data)
    st.dataframe(summary_table_df, use_container_width=True, hide_index=True)

    # Energy balance verification
    if abs(balance_difference) < 100:
        st.success(f"Energy balance verified: {balance_difference:,.0f} MWh difference (within tolerance)")
    else:
        st.warning(f"Energy balance issue: {balance_difference:,.0f} MWh difference detected")

    # =============================================================================
    # MONTHLY DATA DOWNLOAD
    # =============================================================================
    st.divider()
    monthly_csv = monthly_df.to_csv(index=False)
    st.download_button(
        "📥 Download Monthly Detail CSV",
        data=monthly_csv,
        file_name=f"20year_monthly_{bess_capacity:.0f}mwh_{duration}hr.csv",
        mime="text/csv",
        key="download_monthly"
    )

else:
    st.info("Configure degradation settings above and click 'Run 20-Year Projection' to see results.")

st.divider()

# Navigation
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back to Results", use_container_width=True):
        st.switch_page("pages/Step4_Results.py")

# Sidebar
with st.sidebar:
    st.markdown("### Configuration")
    st.markdown(f"**Load:** {setup.get('load_mw', 25):.1f} MW")
    st.markdown(f"**Solar Peak:** {get_solar_peak(setup):.1f} MW")
    bess_power_sidebar = bess_capacity / duration
    st.markdown(f"**BESS:** {bess_capacity:.0f} MWh / {bess_power_sidebar:.1f} MW")
    if dg_enabled and dg_capacity > 0:
        st.markdown(f"**DG:** {dg_capacity:.0f} MW")
    else:
        st.markdown("**DG:** Disabled")

    st.markdown("---")
    st.markdown("### Degradation Model")
    st.markdown(f"**Factory:** {factory_degradation_pct:.0f}%")
    st.markdown(f"**Annual:** {degradation_pct:.1f}%/year")
    st.markdown(f"**Strategy:** {sizing_strategy.replace('year', 'Year ')}")
