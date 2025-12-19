"""
Hourly Operation Examples Page
Demonstrates dispatch templates using the new dispatch engine.
Based on ALGORITHM_SPECIFICATION.md and UX_GUIDELINE.md
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dispatch_engine import (
    SimulationParams, HourlyResult, SummaryMetrics,
    run_simulation, calculate_metrics
)


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

TEMPLATES = {
    0: {
        'name': 'T0: Solar + BESS Only',
        'subtitle': 'Pure green operation - no DG',
        'merit_order': 'Solar → BESS → Unserved',
        'description': 'Pure green system. Load is served only by solar and battery storage.',
        'dispatch_rules': [
            'Solar serves load first (direct priority)',
            'BESS discharges to cover remaining load',
            'If BESS depleted, load goes unserved',
            'No DG available in this topology'
        ],
        'charging_rules': [
            'BESS charges ONLY from excess solar',
            'Charge rate limited by BESS power rating',
            'Efficiency loss applied on charge (√85%)',
            'If BESS full, excess solar is curtailed'
        ],
        'constraints': 'SoC bounded: 10% - 90% | No DG backup',
        'dg_enabled': False
    },
    1: {
        'name': 'T1: Green Priority',
        'subtitle': 'DG as last resort when Solar+BESS insufficient',
        'merit_order': 'Solar → BESS → DG → Unserved',
        'description': 'Maximize green energy. DG activates only when Solar + BESS cannot meet load.',
        'dispatch_rules': [
            'Solar serves load first (highest priority)',
            'BESS discharges to cover remaining load',
            'DG activates ONLY when Solar + BESS insufficient',
            'DG runs at Full Capacity when ON'
        ],
        'charging_rules': [
            'BESS charges from excess solar (priority 1)',
            'BESS charges from excess DG when DG running',
            'Charging only when BESS not discharging'
        ],
        'constraints': 'DG is reactive only | Green-first philosophy',
        'dg_enabled': True
    },
    2: {
        'name': 'T2: DG Night Charge',
        'subtitle': 'DG proactive at night (18:00-06:00), green during day',
        'merit_order': 'Night: DG → BESS | Day: Solar → BESS → Unserved',
        'description': 'DG runs proactively at night to charge BESS. Day is strictly green.',
        'dispatch_rules': [
            'NIGHT (18:00-06:00): DG turns ON when SoC ≤ 30%',
            'NIGHT: DG serves load, excess charges BESS',
            'NIGHT: DG turns OFF when SoC reaches 80%',
            'DAY (06:00-18:00): DG DISABLED',
            'DAY: Solar → BESS → Unserved'
        ],
        'charging_rules': [
            'NIGHT: BESS charges from excess DG',
            'DAY: BESS charges from excess solar only',
            'Charging stops at SoC = 90%'
        ],
        'constraints': 'DG proactive at night | Day strictly green | SoC: ON ≤ 30%, OFF ≥ 80%',
        'dg_enabled': True
    },
    3: {
        'name': 'T3: DG Blackout Window',
        'subtitle': 'DG disabled during blackout hours (22:00-06:00)',
        'merit_order': 'Blackout: Solar → BESS → Unserved | Normal: Solar → BESS → DG',
        'description': 'DG disabled during blackout hours (noise/emissions). Reactive outside blackout.',
        'dispatch_rules': [
            'BLACKOUT (22:00-06:00): DG strictly DISABLED',
            'BLACKOUT: Solar → BESS → Unserved',
            'OUTSIDE: Solar → BESS → DG → Unserved',
            'DG reactive (only when Solar+BESS insufficient)'
        ],
        'charging_rules': [
            'BESS charges from excess solar (always)',
            'BESS charges from excess DG (outside blackout)',
            'No DG charging during blackout'
        ],
        'constraints': 'DG cannot run during blackout | BESS must survive blackout hours',
        'dg_enabled': True
    },
    4: {
        'name': 'T4: DG Emergency Only',
        'subtitle': 'SoC-triggered DG anytime (Range Extender)',
        'merit_order': 'DG OFF: Solar → BESS | DG ON: Solar → DG → BESS (assist)',
        'description': 'SoC-triggered DG with no time restrictions. DG as Range Extender.',
        'dispatch_rules': [
            'Normal: Solar → BESS → Unserved (DG OFF)',
            'DG turns ON when SoC ≤ 30%',
            'DG turns OFF when SoC ≥ 80%',
            'ASSIST MODE: If DG < Load, BESS assists',
            'RECOVERY MODE: If DG ≥ Load, BESS charges',
            'No time restrictions - DG anytime'
        ],
        'charging_rules': [
            'BESS charges from excess solar (DG OFF)',
            'BESS charges from excess DG (Recovery Mode)',
            'No charging in Assist Mode (discharging)'
        ],
        'constraints': 'Deadband: ON ≤ 30%, OFF ≥ 80% | SoC-triggered, not load-triggered',
        'dg_enabled': True
    },
    5: {
        'name': 'T5: DG Day Charge',
        'subtitle': 'SoC-triggered DG during day, silent nights',
        'merit_order': 'Day: Solar → DG (if triggered) → BESS | Night: Solar → BESS',
        'description': 'SoC-triggered DG during day. Night is silent (DG disabled).',
        'dispatch_rules': [
            'DAY (06:00-18:00): DG allowed (SoC-triggered)',
            'DAY: DG ON when SoC ≤ 30%, OFF when SoC ≥ 80%',
            'NIGHT (18:00-06:00): DG DISABLED (silent)',
            'NIGHT: Solar → BESS → Unserved',
            'SUNSET CUT: DG forced OFF when night starts'
        ],
        'charging_rules': [
            'DAY: BESS charges from solar + DG excess',
            'NIGHT: BESS charges from solar only',
            'No DG charging at night'
        ],
        'constraints': 'Silent nights | DG SoC-triggered during day only',
        'dg_enabled': True
    },
    6: {
        'name': 'T6: DG Night SoC Trigger',
        'subtitle': 'SoC-triggered DG at night, green days',
        'merit_order': 'Night: Solar → DG (if triggered) → BESS | Day: Solar → BESS',
        'description': 'SoC-triggered DG during night. Day is green (DG disabled).',
        'dispatch_rules': [
            'NIGHT (18:00-06:00): DG allowed (SoC-triggered)',
            'NIGHT: DG ON when SoC ≤ 30%, OFF when SoC ≥ 80%',
            'DAY (06:00-18:00): DG DISABLED (green)',
            'DAY: Solar → BESS → Unserved',
            'SUNRISE CUT: DG forced OFF when day starts'
        ],
        'charging_rules': [
            'NIGHT: BESS charges from DG excess (Recovery)',
            'DAY: BESS charges from solar only',
            'No DG charging during day'
        ],
        'constraints': 'Green days | DG SoC-triggered during night only',
        'dg_enabled': True
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@st.cache_data
def load_solar_profile():
    """Load full solar profile from CSV."""
    try:
        df = pd.read_csv('Inputs/Solar Profile.csv')
        return df['Solar_Generation_MW'].values.tolist()
    except Exception:
        # Return sample data if file not found
        return [0] * 8760


def get_june_15_16_data(solar_profile):
    """Extract June 15-16 (48 hours) from solar profile."""
    # June 15 is day 166 (31+28+31+30+31+14 = 165 days before, 0-indexed)
    june_15_start = 24 * (31 + 28 + 31 + 30 + 31 + 14)
    return solar_profile[june_15_start:june_15_start + 48]


def create_constant_load(load_mw: float, hours: int = 48) -> list:
    """Create constant load profile."""
    return [load_mw] * hours


def results_to_dataframe(results: list) -> pd.DataFrame:
    """Convert HourlyResult list to DataFrame."""
    data = []
    for r in results:
        data.append({
            'Hour': r.t - 1,  # 0-indexed for display
            'Day': 1 if r.t <= 24 else 2,
            'Solar_MW': round(r.solar, 2),
            'DG_MW': round(r.dg_to_load + r.dg_to_bess + r.dg_curtailed, 2) if r.dg_running else 0,
            'BESS_Power_MW': round(r.bess_power, 2),
            'BESS_Energy_MWh': round(r.soc, 2),
            'SoC_%': round(r.soc_pct, 1),
            'BESS_State': r.bess_state,
            'Load_MW': round(r.load, 2),
            'Deficit_MW': round(r.unserved, 2),
            'Solar_to_Load': round(r.solar_to_load, 2),
            'BESS_to_Load': round(r.bess_to_load, 2),
            'DG_to_Load': round(r.dg_to_load, 2),
            'DG_Mode': r.dg_mode,
            'BESS_Assisted': r.bess_assisted
        })
    return pd.DataFrame(data)


def style_row(row):
    """Apply row styling based on state."""
    if row['Deficit_MW'] > 0:
        return ['background-color: #FFB6C1'] * len(row)  # Pink - deficit
    if row['DG_MW'] > 0:
        return ['background-color: #FFFACD'] * len(row)  # Yellow - DG running
    if row['BESS_State'] == 'Discharging':
        return ['background-color: #E6E6FA'] * len(row)  # Lavender - discharging
    if row['BESS_State'] == 'Charging':
        return ['background-color: #90EE90'] * len(row)  # Green - charging
    return [''] * len(row)


def create_dispatch_graph(df: pd.DataFrame, title: str):
    """Create dispatch visualization graph."""
    hours = df['Hour'].tolist()
    solar_mw = df['Solar_MW'].tolist()
    dg_mw = df['DG_MW'].tolist()
    bess_mw = df['BESS_Power_MW'].tolist()
    soc_pct = df['SoC_%'].tolist()
    bess_energy = df['BESS_Energy_MWh'].tolist()
    delivery = [df['Load_MW'].iloc[0] if d == 0 else 0 for d in df['Deficit_MW'].tolist()]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Solar (orange fill)
    fig.add_trace(
        go.Scatter(x=hours, y=solar_mw, name='Solar', fill='tozeroy',
                   line=dict(color='#FFA500', width=2),
                   hovertemplate='Hour %{x}<br>Solar: %{y:.1f} MW<extra></extra>'),
        secondary_y=False
    )

    # DG (red) - only if used
    if any(d > 0 for d in dg_mw):
        fig.add_trace(
            go.Scatter(x=hours, y=dg_mw, name='DG Output', fill='tozeroy',
                       line=dict(color='#DC143C', width=2, shape='hv'),
                       fillcolor='rgba(220,20,60,0.3)',
                       hovertemplate='Hour %{x}<br>DG: %{y:.1f} MW<extra></extra>'),
            secondary_y=False
        )

    # BESS Power (blue)
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
        go.Scatter(x=hours, y=bess_energy, name='BESS Energy (MWh)',
                   line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
                   hovertemplate='Hour %{x}<br>Energy: %{y:.1f} MWh<extra></extra>'),
        secondary_y=True
    )

    # Delivery (purple)
    fig.add_trace(
        go.Scatter(x=hours, y=delivery, name='Delivery',
                   line=dict(color='purple', width=3, shape='hv'),
                   hovertemplate='Hour %{x}<br>Delivery: %{y:.0f} MW<extra></extra>'),
        secondary_y=False
    )

    # Reference lines
    load_val = df['Load_MW'].iloc[0]
    fig.add_hline(y=load_val, line_dash="dash", line_color="gray",
                  annotation_text=f"Load {load_val:.0f} MW", secondary_y=False)
    fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)
    fig.add_vline(x=24, line_dash="dash", line_color="black", line_width=1,
                  annotation_text="Day 2", annotation_position="top")

    fig.update_layout(
        title=title,
        xaxis_title="Hour (0-23: Day 1 | 24-47: Day 2)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        xaxis=dict(showgrid=True, dtick=6)
    )
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="SOC (%) / Energy (MWh)", secondary_y=True, range=[0, 100])

    return fig


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(page_title="Hourly Examples", page_icon="📊", layout="wide")

st.title("📊 Hourly Operation Examples")
st.markdown("""
This page demonstrates **dispatch templates** from the new algorithm specification.
Configure parameters and see real-time simulation results.
""")
st.markdown("---")


# =============================================================================
# SIDEBAR CONFIGURATION
# =============================================================================

with st.sidebar:
    st.header("Configuration")

    st.subheader("BESS Parameters")
    bess_capacity = st.number_input("Capacity (MWh)", 10, 500, 100, 10)
    bess_power = st.number_input("Power (MW)", 10, 500, 100, 10)
    bess_efficiency = st.slider("Round-trip Efficiency (%)", 70, 95, 85)
    bess_min_soc = st.slider("Min SoC (%)", 0, 30, 10)
    bess_max_soc = st.slider("Max SoC (%)", 70, 100, 90)
    bess_initial_soc = st.slider("Initial SoC (%)", bess_min_soc, bess_max_soc, 50)

    st.subheader("DG Parameters")
    dg_capacity = st.number_input("DG Capacity (MW)", 0, 100, 27, 1)
    dg_charges_bess = st.checkbox("DG can charge BESS", value=True)

    st.subheader("Load")
    load_mw = st.number_input("Constant Load (MW)", 1, 100, 25, 1)

    st.subheader("SoC Thresholds")
    dg_soc_on = st.slider("DG ON threshold (%)", 10, 50, 30)
    dg_soc_off = st.slider("DG OFF threshold (%)", 50, 95, 80)

    st.subheader("Time Windows")
    night_start = st.number_input("Night starts (hour)", 0, 23, 18)
    night_end = st.number_input("Night ends (hour)", 0, 23, 6)
    blackout_start = st.number_input("Blackout starts (hour)", 0, 23, 22)
    blackout_end = st.number_input("Blackout ends (hour)", 0, 23, 6)


# =============================================================================
# BUILD SIMULATION PARAMETERS
# =============================================================================

# Load solar data
full_solar = load_solar_profile()
solar_48h = get_june_15_16_data(full_solar)
load_48h = create_constant_load(load_mw, 48)

# Build params object
params = SimulationParams(
    load_profile=load_48h,
    solar_profile=solar_48h,
    bess_capacity=bess_capacity,
    bess_charge_power=bess_power,
    bess_discharge_power=bess_power,
    bess_efficiency=bess_efficiency,
    bess_min_soc=bess_min_soc,
    bess_max_soc=bess_max_soc,
    bess_initial_soc=bess_initial_soc,
    dg_enabled=True,
    dg_capacity=dg_capacity,
    dg_charges_bess=dg_charges_bess,
    dg_soc_on_threshold=dg_soc_on,
    dg_soc_off_threshold=dg_soc_off,
    night_start_hour=night_start,
    night_end_hour=night_end,
    day_start_hour=night_end,  # Day starts when night ends
    day_end_hour=night_start,  # Day ends when night starts
    blackout_start_hour=blackout_start,
    blackout_end_hour=blackout_end
)


# =============================================================================
# MAIN TABS
# =============================================================================

main_tab1, main_tab2, main_tab3 = st.tabs([
    "⚡ Dispatch & Charging Logic",
    "📋 Simulation Results",
    "📈 Template Comparison"
])


# =============================================================================
# TAB 1: DISPATCH & CHARGING LOGIC
# =============================================================================

with main_tab1:
    st.markdown("## Dispatch & Charging Rules")

    st.info(f"""
    **Current Configuration:** {bess_capacity} MWh BESS | {dg_capacity} MW DG | {load_mw} MW Load |
    SOC: {bess_min_soc}%-{bess_max_soc}% | Efficiency: {bess_efficiency}%
    """)

    template_tabs = st.tabs([TEMPLATES[i]['name'] for i in range(7)])

    for idx in range(7):
        with template_tabs[idx]:
            t = TEMPLATES[idx]
            st.markdown(f"### {t['name']}")
            st.caption(t['subtitle'])
            st.success(t['description'])
            st.markdown(f"**Merit Order:** `{t['merit_order']}`")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Dispatch Rules")
                for rule in t['dispatch_rules']:
                    st.markdown(f"- {rule}")
            with col2:
                st.markdown("#### Charging Rules")
                for rule in t['charging_rules']:
                    st.markdown(f"- {rule}")

            st.warning(f"**Constraints:** {t['constraints']}")


# =============================================================================
# TAB 2: SIMULATION RESULTS
# =============================================================================

with main_tab2:
    st.markdown("## Simulation Results (48-Hour)")

    st.info(f"""
    **Configuration:** {bess_capacity} MWh BESS | {dg_capacity} MW DG | {load_mw} MW Load |
    SOC: {bess_min_soc}%-{bess_max_soc}%

    **Color Legend:** 🟥 Pink = Deficit | 🟨 Yellow = DG Running | 🟪 Lavender = BESS Discharging | 🟩 Green = BESS Charging
    """)

    sim_tabs = st.tabs([TEMPLATES[i]['name'] for i in range(7)])

    display_cols = ['Hour', 'Day', 'Solar_MW', 'DG_MW', 'BESS_Power_MW',
                    'BESS_Energy_MWh', 'SoC_%', 'BESS_State', 'Load_MW',
                    'Deficit_MW', 'Solar_to_Load', 'BESS_to_Load', 'DG_to_Load']

    for idx in range(7):
        with sim_tabs[idx]:
            t = TEMPLATES[idx]
            st.markdown(f"### {t['name']}")

            # Adjust params for template
            template_params = SimulationParams(
                load_profile=load_48h,
                solar_profile=solar_48h,
                bess_capacity=bess_capacity,
                bess_charge_power=bess_power,
                bess_discharge_power=bess_power,
                bess_efficiency=bess_efficiency,
                bess_min_soc=bess_min_soc,
                bess_max_soc=bess_max_soc,
                bess_initial_soc=bess_initial_soc,
                dg_enabled=t['dg_enabled'] and dg_capacity > 0,
                dg_capacity=dg_capacity if t['dg_enabled'] else 0,
                dg_charges_bess=dg_charges_bess,
                dg_soc_on_threshold=dg_soc_on,
                dg_soc_off_threshold=dg_soc_off,
                night_start_hour=night_start,
                night_end_hour=night_end,
                day_start_hour=night_end,
                day_end_hour=night_start,
                blackout_start_hour=blackout_start,
                blackout_end_hour=blackout_end
            )

            # Run simulation
            results = run_simulation(template_params, idx, num_hours=48)
            metrics = calculate_metrics(results, template_params)
            df = results_to_dataframe(results)

            # Metrics display
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Delivery Hours", f"{metrics.hours_full_delivery}/48")
            col2.metric("Total Deficit", f"{metrics.total_unserved:.1f} MWh")
            col3.metric("DG Runtime", f"{metrics.dg_runtime_hours} hours")
            col4.metric("Green Hours", f"{metrics.hours_green_delivery}")

            # Data table
            st.dataframe(
                df[display_cols].style.apply(style_row, axis=1),
                width='stretch',
                height=500
            )

            # Graph
            st.markdown("#### Dispatch Graph")
            fig = create_dispatch_graph(df, f"{t['name']} — June 15-16 Dispatch")
            st.plotly_chart(fig, width='stretch')


# =============================================================================
# TAB 3: TEMPLATE COMPARISON
# =============================================================================

with main_tab3:
    st.markdown("## Template Comparison")

    st.info("""
    Compare all dispatch strategies side-by-side.
    Lower deficit = better reliability. Lower DG = greener operation.
    """)

    # Run all simulations
    comparison_data = []
    for idx in range(7):
        t = TEMPLATES[idx]
        template_params = SimulationParams(
            load_profile=load_48h,
            solar_profile=solar_48h,
            bess_capacity=bess_capacity,
            bess_charge_power=bess_power,
            bess_discharge_power=bess_power,
            bess_efficiency=bess_efficiency,
            bess_min_soc=bess_min_soc,
            bess_max_soc=bess_max_soc,
            bess_initial_soc=bess_initial_soc,
            dg_enabled=t['dg_enabled'] and dg_capacity > 0,
            dg_capacity=dg_capacity if t['dg_enabled'] else 0,
            dg_charges_bess=dg_charges_bess,
            dg_soc_on_threshold=dg_soc_on,
            dg_soc_off_threshold=dg_soc_off,
            night_start_hour=night_start,
            night_end_hour=night_end,
            day_start_hour=night_end,
            day_end_hour=night_start,
            blackout_start_hour=blackout_start,
            blackout_end_hour=blackout_end
        )

        results = run_simulation(template_params, idx, num_hours=48)
        metrics = calculate_metrics(results, template_params)

        comparison_data.append({
            'Template': t['name'],
            'Delivery_Hours': metrics.hours_full_delivery,
            'Green_Hours': metrics.hours_green_delivery,
            'Deficit_MWh': round(metrics.total_unserved, 1),
            'DG_Hours': metrics.dg_runtime_hours,
            'DG_MWh': round(metrics.total_dg_to_load, 1),
            'Curtailed_MWh': round(metrics.total_solar_curtailed, 1),
            'BESS_Cycles': round(metrics.bess_equivalent_cycles, 2)
        })

    summary_df = pd.DataFrame(comparison_data)

    # Summary table
    st.markdown("### Performance Metrics")
    st.dataframe(summary_df, width='stretch')

    # Charts
    st.markdown("### Visual Comparison")
    col1, col2 = st.columns(2)

    with col1:
        fig_delivery = go.Figure(data=[
            go.Bar(
                x=summary_df['Template'],
                y=summary_df['Delivery_Hours'],
                marker_color=['#90EE90' if d == 48 else '#FFB6C1' for d in summary_df['Delivery_Hours']],
                text=summary_df['Delivery_Hours'],
                textposition='auto'
            )
        ])
        fig_delivery.update_layout(
            title='Delivery Hours by Template (out of 48)',
            xaxis_title='Template',
            yaxis_title='Hours',
            height=400
        )
        st.plotly_chart(fig_delivery, width='stretch')

    with col2:
        fig_dg = go.Figure(data=[
            go.Bar(
                x=summary_df['Template'],
                y=summary_df['DG_MWh'],
                marker_color='#FFFACD',
                text=summary_df['DG_MWh'],
                textposition='auto'
            )
        ])
        fig_dg.update_layout(
            title='DG Energy by Template (MWh)',
            xaxis_title='Template',
            yaxis_title='MWh',
            height=400
        )
        st.plotly_chart(fig_dg, width='stretch')

    # Insights
    st.markdown("### Key Insights")

    best_delivery = summary_df.loc[summary_df['Delivery_Hours'].idxmax()]
    greenest = summary_df.loc[summary_df['Green_Hours'].idxmax()]
    least_dg = summary_df[summary_df['DG_Hours'] > 0]['DG_Hours'].min() if summary_df['DG_Hours'].sum() > 0 else None

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"**Best Delivery:** {best_delivery['Template']} ({best_delivery['Delivery_Hours']}/48 hours)")
    with col2:
        st.success(f"**Greenest:** {greenest['Template']} ({greenest['Green_Hours']} green hours)")
    with col3:
        if least_dg:
            min_dg_row = summary_df[summary_df['DG_Hours'] == least_dg].iloc[0]
            st.info(f"**Least DG (with backup):** {min_dg_row['Template']} ({min_dg_row['DG_Hours']} hours)")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption(f"""
**Data Source:** June 15-16 solar data from Inputs/Solar Profile.csv

**Configuration:** {bess_capacity} MWh BESS | {bess_power} MW Power | {dg_capacity} MW DG | {load_mw} MW Load |
SOC: {bess_min_soc}%-{bess_max_soc}% | Efficiency: {bess_efficiency}%

**Algorithm:** Based on ALGORITHM_SPECIFICATION.md v1.0
""")
