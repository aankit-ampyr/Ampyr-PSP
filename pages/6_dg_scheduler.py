"""
Day-Ahead DG Scheduler
Calculates optimal DG runtime hours based on energy deficit analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from math import ceil

from src.data_loader import load_solar_profile
from utils.config_manager import get_config


# Page config
st.set_page_config(page_title="DG Scheduler", page_icon="🗓️", layout="wide")

st.title("🗓️ Day-Ahead DG Scheduler")
st.markdown("""
**Scenario 1**: DG = Load (no excess for BESS charging)

This scheduler runs at 11:30 PM to determine optimal DG hours for the next 24 hours
based on energy deficit analysis.
""")

st.markdown("---")

# Get base configuration
config = get_config()

# Load solar profile first to determine date range
solar_profile = load_solar_profile()

if solar_profile is None:
    st.error("❌ Cannot load solar profile. Please ensure Inputs/Solar Profile.csv exists.")
    st.stop()

# Convert to numpy array if needed
if isinstance(solar_profile, pd.DataFrame):
    solar_col = [c for c in solar_profile.columns if 'solar' in c.lower() or 'generation' in c.lower() or 'mw' in c.lower()]
    if solar_col:
        solar_array = solar_profile[solar_col[0]].values
    else:
        solar_array = solar_profile.iloc[:, 0].values
else:
    solar_array = np.array(solar_profile)

# Calculate date range from solar profile
# Assume solar profile starts from Jan 1, 2024
PROFILE_YEAR = 2024
total_days = len(solar_array) // 24
profile_start_date = date(PROFILE_YEAR, 1, 1)
profile_end_date = profile_start_date + timedelta(days=total_days - 1)

st.info(f"📊 Solar profile: {len(solar_array)} hours ({total_days} days) | {profile_start_date.strftime('%b %d, %Y')} to {profile_end_date.strftime('%b %d, %Y')}")

# Sidebar - Other Parameters
st.sidebar.markdown("### ⚙️ Other Parameters")

load_mw = st.sidebar.slider(
    "Load (MW)",
    min_value=10,
    max_value=50,
    value=25,
    step=1,
    help="Constant load to be delivered every hour"
)

initial_soc_pct = st.sidebar.slider(
    "Initial SOC (%)",
    min_value=10,
    max_value=90,
    value=60,
    step=5,
    help="Starting State of Charge for Day 1"
)

# Display config being used
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 BESS Constraints (from Config)")
st.sidebar.info(f"""
**SOC Limits:** {config['MIN_SOC']*100:.0f}% - {config['MAX_SOC']*100:.0f}%
**Round-trip Efficiency:** {config['ROUND_TRIP_EFFICIENCY']*100:.0f}%
**One-way Efficiency:** {config['ONE_WAY_EFFICIENCY']*100:.1f}%
""")

# Main page - System Configuration
st.markdown("### ⚡ System Configuration")

cfg_col1, cfg_col2, cfg_col3, cfg_col4 = st.columns(4)

with cfg_col1:
    dg_mw = st.number_input(
        "DG Size (MW)",
        min_value=10,
        max_value=100,
        value=25,
        step=5,
        help="Diesel Generator rated capacity"
    )

with cfg_col2:
    bess_mw = st.number_input(
        "BESS Power (MW)",
        min_value=10,
        max_value=100,
        value=25,
        step=5,
        help="Battery power rating"
    )

with cfg_col3:
    bess_hours = st.number_input(
        "BESS Duration (hours)",
        min_value=1,
        max_value=8,
        value=4,
        step=1,
        help="Hours of storage at rated power"
    )

with cfg_col4:
    bess_mwh = bess_mw * bess_hours
    st.metric("BESS Capacity", f"{bess_mwh} MWh", help="MW × Hours")

st.markdown("---")

# Main page - Date Selection
st.markdown("### 📅 Select Simulation Period")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    start_date = st.date_input(
        "Start Date",
        value=date(PROFILE_YEAR, 1, 2),
        min_value=profile_start_date,
        max_value=profile_end_date - timedelta(days=1),
        help="First day of simulation"
    )

with col2:
    # Calculate valid end date range
    min_end = start_date + timedelta(days=1)
    max_end = min(start_date + timedelta(days=6), profile_end_date)
    default_end = min(start_date + timedelta(days=2), max_end)

    end_date = st.date_input(
        "End Date",
        value=default_end,
        min_value=min_end,
        max_value=max_end,
        help="Last day of simulation (max 7 days)"
    )

# Validate dates
if end_date <= start_date:
    st.error("End date must be after start date")
    st.stop()

# Calculate number of days
num_days = (end_date - start_date).days + 1
start_day_idx = (start_date - profile_start_date).days

with col3:
    st.info(f"**Selected:** {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')} ({num_days} days)")

st.markdown("---")


def schedule_day(solar_24h, initial_soc, load_mw, dg_mw, bess_mwh, config, day_date):
    """
    Schedule one day of operation.

    Args:
        solar_24h: Array of 24 hourly solar values (MW)
        initial_soc: Starting SOC as fraction (0-1)
        load_mw: Load in MW
        dg_mw: DG capacity in MW
        bess_mwh: BESS capacity in MWh
        config: Configuration dict with SOC limits and efficiency
        day_date: Date object for this day

    Returns:
        hourly_data: List of hourly records
        end_soc: Final SOC as fraction
        dg_hours: Number of DG hours scheduled
    """
    min_soc = config['MIN_SOC']
    max_soc = config['MAX_SOC']
    one_way_eff = config['ONE_WAY_EFFICIENCY']

    # Step 1: Calculate energy balance for the day
    load_energy = load_mw * 24
    solar_energy = sum(solar_24h)
    bess_available = (initial_soc - min_soc) * bess_mwh

    energy_deficit = load_energy - solar_energy - bess_available
    dg_hours = max(0, ceil(energy_deficit / dg_mw)) if energy_deficit > 0 else 0

    # Cap DG hours at 24
    dg_hours = min(dg_hours, 24)

    # Step 2: Simulate 24 hours
    soc = initial_soc
    hourly_data = []

    for hour in range(24):
        solar = solar_24h[hour]

        wastage = 0  # Track wasted solar energy

        if hour < dg_hours:
            # DG period: DG delivers full load
            dg = dg_mw
            bess_power = 0
            delivery = True
            source = "DG"

            # Solar goes to BESS if available and BESS has headroom
            if solar > 0:
                headroom = (max_soc - soc) * bess_mwh
                charge_power = min(solar, headroom)
                if charge_power > 0:
                    soc += (charge_power * one_way_eff) / bess_mwh
                    bess_power = -charge_power  # Negative = charging
                    source = "DG+Solar→BESS"
                # Calculate wastage (solar that couldn't be stored)
                wastage = solar - charge_power
        else:
            # Solar + BESS period
            dg = 0

            if solar >= load_mw:
                # Solar sufficient for load
                delivery = True
                excess = solar - load_mw
                bess_power = 0
                source = "Solar"

                # Charge BESS with excess
                if excess > 0:
                    headroom = (max_soc - soc) * bess_mwh
                    charge_power = min(excess, headroom)
                    if charge_power > 0:
                        soc += (charge_power * one_way_eff) / bess_mwh
                        bess_power = -charge_power
                        source = "Solar+BESS(chg)"
                    # Calculate wastage (excess that couldn't be stored)
                    wastage = excess - charge_power
            else:
                # Need BESS to supplement
                deficit = load_mw - solar
                usable_bess = (soc - min_soc) * bess_mwh

                if usable_bess >= deficit:
                    # BESS can cover deficit
                    delivery = True
                    bess_power = deficit
                    # Account for efficiency when discharging
                    energy_from_bess = deficit / one_way_eff
                    soc -= energy_from_bess / bess_mwh
                    source = "Solar+BESS"
                else:
                    # BESS cannot cover deficit - partial delivery (deficit hour)
                    delivery = False
                    bess_power = usable_bess
                    soc = min_soc
                    source = "DEFICIT"

        # Clamp SOC to bounds
        soc = max(min_soc, min(max_soc, soc))

        # Create datetime for this hour
        hour_datetime = datetime.combine(day_date, datetime.min.time()) + timedelta(hours=hour)

        hourly_data.append({
            'Date': day_date.strftime('%Y-%m-%d'),
            'Hour': hour,
            'Time': hour_datetime.strftime('%H:%M'),
            'Solar_MW': round(solar, 2),
            'DG_MW': round(dg, 2),
            'BESS_MW': round(bess_power, 2),
            'Load_MW': load_mw,
            'SOC_%': round(soc * 100, 1),
            'Wastage_MWh': round(wastage, 2),
            'Delivery': 'Yes' if delivery else 'No',
            'Source': source
        })

    return hourly_data, soc, dg_hours


def simulate_days(solar_array, start_day_idx, num_days, load_mw, dg_mw, bess_mwh, initial_soc_pct, config, start_date):
    """
    Simulate multiple consecutive days.

    Args:
        solar_array: Full year solar profile array
        start_day_idx: Starting day index (0-based)
        num_days: Number of days to simulate
        load_mw: Load in MW
        dg_mw: DG capacity in MW
        bess_mwh: BESS capacity in MWh
        initial_soc_pct: Initial SOC as percentage
        config: Configuration dict
        start_date: Starting date object

    Returns:
        results: List of day results
        all_hourly: Combined hourly data for all days
    """
    results = []
    all_hourly = []
    soc = initial_soc_pct / 100  # Convert to fraction

    for day in range(num_days):
        day_start = (start_day_idx + day) * 24
        day_end = day_start + 24

        # Get current day's date
        current_date = start_date + timedelta(days=day)

        # Get solar data for this day
        if day_end <= len(solar_array):
            solar_24h = solar_array[day_start:day_end]
        else:
            st.warning(f"Day {current_date.strftime('%b %d')} exceeds available solar data")
            break

        # Run scheduling
        start_soc = soc
        hourly_data, end_soc, dg_hours = schedule_day(
            solar_24h, soc, load_mw, dg_mw, bess_mwh, config, current_date
        )

        # Calculate metrics
        delivery_hours = sum(1 for h in hourly_data if h['Delivery'] == 'Yes')
        deficit_hours = 24 - delivery_hours
        solar_total = sum(h['Solar_MW'] for h in hourly_data)
        dg_total = sum(h['DG_MW'] for h in hourly_data)

        results.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Day_Name': current_date.strftime('%a'),
            'Solar_Energy_MWh': round(solar_total, 1),
            'Start_SOC_%': round(start_soc * 100, 1),
            'Load_Energy_MWh': round(load_mw * 24, 1),
            'DG_Energy_MWh': round(dg_total, 1),
            'DG_Hours': dg_hours,
            'Delivery_Hours': delivery_hours,
            'Deficit_Hours': deficit_hours,
            'End_SOC_%': round(end_soc * 100, 1)
        })

        all_hourly.extend(hourly_data)

        # Carry forward SOC
        soc = end_soc

    return results, all_hourly


# Run simulation button
if st.button("🚀 Run Day-Ahead Scheduling", type="primary"):
    with st.spinner("Running simulation..."):
        results, all_hourly = simulate_days(
            solar_array,
            start_day_idx,
            num_days,
            load_mw,
            dg_mw,
            bess_mwh,
            initial_soc_pct,
            config,
            start_date
        )

        # Store in session state
        st.session_state['dg_scheduler_results'] = results
        st.session_state['dg_scheduler_hourly'] = all_hourly

# Display results if available
if 'dg_scheduler_results' in st.session_state:
    results = st.session_state['dg_scheduler_results']
    all_hourly = st.session_state['dg_scheduler_hourly']

    st.markdown("---")
    st.markdown("## 📊 Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    total_dg_hours = sum(r['DG_Hours'] for r in results)
    total_delivery = sum(r['Delivery_Hours'] for r in results)
    total_deficit = sum(r['Deficit_Hours'] for r in results)
    total_hours = len(results) * 24

    col1.metric("Total DG Hours", f"{total_dg_hours}")
    col2.metric("Delivery Hours", f"{total_delivery}/{total_hours}")
    col3.metric("Deficit Hours", f"{total_deficit}")
    col4.metric("Delivery Rate", f"{total_delivery/total_hours*100:.1f}%")

    # Daily Energy Balance table
    st.markdown("### 📅 Daily Energy Balance")
    summary_df = pd.DataFrame(results)
    energy_cols = ['Date', 'Solar_Energy_MWh', 'Start_SOC_%', 'Load_Energy_MWh', 'DG_Energy_MWh', 'DG_Hours']
    energy_df = summary_df[energy_cols].copy()
    energy_df.columns = ['Date', 'Solar Energy (MWh)', 'BESS Start SOC (%)', 'Load Energy (MWh)', 'Energy Deficit (MWh)', 'DG Hours Required']
    st.dataframe(energy_df, width='stretch', hide_index=True)

    # Delivery summary table
    st.markdown("### 📊 Delivery Summary")
    delivery_cols = ['Date', 'Delivery_Hours', 'Deficit_Hours', 'End_SOC_%']
    delivery_df = summary_df[delivery_cols].copy()
    delivery_df.columns = ['Date', 'Delivery Hours', 'Deficit Hours', 'End SOC (%)']
    st.dataframe(delivery_df, width='stretch', hide_index=True)

    st.markdown("---")

    # Hourly schedule table
    st.markdown("### 🕐 Hourly Schedule (All Days)")
    hourly_df = pd.DataFrame(all_hourly)

    # Reorder columns
    col_order = ['Date', 'Hour', 'Time', 'Solar_MW', 'DG_MW', 'BESS_MW', 'Load_MW', 'SOC_%', 'Wastage_MWh', 'Delivery', 'Source']
    hourly_df = hourly_df[col_order]

    # Style function for rows
    def style_row(row):
        if row['Delivery'] == 'No':
            return ['background-color: #ffcccc'] * len(row)  # Red for deficit
        elif row['DG_MW'] > 0:
            return ['background-color: #ffffcc'] * len(row)  # Yellow for DG
        elif row['BESS_MW'] > 0:
            return ['background-color: #e6e6fa'] * len(row)  # Lavender for BESS discharge
        elif row['BESS_MW'] < 0:
            return ['background-color: #ccffcc'] * len(row)  # Green for BESS charge
        else:
            return [''] * len(row)

    styled_df = hourly_df.style.apply(style_row, axis=1)
    st.dataframe(styled_df, width='stretch', height=600)

    st.caption("""
    **Color Legend:** Red = Deficit | Yellow = DG Running | Lavender = BESS Discharging | Green = BESS Charging
    """)

    # Download button
    st.markdown("---")
    csv = hourly_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Hourly Schedule (CSV)",
        data=csv,
        file_name="dg_schedule_hourly.csv",
        mime="text/csv"
    )

# Energy balance explanation
with st.expander("ℹ️ How the Scheduler Works"):
    st.markdown("""
    ### Energy Deficit Calculation (at 11:30 PM)

    ```
    Load Energy     = Load_MW × 24 hours
    Solar Energy    = Sum of predicted solar for next day
    BESS Available  = (Current_SOC - Min_SOC) × BESS_Capacity

    Energy Deficit  = Load Energy - Solar Energy - BESS Available
    DG Hours        = ceil(Energy Deficit / DG_MW)
    ```

    ### Dispatch Priority

    1. **Hours 00:00 to DG_hours**: DG delivers full load
       - Solar during these hours charges BESS

    2. **Remaining hours**: Solar + BESS
       - Solar > Load: Excess charges BESS
       - Solar < Load: BESS discharges to cover deficit
       - Solar + BESS < Load: DEFICIT (delivery fails)

    ### End-of-Day SOC
    - Final SOC carries to next day as starting SOC
    - This affects next day's energy balance calculation
    """)
