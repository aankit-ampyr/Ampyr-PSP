"""
Step 4: Results

Display and analyze simulation results:
- Recommended configuration hero
- Quick filters
- Sortable table
- Color-coded metrics
- Export options
"""

import streamlit as st
import pandas as pd

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    set_current_step, get_step_status, can_navigate_to_step,
    set_results_filter, toggle_results_filter
)
from src.template_inference import get_template_info


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Results",
    page_icon="📊",
    layout="wide"
)

# Initialize wizard state
init_wizard_state()
set_current_step(4)

# Check if can access this step
if not can_navigate_to_step(4):
    st.warning("Please complete Steps 1-3 first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/8_🚀_Step1_Setup.py")
    st.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Analysis", get_step_status(5)),
    ]

    cols = st.columns(5)
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == 'completed':
                st.markdown(f"✅ **Step {num}**: {label}")
            elif status == 'current':
                st.markdown(f"🔵 **Step {num}**: {label}")
            elif status == 'pending':
                st.markdown(f"⚪ Step {num}: {label}")
            else:
                st.markdown(f"🔒 Step {num}: {label}")


def get_delivery_color(value: float) -> str:
    """Get color for delivery percentage."""
    if value >= 99:
        return "#2ecc71"  # Green
    elif value >= 95:
        return "#f1c40f"  # Yellow
    else:
        return "#e74c3c"  # Red


def get_wastage_color(value: float) -> str:
    """Get color for wastage percentage."""
    if value <= 2:
        return "#2ecc71"  # Green
    elif value <= 5:
        return "#f1c40f"  # Yellow
    else:
        return "#e74c3c"  # Red


def style_results_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply styling to results dataframe."""

    def color_delivery(val):
        color = get_delivery_color(val)
        return f'background-color: {color}20; color: {color}'

    def color_wastage(val):
        color = get_wastage_color(val)
        return f'background-color: {color}20; color: {color}'

    styled = df.style.applymap(color_delivery, subset=['delivery_pct'])
    styled = styled.applymap(color_wastage, subset=['wastage_pct'])

    return styled


def filter_results(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply filters to results dataframe."""
    filtered = df.copy()

    if filters.get('full_delivery', False):
        filtered = filtered[filtered['delivery_pct'] >= 99.9]

    if filters.get('zero_dg', False):
        filtered = filtered[filtered['dg_hours'] == 0]

    if filters.get('low_wastage', False):
        filtered = filtered[filtered['wastage_pct'] <= 2]

    if filters.get('hide_dominated', False):
        # Simple dominated detection: remove if worse on all metrics
        # than another config with same or smaller BESS size
        to_keep = []
        for i, row in filtered.iterrows():
            dominated = False
            for j, other in filtered.iterrows():
                if i != j:
                    if (other['bess_mwh'] <= row['bess_mwh'] and
                        other['delivery_pct'] >= row['delivery_pct'] and
                        other['wastage_pct'] <= row['wastage_pct'] and
                        other['dg_hours'] <= row['dg_hours']):
                        # Check if strictly better on at least one metric
                        if (other['delivery_pct'] > row['delivery_pct'] or
                            other['wastage_pct'] < row['wastage_pct'] or
                            other['dg_hours'] < row['dg_hours'] or
                            other['bess_mwh'] < row['bess_mwh']):
                            dominated = True
                            break
            if not dominated:
                to_keep.append(i)
        filtered = filtered.loc[to_keep]

    return filtered


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("📊 Results")
st.markdown("### Step 4 of 4: Analysis & Comparison")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']
results_state = state['results']

# Check for results
results_df = results_state.get('simulation_results')

if results_df is None or len(results_df) == 0:
    st.warning("No simulation results found. Please run the simulation first.")
    if st.button("Go to Step 3"):
        st.switch_page("pages/10_📐_Step3_Sizing.py")
    st.stop()


# =============================================================================
# RECOMMENDED CONFIGURATION HERO
# =============================================================================

ranked_recommendations = results_state.get('ranked_recommendations')

if ranked_recommendations:
    # Show goal summary and filtering info
    goal_summary = ranked_recommendations.get('goal_summary', '')
    filtered_count = ranked_recommendations.get('filtered_count', 0)
    excluded_count = ranked_recommendations.get('excluded_count', 0)
    total_tested = ranked_recommendations.get('total_configs_tested', len(results_df))

    st.markdown("---")

    # Goal info bar
    if goal_summary:
        st.info(f"🎯 **Optimization Goal:** {goal_summary}")

    if excluded_count > 0:
        st.caption(f"Filtered: {filtered_count} of {total_tested} configs meet criteria ({excluded_count} excluded)")

    # Check if we have a recommended config
    recommended = ranked_recommendations.get('recommended')

    if recommended is None:
        # No configs meet the criteria
        st.error(f"""
        **No configurations meet your criteria.**

        {ranked_recommendations.get('goal_summary', '')}

        **Suggestions:**
        - Lower the delivery target percentage
        - Increase max wastage or DG hours constraints
        - Expand the BESS capacity range in Step 3
        """)
        st.markdown("---")

    else:
        alternatives = ranked_recommendations.get('alternatives', [])

        # Hero section
        st.markdown("## 🎯 RECOMMENDED CONFIGURATION")

        # Main recommendation
        rec_col1, rec_col2 = st.columns([2, 3])

        with rec_col1:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1a5f7a 0%, #2ecc71 100%);
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                color: white;
            ">
                <h1 style="margin: 0; font-size: 3rem;">{recommended['power_mw']:.0f} MW × {recommended['duration_hrs']}-hr</h1>
                <h2 style="margin: 10px 0; font-size: 2rem;">{recommended['bess_mwh']:.0f} MWh</h2>
                <p style="margin: 10px 0; font-size: 1rem; opacity: 0.9;">
                    {recommended.get('reasoning', 'Highest delivery hours with optimal marginal gain')}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with rec_col2:
            # Key metrics grid
            m_cols = st.columns(4)

            with m_cols[0]:
                delivery_hours = recommended.get('delivery_hours', 0)
                delivery_pct = recommended.get('delivery_pct', 0)
                st.metric("Delivery Hours", f"{delivery_hours:,}", f"{delivery_pct:.1f}%")

            with m_cols[1]:
                cycles = recommended.get('total_cycles', 0)
                st.metric("Total Cycles", f"{cycles:,.0f}")

            with m_cols[2]:
                wastage = recommended.get('wastage_pct', 0)
                st.metric("Solar Wastage", f"{wastage:.1f}%")

            with m_cols[3]:
                dg_hours = recommended.get('dg_hours', 0)
                if setup['dg_enabled']:
                    st.metric("DG Runtime", f"{dg_hours:,} hrs")
                else:
                    green_hours = recommended.get('green_hours', delivery_hours)
                    st.metric("Green Hours", f"{green_hours:,}")

            # Fuel consumption if available
            fuel_consumed = recommended.get('fuel_consumed', 0)
            if fuel_consumed > 0:
                st.info(f"**Estimated Fuel:** {fuel_consumed:,.0f} L/year")

        # Alternatives table
        if alternatives:
            st.markdown("### 📊 Top Alternatives")

            alt_data = []
            for alt in alternatives[:4]:  # Show top 4 alternatives
                vs_rec = alt.get('vs_recommended', {})
                hours_diff = vs_rec.get('hours_diff', 0) if isinstance(vs_rec, dict) else 0
                diff_str = f"{hours_diff:+,} hrs" if hours_diff != 0 else "same"

                alt_data.append({
                    'Rank': f"#{alt.get('rank', '-')}",
                    'Configuration': f"{alt.get('power_mw', 0):.0f} MW × {alt.get('duration_hrs', 0)}-hr",
                    'Capacity': f"{alt.get('bess_mwh', 0):.0f} MWh",
                    'Delivery %': f"{alt.get('delivery_pct', 0):.1f}%",
                    'Wastage %': f"{alt.get('wastage_pct', 0):.1f}%",
                    'DG Hours': f"{alt.get('dg_hours', 0):,}",
                    'vs Rec': diff_str,
                })

            if alt_data:
                alt_df = pd.DataFrame(alt_data)
                st.dataframe(alt_df, hide_index=True, width='stretch')

        st.markdown("---")

else:
    # Fallback: No ranked recommendations available - will use legacy top config display
    pass


# =============================================================================
# TABLE VIEW
# =============================================================================

st.markdown("---")

# Quick filters
st.markdown("### Quick Filters")
filter_cols = st.columns(4)

filters = results_state.get('filters', {})

with filter_cols[0]:
    full_delivery = st.checkbox(
        "100% Delivery",
        value=filters.get('full_delivery', False),
        key='filter_full_delivery'
    )
    set_results_filter('full_delivery', full_delivery)

with filter_cols[1]:
    zero_dg = st.checkbox(
        "Zero DG",
        value=filters.get('zero_dg', False),
        key='filter_zero_dg'
    )
    set_results_filter('zero_dg', zero_dg)

with filter_cols[2]:
    low_wastage = st.checkbox(
        "Low Wastage (≤2%)",
        value=filters.get('low_wastage', False),
        key='filter_low_wastage'
    )
    set_results_filter('low_wastage', low_wastage)

with filter_cols[3]:
    hide_dominated = st.checkbox(
        "Hide Dominated",
        value=filters.get('hide_dominated', False),
        key='filter_hide_dominated'
    )
    set_results_filter('hide_dominated', hide_dominated)

# Apply filters
filtered_df = filter_results(results_df, {
    'full_delivery': full_delivery,
    'zero_dg': zero_dg,
    'low_wastage': low_wastage,
    'hide_dominated': hide_dominated,
})

st.caption(f"Showing {len(filtered_df)} of {len(results_df)} configurations")

st.markdown("---")

# Results table
st.markdown("### All Configurations")

# Format display columns - check if wastage_load_pct exists
has_load_wastage = 'wastage_load_pct' in filtered_df.columns

if has_load_wastage:
    display_df = filtered_df[[
        'bess_mwh', 'duration_hrs', 'power_mw', 'dg_mw',
        'delivery_pct', 'wastage_pct', 'wastage_load_pct', 'delivery_hours',
        'dg_hours', 'bess_cycles'
    ]].copy()
else:
    display_df = filtered_df[[
        'bess_mwh', 'duration_hrs', 'power_mw', 'dg_mw',
        'delivery_pct', 'wastage_pct', 'delivery_hours',
        'dg_hours', 'bess_cycles'
    ]].copy()

# Add combined BESS Size column (MW × hr format)
display_df.insert(0, 'BESS Size',
    display_df.apply(lambda r: f"{r['power_mw']:.0f} MW × {r['duration_hrs']:.0f}-hr", axis=1))

if has_load_wastage:
    display_df.columns = [
        'BESS Size', 'Capacity (MWh)', 'Duration (hrs)', 'Power (MW)', 'DG (MW)',
        'Delivery %', 'Total Wastage %', 'Load Wastage %', 'Delivery Hours',
        'DG Hours', 'BESS Cycles'
    ]
else:
    display_df.columns = [
        'BESS Size', 'Capacity (MWh)', 'Duration (hrs)', 'Power (MW)', 'DG (MW)',
        'Delivery %', 'Wastage %', 'Delivery Hours',
        'DG Hours', 'BESS Cycles'
    ]

# Round values
round_dict = {
    'Delivery %': 1,
    'Power (MW)': 1,
    'BESS Cycles': 0,
}
if has_load_wastage:
    round_dict['Total Wastage %'] = 1
    round_dict['Load Wastage %'] = 1
else:
    round_dict['Wastage %'] = 1

display_df = display_df.round(round_dict)

# Sortable dataframe
sort_col = st.selectbox(
    "Sort by:",
    options=display_df.columns.tolist(),
    index=4,  # Default to Delivery %
    key='sort_column'
)

sort_asc = st.checkbox("Ascending", value=False, key='sort_asc')
display_df = display_df.sort_values(by=sort_col, ascending=sort_asc)

st.dataframe(
    display_df,
    width='stretch',
    height=400,
    hide_index=True
)

# Export
st.markdown("---")
st.markdown("### Export")

col1, col2 = st.columns(2)

with col1:
    csv_data = results_df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        data=csv_data,
        file_name="bess_sizing_results.csv",
        mime="text/csv"
    )

with col2:
    # Summary export
    summary = {
        'Total Configurations': len(results_df),
        'Best Delivery %': results_df['delivery_pct'].max(),
        'Best BESS Size': results_df.loc[results_df['delivery_pct'].idxmax(), 'bess_mwh'],
        'Min Wastage %': results_df['wastage_pct'].min(),
    }
    summary_df = pd.DataFrame([summary])
    summary_csv = summary_df.to_csv(index=False)
    st.download_button(
        "📥 Download Summary",
        data=summary_csv,
        file_name="bess_sizing_summary.csv",
        mime="text/csv"
    )


# =============================================================================
# NAVIGATION
# =============================================================================

st.divider()

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Edit Sizing Range", width='stretch'):
        st.switch_page("pages/10_📐_Step3_Sizing.py")

with col2:
    if st.button("🔍 Detailed Analysis →", type="primary", width='stretch'):
        # Store best config index for pre-selection in Step 5
        if len(results_df) > 0:
            best_idx = results_df['delivery_pct'].idxmax()
            update_wizard_state('results', 'analysis_config_idx', best_idx)
        st.switch_page("pages/12_🔍_Step5_Analysis.py")

with col3:
    if st.button("🔄 New Analysis", width='stretch'):
        st.switch_page("pages/8_🚀_Step1_Setup.py")


# Sidebar summary
with st.sidebar:
    st.markdown("### 📋 Analysis Summary")

    st.markdown(f"**Configurations:** {len(results_df)}")
    st.markdown(f"**Best Delivery:** {results_df['delivery_pct'].max():.1f}%")
    st.markdown(f"**Min Wastage:** {results_df['wastage_pct'].min():.1f}%")

    st.markdown("---")

    template_info = get_template_info(rules['inferred_template'])
    st.markdown(f"**Strategy:** {template_info['name']}")
    st.markdown(f"**Load:** {setup['load_mw']} MW")
    st.markdown(f"**Solar:** {setup['solar_capacity_mw']} MWp")
