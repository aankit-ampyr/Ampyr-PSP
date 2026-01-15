"""
Configuration manager for BESS system
Handles session state configuration with fallback to defaults
"""

import streamlit as st

# Import default configurations
from src.config import (
    TARGET_DELIVERY_MW, SOLAR_CAPACITY_MW,
    MIN_SOC, MAX_SOC, ROUND_TRIP_EFFICIENCY,
    C_RATE_CHARGE, C_RATE_DISCHARGE,
    MIN_BATTERY_SIZE_MWH, MAX_BATTERY_SIZE_MWH, BATTERY_SIZE_STEP_MWH,
    MARGINAL_IMPROVEMENT_THRESHOLD, MARGINAL_INCREMENT_MWH,
    DEGRADATION_PER_CYCLE, INITIAL_SOC,
    DG_CAPACITY_MW, DG_SOC_ON_THRESHOLD, DG_SOC_OFF_THRESHOLD, DG_LOAD_MW
)


def get_config(key=None):
    """
    Get configuration value from session state or default.

    Args:
        key: Specific configuration key to retrieve. If None, returns all config.

    Returns:
        Configuration value or dictionary of all configurations
    """
    # Initialize default configuration if not in session state
    if 'config' not in st.session_state:
        st.session_state.config = {
            # Project Parameters
            'TARGET_DELIVERY_MW': TARGET_DELIVERY_MW,
            'SOLAR_CAPACITY_MW': SOLAR_CAPACITY_MW,

            # Battery Technical Parameters
            'MIN_SOC': MIN_SOC,
            'MAX_SOC': MAX_SOC,
            'ROUND_TRIP_EFFICIENCY': ROUND_TRIP_EFFICIENCY,
            'ONE_WAY_EFFICIENCY': ROUND_TRIP_EFFICIENCY ** 0.5,
            'C_RATE_CHARGE': C_RATE_CHARGE,
            'C_RATE_DISCHARGE': C_RATE_DISCHARGE,

            # Battery Sizing Range
            'MIN_BATTERY_SIZE_MWH': MIN_BATTERY_SIZE_MWH,
            'MAX_BATTERY_SIZE_MWH': MAX_BATTERY_SIZE_MWH,
            'BATTERY_SIZE_STEP_MWH': BATTERY_SIZE_STEP_MWH,

            # Optimization Parameters
            'MARGINAL_IMPROVEMENT_THRESHOLD': MARGINAL_IMPROVEMENT_THRESHOLD,
            'MARGINAL_INCREMENT_MWH': MARGINAL_INCREMENT_MWH,

            # Degradation Parameters
            'DEGRADATION_PER_CYCLE': DEGRADATION_PER_CYCLE,

            # Operational Parameters
            'MAX_DAILY_CYCLES': 2.0,
            'INITIAL_SOC': INITIAL_SOC,

            # Diesel Generator Parameters
            'DG_CAPACITY_MW': DG_CAPACITY_MW,
            'DG_SOC_ON_THRESHOLD': DG_SOC_ON_THRESHOLD,
            'DG_SOC_OFF_THRESHOLD': DG_SOC_OFF_THRESHOLD,
            'DG_LOAD_MW': DG_LOAD_MW
        }

    if key:
        return st.session_state.config.get(key)
    return st.session_state.config


def update_config(key, value):
    """
    Update a configuration value in session state.

    Args:
        key: Configuration key to update
        value: New value for the configuration

    Raises:
        ValueError: If key is not a valid configuration parameter
        ValueError: If value is outside valid bounds for the parameter
    """
    if 'config' not in st.session_state:
        get_config()  # Initialize if needed

    # Validate key exists
    if key not in st.session_state.config:
        raise ValueError(f"Unknown configuration key: '{key}'. Valid keys: {list(st.session_state.config.keys())}")

    # Validate value bounds for known parameters
    validation_rules = {
        'MIN_SOC': (0, 1, "must be between 0 and 1"),
        'MAX_SOC': (0, 1, "must be between 0 and 1"),
        'ROUND_TRIP_EFFICIENCY': (0, 1, "must be between 0 and 1"),
        'ONE_WAY_EFFICIENCY': (0, 1, "must be between 0 and 1"),
        'C_RATE_CHARGE': (0, float('inf'), "must be positive"),
        'C_RATE_DISCHARGE': (0, float('inf'), "must be positive"),
        'MIN_BATTERY_SIZE_MWH': (0, float('inf'), "must be positive"),
        'MAX_BATTERY_SIZE_MWH': (0, float('inf'), "must be positive"),
        'BATTERY_SIZE_STEP_MWH': (0, float('inf'), "must be positive"),
        'TARGET_DELIVERY_MW': (0, float('inf'), "must be positive"),
        'SOLAR_CAPACITY_MW': (0, float('inf'), "must be positive"),
        'MAX_DAILY_CYCLES': (0, float('inf'), "must be positive"),
        'INITIAL_SOC': (0, 1, "must be between 0 and 1"),
        'DG_CAPACITY_MW': (0, float('inf'), "must be non-negative"),
        'DG_SOC_ON_THRESHOLD': (0, 1, "must be between 0 and 1"),
        'DG_SOC_OFF_THRESHOLD': (0, 1, "must be between 0 and 1"),
    }

    if key in validation_rules:
        min_val, max_val, msg = validation_rules[key]
        if not (min_val <= value <= max_val):
            raise ValueError(f"{key} {msg}, got {value}")

    st.session_state.config[key] = value

    # Update derived values if needed
    if key == 'ROUND_TRIP_EFFICIENCY':
        st.session_state.config['ONE_WAY_EFFICIENCY'] = value ** 0.5