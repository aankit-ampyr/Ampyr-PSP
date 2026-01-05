"""
Load Profile Builder Module

Generates 8760-hour load profiles from user selections.
Supports constant, day-only, night-only, seasonal, custom windows, and CSV upload.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd


# =============================================================================
# MONTH CONSTANTS
# =============================================================================

# Month boundaries (day of year, 1-indexed, non-leap year)
MONTH_DAY_START = {
    1: 1, 2: 32, 3: 60, 4: 91, 5: 121, 6: 152,
    7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335
}

MONTH_DAY_END = {
    1: 31, 2: 59, 3: 90, 4: 120, 5: 151, 6: 181,
    7: 212, 8: 243, 9: 273, 10: 304, 11: 334, 12: 365
}

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

MONTH_NAMES_FULL = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']


# =============================================================================
# LOAD PROFILE GENERATION
# =============================================================================

def build_load_profile(
    mode: str,
    params: Dict[str, Any],
    num_hours: int = 8760
) -> np.ndarray:
    """
    Generate load profile based on mode and parameters.

    Args:
        mode: Load profile mode
            - 'constant': Fixed MW all hours
            - 'day_only': MW during day hours, 0 at night
            - 'night_only': MW during night hours, 0 during day
            - 'seasonal': MW during specific months and daily time window
            - 'custom': User-defined time windows
            - 'csv': Load from uploaded data
        params: Mode-specific parameters
            - mw: Load value in MW (for constant/day_only/night_only/seasonal)
            - start: Start hour (for day_only/night_only)
            - end: End hour (for day_only/night_only)
            - start_month: Start month 1-12 (for seasonal)
            - end_month: End month 1-12 (for seasonal)
            - day_start: Daily start hour 0-23 (for seasonal)
            - day_end: Daily end hour 0-23, 0=midnight (for seasonal)
            - windows: List of {start, end, mw} dicts (for custom)
            - data: numpy array (for csv)
        num_hours: Number of hours to generate (default 8760)

    Returns:
        numpy array of hourly load values (MW)

    Examples:
        >>> build_load_profile('constant', {'mw': 25})
        array([25., 25., 25., ...])  # 8760 values

        >>> build_load_profile('day_only', {'mw': 25, 'start': 6, 'end': 18})
        array([0., 0., 0., 0., 0., 0., 25., 25., ...])

        >>> build_load_profile('seasonal', {'mw': 25, 'start_month': 4, 'end_month': 10, 'day_start': 8, 'day_end': 0})
        # 25 MW from April to October, 8 AM to midnight daily
    """
    load = np.zeros(num_hours)

    if mode == 'constant':
        mw = params.get('mw', 25.0)
        load[:] = mw

    elif mode == 'day_only':
        mw = params.get('mw', 25.0)
        start = params.get('start', 6)
        end = params.get('end', 18)

        for hour in range(num_hours):
            hour_of_day = hour % 24
            if _is_in_range(hour_of_day, start, end):
                load[hour] = mw

    elif mode == 'night_only':
        mw = params.get('mw', 25.0)
        start = params.get('start', 18)
        end = params.get('end', 6)

        for hour in range(num_hours):
            hour_of_day = hour % 24
            if _is_in_range(hour_of_day, start, end):
                load[hour] = mw

    elif mode == 'seasonal':
        mw = params.get('mw', 25.0)
        start_month = params.get('start_month', 4)   # Default April
        end_month = params.get('end_month', 10)      # Default October
        day_start = params.get('day_start', 8)       # Default 8 AM
        day_end = params.get('day_end', 0)           # Default midnight (0)

        # Normalize midnight: 0 means end of day (24:00)
        effective_day_end = 24 if day_end == 0 else day_end

        for hour in range(num_hours):
            day_of_year = (hour // 24) + 1  # 1-365
            hour_of_day = hour % 24         # 0-23

            # Check if in active month range AND active time window
            if _is_in_month_range(day_of_year, start_month, end_month):
                if _is_in_range(hour_of_day, day_start, effective_day_end):
                    load[hour] = mw

    elif mode == 'custom':
        windows = params.get('windows', [])
        for window in windows:
            start = window.get('start', 0)
            end = window.get('end', 24)
            mw = window.get('mw', 0)

            for hour in range(num_hours):
                hour_of_day = hour % 24
                if _is_in_range(hour_of_day, start, end):
                    load[hour] = mw

    elif mode == 'csv':
        data = params.get('data')
        if data is not None:
            # Handle different input lengths
            if len(data) >= num_hours:
                load = np.array(data[:num_hours])
            else:
                # Repeat pattern to fill year
                repeats = (num_hours // len(data)) + 1
                load = np.tile(data, repeats)[:num_hours]

    return load


def _is_in_range(hour: int, start: int, end: int) -> bool:
    """
    Check if hour is within range, handling midnight wraparound.

    Args:
        hour: Hour to check (0-23)
        start: Start hour
        end: End hour

    Returns:
        True if hour is in range
    """
    if start < end:
        # Normal range (e.g., 6-18)
        return start <= hour < end
    elif start > end:
        # Crosses midnight (e.g., 18-6)
        return hour >= start or hour < end
    else:
        # start == end means no hours
        return False


def _is_in_month_range(day_of_year: int, start_month: int, end_month: int) -> bool:
    """
    Check if day_of_year falls within the month range.

    Args:
        day_of_year: Day of year (1-365)
        start_month: Start month (1-12)
        end_month: End month (1-12)

    Returns:
        True if day is in range

    Handles wraparound (e.g., October to March crossing year boundary).
    """
    start_day = MONTH_DAY_START[start_month]
    end_day = MONTH_DAY_END[end_month]

    if start_month <= end_month:
        # Normal range (e.g., April to October)
        return start_day <= day_of_year <= end_day
    else:
        # Crosses year boundary (e.g., October to March)
        return day_of_year >= start_day or day_of_year <= end_day


def calculate_seasonal_stats(start_month: int, end_month: int,
                             day_start: int, day_end: int) -> Dict[str, Any]:
    """
    Calculate statistics for a seasonal pattern preview.

    Args:
        start_month: Start month (1-12)
        end_month: End month (1-12)
        day_start: Daily start hour (0-23)
        day_end: Daily end hour (0-23, 0 = midnight)

    Returns:
        Dict with active_months, hours_per_day, total_active_hours, description
    """
    # Count active months
    if start_month <= end_month:
        active_months = end_month - start_month + 1
    else:
        active_months = (12 - start_month + 1) + end_month

    # Count active hours per day
    effective_end = 24 if day_end == 0 else day_end
    if day_start < effective_end:
        hours_per_day = effective_end - day_start
    else:
        # Crosses midnight (e.g., 22:00 to 06:00)
        hours_per_day = (24 - day_start) + effective_end

    # Calculate total active days using actual month day counts
    total_days = 0
    if start_month <= end_month:
        # Normal range (e.g., March to October)
        for month in range(start_month, end_month + 1):
            days_in_month = MONTH_DAY_END[month] - MONTH_DAY_START[month] + 1
            total_days += days_in_month
    else:
        # Crosses year boundary (e.g., October to March)
        for month in range(start_month, 13):  # start_month to December
            days_in_month = MONTH_DAY_END[month] - MONTH_DAY_START[month] + 1
            total_days += days_in_month
        for month in range(1, end_month + 1):  # January to end_month
            days_in_month = MONTH_DAY_END[month] - MONTH_DAY_START[month] + 1
            total_days += days_in_month

    total_active_hours = total_days * hours_per_day

    return {
        'active_months': active_months,
        'hours_per_day': hours_per_day,
        'total_days': total_days,
        'total_active_hours': total_active_hours,
        'description': f"{active_months} months, {hours_per_day} hrs/day ({total_active_hours:,} hrs/yr)"
    }


# =============================================================================
# LOAD PROFILE ANALYSIS
# =============================================================================

def analyze_load_profile(load: np.ndarray) -> Dict[str, Any]:
    """
    Analyze a load profile and return statistics.

    Args:
        load: Hourly load values (MW)

    Returns:
        Dictionary with statistics
    """
    # Handle empty or zero profiles
    if len(load) == 0:
        return {
            'total_energy_mwh': 0,
            'peak_mw': 0,
            'min_mw': 0,
            'avg_mw': 0,
            'load_hours': 0,
            'no_load_hours': 0,
            'load_factor': 0,
            'daily_pattern': np.zeros(24),
        }

    # Basic statistics
    total_energy = np.sum(load)
    peak = np.max(load)
    min_load = np.min(load)
    avg = np.mean(load)

    # Count hours
    load_hours = np.sum(load > 0)
    no_load_hours = len(load) - load_hours

    # Load factor
    load_factor = (avg / peak * 100) if peak > 0 else 0

    # Daily pattern (average by hour of day)
    hours = np.arange(len(load)) % 24
    daily_pattern = np.zeros(24)
    for h in range(24):
        mask = hours == h
        if np.any(mask):
            daily_pattern[h] = np.mean(load[mask])

    return {
        'total_energy_mwh': float(total_energy),
        'peak_mw': float(peak),
        'min_mw': float(min_load),
        'avg_mw': float(avg),
        'load_hours': int(load_hours),
        'no_load_hours': int(no_load_hours),
        'load_factor': float(load_factor),
        'daily_pattern': daily_pattern,
    }


def get_load_sparkline_data(load: np.ndarray, num_points: int = 24) -> List[float]:
    """
    Get simplified data for sparkline visualization.

    Args:
        load: Hourly load values
        num_points: Number of points for sparkline

    Returns:
        List of values for sparkline
    """
    if len(load) == 0:
        return [0] * num_points

    # Average by hour of day for a typical day pattern
    hours = np.arange(len(load)) % 24
    daily_avg = []
    for h in range(24):
        mask = hours == h
        if np.any(mask):
            daily_avg.append(np.mean(load[mask]))
        else:
            daily_avg.append(0)

    return daily_avg


def validate_load_csv(df: pd.DataFrame) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Validate uploaded load CSV file.

    Args:
        df: Pandas DataFrame from uploaded CSV

    Returns:
        Tuple of (is_valid, message, data_array)
    """
    # Check if DataFrame is empty
    if df.empty:
        return False, "CSV file is empty", None

    # Look for load column (case-insensitive)
    load_column = None
    for col in df.columns:
        if col.lower() in ['load', 'load_mw', 'demand', 'demand_mw', 'mw', 'power']:
            load_column = col
            break

    # If no named column, use first numeric column
    if load_column is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            load_column = numeric_cols[0]
        else:
            return False, "No numeric data found in CSV", None

    # Extract data
    data = df[load_column].values

    # Validate values
    if np.any(np.isnan(data)):
        return False, "CSV contains missing values (NaN)", None

    if np.any(data < 0):
        return False, "Load values cannot be negative", None

    # Check length
    if len(data) < 24:
        return False, f"CSV must have at least 24 rows (got {len(data)})", None

    if len(data) < 8760:
        msg = f"CSV has {len(data)} rows. Will repeat pattern to fill year."
        return True, msg, data

    if len(data) > 8760:
        msg = f"CSV has {len(data)} rows. Will use first 8760."
        return True, msg, data[:8760]

    return True, f"Valid load profile: {len(data)} hours", data


def validate_solar_csv(df: pd.DataFrame) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Validate uploaded solar profile CSV file.

    Args:
        df: Pandas DataFrame from uploaded CSV

    Returns:
        Tuple of (is_valid, message, data_array)
    """
    # Check if DataFrame is empty
    if df.empty:
        return False, "CSV file is empty", None

    # Look for solar column (case-insensitive)
    solar_column = None
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['solar', 'generation', 'pv', 'mw', 'power', 'output']):
            solar_column = col
            break

    # If no named column, use first numeric column (skip datetime if present)
    if solar_column is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            solar_column = numeric_cols[0]
        else:
            return False, "No numeric data found in CSV", None

    # Extract data
    data = df[solar_column].values.astype(float)

    # Validate values
    if np.any(np.isnan(data)):
        return False, "CSV contains missing values (NaN)", None

    if np.any(data < 0):
        return False, "Solar generation values cannot be negative", None

    # Check length
    if len(data) < 24:
        return False, f"CSV must have at least 24 rows (got {len(data)})", None

    if len(data) < 8760:
        msg = f"CSV has {len(data)} rows. Will repeat pattern to fill year."
        # Repeat pattern to fill year
        repeats = (8760 // len(data)) + 1
        data = np.tile(data, repeats)[:8760]
        return True, msg, data

    if len(data) > 8760:
        msg = f"CSV has {len(data)} rows. Will use first 8760."
        return True, msg, data[:8760]

    return True, f"Valid solar profile: {len(data)} hours", data


def analyze_solar_profile(solar: np.ndarray) -> Dict[str, Any]:
    """
    Calculate statistics for a solar profile.

    Args:
        solar: Hourly solar generation array (MW)

    Returns:
        Dictionary with statistics
    """
    return {
        'total_generation_mwh': float(np.sum(solar)),
        'peak_mw': float(np.max(solar)),
        'mean_mw': float(np.mean(solar)),
        'generation_hours': int(np.sum(solar > 0)),
        'zero_hours': int(np.sum(solar == 0)),
        'capacity_factor': float(np.mean(solar) / np.max(solar)) if np.max(solar) > 0 else 0,
    }


# =============================================================================
# PRESET LOAD PROFILES
# =============================================================================

LOAD_PRESETS = {
    'constant_25mw': {
        'name': 'Constant 25 MW',
        'description': '25 MW load 24/7',
        'mode': 'constant',
        'params': {'mw': 25.0}
    },
    'constant_50mw': {
        'name': 'Constant 50 MW',
        'description': '50 MW load 24/7',
        'mode': 'constant',
        'params': {'mw': 50.0}
    },
    'office_hours': {
        'name': 'Office Hours',
        'description': '25 MW from 8:00 to 18:00',
        'mode': 'day_only',
        'params': {'mw': 25.0, 'start': 8, 'end': 18}
    },
    'evening_peak': {
        'name': 'Evening Peak',
        'description': '25 MW from 17:00 to 23:00',
        'mode': 'custom',
        'params': {'windows': [{'start': 17, 'end': 23, 'mw': 25.0}]}
    },
    'night_operations': {
        'name': 'Night Operations',
        'description': '25 MW from 18:00 to 6:00',
        'mode': 'night_only',
        'params': {'mw': 25.0, 'start': 18, 'end': 6}
    },
    'two_shift': {
        'name': 'Two Shift',
        'description': '25 MW morning (6-14) and evening (14-22)',
        'mode': 'custom',
        'params': {'windows': [
            {'start': 6, 'end': 14, 'mw': 25.0},
            {'start': 14, 'end': 22, 'mw': 25.0}
        ]}
    },
}


def get_preset_load_profile(preset_name: str, num_hours: int = 8760) -> np.ndarray:
    """
    Get a preset load profile by name.

    Args:
        preset_name: Name of the preset
        num_hours: Number of hours to generate

    Returns:
        numpy array of hourly load values
    """
    if preset_name not in LOAD_PRESETS:
        # Default to constant 25 MW
        return build_load_profile('constant', {'mw': 25.0}, num_hours)

    preset = LOAD_PRESETS[preset_name]
    return build_load_profile(preset['mode'], preset['params'], num_hours)


# =============================================================================
# VISUALIZATION HELPERS
# =============================================================================

def create_load_preview_chart_data(load: np.ndarray) -> Dict[str, Any]:
    """
    Create data for load preview chart.

    Args:
        load: Hourly load values

    Returns:
        Dict with chart data
    """
    # Get typical day pattern
    hours = np.arange(len(load)) % 24

    # Calculate hourly averages
    hourly_avg = []
    hourly_min = []
    hourly_max = []

    for h in range(24):
        mask = hours == h
        if np.any(mask):
            hourly_avg.append(np.mean(load[mask]))
            hourly_min.append(np.min(load[mask]))
            hourly_max.append(np.max(load[mask]))
        else:
            hourly_avg.append(0)
            hourly_min.append(0)
            hourly_max.append(0)

    return {
        'hours': list(range(24)),
        'avg': hourly_avg,
        'min': hourly_min,
        'max': hourly_max,
    }


def format_energy(mwh: float) -> str:
    """Format energy value with appropriate units."""
    if mwh >= 1000000:
        return f"{mwh/1000000:.1f} TWh"
    elif mwh >= 1000:
        return f"{mwh/1000:.1f} GWh"
    else:
        return f"{mwh:.0f} MWh"
