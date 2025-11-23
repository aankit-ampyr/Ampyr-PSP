"""
BESS Optimization Page
Advanced optimization algorithms and visualizations
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_solar_profile, get_solar_statistics
from src.battery_simulator import simulate_bess_year
from utils.metrics import calculate_metrics_summary
from utils.config_manager import get_config
from utils.validators import validate_battery_config

# Page config
st.set_page_config(page_title="Optimization", page_icon="🎯", layout="wide")

st.title("🎯 BESS Optimization Analysis")
st.markdown("Advanced optimization algorithms for battery sizing")

# Show configuration status
if 'config' in st.session_state:
    st.info("📌 Using custom configuration from Configuration page")
else:
    st.info("📌 Using default configuration")

st.markdown("---")


def high_yield_knee_algorithm(all_results, performance_threshold=0.95):
    """
    High-Yield Knee Algorithm for battery optimization.

    This algorithm:
    1. Scans all battery sizes to calculate marginal gains
    2. Filters to high-performance arena (≥ threshold of maximum)
    3. Selects the size with maximum marginal gain in high-performance zone

    Args:
        all_results: List of dicts with results for all battery sizes
        performance_threshold: Fraction of max performance to define high-yield zone

    Returns:
        dict: Optimal battery size and detailed analysis
    """
    if len(all_results) < 2:
        return {
            'optimal_size_mwh': all_results[0]['Battery Size (MWh)'],
            'reasoning': 'Insufficient data for optimization',
            'marginal_gains': [],
            'high_performance_candidates': []
        }

    # Phase 1: Scan - Calculate marginal gains for all sizes
    marginal_gains = []

    for i in range(1, len(all_results)):
        prev = all_results[i-1]
        curr = all_results[i]

        size_increase = curr['Battery Size (MWh)'] - prev['Battery Size (MWh)']
        hours_increase = curr['Delivery Hours'] - prev['Delivery Hours']

        # Calculate marginal gain (hours per MWh)
        if size_increase > 0:
            marginal_gain = hours_increase / size_increase
        else:
            marginal_gain = 0

        marginal_gains.append({
            'size_mwh': curr['Battery Size (MWh)'],
            'delivery_hours': curr['Delivery Hours'],
            'marginal_gain_hours_per_mwh': marginal_gain,
            'marginal_gain_hours_per_10mwh': marginal_gain * 10  # For display
        })

    # Phase 2: Filter - Identify high-performance arena
    max_hours = max(result['Delivery Hours'] for result in all_results)
    threshold_hours = max_hours * performance_threshold

    high_performance_candidates = [
        mg for mg in marginal_gains
        if mg['delivery_hours'] >= threshold_hours
    ]

    # Phase 3: Select - Find maximum marginal gain in high-performance zone
    if high_performance_candidates:
        # Find the candidate with maximum marginal gain
        optimal = max(high_performance_candidates,
                     key=lambda x: x['marginal_gain_hours_per_mwh'])

        reasoning = (f"Selected {optimal['size_mwh']} MWh: "
                    f"Maximum marginal gain ({optimal['marginal_gain_hours_per_10mwh']:.1f} hours/10MWh) "
                    f"in high-performance zone (≥{performance_threshold:.0%} of max {max_hours:,} hours)")
    else:
        # Fallback to smallest size that achieves threshold
        for mg in marginal_gains:
            if mg['delivery_hours'] >= threshold_hours:
                optimal = mg
                reasoning = f"First size achieving {performance_threshold:.0%} of maximum hours"
                break
        else:
            # If no size achieves threshold, take the best available
            optimal = max(marginal_gains, key=lambda x: x['delivery_hours'])
            reasoning = f"Best available (threshold not achieved)"

    return {
        'optimal_size_mwh': optimal['size_mwh'],
        'delivery_hours': optimal['delivery_hours'],
        'marginal_gain': optimal['marginal_gain_hours_per_10mwh'],
        'reasoning': reasoning,
        'marginal_gains': marginal_gains,
        'high_performance_candidates': high_performance_candidates,
        'max_hours': max_hours,
        'threshold_hours': threshold_hours
    }


# Get configuration
config = get_config()

# Load solar profile
@st.cache_data
def get_solar_data():
    """Load and cache solar profile data."""
    profile = load_solar_profile()
    stats = get_solar_statistics(profile)
    return profile, stats

solar_profile, solar_stats = get_solar_data()

# Sidebar controls
st.sidebar.markdown("### 🎯 Optimization Controls")

# Algorithm selection
algorithm = st.sidebar.selectbox(
    "Optimization Algorithm",
    ["High-Yield Knee", "Marginal Improvement Threshold"],
    index=0,
    help="Select the optimization algorithm to use"
)

# Performance threshold for High-Yield Knee
if algorithm == "High-Yield Knee":
    performance_threshold = st.sidebar.slider(
        "Performance Threshold (%)",
        min_value=80,
        max_value=99,
        value=95,
        step=1,
        help="Minimum performance level (% of max) to consider for optimization"
    ) / 100
else:
    marginal_threshold = st.sidebar.number_input(
        "Marginal Improvement Threshold (hours/10MWh)",
        min_value=50,
        max_value=500,
        value=config['MARGINAL_IMPROVEMENT_THRESHOLD'],
        step=50,
        help="Stop when marginal improvement falls below this threshold"
    )

# Battery size range
st.sidebar.markdown("### 🔋 Battery Size Range")
min_size = st.sidebar.number_input(
    "Minimum Size (MWh)",
    min_value=10,
    max_value=400,
    value=config['MIN_BATTERY_SIZE_MWH'],
    step=10
)

max_size = st.sidebar.number_input(
    "Maximum Size (MWh)",
    min_value=50,
    max_value=1000,
    value=config['MAX_BATTERY_SIZE_MWH'],
    step=10
)

step_sizes = [5, 10, 20, 25, 50]
default_step_index = step_sizes.index(config['BATTERY_SIZE_STEP_MWH']) if config['BATTERY_SIZE_STEP_MWH'] in step_sizes else 0
step_size = st.sidebar.selectbox(
    "Step Size (MWh)",
    step_sizes,
    index=default_step_index
)

# Check if results already exist from simulation page
if 'all_results' in st.session_state:
    st.sidebar.success("✅ Using existing simulation data")
    st.sidebar.markdown("*Results loaded from Simulation page*")

    # Automatically analyze with current settings if not already done
    if 'optimization_results' not in st.session_state:
        all_results = st.session_state['all_results']

        # Run selected optimization algorithm
        if algorithm == "High-Yield Knee":
            optimal = high_yield_knee_algorithm(all_results, performance_threshold)
        else:
            # Use existing marginal improvement method
            from utils.metrics import find_optimal_battery_size
            optimal = find_optimal_battery_size(all_results)
            # Add marginal gains for visualization
            marginal_gains = []
            for i in range(1, len(all_results)):
                prev = all_results[i-1]
                curr = all_results[i]
                size_increase = curr['Battery Size (MWh)'] - prev['Battery Size (MWh)']
                hours_increase = curr['Delivery Hours'] - prev['Delivery Hours']
                marginal_gain = (hours_increase / size_increase) if size_increase > 0 else 0
                marginal_gains.append({
                    'size_mwh': curr['Battery Size (MWh)'],
                    'delivery_hours': curr['Delivery Hours'],
                    'marginal_gain_hours_per_mwh': marginal_gain,
                    'marginal_gain_hours_per_10mwh': marginal_gain * 10
                })
            optimal['marginal_gains'] = marginal_gains

        # Store results in session state
        st.session_state['optimization_results'] = all_results
        st.session_state['optimal_result'] = optimal
        st.session_state['algorithm_used'] = algorithm

    # Option to re-analyze with different algorithm
    if st.sidebar.button("🔄 Re-analyze with Different Algorithm", type="primary"):
        all_results = st.session_state['all_results']

        # Run selected optimization algorithm
        if algorithm == "High-Yield Knee":
            optimal = high_yield_knee_algorithm(all_results, performance_threshold)
        else:
            # Use existing marginal improvement method
            from utils.metrics import find_optimal_battery_size
            optimal = find_optimal_battery_size(all_results)
            # Add marginal gains for visualization
            marginal_gains = []
            for i in range(1, len(all_results)):
                prev = all_results[i-1]
                curr = all_results[i]
                size_increase = curr['Battery Size (MWh)'] - prev['Battery Size (MWh)']
                hours_increase = curr['Delivery Hours'] - prev['Delivery Hours']
                marginal_gain = (hours_increase / size_increase) if size_increase > 0 else 0
                marginal_gains.append({
                    'size_mwh': curr['Battery Size (MWh)'],
                    'delivery_hours': curr['Delivery Hours'],
                    'marginal_gain_hours_per_mwh': marginal_gain,
                    'marginal_gain_hours_per_10mwh': marginal_gain * 10
                })
            optimal['marginal_gains'] = marginal_gains

        # Store results in session state
        st.session_state['optimization_results'] = all_results
        st.session_state['optimal_result'] = optimal
        st.session_state['algorithm_used'] = algorithm
        st.rerun()

else:
    st.sidebar.warning("⚠️ No simulation data available")
    st.sidebar.info("Please run 'Find Optimal Size' on the Simulation page first")

    # Provide option to run new optimization if needed
    if st.sidebar.button("🚀 Run New Optimization", type="primary"):
        # Validate configuration before running optimization
        is_valid, validation_errors = validate_battery_config(config)

        if not is_valid:
            st.error("❌ **Invalid Configuration - Cannot Run Optimization**")
            st.error("Please fix the following issues in the Configuration page:")
            for error in validation_errors:
                st.error(f"  • {error}")
            st.stop()

        # Configuration is valid - proceed with optimization
        # Calculate number of simulations
        num_simulations = len(list(range(min_size, max_size + step_size, step_size)))

        # Enforce resource limits
        MAX_SIMULATIONS = 200
        actual_step_size = step_size

        if num_simulations > MAX_SIMULATIONS:
            # Calculate adjusted step size to cap at 200 simulations
            actual_step_size = (max_size - min_size) // MAX_SIMULATIONS + 1
            actual_num_simulations = len(list(range(min_size, max_size + actual_step_size, actual_step_size)))

            st.warning(f"⚠️ Configuration would run {num_simulations} simulations (exceeds limit of {MAX_SIMULATIONS})")
            st.warning(f"🔄 Auto-adjusting step size from {step_size} MWh to {actual_step_size} MWh")
            st.info(f"💡 Running {actual_num_simulations} simulations instead. To change this, adjust BATTERY_SIZE_STEP in Configuration page")

            num_simulations = actual_num_simulations
            step_size = actual_step_size

        # Warn about estimated duration for longer runs
        estimated_time_seconds = num_simulations * 0.5  # ~0.5 sec per simulation
        if estimated_time_seconds > 30:
            st.warning(f"⏱️ Running {num_simulations} simulations (estimated ~{estimated_time_seconds:.0f} seconds)")

        with st.spinner(f"Running {num_simulations} simulations..."):
            # Run simulations for all battery sizes with adjusted step
            battery_sizes = range(min_size, max_size + step_size, step_size)
            all_results = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, size in enumerate(battery_sizes):
                status_text.text(f"Simulating {size} MWh battery...")
                results = simulate_bess_year(size, solar_profile, config)
                metrics = calculate_metrics_summary(size, results)
                all_results.append(metrics)
                progress_bar.progress((i + 1) / num_simulations)

            status_text.empty()

            # Run selected optimization algorithm
            if algorithm == "High-Yield Knee":
                optimal = high_yield_knee_algorithm(all_results, performance_threshold)
            else:
                # Use existing marginal improvement method
                from utils.metrics import find_optimal_battery_size
                optimal = find_optimal_battery_size(all_results)
                # Add marginal gains for visualization
                marginal_gains = []
                for i in range(1, len(all_results)):
                    prev = all_results[i-1]
                    curr = all_results[i]
                    size_increase = curr['Battery Size (MWh)'] - prev['Battery Size (MWh)']
                    hours_increase = curr['Delivery Hours'] - prev['Delivery Hours']
                    marginal_gain = (hours_increase / size_increase) if size_increase > 0 else 0
                    marginal_gains.append({
                        'size_mwh': curr['Battery Size (MWh)'],
                        'delivery_hours': curr['Delivery Hours'],
                        'marginal_gain_hours_per_mwh': marginal_gain,
                        'marginal_gain_hours_per_10mwh': marginal_gain * 10
                    })
                optimal['marginal_gains'] = marginal_gains

            # Store results in session state
            st.session_state['all_results'] = all_results
            st.session_state['optimization_results'] = all_results
            st.session_state['optimal_result'] = optimal
            st.session_state['algorithm_used'] = algorithm

# Display results
if 'optimization_results' in st.session_state:
    results = st.session_state['optimization_results']
    optimal = st.session_state['optimal_result']
    algorithm_used = st.session_state['algorithm_used']

    # Results summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🎯 Optimal Size", f"{optimal['optimal_size_mwh']} MWh")

    with col2:
        st.metric("📊 Delivery Hours", f"{optimal['delivery_hours']:,}")

    with col3:
        if 'marginal_gain' in optimal:
            st.metric("📈 Marginal Gain", f"{optimal['marginal_gain']:.1f} hrs/10MWh")
        else:
            st.metric("📈 Total Cycles", f"{optimal.get('total_cycles', 'N/A')}")

    with col4:
        delivery_rate = (optimal['delivery_hours'] / 87.6) if optimal['delivery_hours'] else 0
        st.metric("✅ Delivery Rate", f"{delivery_rate:.1f}%")

    # Algorithm reasoning
    st.info(f"**{algorithm_used} Algorithm Result:** {optimal['reasoning']}")

    # Create visualizations
    st.markdown("---")
    st.markdown("### 📊 Optimization Visualizations")

    # Prepare data
    df = pd.DataFrame(results)

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Delivery Hours vs Battery Size",
            "Marginal Gains Analysis",
            "Performance Threshold Visualization",
            "Cost-Benefit Curve"
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )

    # Plot 1: Delivery Hours vs Battery Size
    fig.add_trace(
        go.Scatter(
            x=df['Battery Size (MWh)'],
            y=df['Delivery Hours'],
            mode='lines+markers',
            name='Delivery Hours',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )

    # Mark optimal point
    optimal_idx = df[df['Battery Size (MWh)'] == optimal['optimal_size_mwh']].index[0]
    fig.add_trace(
        go.Scatter(
            x=[optimal['optimal_size_mwh']],
            y=[optimal['delivery_hours']],
            mode='markers',
            name='Optimal Size',
            marker=dict(color='red', size=12, symbol='star')
        ),
        row=1, col=1
    )

    # Plot 2: Marginal Gains
    if 'marginal_gains' in optimal and optimal['marginal_gains']:
        mg_df = pd.DataFrame(optimal['marginal_gains'])

        fig.add_trace(
            go.Scatter(
                x=mg_df['size_mwh'],
                y=mg_df['marginal_gain_hours_per_10mwh'],
                mode='lines+markers',
                name='Marginal Gain',
                line=dict(color='green', width=2),
                marker=dict(size=6)
            ),
            row=1, col=2
        )

        # Mark optimal marginal gain
        optimal_mg = mg_df[mg_df['size_mwh'] == optimal['optimal_size_mwh']]
        if not optimal_mg.empty:
            fig.add_trace(
                go.Scatter(
                    x=optimal_mg['size_mwh'],
                    y=optimal_mg['marginal_gain_hours_per_10mwh'],
                    mode='markers',
                    name='Selected',
                    marker=dict(color='red', size=12, symbol='star'),
                    showlegend=False
                ),
                row=1, col=2
            )

    # Plot 3: Performance Threshold (for High-Yield Knee)
    if algorithm_used == "High-Yield Knee" and 'high_performance_candidates' in optimal:
        # Show all points
        fig.add_trace(
            go.Scatter(
                x=df['Battery Size (MWh)'],
                y=df['Delivery Hours'],
                mode='markers',
                name='All Sizes',
                marker=dict(color='lightgray', size=8),
                showlegend=True
            ),
            row=2, col=1
        )

        # Highlight high-performance candidates
        hp_sizes = [c['size_mwh'] for c in optimal['high_performance_candidates']]
        hp_hours = [c['delivery_hours'] for c in optimal['high_performance_candidates']]

        # Calculate the threshold percentage for display
        if 'max_hours' in optimal and optimal['max_hours'] > 0:
            threshold_pct = optimal['threshold_hours'] / optimal['max_hours']
        else:
            threshold_pct = 0.95  # Default

        fig.add_trace(
            go.Scatter(
                x=hp_sizes,
                y=hp_hours,
                mode='markers',
                name=f'High Performance (≥{threshold_pct:.0%})',
                marker=dict(color='orange', size=10),
                showlegend=True
            ),
            row=2, col=1
        )

        # Add threshold line
        fig.add_trace(
            go.Scatter(
                x=[df['Battery Size (MWh)'].min(), df['Battery Size (MWh)'].max()],
                y=[optimal['threshold_hours'], optimal['threshold_hours']],
                mode='lines',
                name='Threshold',
                line=dict(color='red', dash='dash'),
                showlegend=True
            ),
            row=2, col=1
        )
    else:
        # For Marginal Improvement algorithm, show a different visualization
        fig.add_trace(
            go.Scatter(
                x=df['Battery Size (MWh)'],
                y=df['Delivery Hours'],
                mode='lines+markers',
                name='Performance Curve',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ),
            row=2, col=1
        )

        # Mark the optimal point
        optimal_idx = df[df['Battery Size (MWh)'] == optimal['optimal_size_mwh']].index[0]
        fig.add_trace(
            go.Scatter(
                x=[optimal['optimal_size_mwh']],
                y=[df.loc[optimal_idx, 'Delivery Hours']],
                mode='markers',
                name='Selected (Marginal)',
                marker=dict(color='red', size=12, symbol='star'),
                showlegend=True
            ),
            row=2, col=1
        )

    # Plot 4: Cost-Benefit (assuming linear cost)
    # Calculate value per MWh (simplified)
    df['Value per MWh'] = df['Delivery Hours'] / df['Battery Size (MWh)']

    fig.add_trace(
        go.Scatter(
            x=df['Battery Size (MWh)'],
            y=df['Value per MWh'],
            mode='lines+markers',
            name='Value/MWh',
            line=dict(color='purple', width=2),
            marker=dict(size=6)
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_layout(
        height=700,
        showlegend=True,
        title_text=f"BESS Optimization Analysis - {algorithm_used} Algorithm",
        title_x=0.5
    )

    # Update axes labels
    fig.update_xaxes(title_text="Battery Size (MWh)", row=1, col=1)
    fig.update_yaxes(title_text="Delivery Hours", row=1, col=1)

    fig.update_xaxes(title_text="Battery Size (MWh)", row=1, col=2)
    fig.update_yaxes(title_text="Marginal Gain (hrs/10MWh)", row=1, col=2)

    fig.update_xaxes(title_text="Battery Size (MWh)", row=2, col=1)
    fig.update_yaxes(title_text="Delivery Hours", row=2, col=1)

    fig.update_xaxes(title_text="Battery Size (MWh)", row=2, col=2)
    fig.update_yaxes(title_text="Hours per MWh", row=2, col=2)

    st.plotly_chart(fig, use_container_width=True)

    # Detailed comparison table
    st.markdown("---")
    st.markdown("### 📋 Detailed Results Comparison")

    if algorithm_used == "High-Yield Knee" and 'high_performance_candidates' in optimal:
        # Show top candidates
        st.markdown("#### Top Candidates (High-Performance Zone)")

        candidates_data = []
        for candidate in optimal['high_performance_candidates'][:10]:  # Show top 10
            # Find full metrics for this size
            full_metrics = next(r for r in results if r['Battery Size (MWh)'] == candidate['size_mwh'])
            candidates_data.append({
                'Battery Size (MWh)': candidate['size_mwh'],
                'Delivery Hours': candidate['delivery_hours'],
                'Marginal Gain (hrs/10MWh)': f"{candidate['marginal_gain_hours_per_10mwh']:.1f}",
                'Total Cycles': f"{full_metrics['Total Cycles']:.1f}",
                'Degradation (%)': f"{full_metrics['Degradation (%)']:.3f}",
                'Selected': '✅' if candidate['size_mwh'] == optimal['optimal_size_mwh'] else ''
            })

        candidates_df = pd.DataFrame(candidates_data)
        st.dataframe(
            candidates_df,
            use_container_width=True,
            hide_index=True
        )

    # Full results table
    with st.expander("📊 View All Results"):
        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )

    # Download results
    col1, col2 = st.columns(2)

    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full Results",
            data=csv,
            file_name=f"bess_optimization_{algorithm_used.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )

    with col2:
        if 'marginal_gains' in optimal:
            mg_df = pd.DataFrame(optimal['marginal_gains'])
            mg_csv = mg_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Marginal Analysis",
                data=mg_csv,
                file_name="marginal_gains_analysis.csv",
                mime="text/csv"
            )