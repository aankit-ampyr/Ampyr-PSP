"""
Step 4: Results

Display and analyze simulation results:
- Quick filters
- Sortable table
- Color-coded metrics
- Detail view
- Comparison view
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    set_current_step, get_step_status, can_navigate_to_step,
    add_comparison_config, remove_comparison_config, clear_comparison_selection,
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


def create_comparison_chart(configs: list, results_df: pd.DataFrame) -> go.Figure:
    """Create side-by-side comparison chart."""
    if not configs:
        return None

    rows = results_df.iloc[configs]

    # Metrics to compare
    metrics = ['delivery_pct', 'wastage_pct', 'bess_cycles', 'dg_hours']
    metric_labels = ['Delivery %', 'Wastage %', 'BESS Cycles', 'DG Hours']

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=metric_labels
    )

    colors = ['#3498db', '#2ecc71', '#e74c3c']
    config_labels = [f"{row['bess_mwh']:.0f} MWh / {row['duration_hrs']}-hr" for _, row in rows.iterrows()]

    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        row_num = i // 2 + 1
        col_num = i % 2 + 1

        values = rows[metric].tolist()

        fig.add_trace(
            go.Bar(
                x=config_labels,
                y=values,
                marker_color=colors[:len(values)],
                showlegend=False,
            ),
            row=row_num, col=col_num
        )

    fig.update_layout(height=500, title_text="Configuration Comparison")
    return fig


def create_detail_charts(row: pd.Series) -> dict:
    """Create detailed charts for a single configuration."""
    charts = {}

    # Key metrics gauge chart
    fig_metrics = make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]]
    )

    fig_metrics.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=row['delivery_pct'],
            title={'text': "Delivery %"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': get_delivery_color(row['delivery_pct'])},
                'steps': [
                    {'range': [0, 95], 'color': '#ffcccc'},
                    {'range': [95, 99], 'color': '#ffffcc'},
                    {'range': [99, 100], 'color': '#ccffcc'},
                ],
            }
        ),
        row=1, col=1
    )

    fig_metrics.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=row['wastage_pct'],
            title={'text': "Wastage %"},
            gauge={
                'axis': {'range': [0, 20]},
                'bar': {'color': get_wastage_color(row['wastage_pct'])},
                'steps': [
                    {'range': [0, 2], 'color': '#ccffcc'},
                    {'range': [2, 5], 'color': '#ffffcc'},
                    {'range': [5, 20], 'color': '#ffcccc'},
                ],
            }
        ),
        row=1, col=2
    )

    fig_metrics.add_trace(
        go.Indicator(
            mode="number+delta",
            value=row['bess_mwh'],
            title={'text': "BESS Size (MWh)"},
            delta={'reference': 100, 'relative': True},
        ),
        row=1, col=3
    )

    fig_metrics.update_layout(height=250)
    charts['metrics'] = fig_metrics

    return charts


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
# VIEW SELECTION
# =============================================================================

view_mode = st.radio(
    "View Mode:",
    options=['table', 'detail', 'compare'],
    format_func=lambda x: {
        'table': '📋 Results Table',
        'detail': '🔍 Detail View',
        'compare': '⚖️ Compare'
    }.get(x),
    horizontal=True,
    key='view_mode_radio'
)


# =============================================================================
# TABLE VIEW
# =============================================================================

if view_mode == 'table':
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

    # THREE KEY METRICS - Always visible at top
    st.markdown("### 🎯 Top Configuration")

    if len(filtered_df) > 0:
        # Best by delivery
        best_row = filtered_df.loc[filtered_df['delivery_pct'].idxmax()]

        metric_cols = st.columns(3)

        with metric_cols[0]:
            delivery_color = get_delivery_color(best_row['delivery_pct'])
            st.markdown(f"""
            <div style="
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid {delivery_color};
            ">
                <h1 style="color: {delivery_color}; margin: 0;">{best_row['delivery_pct']:.1f}%</h1>
                <p style="margin: 5px 0;">Delivery Rate</p>
            </div>
            """, unsafe_allow_html=True)

        with metric_cols[1]:
            wastage_color = get_wastage_color(best_row['wastage_pct'])
            st.markdown(f"""
            <div style="
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid {wastage_color};
            ">
                <h1 style="color: {wastage_color}; margin: 0;">{best_row['wastage_pct']:.1f}%</h1>
                <p style="margin: 5px 0;">Wastage</p>
            </div>
            """, unsafe_allow_html=True)

        with metric_cols[2]:
            power_mw = best_row.get('power_mw', best_row['bess_mwh'] / best_row['duration_hrs'])
            st.markdown(f"""
            <div style="
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #3498db;
            ">
                <h1 style="color: #3498db; margin: 0;">{best_row['bess_mwh']:.0f} MWh</h1>
                <p style="margin: 5px 0; font-size: 14px;">{power_mw:.0f} MW × {best_row['duration_hrs']}-hr</p>
                <p style="margin: 5px 0;">BESS Size</p>
            </div>
            """, unsafe_allow_html=True)

        # Configuration summary with DG info
        config_summary = f"**Configuration:** {power_mw:.0f} MW × {best_row['duration_hrs']}-hr = {best_row['bess_mwh']:.0f} MWh"
        if best_row['dg_mw'] > 0:
            config_summary += f" | DG: {best_row['dg_mw']:.0f} MW"
        st.markdown(config_summary)

        # Select button for this configuration
        best_idx = filtered_df['delivery_pct'].idxmax()
        if st.button("📌 Select this configuration for comparison", key='select_top_config'):
            selected = results_state.get('selected_configs', [])
            if best_idx not in selected and len(selected) < 3:
                add_comparison_config(best_idx)
                st.success(f"Added to comparison: {power_mw:.0f} MW × {best_row['duration_hrs']}-hr")
                st.rerun()

    st.markdown("---")

    # Results table
    st.markdown("### All Configurations")

    # Format display columns
    display_df = filtered_df[[
        'bess_mwh', 'duration_hrs', 'power_mw', 'dg_mw',
        'delivery_pct', 'wastage_pct', 'delivery_hours',
        'dg_hours', 'bess_cycles'
    ]].copy()

    # Add combined BESS Size column (MW × hr format)
    display_df.insert(0, 'BESS Size',
        display_df.apply(lambda r: f"{r['power_mw']:.0f} MW × {r['duration_hrs']:.0f}-hr", axis=1))

    display_df.columns = [
        'BESS Size', 'Capacity (MWh)', 'Duration (hrs)', 'Power (MW)', 'DG (MW)',
        'Delivery %', 'Wastage %', 'Delivery Hours',
        'DG Hours', 'BESS Cycles'
    ]

    # Round values
    display_df = display_df.round({
        'Delivery %': 1,
        'Wastage %': 1,
        'Power (MW)': 1,
        'BESS Cycles': 0,
    })

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

    # Selection for comparison
    st.markdown("### Select for Comparison")
    st.caption("Select up to 3 configurations to compare")

    selected = results_state.get('selected_configs', [])

    select_cols = st.columns(4)
    with select_cols[0]:
        config_options = []
        for i, row in filtered_df.iterrows():
            pwr = row.get('power_mw', row['bess_mwh'] / row['duration_hrs'])
            config_options.append(f"{i}: {pwr:.0f} MW × {row['duration_hrs']}-hr = {row['bess_mwh']:.0f} MWh")
        selected_option = st.selectbox(
            "Add configuration:",
            options=[''] + config_options,
            key='add_config_select'
        )
        if selected_option and selected_option != '':
            idx = int(selected_option.split(':')[0])
            if idx not in selected and len(selected) < 3:
                add_comparison_config(idx)
                st.rerun()

    with select_cols[1]:
        if selected:
            # Show selected configs with MW × hr format
            selected_labels = []
            for idx in selected:
                if idx in filtered_df.index:
                    row = filtered_df.loc[idx]
                    pwr = row.get('power_mw', row['bess_mwh'] / row['duration_hrs'])
                    selected_labels.append(f"{pwr:.0f} MW × {row['duration_hrs']}-hr")
            st.write("Selected:", ", ".join(selected_labels))

    with select_cols[2]:
        if selected and st.button("Clear Selection"):
            clear_comparison_selection()
            st.rerun()

    with select_cols[3]:
        if len(selected) >= 2:
            if st.button("Compare Selected →", type="primary"):
                st.session_state.view_mode_radio = 'compare'
                st.rerun()

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
# DETAIL VIEW
# =============================================================================

elif view_mode == 'detail':
    st.markdown("---")
    st.markdown("### Configuration Detail")

    # Select configuration
    config_options = [f"{i}: {row['bess_mwh']:.0f} MWh / {row['duration_hrs']}-hr / {row['dg_mw']:.0f} MW DG"
                     for i, row in results_df.iterrows()]

    selected_config = st.selectbox(
        "Select configuration:",
        options=config_options,
        key='detail_config_select'
    )

    if selected_config:
        idx = int(selected_config.split(':')[0])
        row = results_df.iloc[idx]

        # Key metrics
        st.markdown("### Key Metrics")
        charts = create_detail_charts(row)
        st.plotly_chart(charts['metrics'], width='stretch')

        # Detailed metrics table
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Configuration")
            st.metric("BESS Capacity", f"{row['bess_mwh']:.0f} MWh")
            st.metric("Duration", f"{row['duration_hrs']} hours")
            st.metric("Power", f"{row['power_mw']:.1f} MW")
            if setup['dg_enabled']:
                st.metric("DG Capacity", f"{row['dg_mw']:.0f} MW")

        with col2:
            st.markdown("#### Performance")
            st.metric("Delivery Rate", f"{row['delivery_pct']:.1f}%")
            st.metric("Delivery Hours", f"{row['delivery_hours']:,} / 8,760")
            st.metric("Wastage", f"{row['wastage_pct']:.1f}%")
            st.metric("BESS Cycles", f"{row['bess_cycles']:.0f}")
            if setup['dg_enabled']:
                st.metric("DG Runtime", f"{row['dg_hours']:,} hours")


# =============================================================================
# COMPARE VIEW
# =============================================================================

elif view_mode == 'compare':
    st.markdown("---")
    st.markdown("### Side-by-Side Comparison")

    selected = results_state.get('selected_configs', [])

    if len(selected) < 2:
        st.warning("Select at least 2 configurations from the Results Table to compare.")

        # Quick select
        st.markdown("### Quick Select")
        config_options = [f"{i}: {row['bess_mwh']:.0f} MWh / {row['duration_hrs']}-hr"
                        for i, row in results_df.iterrows()]

        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                opt = st.selectbox(
                    f"Config {i+1}:",
                    options=[''] + config_options,
                    key=f'compare_select_{i}'
                )
                if opt and opt != '':
                    idx = int(opt.split(':')[0])
                    if idx not in selected:
                        add_comparison_config(idx)

        if len(selected) >= 2 and st.button("Compare", type="primary"):
            st.rerun()

    else:
        # Comparison chart
        fig = create_comparison_chart(selected, results_df)
        if fig:
            st.plotly_chart(fig, width='stretch')

        # Side-by-side metrics
        st.markdown("### Metrics Comparison")

        cols = st.columns(len(selected))

        for i, idx in enumerate(selected):
            row = results_df.iloc[idx]
            with cols[i]:
                st.markdown(f"#### Config {i+1}")
                st.markdown(f"**{row['bess_mwh']:.0f} MWh / {row['duration_hrs']}-hr**")

                # Find best values
                is_best_delivery = row['delivery_pct'] == results_df.iloc[selected]['delivery_pct'].max()
                is_best_wastage = row['wastage_pct'] == results_df.iloc[selected]['wastage_pct'].min()
                is_best_dg = row['dg_hours'] == results_df.iloc[selected]['dg_hours'].min()

                delivery_suffix = " ✓" if is_best_delivery else ""
                wastage_suffix = " ✓" if is_best_wastage else ""
                dg_suffix = " ✓" if is_best_dg else ""

                st.metric("Delivery %", f"{row['delivery_pct']:.1f}%{delivery_suffix}")
                st.metric("Wastage %", f"{row['wastage_pct']:.1f}%{wastage_suffix}")
                st.metric("BESS Cycles", f"{row['bess_cycles']:.0f}")
                st.metric("DG Hours", f"{row['dg_hours']:,}{dg_suffix}")

        st.caption("✓ = Best in category")

        # Clear selection
        if st.button("Clear Selection"):
            clear_comparison_selection()
            st.rerun()


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
