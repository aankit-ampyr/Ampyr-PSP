"""
Data loader module for reading solar profile data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from .config import SOLAR_PROFILE_PATH
from utils.logger import get_logger

# Set up module logger
logger = get_logger(__name__)

def load_solar_profile(file_path=None):
    """
    Load solar generation profile from CSV file.

    Security: Only loads from default path to prevent path traversal attacks.
    For custom file uploads, use a separate upload handler function.

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
            f"For custom uploads, use load_solar_profile_from_upload() instead."
        )

    file_path = SOLAR_PROFILE_PATH

    try:
        # Read CSV file (validated to default path only)
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
            warning_msg = f"Solar profile has {len(solar_profile)} hours, expected 8760. Results may be inaccurate."
            logger.warning(warning_msg)

            try:
                import streamlit as st
                st.warning(f"⚠️ {warning_msg}")
            except ImportError:
                pass  # Logger already handled the warning

        return solar_profile

    except Exception as e:
        # Log the error
        logger.error(f"Failed to load solar profile: {str(e)}")
        logger.error(f"Solar profile file '{SOLAR_PROFILE_PATH}' is required")

        # Show user-visible error messages in Streamlit UI
        try:
            import streamlit as st
            st.error(f"❌ Failed to load solar profile: {str(e)}")
            st.error("⚠️ Solar profile file is required to run simulations")
            st.info(f"📝 Please ensure '{SOLAR_PROFILE_PATH}' exists with 8760 hourly values")
            st.info("📤 Future versions will support uploading custom solar profile files")
        except ImportError:
            pass  # Logger already handled the error

        # Return None - caller must handle missing solar profile
        return None

def generate_synthetic_solar_profile():
    """
    ⚠️ DEPRECATED: This function is deprecated and should only be used for unit testing.

    Generate a synthetic solar profile for testing purposes.
    Production code should NOT use this function - real solar data is required.

    Returns:
        numpy array: Synthetic hourly solar generation for 8760 hours
    """
    import warnings
    warnings.warn(
        "generate_synthetic_solar_profile() is deprecated. "
        "Use real solar profile data. This function should only be used in unit tests.",
        DeprecationWarning,
        stacklevel=2
    )
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