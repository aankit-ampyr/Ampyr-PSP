"""
Data loader module for reading solar profile data
"""

import csv
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from .config import SOLAR_PROFILE_PATH


def _read_solar_csv_robust(file_path) -> np.ndarray:
    """Read column-1 numeric values from a solar profile CSV.

    Robust to both file conventions in `Inputs/`:
      - "Solar Profile.csv" / "Burton Solar Profile.csv": header row present
        (e.g. `timestamp,Solar_Generation_MW`), 8760 data rows underneath.
      - "Burton_Leonard_*.csv" (canonical D13 audit profiles, A14): NO header,
        8760 data rows total.

    The previous `pd.read_csv(...)` path defaulted to `header=0` and silently
    ate the first data row of the canonical files as a column header — see
    decisions log A27 + smoke test §13. This mirrors the dispatch-energy
    loader (`src/dispatch_energy.py::load_solar_profile`) which has always
    been robust to both conventions because it skips non-numeric rows.

    Returns: numpy array of float MW values from column index 1.
    Raises: nothing — caller checks result length / handles None upstream.
    """
    values = []
    with open(file_path, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                values.append(float(row[1]))
            except ValueError:
                # Header rows ("timestamp", "Solar_Generation_MW", etc.) or
                # other non-numeric content — skip silently.
                continue
    return np.array(values, dtype=float)

# Module logger
logger = logging.getLogger(__name__)

# Inputs folder path
INPUTS_FOLDER = Path("Inputs")


def get_active_solar_profile(setup: dict):
    """Return the canonical 8760-element solar profile array stored by Step 1.

    This is the single source of profile truth across the wizard. Step 1
    loads + validates + pads + caches the profile in
    `wizard['setup']['solar_profile_array']`. All downstream pages
    (Step 3, Step 3a, Step 4, Step 7) call this helper rather than
    re-loading from disk.

    Centralising this eliminates a class of bugs surfaced by the Step 3a
    smoke test loop (A24/A25/A26/A27): loader discrepancies, filename
    vs display-name protocol mismatches, row-count off-by-one rejections,
    and per-page rescaling drift. See decisions log A27.

    Args:
        setup: `wizard_state['setup']` dict.

    Returns:
        numpy array of 8760 hourly MW values, or None if Step 1 hasn't
        produced a valid profile yet. Callers should error loud on None.
    """
    arr = setup.get('solar_profile_array') if setup else None
    if arr is None:
        return None
    return np.asarray(arr, dtype=float)


def list_solar_profiles():
    """
    List all available solar profile CSV files in the Inputs folder.

    Returns:
        list: List of (filename, display_name) tuples for available solar profiles
    """
    profiles = []

    if not INPUTS_FOLDER.exists():
        return profiles

    # Find all CSV files that could be solar profiles. Match either:
    #   - "solar" anywhere in filename (e.g. "Solar Profile.csv", "Burton Solar Profile.csv")
    #   - "burton" anywhere in filename (e.g. "Burton_Leonard_82MWp_DC_58MW_AC.csv")
    # The latter covers the canonical D13/A14 audit profiles introduced in
    # May 2026 — they don't contain the word "solar" in their filename and
    # were previously hidden from the dropdown. See decisions log A24
    # smoke-test follow-up.
    for csv_file in INPUTS_FOLDER.glob("*.csv"):
        filename = csv_file.name
        lower = filename.lower()
        if 'solar' in lower or 'burton' in lower:
            # Create display name by removing .csv extension
            display_name = filename.replace('.csv', '')
            profiles.append((filename, display_name))

    # Sort alphabetically by display name
    profiles.sort(key=lambda x: x[1].lower())

    return profiles


def load_solar_profile_by_name(filename):
    """
    Load a specific solar profile from the Inputs folder.

    Accepts either a filename with `.csv` extension or a display name
    without (e.g. as stored by Step 1's wizard state). When the extension
    is missing, `.csv` is appended before attempting to open the file.
    See decisions log A26 — Step 1 stores display names; this loader is
    the safety net so Step 3 / Step 3a don't silently fall through to a
    default profile when the user explicitly picked a canonical one.

    Args:
        filename: Name of the CSV file (e.g., "Solar Profile.csv") or
            the display name without extension.

    Returns:
        numpy array: Hourly solar generation in MW for 8760 hours, or None if failed
    """
    if not filename.lower().endswith('.csv'):
        filename = filename + '.csv'
    file_path = INPUTS_FOLDER / filename

    # Security: Ensure the resolved path is within Inputs folder
    try:
        resolved_path = file_path.resolve()
        inputs_resolved = INPUTS_FOLDER.resolve()
        if not str(resolved_path).startswith(str(inputs_resolved)):
            logger.warning(f"Security: Path traversal attempt blocked for '{filename}'")
            return None
    except Exception as e:
        logger.error(f"Failed to resolve path for '{filename}': {e}")
        return None

    if not file_path.exists():
        return None

    try:
        solar_profile = _read_solar_csv_robust(file_path)

        if len(solar_profile) != 8760:
            try:
                import streamlit as st
                st.warning(f"⚠️ Solar profile has {len(solar_profile)} hours, expected 8760.")
            except ImportError:
                pass

        return solar_profile

    except Exception as e:
        logger.error(f"Failed to load solar profile '{filename}': {e}")
        try:
            import streamlit as st
            st.error(f"Failed to load solar profile: {str(e)}")
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
        solar_profile = _read_solar_csv_robust(file_path)

        if len(solar_profile) != 8760:
            try:
                import streamlit as st
                st.warning(f"⚠️ Solar profile has {len(solar_profile)} hours, expected 8760.")
            except ImportError:
                pass

        return solar_profile

    except Exception as e:
        logger.error(f"Failed to load default solar profile from '{file_path}': {e}")
        try:
            import streamlit as st
            st.error(f"Failed to load solar profile: {str(e)}")
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
    peak_mw = np.max(solar_profile)
    return {
        'max_mw': peak_mw,
        'min_mw': np.min(solar_profile),
        'mean_mw': np.mean(solar_profile),
        'total_mwh': np.sum(solar_profile),
        'capacity_factor': np.mean(solar_profile) / peak_mw if peak_mw > 0 else 0,
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