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
        'Delivery Rate (%)': round(simulation_results['hours_delivered'] / (HOURS_PER_YEAR / 100), 1),
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
    primary_metric='delivery_hours',
    top_n=5
):
    """
    Calculate ranked recommendations with single best + alternatives.

    Args:
        results_df: DataFrame with simulation results
        primary_metric: Column name to optimize (default: 'delivery_hours')
        top_n: Number of alternatives to include

    Returns:
        dict: {
            'recommended': {...config details, reasoning...},
            'alternatives': [{rank, config, vs_recommended}...],
            'all_ranked': list,
            'marginal_analysis': list,
            'selection_method': str
        }
    """
    if results_df is None or len(results_df) == 0:
        return None

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
        'bess_cycles': ['bess_cycles', 'Total Cycles', 'total_cycles'],
        'wastage_pct': ['wastage_pct', 'Wastage (%)', 'Solar Wastage (%)'],
    }

    # Find actual column names
    def find_col(key):
        for possible in col_mapping.get(key, [key]):
            if possible in df.columns:
                return possible
        return key

    delivery_col = find_col('delivery_hours')
    bess_col = find_col('bess_mwh')
    duration_col = find_col('duration_hrs')
    dg_col = find_col('dg_mw')
    cycles_col = find_col('bess_cycles')
    wastage_col = find_col('wastage_pct')
    delivery_pct_col = find_col('delivery_pct')

    # Sort by primary metric (descending for delivery hours)
    df_sorted = df.sort_values(by=delivery_col, ascending=False).reset_index(drop=True)

    # Recommended is the one with max delivery hours
    rec_row = df_sorted.iloc[0]
    rec_idx = 0

    # Build recommended config dict
    recommended = {
        'index': rec_idx,
        'bess_mwh': float(rec_row.get(bess_col, 0)),
        'duration_hrs': int(rec_row.get(duration_col, 0)) if duration_col in rec_row else 0,
        'power_mw': float(rec_row.get('power_mw', rec_row.get(bess_col, 0) / max(rec_row.get(duration_col, 1), 1))),
        'dg_mw': float(rec_row.get(dg_col, 0)) if dg_col in rec_row.index else 0,
        'delivery_hours': int(rec_row.get(delivery_col, 0)),
        'delivery_pct': float(rec_row.get(delivery_pct_col, 0)),
        'total_cycles': float(rec_row.get(cycles_col, 0)) if cycles_col in rec_row.index else 0,
        'wastage_pct': float(rec_row.get(wastage_col, 0)) if wastage_col in rec_row.index else 0,
        'reasoning': 'Highest delivery hours among all configurations tested',
    }

    # Calculate degradation estimate
    if recommended['total_cycles'] > 0:
        recommended['degradation_pct'] = recommended['total_cycles'] * 0.0015 * 100
    else:
        recommended['degradation_pct'] = 0

    # Build alternatives list (excluding recommended)
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
            'vs_recommended': {
                'hours_diff': hours_diff,
                'pct_diff': (hours_diff / recommended['delivery_hours'] * 100
                            if recommended['delivery_hours'] > 0 else 0),
                'cost_diff_pct': cost_diff_pct
            }
        })

    # Calculate marginal analysis (for size-based analysis)
    marginal_analysis = []
    if bess_col in df.columns:
        # Sort by BESS size for marginal analysis
        df_by_size = df.sort_values(by=bess_col).reset_index(drop=True)

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

    # All ranked (for table display)
    all_ranked = []
    for rank, (idx, row) in enumerate(df_sorted.iterrows(), start=1):
        all_ranked.append({
            'rank': rank,
            'bess_mwh': float(row.get(bess_col, 0)),
            'delivery_hours': int(row.get(delivery_col, 0)),
            'delivery_pct': float(row.get(delivery_pct_col, 0)),
        })

    return {
        'recommended': recommended,
        'alternatives': alternatives,
        'all_ranked': all_ranked,
        'marginal_analysis': marginal_analysis,
        'selection_method': 'max_delivery_hours',
        'total_configs_tested': len(df)
    }


def calculate_simulation_params(min_size, max_size, step_size, max_simulations=None):
    """
    Calculate simulation parameters with auto-adjustment for resource limits.

    Args:
        min_size: Minimum battery size (MWh)
        max_size: Maximum battery size (MWh)
        step_size: Step size between simulations (MWh)
        max_simulations: Maximum allowed simulations (defaults to MAX_SIMULATIONS)

    Returns:
        dict: {
            'num_simulations': int - Number of simulations to run
            'actual_step_size': int - Adjusted step size
            'was_adjusted': bool - Whether step size was auto-adjusted
            'battery_sizes': list - List of battery sizes to test
        }
    """
    if max_simulations is None:
        max_simulations = MAX_SIMULATIONS

    num_simulations = len(list(range(min_size, max_size + step_size, step_size)))
    actual_step_size = step_size
    was_adjusted = False

    if num_simulations > max_simulations:
        # Auto-adjust step size to cap at max_simulations
        actual_step_size = (max_size - min_size) // max_simulations + 1
        was_adjusted = True

    battery_sizes = list(range(min_size, max_size + actual_step_size, actual_step_size))
    num_simulations = len(battery_sizes)

    return {
        'num_simulations': num_simulations,
        'actual_step_size': actual_step_size,
        'was_adjusted': was_adjusted,
        'original_step_size': step_size,
        'battery_sizes': battery_sizes
    }