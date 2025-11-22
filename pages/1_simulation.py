"""
BESS Simulation Page
Run battery sizing simulations and view results
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_solar_profile, get_solar_statistics
from src.battery_simulator import simulate_bess_year
from utils.metrics import (
    calculate_metrics_summary, find_optimal_battery_size,
    create_hourly_dataframe, format_results_for_export
)
from utils.config_manager import get_config


# Page config
st.set_page_config(page_title="Simulation", page_icon="⚡", layout="wide")

st.title("⚡ BESS Simulation")

# Show configuration status
if 'config' in st.session_state:
    st.info("📌 Using custom configuration from Configuration page")
else:
    st.info("📌 Using default configuration")

st.markdown("---")

# Load solar profile
@st.cache_data
def get_solar_data():
    """Load and cache solar profile data."""
    profile = load_solar_profile()
    stats = get_solar_statistics(profile)
    return profile, stats

solar_profile, solar_stats = get_solar_data()

# Sidebar - Solar Profile Statistics
st.sidebar.markdown("### 📊 Solar Profile Statistics")
st.sidebar.info(f"""
**Max Generation:** {solar_stats['max_mw']:.1f} MW
**Avg Generation:** {solar_stats['mean_mw']:.1f} MW
**Capacity Factor:** {solar_stats['capacity_factor']:.1%}
**Total Energy:** {solar_stats['total_mwh']/1000:.1f} GWh
**Zero Hours:** {int(solar_stats['zero_hours'])}
""")

# Get configuration
config = get_config()

# Sidebar - BESS Profile Statistics
st.sidebar.markdown("### 🔋 BESS Profile Statistics")
usable_capacity = (config['MAX_SOC'] - config['MIN_SOC']) * 100
one_way_eff = config['ONE_WAY_EFFICIENCY'] * 100
st.sidebar.info(f"""
**Target Delivery:** {config['TARGET_DELIVERY_MW']:.0f} MW
**SOC Limits:** {config['MIN_SOC']*100:.0f}% - {config['MAX_SOC']*100:.0f}%
**Usable Capacity:** {usable_capacity:.0f}% of rated
**Round-trip Efficiency:** {config['ROUND_TRIP_EFFICIENCY']*100:.0f}%
**One-way Efficiency:** {one_way_eff:.1f}%
**C-rates:** {config['C_RATE_CHARGE']:.1f} (charge) / {config['C_RATE_DISCHARGE']:.1f} (discharge)
**Max Cycles/Day:** {config['MAX_DAILY_CYCLES']:.1f}
**Degradation:** {config['DEGRADATION_PER_CYCLE']*100:.3f}% per cycle
""")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔋 Battery Configuration")

    # Single battery simulation
    battery_size = st.slider(
        "Battery Size (MWh)",
        min_value=config['MIN_BATTERY_SIZE_MWH'],
        max_value=config['MAX_BATTERY_SIZE_MWH'],
        value=100,
        step=config['BATTERY_SIZE_STEP_MWH'],
        help="Select battery capacity for simulation"
    )

    if st.button("🚀 Run Simulation", type="primary"):
        with st.spinner(f"Simulating {battery_size} MWh battery..."):
            # Run simulation with config
            results = simulate_bess_year(battery_size, solar_profile, config)
            metrics = calculate_metrics_summary(battery_size, results)

            # Store in session state
            st.session_state['single_result'] = metrics
            st.session_state['hourly_data'] = results['hourly_data']

    st.markdown("---")

    # Batch simulation
    st.markdown("### 📈 Optimization Analysis")

    if st.button("🔍 Find Optimal Size"):
        with st.spinner("Running optimization analysis..."):
            all_results = []
            progress_bar = st.progress(0)

            # Test all battery sizes
            battery_sizes = range(
                config['MIN_BATTERY_SIZE_MWH'],
                config['MAX_BATTERY_SIZE_MWH'] + config['BATTERY_SIZE_STEP_MWH'],
                config['BATTERY_SIZE_STEP_MWH']
            )

            for i, size in enumerate(battery_sizes):
                results = simulate_bess_year(size, solar_profile, config)
                metrics = calculate_metrics_summary(size, results)
                all_results.append(metrics)
                progress_bar.progress((i + 1) / len(battery_sizes))

            # Find optimal size
            optimal = find_optimal_battery_size(all_results)

            # Store in session state
            st.session_state['all_results'] = all_results
            st.session_state['optimal'] = optimal

            st.success(f"✅ Optimal battery size: **{optimal['optimal_size_mwh']} MWh**")

with col2:
    st.markdown("### 📊 Results")

    # Display single simulation result
    if 'single_result' in st.session_state:
        st.markdown("#### Current Simulation")
        metrics = st.session_state['single_result']

        # Display key metrics in columns
        metric_cols = st.columns(4)
        metric_cols[0].metric("Delivery Hours", f"{metrics['Delivery Hours']:,}")
        metric_cols[1].metric("Delivery Rate", f"{metrics['Delivery Rate (%)']:.1f}%")
        metric_cols[2].metric("Total Cycles", f"{metrics['Total Cycles']:.1f}")
        metric_cols[3].metric("Degradation", f"{metrics['Degradation (%)']:.3f}%")

        # Detailed metrics table
        st.markdown("##### Detailed Metrics")
        metrics_df = pd.DataFrame([metrics])
        st.dataframe(metrics_df, use_container_width=True)

        # Download hourly data
        if 'hourly_data' in st.session_state:
            hourly_df = create_hourly_dataframe(st.session_state['hourly_data'])
            csv = hourly_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Hourly Data",
                data=csv,
                file_name=f"bess_{metrics['Battery Size (MWh)']}mwh_hourly.csv",
                mime="text/csv"
            )

    # Display optimization results
    if 'all_results' in st.session_state:
        st.markdown("---")
        st.markdown("#### Optimization Results")

        optimal = st.session_state['optimal']
        st.info(f"""
        **Optimal Size:** {optimal['optimal_size_mwh']} MWh
        **Delivery Hours:** {optimal['delivery_hours']:,}
        **Total Cycles:** {optimal['total_cycles']:.1f}
        **Reasoning:** {optimal['reasoning']}
        """)

        # Show all results table
        st.markdown("##### All Battery Sizes")
        all_df = format_results_for_export(st.session_state['all_results'])
        st.dataframe(
            all_df,
            use_container_width=True,
            height=400
        )

        # Download all results
        csv_all = all_df.to_csv(index=False)
        st.download_button(
            label="📥 Download All Results",
            data=csv_all,
            file_name="bess_optimization_results.csv",
            mime="text/csv"
        )

        # Marginal improvements
        if optimal['marginal_improvements']:
            st.markdown("##### Marginal Improvements")
            marginal_df = pd.DataFrame(optimal['marginal_improvements'])
            st.line_chart(
                data=marginal_df.set_index('size_mwh')['marginal_hours_per_10mwh'],
                use_container_width=True
            )