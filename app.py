"""
BESS Sizing Tool
A streamlit application for optimizing Battery Energy Storage System sizing
for solar PV installations with binary delivery constraints.
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="BESS Sizing Tool",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main page content
st.title("🔋 BESS Sizing Tool")
st.markdown("---")

st.markdown("""
## Welcome to the BESS Sizing Optimization Tool

This tool helps optimize Battery Energy Storage System (BESS) sizing for solar PV installations
with binary delivery constraints (must deliver target power or nothing).

### Key Features:
- **Binary Delivery System**: Delivers either full target power (25 MW) or nothing
- **Solar Integration**: Battery charges only from solar energy
- **Cycle Tracking**: Monitors battery cycles using state transition method
- **Optimization**: Finds optimal battery size based on diminishing returns

### How to Use:
1. Navigate to **Simulation** page to run battery sizing analysis
2. View **Calculation Logic** page to understand the algorithms

### System Parameters:
- Target Delivery: 25 MW
- Solar Capacity: 67 MW
- Battery SOC Limits: 5% - 95%
- Round-trip Efficiency: 87%
- C-rates: 1.0 (charge and discharge)

Use the sidebar to navigate between pages.
""")

# Sidebar information
st.sidebar.markdown("### Navigation")
st.sidebar.info("Use the pages above to access different features")
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**Version**: 1.0.0
**Purpose**: BESS Sizing Optimization
**Method**: Hour-by-hour simulation over full year
""")