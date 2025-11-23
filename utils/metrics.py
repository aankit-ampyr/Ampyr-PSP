"""
Metrics calculation utilities for BESS sizing analysis
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.config import (
    MARGINAL_IMPROVEMENT_THRESHOLD,
    MARGINAL_INCREMENT_MWH,
    BATTERY_SIZE_STEP_MWH,
    HOURS_PER_YEAR
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
    optimal_result = next(r for r in all_results if r['Battery Size (MWh)'] == optimal_size)

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

    # Create date column (assuming simulation starts from Jan 1, 2024)
    import datetime
    start_date = datetime.date(2024, 1, 1)
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


def calculate_daily_statistics(hourly_df):
    """
    Calculate daily statistics from hourly data.

    Args:
        hourly_df: DataFrame with hourly data

    Returns:
        pd.DataFrame: Daily statistics
    """
    daily_stats = hourly_df.groupby('Day').agg({
        'Solar Generation (MW)': 'sum',
        'Power Delivered (MW)': 'sum',
        'Battery Charge (MW)': 'sum',
        'Battery Discharge (MW)': 'sum'
    }).round(1)

    # Add delivery hours per day
    daily_delivery = hourly_df[hourly_df['Power Delivered (MW)'] > 0].groupby('Day').size()
    daily_stats['Delivery Hours'] = daily_delivery.fillna(0)

    return daily_stats


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