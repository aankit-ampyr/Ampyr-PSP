"""
Metrics calculation utilities for BESS sizing analysis
"""

import datetime

import pandas as pd
import numpy as np

from src.config import (
    MARGINAL_IMPROVEMENT_THRESHOLD,
    MARGINAL_INCREMENT_MWH,
    BATTERY_SIZE_STEP_MWH,
    HOURS_PER_YEAR,
    MAX_SIMULATIONS,
    SIMULATION_START_YEAR
)


def calculate_metrics_summary(battery_capacity_mwh, simulation_results):
    """
    Calculate summary metrics for a battery configuration.

    Args:
        battery_capacity_mwh: Battery capacity in MWh
        simulation_results: Results from simulation

    Returns:
        dict: Formatted metrics
    """
    # Calculate wastage percentage
    # Wastage = wasted solar / total solar available (excludes battery discharge energy)
    total_solar_available = simulation_results.get('solar_charged_mwh', 0) + simulation_results.get('solar_wasted_mwh', 0)
    if total_solar_available > 0:
        wastage_percent = (simulation_results['solar_wasted_mwh'] / total_solar_available) * 100
    else:
        wastage_percent = 0

    metrics = {
        'Battery Size (MWh)': battery_capacity_mwh,
        'Delivery Hours': simulation_results['hours_delivered'],
        'Delivery Rate (%)': round((simulation_results['hours_delivered'] / HOURS_PER_YEAR) * 100, 1),
        'Energy Delivered (GWh)': round(simulation_results['energy_delivered_mwh'] / 1000, 2),
        'Solar Charged (MWh)': round(simulation_results['solar_charged_mwh'], 1),
        'Solar Wasted (MWh)': round(simulation_results['solar_wasted_mwh'], 1),
        'Wastage (%)': round(wastage_percent, 1),
        'Battery Discharged (MWh)': round(simulation_results['battery_discharged_mwh'], 1),
        'Total Cycles': round(simulation_results['total_cycles'], 1),
        'Avg Daily Cycles': round(simulation_results['avg_daily_cycles'], 2),
        'Max Daily Cycles': round(simulation_results['max_daily_cycles'], 2),
        'Degradation (%)': round(simulation_results['degradation_percent'], 3)
    }
    return metrics


def find_optimal_battery_size(all_results):
    """
    Find optimal battery size based on diminishing returns.

    Args:
        all_results: List of dicts with results for all battery sizes

    Returns:
        dict: Optimal battery size and reasoning
    """
    if len(all_results) < 2:
        return {
            'optimal_size_mwh': all_results[0]['Battery Size (MWh)'],
            'reasoning': 'Insufficient data for optimization',
            'marginal_improvements': []
        }

    # Calculate marginal improvements
    marginal_improvements = []

    for i in range(1, len(all_results)):
        prev = all_results[i-1]
        curr = all_results[i]

        size_increase = curr['Battery Size (MWh)'] - prev['Battery Size (MWh)']
        hours_increase = curr['Delivery Hours'] - prev['Delivery Hours']

        # Calculate marginal improvement per 10 MWh
        if size_increase > 0:
            marginal_per_10mwh = (hours_increase / size_increase) * MARGINAL_INCREMENT_MWH
        else:
            marginal_per_10mwh = 0

        marginal_improvements.append({
            'size_mwh': curr['Battery Size (MWh)'],
            'marginal_hours_per_10mwh': round(marginal_per_10mwh, 1),
            'total_hours': curr['Delivery Hours']
        })

    # Find where marginal improvement falls below threshold
    optimal_idx = 0
    for i, improvement in enumerate(marginal_improvements):
        if improvement['marginal_hours_per_10mwh'] < MARGINAL_IMPROVEMENT_THRESHOLD:
            optimal_idx = i
            break
    else:
        optimal_idx = len(marginal_improvements) - 1

    optimal_size = marginal_improvements[optimal_idx]['size_mwh']

    # Get the actual result for optimal size
    # Bug #9 Fix: Use default value to prevent StopIteration exception
    optimal_result = next(
        (r for r in all_results if r['Battery Size (MWh)'] == optimal_size),
        None
    )

    if optimal_result is None:
        available_sizes = sorted([r['Battery Size (MWh)'] for r in all_results])
        raise ValueError(
            f"Optimal size {optimal_size} MWh not found in simulation results. "
            f"Available sizes: {available_sizes}. "
            f"This may indicate a bug in the optimization algorithm or configuration mismatch."
        )

    return {
        'optimal_size_mwh': optimal_size,
        'delivery_hours': optimal_result['Delivery Hours'],
        'total_cycles': optimal_result['Total Cycles'],
        'reasoning': f'Marginal improvement below {MARGINAL_IMPROVEMENT_THRESHOLD} hours per {MARGINAL_INCREMENT_MWH} MWh',
        'marginal_improvements': marginal_improvements
    }


def create_hourly_dataframe(hourly_data):
    """
    Create a DataFrame from hourly simulation data.

    Args:
        hourly_data: List of hourly data dicts

    Returns:
        pd.DataFrame: Formatted hourly data with specified columns
    """
    df = pd.DataFrame(hourly_data)

    # Create date column using configured simulation start year
    start_date = datetime.date(SIMULATION_START_YEAR, 1, 1)
    df['date'] = pd.to_datetime(start_date) + pd.to_timedelta(df['hour'] // 24, unit='days')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    # Add hour of day
    df['hour_of_day'] = df['hour'] % 24

    # Create the final dataframe with requested columns and order
    result_df = pd.DataFrame({
        'Date': df['date'],
        'Hour of Day': df['hour_of_day'],
        'Solar Generation (MW)': df['solar_mw'].round(2),
        'BESS_MW': df['bess_mw'].round(2),  # +ve for discharge, -ve for charge
        'BESS_Charge_MWh': df['bess_charge_mwh'].round(2),  # Battery energy content at start of hour
        'SOC%': df['soc_percent'].round(1),
        'Usable Energy (SOC-5%)×Cap': df['usable_energy_mwh'].round(2),  # Usable energy with formula
        'Committed MW': df['committed_mw'].round(2),  # Always 25 MW (requirement profile)
        'Deficit_MW': df['deficit_mw'].round(2),
        'Delivery': df['delivery'],
        'BESS State': df['bess_state'],
        'Wastage MWh': df['wastage_mwh'].round(2)
    })

    return result_df


def format_results_for_export(all_results):
    """
    Format all results for CSV export.

    Args:
        all_results: List of all simulation results

    Returns:
        pd.DataFrame: Formatted results ready for export
    """
    df = pd.DataFrame(all_results)

    # Reorder columns for better readability
    column_order = [
        'Battery Size (MWh)',
        'Delivery Hours',
        'Delivery Rate (%)',
        'Energy Delivered (GWh)',
        'Total Cycles',
        'Avg Daily Cycles',
        'Max Daily Cycles',
        'Solar Charged (MWh)',
        'Solar Wasted (MWh)',
        'Wastage (%)',
        'Battery Discharged (MWh)',
        'Degradation (%)'
    ]

    df = df[column_order]

    return df


def create_dg_hourly_dataframe(hourly_data):
    """
    Create a DataFrame from hourly DG simulation data.

    Args:
        hourly_data: List of hourly data dicts from DG simulation

    Returns:
        pd.DataFrame: Formatted hourly data with DG columns
    """
    df = pd.DataFrame(hourly_data)

    # Create date column using configured simulation start year
    start_date = datetime.date(SIMULATION_START_YEAR, 1, 1)
    df['date'] = pd.to_datetime(start_date) + pd.to_timedelta(df['hour'] // 24, unit='days')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    # Add hour of day
    df['hour_of_day'] = df['hour'] % 24

    # Create the final dataframe with DG-specific columns
    result_df = pd.DataFrame({
        'Date': df['date'],
        'Hour of Day': df['hour_of_day'],
        'Load (MW)': df['load_mw'].round(2),
        'Solar (MW)': df['solar_mw'].round(2),
        'Solar to Load (MW)': df['solar_to_load_mw'].round(2),
        'BESS (MW)': df['bess_mw'].round(2),  # +ve discharge, -ve charge
        'BESS to Load (MW)': df['bess_to_load_mw'].round(2),
        'SOC (%)': df['soc_percent'].round(1),
        'BESS State': df['bess_state'],
        'DG State': df['dg_state'],
        'DG Output (MW)': df['dg_output_mw'].round(2),
        'DG to Load (MW)': df['dg_to_load_mw'].round(2),
        'DG to BESS (MW)': df['dg_to_bess_mw'].round(2),
        'Solar Charged (MWh)': df['solar_charged_mwh'].round(2),
        'Solar Wasted (MWh)': df['solar_wasted_mwh'].round(2),
        'Unmet Load (MW)': df['unmet_load_mw'].round(2),
        'Delivery': df['delivery'],
    })

    return result_df


def calculate_ranked_recommendations(
    results_df,
    optimization_goal=None,
    top_n=5,
    solar_peak_mw=None
):
    """
    Calculate ranked recommendations based on user-defined optimization goals.

    Args:
        results_df: DataFrame with simulation results
        optimization_goal: dict with optimization criteria:
            - delivery_mode: 'maximize', 'at_least', 'exactly'
            - delivery_target_pct: target % when mode is 'at_least' or 'exactly'
            - optimize_for: 'min_bess_size', 'min_wastage', 'min_dg_hours', 'min_cycles'
            - max_wastage_pct: optional max wastage constraint
            - max_dg_hours: optional max DG runtime constraint
        top_n: Number of alternatives to include
        solar_peak_mw: Peak solar generation (MW). Used to filter out configs where
                       power < solar_peak (cannot capture all solar excess)

    Returns:
        dict: {
            'recommended': {...config details, reasoning...},
            'alternatives': [{rank, config, vs_recommended}...],
            'all_ranked': list,
            'marginal_analysis': list,
            'selection_method': str,
            'goal_summary': str,
            'filtered_count': int,
            'excluded_count': int
        }
    """
    if results_df is None or len(results_df) == 0:
        return None

    # Default optimization goal (backward compatibility)
    if optimization_goal is None:
        optimization_goal = {
            'delivery_mode': 'maximize',
            'delivery_target_pct': 95.0,
            'optimize_for': 'min_bess_size',
            'max_wastage_pct': None,
            'max_dg_hours': None,
        }

    # Normalize column names (handle both formats)
    df = results_df.copy()

    # Map possible column names
    col_mapping = {
        'delivery_hours': ['delivery_hours', 'Delivery Hours'],
        'delivery_pct': ['delivery_pct', 'Delivery Rate (%)', 'Delivery (%)'],
        'bess_mwh': ['bess_mwh', 'Battery Size (MWh)', 'capacity_mwh'],
        'duration_hrs': ['duration_hrs', 'duration', 'Duration'],
        'power_mw': ['power_mw', 'Power (MW)'],
        'dg_mw': ['dg_mw', 'DG Size (MW)', 'dg_capacity'],
        'dg_hours': ['dg_hours', 'DG Hours', 'dg_runtime_hours'],
        'bess_cycles': ['bess_cycles', 'Total Cycles', 'total_cycles'],
        'wastage_pct': ['wastage_pct', 'Wastage (%)', 'Solar Wastage (%)'],
        'green_hours': ['green_hours', 'Green Hours', 'hours_green_delivery'],
    }

    # Find actual column names
    def find_col(key):
        """Find the actual column name in DataFrame for a given key.

        Args:
            key: The standardized column key to look up

        Returns:
            str: The actual column name found in the DataFrame, or the key itself if not found
        """
        for possible in col_mapping.get(key, [key]):
            if possible in df.columns:
                return possible
        return key

    delivery_col = find_col('delivery_hours')
    bess_col = find_col('bess_mwh')
    duration_col = find_col('duration_hrs')
    power_col = find_col('power_mw')
    dg_col = find_col('dg_mw')
    dg_hours_col = find_col('dg_hours')
    cycles_col = find_col('bess_cycles')
    wastage_col = find_col('wastage_pct')
    delivery_pct_col = find_col('delivery_pct')
    green_hours_col = find_col('green_hours')

    # Store original count
    original_count = len(df)

    # ===========================================
    # STEP 1: Apply delivery requirement filter
    # ===========================================
    delivery_mode = optimization_goal.get('delivery_mode', 'maximize')
    delivery_target = optimization_goal.get('delivery_target_pct', 95.0)

    if delivery_mode == 'at_least':
        # Filter to configs meeting minimum delivery
        df_filtered = df[df[delivery_pct_col] >= delivery_target].copy()
        delivery_filter_desc = f"≥{delivery_target:.0f}% delivery"
    elif delivery_mode == 'exactly':
        # Filter to configs within ±1% of target (allow small tolerance)
        df_filtered = df[
            (df[delivery_pct_col] >= delivery_target - 1.0) &
            (df[delivery_pct_col] <= delivery_target + 1.0)
        ].copy()
        delivery_filter_desc = f"={delivery_target:.0f}% delivery (±1%)"
    else:
        # Maximize: no filter
        df_filtered = df.copy()
        delivery_filter_desc = "maximize delivery"

    # ===========================================
    # STEP 2: Apply secondary constraints
    # ===========================================
    constraint_descs = []

    # Max wastage constraint
    max_wastage = optimization_goal.get('max_wastage_pct')
    if max_wastage is not None and wastage_col in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[wastage_col] <= max_wastage]
        constraint_descs.append(f"≤{max_wastage:.0f}% wastage")

    # Max DG hours constraint
    max_dg_hours = optimization_goal.get('max_dg_hours')
    if max_dg_hours is not None and dg_hours_col in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[dg_hours_col] <= max_dg_hours]
        constraint_descs.append(f"≤{max_dg_hours:,} DG hrs")

    filtered_count = len(df_filtered)
    excluded_count = original_count - filtered_count

    # Handle case where no configs meet criteria
    if filtered_count == 0:
        return {
            'recommended': None,
            'alternatives': [],
            'all_ranked': [],
            'marginal_analysis': [],
            'selection_method': 'no_match',
            'goal_summary': f"No configurations meet criteria: {delivery_filter_desc}" +
                           (f", {', '.join(constraint_descs)}" if constraint_descs else ""),
            'filtered_count': 0,
            'excluded_count': original_count,
            'total_configs_tested': original_count
        }

    # ===========================================
    # STEP 3: Sort by optimization priority
    # ===========================================
    optimize_for = optimization_goal.get('optimize_for', 'min_bess_size')

    # Define sort configuration for each optimization priority
    sort_configs = {
        'min_bess_size': (bess_col, True, "smallest BESS"),
        'min_wastage': (wastage_col, True, "lowest wastage"),
        'min_dg_hours': (dg_hours_col, True, "lowest DG runtime"),
        'min_cycles': (cycles_col, True, "lowest cycles"),
    }

    sort_col, sort_asc, sort_desc = sort_configs.get(optimize_for, (bess_col, True, "smallest BESS"))

    # For 'maximize' mode, find smallest BESS that achieves max delivery
    if delivery_mode == 'maximize':
        # First, find the max delivery achieved
        max_delivery_pct = df_filtered[delivery_pct_col].max()
        # Filter to configs achieving within 0.1% of max (to handle floating point)
        near_max_delivery = df_filtered[df_filtered[delivery_pct_col] >= max_delivery_pct - 0.1].copy()

        # Special handling for min_wastage optimization:
        # Apply multi-level sorting algorithm:
        # 1. Filter configs where power >= solar_peak (can capture all solar)
        # 2. Sort by wastage ASC (lowest first)
        # 3. Sort by green_hours DESC (max solar utilization)
        # 4. Sort by power_mw ASC (smallest power that works)
        if optimize_for == 'min_wastage' and power_col in near_max_delivery.columns:
            # Apply power constraint if solar_peak_mw provided
            if solar_peak_mw is not None and solar_peak_mw > 0:
                # Filter out configs where power < solar peak (cannot capture all solar)
                power_sufficient = near_max_delivery[near_max_delivery[power_col] >= solar_peak_mw].copy()
                if len(power_sufficient) > 0:
                    near_max_delivery = power_sufficient
                    constraint_descs.append(f"power ≥ {solar_peak_mw:.0f} MW solar peak")

            # Multi-level sort for min_wastage:
            # 1. wastage_pct ASC, 2. green_hours DESC, 3. power_mw ASC
            sort_columns = [wastage_col]
            sort_ascending = [True]

            if green_hours_col in near_max_delivery.columns:
                sort_columns.append(green_hours_col)
                sort_ascending.append(False)  # DESC for green hours

            sort_columns.append(power_col)
            sort_ascending.append(True)  # ASC for power (smallest)

            df_sorted = near_max_delivery.sort_values(
                by=sort_columns,
                ascending=sort_ascending
            ).reset_index(drop=True)
            selection_method = "min_wastage_multi_level"
        else:
            # Standard single-column sort for other optimization priorities
            df_sorted = near_max_delivery.sort_values(
                by=sort_col,
                ascending=sort_asc
            ).reset_index(drop=True)
            selection_method = f"smallest_at_max_delivery_{optimize_for}"
    else:
        # All configs meet delivery requirement
        # Apply same multi-level logic for min_wastage
        if optimize_for == 'min_wastage' and power_col in df_filtered.columns:
            # Apply power constraint if solar_peak_mw provided
            working_df = df_filtered.copy()
            if solar_peak_mw is not None and solar_peak_mw > 0:
                power_sufficient = working_df[working_df[power_col] >= solar_peak_mw].copy()
                if len(power_sufficient) > 0:
                    working_df = power_sufficient
                    constraint_descs.append(f"power ≥ {solar_peak_mw:.0f} MW solar peak")

            # Multi-level sort
            sort_columns = [wastage_col]
            sort_ascending = [True]

            if green_hours_col in working_df.columns:
                sort_columns.append(green_hours_col)
                sort_ascending.append(False)

            sort_columns.append(power_col)
            sort_ascending.append(True)

            df_sorted = working_df.sort_values(
                by=sort_columns,
                ascending=sort_ascending
            ).reset_index(drop=True)
            selection_method = "min_wastage_multi_level"
        else:
            # Standard single-column sort
            df_sorted = df_filtered.sort_values(
                by=sort_col,
                ascending=sort_asc
            ).reset_index(drop=True)
            selection_method = optimize_for

    # ===========================================
    # STEP 4: Build recommendation
    # ===========================================
    rec_row = df_sorted.iloc[0]
    rec_idx = 0

    # Build reasoning string
    reasoning_parts = []
    if delivery_mode == 'maximize':
        reasoning_parts.append(f"Achieves max delivery ({rec_row.get(delivery_pct_col, 0):.1f}%)")
        reasoning_parts.append(f"with {sort_desc}")
    else:
        reasoning_parts.append(f"Meets {delivery_filter_desc}")
        reasoning_parts.append(f"with {sort_desc}")
    if constraint_descs:
        reasoning_parts.append(f"within constraints ({', '.join(constraint_descs)})")

    recommended = {
        'index': rec_idx,
        'bess_mwh': float(rec_row.get(bess_col, 0)),
        'duration_hrs': int(rec_row.get(duration_col, 0)) if duration_col in rec_row else 0,
        'power_mw': float(rec_row.get('power_mw', rec_row.get(bess_col, 0) / max(rec_row.get(duration_col, 1), 1))),
        'dg_mw': float(rec_row.get(dg_col, 0)) if dg_col in rec_row.index else 0,
        'delivery_hours': int(rec_row.get(delivery_col, 0)),
        'delivery_pct': float(rec_row.get(delivery_pct_col, 0)),
        'dg_hours': int(rec_row.get(dg_hours_col, 0)) if dg_hours_col in rec_row.index else 0,
        'total_cycles': float(rec_row.get(cycles_col, 0)) if cycles_col in rec_row.index else 0,
        'wastage_pct': float(rec_row.get(wastage_col, 0)) if wastage_col in rec_row.index else 0,
        'reasoning': ' '.join(reasoning_parts),
    }

    # Calculate degradation estimate
    if recommended['total_cycles'] > 0:
        recommended['degradation_pct'] = recommended['total_cycles'] * 0.0015 * 100
    else:
        recommended['degradation_pct'] = 0

    # ===========================================
    # STEP 5: Build alternatives list
    # ===========================================
    alternatives = []
    for rank, (idx, row) in enumerate(df_sorted.iloc[1:top_n+1].iterrows(), start=2):
        alt_delivery = int(row.get(delivery_col, 0))
        alt_bess = float(row.get(bess_col, 0))

        hours_diff = alt_delivery - recommended['delivery_hours']
        cost_diff_pct = ((alt_bess - recommended['bess_mwh']) / recommended['bess_mwh'] * 100
                        if recommended['bess_mwh'] > 0 else 0)

        alternatives.append({
            'rank': rank,
            'index': idx,
            'bess_mwh': alt_bess,
            'duration_hrs': int(row.get(duration_col, 0)) if duration_col in row else 0,
            'power_mw': float(row.get('power_mw', 0)),
            'dg_mw': float(row.get(dg_col, 0)) if dg_col in row.index else 0,
            'delivery_hours': alt_delivery,
            'delivery_pct': float(row.get(delivery_pct_col, 0)),
            'dg_hours': int(row.get(dg_hours_col, 0)) if dg_hours_col in row.index else 0,
            'wastage_pct': float(row.get(wastage_col, 0)) if wastage_col in row.index else 0,
            'vs_recommended': {
                'hours_diff': hours_diff,
                'pct_diff': (hours_diff / recommended['delivery_hours'] * 100
                            if recommended['delivery_hours'] > 0 else 0),
                'cost_diff_pct': cost_diff_pct
            }
        })

    # ===========================================
    # STEP 6: Marginal analysis (using filtered data)
    # ===========================================
    marginal_analysis = []
    if bess_col in df_filtered.columns:
        df_by_size = df_filtered.sort_values(by=bess_col).reset_index(drop=True)

        for i in range(1, len(df_by_size)):
            prev = df_by_size.iloc[i-1]
            curr = df_by_size.iloc[i]

            size_diff = float(curr.get(bess_col, 0)) - float(prev.get(bess_col, 0))
            hours_diff = int(curr.get(delivery_col, 0)) - int(prev.get(delivery_col, 0))

            if size_diff > 0:
                marginal_per_10mwh = (hours_diff / size_diff) * 10
            else:
                marginal_per_10mwh = 0

            marginal_analysis.append({
                'size_mwh': float(curr.get(bess_col, 0)),
                'marginal_hours_per_10mwh': round(marginal_per_10mwh, 1),
                'total_hours': int(curr.get(delivery_col, 0))
            })

    # All ranked (for table display, from filtered set)
    all_ranked = []
    for rank, (idx, row) in enumerate(df_sorted.iterrows(), start=1):
        all_ranked.append({
            'rank': rank,
            'bess_mwh': float(row.get(bess_col, 0)),
            'delivery_hours': int(row.get(delivery_col, 0)),
            'delivery_pct': float(row.get(delivery_pct_col, 0)),
            'wastage_pct': float(row.get(wastage_col, 0)) if wastage_col in row.index else 0,
            'dg_hours': int(row.get(dg_hours_col, 0)) if dg_hours_col in row.index else 0,
        })

    # Build goal summary
    goal_parts = [delivery_filter_desc]
    if optimize_for != 'min_bess_size' or delivery_mode != 'maximize':
        goal_parts.append(f"optimize: {sort_desc}")
    if constraint_descs:
        goal_parts.extend(constraint_descs)

    return {
        'recommended': recommended,
        'alternatives': alternatives,
        'all_ranked': all_ranked,
        'marginal_analysis': marginal_analysis,
        'selection_method': selection_method,
        'goal_summary': ', '.join(goal_parts),
        'filtered_count': filtered_count,
        'excluded_count': excluded_count,
        'total_configs_tested': original_count
    }


def calculate_simulation_params(min_size, max_size, step_size, max_simulations=None):
    """
    Calculate simulation parameters with auto-adjustment for resource limits.

    Args:
        min_size: Minimum battery size (MWh) - can be int or float
        max_size: Maximum battery size (MWh) - can be int or float
        step_size: Step size between simulations (MWh) - can be int or float
        max_simulations: Maximum allowed simulations (defaults to MAX_SIMULATIONS)

    Returns:
        dict: {
            'num_simulations': int - Number of simulations to run
            'actual_step_size': float - Adjusted step size
            'was_adjusted': bool - Whether step size was auto-adjusted
            'battery_sizes': list - List of battery sizes to test
        }
    """
    if max_simulations is None:
        max_simulations = MAX_SIMULATIONS

    # Convert to integers for range() - use int() to handle float inputs
    min_size_int = int(min_size)
    max_size_int = int(max_size)
    step_size_int = max(1, int(step_size))  # Ensure step is at least 1

    # Use max_size_int + 1 to include max_size if it falls on a step boundary
    # This prevents exceeding max_size when step doesn't divide evenly
    num_simulations = len(list(range(min_size_int, max_size_int + 1, step_size_int)))
    actual_step_size = step_size_int
    was_adjusted = False

    if num_simulations > max_simulations:
        # Auto-adjust step size to cap at max_simulations
        actual_step_size = max(1, (max_size_int - min_size_int) // max_simulations + 1)
        was_adjusted = True

    # Generate battery sizes, ensuring we don't exceed max_size
    battery_sizes = list(range(min_size_int, max_size_int + 1, actual_step_size))
    num_simulations = len(battery_sizes)

    return {
        'num_simulations': num_simulations,
        'actual_step_size': actual_step_size,
        'was_adjusted': was_adjusted,
        'original_step_size': step_size,
        'battery_sizes': battery_sizes
    }


def find_top_capacities(
    target_delivery_pct: float,
    solar_profile: list,
    load_profile: list,
    setup: dict,
    rules: dict,
    run_simulation_func,
    calculate_metrics_func,
    capacity_range: tuple = (100, 500, 25),
    duration_options: list = None,
    top_n: int = 3,
    factory_degradation: float = 0.08,
):
    """
    Find top N smallest capacities meeting delivery target using capacity-first approach.

    This algorithm:
    1. Determines minimum power required to capture solar
    2. Scans all capacities with valid durations
    3. Groups results by capacity, selecting best duration for each
    4. Returns top N smallest capacities meeting the target

    Args:
        target_delivery_pct: Target delivery percentage (e.g., 95.0)
        solar_profile: List of 8760 hourly solar values (MW)
        load_profile: List of 8760 hourly load values (MW)
        setup: Setup configuration dict (contains bess_efficiency, etc.)
        rules: Dispatch rules dict (contains template, DG settings, etc.)
        run_simulation_func: Function to run simulation (from dispatch_engine)
        calculate_metrics_func: Function to calculate metrics
        capacity_range: Tuple of (min_mwh, max_mwh, step_mwh)
        duration_options: List of duration hours to test (default: [2, 4, 6])
        top_n: Number of top capacities to return (default: 3)
        factory_degradation: Factory degradation percentage (default: 0.08 = 8%)

    Returns:
        dict: {
            'min_power_required': float - Minimum power to capture all solar,
            'solar_peak_mw': float - Peak solar generation,
            'top_capacities': [
                {
                    'capacity_mwh': float,
                    'best_duration_hrs': int,
                    'best_power_mw': float,
                    'delivery_hours': int,
                    'delivery_pct': float,
                    'wastage_pct': float,
                    'dg_hours': int,
                    'cycles': float,
                    'nameplate_mwh': float,  # capacity / (1 - factory_degradation)
                    'all_durations': [{duration, power, delivery_hours, ...}],
                },
                ...
            ],
            'scan_summary': {
                'total_capacities_tested': int,
                'capacities_meeting_target': int,
                'min_capacity_for_target': float,
                'max_delivery_achieved': float,
            },
            'all_capacity_results': list,  # Full results for charting
        }
    """
    from src.dispatch_engine import SimulationParams

    if duration_options is None:
        duration_options = [2, 4, 6]

    min_cap, max_cap, step_cap = capacity_range

    # ===========================================
    # PHASE 1: Determine minimum power requirement
    # ===========================================
    solar_peak_mw = max(solar_profile) if solar_profile else 0

    # If DG takeover mode is ON, all solar goes to BESS, so need power >= solar_peak
    # Otherwise, only excess solar goes to BESS
    dg_takeover = rules.get('dg_takeover_mode', False)
    load_mw = setup.get('load_mw', 25)

    if dg_takeover:
        min_power_required = solar_peak_mw
    else:
        min_power_required = max(0, solar_peak_mw - load_mw)

    # ===========================================
    # PHASE 2: Scan all capacities
    # ===========================================
    all_capacity_results = []
    capacity_best_configs = {}  # Group by capacity, track best duration

    capacities = list(range(int(min_cap), int(max_cap) + int(step_cap), int(step_cap)))

    for capacity in capacities:
        duration_results = []

        for duration in duration_options:
            power = capacity / duration

            # Skip if power is too low to capture solar (will curtail significantly)
            # We still run the simulation but flag it
            power_sufficient = power >= min_power_required

            # Build simulation params
            params = SimulationParams(
                load_profile=load_profile,
                solar_profile=solar_profile,
                bess_capacity=capacity,
                bess_charge_power=power,
                bess_discharge_power=power,
                bess_efficiency=setup.get('bess_efficiency', 87),
                bess_min_soc=setup.get('bess_min_soc', 10),
                bess_max_soc=setup.get('bess_max_soc', 90),
                bess_initial_soc=setup.get('bess_initial_soc', 50),
                bess_daily_cycle_limit=setup.get('bess_daily_cycle_limit', 2.0),
                bess_enforce_cycle_limit=setup.get('bess_enforce_cycle_limit', False),
                dg_enabled=setup.get('dg_enabled', True),
                dg_capacity=setup.get('dg_capacity_mw', 30),
                dg_charges_bess=rules.get('dg_charges_bess', False),
                dg_load_priority=rules.get('dg_load_priority', 'bess_first'),
                dg_takeover_mode=rules.get('dg_takeover_mode', False),
                night_start_hour=rules.get('night_start', 18),
                night_end_hour=rules.get('night_end', 6),
                day_start_hour=rules.get('day_start', 6),
                day_end_hour=rules.get('day_end', 18),
                blackout_start_hour=rules.get('blackout_start', 0),
                blackout_end_hour=rules.get('blackout_end', 0),
                dg_soc_on_threshold=rules.get('soc_on_threshold', 30),
                dg_soc_off_threshold=rules.get('soc_off_threshold', 80),
                dg_fuel_curve_enabled=setup.get('dg_fuel_curve_enabled', False),
                dg_fuel_f0=setup.get('dg_fuel_f0', 0.03),
                dg_fuel_f1=setup.get('dg_fuel_f1', 0.22),
                dg_fuel_flat_rate=setup.get('dg_fuel_flat_rate', 0.25),
                cycle_charging_enabled=rules.get('cycle_charging_enabled', False),
                cycle_charging_min_load_pct=rules.get('cycle_charging_min_load_pct', 70.0),
                cycle_charging_off_soc=rules.get('cycle_charging_off_soc', 80.0),
            )

            # Run simulation
            template_id = rules.get('inferred_template', 'T1')
            hourly_results = run_simulation_func(params, template_id, num_hours=8760)
            metrics = calculate_metrics_func(hourly_results, params)

            duration_result = {
                'duration_hrs': duration,
                'power_mw': power,
                'power_sufficient': power_sufficient,
                'delivery_hours': metrics.hours_full_delivery,
                'delivery_pct': metrics.pct_full_delivery,
                'wastage_pct': metrics.pct_solar_curtailed,
                'dg_hours': metrics.dg_runtime_hours,
                'cycles': metrics.bess_equivalent_cycles,
                'green_hours': metrics.hours_green_delivery,
            }
            duration_results.append(duration_result)

        # Find best duration for this capacity (max delivery hours)
        if duration_results:
            best = max(duration_results, key=lambda x: x['delivery_hours'])

            capacity_result = {
                'capacity_mwh': capacity,
                'best_duration_hrs': best['duration_hrs'],
                'best_power_mw': best['power_mw'],
                'power_sufficient': best['power_sufficient'],
                'delivery_hours': best['delivery_hours'],
                'delivery_pct': best['delivery_pct'],
                'wastage_pct': best['wastage_pct'],
                'dg_hours': best['dg_hours'],
                'cycles': best['cycles'],
                'green_hours': best['green_hours'],
                'nameplate_mwh': capacity / (1 - factory_degradation),  # Nameplate to order
                'all_durations': duration_results,
            }

            all_capacity_results.append(capacity_result)
            capacity_best_configs[capacity] = capacity_result

    # ===========================================
    # PHASE 3: Filter and select top N
    # ===========================================
    # Filter capacities meeting target
    meeting_target = [r for r in all_capacity_results if r['delivery_pct'] >= target_delivery_pct]

    # Sort by capacity (smallest first)
    meeting_target_sorted = sorted(meeting_target, key=lambda x: x['capacity_mwh'])

    # Select top N smallest
    top_capacities = meeting_target_sorted[:top_n]

    # Add comparison metrics to alternatives
    if top_capacities:
        base = top_capacities[0]
        for i, cap in enumerate(top_capacities):
            if i == 0:
                cap['vs_smallest'] = None
            else:
                cap['vs_smallest'] = {
                    'extra_capacity_mwh': cap['capacity_mwh'] - base['capacity_mwh'],
                    'extra_delivery_pct': cap['delivery_pct'] - base['delivery_pct'],
                    'extra_delivery_hours': cap['delivery_hours'] - base['delivery_hours'],
                    'dg_hours_saved': base['dg_hours'] - cap['dg_hours'],
                }

    # ===========================================
    # PHASE 4: Calculate marginal analysis
    # ===========================================
    for i in range(1, len(all_capacity_results)):
        prev = all_capacity_results[i - 1]
        curr = all_capacity_results[i]
        delta_cap = curr['capacity_mwh'] - prev['capacity_mwh']
        delta_hours = curr['delivery_hours'] - prev['delivery_hours']
        curr['marginal_gain'] = delta_hours / delta_cap if delta_cap > 0 else 0

    if all_capacity_results:
        all_capacity_results[0]['marginal_gain'] = 0

    # ===========================================
    # Build summary
    # ===========================================
    scan_summary = {
        'total_capacities_tested': len(all_capacity_results),
        'capacities_meeting_target': len(meeting_target),
        'min_capacity_for_target': meeting_target_sorted[0]['capacity_mwh'] if meeting_target_sorted else None,
        'max_delivery_achieved': max(r['delivery_pct'] for r in all_capacity_results) if all_capacity_results else 0,
        'target_delivery_pct': target_delivery_pct,
    }

    return {
        'min_power_required': min_power_required,
        'solar_peak_mw': solar_peak_mw,
        'dg_takeover_mode': dg_takeover,
        'factory_degradation_pct': factory_degradation * 100,
        'top_capacities': top_capacities,
        'scan_summary': scan_summary,
        'all_capacity_results': all_capacity_results,
    }