"""
BESS Configuration Page
Modify all system parameters and constraints
"""

import streamlit as st

# Import default configurations
from src.config import (
    TARGET_DELIVERY_MW, SOLAR_CAPACITY_MW,
    MIN_SOC, MAX_SOC, ROUND_TRIP_EFFICIENCY,
    C_RATE_CHARGE, C_RATE_DISCHARGE,
    MIN_BATTERY_SIZE_MWH, MAX_BATTERY_SIZE_MWH, BATTERY_SIZE_STEP_MWH,
    MARGINAL_IMPROVEMENT_THRESHOLD, MARGINAL_INCREMENT_MWH,
    DEGRADATION_PER_CYCLE, INITIAL_SOC
)

# Page config
st.set_page_config(page_title="Configurations", page_icon="⚙️", layout="wide")

st.title("⚙️ BESS Configurations")
st.markdown("Configure all system parameters and constraints")
st.markdown("---")


def initialize_config():
    """Initialize configuration in session state with defaults."""
    if 'config' not in st.session_state:
        st.session_state.config = {
            # Project Parameters
            'TARGET_DELIVERY_MW': TARGET_DELIVERY_MW,
            'SOLAR_CAPACITY_MW': SOLAR_CAPACITY_MW,

            # Battery Technical Parameters
            'MIN_SOC': MIN_SOC,
            'MAX_SOC': MAX_SOC,
            'ROUND_TRIP_EFFICIENCY': ROUND_TRIP_EFFICIENCY,
            'ONE_WAY_EFFICIENCY': ROUND_TRIP_EFFICIENCY ** 0.5,
            'C_RATE_CHARGE': C_RATE_CHARGE,
            'C_RATE_DISCHARGE': C_RATE_DISCHARGE,

            # Battery Sizing Range
            'MIN_BATTERY_SIZE_MWH': MIN_BATTERY_SIZE_MWH,
            'MAX_BATTERY_SIZE_MWH': MAX_BATTERY_SIZE_MWH,
            'BATTERY_SIZE_STEP_MWH': BATTERY_SIZE_STEP_MWH,

            # Optimization Parameters
            'MARGINAL_IMPROVEMENT_THRESHOLD': MARGINAL_IMPROVEMENT_THRESHOLD,
            'MARGINAL_INCREMENT_MWH': MARGINAL_INCREMENT_MWH,

            # Degradation Parameters
            'DEGRADATION_PER_CYCLE': DEGRADATION_PER_CYCLE,

            # Operational Parameters
            'MAX_DAILY_CYCLES': 2.0,
            'INITIAL_SOC': INITIAL_SOC
        }
        st.success("✅ Configuration initialized with default values")


def reset_to_defaults():
    """Reset all configurations to default values."""
    if 'config' in st.session_state:
        del st.session_state['config']
    initialize_config()
    st.success("✅ Configuration reset to defaults")
    st.rerun()


# Initialize configuration
initialize_config()

# Configuration sections
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌟 Project Parameters")

    st.session_state.config['TARGET_DELIVERY_MW'] = st.number_input(
        "Target Delivery (MW)",
        min_value=1.0,
        max_value=100.0,
        value=st.session_state.config['TARGET_DELIVERY_MW'],
        step=1.0,
        help="Binary delivery target - deliver this amount or nothing"
    )

    st.session_state.config['SOLAR_CAPACITY_MW'] = st.number_input(
        "Solar Capacity (MW)",
        min_value=10.0,
        max_value=200.0,
        value=st.session_state.config['SOLAR_CAPACITY_MW'],
        step=1.0,
        help="Maximum solar generation capacity"
    )

    st.markdown("### 🔋 Battery Sizing Range")

    st.session_state.config['MIN_BATTERY_SIZE_MWH'] = st.number_input(
        "Minimum Battery Size (MWh)",
        min_value=5,
        max_value=100,
        value=st.session_state.config['MIN_BATTERY_SIZE_MWH'],
        step=5,
        help="Minimum battery size to test in optimization"
    )

    st.session_state.config['MAX_BATTERY_SIZE_MWH'] = st.number_input(
        "Maximum Battery Size (MWh)",
        min_value=50,
        max_value=1000,
        value=st.session_state.config['MAX_BATTERY_SIZE_MWH'],
        step=10,
        help="Maximum battery size to test in optimization"
    )

    st.session_state.config['BATTERY_SIZE_STEP_MWH'] = st.selectbox(
        "Battery Size Step (MWh)",
        options=[5, 10, 20, 25, 50],
        index=[5, 10, 20, 25, 50].index(st.session_state.config['BATTERY_SIZE_STEP_MWH']),
        help="Step size for battery sizing optimization"
    )

with col2:
    st.markdown("### ⚡ Battery Technical Parameters")

    # SOC Limits
    min_soc_percent = st.number_input(
        "Minimum SOC (%)",
        min_value=0,
        max_value=20,
        value=int(st.session_state.config['MIN_SOC'] * 100),
        step=1,
        help="Minimum State of Charge limit"
    )
    st.session_state.config['MIN_SOC'] = min_soc_percent / 100

    max_soc_percent = st.number_input(
        "Maximum SOC (%)",
        min_value=80,
        max_value=100,
        value=int(st.session_state.config['MAX_SOC'] * 100),
        step=1,
        help="Maximum State of Charge limit"
    )
    st.session_state.config['MAX_SOC'] = max_soc_percent / 100

    # Calculate usable capacity
    usable_capacity = (st.session_state.config['MAX_SOC'] - st.session_state.config['MIN_SOC']) * 100
    st.info(f"**Usable Capacity:** {usable_capacity:.0f}% of rated")

    # Efficiency
    rte_percent = st.number_input(
        "Round-Trip Efficiency (%)",
        min_value=70,
        max_value=95,
        value=int(st.session_state.config['ROUND_TRIP_EFFICIENCY'] * 100),
        step=1,
        help="Round-trip efficiency of the battery system"
    )
    st.session_state.config['ROUND_TRIP_EFFICIENCY'] = rte_percent / 100
    st.session_state.config['ONE_WAY_EFFICIENCY'] = (rte_percent / 100) ** 0.5

    one_way_eff = st.session_state.config['ONE_WAY_EFFICIENCY'] * 100
    st.info(f"**One-Way Efficiency:** {one_way_eff:.1f}%")

    # C-rates
    st.session_state.config['C_RATE_CHARGE'] = st.number_input(
        "C-Rate Charge",
        min_value=0.25,
        max_value=2.0,
        value=st.session_state.config['C_RATE_CHARGE'],
        step=0.25,
        help="Maximum charge rate as fraction of capacity"
    )

    st.session_state.config['C_RATE_DISCHARGE'] = st.number_input(
        "C-Rate Discharge",
        min_value=0.25,
        max_value=2.0,
        value=st.session_state.config['C_RATE_DISCHARGE'],
        step=0.25,
        help="Maximum discharge rate as fraction of capacity"
    )

with col3:
    st.markdown("### 🔄 Operational Parameters")

    st.session_state.config['MAX_DAILY_CYCLES'] = st.number_input(
        "Max Daily Cycles",
        min_value=0.5,
        max_value=4.0,
        value=st.session_state.config['MAX_DAILY_CYCLES'],
        step=0.5,
        help="Maximum number of cycles allowed per day"
    )

    initial_soc_percent = st.number_input(
        "Initial SOC (%)",
        min_value=0,
        max_value=100,
        value=int(st.session_state.config['INITIAL_SOC'] * 100),
        step=5,
        help="Initial State of Charge at start of simulation"
    )
    st.session_state.config['INITIAL_SOC'] = initial_soc_percent / 100

    st.markdown("### 📉 Degradation Parameters")

    degradation_percent = st.number_input(
        "Degradation per Cycle (%)",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.config['DEGRADATION_PER_CYCLE'] * 100,
        step=0.01,
        format="%.3f",
        help="Capacity degradation per equivalent full cycle"
    )
    st.session_state.config['DEGRADATION_PER_CYCLE'] = degradation_percent / 100

    st.markdown("### 📊 Optimization Parameters")

    st.session_state.config['MARGINAL_IMPROVEMENT_THRESHOLD'] = st.number_input(
        "Marginal Improvement Threshold (hrs/10MWh)",
        min_value=50,
        max_value=1000,
        value=st.session_state.config['MARGINAL_IMPROVEMENT_THRESHOLD'],
        step=50,
        help="Threshold for marginal improvement algorithm"
    )

    st.session_state.config['MARGINAL_INCREMENT_MWH'] = st.number_input(
        "Marginal Increment (MWh)",
        min_value=5,
        max_value=50,
        value=st.session_state.config['MARGINAL_INCREMENT_MWH'],
        step=5,
        help="Increment for marginal analysis calculations"
    )

# Configuration summary
st.markdown("---")
st.markdown("### 📋 Configuration Summary")

# Create summary in columns
sum_col1, sum_col2, sum_col3 = st.columns(3)

with sum_col1:
    st.markdown("#### Project")
    st.text(f"Target: {st.session_state.config['TARGET_DELIVERY_MW']:.0f} MW")
    st.text(f"Solar: {st.session_state.config['SOLAR_CAPACITY_MW']:.0f} MW")
    st.text(f"Battery Range: {st.session_state.config['MIN_BATTERY_SIZE_MWH']}-{st.session_state.config['MAX_BATTERY_SIZE_MWH']} MWh")

with sum_col2:
    st.markdown("#### Technical")
    st.text(f"SOC Range: {st.session_state.config['MIN_SOC']*100:.0f}%-{st.session_state.config['MAX_SOC']*100:.0f}%")
    st.text(f"RTE: {st.session_state.config['ROUND_TRIP_EFFICIENCY']*100:.0f}%")
    st.text(f"C-rates: {st.session_state.config['C_RATE_CHARGE']:.1f}/{st.session_state.config['C_RATE_DISCHARGE']:.1f}")

with sum_col3:
    st.markdown("#### Operational")
    st.text(f"Max Cycles/Day: {st.session_state.config['MAX_DAILY_CYCLES']:.1f}")
    st.text(f"Degradation: {st.session_state.config['DEGRADATION_PER_CYCLE']*100:.3f}%/cycle")
    st.text(f"Initial SOC: {st.session_state.config['INITIAL_SOC']*100:.0f}%")

# Action buttons
st.markdown("---")
col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

with col1:
    if st.button("💾 Save Configuration", type="primary"):
        st.success("✅ Configuration saved to session")

with col2:
    if st.button("🔄 Reset to Defaults"):
        reset_to_defaults()

with col3:
    # Export configuration
    import json
    config_json = json.dumps(st.session_state.config, indent=2)
    st.download_button(
        label="📥 Export Config",
        data=config_json,
        file_name="bess_configuration.json",
        mime="application/json"
    )

# Instructions
with st.expander("ℹ️ How to Use"):
    st.markdown("""
    ### Configuration Instructions

    1. **Modify Parameters**: Adjust any parameters using the input fields above
    2. **Save Configuration**: Click "Save Configuration" to apply changes
    3. **Use in Analysis**: Navigate to Simulation or Optimization pages - they will use these settings
    4. **Reset**: Click "Reset to Defaults" to restore original values
    5. **Export**: Download current configuration as JSON for backup or sharing

    ### Parameter Guidelines

    - **SOC Limits**: Define operational range (typically 5-95%)
    - **C-Rates**: Higher values allow faster charge/discharge
    - **Daily Cycles**: Limits battery usage to preserve lifespan
    - **Degradation**: Realistic values are 0.1-0.2% per cycle
    - **Efficiency**: Modern batteries achieve 85-90% round-trip efficiency

    ### Impact on Analysis

    These configurations directly affect:
    - Battery operation simulation
    - Optimization algorithms
    - Economic calculations
    - Performance metrics
    """)

# Display warning if unusual values
warnings = []

if st.session_state.config['MIN_SOC'] >= st.session_state.config['MAX_SOC']:
    warnings.append("⚠️ Minimum SOC must be less than Maximum SOC")

if st.session_state.config['MIN_BATTERY_SIZE_MWH'] >= st.session_state.config['MAX_BATTERY_SIZE_MWH']:
    warnings.append("⚠️ Minimum battery size must be less than maximum")

if st.session_state.config['ROUND_TRIP_EFFICIENCY'] < 0.7:
    warnings.append("⚠️ Round-trip efficiency seems unusually low")

if st.session_state.config['DEGRADATION_PER_CYCLE'] > 0.005:
    warnings.append("⚠️ Degradation rate seems unusually high")

if st.session_state.config['MAX_DAILY_CYCLES'] > 3:
    warnings.append("⚠️ Daily cycle limit is higher than typical battery warranty")

if warnings:
    st.markdown("---")
    st.markdown("### ⚠️ Configuration Warnings")
    for warning in warnings:
        st.warning(warning)