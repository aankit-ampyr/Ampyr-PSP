"""
Hourly Operation Examples Page
Detailed hour-by-hour simulation tables for various dispatch scenarios
Computed dynamically using the app's implemented logic
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.battery_simulator import BatterySystem


def create_scenario_graph(df, scenario_name):
    """Create a standard dispatch graph from simulation dataframe."""
    hours = df['Hour'].tolist()
    solar_mw = df['Solar_MW'].tolist()
    dg_mw = df['DG_MW'].tolist()
    bess_mw = df['BESS_Power_MW'].tolist()
    soc_pct = df['SoC_%'].tolist()
    bess_energy_mwh = df['BESS_Energy_MWh'].tolist()
    delivery_mw = [25 if d == 0 else 0 for d in df['Deficit_MW'].tolist()]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Solar (orange fill)
    fig.add_trace(
        go.Scatter(x=hours, y=solar_mw, name='Solar', fill='tozeroy',
                   line=dict(color='#FFA500', width=2),
                   hovertemplate='Hour %{x}<br>Solar: %{y:.1f} MW<extra></extra>'),
        secondary_y=False
    )

    # DG Output (red fill) - only if DG is used
    if any(d > 0 for d in dg_mw):
        fig.add_trace(
            go.Scatter(x=hours, y=dg_mw, name='DG Output', fill='tozeroy',
                       line=dict(color='#DC143C', width=2, shape='hv'),
                       fillcolor='rgba(220,20,60,0.3)',
                       hovertemplate='Hour %{x}<br>DG Output: %{y} MW<extra></extra>'),
            secondary_y=False
        )

    # BESS Power (blue solid)
    fig.add_trace(
        go.Scatter(x=hours, y=bess_mw, name='BESS Power',
                   line=dict(color='#1f77b4', width=2, shape='hv'),
                   hovertemplate='Hour %{x}<br>BESS: %{y:.1f} MW<extra></extra>'),
        secondary_y=False
    )

    # SOC % (green dotted)
    fig.add_trace(
        go.Scatter(x=hours, y=soc_pct, name='SOC %',
                   line=dict(color='#2E8B57', width=2, dash='dot', shape='hv'),
                   hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'),
        secondary_y=True
    )

    # BESS Energy (royal blue dashed)
    fig.add_trace(
        go.Scatter(x=hours, y=bess_energy_mwh, name='BESS Energy (MWh)',
                   line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
                   hovertemplate='Hour %{x}<br>BESS Energy: %{y:.1f} MWh<extra></extra>'),
        secondary_y=True
    )

    # Delivery (purple thick)
    fig.add_trace(
        go.Scatter(x=hours, y=delivery_mw, name='Delivery',
                   line=dict(color='purple', width=3, shape='hv'),
                   hovertemplate='Hour %{x}<br>Delivery: %{y} MW<extra></extra>'),
        secondary_y=False
    )

    # Reference lines
    fig.add_hline(y=25, line_dash="dash", line_color="gray",
                  annotation_text="Load 25 MW", secondary_y=False)
    fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)

    # Day boundary
    fig.add_vline(x=24, line_dash="dash", line_color="black", line_width=1,
                  annotation_text="Day 2", annotation_position="top")

    # Hourly grid
    for h in range(48):
        fig.add_vline(x=h, line_dash="dot", line_color="lightgray", line_width=1)

    # Layout
    fig.update_layout(
        title=f"{scenario_name} — June 15-16 Dispatch",
        xaxis_title="Hour (0-23: June 15 | 24-47: June 16)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        xaxis=dict(showgrid=False,
                   tickvals=[0, 6, 12, 18, 24, 30, 36, 42, 47],
                   ticktext=['0', '6', '12', '18', '24', '30', '36', '42', '47'])
    )
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="SOC (%) / BESS Energy (MWh)", secondary_y=True, range=[0, 100])

    return fig

# Page config
st.set_page_config(page_title="Hourly Examples", page_icon="📊", layout="wide")

st.title("📊 Hourly Operation Examples")
st.markdown("""
This page provides detailed hour-by-hour simulation tables demonstrating various dispatch strategies.
All scenarios are computed dynamically using the app's implemented logic.
""")
st.markdown("---")


# =============================================================================
# SCENARIO DEFINITIONS (Rules and descriptions)
# =============================================================================

SCENARIOS = {
    'T0': {
        'name': 'T0: Solar + BESS Only',
        'subtitle': 'No DG - Pure renewable operation',
        'merit_order': 'Solar → BESS → Unserved',
        'description': 'Pure green system with no DG. BESS provides backup when solar insufficient.',
        'dispatch_rules': [
            '1. Solar serves load first (direct priority)',
            '2. BESS discharges to cover remaining load after solar',
            '3. If BESS depleted (SoC ≤ 10%), load goes unserved',
            '4. No DG available in this topology'
        ],
        'charging_rules': [
            '1. BESS charges ONLY from excess solar (after load served)',
            '2. Charge rate limited by BESS power (100 MW)',
            '3. Charge efficiency: 92.2% one-way',
            '4. If BESS full (SoC = 90%), excess solar is curtailed'
        ],
        'constraints': 'SoC bounded: 10% (min) to 90% (max) | No DG backup'
    },
    'T1': {
        'name': 'T1: Green Priority',
        'subtitle': 'DG as last resort when Solar+BESS insufficient',
        'merit_order': 'Solar → BESS → DG → Unserved',
        'description': 'Maximize green energy. DG activates only when Solar + BESS cannot meet load.',
        'dispatch_rules': [
            '1. Solar serves load first (highest priority)',
            '2. BESS discharges to cover remaining load',
            '3. DG activates ONLY when Solar + BESS insufficient',
            '4. DG runs at Full Capacity (27 MW) when ON'
        ],
        'charging_rules': [
            '1. BESS charges from excess solar (priority 1)',
            '2. BESS charges from excess DG when DG running',
            '3. Charging only when BESS not discharging',
            '4. Charge rate limited by BESS power (100 MW)'
        ],
        'constraints': 'DG is reactive only - no proactive charging | Green-first philosophy'
    },
    'T2': {
        'name': 'T2: DG Night Charge',
        'subtitle': 'DG proactive at night (18:00-06:00), green during day',
        'merit_order': 'Night: DG → BESS | Day: Solar → BESS → Unserved',
        'description': 'DG runs proactively at night to charge BESS. Day is strictly green.',
        'dispatch_rules': [
            '1. NIGHT (18:00-06:00): DG turns ON when SoC ≤ 30%',
            '2. NIGHT: DG serves load, excess charges BESS',
            '3. NIGHT: DG OFF when SoC reaches 80%',
            '4. DAY (06:00-18:00): DG DISABLED',
            '5. DAY: Solar → BESS → Unserved'
        ],
        'charging_rules': [
            '1. NIGHT: BESS charges from excess DG',
            '2. DAY: BESS charges from excess solar only',
            '3. Charging stops at SoC = 90%'
        ],
        'constraints': 'DG proactive at night | Day strictly green | SoC thresholds: ON ≤ 30%, OFF ≥ 80%'
    },
    'T3': {
        'name': 'T3: DG Blackout',
        'subtitle': 'DG disabled during blackout hours (22:00-06:00)',
        'merit_order': 'Blackout: Solar → BESS → Unserved | Normal: Solar → BESS → DG',
        'description': 'DG disabled during blackout hours (noise/emissions). Reactive outside blackout.',
        'dispatch_rules': [
            '1. BLACKOUT (22:00-06:00): DG strictly DISABLED',
            '2. BLACKOUT: Solar → BESS → Unserved',
            '3. OUTSIDE: Solar → BESS → DG → Unserved',
            '4. DG reactive (only when Solar+BESS insufficient)'
        ],
        'charging_rules': [
            '1. BESS charges from excess solar (always)',
            '2. BESS charges from excess DG (outside blackout)',
            '3. No DG charging during blackout'
        ],
        'constraints': 'DG cannot run during blackout | BESS must survive blackout hours'
    },
    'T4': {
        'name': 'T4: DG Emergency',
        'subtitle': 'SOC-triggered DG anytime (Range Extender)',
        'merit_order': 'DG OFF: Solar → BESS | DG ON: Solar → DG → BESS',
        'description': 'SoC-triggered DG with no time restrictions. DG as Range Extender.',
        'dispatch_rules': [
            '1. Normal: Solar → BESS → Unserved (DG OFF)',
            '2. DG ON when SoC ≤ 30%',
            '3. DG OFF when SoC ≥ 80%',
            '4. ASSIST MODE: DG < Load → BESS assists',
            '5. No time restrictions - DG anytime'
        ],
        'charging_rules': [
            '1. BESS charges from excess solar (DG OFF)',
            '2. BESS charges from excess DG (Recovery Mode)',
            '3. No charging in Assist Mode (discharging)'
        ],
        'constraints': 'Deadband: ON ≤ 30%, OFF ≥ 80% | DG SoC-triggered, not load-triggered'
    },
    'T5': {
        'name': 'T5: DG Day Charge',
        'subtitle': 'SOC-triggered DG during day, silent nights',
        'merit_order': 'Day: Solar → DG (if triggered) → BESS | Night: Solar → BESS',
        'description': 'SoC-triggered DG during day. Night is silent (DG disabled).',
        'dispatch_rules': [
            '1. DAY (06:00-18:00): DG allowed (SoC-triggered)',
            '2. DAY: DG ON ≤ 30%, OFF ≥ 80%',
            '3. NIGHT (18:00-06:00): DG DISABLED (silent)',
            '4. NIGHT: Solar → BESS → Unserved',
            '5. SUNSET CUT: DG OFF when night starts'
        ],
        'charging_rules': [
            '1. DAY: BESS charges from solar + DG (Recovery)',
            '2. NIGHT: BESS charges from solar only',
            '3. No DG charging at night'
        ],
        'constraints': 'Silent nights for residential areas | DG SoC-triggered during day only'
    },
    'T6': {
        'name': 'T6: DG Night SoC',
        'subtitle': 'SOC-triggered DG at night, green days',
        'merit_order': 'Night: Solar → DG (if triggered) → BESS | Day: Solar → BESS',
        'description': 'SoC-triggered DG during night. Day is green (DG disabled).',
        'dispatch_rules': [
            '1. NIGHT (18:00-06:00): DG allowed (SoC-triggered)',
            '2. NIGHT: DG ON ≤ 30%, OFF ≥ 80%',
            '3. DAY (06:00-18:00): DG DISABLED (green)',
            '4. DAY: Solar → BESS → Unserved',
            '5. SUNRISE CUT: DG OFF when day starts'
        ],
        'charging_rules': [
            '1. NIGHT: BESS charges from DG (Recovery Mode)',
            '2. DAY: BESS charges from solar only',
            '3. No DG charging during day'
        ],
        'constraints': 'Green days maximize solar | DG runs only at night for recharge'
    }
}


# =============================================================================
# MAIN TABS
# =============================================================================

main_tab1, main_tab2, main_tab3 = st.tabs([
    "⚡ Dispatch & Charging Logic",
    "📋 All Simulation Scenarios",
    "📈 Summary Comparison"
])

# =============================================================================
# TAB 1: DISPATCH & CHARGING LOGIC
# =============================================================================
with main_tab1:
    st.markdown("## Dispatch & Charging Rules")

    st.info("""
    **Configuration:** 100 MWh BESS | 27 MW DG | 25 MW Load | SOC Limits: 10%-90% | Efficiency: 85%

    Each template below defines a different dispatch strategy with specific rules for when DG runs,
    how load is served, and how BESS is charged.
    """)

    scenario_tabs = st.tabs([SCENARIOS[k]['name'] for k in SCENARIOS])

    for idx, (key, scenario) in enumerate(SCENARIOS.items()):
        with scenario_tabs[idx]:
            st.markdown(f"### {scenario['name']}")
            st.caption(scenario['subtitle'])

            st.success(scenario['description'])
            st.markdown(f"**Merit Order:** `{scenario['merit_order']}`")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Dispatch Rules")
                for rule in scenario['dispatch_rules']:
                    st.markdown(f"- {rule}")

            with col2:
                st.markdown("#### Charging Rules")
                for rule in scenario['charging_rules']:
                    st.markdown(f"- {rule}")

            st.warning(f"**Constraints:** {scenario['constraints']}")
            st.markdown("---")

# =============================================================================
# TAB 2: ALL SIMULATION SCENARIOS
# =============================================================================
with main_tab2:
    st.markdown("## Simulation Scenarios (48-Hour Data)")

    st.info("""
    **Configuration:** 100 MWh BESS | 27 MW DG | 25 MW Load | SOC Limits: 10%-90%

    Each scenario shows 48 hours (June 15-16) of simulation data computed dynamically:
    - 🟥 **Pink**: Deficit (delivery failure)
    - 🟨 **Yellow**: DG running
    - 🟪 **Lavender**: BESS discharging
    - 🟩 **Green**: BESS charging
    """)

    # Load solar data once
    @st.cache_data
    def load_june15_16_solar():
        """Load June 15-16 solar data (48 hours)."""
        solar_df = pd.read_csv('Inputs/Solar Profile.csv')
        june_15_start = 24 * (31 + 28 + 31 + 30 + 31 + 14)  # Hour index for June 15
        return solar_df['Solar_Generation_MW'].iloc[june_15_start:june_15_start+48].values

    def get_base_config():
        """Get base configuration for simulations."""
        return {
            'MIN_SOC': 0.10, 'MAX_SOC': 0.90,
            'ONE_WAY_EFFICIENCY': 0.85 ** 0.5,
            'C_RATE_CHARGE': 1.0, 'C_RATE_DISCHARGE': 1.0,
            'INITIAL_SOC': 0.50,
            'MAX_DAILY_CYCLES': 2.0
        }

    # Styling function (same pattern as calculation_logic.py)
    def style_scenario_row(row):
        if row['Deficit_MW'] > 0:
            return ['background-color: #FFB6C1'] * len(row)
        if row['DG_MW'] > 0:
            return ['background-color: #FFFACD'] * len(row)
        if row['BESS_State'] == 'Discharging':
            return ['background-color: #E6E6FA'] * len(row)
        if row['BESS_State'] == 'Charging':
            return ['background-color: #90EE90'] * len(row)
        return [''] * len(row)

    # Create sub-tabs for each scenario
    data_tabs = st.tabs([SCENARIOS[k]['name'] for k in SCENARIOS])

    # -------------------------------------------------------------------------
    # T0: Solar + BESS Only
    # -------------------------------------------------------------------------
    with data_tabs[0]:
        st.markdown("### T0: Solar + BESS Only")

        @st.cache_data
        def compute_t0():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)  # 100 MWh battery
            load_mw = 25
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                remaining_load = load_mw

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                solar_charged = 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)

                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif solar_charged > 0:
                    bess_state, bess_power = 'Charging', -solar_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': 0,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': 0
                })

            return pd.DataFrame(results)

        df_t0 = compute_t0()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t0['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t0['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", "0 hours")
        col4.metric("DG Energy", "0 MWh")

        display_cols = ['Hour', 'Day', 'Solar_MW', 'DG_MW', 'BESS_Power_MW',
                        'BESS_Energy_MWh', 'SoC_%', 'BESS_State', 'Load_MW',
                        'Deficit_MW', 'Solar_to_Load', 'BESS_to_Load', 'DG_to_Load']

        st.dataframe(
            df_t0[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t0 = create_scenario_graph(df_t0, "T0: Solar + BESS Only")
        st.plotly_chart(fig_t0, width='stretch')

    # -------------------------------------------------------------------------
    # T1: Green Priority
    # -------------------------------------------------------------------------
    with data_tabs[1]:
        st.markdown("### T1: Green Priority")

        @st.cache_data
        def compute_t1():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                remaining_load = load_mw

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if remaining_load > 0.001:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t1 = compute_t1()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t1['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t1['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t1['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t1['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t1[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t1 = create_scenario_graph(df_t1, "T1: Green Priority")
        st.plotly_chart(fig_t1, width='stretch')

    # -------------------------------------------------------------------------
    # T2: DG Night Charge
    # -------------------------------------------------------------------------
    with data_tabs[2]:
        st.markdown("### T2: DG Night Charge")

        @st.cache_data
        def compute_t2():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            dg_on = False
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                hour_of_day = hour % 24
                remaining_load = load_mw

                is_night = hour_of_day >= 18 or hour_of_day < 6

                if is_night:
                    if not dg_on and battery.soc <= 0.30:
                        dg_on = True
                    elif dg_on and battery.soc >= 0.80:
                        dg_on = False
                else:
                    dg_on = False

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if dg_on:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t2 = compute_t2()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t2['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t2['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t2['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t2['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t2[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t2 = create_scenario_graph(df_t2, "T2: DG Night Charge")
        st.plotly_chart(fig_t2, width='stretch')

    # -------------------------------------------------------------------------
    # T3: DG Blackout
    # -------------------------------------------------------------------------
    with data_tabs[3]:
        st.markdown("### T3: DG Blackout")

        @st.cache_data
        def compute_t3():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                hour_of_day = hour % 24
                remaining_load = load_mw

                is_blackout = hour_of_day >= 22 or hour_of_day < 6
                dg_available = not is_blackout

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if dg_available and remaining_load > 0.001:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t3 = compute_t3()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t3['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t3['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t3['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t3['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t3[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t3 = create_scenario_graph(df_t3, "T3: DG Blackout")
        st.plotly_chart(fig_t3, width='stretch')

    # -------------------------------------------------------------------------
    # T4: DG Emergency
    # -------------------------------------------------------------------------
    with data_tabs[4]:
        st.markdown("### T4: DG Emergency")

        @st.cache_data
        def compute_t4():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            dg_on = False
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                remaining_load = load_mw

                if not dg_on and battery.soc <= 0.30:
                    dg_on = True
                elif dg_on and battery.soc >= 0.80:
                    dg_on = False

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if dg_on:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t4 = compute_t4()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t4['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t4['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t4['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t4['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t4[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t4 = create_scenario_graph(df_t4, "T4: DG Emergency")
        st.plotly_chart(fig_t4, width='stretch')

    # -------------------------------------------------------------------------
    # T5: DG Day Charge
    # -------------------------------------------------------------------------
    with data_tabs[5]:
        st.markdown("### T5: DG Day Charge")

        @st.cache_data
        def compute_t5():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            dg_on = False
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                hour_of_day = hour % 24
                remaining_load = load_mw

                is_day = 6 <= hour_of_day < 18

                if is_day:
                    if not dg_on and battery.soc <= 0.30:
                        dg_on = True
                    elif dg_on and battery.soc >= 0.80:
                        dg_on = False
                else:
                    dg_on = False

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if dg_on:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t5 = compute_t5()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t5['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t5['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t5['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t5['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t5[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t5 = create_scenario_graph(df_t5, "T5: DG Day Charge")
        st.plotly_chart(fig_t5, width='stretch')

    # -------------------------------------------------------------------------
    # T6: DG Night SoC
    # -------------------------------------------------------------------------
    with data_tabs[6]:
        st.markdown("### T6: DG Night SoC")

        @st.cache_data
        def compute_t6():
            solar_data = load_june15_16_solar()
            config = get_base_config()
            battery = BatterySystem(100, config)
            load_mw, dg_capacity = 25, 27
            dg_on = False
            results = []

            for hour in range(48):
                solar_mw = solar_data[hour]
                hour_of_day = hour % 24
                remaining_load = load_mw

                is_night = hour_of_day >= 18 or hour_of_day < 6

                if is_night:
                    if not dg_on and battery.soc <= 0.30:
                        dg_on = True
                    elif dg_on and battery.soc >= 0.80:
                        dg_on = False
                else:
                    dg_on = False

                solar_to_load = min(solar_mw, remaining_load)
                remaining_load -= solar_to_load
                excess_solar = solar_mw - solar_to_load

                dg_output, dg_to_load, excess_dg = 0, 0, 0
                if dg_on:
                    dg_output = dg_capacity
                    dg_to_load = min(dg_output, remaining_load)
                    remaining_load -= dg_to_load
                    excess_dg = dg_output - dg_to_load

                bess_to_load = 0
                if remaining_load > 0 and battery.get_available_energy() > 0:
                    bess_to_load = battery.discharge(remaining_load)
                    remaining_load -= bess_to_load

                solar_charged, dg_charged = 0, 0
                if excess_solar > 0 and battery.get_charge_headroom() > 0:
                    solar_charged = battery.charge(excess_solar)
                if excess_dg > 0 and battery.get_charge_headroom() > 0:
                    dg_charged = battery.charge(excess_dg)

                total_charged = solar_charged + dg_charged
                if bess_to_load > 0:
                    bess_state, bess_power = 'Discharging', bess_to_load
                elif total_charged > 0:
                    bess_state, bess_power = 'Charging', -total_charged
                else:
                    bess_state, bess_power = 'Idle', 0

                deficit = remaining_load if remaining_load > 0.001 else 0

                results.append({
                    'Hour': hour, 'Day': 1 if hour < 24 else 2,
                    'Solar_MW': round(solar_mw, 2), 'DG_MW': dg_output,
                    'BESS_Power_MW': round(bess_power, 2),
                    'BESS_Energy_MWh': round(battery.soc * 100, 2),
                    'SoC_%': round(battery.soc * 100, 1),
                    'BESS_State': bess_state, 'Load_MW': load_mw,
                    'Deficit_MW': round(deficit, 2),
                    'Solar_to_Load': round(solar_to_load, 2),
                    'BESS_to_Load': round(bess_to_load, 2),
                    'DG_to_Load': round(dg_to_load, 2)
                })

            return pd.DataFrame(results)

        df_t6 = compute_t6()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Delivery Hours", f"{(df_t6['Deficit_MW'] == 0).sum()}/48")
        col2.metric("Total Deficit", f"{df_t6['Deficit_MW'].sum():.1f} MWh")
        col3.metric("DG Runtime", f"{(df_t6['DG_MW'] > 0).sum()} hours")
        col4.metric("DG Energy", f"{df_t6['DG_MW'].sum():.0f} MWh")

        st.dataframe(
            df_t6[display_cols].style.apply(style_scenario_row, axis=1),
            width='stretch',
            height=600
        )

        # Graph
        st.markdown("#### Dispatch Graph")
        fig_t6 = create_scenario_graph(df_t6, "T6: DG Night SoC")
        st.plotly_chart(fig_t6, width='stretch')

    st.caption("""
    **Color Legend:** Pink = Deficit | Yellow = DG Running | Lavender = BESS Discharging | Green = BESS Charging

    **Graph Legend:** Orange = Solar | Red = DG | Blue = BESS Power | Purple = Delivery | Green dotted = SOC% | Royal Blue dashed = BESS Energy
    """)

# =============================================================================
# TAB 3: SUMMARY COMPARISON
# =============================================================================
with main_tab3:
    st.markdown("## Scenario Summary Comparison")

    st.info("""
    Compare all dispatch strategies side-by-side. Lower deficit indicates better reliability.
    Lower DG usage indicates greener operation.
    """)

    # Build summary from computed scenarios
    @st.cache_data
    def build_summary():
        scenarios_data = {
            'T0': compute_t0(),
            'T1': compute_t1(),
            'T2': compute_t2(),
            'T3': compute_t3(),
            'T4': compute_t4(),
            'T5': compute_t5(),
            'T6': compute_t6()
        }

        summary_data = []
        for key, df in scenarios_data.items():
            summary_data.append({
                'Scenario': SCENARIOS[key]['name'],
                'Delivery_Hours': (df['Deficit_MW'] == 0).sum(),
                'Total_Deficit_MWh': round(df['Deficit_MW'].sum(), 1),
                'DG_Hours': (df['DG_MW'] > 0).sum(),
                'Total_DG_MWh': round(df['DG_MW'].sum(), 1)
            })

        return pd.DataFrame(summary_data)

    summary_df = build_summary()

    st.markdown("### Performance Metrics")
    st.dataframe(summary_df, width='stretch')

    st.markdown("---")

    st.markdown("### Visual Comparison")

    col1, col2 = st.columns(2)

    with col1:
        fig_deficit = go.Figure(data=[
            go.Bar(
                x=summary_df['Scenario'],
                y=summary_df['Total_Deficit_MWh'],
                marker_color=['#FFB6C1' if d > 0 else '#90EE90' for d in summary_df['Total_Deficit_MWh']],
                text=summary_df['Total_Deficit_MWh'],
                textposition='auto'
            )
        ])
        fig_deficit.update_layout(
            title='Total Deficit by Scenario (MWh)',
            xaxis_title='Scenario',
            yaxis_title='Deficit (MWh)',
            height=400
        )
        st.plotly_chart(fig_deficit, width='stretch')

    with col2:
        fig_dg = go.Figure(data=[
            go.Bar(
                x=summary_df['Scenario'],
                y=summary_df['Total_DG_MWh'],
                marker_color='#FFFACD',
                text=summary_df['Total_DG_MWh'],
                textposition='auto'
            )
        ])
        fig_dg.update_layout(
            title='Total DG Energy by Scenario (MWh)',
            xaxis_title='Scenario',
            yaxis_title='DG Energy (MWh)',
            height=400
        )
        st.plotly_chart(fig_dg, width='stretch')

    st.markdown("### Key Insights")

    best_idx = summary_df['Total_Deficit_MWh'].idxmin()
    worst_idx = summary_df['Total_Deficit_MWh'].idxmax()

    col1, col2 = st.columns(2)

    with col1:
        st.success(f"**Best Delivery:** {summary_df.loc[best_idx, 'Scenario']} ({summary_df.loc[best_idx, 'Total_Deficit_MWh']} MWh deficit)")

    with col2:
        st.error(f"**Highest Deficit:** {summary_df.loc[worst_idx, 'Scenario']} ({summary_df.loc[worst_idx, 'Total_Deficit_MWh']} MWh deficit)")

# Footer
st.markdown("---")
st.caption("""
**Data Source:** Computed dynamically using June 15-16 solar data from Inputs/Solar Profile.csv

**Configuration:** 100 MWh BESS | 27 MW DG | 25 MW Load | SOC: 10%-90% | Efficiency: 85%
""")
