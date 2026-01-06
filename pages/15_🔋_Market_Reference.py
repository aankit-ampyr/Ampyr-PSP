"""
Market Reference: Utility-Scale BESS Configurations

Reference page showing available battery energy storage systems
in the European market for utility-scale solar+BESS projects.

Data updated: January 2026
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Market Reference",
    page_icon="🔋",
    layout="wide"
)

# =============================================================================
# DATA: MANUFACTURER SPECIFICATIONS
# =============================================================================

MANUFACTURERS_DATA = [
    {
        "Manufacturer": "CATL",
        "Product": "TENER Stack",
        "Capacity_MWh": 9.0,
        "Container": "Stacked 2×4.5 MWh",
        "Chemistry": "LFP",
        "Cycle_Life": 10000,
        "RTE_pct": 90,
        "Weight_tonnes": 36,
        "Warranty_years": 20,
        "Notes": "World's largest mass-produced; 45% better volume utilization",
        "Available_Europe": True
    },
    {
        "Manufacturer": "CATL",
        "Product": "EnerC+",
        "Capacity_MWh": 6.25,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 10000,
        "RTE_pct": 90,
        "Weight_tonnes": 32,
        "Warranty_years": 15,
        "Notes": "Previous generation; widely deployed globally",
        "Available_Europe": True
    },
    {
        "Manufacturer": "BYD",
        "Product": "HaoHan (14.5 MWh)",
        "Capacity_MWh": 14.5,
        "Container": "Custom DC Block",
        "Chemistry": "LFP (Blade)",
        "Cycle_Life": 10000,
        "RTE_pct": 92,
        "Weight_tonnes": None,
        "Warranty_years": 15,
        "Notes": "World's largest single unit; 2,710 Ah blade cells; Sep 2025",
        "Available_Europe": True
    },
    {
        "Manufacturer": "BYD",
        "Product": "HaoHan (10 MWh)",
        "Capacity_MWh": 10.0,
        "Container": "20-ft",
        "Chemistry": "LFP (Blade)",
        "Cycle_Life": 10000,
        "RTE_pct": 92,
        "Weight_tonnes": 38,
        "Warranty_years": 15,
        "Notes": "233 kWh/m³ density (50% above industry avg)",
        "Available_Europe": True
    },
    {
        "Manufacturer": "BYD",
        "Product": "MC Cube-T",
        "Capacity_MWh": 6.43,
        "Container": "20-ft",
        "Chemistry": "LFP (Blade)",
        "Cycle_Life": 8000,
        "RTE_pct": 90,
        "Weight_tonnes": 34,
        "Warranty_years": 15,
        "Notes": "Widely available; proven technology",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Tesla",
        "Product": "Megapack 3",
        "Capacity_MWh": 5.0,
        "Container": "Custom",
        "Chemistry": "LFP",
        "Cycle_Life": 7000,
        "RTE_pct": 92,
        "Weight_tonnes": 39,
        "Warranty_years": 15,
        "Notes": "15-year warranty; proven track record",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Tesla",
        "Product": "Megablock (4× MP3)",
        "Capacity_MWh": 20.0,
        "Container": "Integrated Block",
        "Chemistry": "LFP",
        "Cycle_Life": 7000,
        "RTE_pct": 92,
        "Weight_tonnes": 156,
        "Warranty_years": 15,
        "Notes": "Coming late 2026; 248 MWh/acre density",
        "Available_Europe": False
    },
    {
        "Manufacturer": "Sungrow",
        "Product": "PowerTitan 3.0",
        "Capacity_MWh": 6.9,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 12500,
        "RTE_pct": 93.6,
        "Weight_tonnes": 35,
        "Warranty_years": 15,
        "Notes": "661 Ah cells; highest RTE; SiC inverter",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Sungrow",
        "Product": "PowerTitan 2.0",
        "Capacity_MWh": 5.0,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 10000,
        "RTE_pct": 91,
        "Weight_tonnes": 33,
        "Warranty_years": 15,
        "Notes": "Previous generation; widely deployed",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Fluence",
        "Product": "Gridstack Pro",
        "Capacity_MWh": 5.3,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 10000,
        "RTE_pct": 90,
        "Weight_tonnes": 34,
        "Warranty_years": 15,
        "Notes": "#1 European integrator; CATL/AESC cells",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Fluence",
        "Product": "SmartStack",
        "Capacity_MWh": 7.5,
        "Container": "Custom",
        "Chemistry": "LFP",
        "Cycle_Life": 10000,
        "RTE_pct": 90,
        "Weight_tonnes": 40,
        "Warranty_years": 15,
        "Notes": "European market leader in integration",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Envision",
        "Product": "Grid-Scale ESS",
        "Capacity_MWh": 8.0,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 8000,
        "RTE_pct": 89,
        "Weight_tonnes": 36,
        "Warranty_years": 15,
        "Notes": "Growing European presence",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Wärtsilä",
        "Product": "Quantum3",
        "Capacity_MWh": 5.0,
        "Container": "AC Block",
        "Chemistry": "LFP",
        "Cycle_Life": 8000,
        "RTE_pct": 88,
        "Weight_tonnes": 35,
        "Warranty_years": 15,
        "Notes": "European manufacturer; integrated solution",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Samsung SDI",
        "Product": "E3 Battery",
        "Capacity_MWh": 3.9,
        "Container": "20-ft",
        "Chemistry": "NMC/LFP",
        "Cycle_Life": 6000,
        "RTE_pct": 90,
        "Weight_tonnes": 28,
        "Warranty_years": 12,
        "Notes": "Hungary plant; transitioning to LFP",
        "Available_Europe": True
    },
    {
        "Manufacturer": "LG Energy Solution",
        "Product": "Grid ESS",
        "Capacity_MWh": 4.2,
        "Container": "20-ft",
        "Chemistry": "NMC",
        "Cycle_Life": 6000,
        "RTE_pct": 91,
        "Weight_tonnes": 26,
        "Warranty_years": 12,
        "Notes": "Poland 70 GWh plant; NMC specialist",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Northvolt",
        "Product": "Voltpack",
        "Capacity_MWh": 2.5,
        "Container": "Modular",
        "Chemistry": "NMC",
        "Cycle_Life": 5000,
        "RTE_pct": 90,
        "Weight_tonnes": 18,
        "Warranty_years": 10,
        "Notes": "European manufacturer; Sweden",
        "Available_Europe": True
    },
    {
        "Manufacturer": "Saft (TotalEnergies)",
        "Product": "Intensium Max+",
        "Capacity_MWh": 4.0,
        "Container": "20-ft",
        "Chemistry": "LFP",
        "Cycle_Life": 7000,
        "RTE_pct": 88,
        "Weight_tonnes": 30,
        "Warranty_years": 15,
        "Notes": "French manufacturer; industrial focus",
        "Available_Europe": True
    },
]

# Container size options
CONTAINER_SIZES = [
    {"Container_Type": "20-ft Standard", "Capacity_Range": "1-2 MWh", "Power_Range": "0.25-0.5 MW", "Use_Case": "Entry-level, pilot projects"},
    {"Container_Type": "20-ft Mid-Range", "Capacity_Range": "2-4 MWh", "Power_Range": "0.5-1 MW", "Use_Case": "C&I, frequency regulation"},
    {"Container_Type": "20-ft High-Density", "Capacity_Range": "4-5 MWh", "Power_Range": "1-1.25 MW", "Use_Case": "Utility-scale, grid services"},
    {"Container_Type": "20-ft Latest Gen", "Capacity_Range": "5-7 MWh", "Power_Range": "1.25-1.75 MW", "Use_Case": "Large utility projects"},
    {"Container_Type": "20-ft Cutting-Edge", "Capacity_Range": "9-10 MWh", "Power_Range": "2.25-2.5 MW", "Use_Case": "Mega-scale solar+storage"},
    {"Container_Type": "40-ft Integrated", "Capacity_Range": "3-4 MWh", "Power_Range": "1-1.5 MW", "Use_Case": "Battery + inverter + transformer"},
    {"Container_Type": "40-ft High-Density", "Capacity_Range": "5-6.5 MWh", "Power_Range": "1.5-2 MW", "Use_Case": "Large utility projects"},
    {"Container_Type": "Custom Block", "Capacity_Range": "10-20 MWh", "Power_Range": "2.5-5 MW", "Use_Case": "Grid-scale infrastructure"},
]

# Duration classes
DURATION_CLASSES = [
    {"Duration": "1-hour", "Ratio": "1:1", "Application": "Frequency regulation, ancillary services", "Typical_Revenue": "High $/MWh"},
    {"Duration": "2-hour", "Ratio": "1:2", "Application": "Peak shaving, grid balancing", "Typical_Revenue": "Medium-High $/MWh"},
    {"Duration": "4-hour", "Ratio": "1:4", "Application": "Solar shifting, capacity firming", "Typical_Revenue": "Medium $/MWh"},
    {"Duration": "6-hour", "Ratio": "1:6", "Application": "Extended evening coverage", "Typical_Revenue": "Medium-Low $/MWh"},
    {"Duration": "8-hour", "Ratio": "1:8", "Application": "Overnight storage, long duration", "Typical_Revenue": "Low $/MWh"},
]

# Project scales
PROJECT_SCALES = [
    {"Scale": "Small", "Battery_MWh": "10-50", "Solar_MW": "10-25", "Use_Case": "C&I, small utility", "Example": "Rooftop solar + storage"},
    {"Scale": "Medium", "Battery_MWh": "50-200", "Solar_MW": "25-100", "Use_Case": "Utility-scale", "Example": "Solar farm + BESS"},
    {"Scale": "Large", "Battery_MWh": "200-500", "Solar_MW": "100-250", "Use_Case": "Grid-scale", "Example": "Major solar park"},
    {"Scale": "Mega", "Battery_MWh": "500+", "Solar_MW": "250+", "Use_Case": "Major infrastructure", "Example": "National grid storage"},
]

# Pricing data
PRICING_DATA = [
    {"Component": "LFP Cells (China domestic)", "Price": "$40/kWh", "Year": "2025", "Trend": "Declining"},
    {"Component": "Complete BESS (Global avg)", "Price": "$125/kWh", "Year": "2025", "Trend": "Declining"},
    {"Component": "Complete BESS (Europe)", "Price": "$150-200/kWh", "Year": "2025", "Trend": "Stable"},
    {"Component": "Installation & BOS", "Price": "15-20% of equipment", "Year": "2025", "Trend": "Stable"},
    {"Component": "O&M (Annual)", "Price": "$5-10/kWh/year", "Year": "2025", "Trend": "Stable"},
]

# =============================================================================
# PAGE CONTENT
# =============================================================================

st.title("🔋 Market Reference: Utility-Scale BESS")
st.markdown("Reference data for battery energy storage systems available in the European market for utility-scale solar+BESS projects.")
st.markdown("---")

# Market overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("2024 EU Installations", "21.9 GWh", "+15%")
with col2:
    st.metric("2025 Projected", "29.7 GWh", "+36%")
with col3:
    st.metric("Utility-Scale Share", "55%", "+15pp")
with col4:
    st.metric("LFP Cell Price", "$40/kWh", "-25%")

st.markdown("---")

# =============================================================================
# TABS
# =============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Manufacturer Products",
    "📏 Container Sizes",
    "⏱️ Duration Classes",
    "📊 Project Scales",
    "💰 Pricing"
])

# -----------------------------------------------------------------------------
# TAB 1: Manufacturer Products
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Utility-Scale BESS Products (2025)")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        manufacturers = ["All"] + sorted(list(set(d["Manufacturer"] for d in MANUFACTURERS_DATA)))
        selected_mfr = st.selectbox("Filter by Manufacturer", manufacturers)
    with col2:
        chemistries = ["All"] + sorted(list(set(d["Chemistry"] for d in MANUFACTURERS_DATA)))
        selected_chem = st.selectbox("Filter by Chemistry", chemistries)
    with col3:
        min_capacity = st.slider("Minimum Capacity (MWh)", 0.0, 15.0, 0.0, 0.5)

    # Filter data
    filtered_data = MANUFACTURERS_DATA.copy()
    if selected_mfr != "All":
        filtered_data = [d for d in filtered_data if d["Manufacturer"] == selected_mfr]
    if selected_chem != "All":
        filtered_data = [d for d in filtered_data if d["Chemistry"] == selected_chem]
    filtered_data = [d for d in filtered_data if d["Capacity_MWh"] >= min_capacity]

    # Convert to DataFrame
    df = pd.DataFrame(filtered_data)

    # Display table
    st.dataframe(
        df[[
            "Manufacturer", "Product", "Capacity_MWh", "Container",
            "Chemistry", "Cycle_Life", "RTE_pct", "Warranty_years", "Notes"
        ]].rename(columns={
            "Capacity_MWh": "Capacity (MWh)",
            "Cycle_Life": "Cycles",
            "RTE_pct": "RTE (%)",
            "Warranty_years": "Warranty (yrs)"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Comparison chart
    st.subheader("Capacity Comparison")
    fig = px.bar(
        df.sort_values("Capacity_MWh", ascending=True),
        x="Capacity_MWh",
        y="Product",
        color="Manufacturer",
        orientation="h",
        title="Battery Capacity by Product",
        labels={"Capacity_MWh": "Capacity (MWh)", "Product": ""}
    )
    fig.update_layout(height=500, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # Cycle life vs RTE scatter
    col1, col2 = st.columns(2)
    with col1:
        fig2 = px.scatter(
            df,
            x="Cycle_Life",
            y="RTE_pct",
            size="Capacity_MWh",
            color="Manufacturer",
            hover_name="Product",
            title="Cycle Life vs Round-Trip Efficiency",
            labels={"Cycle_Life": "Cycle Life", "RTE_pct": "RTE (%)"}
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # Chemistry distribution pie chart
        chem_counts = df["Chemistry"].value_counts()
        fig3 = px.pie(
            values=chem_counts.values,
            names=chem_counts.index,
            title="Chemistry Distribution"
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: Container Sizes
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Standard Container Configurations")

    df_containers = pd.DataFrame(CONTAINER_SIZES)
    st.dataframe(
        df_containers.rename(columns={
            "Container_Type": "Container Type",
            "Capacity_Range": "Capacity Range",
            "Power_Range": "Power Range",
            "Use_Case": "Use Case"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("Container Selection Guide")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **20-ft ISO Container (Standard)**
        - Dimensions: 6.06m (L) × 2.44m (W) × 2.9m (H)
        - Max Weight: 36 tonnes (road transport)
        - Most common for utility-scale
        - Easy transport and installation
        """)

    with col2:
        st.markdown("""
        **40-ft ISO Container**
        - Dimensions: 12.2m (L) × 2.44m (W) × 2.9m (H)
        - Max Weight: 40+ tonnes (special permits)
        - Higher capacity per unit
        - Integrated systems (battery + PCS)
        """)

    st.info("""
    **Transport Considerations:**
    - Units ≤36 tonnes: Standard road transport (99% of markets)
    - Units >36 tonnes: Special permits required
    - Stackable designs (like CATL TENER) maximize site density
    """)

# -----------------------------------------------------------------------------
# TAB 3: Duration Classes
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Battery Duration Classes")

    df_duration = pd.DataFrame(DURATION_CLASSES)
    st.dataframe(
        df_duration.rename(columns={
            "Typical_Revenue": "Revenue Profile"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("Duration Selection for Solar+BESS")

    # Visual guide
    fig = go.Figure()

    durations = [1, 2, 4, 6, 8]
    solar_shift = [20, 60, 95, 80, 60]
    freq_reg = [95, 70, 30, 10, 5]
    peak_shave = [50, 90, 85, 70, 50]

    fig.add_trace(go.Scatter(
        x=durations, y=solar_shift, mode='lines+markers',
        name='Solar Shifting', line=dict(width=3)
    ))
    fig.add_trace(go.Scatter(
        x=durations, y=freq_reg, mode='lines+markers',
        name='Frequency Regulation', line=dict(width=3)
    ))
    fig.add_trace(go.Scatter(
        x=durations, y=peak_shave, mode='lines+markers',
        name='Peak Shaving', line=dict(width=3)
    ))

    fig.update_layout(
        title="Application Suitability by Duration",
        xaxis_title="Duration (hours)",
        yaxis_title="Suitability Score (%)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    st.success("""
    **Recommendation for Solar+BESS:**
    - **4-hour duration** is the most common and versatile choice
    - Captures majority of solar shifting value
    - Good balance of cost and performance
    - Matches typical evening peak demand window
    """)

# -----------------------------------------------------------------------------
# TAB 4: Project Scales
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Typical Project Scales")

    df_scales = pd.DataFrame(PROJECT_SCALES)
    st.dataframe(
        df_scales.rename(columns={
            "Battery_MWh": "Battery (MWh)",
            "Solar_MW": "Solar (MW)",
            "Use_Case": "Use Case"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("Sizing Examples")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Medium Project (Typical)**
        - Solar: 50 MW AC
        - Battery: 100 MWh / 25 MW
        - Duration: 4 hours
        - Containers: ~20 × 5 MWh units
        - Land: ~2-3 hectares (BESS)
        """)

    with col2:
        st.markdown("""
        **Large Project**
        - Solar: 150 MW AC
        - Battery: 300 MWh / 75 MW
        - Duration: 4 hours
        - Containers: ~50-60 × 5 MWh units
        - Land: ~5-7 hectares (BESS)
        """)

    # Cost estimation
    st.markdown("---")
    st.subheader("Indicative Project Costs (2025)")

    sizes = [50, 100, 200, 300, 500]
    costs_low = [s * 150000 / 1e6 for s in sizes]
    costs_high = [s * 200000 / 1e6 for s in sizes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sizes, y=costs_low,
        mode='lines+markers',
        name='Low Estimate ($150/kWh)',
        fill=None
    ))
    fig.add_trace(go.Scatter(
        x=sizes, y=costs_high,
        mode='lines+markers',
        name='High Estimate ($200/kWh)',
        fill='tonexty'
    ))
    fig.update_layout(
        title="Estimated BESS CAPEX by Capacity",
        xaxis_title="Battery Capacity (MWh)",
        yaxis_title="Total Cost (€ Million)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: Pricing
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("Market Pricing (2025)")

    df_pricing = pd.DataFrame(PRICING_DATA)
    st.dataframe(df_pricing, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Cost Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        # CAPEX breakdown pie
        capex_components = ["Battery Cells", "Power Electronics", "BMS & Controls", "Enclosure & HVAC", "Installation"]
        capex_values = [50, 20, 10, 12, 8]

        fig = px.pie(
            values=capex_values,
            names=capex_components,
            title="Typical CAPEX Breakdown",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Price trend
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        prices = [350, 300, 280, 200, 150, 125]

        fig = px.line(
            x=years, y=prices,
            title="BESS Price Trend ($/kWh)",
            labels={"x": "Year", "y": "Price ($/kWh)"}
        )
        fig.update_traces(mode='lines+markers', line=dict(width=3))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Cost Estimation Calculator")

    col1, col2, col3 = st.columns(3)
    with col1:
        calc_capacity = st.number_input("Battery Capacity (MWh)", 10, 1000, 100, 10)
    with col2:
        calc_price = st.number_input("Price ($/kWh)", 100, 300, 175, 5)
    with col3:
        calc_install = st.number_input("Installation (%)", 10, 30, 15, 1)

    equipment_cost = calc_capacity * calc_price * 1000
    install_cost = equipment_cost * (calc_install / 100)
    total_cost = equipment_cost + install_cost

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Equipment Cost", f"${equipment_cost/1e6:,.1f}M")
    with col2:
        st.metric("Installation Cost", f"${install_cost/1e6:,.1f}M")
    with col3:
        st.metric("Total CAPEX", f"${total_cost/1e6:,.1f}M")

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
### Data Sources
- [SolarPower Europe - European Market Outlook 2025-2029](https://www.solarpowereurope.org/insights/outlooks/european-market-outlook-for-battery-storage-2025-2029/detail)
- [ESS News - European Battery Storage Market](https://www.ess-news.com)
- [PV Magazine - CATL, BYD, Sungrow Product Announcements](https://www.pv-magazine.com)
- [Modo Energy - BESS Market Research](https://modoenergy.com)
- [Ember - Battery Storage Economics](https://ember-energy.org)

*Last updated: January 2026*
""")

st.caption("This reference data is for informational purposes. Contact manufacturers directly for current specifications and pricing.")
