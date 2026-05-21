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
        'solar_source': 'inputs',  # 'inputs' (from folder) or 'upload' (custom CSV)
        'solar_selected_file': None,  # Selected filename from Inputs folder
        'solar_csv_data': None,  # numpy array if CSV uploaded

        # Market price curve (A48, 2026-05-21):
        # Placeholder for Step 1's price-curve panel. None = use the engine
        # default (_DEFAULT_MERCHANT_PRICES_MONTHLY in src/project_irr.py).
        # When user uploads a CSV, this holds the parsed curve dict
        # {(year, month): price_gbp_per_mwh}. Engine wiring is a follow-up;
        # for now the engine ignores this field and uses its locked default.
        'merchant_price_curve_source': 'default',  # 'default' or 'upload'
        'merchant_price_curve': None,

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
    # Sizing simulation results live at top-level `st.session_state.sizing_results`
    # per Spec §8 and Step 1's cache-invalidation contract — NOT nested here. See
    # decisions log A42 (2026-05-16). The previously-present nested keys
    # (selected_configs, sort_*, filters, detail_view_config,
    # ranked_recommendations) were removed in A47 (2026-05-16) — they were
    # never read by any page; the 5 helper functions that referenced them were
    # removed too.

    # Financial Analysis (GBP-based, mirrors Excel model Off-Grid Solution v8.xlsm)
    #
    # IMPORTANT (A43, 2026-05-16): All values below are aligned with Step 7's
    # UI defaults (A28) and the D13 audit fixture. Pre-A43, the wizard state
    # used a stale pre-A28 defaults baseline — so when a user opened Step 3a
    # without visiting Step 7 first, the engine got the wrong defaults
    # (CAPEX £64.7m vs £101.6m audit; Combined PIRR ~19.7% vs 8.88% audit).
    # The lock-in test is `test_default_wizard_state_produces_audit` in
    # `tests/test_wizard_state_path.py`. If you change a value here, that
    # test will tell you whether the engine still reproduces the D13 audit.
    'financial': {
        'enabled': False,

        # --- Timing ---
        'model_start': None,       # date object
        'dev_start': None,
        'dev_time_months': 12,
        'construction_start': None,
        'construction_months': 18,
        'cod_date': None,
        'project_life_years': 35,

        # --- Solar ---
        'solar_capacity_mwp': 82.0,
        'generation_selection': 'P50',   # A43: was 'P90', D13 uses P50
        'yield_p50': 967.0,
        'yield_p75': 936.0,
        'yield_p90': 895.0,
        'degradation_pct': 0.3,      # display % (0.3 = 0.003 decimal)
        'outage_selection': 0,
        'outage_month_idx': 0,
        'outage_length_days': 14,

        # --- BESS ---
        'bess_switch': 1,
        'bess_capacity_mw': 62.5,
        'bess_duration_hrs': 4.0,
        'bess_operating_life': 10,       # A43: was 15, Excel `Solar&BESS Inputs!F112` = 10
        'bess_degradation_pct': 2.5,
        'bess_merchant_switch': 1,
        'bess_scenario': 1,
        'bess_merchant_discount': 5.0,  # display %

        # --- PPA ---
        'ppa_selection': 1,
        'ppa_flex_pct': 0.0,
        'ppa_indexation': 'CPI',
        'ppa_tariff_gbp_mwh': 170.0,    # Excel: Overall Inputs!E13
        'ppa_tenor_years': 10,          # Excel: Overall Inputs!E11
        'ppa_escalation_pct': 0.0,      # Excel: Overall Inputs!E14 (display %)

        # --- Dispatch / merchant (used by tariff_inputs_from_wizard_state) ---
        'merchant_price_default': 67.0,  # GBP/MWh fallback for post-PPA solar
        'profile_reference_mwp': 67.89,  # peak MW of Inputs/Solar Profile.csv

        # --- REGOs (A43: aligned to D13) ---
        'rego_switch': 1,
        'rego_price': 2.5,           # A43: was 5.0
        'rego_indexation': 'NIL',    # A43: was 'CPI'
        'rego_tenor_years': 35,      # A43: was 15

        # --- Capacity Market (A43: D13 has CM OFF) ---
        'cm_t1_value': 0.0,          # A43: was 20.0
        'cm_t1_derating': 27.15,     # display %
        'cm_t1_tenor': 3,            # A43: was 1
        'cm_t4_value': 0.0,
        'cm_t4_derating': 20.94,     # A43: was 0.0
        'cm_t4_tenor': 15,           # A43: was 0

        # --- Embedded Benefits (A43: D13 has Embedded ON) ---
        'emb_benefits_switch': 1,    # A43: was 0
        'emb_benefits_tenor': 15,
        'emb_benefits_index': 'CPI',

        # --- BESS Floor (A43: D13 has Floor OFF) ---
        'bess_floor_switch': 0,      # A43: was 1
        'bess_floor_price': 40.0,
        'bess_floor_rev_share': 9.0, # A43: was 10.0
        'bess_floor_tenor': 10,

        # --- CAPEX (GBP/kWp) — A43: aligned to engine PirrInputs / Excel ---
        'capex_epc': 400.0,
        'capex_grid': 57.858,        # A43: was 30.0
        'capex_development': 2.949,  # A43: was 15.0
        'capex_acquisition': 0.0,
        'capex_dd': 3.775,           # A43: was 5.0
        'capex_discharge': 0.983,    # A43: was 0.0
        'capex_sdlt': 0.753,         # A43: was 0.0
        'capex_land_legal': 3.686,   # A43: was 2.0
        'capex_other_finance': 5.0,  # A43: was 0.0
        'capex_other_legal': 0.0,    # A43: was 2.0
        'capex_land_purchase': 0.0,
        'capex_ampyr_tech': 3.236,   # A43: was 0.0
        'capex_success_fee': 0.0,
        'capex_community': 0.0,
        # A43: was 80.0. Unit was wrong (labelled GBP/kWp solar; engine field
        # `capex_bess_gbp_per_kw_bess` expects GBP/kW of BESS power). Excel
        # `Solar&BESS Inputs!F349` = 600. This was the root cause of the
        # £64.7m vs £101.6m CAPEX bug in browser smoke test §16.
        'capex_bess': 600.0,
        'capex_landowner_fees': 11.597,  # A43: was 0.0
        'capex_insurance': 6.329,    # A43: was 3.0
        'capex_land_lease_constr': 2.457,  # A43: was 0.0
        'capex_asset_adoption': 0.0,
        'capex_others': 0.0,
        'capex_misc': 4.916,         # A43: was 0.0
        'capex_contingency_pct': 1.0,  # display %

        # --- Solar OPEX (GBP/kWp/Yr) — A43: aligned to engine ---
        'opex_pv_om': 5.48,
        'opex_grid_conn': 0.003,     # A43: was 1.5
        'opex_greenkeeping': 1.5,    # A43: was 0.5
        'opex_community': 0.5,       # A43: was 0.0
        'opex_real_estate_tax': 1.222,  # A43: was 1.0
        'opex_non_tech_am': 1.3,     # A43: was 1.0
        'opex_subsidy_loss': 0.0,
        'opex_insurance': 2.021,     # A43: was 2.02 (precision)
        'opex_fixed_lease': 0.0,
        'opex_corrective_maint': 3.2,
        'opex_tech_am': 0.3,         # A43: was 1.5
        'opex_social_cost': 0.0,       # GBP/MWh
        'opex_balancing_cfd': 2.75,  # A43: was 0.0, GBP/MWh

        # --- BESS OPEX (GBPk/MW/Yr) — A43: aligned ---
        'bess_opex_om': 7.063,       # A43: was 7.06 (precision)
        'bess_opex_import': 0.0,
        'bess_opex_rates': 3.276,    # A43: was 0.0
        'bess_opex_lease': 1.489,    # A43: was 0.0

        # --- Land (A43: D13 has lease ON, 205 acres, £700/acre, 5%/5%) ---
        'fixed_lease_switch': 1,     # A43: was 0
        'fixed_lease_acres': 205.0,  # A43: was 200.0
        'fixed_lease_price': 700.0,  # A43: was 800.0
        'rev_dep_lease_switch': 1,   # A43: was 0
        'rev_share_yr1_10': 5.0,
        'rev_share_yr11_35': 5.0,    # A43: was 7.5
        'land_purchase_switch': 0,
        'land_purchase_acres': 0.0,
        'land_purchase_price': 10000.0,
        'construction_rent_sw': 0,
        'construction_rent': 500.0,

        # --- Tax ---
        'corp_tax_rate_low': 19.0,
        'corp_tax_rate_high': 25.0,
        'corp_tax_threshold': 250.0,   # GBPk
        'taxation_month': 12,

        # --- Working Capital & Financial (A43: aligned) ---
        'wc_debtors_days': 30,         # A43: was 45
        'wc_creditors_days': 30,
        'project_discount_rate': 6.5,  # A43: was 8.0
        'cost_of_capital': 6.0,        # display %

        # --- Advanced (A43: SHL + depreciation, Excel-locked per A21/A28) ---
        # These keys were missing from DEFAULT_WIZARD_STATE pre-A43 but the
        # engine adapter `pirr_inputs_from_wizard_state` reads them. Without
        # them, SHL tax shield + RB depreciation didn't activate on the
        # fresh-session path (only on the Step 7-Save path).
        'shl_switch': 1,
        'shl_pct_of_unfunded': 99.0,     # Excel `Solar&BESS Inputs!F556` = 0.99
        'shl_rate': 15.0,                # Excel `Solar&BESS Inputs!F553` = 15%
        'depreciation_method': 'RB',     # Excel `D&T!E165` = "RB"
        'depreciation_rate': 100.0 * 2.0 / 36.0,  # Excel `D&T!E164` = 2/36 ≈ 5.5556%

        # --- Results (cached) ---
        'screening_results': None,
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


TOTAL_STEPS = 7   # Setup, Rules, Sizing, Results, MultiYear, GreenEnergy, Financial


def set_current_step(step: int) -> None:
    """Set current wizard step."""
    init_wizard_state()
    st.session_state.wizard['current_step'] = max(1, min(TOTAL_STEPS, step))


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


def validate_step_7() -> tuple[bool, List[str]]:
    """Validate Step 7 (Financial) data. Returns (is_valid, error_messages)."""
    init_wizard_state()
    fin = st.session_state.wizard['financial']
    errors = []

    # Must be enabled
    if not fin.get('enabled'):
        errors.append("Financial inputs have not been saved yet")
        return False, errors

    # Timing
    if fin.get('project_life_years', 0) < 10:
        errors.append("Project life must be at least 10 years")
    if fin.get('construction_months', 0) < 1:
        errors.append("Construction time must be at least 1 month")

    # Solar
    if fin.get('solar_capacity_mwp', 0) <= 0:
        errors.append("Solar capacity must be positive")

    # CAPEX
    if fin.get('capex_epc', 0) <= 0:
        errors.append("EPC cost must be positive")

    # Financial
    if fin.get('project_discount_rate', 0) <= 0:
        errors.append("Discount rate must be positive")

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


# A47 (2026-05-16) removed 5 helper functions that operated on the dead
# `wizard['results']` slot (which itself was removed at A47):
#   add_comparison_config, remove_comparison_config, clear_comparison_selection,
#   set_results_filter, toggle_results_filter
# None of these were imported by any page. They were vestiges of an earlier
# results-comparison feature that never shipped to the UI. If a future
# version wants config-comparison UX, re-introduce these in a fresh module
# alongside the actual UI that needs them — not as orphan functions in
# wizard_state.py.
