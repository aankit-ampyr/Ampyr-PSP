"""
Data loader module for reading solar profile data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from .config import SOLAR_PROFILE_PATH

# Inputs folder path
INPUTS_FOLDER = Path("Inputs")


def list_solar_profiles():
    """
    List all available solar profile CSV files in the Inputs folder.

    Returns:
        list: List of (filename, display_name) tuples for available solar profiles
    """
    profiles = []

    if not INPUTS_FOLDER.exists():
        return profiles

    # Find all CSV files that could be solar profiles
    for csv_file in INPUTS_FOLDER.glob("*.csv"):
        filename = csv_file.name
        # Check if it's likely a solar profile (contains 'solar' in name, case-insensitive)
        if 'solar' in filename.lower():
            # Create display name by removing .csv extension
            display_name = filename.replace('.csv', '')
            profiles.append((filename, display_name))

    # Sort alphabetically by display name
    profiles.sort(key=lambda x: x[1].lower())

    return profiles


def load_solar_profile_by_name(filename):
    """
    Load a specific solar profile from the Inputs folder.

    Args:
        filename: Name of the CSV file (e.g., "Solar Profile.csv")

    Returns:
        numpy array: Hourly solar generation in MW for 8760 hours, or None if failed
    """
    file_path = INPUTS_FOLDER / filename

    # Security: Ensure the resolved path is within Inputs folder
    try:
        resolved_path = file_path.resolve()
        inputs_resolved = INPUTS_FOLDER.resolve()
        if not str(resolved_path).startswith(str(inputs_resolved)):
            return None
    except Exception:
        return None

    if not file_path.exists():
        return None

    try:
        df = pd.read_csv(file_path)

        # Extract solar generation column
        solar_column = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['solar', 'generation', 'mw']):
                solar_column = col
                break

        if solar_column is None:
            if len(df.columns) > 1:
                solar_column = df.columns[1]
            else:
                solar_column = df.columns[0]

        solar_profile = df[solar_column].values

        if len(solar_profile) != 8760:
            try:
                import streamlit as st
                st.warning(f"⚠️ Solar profile has {len(solar_profile)} hours, expected 8760.")
            except ImportError:
                pass

        return solar_profile

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"❌ Failed to load solar profile: {str(e)}")
        except ImportError:
            pass
        return None


def load_solar_profile(file_path=None):
    """
    Load solar generation profile from default CSV file.

    Security: Only loads from default path to prevent path traversal attacks.
    For custom file uploads, use load_solar_profile_by_name() instead.

    Args:
        file_path: Optional path to solar profile CSV. Must be None or default path.
                   Custom paths are rejected for security.

    Returns:
        numpy array: Hourly solar generation in MW for 8760 hours

    Raises:
        ValueError: If custom file path is provided (security violation)
    """
    # Security fix: Only allow default path to prevent path traversal attacks
    if file_path is not None and file_path != SOLAR_PROFILE_PATH:
        raise ValueError(
            f"Security: Custom file paths not allowed. "
            f"Only default solar profile can be loaded via this function. "
            f"For custom uploads, use load_solar_profile_by_name() instead."
        )

    file_path = SOLAR_PROFILE_PATH

    try:
        df = pd.read_csv(file_path)

        # Extract solar generation column
        solar_column = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['solar', 'generation', 'mw']):
                solar_column = col
                break

        if solar_column is None:
            if len(df.columns) > 1:
                solar_column = df.columns[1]
            else:
                solar_column = df.columns[0]

        solar_profile = df[solar_column].values

        if len(solar_profile) != 8760:
            try:
                import streamlit as st
                st.warning(f"⚠️ Solar profile has {len(solar_profile)} hours, expected 8760.")
            except ImportError:
                pass

        return solar_profile

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"❌ Failed to load solar profile: {str(e)}")
        except ImportError:
            pass

        return None


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


def scale_solar_profile(base_profile, base_capacity_mw, target_capacity_mw):
    """
    Scale solar profile to different capacity while maintaining shape.

    This function proportionally scales a solar generation profile from one
    capacity to another, preserving the temporal pattern while adjusting
    the magnitude.

    Args:
        base_profile: Original 8760-hour solar profile (MW) - list or numpy array
        base_capacity_mw: Peak capacity of base profile (e.g., 67.9)
        target_capacity_mw: Desired peak capacity (e.g., 100.0)

    Returns:
        list: Scaled profile with target capacity

    Raises:
        ValueError: If base_capacity_mw is not positive

    Example:
        >>> base = [33.95, 67.9, 50.0, ...]  # 67.9 MW peak
        >>> scaled = scale_solar_profile(base, 67.9, 100.0)
        >>> # Returns [50.0, 100.0, 73.6, ...]  # 100 MW peak
    """
    if base_capacity_mw <= 0:
        raise ValueError("Base capacity must be positive")

    scaling_factor = target_capacity_mw / base_capacity_mw
    scaled_profile = [hour * scaling_factor for hour in base_profile]

    return scaled_profile


def get_base_solar_peak_capacity(profile):
    """
    Get peak capacity of solar profile.

    Args:
        profile: Solar profile (MW) - list or numpy array

    Returns:
        float: Peak MW generation

    Example:
        >>> profile = [10.5, 45.2, 67.9, 23.1, ...]
        >>> get_base_solar_peak_capacity(profile)
        67.9
    """
    if profile is None:
        return 0.0
    if hasattr(profile, '__len__') and len(profile) == 0:
        return 0.0
    return float(max(profile))