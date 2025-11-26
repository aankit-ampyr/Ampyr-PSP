"""
Calculation Logic Page
Detailed explanation of BESS sizing calculations and algorithms
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import (
    TARGET_DELIVERY_MW, MIN_SOC, MAX_SOC,
    ONE_WAY_EFFICIENCY, ROUND_TRIP_EFFICIENCY,
    C_RATE_CHARGE, C_RATE_DISCHARGE,
    DEGRADATION_PER_CYCLE, MARGINAL_IMPROVEMENT_THRESHOLD,
    MARGINAL_INCREMENT_MWH
)

# Page config
st.set_page_config(page_title="Calculation Logic", page_icon="🧮", layout="wide")

st.title("🧮 Calculation Logic")
st.markdown("---")

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 Operation Logic",
    "🔄 Cycle Calculations",
    "⚡ Efficiency Model",
    "📊 Optimization",
    "🔥 DG Simulation",
    "💻 Code Examples"
])

with tab1:
    st.markdown("## Sample Daily Power Flow")
    st.info("This illustrative chart shows how solar and battery power flow through a typical day to meet the 25 MW delivery target.")

    # Sample data for a typical sunny day
    # Scenario: Battery starts partially charged (30 MWh usable)
    hours = list(range(24))
    solar_mw = [0, 0, 0, 0, 0, 5, 15, 30, 45, 55, 60, 65, 67, 65, 60, 50, 35, 20, 10, 5, 0, 0, 0, 0]

    # BESS logic (negative = charging, positive = discharging):
    # Decision: If solar + battery_available >= 25 → DELIVER, else → CHARGE
    #
    # Hour 0: 0+30=30>=25 → Deliver, discharge 25 → BESS=+25 (battery: 30→5)
    # Hour 1-4: 0+5<25 → Can't deliver, charge with solar(0) → BESS=0
    # Hour 5: 5+5=10<25 → Can't deliver, charge with solar → BESS=-5 (battery: 5→10)
    # Hour 6: 15+10=25>=25 → Deliver, discharge 10 → BESS=+10 (battery: 10→0)
    # Hour 7: 30+0=30>=25 → Deliver (solar enough), charge excess → BESS=-5
    # Hours 8-16: Solar>=25 → Deliver, charge excess → BESS=-(solar-25)
    # Hours 17-21: Solar<25 → Deliver, discharge gap → BESS=+(25-solar)
    # Hours 22-23: 0+0<25 → Can't deliver, no solar → BESS=0
    bess_mw = [25, 0, 0, 0, 0, -5, 10, -5, -20, -30, -35, -40, -42, -40, -35, -25, -10, 5, 15, 20, 25, 25, 0, 0]

    # Combined: Solar + BESS (net power delivered)
    combined_mw = [s + b for s, b in zip(solar_mw, bess_mw)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=solar_mw, name='Solar',
                             fill='tozeroy', line=dict(color='#FFA500', width=2)))
    fig.add_trace(go.Scatter(x=hours, y=bess_mw, name='BESS',
                             line=dict(color='#1f77b4', width=2)))
    fig.add_trace(go.Scatter(x=hours, y=combined_mw, name='Solar + BESS',
                             line=dict(color='red', width=3, shape='hv')))
    fig.add_hline(y=25, line_dash="dash", line_color="green",
                  annotation_text="Target 25 MW")
    fig.add_hline(y=0, line_color="gray", line_width=1)

    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Power (MW)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=350,
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            griddash='dot',
            dtick=1  # Show grid line every hour
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption("**Orange area**: Solar | **Blue line**: BESS (negative=charging, positive=discharging) | **Red line**: Solar + BESS (net power)")
    st.markdown("---")

    st.markdown("## Operational Decision Logic")

    st.markdown("### Binary Delivery System")
    st.info(f"""
    The system operates on a binary delivery constraint:
    - Deliver **exactly {TARGET_DELIVERY_MW} MW** if possible
    - Otherwise deliver **0 MW**
    - No partial delivery allowed
    """)

    # Decision Flow Diagram
    st.markdown("### Hourly Decision Flow Diagram")
    st.graphviz_chart('''
        digraph HourlyDecision {
            rankdir=TB;
            node [shape=box, style="rounded,filled", fillcolor="#E8F4FD", fontname="Arial"];
            edge [fontname="Arial", fontsize=10];

            start [label="Start Hour", shape=ellipse, fillcolor="#90EE90"];
            calc_avail [label="Calculate Available Power\\nsolar + battery_power"];
            check_avail [label="Available ≥ 25 MW?", shape=diamond, fillcolor="#FFE4B5"];
            deliver_yes [label="DELIVER 25 MW", fillcolor="#90EE90"];
            deliver_no [label="DELIVER 0 MW", fillcolor="#FFB6C1"];
            check_solar [label="Solar ≥ 25 MW?", shape=diamond, fillcolor="#FFE4B5"];
            charge_excess [label="CHARGE battery\\nwith (Solar - 25)", fillcolor="#87CEEB"];
            discharge [label="DISCHARGE battery\\nfor (25 - Solar)", fillcolor="#DDA0DD"];
            charge_all [label="CHARGE battery\\nwith all Solar", fillcolor="#87CEEB"];
            update [label="Update SOC & Cycles"];
            end_hour [label="End Hour", shape=ellipse, fillcolor="#D3D3D3"];

            start -> calc_avail;
            calc_avail -> check_avail;
            check_avail -> deliver_yes [label="Yes"];
            check_avail -> deliver_no [label="No"];
            deliver_yes -> check_solar;
            check_solar -> charge_excess [label="Yes\\n(Excess Solar)"];
            check_solar -> discharge [label="No\\n(Need Battery)"];
            deliver_no -> charge_all;
            charge_excess -> update;
            discharge -> update;
            charge_all -> update;
            update -> end_hour;
        }
    ''')

    st.markdown("### Hour-by-Hour Decision Tree")

    st.warning("""
    ⚠️ **Critical**: Battery availability must consider BOTH energy capacity AND C-rate power limits.
    Energy (MWh) ≠ Power (MW). A 100 MWh battery with 1.0 C-rate can only deliver 100 MW,
    even if it has 100 MWh of energy available.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Step 1: Check Availability")
        st.code("""
# Battery power limited by BOTH energy and C-rate
battery_power_mw = min(
    battery_energy_mwh,  # Energy for 1 hour
    capacity_mwh * c_rate  # Power limit
)
available_mw = solar_mw + battery_power_mw
can_deliver = available_mw >= 25 MW
        """, language='python')

    with col2:
        st.markdown("#### Step 2: Make Decision")
        st.code("""
if can_deliver:
    deliver = 25 MW
else:
    deliver = 0 MW
        """, language='python')

    st.markdown("### Operational Scenarios")

    scenarios_data = {
        'Scenario': [
            'Excess Solar',
            'Partial Solar',
            'No Solar (Night)',
            'Insufficient Total'
        ],
        'Solar (MW)': [40, 15, 0, 10],
        'Battery Available (MW)': [50, 50, 50, 10],
        'Delivery (MW)': [25, 25, 25, 0],
        'Battery Action': ['Charge 15 MW', 'Discharge 10 MW', 'Discharge 25 MW', 'Charge 10 MW']
    }

    scenarios_df = pd.DataFrame(scenarios_data)
    st.table(scenarios_df)

    st.markdown("### Charging Rules")
    st.markdown("""
    **Battery charges ONLY from solar energy:**
    1. When delivering and solar > 25 MW: Charge with excess (solar - 25)
    2. When NOT delivering: Charge with all available solar
    3. No grid charging allowed
    """)

with tab2:
    st.markdown("## Cycle Calculation Method")

    st.markdown("### State Transition Method")
    st.info("""
    Cycles are counted based on state transitions:
    - Each transition between charging and discharging = +0.5 cycles
    - Transitions to/from IDLE may or may not increment cycles
    """)

    # State Transition Diagram
    st.markdown("### State Machine Diagram")
    st.graphviz_chart('''
        digraph StateMachine {
            rankdir=LR;
            node [shape=circle, style=filled, fontname="Arial", fontsize=12, width=1.2];
            edge [fontname="Arial", fontsize=10];

            IDLE [fillcolor="#E8E8E8", label="IDLE"];
            CHARGING [fillcolor="#87CEEB", label="CHARGING"];
            DISCHARGING [fillcolor="#DDA0DD", label="DISCHARGING"];

            IDLE -> CHARGING [label="+0.5 cycles", color="blue"];
            IDLE -> DISCHARGING [label="+0.5 cycles", color="purple"];
            CHARGING -> IDLE [label="0 cycles", style="dashed"];
            CHARGING -> DISCHARGING [label="+0.5 cycles", color="red", penwidth=2];
            DISCHARGING -> IDLE [label="0 cycles", style="dashed"];
            DISCHARGING -> CHARGING [label="+0.5 cycles", color="red", penwidth=2];
            CHARGING -> CHARGING [label="0 cycles", style="dashed"];
            DISCHARGING -> DISCHARGING [label="0 cycles", style="dashed"];
        }
    ''')

    st.caption("**Red arrows**: Direct charge↔discharge transitions add 0.5 cycles each")

    st.markdown("### State Transition Table")

    transitions_data = {
        'Previous State': [
            'IDLE', 'IDLE', 'IDLE',
            'CHARGING', 'CHARGING', 'CHARGING',
            'DISCHARGING', 'DISCHARGING', 'DISCHARGING'
        ],
        'New State': [
            'IDLE', 'CHARGING', 'DISCHARGING',
            'IDLE', 'CHARGING', 'DISCHARGING',
            'IDLE', 'CHARGING', 'DISCHARGING'
        ],
        'Cycle Increment': [
            '0', '+0.5', '+0.5',
            '0', '0', '+0.5',
            '0', '+0.5', '0'
        ]
    }

    transitions_df = pd.DataFrame(transitions_data)
    st.table(transitions_df)

    st.markdown("### Example Cycle Calculation")

    example_data = {
        'Hour': [1, 2, 3, 4, 5, 6, 7, 8],
        'State': ['IDLE', 'CHARGING', 'CHARGING', 'DISCHARGING', 'DISCHARGING', 'CHARGING', 'IDLE', 'DISCHARGING'],
        'Transition': [
            '- → IDLE',
            'IDLE → CHARGING',
            'CHARGING → CHARGING',
            'CHARGING → DISCHARGING',
            'DISCHARGING → DISCHARGING',
            'DISCHARGING → CHARGING',
            'CHARGING → IDLE',
            'IDLE → DISCHARGING'
        ],
        'Cycles Added': [0, 0.5, 0, 0.5, 0, 0.5, 0, 0.5],
        'Total Cycles': [0, 0.5, 0.5, 1.0, 1.0, 1.5, 1.5, 2.0]
    }

    example_df = pd.DataFrame(example_data)
    st.table(example_df)

    st.markdown("### Cycle Metrics")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### Total Cycles")
        st.code("Sum of all cycle increments", language='text')

    with col2:
        st.markdown("##### Average Daily Cycles")
        st.code("Total Cycles / 365 days", language='text')

    with col3:
        st.markdown("##### Max Daily Cycles")
        st.code("Maximum cycles in any 24-hour period", language='text')

with tab3:
    st.markdown("## Efficiency Model")

    st.markdown("### Round-Trip Efficiency")
    st.info(f"""
    **RTE = {ROUND_TRIP_EFFICIENCY:.0%}**

    This means:
    - One-way efficiency = √{ROUND_TRIP_EFFICIENCY} = {ONE_WAY_EFFICIENCY:.1%}
    - Applied to both charging and discharging
    """)

    st.markdown("### Efficiency Calculations")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Charging")
        st.code(f"""
# Energy from solar
solar_available = 10 MWh

# Energy stored in battery
energy_stored = solar_available × {ONE_WAY_EFFICIENCY:.3f}
energy_stored = 10 × {ONE_WAY_EFFICIENCY:.3f} = {10 * ONE_WAY_EFFICIENCY:.2f} MWh
        """, language='python')

    with col2:
        st.markdown("#### Discharging")
        st.code(f"""
# Energy needed from battery
energy_needed = 10 MWh

# Energy delivered
energy_delivered = battery_energy × {ONE_WAY_EFFICIENCY:.3f}
# Or: battery needs {10 / ONE_WAY_EFFICIENCY:.2f} MWh to deliver 10 MWh
        """, language='python')

    st.markdown("### SOC Limits")
    st.markdown(f"""
    **Operating Range: {MIN_SOC:.0%} - {MAX_SOC:.0%}**

    For a 100 MWh battery:
    - Minimum usable: {MIN_SOC * 100:.0f} MWh
    - Maximum usable: {MAX_SOC * 100:.0f} MWh
    - Available capacity: {(MAX_SOC - MIN_SOC) * 100:.0f} MWh
    """)

    st.markdown("### C-Rate Limits")
    st.markdown(f"""
    **Charge C-Rate: {C_RATE_CHARGE}**
    **Discharge C-Rate: {C_RATE_DISCHARGE}**

    For a 100 MWh battery:
    - Max charge rate: {100 * C_RATE_CHARGE:.0f} MW
    - Max discharge rate: {100 * C_RATE_DISCHARGE:.0f} MW
    """)

with tab4:
    st.markdown("## Optimization Algorithm")

    st.markdown("### Marginal Analysis Method")
    st.info(f"""
    **Optimization Threshold: {MARGINAL_IMPROVEMENT_THRESHOLD} hours per {MARGINAL_INCREMENT_MWH} MWh**

    The algorithm finds the battery size where adding more capacity provides
    diminishing returns below this threshold.
    """)

    # Optimization Algorithm Flow Diagram
    st.markdown("### Optimization Algorithm Flow")
    st.graphviz_chart('''
        digraph Optimization {
            rankdir=TB;
            node [shape=box, style="rounded,filled", fillcolor="#E8F4FD", fontname="Arial"];
            edge [fontname="Arial", fontsize=10];

            start [label="Start Optimization", shape=ellipse, fillcolor="#90EE90"];
            init [label="Initialize\\nsize = MIN_SIZE\\nbest_hours = 0"];
            simulate [label="Run Year Simulation\\nfor current size"];
            calc_hours [label="Calculate\\ndelivery_hours"];
            calc_marginal [label="Calculate Marginal Gain\\n(hours[i] - hours[i-1]) / step"];
            check_threshold [label="Marginal Gain\\n< Threshold?", shape=diamond, fillcolor="#FFE4B5"];
            found [label="OPTIMAL SIZE FOUND\\nPrevious size is optimal", fillcolor="#90EE90"];
            increment [label="Increment size\\nsize += STEP"];
            check_max [label="size > MAX?", shape=diamond, fillcolor="#FFE4B5"];
            max_reached [label="MAX SIZE reached\\nUse largest tested", fillcolor="#FFB6C1"];
            end_opt [label="Return Optimal Size", shape=ellipse, fillcolor="#D3D3D3"];

            start -> init;
            init -> simulate;
            simulate -> calc_hours;
            calc_hours -> calc_marginal;
            calc_marginal -> check_threshold;
            check_threshold -> found [label="Yes"];
            check_threshold -> increment [label="No"];
            increment -> check_max;
            check_max -> simulate [label="No"];
            check_max -> max_reached [label="Yes"];
            found -> end_opt;
            max_reached -> end_opt;
        }
    ''')

    st.markdown("### Example Optimization")

    opt_data = {
        'Battery Size (MWh)': [50, 60, 70, 80, 90, 100],
        'Delivery Hours': [3000, 3500, 3900, 4200, 4400, 4500],
        'Marginal Hours': ['-', 500, 400, 300, 200, 100],
        'Hours per 10 MWh': ['-', 500, 400, 300, 200, 100],
        'Decision': ['', '', '', 'Optimal ✓', 'Below threshold', 'Below threshold']
    }

    opt_df = pd.DataFrame(opt_data)
    st.table(opt_df)

    st.markdown("### Algorithm Steps")
    st.code("""
1. Test battery sizes from 10 to 500 MWh (step: 5 MWh)
2. For each size:
   - Run 8,760 hour simulation
   - Calculate delivery hours
   - Track cycles and degradation

3. Calculate marginal improvement:
   marginal = (hours[i] - hours[i-1]) / (size[i] - size[i-1]) * 10

4. Find optimal size:
   optimal = first size where marginal < 300 hours per 10 MWh
    """, language='text')

    st.markdown("### Solar Wastage Calculation")
    st.info("""
    **Wastage Formula: Wasted Solar / Total Solar Available**

    The wastage percentage represents solar energy that could not be used:
    - **Numerator**: Solar wasted (MWh)
    - **Denominator**: Total solar available = Solar charged + Solar wasted

    **Important**: Battery discharge energy is NOT included in the denominator
    as it's not solar energy.
    """)

    st.code("""
# Correct wastage calculation
total_solar_available = solar_charged_mwh + solar_wasted_mwh
wastage_percent = (solar_wasted_mwh / total_solar_available) × 100

# Example:
# - 800 MWh solar charged to battery
# - 200 MWh solar wasted
# - Wastage = 200 / (800 + 200) = 20%
    """, language='python')

    st.markdown("### Degradation Model")
    st.markdown(f"""
    **Degradation per cycle: {DEGRADATION_PER_CYCLE:.4%}**

    Example for 100 cycles:
    - Capacity loss = {100 * DEGRADATION_PER_CYCLE:.2f}%
    - Remaining capacity = {100 - 100 * DEGRADATION_PER_CYCLE:.2f}%
    """)

with tab5:
    st.markdown("## Solar + BESS + DG Hybrid System")

    st.info("""
    The DG (Diesel Generator) simulation adds a backup generator to the Solar+BESS system.
    The DG operates based on battery SOC thresholds using hysteresis control to prevent
    frequent start/stop cycling.
    """)

    # Sample DG Dispatch Graph
    st.markdown("### Sample DG Dispatch Through a Day")
    st.caption("This illustrative chart shows how Solar, DG, and BESS interact with SOC-triggered DG control.")

    # Sample data for a day with DG activation
    # Scenario: Battery starts at 30% SOC, DG ON threshold=20%, OFF threshold=80%
    # Load = 25 MW, DG capacity = 25 MW
    hours = list(range(24))

    # Solar profile (typical sunny day)
    solar_mw = [0, 0, 0, 0, 0, 5, 15, 30, 45, 55, 60, 65, 67, 65, 60, 50, 35, 20, 10, 5, 0, 0, 0, 0]

    # SOC profile (starts at 30%, drops to 20% at hour 3, DG charges to 80% by hour 8)
    # After DG off, solar maintains/charges, then depletes in evening
    soc_pct = [30, 25, 22, 20, 35, 50, 65, 80, 85, 90, 92, 93, 93, 92, 90, 85, 75, 60, 45, 35, 28, 22, 20, 25]

    # DG state (ON when SOC hits 20%, OFF when SOC hits 80%)
    # Hours 3-7: DG ON (SOC dropped to 20% at hour 3, reaches 80% at hour 7)
    # Hours 22-23: DG ON again (SOC dropped to 20% at hour 22)
    dg_output_mw = [0, 0, 0, 25, 25, 25, 25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 25]

    # BESS (negative=charging, positive=discharging)
    # When DG ON: excess DG+Solar charges battery
    # When DG OFF: battery discharges if solar < load, charges if solar > load
    bess_mw = [25, 25, 25, -25, -30, -30, -40, -55, -20, -30, -35, -40, -42, -40, -35, -25, -10, 5, 15, 20, 25, 25, -25, -25]

    # Combined output to load: Solar + DG + BESS discharge (positive only)
    # This represents total power delivered to the load
    combined_mw = [s + d + max(0, b) for s, d, b in zip(solar_mw, dg_output_mw, bess_mw)]

    # Create figure with secondary y-axis for SOC
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Scatter(x=hours, y=solar_mw, name='Solar', fill='tozeroy',
                   line=dict(color='#FFA500', width=2)),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=hours, y=dg_output_mw, name='DG Output', fill='tozeroy',
                   line=dict(color='#DC143C', width=2), fillcolor='rgba(220,20,60,0.3)'),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=hours, y=bess_mw, name='BESS',
                   line=dict(color='#1f77b4', width=2)),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=hours, y=soc_pct, name='SOC %',
                   line=dict(color='#2E8B57', width=2, dash='dot')),
        secondary_y=True
    )
    fig.add_trace(
        go.Scatter(x=hours, y=combined_mw, name='Total to Load',
                   line=dict(color='purple', width=3, shape='hv')),
        secondary_y=False
    )

    # Add threshold lines
    fig.add_hline(y=25, line_dash="dash", line_color="gray",
                  annotation_text="Load 25 MW", secondary_y=False)
    fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)
    fig.add_hline(y=20, line_dash="dot", line_color="red",
                  annotation_text="DG ON (20%)", secondary_y=True)
    fig.add_hline(y=80, line_dash="dot", line_color="green",
                  annotation_text="DG OFF (80%)", secondary_y=True)

    fig.update_layout(
        xaxis_title="Hour of Day",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        xaxis=dict(showgrid=True, gridcolor='lightgray', gridwidth=1, griddash='dot', dtick=1)
    )
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="SOC (%)", secondary_y=True, range=[0, 100])

    st.plotly_chart(fig, use_container_width=True)

    st.caption("""
    **Orange**: Solar | **Red**: DG Output | **Blue**: BESS (negative=charging) | **Purple**: Total to Load | **Green dotted**: SOC %

    **Scenario**: SOC drops to 20% → DG starts → DG+Solar charge battery → SOC reaches 80% → DG stops
    """)

    st.markdown("---")

    st.markdown("### Merit Order Dispatch")
    st.markdown("""
    **For Load Serving (Priority Order):**
    1. **Solar** - Always serves load first (free, clean energy)
    2. **DG** - Serves remaining load when running (before BESS)
    3. **BESS** - Discharges only if Solar + DG can't meet load

    **For BESS Charging (Priority Order):**
    1. **Excess Solar** - After load is met
    2. **Excess DG** - When DG has spare capacity
    """)

    # Merit Order Flow Diagram
    st.markdown("### Load Serving Flow Diagram")
    st.graphviz_chart('''
        digraph MeritOrder {
            rankdir=TB;
            node [shape=box, style="rounded,filled", fillcolor="#E8F4FD", fontname="Arial"];
            edge [fontname="Arial", fontsize=10];

            start [label="Start Hour", shape=ellipse, fillcolor="#90EE90"];
            load [label="Load Demand\\n(e.g., 25 MW)"];
            solar_first [label="1. Solar to Load\\nmin(solar, load)"];
            calc_remaining [label="Calculate Remaining Load\\nremaining = load - solar_to_load"];
            check_dg [label="DG Running?", shape=diamond, fillcolor="#FFE4B5"];
            dg_serve [label="2. DG to Load\\nmin(dg_output, remaining)"];
            update_remaining [label="Update Remaining\\nremaining -= dg_to_load"];
            check_bess [label="Remaining > 0?", shape=diamond, fillcolor="#FFE4B5"];
            bess_serve [label="3. BESS Discharge\\nmin(available, remaining)"];
            final_check [label="Load Met?", shape=diamond, fillcolor="#FFE4B5"];
            delivered [label="DELIVERY: Yes", fillcolor="#90EE90"];
            not_delivered [label="DELIVERY: No", fillcolor="#FFB6C1"];
            end_hour [label="End Hour", shape=ellipse, fillcolor="#D3D3D3"];

            start -> load;
            load -> solar_first;
            solar_first -> calc_remaining;
            calc_remaining -> check_dg;
            check_dg -> dg_serve [label="Yes"];
            check_dg -> check_bess [label="No"];
            dg_serve -> update_remaining;
            update_remaining -> check_bess;
            check_bess -> bess_serve [label="Yes"];
            check_bess -> delivered [label="No\\n(Load Met)"];
            bess_serve -> final_check;
            final_check -> delivered [label="Yes"];
            final_check -> not_delivered [label="No"];
            delivered -> end_hour;
            not_delivered -> end_hour;
        }
    ''')

    st.markdown("---")
    st.markdown("### DG Hysteresis Control")

    st.warning("""
    **Hysteresis Control** prevents frequent DG start/stop cycles by using two SOC thresholds:
    - **ON Threshold** (e.g., 20%): Start DG when SOC drops to this level
    - **OFF Threshold** (e.g., 80%): Stop DG when SOC rises to this level
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### DG State Logic")
        st.code("""
# DG starts when SOC is low
if dg_state == 'OFF':
    if battery_soc <= SOC_ON_THRESHOLD:
        dg_state = 'ON'
        total_starts += 1

# DG stops when SOC is high
elif dg_state == 'ON':
    if battery_soc >= SOC_OFF_THRESHOLD:
        dg_state = 'OFF'
        """, language='python')

    with col2:
        st.markdown("#### Hysteresis Band")
        st.info("""
        **Example with 20%/80% thresholds:**

        - SOC drops to 20% → DG turns ON
        - DG runs at full capacity
        - SOC rises (from DG + Solar charging)
        - SOC reaches 80% → DG turns OFF
        - System runs on Solar + BESS
        - Cycle repeats when SOC drops again
        """)

    # DG State Machine Diagram
    st.markdown("### DG State Machine")
    st.graphviz_chart('''
        digraph DGStateMachine {
            rankdir=LR;
            node [shape=circle, style=filled, fontname="Arial", fontsize=12, width=1.5];
            edge [fontname="Arial", fontsize=10];

            OFF [fillcolor="#90EE90", label="DG OFF"];
            ON [fillcolor="#FFB6C1", label="DG ON"];

            OFF -> ON [label="SOC ≤ 20%\\n(Start DG)", color="red", penwidth=2];
            ON -> OFF [label="SOC ≥ 80%\\n(Stop DG)", color="green", penwidth=2];
            OFF -> OFF [label="SOC > 20%", style="dashed"];
            ON -> ON [label="SOC < 80%", style="dashed"];
        }
    ''')

    st.markdown("---")
    st.markdown("### BESS Charging Priority")

    st.markdown("""
    When charging the BESS, excess energy is used in this order:

    | Priority | Source | Condition |
    |----------|--------|-----------|
    | 1st | Excess Solar | Solar > Load demand |
    | 2nd | Excess DG | DG output > Load remaining after solar |
    """)

    st.markdown("#### Charging Flow")
    st.graphviz_chart('''
        digraph ChargingFlow {
            rankdir=TB;
            node [shape=box, style="rounded,filled", fillcolor="#E8F4FD", fontname="Arial"];
            edge [fontname="Arial", fontsize=10];

            start [label="After Load Dispatch", shape=ellipse, fillcolor="#90EE90"];
            calc_excess_solar [label="Calculate Excess Solar\\nexcess_solar = solar - solar_to_load"];
            check_solar [label="Excess Solar > 0?", shape=diamond, fillcolor="#FFE4B5"];
            charge_solar [label="1. Charge from Solar\\nbattery.charge(excess_solar)", fillcolor="#87CEEB"];
            check_dg_excess [label="DG has Excess?", shape=diamond, fillcolor="#FFE4B5"];
            charge_dg [label="2. Charge from DG\\nbattery.charge(excess_dg)", fillcolor="#DDA0DD"];
            end_charge [label="Charging Complete", shape=ellipse, fillcolor="#D3D3D3"];

            start -> calc_excess_solar;
            calc_excess_solar -> check_solar;
            check_solar -> charge_solar [label="Yes"];
            check_solar -> check_dg_excess [label="No"];
            charge_solar -> check_dg_excess;
            check_dg_excess -> charge_dg [label="Yes"];
            check_dg_excess -> end_charge [label="No"];
            charge_dg -> end_charge;
        }
    ''')

    st.markdown("---")
    st.markdown("### DG Metrics Tracked")

    metrics_data = {
        'Metric': [
            'DG Runtime (hours)',
            'DG Starts',
            'DG Energy Generated (MWh)',
            'DG to Load (MWh)',
            'DG to BESS (MWh)',
            'DG Capacity Factor (%)'
        ],
        'Description': [
            'Total hours DG was running',
            'Number of times DG was started',
            'Total energy produced by DG',
            'DG energy used directly for load',
            'DG energy used to charge battery',
            'DG utilization = Runtime / 8760 hours'
        ]
    }
    metrics_df = pd.DataFrame(metrics_data)
    st.table(metrics_df)

    st.markdown("### Complete DG Dispatch Example")
    st.code("""
# Hour-by-hour simulation with DG
for hour in range(8760):
    solar_mw = solar_profile[hour]

    # Step 1: Update DG state based on current SOC (BEFORE dispatch)
    dg.update_state(battery.soc)

    remaining_load = LOAD_MW  # e.g., 25 MW

    # Step 2: Merit Order Dispatch for LOAD

    # Priority 1: Solar to Load
    solar_to_load = min(solar_mw, remaining_load)
    remaining_load -= solar_to_load
    excess_solar = solar_mw - solar_to_load

    # Priority 2: DG to Load (if DG is ON)
    dg_to_load = 0
    if dg.state == 'ON':
        dg_output = dg.run()  # Full capacity when ON
        dg_to_load = min(dg_output, remaining_load)
        remaining_load -= dg_to_load
        excess_dg = dg_output - dg_to_load

    # Priority 3: BESS discharge (only if needed)
    if remaining_load > 0:
        bess_to_load = battery.discharge(remaining_load)
        remaining_load -= bess_to_load

    # Step 3: Charge BESS (Solar first, then DG)
    if excess_solar > 0:
        battery.charge(excess_solar)

    if dg.state == 'ON' and excess_dg > 0:
        battery.charge(excess_dg)

    # Track delivery
    if remaining_load <= 0.001:
        hours_delivered += 1
    """, language='python')

with tab6:
    st.markdown("## Implementation Code Examples")

    st.markdown("### Core Simulation Loop")
    st.code("""
def simulate_hour(solar_mw, battery, target_mw=25):
    # Check if we can deliver (consider BOTH energy and power limits)
    battery_energy_mwh = battery.get_available_energy()
    battery_power_mw = min(
        battery_energy_mwh,  # Energy available for 1 hour
        battery.capacity * battery.c_rate_discharge  # C-rate power limit
    )
    can_deliver = (solar_mw + battery_power_mw) >= target_mw

    if can_deliver:
        # Deliver target power
        delivered = target_mw

        if solar_mw >= target_mw:
            # Excess solar - charge battery
            excess = solar_mw - target_mw
            battery.charge(excess)
            new_state = 'CHARGING' if excess > 0 else 'IDLE'
        else:
            # Need battery support
            deficit = target_mw - solar_mw
            battery.discharge(deficit)
            new_state = 'DISCHARGING'
    else:
        # Cannot deliver - charge battery
        delivered = 0
        battery.charge(solar_mw)
        new_state = 'CHARGING' if solar_mw > 0 else 'IDLE'

    # Update cycles based on state transition
    battery.update_cycles(new_state)

    return delivered, new_state
    """, language='python')

    st.markdown("### Battery Class Structure")
    st.code("""
class BatterySystem:
    def __init__(self, capacity_mwh):
        self.capacity = capacity_mwh
        self.soc = 0.5  # Start at 50%
        self.state = 'IDLE'
        self.total_cycles = 0

    def charge(self, energy_mwh):
        # Apply efficiency
        energy_to_battery = energy_mwh * 0.933

        # Limit by headroom and C-rate
        max_charge = min(
            (0.95 - self.soc) * self.capacity,
            self.capacity * 1.0  # C-rate
        )

        actual = min(energy_to_battery, max_charge)
        self.soc += actual / self.capacity

        return actual / 0.933  # Return AC consumed

    def discharge(self, energy_mwh):
        # Energy from battery (before efficiency)
        energy_from_battery = energy_mwh / 0.933

        # Limit by available and C-rate
        max_discharge = min(
            (self.soc - 0.05) * self.capacity,
            self.capacity * 1.0  # C-rate
        )

        actual = min(energy_from_battery, max_discharge)
        self.soc -= actual / self.capacity

        return actual * 0.933  # Return AC delivered
    """, language='python')

    st.markdown("### State Transition Cycle Counting")
    st.code("""
def update_cycles(self, new_state):
    # Count specific transitions as half cycles
    if self.state != new_state:
        if ((self.state in ['IDLE', 'CHARGING'] and
             new_state == 'DISCHARGING') or
            (self.state in ['IDLE', 'DISCHARGING'] and
             new_state == 'CHARGING')):
            self.total_cycles += 0.5

    self.state = new_state
    """, language='python')

    st.markdown("### Complete Working Example")
    with st.expander("View Full Implementation"):
        st.code("""
import numpy as np

# Configuration
TARGET_MW = 25
BATTERY_SIZE = 100  # MWh
RTE = 0.87
EFFICIENCY = np.sqrt(RTE)

# Sample solar profile (24 hours)
solar_profile = [0, 0, 0, 0, 0, 5, 15, 30, 45, 55, 60, 65,
                 67, 65, 60, 50, 35, 20, 10, 5, 0, 0, 0, 0]

# Initialize battery
soc = 0.5  # 50% initial charge
state = 'IDLE'
cycles = 0

# Results tracking
delivered_hours = 0
total_delivered = 0

# Hour-by-hour simulation
for hour, solar in enumerate(solar_profile):
    # Battery power limited by BOTH energy and C-rate
    battery_energy = (soc - 0.05) * BATTERY_SIZE
    battery_power = min(battery_energy, BATTERY_SIZE * 1.0)  # 1.0 C-rate

    # Can we deliver?
    if solar + battery_power >= TARGET_MW:
        # Yes - deliver
        delivered_hours += 1
        total_delivered += TARGET_MW

        if solar >= TARGET_MW:
            # Charge with excess
            excess = solar - TARGET_MW
            charge = min(excess * EFFICIENCY,
                        (0.95 - soc) * BATTERY_SIZE)
            soc += charge / BATTERY_SIZE
            new_state = 'CHARGING' if charge > 0 else 'IDLE'
        else:
            # Discharge to support
            needed = (TARGET_MW - solar) / EFFICIENCY
            discharge = min(needed, battery_energy, BATTERY_SIZE * 1.0)
            soc -= discharge / BATTERY_SIZE
            new_state = 'DISCHARGING'
    else:
        # No - charge only
        charge = min(solar * EFFICIENCY,
                    (0.95 - soc) * BATTERY_SIZE)
        soc += charge / BATTERY_SIZE
        new_state = 'CHARGING' if charge > 0 else 'IDLE'

    # Update cycles
    if state != new_state:
        if ((state in ['IDLE', 'CHARGING'] and
             new_state == 'DISCHARGING') or
            (state in ['IDLE', 'DISCHARGING'] and
             new_state == 'CHARGING')):
            cycles += 0.5

    state = new_state

    print(f"Hour {hour:2d}: Solar={solar:3.0f}, "
          f"SOC={soc:.1%}, State={state:11s}, "
          f"Delivered={25 if delivered_hours else 0}")

print(f"\\nResults: {delivered_hours} hours delivered, "
      f"{cycles} cycles")
        """, language='python')