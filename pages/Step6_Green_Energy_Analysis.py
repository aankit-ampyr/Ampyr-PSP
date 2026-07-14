"""
Step 6: Green Energy Analysis

4D optimization sweep (Solar × BESS × Container × DG) to find configurations
meeting green energy targets with acceptable wastage.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

from src.wizard_state import get_wizard_state
from src.data_loader import load_solar_profile_by_name, get_base_solar_peak_capacity
from src.load_builder import build_load_profile
from src.green_energy_optimizer import (
    run_green_energy_optimization,
    GreenEnergyOptimizationParams,
    create_results_dataframe,
    CONTAINER_SPECS,
    parse_template_id
)


# =============================================================================
# CONSTANTS
# =============================================================================

CAPACITY_STEP_MWH = 5  # Discrete container increment

# Multi-year monthly sheet (column set + month bucketing match Step 5 exactly)
MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
HOURS_PER_MONTH = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
    from src.data_loader import load_solar_profile

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


def compute_green_multiyear(selected_solar, selected_bess, selected_duration,
                            selected_dg, setup, rules, degradation_rate, num_years=20):
    """Project one green-energy config over N years with BESS-only degradation.

    Solar is scaled to ``selected_solar`` MWp and held flat across all years; only
    BESS usable capacity/power degrades compound-annually. SOC carries over between
    years. Returns a per-year DataFrame (energy-based Green %, Delivery %, DG,
    wastage) or ``None`` if the solar profile cannot be loaded/scaled.

    Pure (no Streamlit calls) so it can be exercised headlessly.
    """
    from src.dispatch_engine import SimulationParams, run_simulation
    from src.data_loader import scale_solar_profile

    base_solar = get_solar_profile(setup)
    if base_solar is None or len(base_solar) == 0:
        return None, None, None
    base_peak = get_base_solar_peak_capacity(base_solar)
    if base_peak <= 0:
        return None, None, None
    solar_profile = scale_solar_profile(base_solar, base_peak, selected_solar)

    load_profile = get_load_profile(setup)
    load_profile = load_profile.tolist() if hasattr(load_profile, 'tolist') else load_profile

    template_id = parse_template_id(rules.get('inferred_template', 'T0'))
    power_mw = selected_bess / selected_duration if selected_bess > 0 else 0.0

    min_soc = setup.get('bess_min_soc', 5)
    max_soc = setup.get('bess_max_soc', 95)

    # Efficiency split for BESS loss accounting (mirrors Step 5)
    load_mw = setup.get('load_mw', 25)
    one_way_eff = (setup.get('bess_efficiency', 87) / 100) ** 0.5
    loss_factor = 1 - one_way_eff

    # 20-year energy-balance running totals (feed the Step 5 energy-summary table)
    tot_solar_gen = tot_dg_gen = tot_solar_curtailed = tot_dg_curtailed = 0.0
    tot_solar_to_load = tot_bess_to_load = tot_dg_to_load = tot_energy_to_load = 0.0
    tot_load_solar = tot_load_curtailed = 0.0
    tot_charging_loss = tot_discharging_loss = tot_delivery_met = 0.0
    last_capacity = selected_bess
    last_final_soc = setup.get('bess_initial_soc', 50) / 100

    # Hour -> calendar-month index (0-11); built once, sized to the sim length,
    # using Step 5's exact datetime mapping so the monthly buckets match Step 5.
    month_idx_by_hour = []

    rows = []
    monthly_rows = []
    carryover_energy_mwh = None
    for year in range(1, num_years + 1):
        capacity_factor = (1 - degradation_rate) ** (year - 1)
        eff_capacity = selected_bess * capacity_factor
        eff_power = power_mw * capacity_factor

        if year == 1 or carryover_energy_mwh is None or eff_capacity <= 0:
            init_soc = setup.get('bess_initial_soc', 50)
        else:
            carry_pct = (carryover_energy_mwh / eff_capacity) * 100
            init_soc = max(min_soc, min(max_soc, carry_pct))

        params = SimulationParams(
            load_profile=load_profile,
            solar_profile=solar_profile,
            bess_capacity=eff_capacity,
            bess_charge_power=eff_power,
            bess_discharge_power=eff_power,
            bess_efficiency=setup.get('bess_efficiency', 87),
            bess_min_soc=min_soc,
            bess_max_soc=max_soc,
            bess_initial_soc=init_soc,
            bess_daily_cycle_limit=setup.get('bess_daily_cycle_limit', 2.0),
            bess_enforce_cycle_limit=setup.get('bess_enforce_cycle_limit', False),
            dg_enabled=setup.get('dg_enabled', False) and selected_dg > 0,
            dg_capacity=selected_dg,
            dg_charges_bess=rules.get('dg_charges_bess', False),
            dg_load_priority=rules.get('dg_load_priority', 'bess_first'),
            dg_takeover_mode=rules.get('dg_takeover_mode', False),
            night_start_hour=rules.get('night_start', 18),
            night_end_hour=rules.get('night_end', 6),
            day_start_hour=rules.get('day_start', 6),
            day_end_hour=rules.get('day_end', 18),
            blackout_start_hour=rules.get('blackout_start', 0),
            blackout_end_hour=rules.get('blackout_end', 0),
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

        results = run_simulation(params, template_id, num_hours=8760)
        if not month_idx_by_hour:
            max_t = max(h.t for h in results)
            month_idx_by_hour = [min(11, (date(2023, 1, 1) + timedelta(hours=t)).month - 1)
                                 for t in range(max_t + 1)]

        solar_gen = sum(h.solar for h in results)
        solar_curtailed = sum(h.solar_curtailed for h in results)
        solar_to_load = sum(h.solar_to_load for h in results)
        bess_to_load = sum(h.bess_to_load for h in results)
        dg_to_load = sum(h.dg_to_load for h in results)
        delivery_hrs = sum(1 for h in results if h.load > 0 and h.unserved < 0.001)
        load_hrs = sum(1 for h in results if h.load > 0)
        dg_hrs = sum(1 for h in results if h.dg_running)

        # Energy-balance accumulators (mirror Step 5's 20-year energy summary)
        dg_gen = sum(h.dg_to_load + h.dg_to_bess + h.dg_curtailed for h in results)
        dg_curtailed = sum(h.dg_curtailed for h in results)
        load_solar = sum(h.solar for h in results if h.load > 0)
        load_curtailed = sum(h.solar_curtailed for h in results if h.load > 0)
        charging_energy = sum(-h.bess_power for h in results if h.bess_power < 0)
        discharging_energy = sum(h.bess_power for h in results if h.bess_power > 0)
        tot_solar_gen += solar_gen
        tot_dg_gen += dg_gen
        tot_solar_curtailed += solar_curtailed
        tot_dg_curtailed += dg_curtailed
        tot_solar_to_load += solar_to_load
        tot_bess_to_load += bess_to_load
        tot_dg_to_load += dg_to_load
        tot_energy_to_load += solar_to_load + bess_to_load + dg_to_load
        tot_load_solar += load_solar
        tot_load_curtailed += load_curtailed
        tot_charging_loss += charging_energy * loss_factor
        tot_discharging_loss += (discharging_energy * loss_factor / one_way_eff) if one_way_eff else 0.0
        tot_delivery_met += delivery_hrs * load_mw

        green_energy = solar_to_load + bess_to_load
        total_to_load = green_energy + dg_to_load
        green_pct = (green_energy / total_to_load * 100) if total_to_load > 0 else 0.0
        delivery_pct = min(100.0, delivery_hrs / load_hrs * 100) if load_hrs > 0 else 0.0
        wastage_pct = (solar_curtailed / solar_gen * 100) if solar_gen > 0 else 0.0

        rows.append({
            'Year': year,
            'Capacity (MWh)': round(eff_capacity, 1),
            'Capacity %': round(capacity_factor * 100, 1),
            'Green % (Energy)': round(green_pct, 1),
            'Delivery %': round(delivery_pct, 1),
            'Green Energy to Load (MWh)': round(green_energy, 1),
            'DG to Load (MWh)': round(dg_to_load, 1),
            'DG Hrs': dg_hrs,
            'Wastage %': round(wastage_pct, 1),
        })

        # Monthly detail rows (columns identical to the Step 5 monthly sheet)
        m_solar_gen = [0.0] * 12
        m_curtailed = [0.0] * 12
        m_green = [0.0] * 12
        m_dg_to_load = [0.0] * 12
        m_delivery_hrs = [0] * 12
        m_dg_hrs = [0] * 12
        for h in results:
            mi = month_idx_by_hour[h.t]
            m_solar_gen[mi] += h.solar
            m_curtailed[mi] += h.solar_curtailed
            m_green[mi] += h.solar_to_load + h.bess_to_load
            m_dg_to_load[mi] += h.dg_to_load
            if h.load > 0 and h.unserved < 0.001:
                m_delivery_hrs[mi] += 1
            if h.dg_running:
                m_dg_hrs[mi] += 1
        for mi in range(12):
            m_wastage = (m_curtailed[mi] / m_solar_gen[mi] * 100) if m_solar_gen[mi] > 0 else 0
            monthly_rows.append({
                'Year': year,
                'Month': MONTH_NAMES[mi],
                'Month_Num': mi + 1,
                'Capacity_MWh': round(eff_capacity, 1),
                'Delivery_Hrs': m_delivery_hrs[mi],
                'Delivery_%': round(m_delivery_hrs[mi] / HOURS_PER_MONTH[mi] * 100, 1),
                'DG_Hrs': m_dg_hrs[mi],
                'Green_Energy_to_Load_MWh': round(m_green[mi], 1),
                'DG_to_Load_MWh': round(m_dg_to_load[mi], 1),
                'Curtailed_MWh': round(m_curtailed[mi], 1),
                'Wastage_%': round(m_wastage, 1),
            })

        final_soc_pct = results[-1].soc_pct / 100 if results else 0.0
        carryover_energy_mwh = eff_capacity * final_soc_pct
        last_capacity = eff_capacity
        last_final_soc = final_soc_pct

    # 20-year energy balance (In - Out should be ~0 if energy is conserved)
    initial_soc_frac = setup.get('bess_initial_soc', 50) / 100
    initial_bess_energy = selected_bess * initial_soc_frac
    final_bess_energy = last_capacity * last_final_soc
    total_bess_losses = tot_charging_loss + tot_discharging_loss
    total_curtailed = tot_solar_curtailed + tot_dg_curtailed
    total_energy_in = tot_solar_gen + tot_dg_gen + initial_bess_energy
    total_energy_out = (tot_energy_to_load + tot_solar_curtailed + tot_dg_curtailed
                        + total_bess_losses + final_bess_energy)
    energy_summary = {
        'num_years': num_years,
        'total_solar_gen': tot_solar_gen,
        'total_dg_gen': tot_dg_gen,
        'total_solar_curtailed': tot_solar_curtailed,
        'total_dg_curtailed': tot_dg_curtailed,
        'total_curtailed': total_curtailed,
        'total_energy_to_load': tot_energy_to_load,
        'total_solar_to_load': tot_solar_to_load,
        'total_bess_to_load': tot_bess_to_load,
        'total_dg_to_load': tot_dg_to_load,
        'total_delivery_met': tot_delivery_met,
        'total_load_solar': tot_load_solar,
        'total_load_curtailed': tot_load_curtailed,
        'total_charging_loss': tot_charging_loss,
        'total_discharging_loss': tot_discharging_loss,
        'total_bess_losses': total_bess_losses,
        'initial_bess_energy': initial_bess_energy,
        'final_bess_energy': final_bess_energy,
        'final_capacity': last_capacity,
        'final_soc_pct': last_final_soc,
        'initial_soc_pct': initial_soc_frac,
        'bol_capacity': selected_bess,
        'load_wastage_pct': (tot_load_curtailed / tot_load_solar * 100) if tot_load_solar > 0 else 0.0,
        'total_energy_in': total_energy_in,
        'total_energy_out': total_energy_out,
        'balance_difference': total_energy_in - total_energy_out,
    }

    return pd.DataFrame(rows), pd.DataFrame(monthly_rows), energy_summary


def main():
    st.title("Green Energy Analysis")
    st.markdown("""
    Find optimal Solar + BESS + DG configurations to meet green energy targets
    with acceptable wastage levels.
    """)

    # Get wizard state
    wizard_state = get_wizard_state()
    setup = wizard_state.get('setup', {})
    rules = wizard_state.get('rules', {})

    # Check prerequisites
    if not setup or not rules:
        st.warning("Please complete Step 1 (Setup) and Step 2 (Rules) first.")
        return

    # Get DG enabled status and container types from setup
    dg_enabled = setup.get('dg_enabled', False)
    container_types = setup.get('bess_container_types', ['5mwh_2.5mw', '5mwh_1.25mw'])

    # Get inferred template from Step 2
    template_id = rules.get('inferred_template', 'T0')

    # Template descriptions
    template_descriptions = {
        'T0': 'Solar + BESS Only (No DG)',
        'T1': 'Green Priority (DG as last resort)',
        'T2': 'DG Night Charge (Proactive charging)',
        'T3': 'DG Blackout Window',
        'T4': 'DG Emergency Only (SOC-triggered)',
        'T5': 'DG Day Charge (SOC-triggered)',
        'T6': 'DG Night SOC Trigger',
        0: 'Solar + BESS Only (No DG)',
        1: 'Green Priority (DG as last resort)',
        2: 'DG Night Charge (Proactive charging)',
        3: 'DG Blackout Window',
        4: 'DG Emergency Only (SOC-triggered)',
        5: 'DG Day Charge (SOC-triggered)',
        6: 'DG Night SOC Trigger',
    }

    # ===========================
    # SECTION 1: Dispatch Template (from Step 2)
    # ===========================
    st.header("1. Dispatch Strategy")
    template_desc = template_descriptions.get(template_id, f'Template {template_id}')
    st.info(f"Using dispatch template **{template_id}**: {template_desc} (configured in Step 2)")

    st.divider()

    # ===========================
    # SECTION 2: Configuration Ranges
    # ===========================
    st.header("2. Configuration Ranges")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Solar Capacity Range")
        solar_min = st.number_input(
            "Minimum Solar (MWp)",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            key='solar_min'
        )

        # Validate and fix session state to prevent min_value conflict
        if 'solar_max' in st.session_state and st.session_state.solar_max < solar_min:
            st.session_state.solar_max = max(150, solar_min)

        solar_max = st.number_input(
            "Maximum Solar (MWp)",
            min_value=solar_min,
            max_value=500,
            value=max(150, solar_min),
            step=10,
            key='solar_max'
        )
        solar_step = st.number_input(
            "Solar Step (MWp)",
            min_value=5,
            max_value=50,
            value=25,
            step=5,
            key='solar_step'
        )

    with col2:
        st.subheader("BESS Capacity Range")
        bess_min = st.number_input(
            "Minimum BESS (MWh)",
            min_value=0,
            max_value=500,
            value=0,
            step=5,
            key='bess_min'
        )

        # Validate and fix session state to prevent min_value conflict
        if 'bess_max' in st.session_state and st.session_state.bess_max < bess_min:
            st.session_state.bess_max = max(150, bess_min)

        bess_max = st.number_input(
            "Maximum BESS (MWh)",
            min_value=bess_min,
            max_value=1000,
            value=max(150, bess_min),
            step=5,
            key='bess_max'
        )

    # Duration classes from container types
    st.markdown("**Duration Classes**")
    if container_types:
        duration_labels = [f"{CONTAINER_SPECS[ct]['duration_hr']}-hour ({CONTAINER_SPECS[ct]['label']})"
                          for ct in container_types if ct in CONTAINER_SPECS]
        st.info(f"Evaluating: {', '.join(duration_labels)}")
    else:
        container_types = ['5mwh_2.5mw', '5mwh_1.25mw']
        st.info("Evaluating: 2-hour (0.5C), 4-hour (0.25C)")

    st.divider()

    # ===========================
    # SECTION 3: DG Range (if enabled)
    # ===========================
    if dg_enabled:
        st.header("3. DG Capacity Range")

        col3, col4 = st.columns(2)

        load_mw = int(setup.get('load_mw', 25))

        with col3:
            dg_min = st.number_input(
                "Minimum DG (MW)",
                min_value=0,
                max_value=200,
                value=load_mw,
                step=5,
                key='dg_min'
            )

        # Validate and fix session state to prevent min_value conflict
        if 'dg_max' in st.session_state and st.session_state.dg_max < dg_min:
            st.session_state.dg_max = max(load_mw, dg_min)

        with col4:
            dg_max = st.number_input(
                "Maximum DG (MW)",
                min_value=dg_min,
                max_value=200,
                value=max(load_mw, dg_min),
                step=5,
                key='dg_max'
            )

        dg_step = st.selectbox(
            "DG Step Size (MW)",
            options=[5, 10, 25],
            index=0,
            key='dg_step'
        )

        st.divider()
    else:
        st.header("3. DG Configuration")
        st.info("DG is disabled in Step 1. Running Solar + BESS only configurations.")
        dg_min, dg_max, dg_step = 0, 0, 5

    # ===========================
    # SECTION 4: Green Energy Targets
    # ===========================
    st.header("4. Green Energy Targets")

    col5, col6 = st.columns(2)

    with col5:
        green_target = st.number_input(
            "Minimum Green Energy %",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=5.0,
            help="Minimum percentage of energy delivered from solar + BESS (MWh-based)"
        )

    with col6:
        enable_wastage_limit = st.checkbox(
            "Set Maximum Wastage %",
            value=True,
            help="Limit solar curtailment as percentage of total solar generation"
        )

        if enable_wastage_limit:
            max_wastage = st.number_input(
                "Maximum Wastage %",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
                step=5.0
            )
        else:
            max_wastage = None

    st.divider()

    # ===========================
    # SECTION 5: Simulation Summary
    # ===========================
    st.header("5. Simulation Summary")

    # Calculate number of configurations
    num_solar = int((solar_max - solar_min) / solar_step) + 1
    num_bess = int((bess_max - bess_min) / CAPACITY_STEP_MWH) + 1
    num_containers = len(container_types)
    num_dg = int((dg_max - dg_min) / dg_step) + 1 if dg_enabled and dg_step > 0 else 1
    total_configs = num_solar * num_bess * num_containers * num_dg

    col7, col8, col9, col10 = st.columns(4)
    col7.metric("Solar Sizes", f"{num_solar}")
    col8.metric("BESS Sizes", f"{num_bess}")
    col9.metric("Durations", f"{num_containers}")
    col10.metric("DG Sizes", f"{num_dg}")

    st.metric("Total Configurations", f"{total_configs:,}")

    # Estimate time
    est_seconds = total_configs * 0.05  # ~50ms per config
    if est_seconds < 60:
        est_time = f"~{int(est_seconds)} seconds"
    else:
        est_time = f"~{int(est_seconds / 60)} minutes"
    st.caption(f"Estimated runtime: {est_time}")

    if total_configs > 500:
        st.warning(f"Large simulation count ({total_configs}). Consider increasing step sizes for faster results.")

    st.divider()

    # ===========================
    # SECTION 6: Run Optimization
    # ===========================
    if st.button("Run Green Energy Analysis", type="primary", width='stretch'):
        # Load data
        with st.spinner("Loading solar and load profiles..."):
            # Load solar profile
            solar_source = setup.get('solar_source', 'inputs')
            if solar_source in ('inputs', 'file', 'default'):
                solar_file = setup.get('solar_selected_file', 'Solar Profile.csv')
                base_solar_profile = load_solar_profile_by_name(solar_file)
            elif solar_source == 'upload' and setup.get('solar_csv_data') is not None:
                solar_data = setup['solar_csv_data']
                if isinstance(solar_data, list):
                    base_solar_profile = solar_data[:8760] if len(solar_data) >= 8760 else solar_data
                else:
                    base_solar_profile = solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
            else:
                # Fallback to default
                base_solar_profile = load_solar_profile_by_name('Solar Profile.csv')

            if base_solar_profile is None or len(base_solar_profile) == 0:
                st.error("Failed to load solar profile. Please check Step 1 configuration.")
                return

            base_solar_capacity = get_base_solar_peak_capacity(base_solar_profile)

            if base_solar_capacity <= 0:
                st.error("Solar profile has no generation data (peak capacity is 0). Please check your solar profile in Step 1.")
                return

            # Build load profile
            load_profile = get_load_profile(setup)

        # Build optimization parameters
        opt_params = GreenEnergyOptimizationParams(
            solar_min_mw=solar_min,
            solar_max_mw=solar_max,
            solar_step_mw=solar_step,
            bess_min_mwh=float(bess_min),
            bess_max_mwh=float(bess_max),
            bess_step_mwh=float(CAPACITY_STEP_MWH),
            dg_enabled=dg_enabled,
            dg_min_mw=float(dg_min),
            dg_max_mw=float(dg_max),
            dg_step_mw=float(dg_step),
            container_types=container_types,
            green_energy_target_pct=green_target,
            max_wastage_pct=max_wastage,
            dispatch_template=template_id
        )

        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(current, total, message):
            progress_bar.progress(current / total)
            status_text.text(f"{message} ({current}/{total})")

        # Run optimization
        with st.spinner("Running optimization..."):
            results = run_green_energy_optimization(
                base_solar_profile=base_solar_profile,
                base_solar_capacity_mw=base_solar_capacity,
                load_profile=load_profile.tolist() if hasattr(load_profile, 'tolist') else load_profile,
                bess_config=setup,
                dg_config=setup,
                dispatch_rules=rules,
                opt_params=opt_params,
                progress_callback=progress_callback
            )

        progress_bar.empty()
        status_text.empty()

        # Store in session state
        st.session_state['green_energy_results'] = results
        st.session_state['green_energy_target'] = green_target
        st.session_state['green_energy_wastage'] = max_wastage
        st.success("Optimization complete!")

    # ===========================
    # SECTION 7: Display Results
    # ===========================
    if 'green_energy_results' in st.session_state:
        results = st.session_state['green_energy_results']
        green_target = st.session_state.get('green_energy_target', 50.0)
        max_wastage = st.session_state.get('green_energy_wastage', 20.0)

        st.header("Results")

        # Summary metrics
        summary = results['summary']

        col11, col12, col13, col14, col15 = st.columns(5)
        with col11:
            st.metric("Configs Tested", f"{summary['total_configs_tested']:,}")
        with col12:
            st.metric("Viable Configs", f"{summary['viable_count']:,}")
        with col13:
            if summary['min_solar_for_target']:
                st.metric("Min Solar", f"{summary['min_solar_for_target']:.0f} MWp")
            else:
                st.metric("Min Solar", "N/A")
        with col14:
            if summary['min_bess_for_target'] is not None:
                st.metric("Min BESS", f"{summary['min_bess_for_target']:.0f} MWh")
            else:
                st.metric("Min BESS", "N/A")
        with col15:
            if summary.get('min_dg_for_target') is not None:
                st.metric("Min DG", f"{summary['min_dg_for_target']:.0f} MW")
            else:
                st.metric("Min DG", "N/A")

        st.divider()

        # Create DataFrames
        df_all = create_results_dataframe(results['all_results'])
        df_viable = create_results_dataframe(results['viable_configs']) if results['viable_configs'] else None

        # ===========================
        # Results Table (Step 3 format)
        # ===========================
        st.subheader("All Configurations")

        # Filters section
        st.markdown("**Filters**")

        # Row 1: Checkbox filters
        filter_row1 = st.columns(4)
        with filter_row1[0]:
            filter_viable = st.checkbox("Viable only", value=False, key='filter_viable')
        with filter_row1[1]:
            filter_zero_dg = st.checkbox("Zero DG hours", value=False, key='filter_zero_dg')
        with filter_row1[2]:
            filter_100_delivery = st.checkbox("100% Delivery", value=False, key='filter_100_delivery')
        with filter_row1[3]:
            filter_no_unserved = st.checkbox("No unserved", value=False, key='filter_no_unserved')

        # Row 2: Range filters
        filter_row2 = st.columns(4)

        with filter_row2[0]:
            solar_values = sorted(df_all['solar_capacity_mw'].unique())
            solar_range = st.select_slider(
                "Solar (MWp)",
                options=solar_values,
                value=(solar_values[0], solar_values[-1]),
                key='filter_solar_range'
            )

        with filter_row2[1]:
            bess_values = sorted(df_all['bess_capacity_mwh'].unique())
            bess_range = st.select_slider(
                "BESS (MWh)",
                options=bess_values,
                value=(bess_values[0], bess_values[-1]),
                key='filter_bess_range'
            )

        with filter_row2[2]:
            duration_values = sorted(df_all['duration_hr'].unique())
            selected_durations = st.multiselect(
                "Duration (hr)",
                options=duration_values,
                default=duration_values,
                key='filter_duration'
            )

        with filter_row2[3]:
            dg_values = sorted(df_all['dg_capacity_mw'].unique())
            if len(dg_values) > 1:
                selected_dg = st.multiselect(
                    "DG (MW)",
                    options=dg_values,
                    default=dg_values,
                    format_func=lambda x: f"{x:.0f} MW" if x > 0 else "No DG",
                    key='filter_dg'
                )
            else:
                selected_dg = dg_values

        # Row 3: Percentage range filters
        filter_row3 = st.columns(4)

        with filter_row3[0]:
            green_min = st.number_input(
                "Min Green %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=5.0,
                key='filter_green_min'
            )

        with filter_row3[1]:
            wastage_max = st.number_input(
                "Max Wastage %",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=5.0,
                key='filter_wastage_max'
            )

        with filter_row3[2]:
            delivery_min = st.number_input(
                "Min Delivery %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=5.0,
                key='filter_delivery_min'
            )

        with filter_row3[3]:
            sort_by = st.selectbox(
                "Sort by",
                options=['delivery_pct', 'green_energy_pct', 'wastage_pct', 'solar_capacity_mw', 'bess_capacity_mwh', 'dg_runtime_hours'],
                format_func=lambda x: {
                    'delivery_pct': 'Delivery %',
                    'solar_capacity_mw': 'Solar (MWp)',
                    'bess_capacity_mwh': 'BESS (MWh)',
                    'green_energy_pct': 'Green % (Energy)',
                    'wastage_pct': 'Wastage %',
                    'dg_runtime_hours': 'DG Hours'
                }.get(x, x),
                index=0,
                key='sort_by'
            )

        # Apply filters
        filtered_df = df_all.copy()

        # Checkbox filters
        if filter_viable:
            filtered_df = filtered_df[filtered_df['is_viable'] == True]
        if filter_zero_dg:
            filtered_df = filtered_df[filtered_df['dg_runtime_hours'] == 0]
        if filter_100_delivery:
            filtered_df = filtered_df[filtered_df['delivery_pct'] >= 99.9]
        if filter_no_unserved:
            filtered_df = filtered_df[filtered_df['unserved_mwh'] == 0]

        # Range filters
        filtered_df = filtered_df[
            (filtered_df['solar_capacity_mw'] >= solar_range[0]) &
            (filtered_df['solar_capacity_mw'] <= solar_range[1])
        ]
        filtered_df = filtered_df[
            (filtered_df['bess_capacity_mwh'] >= bess_range[0]) &
            (filtered_df['bess_capacity_mwh'] <= bess_range[1])
        ]

        # Multiselect filters
        if selected_durations:
            filtered_df = filtered_df[filtered_df['duration_hr'].isin(selected_durations)]
        if selected_dg:
            filtered_df = filtered_df[filtered_df['dg_capacity_mw'].isin(selected_dg)]

        # Percentage filters
        filtered_df = filtered_df[filtered_df['green_energy_pct'] >= green_min]
        filtered_df = filtered_df[filtered_df['wastage_pct'] <= wastage_max]
        filtered_df = filtered_df[filtered_df['delivery_pct'] >= delivery_min]

        # Sort
        ascending = sort_by in ['solar_capacity_mw', 'bess_capacity_mwh', 'wastage_pct', 'dg_runtime_hours']
        filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)

        # Rename columns for display (matching Step 3 format)
        display_df = filtered_df.rename(columns={
            'solar_capacity_mw': 'Solar (MWp)',
            'bess_capacity_mwh': 'BESS (MWh)',
            'duration_hr': 'Duration (hr)',
            'power_mw': 'Power (MW)',
            'containers': 'Containers',
            'dg_capacity_mw': 'DG (MW)',
            'delivery_pct': 'Delivery %',
            'green_energy_pct': 'Green % (Energy)',
            'green_hours_pct': 'Green % (Hours)',
            'green_hours_pct_mar_oct': 'Green % (Mar-Oct)',
            'wastage_pct': 'Wastage %',
            'delivery_hours': 'Delivery Hrs',
            'load_hours': 'Load Hrs',
            'green_hours': 'Green Hrs',
            'dg_runtime_hours': 'DG Hrs',
            'dg_starts': 'DG Starts',
            'total_cycles': 'BESS Cycles',
            'unserved_mwh': 'Unserved (MWh)',
            'fuel_liters': 'Fuel (L)',
        })

        # Select columns for display (matching Step 3)
        display_columns = [
            'Solar (MWp)',
            'BESS (MWh)',
            'Duration (hr)',
            'Power (MW)',
            'Containers',
            'DG (MW)',
            'Delivery %',
            'Green % (Energy)',
            'Green % (Hours)',
            'Green % (Mar-Oct)',
            'Wastage %',
            'Delivery Hrs',
            'Load Hrs',
            'Green Hrs',
            'DG Hrs',
            'DG Starts',
            'BESS Cycles',
            'Unserved (MWh)',
            'Fuel (L)',
        ]

        # Only show columns that exist
        available_display = [c for c in display_columns if c in display_df.columns]
        display_df = display_df[available_display]

        # Display table with formatting
        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True,
            column_config={
                'Delivery %': st.column_config.ProgressColumn(
                    'Delivery %',
                    min_value=0,
                    max_value=100,
                    format="%.1f%%"
                ),
                'Green % (Energy)': st.column_config.ProgressColumn(
                    'Green % (Energy)',
                    min_value=0,
                    max_value=100,
                    format="%.1f%%"
                ),
                'Green % (Hours)': st.column_config.ProgressColumn(
                    'Green % (Hours)',
                    min_value=0,
                    max_value=100,
                    format="%.1f%%"
                ),
                'Green % (Mar-Oct)': st.column_config.ProgressColumn(
                    'Green % (Mar-Oct)',
                    min_value=0,
                    max_value=100,
                    format="%.1f%%"
                ),
                'Wastage %': st.column_config.NumberColumn(
                    'Wastage %',
                    format="%.1f%%"
                ),
                'BESS Cycles': st.column_config.NumberColumn(
                    'BESS Cycles',
                    format="%.0f"
                ),
            }
        )

        st.caption(f"Showing {len(filtered_df)} of {len(df_all)} configurations")

        # Quick insights
        if len(filtered_df) > 0:
            st.markdown("---")
            st.markdown("**Quick Insights:**")

            # Find best viable configs
            viable_df = df_all[df_all['is_viable'] == True] if 'is_viable' in df_all.columns else pd.DataFrame()

            if len(viable_df) > 0:
                # Smallest total system meeting targets
                min_solar_row = viable_df.loc[viable_df['solar_capacity_mw'].idxmin()]
                st.success(f"Smallest Solar meeting targets: **{min_solar_row['solar_capacity_mw']:.0f} MWp** "
                          f"with {min_solar_row['bess_capacity_mwh']:.0f} MWh BESS "
                          f"({min_solar_row['green_energy_pct']:.1f}% green, {min_solar_row['wastage_pct']:.1f}% wastage)")

                min_bess_row = viable_df.loc[viable_df['bess_capacity_mwh'].idxmin()]
                if min_bess_row['solar_capacity_mw'] != min_solar_row['solar_capacity_mw']:
                    st.info(f"Smallest BESS meeting targets: **{min_bess_row['bess_capacity_mwh']:.0f} MWh** "
                           f"with {min_bess_row['solar_capacity_mw']:.0f} MWp Solar "
                           f"({min_bess_row['green_energy_pct']:.1f}% green, {min_bess_row['wastage_pct']:.1f}% wastage)")
            else:
                max_green_row = df_all.loc[df_all['green_energy_pct'].idxmax()]
                st.warning(f"No configuration meets both targets. Best green energy: "
                          f"**{max_green_row['green_energy_pct']:.1f}%** with "
                          f"{max_green_row['solar_capacity_mw']:.0f} MWp Solar, "
                          f"{max_green_row['bess_capacity_mwh']:.0f} MWh BESS")

        st.divider()

        # ===========================
        # Export
        # ===========================
        st.subheader("Export Results")

        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            csv_all = df_all.to_csv(index=False)
            st.download_button(
                "Download All Results (CSV)",
                data=csv_all,
                file_name="green_energy_all_results.csv",
                mime="text/csv"
            )

        with col_exp2:
            if df_viable is not None and len(df_viable) > 0:
                csv_viable = df_viable.to_csv(index=False)
                st.download_button(
                    "Download Viable Configs (CSV)",
                    data=csv_viable,
                    file_name="green_energy_viable_configs.csv",
                    mime="text/csv"
                )
            else:
                st.button("Download Viable Configs (CSV)", disabled=True)
                st.caption("No viable configurations to export")

        st.divider()

        # ===========================
        # Hourly Dispatch Export
        # ===========================
        st.subheader("Hourly Dispatch Export")
        st.markdown("Select a configuration to generate and download the full 8760-hour dispatch sheet.")

        # Get unique values for each dimension
        solar_options = sorted(df_all['solar_capacity_mw'].unique())
        bess_options = sorted(df_all['bess_capacity_mwh'].unique())
        duration_options = sorted(df_all['duration_hr'].unique())
        dg_options = sorted(df_all['dg_capacity_mw'].unique())

        # Create separate dropdowns
        col_sel1, col_sel2, col_sel3 = st.columns(3)

        with col_sel1:
            selected_solar = st.selectbox(
                "Solar Capacity (MWp)",
                options=solar_options,
                format_func=lambda x: f"{x:.0f} MWp",
                key='hourly_solar_select'
            )

        with col_sel2:
            # Filter BESS options based on what's available for selected solar
            available_bess = df_all[df_all['solar_capacity_mw'] == selected_solar][['bess_capacity_mwh', 'duration_hr']].drop_duplicates()
            bess_config_options = []
            for _, row in available_bess.iterrows():
                label = f"{row['bess_capacity_mwh']:.0f} MWh ({row['duration_hr']:.0f}hr)"
                bess_config_options.append((row['bess_capacity_mwh'], row['duration_hr'], label))

            # Sort by MWh then duration
            bess_config_options = sorted(bess_config_options, key=lambda x: (x[0], x[1]))

            selected_bess_config = st.selectbox(
                "BESS Configuration",
                options=[(opt[0], opt[1]) for opt in bess_config_options],
                format_func=lambda x: f"{x[0]:.0f} MWh ({x[1]:.0f}hr)",
                key='hourly_bess_select'
            )
            selected_bess = selected_bess_config[0]
            selected_duration = selected_bess_config[1]

        with col_sel3:
            # Filter DG options based on selected solar and BESS
            available_dg = df_all[
                (df_all['solar_capacity_mw'] == selected_solar) &
                (df_all['bess_capacity_mwh'] == selected_bess) &
                (df_all['duration_hr'] == selected_duration)
            ]['dg_capacity_mw'].unique()
            available_dg = sorted(available_dg)

            selected_dg = st.selectbox(
                "DG Capacity (MW)",
                options=available_dg,
                format_func=lambda x: f"{x:.0f} MW" if x > 0 else "No DG",
                key='hourly_dg_select'
            )

        # Find the matching row in results
        matching_rows = df_all[
            (df_all['solar_capacity_mw'] == selected_solar) &
            (df_all['bess_capacity_mwh'] == selected_bess) &
            (df_all['duration_hr'] == selected_duration) &
            (df_all['dg_capacity_mw'] == selected_dg)
        ]

        if len(matching_rows) > 0:
            selected_row = matching_rows.iloc[0]

            # Show selected config summary with metrics
            st.info(f"**Selected:** Solar {selected_solar:.0f} MWp, "
                   f"BESS {selected_bess:.0f} MWh ({selected_duration:.0f}hr), "
                   f"DG {selected_dg:.0f} MW\n\n"
                   f"**Metrics:** Delivery {selected_row['delivery_pct']:.1f}%, "
                   f"Green {selected_row['green_energy_pct']:.1f}%, "
                   f"Wastage {selected_row['wastage_pct']:.1f}%")
        else:
            st.warning("No matching configuration found.")
            selected_row = None

        if selected_row is not None and st.button("Generate Hourly Dispatch", type="primary", key='gen_hourly'):
            with st.spinner("Generating 8760-hour dispatch simulation..."):
                # Re-run simulation for selected config to get hourly data
                solar_source = setup.get('solar_source', 'inputs')
                if solar_source in ('inputs', 'file', 'default'):
                    solar_file = setup.get('solar_selected_file', 'Solar Profile.csv')
                    base_solar_profile = load_solar_profile_by_name(solar_file)
                elif solar_source == 'upload' and setup.get('solar_csv_data') is not None:
                    solar_data = setup['solar_csv_data']
                    if isinstance(solar_data, list):
                        base_solar_profile = solar_data[:8760] if len(solar_data) >= 8760 else solar_data
                    else:
                        base_solar_profile = solar_data[:8760].tolist() if len(solar_data) >= 8760 else solar_data.tolist()
                else:
                    base_solar_profile = load_solar_profile_by_name('Solar Profile.csv')

                base_solar_capacity = get_base_solar_peak_capacity(base_solar_profile)

                # Scale solar to selected capacity
                from src.data_loader import scale_solar_profile
                scaled_solar = scale_solar_profile(
                    base_solar_profile,
                    base_solar_capacity,
                    selected_solar
                )

                # Build load profile
                load_profile = get_load_profile(setup)

                # Get BESS power from duration
                power_mw = selected_bess / selected_duration if selected_bess > 0 else 0

                # Build simulation params
                from src.dispatch_engine import SimulationParams, run_simulation

                sim_params = SimulationParams(
                    load_profile=load_profile.tolist() if hasattr(load_profile, 'tolist') else load_profile,
                    solar_profile=scaled_solar,
                    bess_capacity=selected_bess,
                    bess_charge_power=power_mw,
                    bess_discharge_power=power_mw,
                    bess_efficiency=setup.get('bess_efficiency', 87),
                    bess_min_soc=setup.get('bess_min_soc', 5),
                    bess_max_soc=setup.get('bess_max_soc', 95),
                    bess_initial_soc=setup.get('bess_initial_soc', 50),
                    bess_daily_cycle_limit=setup.get('bess_daily_cycle_limit', 2.0),
                    bess_enforce_cycle_limit=setup.get('bess_enforce_cycle_limit', False),
                    dg_enabled=setup.get('dg_enabled', False) and selected_dg > 0,
                    dg_capacity=selected_dg,
                    dg_charges_bess=rules.get('dg_charges_bess', False),
                    dg_load_priority=rules.get('dg_load_priority', 'bess_first'),
                    dg_takeover_mode=rules.get('dg_takeover_mode', False),
                    night_start_hour=rules.get('night_start', 18),
                    night_end_hour=rules.get('night_end', 6),
                    day_start_hour=rules.get('day_start', 6),
                    day_end_hour=rules.get('day_end', 18),
                    blackout_start_hour=rules.get('blackout_start', 0),
                    blackout_end_hour=rules.get('blackout_end', 0),
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
                template_id = parse_template_id(rules.get('inferred_template', 'T0'))
                hourly_results = run_simulation(sim_params, template_id, num_hours=8760)

                # Convert to DataFrame
                hourly_data = []
                for i, hr in enumerate(hourly_results):
                    # Calculate derived values
                    load_served = hr.solar_to_load + hr.bess_to_load + hr.dg_to_load
                    bess_charge = hr.solar_to_bess + hr.dg_to_bess
                    full_delivery = hr.unserved == 0 and hr.load > 0
                    green_delivery = full_delivery and hr.dg_to_load == 0

                    hourly_data.append({
                        'Hour': hr.t,
                        'Day': hr.day,
                        'Hour_of_Day': hr.hour_of_day,
                        'Load_MW': hr.load,
                        'Solar_MW': hr.solar,
                        'Solar_to_Load_MW': hr.solar_to_load,
                        'Solar_to_BESS_MW': hr.solar_to_bess,
                        'Solar_Curtailed_MW': hr.solar_curtailed,
                        'BESS_to_Load_MW': hr.bess_to_load,
                        'BESS_Charge_MW': bess_charge,
                        'BESS_SOC_pct': hr.soc_pct,
                        'DG_to_Load_MW': hr.dg_to_load,
                        'DG_to_BESS_MW': hr.dg_to_bess,
                        'DG_Output_MW': hr.dg_output_mw,
                        'DG_Fuel_L': hr.dg_fuel_consumed,
                        'Load_Served_MW': load_served,
                        'Unserved_MW': hr.unserved,
                        'Full_Delivery': 'Yes' if full_delivery else 'No',
                        'Green_Delivery': 'Yes' if green_delivery else 'No',
                        'DG_Running': 'Yes' if hr.dg_running else 'No',
                        'Daily_Cycles': hr.daily_cycles,
                    })

                hourly_df = pd.DataFrame(hourly_data)

                # Store in session state for download
                st.session_state['hourly_dispatch_df'] = hourly_df
                st.session_state['hourly_dispatch_config'] = {
                    'solar_mwp': selected_solar,
                    'bess_mwh': selected_bess,
                    'duration_hr': selected_duration,
                    'dg_mw': selected_dg,
                }

            st.success("Hourly dispatch generated!")

        # Show download button if hourly data exists
        if 'hourly_dispatch_df' in st.session_state:
            hourly_df = st.session_state['hourly_dispatch_df']
            config = st.session_state.get('hourly_dispatch_config', {})

            # Preview
            with st.expander("Preview Hourly Data (first 48 hours)", expanded=False):
                st.dataframe(hourly_df.head(48), width='stretch', hide_index=True)

            # Download button
            csv_hourly = hourly_df.to_csv(index=False)
            filename = (f"hourly_dispatch_Solar{config.get('solar_mwp', 0):.0f}MWp_"
                       f"BESS{config.get('bess_mwh', 0):.0f}MWh_"
                       f"DG{config.get('dg_mw', 0):.0f}MW.csv")

            st.download_button(
                "Download Hourly Dispatch (8760 hours CSV)",
                data=csv_hourly,
                file_name=filename,
                mime="text/csv",
                type="primary"
            )

            # ===========================
            # Monthly Performance Summary
            # ===========================
            st.divider()
            st.subheader("Monthly Performance Summary")

            # Calculate monthly metrics from hourly_df
            monthly_data = []
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            # Calculate month using accurate day-based calculation
            days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            cumulative_hours = []
            cumsum = 0
            for days in days_in_months:
                cumsum += days * 24
                cumulative_hours.append(cumsum)

            def get_month(hour):
                for i, cum_hrs in enumerate(cumulative_hours):
                    if hour <= cum_hrs:
                        return i + 1
                return 12

            hourly_df['Month'] = hourly_df['Hour'].apply(get_month)

            for month_num in range(1, 13):
                # Filter data for this month
                month_df = hourly_df[hourly_df['Month'] == month_num]

                if len(month_df) == 0:
                    continue

                # Calculate metrics for this month
                month_hours = len(month_df)
                month_load_hours = (month_df['Load_MW'] > 0).sum()
                month_delivery = (month_df['Full_Delivery'] == 'Yes').sum()
                month_green = (month_df['Green_Delivery'] == 'Yes').sum()
                month_dg_hours = (month_df['DG_Running'] == 'Yes').sum()
                month_solar = month_df['Solar_MW'].sum()
                month_curtailed = month_df['Solar_Curtailed_MW'].sum()
                month_unserved = month_df['Unserved_MW'].sum()
                month_fuel = month_df['DG_Fuel_L'].sum()

                # Solar delivery hours: hours where solar contributed to load during full delivery
                month_solar_delivery_hrs = ((month_df['Full_Delivery'] == 'Yes') & (month_df['Solar_to_Load_MW'] > 0)).sum()
                # BESS delivery hours: hours where BESS contributed to load during full delivery
                month_bess_delivery_hrs = ((month_df['Full_Delivery'] == 'Yes') & (month_df['BESS_to_Load_MW'] > 0)).sum()

                effective_hours = month_load_hours if month_load_hours > 0 else month_hours
                delivery_pct = (month_delivery / effective_hours * 100) if effective_hours > 0 else 0
                green_pct = (month_green / month_delivery * 100) if month_delivery > 0 else 0
                wastage_pct = (month_curtailed / month_solar * 100) if month_solar > 0 else 0

                monthly_data.append({
                    'Month': month_names[month_num - 1],
                    'Delivery %': round(delivery_pct, 1),
                    'Green %': round(max(0, green_pct), 1),
                    'Wastage %': round(wastage_pct, 1),
                    'Delivery Hrs': int(month_delivery),
                    'Load Hrs': int(month_load_hours),
                    'Green Hrs': int(month_green),
                    'Solar Hrs': int(month_solar_delivery_hrs),
                    'BESS Hrs': int(month_bess_delivery_hrs),
                    'DG Hrs': int(month_dg_hours),
                    'Curtailed (MWh)': round(month_curtailed, 1),
                    'Unserved (MWh)': round(month_unserved, 1),
                    'Fuel (L)': round(month_fuel, 1),
                })

            monthly_summary_df = pd.DataFrame(monthly_data)

            st.dataframe(
                monthly_summary_df,
                width='stretch',
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

            # Download monthly summary
            csv_monthly = monthly_summary_df.to_csv(index=False)
            monthly_filename = (f"monthly_summary_Solar{config.get('solar_mwp', 0):.0f}MWp_"
                               f"BESS{config.get('bess_mwh', 0):.0f}MWh_"
                               f"DG{config.get('dg_mw', 0):.0f}MW.csv")

            st.download_button(
                "Download Monthly Summary (CSV)",
                data=csv_monthly,
                file_name=monthly_filename,
                mime="text/csv"
            )

        # ===========================
        # 20-Year Green Energy Projection
        # ===========================
        st.divider()
        st.subheader("20-Year Green Energy Projection")
        st.markdown(
            "Project the **configuration selected above** over 20 years with compound "
            "BESS degradation. Solar is held flat; only BESS usable capacity degrades, "
            "so green energy declines as the battery ages. Year 1 uses the selected "
            "capacity as beginning-of-life (BOL)."
        )

        if selected_row is None:
            st.info("Select a configuration above to enable the 20-year projection.")
        else:
            my_col1, my_col2 = st.columns([1, 2])
            with my_col1:
                my_deg_pct = st.select_slider(
                    "Annual BESS Degradation",
                    options=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
                    value=2.0,
                    format_func=lambda x: f"{x}%/year",
                    key='green_my_degradation',
                )
            with my_col2:
                st.caption(
                    f"Projecting Solar {selected_solar:.0f} MWp, "
                    f"BESS {selected_bess:.0f} MWh ({selected_duration:.0f}hr), "
                    f"DG {selected_dg:.0f} MW over 20 years."
                )

            if st.button("Run 20-Year Projection", type="primary", key='run_green_multiyear'):
                with st.spinner("Simulating 20 years..."):
                    my_df, my_monthly_df, my_summary = compute_green_multiyear(
                        selected_solar, selected_bess, selected_duration, selected_dg,
                        setup, rules, my_deg_pct / 100,
                    )
                if my_df is None:
                    st.error("Could not load or scale the solar profile for the projection. "
                             "Check the Step 1 solar configuration.")
                else:
                    st.session_state['green_multiyear_df'] = my_df
                    st.session_state['green_multiyear_monthly_df'] = my_monthly_df
                    st.session_state['green_multiyear_summary'] = my_summary
                    st.session_state['green_multiyear_config'] = {
                        'solar_mwp': selected_solar,
                        'bess_mwh': selected_bess,
                        'duration_hr': selected_duration,
                        'dg_mw': selected_dg,
                        'degradation_pct': my_deg_pct,
                    }

            if 'green_multiyear_df' in st.session_state:
                my_df = st.session_state['green_multiyear_df']
                my_cfg = st.session_state.get('green_multiyear_config', {})

                # Green % trajectory chart
                fig_my = go.Figure()
                fig_my.add_trace(go.Scatter(
                    x=my_df['Year'], y=my_df['Green % (Energy)'],
                    mode='lines+markers', name='Green % (Energy)',
                    line=dict(color='#2E8B57', width=3),
                ))
                fig_my.add_trace(go.Scatter(
                    x=my_df['Year'], y=my_df['Delivery %'],
                    mode='lines+markers', name='Delivery %',
                    line=dict(color='#4169E1', width=2, dash='dot'),
                ))
                fig_my.update_layout(
                    title="Green % and Delivery % over 20 Years",
                    xaxis_title="Year", yaxis_title="%",
                    yaxis=dict(range=[0, 100]), height=400,
                    legend=dict(orientation='h', yanchor='bottom', y=1.02,
                                xanchor='right', x=1),
                )
                st.plotly_chart(fig_my, width='stretch')

                # Year 1 vs Year 20 insight
                y1 = my_df.iloc[0]
                y20 = my_df.iloc[-1]
                st.info(
                    f"**Green % (Energy):** Year 1 {y1['Green % (Energy)']:.1f}% → "
                    f"Year 20 {y20['Green % (Energy)']:.1f}% "
                    f"({y20['Green % (Energy)'] - y1['Green % (Energy)']:+.1f} pp) as BESS "
                    f"degrades to {y20['Capacity %']:.0f}% of BOL."
                )

                st.dataframe(
                    my_df,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        'Green % (Energy)': st.column_config.ProgressColumn(
                            'Green % (Energy)', min_value=0, max_value=100, format="%.1f%%"),
                        'Delivery %': st.column_config.ProgressColumn(
                            'Delivery %', min_value=0, max_value=100, format="%.1f%%"),
                        'Wastage %': st.column_config.NumberColumn('Wastage %', format="%.1f%%"),
                        'Capacity %': st.column_config.NumberColumn('Cap %', format="%.1f%%"),
                    },
                )

                my_csv = my_df.to_csv(index=False)
                my_fname = (f"green_multiyear_Solar{my_cfg.get('solar_mwp', 0):.0f}MWp_"
                            f"BESS{my_cfg.get('bess_mwh', 0):.0f}MWh_"
                            f"DG{my_cfg.get('dg_mw', 0):.0f}MW.csv")
                st.download_button(
                    "Download 20-Year Projection (CSV)",
                    data=my_csv,
                    file_name=my_fname,
                    mime="text/csv",
                    key='download_green_multiyear',
                )

                if 'green_multiyear_monthly_df' in st.session_state:
                    my_monthly_df = st.session_state['green_multiyear_monthly_df']
                    my_monthly_csv = my_monthly_df.to_csv(index=False)
                    my_monthly_fname = (
                        f"green_20year_monthly_Solar{my_cfg.get('solar_mwp', 0):.0f}MWp_"
                        f"BESS{my_cfg.get('bess_mwh', 0):.0f}MWh_"
                        f"DG{my_cfg.get('dg_mw', 0):.0f}MW.csv"
                    )
                    st.download_button(
                        "Download 20-Year Monthly Detail (CSV)",
                        data=my_monthly_csv,
                        file_name=my_monthly_fname,
                        mime="text/csv",
                        key='download_green_multiyear_monthly',
                    )
                    st.caption(
                        f"Monthly sheet: {len(my_monthly_df)} rows (20 years x 12 months), "
                        "same columns as the Step 5 monthly export."
                    )

                # ---- 20-Year Energy Summary (energy-balance correction check) ----
                if 'green_multiyear_summary' in st.session_state:
                    s = st.session_state['green_multiyear_summary']
                    st.divider()
                    st.subheader("20-Year Energy Summary")

                    sc = st.columns(6)
                    sc[0].metric("Total Solar", f"{s['total_solar_gen']:,.0f} MWh")
                    sc[1].metric("Total DG", f"{s['total_dg_gen']:,.0f} MWh")
                    sc[2].metric(
                        "Total Curtailed", f"{s['total_curtailed']:,.0f} MWh",
                        f"{s['total_curtailed'] / s['total_solar_gen'] * 100:.1f}%"
                        if s['total_solar_gen'] > 0 else "N/A")
                    sc[3].metric("Load Wastage", f"{s['total_load_curtailed']:,.0f} MWh",
                                 f"{s['load_wastage_pct']:.1f}%")
                    sc[4].metric("Delivery Met", f"{s['total_delivery_met']:,.0f} MWh")
                    sc[5].metric("BESS Losses", f"{s['total_bess_losses']:,.0f} MWh")

                    n_yr = s['num_years']
                    summary_table_df = pd.DataFrame({
                        'Category': [
                            'ENERGY IN', '', '', '', '',
                            'ENERGY OUT', '', '', '', '', '',
                            'BALANCE',
                        ],
                        'Item': [
                            'Solar Generated', 'DG Generated', 'Initial BESS Energy',
                            'Total Energy In', '',
                            'Energy to Load', 'Solar Curtailed', 'DG Curtailed',
                            'BESS Losses', 'Final BESS Energy', 'Total Energy Out',
                            'Difference (In - Out)',
                        ],
                        'Value (MWh)': [
                            f"{s['total_solar_gen']:,.0f}",
                            f"{s['total_dg_gen']:,.0f}",
                            f"{s['initial_bess_energy']:,.0f}",
                            f"{s['total_energy_in']:,.0f}",
                            '',
                            f"{s['total_energy_to_load']:,.0f}",
                            f"{s['total_solar_curtailed']:,.0f}",
                            f"{s['total_dg_curtailed']:,.0f}",
                            f"{s['total_bess_losses']:,.0f}",
                            f"{s['final_bess_energy']:,.0f}",
                            f"{s['total_energy_out']:,.0f}",
                            f"{s['balance_difference']:,.0f}",
                        ],
                        'Details': [
                            f"{s['total_solar_gen'] / n_yr:,.0f} MWh/year avg",
                            f"{s['total_dg_gen'] / n_yr:,.0f} MWh/year avg"
                            if s['total_dg_gen'] > 0 else "DG disabled",
                            f"{s['bol_capacity']:.0f} MWh x {s['initial_soc_pct'] * 100:.0f}% SOC",
                            '',
                            '',
                            f"Solar: {s['total_solar_to_load']:,.0f} + "
                            f"BESS: {s['total_bess_to_load']:,.0f} + "
                            f"DG: {s['total_dg_to_load']:,.0f}",
                            f"{s['total_solar_curtailed'] / s['total_solar_gen'] * 100:.1f}% of solar"
                            if s['total_solar_gen'] > 0 else "N/A",
                            f"{s['total_dg_curtailed'] / s['total_dg_gen'] * 100:.1f}% of DG"
                            if s['total_dg_gen'] > 0 else "N/A",
                            f"Charge: {s['total_charging_loss']:,.0f} + "
                            f"Discharge: {s['total_discharging_loss']:,.0f}",
                            f"{s['final_capacity']:.0f} MWh x {s['final_soc_pct'] * 100:.0f}% "
                            f"SOC (Year {n_yr} end)",
                            '',
                            'Should be ~0 if balanced',
                        ],
                    })
                    st.dataframe(summary_table_df, width='stretch', hide_index=True)

                    if abs(s['balance_difference']) < 100:
                        st.success(f"Energy balance verified: {s['balance_difference']:,.0f} MWh "
                                   "difference (within tolerance)")
                    else:
                        st.warning(f"Energy balance issue: {s['balance_difference']:,.0f} MWh "
                                   "difference detected")


if __name__ == "__main__":
    main()
