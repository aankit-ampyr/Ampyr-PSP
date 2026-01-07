"""
Wizard State Manager

Centralizes all state management for the new wizard UI.
Provides initialization, validation, and persistence for wizard steps.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from copy import deepcopy


# =============================================================================
# DEFAULT STATE DEFINITIONS
# =============================================================================

DEFAULT_WIZARD_STATE = {
    # Current step (1-4)
    'current_step': 1,
    'max_completed_step': 0,

    # Step 1: System Setup
    'setup': {
        # Load profile
        'load_mode': 'constant',  # 'constant', 'day_only', 'night_only', 'custom', 'csv'
        'load_mw': 25.0,
        'load_day_start': 6,
        'load_day_end': 18,
        'load_night_start': 18,
        'load_night_end': 6,
        'load_windows': [],  # List of {'start': int, 'end': int, 'mw': float}
        'load_csv_data': None,  # numpy array if CSV uploaded

        # Seasonal load pattern
        'load_season_start': 4,      # Start month (1-12), default April
        'load_season_end': 10,       # End month (1-12), default October
        'load_season_day_start': 8,  # Daily start hour (0-23)
        'load_season_day_end': 0,    # Daily end hour (0-23, 0 = midnight)

        # Solar profile
        'solar_capacity_mw': 100.0,
        'solar_source': 'default',  # 'default' or 'uploaded'
        'solar_csv_data': None,  # numpy array if CSV uploaded

        # BESS parameters
        'bess_container_types': ['5mwh_2.5mw', '5mwh_1.25mw'],  # List of container types to evaluate
        'bess_efficiency': 87.0,  # %
        'bess_min_soc': 5.0,  # %
        'bess_max_soc': 95.0,  # %
        'bess_initial_soc': 50.0,  # %
        'bess_daily_cycle_limit': 1.0,
        'bess_enforce_cycle_limit': False,

        # DG enabled
        'dg_enabled': True,
        'dg_operating_mode': 'binary',  # 'binary' (100% or off) or 'variable' (above min load)
        'dg_min_load_pct': 30.0,  # % (only used when operating_mode is 'variable')

        # Degradation Strategy
        'degradation_strategy': 'standard',  # 'standard', 'overbuild', 'augmentation'
        'overbuild_factor': 0.20,  # 20% overbuild factor
        'augmentation_year': 8,  # Year to add capacity
        'calendar_degradation_rate': 0.02,  # 2% per year
        'use_rainflow_counting': True,  # Use advanced cycle counting
        'include_calendar_aging': True,  # Include calendar degradation

        # Fuel Model (Advanced DG)
        'dg_fuel_curve_enabled': False,  # Use advanced Willans line model
        'dg_fuel_f0': 0.03,  # L/hr/kW (no-load coefficient)
        'dg_fuel_f1': 0.22,  # L/kWh (load coefficient)
        'dg_fuel_flat_rate': 0.25,  # L/kWh (flat rate when disabled)
        'dg_fuel_price': 1.50,  # $/L
    },

    # Step 2: Dispatch Rules
    'rules': {
        'dg_timing': 'anytime',  # 'anytime', 'day_only', 'night_only', 'custom_blackout'
        'dg_trigger': 'reactive',  # 'reactive', 'soc_based', 'proactive'
        'dg_charges_bess': False,
        'dg_load_priority': 'bess_first',  # 'bess_first' or 'dg_first'
        'dg_takeover_mode': True,  # When True: DG serves full load, solar goes to BESS

        # SoC thresholds (for soc_based trigger)
        'soc_on_threshold': 30.0,  # %
        'soc_off_threshold': 80.0,  # %

        # Blackout window (for custom_blackout timing)
        'blackout_start': 22,
        'blackout_end': 6,

        # Time windows
        'night_start': 18,
        'night_end': 6,
        'day_start': 6,
        'day_end': 18,

        # Inferred template (read-only, set by inference)
        'inferred_template': 0,

        # Cycle Charging Mode
        'cycle_charging_enabled': False,  # Enable cycle charging
        'cycle_charging_min_load_pct': 70.0,  # Minimum DG load %
        'cycle_charging_off_soc': 80.0,  # Stop charging at this SOC %
    },

    # Step 3: Sizing Range
    'sizing': {
        # BESS capacity range
        'capacity_min': 50.0,  # MWh
        'capacity_max': 200.0,  # MWh
        'capacity_step': 25.0,  # MWh

        # Duration classes (hours)
        'durations': [2, 4],  # Selected durations
        'duration_options': [1, 2, 4, 6, 8],  # Available options

        # DG range (only if DG enabled)
        'dg_min': 0.0,  # MW
        'dg_max': 20.0,  # MW
        'dg_step': 5.0,  # MW

        # Optimization Goals
        'optimization_goal': {
            # Delivery requirement
            'delivery_mode': 'maximize',  # 'maximize', 'at_least', 'exactly'
            'delivery_target_pct': 95.0,  # Target % when mode is 'at_least' or 'exactly'

            # Optimization priority (what to minimize when multiple configs meet delivery requirement)
            'optimize_for': 'min_bess_size',  # 'min_bess_size', 'min_wastage', 'min_dg_hours', 'min_cycles'

            # Secondary constraints (optional filters)
            'max_wastage_pct': None,  # If set, exclude configs above this wastage %
            'max_dg_hours': None,  # If set, exclude configs above this DG runtime
        },
    },

    # Step 4: Results
    'results': {
        'simulation_results': None,  # DataFrame with all configs
        'selected_configs': [],  # List of config indices for comparison (max 3)
        'sort_column': 'delivery_pct',
        'sort_ascending': False,
        'filters': {
            'full_delivery': False,
            'zero_dg': False,
            'low_wastage': False,
            'hide_dominated': False,
        },
        'detail_view_config': None,  # Config index for detail view

        # Ranked recommendations
        'ranked_recommendations': None,  # Result from calculate_ranked_recommendations()
        'recommendation_generated': False,
    },

    # Financial Analysis
    'financial': {
        'enabled': False,  # Enable financial analysis
        'bess_cost_per_mwh': 300000,  # $/MWh
        'dg_cost_per_mw': 200000,  # $/MW
        'augmentation_cost_per_mwh': 250000,  # $/MWh
        'discount_rate': 0.08,  # 8%
        'project_life_years': 20,
        'fuel_price_per_liter': 1.50,
        'delivery_value_per_mwh': 100,  # $/MWh
        'projection_results': None,  # Cached projection results
    },

    # Quick Analysis (alternative to 5-step wizard)
    'quick_analysis': {
        'bess_capacity': 100.0,  # MWh
        'duration': 4,  # hours
        'dg_capacity': 10.0,  # MW
        'simulation_results': None,  # Cached HourlyResult list
        'cache_key': None,  # For change detection
        'rules_synced': False,  # Whether rules have been synced from Step 2
        # Quick Analysis has its own copy of rules (synced from Step 2 when simulation runs)
        'rules': None,  # Will be populated from Step 2 rules when sizing simulation runs
    },
}


# =============================================================================
# STATE MANAGEMENT FUNCTIONS
# =============================================================================

def init_wizard_state() -> None:
    """Initialize wizard state in session_state if not present."""
    if 'wizard' not in st.session_state:
        st.session_state.wizard = deepcopy(DEFAULT_WIZARD_STATE)


def get_wizard_state() -> Dict[str, Any]:
    """Get the current wizard state."""
    init_wizard_state()
    return st.session_state.wizard


def update_wizard_state(section: str, key: str, value: Any) -> None:
    """Update a specific value in wizard state."""
    init_wizard_state()
    if section in st.session_state.wizard:
        st.session_state.wizard[section][key] = value


def update_wizard_section(section: str, updates: Dict[str, Any]) -> None:
    """Update multiple values in a wizard section."""
    init_wizard_state()
    if section in st.session_state.wizard:
        st.session_state.wizard[section].update(updates)


def reset_wizard_state() -> None:
    """Reset wizard to default state."""
    st.session_state.wizard = deepcopy(DEFAULT_WIZARD_STATE)


def sync_quick_analysis_rules() -> None:
    """
    Sync Step 2 rules to Quick Analysis page.
    Called when sizing simulation runs to ensure Quick Analysis
    starts with the same dispatch rules as the wizard.
    """
    init_wizard_state()
    # Deep copy Step 2 rules to Quick Analysis
    step2_rules = st.session_state.wizard['rules']
    st.session_state.wizard['quick_analysis']['rules'] = deepcopy(step2_rules)
    st.session_state.wizard['quick_analysis']['rules_synced'] = True
    # Clear cached simulation results since rules changed
    st.session_state.wizard['quick_analysis']['simulation_results'] = None
    st.session_state.wizard['quick_analysis']['cache_key'] = None


def get_quick_analysis_rules() -> Dict[str, Any]:
    """
    Get rules for Quick Analysis page.
    Returns Quick Analysis rules if synced, otherwise returns Step 2 rules as default.
    """
    init_wizard_state()
    qa_rules = st.session_state.wizard['quick_analysis'].get('rules')
    if qa_rules is None:
        # Not yet synced, return Step 2 rules as initial values
        return deepcopy(st.session_state.wizard['rules'])
    return qa_rules


def update_quick_analysis_rule(key: str, value: Any) -> None:
    """Update a specific rule in Quick Analysis (independent of Step 2)."""
    init_wizard_state()
    qa_state = st.session_state.wizard['quick_analysis']
    # Initialize rules from Step 2 if not yet set
    if qa_state.get('rules') is None:
        qa_state['rules'] = deepcopy(st.session_state.wizard['rules'])
    qa_state['rules'][key] = value
    # Clear cache since rules changed
    qa_state['simulation_results'] = None
    qa_state['cache_key'] = None


def get_current_step() -> int:
    """Get current wizard step."""
    init_wizard_state()
    return st.session_state.wizard['current_step']


def set_current_step(step: int) -> None:
    """Set current wizard step."""
    init_wizard_state()
    st.session_state.wizard['current_step'] = max(1, min(5, step))


def can_navigate_to_step(target_step: int) -> bool:
    """Check if navigation to target step is allowed."""
    init_wizard_state()
    max_completed = st.session_state.wizard['max_completed_step']
    return target_step <= max_completed + 1


def mark_step_completed(step: int) -> None:
    """Mark a step as completed."""
    init_wizard_state()
    current_max = st.session_state.wizard['max_completed_step']
    st.session_state.wizard['max_completed_step'] = max(current_max, step)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_step_1() -> tuple[bool, List[str]]:
    """Validate Step 1 (Setup) data. Returns (is_valid, error_messages)."""
    init_wizard_state()
    setup = st.session_state.wizard['setup']
    errors = []

    # Load validation
    if setup['load_mode'] == 'csv' and setup['load_csv_data'] is None:
        errors.append("Load profile CSV is required")
    elif setup['load_mode'] != 'csv' and setup['load_mw'] <= 0:
        errors.append("Load MW must be positive")

    # Solar validation
    solar_source = setup.get('solar_source', 'default')
    if solar_source == 'upload' and setup.get('solar_csv_data') is None:
        errors.append("Solar profile CSV is required when using uploaded source")

    # BESS validation
    if setup['bess_min_soc'] >= setup['bess_max_soc']:
        errors.append("Min SOC must be less than Max SOC")
    if not (0 < setup['bess_min_soc'] < 100):
        errors.append("Min SOC must be between 0 and 100%")
    if not (0 < setup['bess_max_soc'] <= 100):
        errors.append("Max SOC must be between 0 and 100%")
    if not (setup['bess_min_soc'] <= setup['bess_initial_soc'] <= setup['bess_max_soc']):
        errors.append("Initial SOC must be between Min and Max SOC")
    if not (0 < setup['bess_efficiency'] <= 100):
        errors.append("Efficiency must be between 0 and 100%")

    return len(errors) == 0, errors


def validate_step_2() -> tuple[bool, List[str]]:
    """Validate Step 2 (Rules) data. Returns (is_valid, error_messages)."""
    init_wizard_state()
    setup = st.session_state.wizard['setup']
    rules = st.session_state.wizard['rules']
    errors = []
    warnings = []

    # Skip validation if DG not enabled
    if not setup['dg_enabled']:
        return True, []

    # SoC threshold validation for soc_based trigger
    if rules['dg_trigger'] == 'soc_based':
        if rules['soc_on_threshold'] >= rules['soc_off_threshold']:
            errors.append("SOC ON threshold must be less than OFF threshold")

        deadband = rules['soc_off_threshold'] - rules['soc_on_threshold']
        if deadband < 20:
            warnings.append(f"Small deadband ({deadband:.0f}%) may cause frequent DG cycling")

        if rules['soc_on_threshold'] < setup['bess_min_soc']:
            errors.append("SOC ON threshold cannot be below BESS min SOC")
        if rules['soc_off_threshold'] > setup['bess_max_soc']:
            errors.append("SOC OFF threshold cannot exceed BESS max SOC")

    # Blackout window validation
    if rules['dg_timing'] == 'custom_blackout':
        if rules['blackout_start'] == rules['blackout_end']:
            errors.append("Blackout start and end cannot be the same hour")

    return len(errors) == 0, errors + warnings


def validate_step_3() -> tuple[bool, List[str]]:
    """Validate Step 3 (Sizing) data. Returns (is_valid, error_messages)."""
    init_wizard_state()
    sizing = st.session_state.wizard['sizing']
    errors = []

    # Capacity range
    if sizing['capacity_min'] <= 0:
        errors.append("Minimum capacity must be positive")
    if sizing['capacity_max'] < sizing['capacity_min']:
        errors.append("Maximum capacity must be >= minimum")
    if sizing['capacity_step'] <= 0:
        errors.append("Capacity step must be positive")

    # Duration selection
    if not sizing['durations']:
        errors.append("At least one duration class must be selected")

    # DG range (if enabled)
    setup = st.session_state.wizard['setup']
    if setup['dg_enabled']:
        if sizing['dg_max'] < sizing['dg_min']:
            errors.append("Maximum DG must be >= minimum")
        if sizing['dg_step'] <= 0:
            errors.append("DG step must be positive")

    # Check total configurations
    num_configs = count_configurations()
    if num_configs > 50000:
        errors.append(f"Too many configurations ({num_configs:,}). Maximum is 50,000")
    elif num_configs > 10000:
        errors.append(f"Warning: {num_configs:,} configurations may take several minutes")

    return len(errors) == 0, errors


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def count_configurations() -> int:
    """Count total configurations to simulate based on sizing parameters."""
    init_wizard_state()
    sizing = st.session_state.wizard['sizing']
    setup = st.session_state.wizard['setup']

    # Count capacity values
    cap_range = sizing['capacity_max'] - sizing['capacity_min']
    cap_count = int(cap_range / sizing['capacity_step']) + 1 if sizing['capacity_step'] > 0 else 1

    # Count duration values
    dur_count = len(sizing['durations'])

    # Count DG values
    if setup['dg_enabled'] and sizing['dg_step'] > 0:
        dg_range = sizing['dg_max'] - sizing['dg_min']
        dg_count = int(dg_range / sizing['dg_step']) + 1
    else:
        dg_count = 1

    return cap_count * dur_count * dg_count


def estimate_simulation_time() -> str:
    """Estimate simulation time based on configuration count."""
    num_configs = count_configurations()

    # Rough estimate: ~30ms per configuration
    seconds = num_configs * 0.03

    if seconds < 1:
        return "< 1 second"
    elif seconds < 60:
        return f"~{int(seconds)} seconds"
    elif seconds < 300:
        return f"~{int(seconds / 60)} minutes"
    else:
        return f"~{int(seconds / 60)} minutes (consider reducing range)"


def get_step_status(step: int) -> str:
    """Get status of a step: 'completed', 'current', 'pending', or 'locked'."""
    init_wizard_state()
    current = st.session_state.wizard['current_step']
    max_completed = st.session_state.wizard['max_completed_step']

    if step < current and step <= max_completed:
        return 'completed'
    elif step == current:
        return 'current'
    elif step <= max_completed + 1:
        return 'pending'
    else:
        return 'locked'


def build_simulation_params() -> Dict[str, Any]:
    """Build SimulationParams dict from wizard state."""
    init_wizard_state()
    setup = st.session_state.wizard['setup']
    rules = st.session_state.wizard['rules']

    return {
        # Load (built separately by load_builder)
        'load_mode': setup['load_mode'],
        'load_mw': setup['load_mw'],
        'load_day_start': setup['load_day_start'],
        'load_day_end': setup['load_day_end'],
        'load_night_start': setup['load_night_start'],
        'load_night_end': setup['load_night_end'],
        'load_windows': setup['load_windows'],
        'load_csv_data': setup['load_csv_data'],

        # BESS
        'bess_efficiency': setup['bess_efficiency'],
        'bess_min_soc': setup['bess_min_soc'],
        'bess_max_soc': setup['bess_max_soc'],
        'bess_initial_soc': setup['bess_initial_soc'],
        'bess_daily_cycle_limit': setup['bess_daily_cycle_limit'],
        'bess_enforce_cycle_limit': setup['bess_enforce_cycle_limit'],

        # DG
        'dg_enabled': setup['dg_enabled'],
        'dg_charges_bess': rules['dg_charges_bess'],
        'dg_load_priority': rules['dg_load_priority'],
        'dg_takeover_mode': rules['dg_takeover_mode'],

        # Time windows
        'night_start_hour': rules['night_start'],
        'night_end_hour': rules['night_end'],
        'day_start_hour': rules['day_start'],
        'day_end_hour': rules['day_end'],
        'blackout_start_hour': rules['blackout_start'],
        'blackout_end_hour': rules['blackout_end'],

        # SoC thresholds
        'dg_soc_on_threshold': rules['soc_on_threshold'],
        'dg_soc_off_threshold': rules['soc_off_threshold'],
    }


def add_comparison_config(config_index: int) -> bool:
    """Add a config to comparison selection. Returns True if added."""
    init_wizard_state()
    selected = st.session_state.wizard['results']['selected_configs']

    if config_index in selected:
        return False
    if len(selected) >= 3:
        return False

    selected.append(config_index)
    return True


def remove_comparison_config(config_index: int) -> bool:
    """Remove a config from comparison selection. Returns True if removed."""
    init_wizard_state()
    selected = st.session_state.wizard['results']['selected_configs']

    if config_index not in selected:
        return False

    selected.remove(config_index)
    return True


def clear_comparison_selection() -> None:
    """Clear all selected configs for comparison."""
    init_wizard_state()
    st.session_state.wizard['results']['selected_configs'] = []


def set_results_filter(filter_name: str, value: bool) -> None:
    """Set a results filter."""
    init_wizard_state()
    if filter_name in st.session_state.wizard['results']['filters']:
        st.session_state.wizard['results']['filters'][filter_name] = value


def toggle_results_filter(filter_name: str) -> None:
    """Toggle a results filter."""
    init_wizard_state()
    filters = st.session_state.wizard['results']['filters']
    if filter_name in filters:
        filters[filter_name] = not filters[filter_name]
