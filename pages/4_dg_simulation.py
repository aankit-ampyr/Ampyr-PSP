"""
Solar + BESS + DG Simulation Page
Run simulations with diesel generator backup
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from src.data_loader import load_solar_profile, get_solar_statistics
from src.dg_simulator import simulate_solar_bess_dg_year, find_optimal_dg_size
from utils.metrics import calculate_dg_metrics_summary, create_dg_hourly_dataframe
from utils.config_manager import get_config, update_config


# Page config
st.set_page_config(page_title="Solar+BESS+DG", page_icon="⚡", layout="wide")

st.title("⚡ Solar + BESS + DG Simulation")

st.markdown("""
This simulation models a hybrid system with:
- **Solar** as the primary power source
- **DG** (Diesel Generator) as backup when battery SOC drops below threshold
- **BESS** (Battery Energy Storage) discharges only if Solar + DG can't meet load

**Merit Order for Load:** Solar → DG → BESS

**BESS Charging Priority:** Excess Solar → Excess DG
""")

st.markdown("---")

# Load solar profile
@st.cache_data
def get_solar_data():
    """Load and cache solar profile data."""
    profile = load_solar_profile()
    stats = get_solar_statistics(profile)
    return profile, stats

solar_profile, solar_stats = get_solar_data()

# Get configuration
config = get_config()

# Sidebar - Solar Profile Statistics
st.sidebar.markdown("### Solar Profile")
st.sidebar.info(f"""
**Max Generation:** {solar_stats['max_mw']:.1f} MW
**Avg Generation:** {solar_stats['mean_mw']:.1f} MW
**Capacity Factor:** {solar_stats['capacity_factor']:.1%}
**Total Energy:** {solar_stats['total_mwh']/1000:.1f} GWh
""")

# Sidebar - BESS Profile Statistics
st.sidebar.markdown("### BESS Parameters")
usable_capacity = (config['MAX_SOC'] - config['MIN_SOC']) * 100
st.sidebar.info(f"""
**SOC Limits:** {config['MIN_SOC']*100:.0f}% - {config['MAX_SOC']*100:.0f}%
**Usable Capacity:** {usable_capacity:.0f}% of rated
**Round-trip Efficiency:** {config['ROUND_TRIP_EFFICIENCY']*100:.0f}%
**Max Cycles/Day:** {config['MAX_DAILY_CYCLES']:.1f}
""")

# Sidebar - DG Profile Statistics
st.sidebar.markdown("### DG Parameters")
dg_soc_on_default = config.get('DG_SOC_ON_THRESHOLD', 0.20)
dg_soc_off_default = config.get('DG_SOC_OFF_THRESHOLD', 0.80)
st.sidebar.info(f"""
**SOC ON Threshold:** {dg_soc_on_default*100:.0f}%
**SOC OFF Threshold:** {dg_soc_off_default*100:.0f}%
**Operation:** Full capacity when ON
""")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### System Configuration")

    # Load configuration
    load_mw = st.number_input(
        "Load (MW)",
        min_value=1.0,
        max_value=100.0,
        value=float(config.get('DG_LOAD_MW', 25.0)),
        step=1.0,
        help="Fixed load demand in MW"
    )

    # Battery configuration
    battery_size = st.slider(
        "Battery Size (MWh)",
        min_value=config.get('MIN_BATTERY_SIZE_MWH', 10),
        max_value=config.get('MAX_BATTERY_SIZE_MWH', 500),
        value=100,
        step=config.get('BATTERY_SIZE_STEP_MWH', 5),
        help="Battery capacity in MWh"
    )

    # DG configuration
    dg_capacity = st.number_input(
        "DG Capacity (MW)",
        min_value=1.0,
        max_value=100.0,
        value=float(config.get('DG_CAPACITY_MW', 25.0)),
        step=1.0,
        help="Diesel generator rated capacity in MW"
    )

    st.markdown("#### DG Control Thresholds")

    dg_soc_on = st.slider(
        "DG ON Threshold (SOC %)",
        min_value=5,
        max_value=50,
        value=int(dg_soc_on_default * 100),
        step=5,
        help="Start DG when battery SOC drops to this level"
    )

    dg_soc_off = st.slider(
        "DG OFF Threshold (SOC %)",
        min_value=50,
        max_value=95,
        value=int(dg_soc_off_default * 100),
        step=5,
        help="Stop DG when battery SOC rises to this level"
    )

    # Validate thresholds
    if dg_soc_on >= dg_soc_off:
        st.warning("ON threshold must be less than OFF threshold for proper hysteresis control.")

    st.markdown("---")

    if st.button("🚀 Run Simulation", type="primary"):
        if dg_soc_on >= dg_soc_off:
            st.error("Please fix threshold values before running simulation.")
        else:
            # Update config with user inputs
            sim_config = config.copy()
            sim_config['DG_LOAD_MW'] = load_mw
            sim_config['DG_SOC_ON_THRESHOLD'] = dg_soc_on / 100
            sim_config['DG_SOC_OFF_THRESHOLD'] = dg_soc_off / 100

            with st.spinner(f"Simulating Solar + {battery_size} MWh BESS + {dg_capacity} MW DG..."):
                # Run simulation
                results = simulate_solar_bess_dg_year(
                    battery_size,
                    dg_capacity,
                    solar_profile,
                    sim_config
                )
                metrics = calculate_dg_metrics_summary(battery_size, dg_capacity, results)

                # Store in session state
                st.session_state['dg_result'] = metrics
                st.session_state['dg_hourly_data'] = results['hourly_data']
                st.session_state['dg_config'] = {
                    'battery_mwh': battery_size,
                    'dg_mw': dg_capacity,
                    'load_mw': load_mw,
                    'soc_on': dg_soc_on,
                    'soc_off': dg_soc_off
                }

            st.success("Simulation complete!")

with col2:
    st.markdown("### Results")

    if 'dg_result' in st.session_state:
        metrics = st.session_state['dg_result']
        dg_config = st.session_state['dg_config']

        # Display configuration summary
        st.markdown(f"""
        **Configuration:** {dg_config['battery_mwh']} MWh BESS + {dg_config['dg_mw']} MW DG |
        Load: {dg_config['load_mw']} MW |
        DG ON: {dg_config['soc_on']}% | DG OFF: {dg_config['soc_off']}%
        """)

        # Key metrics in columns
        st.markdown("#### Delivery Metrics")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Delivery Hours", f"{metrics['Delivery Hours']:,}")
        metric_cols[1].metric("Delivery Rate", f"{metrics['Delivery Rate (%)']:.1f}%")
        metric_cols[2].metric("Energy Delivered", f"{metrics['Energy Delivered (GWh)']:.2f} GWh")
        metric_cols[3].metric("Solar Wastage", f"{metrics['Solar Wastage (%)']:.1f}%")

        # DG metrics
        st.markdown("#### DG Metrics")
        dg_cols = st.columns(4)
        dg_cols[0].metric("DG Runtime", f"{metrics['DG Runtime (hours)']:,} hrs")
        dg_cols[1].metric("DG Starts", f"{metrics['DG Starts']:,}")
        dg_cols[2].metric("DG Energy", f"{metrics['DG Energy (MWh)']:,.0f} MWh")
        dg_cols[3].metric("DG Capacity Factor", f"{metrics['DG Capacity Factor (%)']:.1f}%")

        # BESS metrics
        st.markdown("#### BESS Metrics")
        bess_cols = st.columns(4)
        bess_cols[0].metric("Total Cycles", f"{metrics['Total Cycles']:.1f}")
        bess_cols[1].metric("Avg Daily Cycles", f"{metrics['Avg Daily Cycles']:.2f}")
        bess_cols[2].metric("Battery Discharged", f"{metrics['Battery Discharged (MWh)']:,.0f} MWh")
        bess_cols[3].metric("Degradation", f"{metrics['Degradation (%)']:.3f}%")

        # Energy flow summary
        st.markdown("#### Energy Flow Summary")
        flow_cols = st.columns(3)
        flow_cols[0].metric("Solar to Load", f"{metrics['Solar to Load (MWh)']:,.0f} MWh")
        flow_cols[1].metric("DG to Load", f"{metrics['DG to Load (MWh)']:,.0f} MWh")
        flow_cols[2].metric("DG to BESS", f"{metrics['DG to BESS (MWh)']:,.0f} MWh")

        # Detailed metrics table
        st.markdown("#### All Metrics")
        with st.expander("View detailed metrics"):
            metrics_df = pd.DataFrame([metrics])
            st.dataframe(metrics_df.T.rename(columns={0: 'Value'}), use_container_width=True)

        # Download hourly data
        st.markdown("---")
        if 'dg_hourly_data' in st.session_state:
            hourly_df = create_dg_hourly_dataframe(st.session_state['dg_hourly_data'])

            # Show sample of hourly data
            with st.expander("Preview hourly data (first 48 hours)"):
                st.dataframe(hourly_df.head(48), use_container_width=True)

            csv = hourly_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Hourly Data",
                data=csv,
                file_name=f"solar_bess_dg_{dg_config['battery_mwh']}mwh_{dg_config['dg_mw']}mw_hourly.csv",
                mime="text/csv"
            )

    else:
        st.info("Configure the system parameters and click 'Run Simulation' to see results.")

        # Show merit order diagram
        st.markdown("""
        #### How it works

        **Load Serving (Merit Order):**
        1. Solar generation serves load first
        2. DG output serves remaining load (when DG is ON)
        3. BESS discharges only if Solar + DG can't meet load

        **BESS Charging:**
        1. Excess solar charges the battery first
        2. Excess DG output charges the battery when DG is running

        **DG Control (Hysteresis):**
        - DG starts when battery SOC ≤ ON threshold
        - DG stops when battery SOC ≥ OFF threshold
        - DG runs at full capacity when ON
        """)

# DG Sizing Optimization Section
st.markdown("---")
st.markdown("### DG Sizing Optimization")
st.markdown("Find the minimum DG size required for 100% delivery (8760 hours) with a fixed BESS size.")

opt_col1, opt_col2 = st.columns(2)

with opt_col1:
    opt_battery_size = st.slider(
        "BESS Size for Optimization (MWh)",
        min_value=config.get('MIN_BATTERY_SIZE_MWH', 10),
        max_value=config.get('MAX_BATTERY_SIZE_MWH', 500),
        value=100,
        step=config.get('BATTERY_SIZE_STEP_MWH', 5),
        key="opt_battery_size",
        help="Fixed BESS capacity for DG optimization"
    )

    opt_load_mw = st.number_input(
        "Load for Optimization (MW)",
        min_value=1.0,
        max_value=100.0,
        value=float(config.get('DG_LOAD_MW', 25.0)),
        step=1.0,
        key="opt_load_mw",
        help="Load demand for optimization"
    )

with opt_col2:
    dg_range = st.slider(
        "DG Search Range (% of Load)",
        min_value=10,
        max_value=300,
        value=(50, 200),
        step=10,
        help="Range of DG sizes to test as percentage of load"
    )

    opt_step = st.selectbox(
        "Step Size (% of Load)",
        options=[5, 10, 20, 25],
        index=1,
        help="Increment between tested DG sizes"
    )

# SOC thresholds for optimization
opt_soc_col1, opt_soc_col2 = st.columns(2)
with opt_soc_col1:
    opt_soc_on = st.slider(
        "DG ON Threshold for Optimization (SOC %)",
        min_value=5, max_value=50,
        value=int(dg_soc_on_default * 100),
        step=5,
        key="opt_soc_on"
    )
with opt_soc_col2:
    opt_soc_off = st.slider(
        "DG OFF Threshold for Optimization (SOC %)",
        min_value=50, max_value=95,
        value=int(dg_soc_off_default * 100),
        step=5,
        key="opt_soc_off"
    )

if st.button("Find Optimal DG Size", type="primary"):
    if opt_soc_on >= opt_soc_off:
        st.error("ON threshold must be less than OFF threshold.")
    else:
        # Build config for optimization
        opt_config = config.copy()
        opt_config['DG_LOAD_MW'] = opt_load_mw
        opt_config['DG_SOC_ON_THRESHOLD'] = opt_soc_on / 100
        opt_config['DG_SOC_OFF_THRESHOLD'] = opt_soc_off / 100

        num_tests = (dg_range[1] - dg_range[0]) // opt_step + 1
        with st.spinner(f"Testing {num_tests} DG sizes..."):
            opt_result = find_optimal_dg_size(
                opt_battery_size,
                solar_profile,
                opt_config,
                min_dg_percent=dg_range[0],
                max_dg_percent=dg_range[1],
                step_percent=opt_step
            )
            st.session_state['dg_optimization'] = opt_result
            st.session_state['dg_opt_config'] = {
                'battery_mwh': opt_battery_size,
                'load_mw': opt_load_mw,
                'soc_on': opt_soc_on,
                'soc_off': opt_soc_off
            }

# Display optimization results
if 'dg_optimization' in st.session_state:
    opt = st.session_state['dg_optimization']
    opt_cfg = st.session_state['dg_opt_config']

    st.markdown(f"**Configuration:** {opt_cfg['battery_mwh']} MWh BESS | Load: {opt_cfg['load_mw']} MW | DG ON: {opt_cfg['soc_on']}% | DG OFF: {opt_cfg['soc_off']}%")

    # Highlight optimal result
    if opt['is_100_percent']:
        st.success(f"✅ {opt['reasoning']}")
    else:
        st.warning(f"⚠️ {opt['reasoning']}")

    # Display key metrics
    opt_metrics = st.columns(3)
    opt_metrics[0].metric("Optimal DG Size", f"{opt['optimal_dg_mw']} MW")
    opt_metrics[1].metric("Delivery Hours", f"{opt['optimal_delivery_hours']:,}")
    opt_metrics[2].metric("100% Delivery", "Yes" if opt['is_100_percent'] else "No")

    # Results table
    st.markdown("#### All Tested DG Sizes")
    results_df = pd.DataFrame(opt['all_results'])

    # Highlight the optimal row
    def highlight_optimal(row):
        if row['DG (MW)'] == opt['optimal_dg_mw']:
            return ['background-color: #90EE90'] * len(row)
        return [''] * len(row)

    styled_df = results_df.style.apply(highlight_optimal, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    # Chart: DG Size vs Delivery Hours
    st.markdown("#### DG Size vs Delivery Hours")
    chart_df = results_df.set_index('DG (MW)')['Delivery Hours']
    st.line_chart(chart_df)

    # Download results
    csv_opt = results_df.to_csv(index=False)
    st.download_button(
        label="Download Optimization Results",
        data=csv_opt,
        file_name=f"dg_optimization_{opt_cfg['battery_mwh']}mwh_bess.csv",
        mime="text/csv"
    )
