"""
Calculation Logic Page
Detailed explanation of BESS sizing calculations and algorithms
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Operation Logic",
    "🔄 Cycle Calculations",
    "⚡ Efficiency Model",
    "📊 Optimization",
    "💻 Code Examples"
])

with tab1:
    st.markdown("## Operational Decision Logic")

    st.markdown("### Binary Delivery System")
    st.info(f"""
    The system operates on a binary delivery constraint:
    - Deliver **exactly {TARGET_DELIVERY_MW} MW** if possible
    - Otherwise deliver **0 MW**
    - No partial delivery allowed
    """)

    st.markdown("### Hour-by-Hour Decision Tree")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Step 1: Check Availability")
        st.code("""
available_mw = solar_mw + battery_available_mw
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

    st.markdown("### Degradation Model")
    st.markdown(f"""
    **Degradation per cycle: {DEGRADATION_PER_CYCLE:.4%}**

    Example for 100 cycles:
    - Capacity loss = {100 * DEGRADATION_PER_CYCLE:.2f}%
    - Remaining capacity = {100 - 100 * DEGRADATION_PER_CYCLE:.2f}%
    """)

with tab5:
    st.markdown("## Implementation Code Examples")

    st.markdown("### Core Simulation Loop")
    st.code("""
def simulate_hour(solar_mw, battery, target_mw=25):
    # Check if we can deliver
    battery_available = battery.get_available_energy()
    can_deliver = (solar_mw + battery_available) >= target_mw

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
    battery_available = (soc - 0.05) * BATTERY_SIZE

    # Can we deliver?
    if solar + battery_available >= TARGET_MW:
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
            discharge = min(needed, battery_available)
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