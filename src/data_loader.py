"""
Data loader module for reading solar profile data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from .config import SOLAR_PROFILE_PATH

def load_solar_profile(file_path=None):
    """
    Load solar generation profile from CSV file.

    Args:
        file_path: Optional path to solar profile CSV. Uses default if None.

    Returns:
        numpy array: Hourly solar generation in MW for 8760 hours
    """
    if file_path is None:
        file_path = SOLAR_PROFILE_PATH

    try:
        # Read CSV file
        df = pd.read_csv(file_path)

        # Extract solar generation column
        # Assuming column name contains 'Solar' or 'Generation' or 'MW'
        solar_column = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['solar', 'generation', 'mw']):
                solar_column = col
                break

        if solar_column is None:
            # If no matching column found, use the second column (first is usually datetime)
            if len(df.columns) > 1:
                solar_column = df.columns[1]
            else:
                solar_column = df.columns[0]

        solar_profile = df[solar_column].values

        # Ensure we have 8760 values
        if len(solar_profile) != 8760:
            print(f"Warning: Solar profile has {len(solar_profile)} hours, expected 8760")

        return solar_profile

    except Exception as e:
        print(f"Error loading solar profile: {e}")
        # Return synthetic profile if file cannot be loaded
        return generate_synthetic_solar_profile()

def generate_synthetic_solar_profile():
    """
    Generate a synthetic solar profile for testing purposes.

    Returns:
        numpy array: Synthetic hourly solar generation for 8760 hours
    """
    hours = np.arange(8760)
    days = hours // 24
    hour_of_day = hours % 24

    # Simple solar pattern: zero at night, peak at noon
    solar_profile = np.zeros(8760)

    for i in range(8760):
        h = hour_of_day[i]
        d = days[i]

        # Solar generation only between 6 AM and 6 PM
        if 6 <= h <= 18:
            # Peak at noon (12:00)
            peak_factor = 1 - abs(h - 12) / 6
            # Seasonal variation
            seasonal_factor = 0.7 + 0.3 * np.sin(2 * np.pi * d / 365)
            # Random cloud cover
            weather_factor = 0.5 + 0.5 * np.random.random()

            solar_profile[i] = 67 * peak_factor * seasonal_factor * weather_factor

    return solar_profile

def get_solar_statistics(solar_profile):
    """
    Calculate statistics for solar profile.

    Args:
        solar_profile: numpy array of hourly solar generation

    Returns:
        dict: Statistics including max, min, mean, total
    """
    return {
        'max_mw': np.max(solar_profile),
        'min_mw': np.min(solar_profile),
        'mean_mw': np.mean(solar_profile),
        'total_mwh': np.sum(solar_profile),
        'capacity_factor': np.mean(solar_profile) / 67.0,
        'zero_hours': np.sum(solar_profile == 0)
    }