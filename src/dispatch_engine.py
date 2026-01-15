"""
Dispatch Engine Module - BESS & DG Sizing Tool

Implements the algorithm specification for all dispatch templates (0-6).
Based on ALGORITHM_SPECIFICATION.md v1.0

This module is used ONLY by the hourly examples page.
Existing pages continue to use battery_simulator.py.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Import fuel model for DG fuel consumption calculations
from src.fuel_model import calculate_fuel_rate, calculate_fuel_consumption


# =============================================================================
# CONSTANTS
# =============================================================================

DURATION_CLASSES = [1, 2, 3, 4, 6, 8, 10]  # hours


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SimulationParams:
    """Input parameters for simulation."""
    # Profiles
    load_profile: List[float] = field(default_factory=list)
    solar_profile: List[float] = field(default_factory=list)

    # BESS parameters
    bess_capacity: float = 100  # MWh
    bess_charge_power: float = 100  # MW
    bess_discharge_power: float = 100  # MW
    bess_efficiency: float = 85  # %
    bess_min_soc: float = 10  # %
    bess_max_soc: float = 90  # %
    bess_initial_soc: float = 50  # %
    bess_daily_cycle_limit: Optional[float] = None
    bess_enforce_cycle_limit: bool = False

    # DG parameters
    dg_enabled: bool = False
    dg_capacity: float = 0  # MW
    dg_charges_bess: bool = True
    dg_load_priority: str = 'bess_first'  # 'bess_first' or 'dg_first'
    dg_takeover_mode: bool = False  # When True: DG serves full load, solar goes to BESS

    # Template-specific: Time windows
    night_start_hour: int = 18
    night_end_hour: int = 6
    day_start_hour: int = 6
    day_end_hour: int = 18
    blackout_start_hour: int = 22
    blackout_end_hour: int = 6

    # Template-specific: SoC thresholds
    dg_soc_on_threshold: float = 30  # %
    dg_soc_off_threshold: float = 80  # %
    emergency_soc_threshold: float = 15  # %

    # Template-specific: Flags
    allow_emergency_dg_day: bool = False
    allow_emergency_dg_night: bool = False

    # Fuel model parameters
    dg_fuel_curve_enabled: bool = False
    dg_fuel_f0: float = 0.03  # L/hr per kW rated (no-load coefficient)
    dg_fuel_f1: float = 0.22  # L/kWh output (load coefficient)
    dg_fuel_flat_rate: float = 0.25  # L/kWh (flat rate when curve disabled)

    # Cycle charging parameters
    cycle_charging_enabled: bool = False
    cycle_charging_min_load_pct: float = 70.0  # Minimum DG load in cycle charging
    cycle_charging_off_soc: float = 80.0  # Stop cycle charging at this SOC %


@dataclass
class SimulationState:
    """Mutable state during simulation."""
    # Configuration
    bess_capacity: float = 0
    dg_capacity: float = 0

    # Derived constants
    usable_capacity: float = 0
    min_soc_mwh: float = 0
    max_soc_mwh: float = 0
    charge_power_limit: float = 0
    discharge_power_limit: float = 0
    charge_efficiency: float = 0
    discharge_efficiency: float = 0

    # SoC thresholds (MWh)
    dg_soc_on_mwh: float = 0
    dg_soc_off_mwh: float = 0
    emergency_soc_mwh: float = 0

    # Time window arrays
    is_night_hour: List[bool] = field(default_factory=lambda: [False] * 24)
    is_day_hour: List[bool] = field(default_factory=lambda: [False] * 24)
    is_blackout_hour: List[bool] = field(default_factory=lambda: [False] * 24)

    # State variables
    soc: float = 0
    daily_discharge: float = 0
    daily_cycles: float = 0
    bess_disabled_today: bool = False
    current_day: int = 1
    dg_was_running: bool = False

    # Counters
    total_dg_starts: int = 0
    total_dg_runtime_hours: int = 0
    total_dg_fuel_consumed: float = 0  # Liters


@dataclass
class HourlyResult:
    """Results for a single hour."""
    t: int = 0
    day: int = 0
    hour_of_day: int = 0

    load: float = 0
    solar: float = 0

    solar_to_load: float = 0
    solar_to_bess: float = 0
    solar_curtailed: float = 0

    bess_to_load: float = 0

    dg_to_load: float = 0
    dg_to_bess: float = 0
    dg_curtailed: float = 0
    dg_running: bool = False
    dg_mode: str = "OFF"
    dg_output_mw: float = 0  # Actual DG output (MW)
    dg_fuel_consumed: float = 0  # Fuel consumed this hour (Liters)
    cycle_charging: bool = False  # True if DG is in cycle charging mode

    bess_assisted: bool = False
    unserved: float = 0

    soc: float = 0
    soc_pct: float = 0
    daily_cycles: float = 0
    bess_disabled: bool = False

    is_night: bool = False
    is_day: bool = False
    is_blackout: bool = False

    bess_state: str = "Idle"
    bess_power: float = 0


@dataclass
class SummaryMetrics:
    """Summary metrics after simulation completes."""
    total_load: float = 0
    total_solar_generation: float = 0
    total_solar_to_load: float = 0
    total_solar_to_bess: float = 0
    total_solar_curtailed: float = 0
    total_bess_to_load: float = 0
    total_dg_to_load: float = 0
    total_dg_to_bess: float = 0
    total_dg_curtailed: float = 0
    total_unserved: float = 0

    hours_with_load: int = 0  # Hours where load > 0 (for seasonal patterns)
    hours_full_delivery: int = 0
    hours_green_delivery: int = 0
    hours_with_dg: int = 0

    pct_full_delivery: float = 0
    pct_green_delivery: float = 0
    pct_unserved: float = 0
    pct_solar_curtailed: float = 0

    # Load-period-only metrics (for seasonal loads)
    solar_during_load_hours: float = 0
    solar_curtailed_during_load_hours: float = 0
    pct_solar_curtailed_load_hours: float = 0  # Wastage % during load periods only

    dg_runtime_hours: int = 0
    dg_starts: int = 0
    bess_throughput: float = 0
    bess_equivalent_cycles: float = 0

    # Fuel consumption metrics
    total_fuel_consumed: float = 0  # Liters
    avg_fuel_rate_lph: float = 0  # L/hr (average when running)
    specific_fuel_consumption: float = 0  # L/kWh delivered
    cycle_charging_hours: int = 0  # Hours DG was in cycle charging mode

    # Energy-based green delivery metrics (for green energy optimization)
    total_green_energy_delivered: float = 0.0  # MWh from solar + BESS
    total_energy_delivered: float = 0.0  # MWh from all sources
    pct_green_energy: float = 0.0  # Energy-based green %


# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================

def build_hour_arrays(params: SimulationParams) -> Tuple[List[bool], List[bool], List[bool]]:
    """Build boolean arrays for night, day, and blackout hours."""
    is_night = [False] * 24
    is_day = [False] * 24
    is_blackout = [False] * 24

    # Night hours (spans midnight typically)
    start, end = params.night_start_hour, params.night_end_hour
    if start > end:
        for h in range(start, 24):
            is_night[h] = True
        for h in range(0, end):
            is_night[h] = True
    elif start < end:
        for h in range(start, end):
            is_night[h] = True

    # Day hours
    start, end = params.day_start_hour, params.day_end_hour
    if start < end:
        for h in range(start, end):
            is_day[h] = True
    elif start > end:
        for h in range(start, 24):
            is_day[h] = True
        for h in range(0, end):
            is_day[h] = True

    # Blackout hours
    start, end = params.blackout_start_hour, params.blackout_end_hour
    if start > end:
        for h in range(start, 24):
            is_blackout[h] = True
        for h in range(0, end):
            is_blackout[h] = True
    elif start < end:
        for h in range(start, end):
            is_blackout[h] = True

    return is_night, is_day, is_blackout


def initialize_simulation(params: SimulationParams) -> SimulationState:
    """Initialize simulation state from parameters."""
    state = SimulationState()

    state.bess_capacity = params.bess_capacity
    state.dg_capacity = params.dg_capacity if params.dg_enabled else 0

    # BESS capacity limits (MWh)
    state.usable_capacity = params.bess_capacity * (params.bess_max_soc - params.bess_min_soc) / 100
    state.min_soc_mwh = params.bess_capacity * params.bess_min_soc / 100
    state.max_soc_mwh = params.bess_capacity * params.bess_max_soc / 100

    # Power limits
    state.charge_power_limit = params.bess_charge_power
    state.discharge_power_limit = params.bess_discharge_power

    # Efficiency factors (sqrt split)
    state.charge_efficiency = math.sqrt(params.bess_efficiency / 100)
    state.discharge_efficiency = math.sqrt(params.bess_efficiency / 100)

    # SoC thresholds (MWh)
    state.dg_soc_on_mwh = params.bess_capacity * params.dg_soc_on_threshold / 100
    state.dg_soc_off_mwh = params.bess_capacity * params.dg_soc_off_threshold / 100
    state.emergency_soc_mwh = params.bess_capacity * params.emergency_soc_threshold / 100

    # Time windows
    state.is_night_hour, state.is_day_hour, state.is_blackout_hour = build_hour_arrays(params)

    # Initial state
    state.soc = params.bess_capacity * params.bess_initial_soc / 100
    state.daily_discharge = 0
    state.daily_cycles = 0
    state.bess_disabled_today = False
    state.current_day = 1
    state.dg_was_running = False
    state.total_dg_starts = 0
    state.total_dg_runtime_hours = 0

    return state


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def charge_bess(state: SimulationState, energy_available: float,
                charge_power_used: float) -> Tuple[float, float]:
    """Attempt to charge BESS. Returns (energy_charged, new_charge_power_used)."""
    if energy_available <= 0 or state.bess_disabled_today:
        return 0, charge_power_used

    charge_room = state.max_soc_mwh - state.soc
    charge_power_available = state.charge_power_limit - charge_power_used

    if charge_power_available <= 0 or charge_room <= 0:
        return 0, charge_power_used

    max_charge = min(
        energy_available,
        charge_power_available,
        charge_room / state.charge_efficiency
    )

    if max_charge <= 0:
        return 0, charge_power_used

    energy_stored = max_charge * state.charge_efficiency
    state.soc += energy_stored

    return max_charge, charge_power_used + max_charge


def discharge_bess(state: SimulationState, params: SimulationParams,
                   energy_needed: float) -> Tuple[float, bool]:
    """Attempt to discharge BESS. Returns (energy_discharged, discharged_flag)."""
    if energy_needed <= 0 or state.bess_disabled_today:
        return 0, False

    discharge_available = state.soc - state.min_soc_mwh
    if discharge_available <= 0:
        return 0, False

    max_discharge = min(
        energy_needed,
        state.discharge_power_limit,
        discharge_available * state.discharge_efficiency
    )

    if max_discharge <= 0:
        return 0, False

    energy_withdrawn = max_discharge / state.discharge_efficiency
    state.soc -= energy_withdrawn

    # Update cycle tracking
    state.daily_discharge += max_discharge
    if state.usable_capacity > 0:
        state.daily_cycles = state.daily_discharge / state.usable_capacity

    # Check cycle limit
    if params.bess_enforce_cycle_limit and params.bess_daily_cycle_limit:
        if state.daily_cycles >= params.bess_daily_cycle_limit:
            state.bess_disabled_today = True

    return max_discharge, True


def calculate_dg_fuel(params: SimulationParams, dg_output_mw: float, hours: float = 1.0) -> float:
    """Calculate fuel consumption for DG operation.

    Args:
        params: Simulation parameters with fuel model settings
        dg_output_mw: Actual DG output in MW
        hours: Duration of operation (default 1 hour)

    Returns:
        Fuel consumed in Liters
    """
    if params.dg_fuel_curve_enabled:
        # Use non-linear Willans line model
        return calculate_fuel_consumption(
            p_rated_kw=params.dg_capacity * 1000,  # MW to kW
            p_actual_kw=dg_output_mw * 1000,  # MW to kW
            hours=hours,
            f0=params.dg_fuel_f0,
            f1=params.dg_fuel_f1
        )
    else:
        # Use flat rate
        return dg_output_mw * 1000 * params.dg_fuel_flat_rate * hours  # kWh * L/kWh


def activate_dg(state: SimulationState, params: SimulationParams, hour: HourlyResult,
                remaining_load: float, bess_discharged: bool,
                charge_power_used: float, mode: str = "NORMAL") -> Tuple[float, float]:
    """Activate DG. Returns (remaining_load, charge_power_used)."""
    hour.dg_running = True
    hour.dg_mode = mode

    if not state.dg_was_running:
        state.total_dg_starts += 1
    state.total_dg_runtime_hours += 1

    dg_output = state.dg_capacity
    hour.dg_output_mw = dg_output
    hour.dg_to_load = min(dg_output, remaining_load)
    remaining_load -= hour.dg_to_load
    dg_excess = dg_output - hour.dg_to_load

    # DG charges BESS with excess
    if params.dg_charges_bess and dg_excess > 0 and not bess_discharged and not state.bess_disabled_today:
        hour.dg_to_bess, charge_power_used = charge_bess(state, dg_excess, charge_power_used)
        hour.dg_curtailed = dg_excess - hour.dg_to_bess
    else:
        hour.dg_curtailed = dg_excess

    # Calculate fuel consumption
    actual_output = hour.dg_to_load + hour.dg_to_bess
    hour.dg_fuel_consumed = calculate_dg_fuel(params, actual_output)
    state.total_dg_fuel_consumed += hour.dg_fuel_consumed

    return remaining_load, charge_power_used


def activate_dg_cycle_charging(state: SimulationState, params: SimulationParams,
                               hour: HourlyResult, remaining_load: float,
                               charge_power_used: float, mode: str = "CYCLE") -> Tuple[float, float]:
    """Activate DG in cycle charging mode.

    In cycle charging mode, DG runs at minimum load percentage (default 70%)
    for efficiency. Excess power is used to charge BESS.

    Returns (remaining_load, charge_power_used).
    """
    hour.dg_running = True
    hour.dg_mode = mode
    hour.cycle_charging = True

    if not state.dg_was_running:
        state.total_dg_starts += 1
    state.total_dg_runtime_hours += 1

    # Calculate minimum DG output for cycle charging
    min_dg_output = state.dg_capacity * params.cycle_charging_min_load_pct / 100
    dg_output = max(min_dg_output, remaining_load)  # At least min load or actual need

    # Cap at DG capacity
    dg_output = min(dg_output, state.dg_capacity)
    hour.dg_output_mw = dg_output

    # Serve load first
    hour.dg_to_load = min(dg_output, remaining_load)
    remaining_load -= hour.dg_to_load
    dg_excess = dg_output - hour.dg_to_load

    # All excess goes to BESS (cycle charging purpose)
    if dg_excess > 0 and not state.bess_disabled_today:
        hour.dg_to_bess, charge_power_used = charge_bess(state, dg_excess, charge_power_used)
        hour.dg_curtailed = dg_excess - hour.dg_to_bess
    else:
        hour.dg_curtailed = dg_excess

    # Calculate fuel consumption
    actual_output = hour.dg_to_load + hour.dg_to_bess
    hour.dg_fuel_consumed = calculate_dg_fuel(params, actual_output)
    state.total_dg_fuel_consumed += hour.dg_fuel_consumed

    return remaining_load, charge_power_used


# =============================================================================
# TEMPLATE DISPATCH FUNCTIONS
# =============================================================================

def should_use_cycle_charging(params: SimulationParams, state: SimulationState) -> bool:
    """Check if cycle charging mode should be used.

    Cycle charging is used when:
    1. cycle_charging_enabled is True
    2. DG needs to run
    3. BESS SOC is below the off-threshold

    Returns True if cycle charging should be used.
    """
    if not params.cycle_charging_enabled:
        return False

    # Check if BESS SOC is below the cycle charging off threshold
    soc_pct = (state.soc / state.bess_capacity * 100) if state.bess_capacity > 0 else 100
    return soc_pct < params.cycle_charging_off_soc


def check_dg_takeover(params: SimulationParams, state: SimulationState,
                      hour: HourlyResult, remaining_load: float,
                      excess_solar: float) -> Tuple[bool, float, bool, float]:
    """Check if DG takeover mode should activate and execute if needed.

    Returns: (takeover_activated, remaining_load, bess_discharged, charge_power_used)
    If takeover_activated is True, the template should return immediately.
    """
    if not params.dg_takeover_mode or state.dg_capacity <= 0:
        return False, remaining_load, False, 0

    # Calculate if Solar + BESS can meet full load
    bess_available = state.soc - state.min_soc_mwh
    bess_can_provide = min(
        state.discharge_power_limit,
        max(0, bess_available) * state.discharge_efficiency
    )
    total_green_capacity = hour.solar + bess_can_provide

    if total_green_capacity >= hour.load - 0.001:
        # Green sources can meet load - no takeover
        return False, remaining_load, False, 0

    # TAKEOVER: DG serves full load, solar to BESS
    charge_power_used = 0

    # Reverse the solar_to_load assignment (all solar goes to BESS)
    total_solar = hour.solar_to_load + excess_solar
    hour.solar_to_load = 0
    remaining_load = hour.load  # Reset to full load

    # DG serves full load
    hour.dg_running = True
    hour.dg_mode = "TAKEOVER"
    if not state.dg_was_running:
        state.total_dg_starts += 1
    state.total_dg_runtime_hours += 1

    hour.dg_to_load = hour.load  # DG serves exactly the load
    hour.dg_output_mw = hour.load  # DG output matches load
    remaining_load = 0
    hour.dg_curtailed = 0  # No DG curtailment in takeover mode

    # All solar goes to BESS
    if total_solar > 0 and not state.bess_disabled_today:
        hour.solar_to_bess, charge_power_used = charge_bess(state, total_solar, charge_power_used)
        hour.solar_curtailed = total_solar - hour.solar_to_bess
    else:
        hour.solar_curtailed = total_solar

    # Calculate fuel consumption for takeover mode
    hour.dg_fuel_consumed = calculate_dg_fuel(params, hour.dg_output_mw)
    state.total_dg_fuel_consumed += hour.dg_fuel_consumed

    return True, remaining_load, False, charge_power_used


def dispatch_template_0(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 0: Solar + BESS Only. Merit: Solar -> BESS -> Unserved."""
    bess_discharged = False
    charge_power_used = 0

    # Charge BESS with excess solar
    if excess_solar > 0:
        hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
        hour.solar_curtailed = excess_solar - hour.solar_to_bess

    # Discharge BESS to serve load
    if remaining_load > 0:
        hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
        remaining_load -= hour.bess_to_load

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_1(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 1: Green Priority. Merit order depends on dg_load_priority setting.

    DG Takeover Mode (when dg_takeover_mode=True):
        - If Solar + BESS cannot meet load, DG takes over full load
        - Solar is diverted to BESS (not load)
        - Zero DG curtailment (DG output = Load exactly)
    """
    bess_discharged = False
    charge_power_used = 0

    # Check if DG Takeover Mode is enabled and DG is available
    if params.dg_takeover_mode and state.dg_capacity > 0:
        # Calculate if Solar + BESS can meet the FULL load (not just remaining)
        # Available BESS discharge capacity
        bess_available = state.soc - state.min_soc_mwh
        if bess_available > 0:
            bess_can_provide = min(
                state.discharge_power_limit,
                bess_available * state.discharge_efficiency
            )
        else:
            bess_can_provide = 0

        # Total green capacity = solar + BESS discharge potential
        total_green_capacity = hour.solar + bess_can_provide

        # Check if green sources can meet load
        if total_green_capacity >= hour.load - 0.001:
            # GREEN MODE: Solar + BESS can meet load - proceed normally
            # Charge BESS with excess solar
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar

            # Discharge BESS if needed
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
                remaining_load -= hour.bess_to_load
        else:
            # DG TAKEOVER MODE: Solar + BESS cannot meet load
            # DG serves full load, solar goes to BESS

            # Reverse the solar_to_load assignment (all solar goes to BESS)
            total_solar = hour.solar_to_load + excess_solar
            hour.solar_to_load = 0
            remaining_load = hour.load  # Reset to full load

            # DG serves full load
            hour.dg_running = True
            hour.dg_mode = "TAKEOVER"
            if not state.dg_was_running:
                state.total_dg_starts += 1
            state.total_dg_runtime_hours += 1

            hour.dg_to_load = hour.load  # DG serves exactly the load
            remaining_load = 0
            hour.dg_curtailed = 0  # No DG curtailment in takeover mode

            # All solar goes to BESS
            if total_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(state, total_solar, charge_power_used)
                hour.solar_curtailed = total_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = total_solar
    else:
        # STANDARD MODE (no takeover)
        # Charge BESS with excess solar
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

        # Load serving order depends on dg_load_priority
        if params.dg_load_priority == 'dg_first':
            # DG First: Solar -> DG -> BESS -> Unserved
            # DG activation first (when load exceeds solar)
            if remaining_load > 0.001 and state.dg_capacity > 0:
                remaining_load, charge_power_used = activate_dg(
                    state, params, hour, remaining_load, bess_discharged, charge_power_used)

            # Then discharge BESS for any remaining load
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
                remaining_load -= hour.bess_to_load
        else:
            # BESS First (default): Solar -> BESS -> DG -> Unserved
            # Discharge BESS first
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
                remaining_load -= hour.bess_to_load

            # DG activation (reactive - only when BESS insufficient)
            if remaining_load > 0.001 and state.dg_capacity > 0:
                remaining_load, charge_power_used = activate_dg(
                    state, params, hour, remaining_load, bess_discharged, charge_power_used)

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_2(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 2: DG Night Charge. Night: DG proactive. Day: Green only."""
    bess_discharged = False
    charge_power_used = 0

    # Check for DG takeover mode first
    takeover, remaining_load, bess_discharged, charge_power_used = check_dg_takeover(
        params, state, hour, remaining_load, excess_solar)
    if takeover:
        return remaining_load, bess_discharged, charge_power_used

    is_night = state.is_night_hour[hour.hour_of_day]
    hour.is_night = is_night

    # Determine DG state
    dg_should_run = False
    dg_mode = "OFF"

    if is_night:
        # SoC-based control with deadband
        if state.soc <= state.dg_soc_on_mwh:
            dg_should_run = True
        elif state.soc >= state.dg_soc_off_mwh:
            dg_should_run = False
        else:
            dg_should_run = state.dg_was_running
        dg_mode = "NORMAL"
    else:
        # Day: emergency only
        if params.allow_emergency_dg_day and state.soc <= state.emergency_soc_mwh:
            dg_should_run = True
            dg_mode = "EMERGENCY"

    # Night with DG ON
    if is_night and dg_should_run and state.dg_capacity > 0:
        remaining_load, charge_power_used = activate_dg(
            state, params, hour, remaining_load, bess_discharged, charge_power_used, dg_mode)

        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

    # Night with DG OFF or Day
    else:
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load

        # Day emergency DG
        if not is_night and dg_should_run and remaining_load > 0 and state.dg_capacity > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, bess_discharged, charge_power_used, "EMERGENCY")

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_3(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 3: DG Blackout Window. DG disabled during blackout hours."""
    bess_discharged = False
    charge_power_used = 0

    # Check for DG takeover mode first
    takeover, remaining_load, bess_discharged, charge_power_used = check_dg_takeover(
        params, state, hour, remaining_load, excess_solar)
    if takeover:
        return remaining_load, bess_discharged, charge_power_used

    is_blackout = state.is_blackout_hour[hour.hour_of_day]
    hour.is_blackout = is_blackout

    # Charge BESS
    if excess_solar > 0 and not state.bess_disabled_today:
        hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
        hour.solar_curtailed = excess_solar - hour.solar_to_bess
    else:
        hour.solar_curtailed = excess_solar

    # Load serving order depends on dg_load_priority (only outside blackout for DG)
    dg_available = not is_blackout and state.dg_capacity > 0

    if params.dg_load_priority == 'dg_first' and dg_available:
        # DG First: Solar -> DG -> BESS -> Unserved
        if remaining_load > 0.001:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, bess_discharged, charge_power_used)

        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load
    else:
        # BESS First (default): Solar -> BESS -> DG -> Unserved
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load

        if dg_available and remaining_load > 0.001:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, bess_discharged, charge_power_used)

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_4(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 4: DG Emergency Only. SoC-triggered, no time restrictions."""
    bess_discharged = False
    charge_power_used = 0

    # Check for DG takeover mode first
    takeover, remaining_load, bess_discharged, charge_power_used = check_dg_takeover(
        params, state, hour, remaining_load, excess_solar)
    if takeover:
        return remaining_load, bess_discharged, charge_power_used

    # SoC-based DG trigger with deadband
    if state.soc <= state.dg_soc_on_mwh:
        dg_should_run = True
    elif state.soc >= state.dg_soc_off_mwh:
        dg_should_run = False
    else:
        dg_should_run = state.dg_was_running

    # DG OFF: Normal green operation
    if not dg_should_run or state.dg_capacity == 0:
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load

    # DG ON: DG priority with BESS assist/recovery
    else:
        hour.dg_running = True
        hour.dg_mode = "NORMAL"

        if not state.dg_was_running:
            state.total_dg_starts += 1
        state.total_dg_runtime_hours += 1

        dg_output = state.dg_capacity
        hour.dg_to_load = min(dg_output, remaining_load)
        remaining_load -= hour.dg_to_load
        dg_excess = dg_output - hour.dg_to_load

        # Assist mode: BESS helps if DG < Load
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load
            hour.bess_assisted = True
            hour.solar_curtailed = excess_solar
            hour.dg_curtailed = dg_excess

        # Recovery mode: charge from excess
        else:
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar

            if dg_excess > 0 and params.dg_charges_bess and not state.bess_disabled_today:
                hour.dg_to_bess, charge_power_used = charge_bess(state, dg_excess, charge_power_used)
                hour.dg_curtailed = dg_excess - hour.dg_to_bess
            else:
                hour.dg_curtailed = dg_excess

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_5(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 5: DG Day Charge. Day: SoC-triggered. Night: Silent."""
    bess_discharged = False
    charge_power_used = 0

    # Check for DG takeover mode first
    takeover, remaining_load, bess_discharged, charge_power_used = check_dg_takeover(
        params, state, hour, remaining_load, excess_solar)
    if takeover:
        return remaining_load, bess_discharged, charge_power_used

    is_day = state.is_day_hour[hour.hour_of_day]
    hour.is_day = is_day

    # Determine DG state
    dg_should_run = False
    dg_mode = "OFF"

    if is_day:
        if state.soc <= state.dg_soc_on_mwh:
            dg_should_run = True
        elif state.soc >= state.dg_soc_off_mwh:
            dg_should_run = False
        else:
            dg_should_run = state.dg_was_running
        dg_mode = "NORMAL"
    else:
        # Night: emergency only
        if params.allow_emergency_dg_night and state.soc <= state.emergency_soc_mwh:
            dg_should_run = True
            dg_mode = "EMERGENCY"

    # Day with DG triggered
    if is_day and dg_should_run and state.dg_capacity > 0:
        hour.dg_running = True
        hour.dg_mode = dg_mode

        if not state.dg_was_running:
            state.total_dg_starts += 1
        state.total_dg_runtime_hours += 1

        dg_output = state.dg_capacity
        hour.dg_to_load = min(dg_output, remaining_load)
        remaining_load -= hour.dg_to_load
        dg_excess = dg_output - hour.dg_to_load

        # Assist mode
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load
            hour.bess_assisted = True
            hour.solar_curtailed = excess_solar
            hour.dg_curtailed = dg_excess
        # Recovery mode
        else:
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar

            if dg_excess > 0 and params.dg_charges_bess and not state.bess_disabled_today:
                hour.dg_to_bess, charge_power_used = charge_bess(state, dg_excess, charge_power_used)
                hour.dg_curtailed = dg_excess - hour.dg_to_bess
            else:
                hour.dg_curtailed = dg_excess

    # Day without DG or Night
    else:
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load

        # Night emergency
        if not is_day and dg_should_run and remaining_load > 0 and state.dg_capacity > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, bess_discharged, charge_power_used, "EMERGENCY")

    return remaining_load, bess_discharged, charge_power_used


def dispatch_template_6(params: SimulationParams, state: SimulationState,
                        hour: HourlyResult, remaining_load: float,
                        excess_solar: float) -> Tuple[float, bool, float]:
    """Template 6: DG Night SoC Trigger. Night: SoC-triggered. Day: Green."""
    bess_discharged = False
    charge_power_used = 0

    # Check for DG takeover mode first
    takeover, remaining_load, bess_discharged, charge_power_used = check_dg_takeover(
        params, state, hour, remaining_load, excess_solar)
    if takeover:
        return remaining_load, bess_discharged, charge_power_used

    is_night = state.is_night_hour[hour.hour_of_day]
    hour.is_night = is_night

    # Determine DG state
    dg_should_run = False
    dg_mode = "OFF"

    if is_night:
        if state.soc <= state.dg_soc_on_mwh:
            dg_should_run = True
        elif state.soc >= state.dg_soc_off_mwh:
            dg_should_run = False
        else:
            dg_should_run = state.dg_was_running
        dg_mode = "NORMAL"
    else:
        # Day: emergency only
        if params.allow_emergency_dg_day and state.soc <= state.emergency_soc_mwh:
            dg_should_run = True
            dg_mode = "EMERGENCY"

    # Night with DG triggered
    if is_night and dg_should_run and state.dg_capacity > 0:
        hour.dg_running = True
        hour.dg_mode = dg_mode

        if not state.dg_was_running:
            state.total_dg_starts += 1
        state.total_dg_runtime_hours += 1

        dg_output = state.dg_capacity
        hour.dg_to_load = min(dg_output, remaining_load)
        remaining_load -= hour.dg_to_load
        dg_excess = dg_output - hour.dg_to_load

        # Assist mode
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load
            hour.bess_assisted = True
            hour.solar_curtailed = excess_solar
            hour.dg_curtailed = dg_excess
        # Recovery mode
        else:
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar

            if dg_excess > 0 and params.dg_charges_bess and not state.bess_disabled_today:
                hour.dg_to_bess, charge_power_used = charge_bess(state, dg_excess, charge_power_used)
                hour.dg_curtailed = dg_excess - hour.dg_to_bess
            else:
                hour.dg_curtailed = dg_excess

    # Night without DG or Day
    else:
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(state, excess_solar, charge_power_used)
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar

        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged = discharge_bess(state, params, remaining_load)
            remaining_load -= hour.bess_to_load

        # Day emergency
        if not is_night and dg_should_run and remaining_load > 0 and state.dg_capacity > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, bess_discharged, charge_power_used, "EMERGENCY")

    return remaining_load, bess_discharged, charge_power_used


# =============================================================================
# MAIN SIMULATION LOOP
# =============================================================================

DISPATCH_FUNCTIONS = {
    0: dispatch_template_0,
    1: dispatch_template_1,
    2: dispatch_template_2,
    3: dispatch_template_3,
    4: dispatch_template_4,
    5: dispatch_template_5,
    6: dispatch_template_6,
}


def run_simulation(params: SimulationParams, template_id: int,
                   num_hours: int = 8760) -> List[HourlyResult]:
    """
    Execute hourly simulation.

    Args:
        params: Simulation parameters
        template_id: Template (0-6)
        num_hours: Hours to simulate (default 8760)

    Returns:
        List of HourlyResult
    """
    state = initialize_simulation(params)
    dispatch_func = DISPATCH_FUNCTIONS.get(template_id, dispatch_template_0)
    results = []

    load_len = len(params.load_profile)
    solar_len = len(params.solar_profile)

    for t in range(num_hours):
        # Daily reset
        day_of_year = (t // 24) + 1
        if day_of_year > state.current_day:
            state.current_day = day_of_year
            state.daily_discharge = 0
            state.daily_cycles = 0
            state.bess_disabled_today = False

        # Initialize hour
        hour = HourlyResult()
        hour.t = t + 1
        hour.day = day_of_year
        hour.hour_of_day = t % 24

        hour.load = params.load_profile[t % load_len] if load_len > 0 else 0
        hour.solar = params.solar_profile[t % solar_len] if solar_len > 0 else 0

        remaining_load = hour.load

        # Solar direct to load
        hour.solar_to_load = min(hour.solar, remaining_load)
        remaining_load -= hour.solar_to_load
        excess_solar = hour.solar - hour.solar_to_load

        # Template dispatch
        remaining_load, bess_discharged, charge_power_used = dispatch_func(
            params, state, hour, remaining_load, excess_solar)

        # Unserved
        hour.unserved = remaining_load if remaining_load > 0.001 else 0

        # SoC clamping
        state.soc = max(state.min_soc_mwh, min(state.soc, state.max_soc_mwh))

        # Record results
        hour.soc = state.soc
        hour.soc_pct = (state.soc / state.bess_capacity * 100) if state.bess_capacity > 0 else 0
        hour.daily_cycles = state.daily_cycles
        hour.bess_disabled = state.bess_disabled_today

        # BESS state for display
        if hour.bess_to_load > 0:
            hour.bess_state = "Discharging"
            hour.bess_power = hour.bess_to_load
        elif hour.solar_to_bess > 0 or hour.dg_to_bess > 0:
            hour.bess_state = "Charging"
            hour.bess_power = -(hour.solar_to_bess + hour.dg_to_bess)
        else:
            hour.bess_state = "Idle"
            hour.bess_power = 0

        results.append(hour)
        state.dg_was_running = hour.dg_running

    return results


def calculate_metrics(results: List[HourlyResult], params: SimulationParams) -> SummaryMetrics:
    """Calculate summary metrics from simulation results."""
    metrics = SummaryMetrics()

    metrics.total_load = sum(r.load for r in results)
    metrics.total_solar_generation = sum(r.solar for r in results)
    metrics.total_solar_to_load = sum(r.solar_to_load for r in results)
    metrics.total_solar_to_bess = sum(r.solar_to_bess for r in results)
    metrics.total_solar_curtailed = sum(r.solar_curtailed for r in results)
    metrics.total_bess_to_load = sum(r.bess_to_load for r in results)
    metrics.total_dg_to_load = sum(r.dg_to_load for r in results)
    metrics.total_dg_to_bess = sum(r.dg_to_bess for r in results)
    metrics.total_dg_curtailed = sum(r.dg_curtailed for r in results)
    metrics.total_unserved = sum(r.unserved for r in results)

    # Count hours with actual load demand (important for seasonal patterns)
    metrics.hours_with_load = sum(1 for r in results if r.load > 0)

    # Delivery hours: only count hours where there was load AND it was fully served
    metrics.hours_full_delivery = sum(1 for r in results if r.load > 0 and r.unserved < 0.001)
    metrics.hours_green_delivery = sum(1 for r in results if r.load > 0 and r.unserved < 0.001 and not r.dg_running)
    metrics.hours_with_dg = sum(1 for r in results if r.dg_running)

    # Calculate percentages against hours with load (not total hours)
    if metrics.hours_with_load > 0:
        metrics.pct_full_delivery = metrics.hours_full_delivery / metrics.hours_with_load * 100
        metrics.pct_green_delivery = metrics.hours_green_delivery / metrics.hours_with_load * 100
    else:
        metrics.pct_full_delivery = 100.0  # No load = 100% delivery by default
        metrics.pct_green_delivery = 100.0

    if metrics.total_load > 0:
        metrics.pct_unserved = metrics.total_unserved / metrics.total_load * 100
    if metrics.total_solar_generation > 0:
        metrics.pct_solar_curtailed = metrics.total_solar_curtailed / metrics.total_solar_generation * 100

    # Calculate wastage during load hours only (for seasonal loads)
    metrics.solar_during_load_hours = sum(r.solar for r in results if r.load > 0)
    metrics.solar_curtailed_during_load_hours = sum(r.solar_curtailed for r in results if r.load > 0)
    if metrics.solar_during_load_hours > 0:
        metrics.pct_solar_curtailed_load_hours = (
            metrics.solar_curtailed_during_load_hours / metrics.solar_during_load_hours * 100
        )

    metrics.dg_runtime_hours = metrics.hours_with_dg
    metrics.dg_starts = sum(1 for i, r in enumerate(results)
                           if r.dg_running and (i == 0 or not results[i-1].dg_running))

    metrics.bess_throughput = metrics.total_bess_to_load
    usable = params.bess_capacity * (params.bess_max_soc - params.bess_min_soc) / 100
    if usable > 0:
        metrics.bess_equivalent_cycles = metrics.bess_throughput / usable

    # Fuel consumption metrics
    metrics.total_fuel_consumed = sum(r.dg_fuel_consumed for r in results)
    metrics.cycle_charging_hours = sum(1 for r in results if r.cycle_charging)

    if metrics.dg_runtime_hours > 0:
        metrics.avg_fuel_rate_lph = metrics.total_fuel_consumed / metrics.dg_runtime_hours

    total_dg_delivered = metrics.total_dg_to_load + metrics.total_dg_to_bess
    if total_dg_delivered > 0:
        # L per MWh delivered
        metrics.specific_fuel_consumption = metrics.total_fuel_consumed / total_dg_delivered

    # Energy-based green delivery metrics
    metrics.total_green_energy_delivered = (
        metrics.total_solar_to_load + metrics.total_bess_to_load
    )
    metrics.total_energy_delivered = (
        metrics.total_solar_to_load +
        metrics.total_bess_to_load +
        metrics.total_dg_to_load
    )

    if metrics.total_energy_delivered > 0:
        metrics.pct_green_energy = (
            metrics.total_green_energy_delivered /
            metrics.total_energy_delivered * 100
        )
    else:
        metrics.pct_green_energy = 0.0

    return metrics
